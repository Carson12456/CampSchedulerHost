"""Legacy ConstrainedScheduler methods (split mixin part)."""

from __future__ import annotations

import math
import os
import random
import typing
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

from ...activities import get_activity_by_name, get_all_activities
from ...models import Activity, Day, ScheduleEntry, TimeSlot, Troop, Zone, generate_time_slots
from .. import config_loader
from ..constants import SchedulerConstants
from ..validators import would_create_excess_day_for_entries

EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()

class LegacyPart03Mixin:
    """Scheduler legacy methods part 03."""

    def _protect_aqua_trampoline_sharing(self, troop: Troop, activity: Activity, slot: TimeSlot) -> bool:
        """
        Check if swapping/moving would break existing Aqua Trampoline sharing.
        Only allow breaking sharing if the swap enables sharing elsewhere.
        Returns True if the operation should be blocked (protect sharing).
        """
        if activity.name != "Aqua Trampoline":
            return False  # Not AT, no protection needed

        # Check if this slot has sharing (2 troops)
        at_entries = [e for e in self.schedule.entries 
                     if e.time_slot == slot and e.activity.name == "Aqua Trampoline"]

        if len(at_entries) < 2:
            return False  # Not sharing, no protection needed

        # Check if removing this troop would break sharing
        other_troops = [e.troop for e in at_entries if e.troop != troop]
        if len(other_troops) == 0:
            return False  # This troop is the only one, can't break sharing

        # Sharing would be broken - check if there's a beneficial swap elsewhere
        # (This is a placeholder - actual swap logic would check if swap enables sharing)
        # For now, protect existing sharing
        return True  # Block operation to protect sharing


    def _try_schedule_activity(self, troop: Troop, activity: Activity) -> bool:
        """Try to schedule an activity for a troop, prioritizing area pair day blocking."""
        pref_rank = troop.get_priority(activity.name)

        # Define activity groups for area pair blocking
        rifle_range_activities = ["Troop Rifle", "Troop Shotgun"]
        tower_ods_activities = ["Climbing Tower", "Knots and Lashings", "Orienteering", 
                                "GPS & Geocaching", "Ultimate Survivor", 
                                "What's Cooking", "Chopped!"]
        handicrafts_activities = ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"]

        staff_areas = rifle_range_activities + tower_ods_activities + handicrafts_activities
        is_staff_activity = activity.name in staff_areas
        is_handicrafts_activity = activity.name in handicrafts_activities

        # Get commissioner for this troop
        commissioner = self.troop_commissioner.get(troop.name, "")

        # === STAFF BALANCE FIRST MODE ===
        # When prioritize_staff_balance is True (during Top 5 scheduling),
        # try ALL slots sorted by total staff load to distribute evenly
        if self.prioritize_staff_balance:
            # Get all slots sorted by total staff load (lowest first)
            all_slots = sorted(self.time_slots, key=lambda s: (
                self._get_total_staff_score(s),  # Primary: total staff balance
                self._get_slot_staff_score(s, activity.name) if activity.name in self.ACTIVITY_STAFF_COUNT else 0,
                1 if s.day == Day.FRIDAY else 0  # Prefer non-Friday
            ))
            all_slots = self._rerank_slots_by_projected_score(
                troop, activity, all_slots, pref_rank
            )

            # Try each slot in staff-load order
            for slot in all_slots:
                if self._can_schedule(troop, activity, slot, slot.day):
                    self._add_to_schedule(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    if slot.day == Day.FRIDAY:
                        self._check_and_schedule_reflection(troop)
                    self._try_pair_chain(troop, activity, slot)
                    return True

            # If no slot found in staff-balance mode, fall through to normal logic
            # (This shouldn't happen normally, but provides fallback)

        # === AREA PAIR DAY BLOCKING (SOFT CONSTRAINTS) ===
        # 3-hour activities: EXCLUDE Thursday (short day) and Friday (Reflection). Allow Tuesday.
        if activity.name in self.THREE_HOUR_ACTIVITIES:
            preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]  # Tuesday allowed for Rocks

        # Archery: COMMISSIONER-AWARE CLUSTERING
        # Prefer days where OTHER TROOPS FROM SAME COMMISSIONER have archery scheduled
        # This ensures one commissioner runs all archery for a full day
        elif activity.name == "Archery":
            troop_commissioner = self.troop_commissioner.get(troop.name)

            # Find days where SAME COMMISSIONER troops already have archery
            same_comm_archery_days = []
            other_comm_archery_days = []

            for entry in self.schedule.entries:
                if entry.activity.name == "Archery":
                    entry_comm = self.troop_commissioner.get(entry.troop.name)
                    if entry.time_slot.day not in same_comm_archery_days and entry.time_slot.day not in other_comm_archery_days:
                        if entry_comm == troop_commissioner:
                            same_comm_archery_days.append(entry.time_slot.day)
                        else:
                            other_comm_archery_days.append(entry.time_slot.day)

            # DEBUG
            if same_comm_archery_days:
                print(f"  [Comm Cluster] {troop.name} Archery: Same comm ({troop_commissioner}) on {[d.name for d in same_comm_archery_days]}")

            # Build preferred days list:
            # 1. FIRST: Days where SAME commissioner already has archery (cluster with same)
            # 2. SECOND: Days where NO archery yet (start new commissioner block)
            # 3. LAST: Days where OTHER commissioner has archery (avoid mixing)
            preferred_days = []

            # Same commissioner days first (best clustering)
            for d in same_comm_archery_days:
                if d not in preferred_days and d != Day.FRIDAY:
                    preferred_days.append(d)

            # Empty days next (good for starting fresh blocks)
            for d in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY]:
                if d not in same_comm_archery_days and d not in other_comm_archery_days and d not in preferred_days:
                    preferred_days.append(d)

            # Other commissioner days last (avoid if possible)
            for d in other_comm_archery_days:
                if d not in preferred_days and d != Day.FRIDAY:
                    preferred_days.append(d)

            # Friday absolute last
            if Day.FRIDAY not in preferred_days:
                preferred_days.append(Day.FRIDAY)
            preferred_days = self._reorder_days_with_commissioner_priority(preferred_days, troop, activity.name)

        # Sailing: pair with Delta day if possible, then commissioner clustering
        elif activity.name == "Sailing" and commissioner:
            preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

            # If Delta already scheduled, put that day first (pairing)
            delta_day = next(
                (e.time_slot.day for e in self.schedule.entries
                 if e.troop == troop and e.activity.name == "Delta"),
                None
            )
            if delta_day:
                preferred_days = [delta_day] + [d for d in preferred_days if d != delta_day]

            # Commissioner-based clustering next
            comm_day = self.COMMISSIONER_SAILING_DAYS.get(commissioner)
            if comm_day and comm_day in preferred_days:
                preferred_days = [comm_day] + [d for d in preferred_days if d != comm_day]
            preferred_days = self._reorder_days_with_commissioner_priority(preferred_days, troop, activity.name)

        # Rifle Range: CLUSTER-AWARE - prefer days where rifle is already scheduled
        # AVOID FRIDAY: Commissioner activities should not conflict with Reflection
        elif activity.name in rifle_range_activities:
            # Find days where rifle activities are already scheduled
            rifle_days = self._get_days_with_activity("Troop Rifle") + self._get_days_with_activity("Troop Shotgun")
            rifle_days = list(set(rifle_days))  # Remove duplicates

            # Remove Friday from cluster days (deprioritize it)
            rifle_days_no_friday = [d for d in rifle_days if d != Day.FRIDAY]

            # DEBUG: Print cluster info
            if rifle_days:
                print(f"  [Rifle Debug] {troop.name} {activity.name}: Found existing on {[d.name for d in rifle_days]}")
            else:
                print(f"  [Rifle Debug] {troop.name} {activity.name}: No existing clusters, starting new")

            if rifle_days_no_friday:
                # Prioritize existing cluster days (except Friday)
                preferred_days = rifle_days_no_friday
                # Add commissioner day if not already in list and not Friday
                if commissioner:
                    comm_day = self.COMMISSIONER_RIFLE_DAYS.get(commissioner)
                    if comm_day and comm_day not in preferred_days and comm_day != Day.FRIDAY:
                        preferred_days.append(comm_day)
                # Add other Mon-Thu days
                for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY]:
                    if day not in preferred_days:
                        preferred_days.append(day)
                # Friday last
                if Day.FRIDAY not in preferred_days:
                    preferred_days.append(Day.FRIDAY)
            else:
                # No rifle scheduled yet (or only on Friday) - use Mon-Thu first
                if commissioner:
                    comm_day = self.COMMISSIONER_RIFLE_DAYS.get(commissioner)
                    if comm_day and comm_day != Day.FRIDAY:
                        preferred_days = [comm_day, Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
                    else:
                        preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
                else:
                    preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
            # Remove duplicates while preserving order
            seen = set()
            preferred_days = [d for d in preferred_days if not (d in seen or seen.add(d))]
            preferred_days = self._reorder_days_with_commissioner_priority(preferred_days, troop, activity.name)
            print(f"  [Rifle Debug] {troop.name} {activity.name}: Preferred days = {[d.name for d in preferred_days]}")

        # Tower+ODS: CLUSTER-AWARE - prefer days where tower/ODS is already scheduled
        elif activity.name in tower_ods_activities:
            # Find days where tower/ODS activities are already scheduled
            tower_ods_days = []
            for act in tower_ods_activities:
                tower_ods_days.extend(self._get_days_with_activity(act))
            tower_ods_days = list(set(tower_ods_days))  # Remove duplicates

            if tower_ods_days:
                # Prioritize existing cluster days
                preferred_days = tower_ods_days
                # Add commissioner day if not already in list
                if commissioner:
                    comm_day = self.COMMISSIONER_TOWER_ODS_DAYS.get(commissioner)
                    if comm_day and comm_day not in preferred_days:
                        preferred_days.append(comm_day)
                # Add days with other staff activities
                for day in self._get_days_with_staff_activities(troop, staff_areas):
                    if day not in preferred_days:
                        preferred_days.append(day)
            else:
                # No tower/ODS scheduled yet - use commissioner day or staff activity days
                if commissioner:
                    comm_day = self.COMMISSIONER_TOWER_ODS_DAYS.get(commissioner)
                    if comm_day:
                        preferred_days = [comm_day] + self._get_days_with_staff_activities(troop, staff_areas)
                    else:
                        preferred_days = self._get_days_with_staff_activities(troop, staff_areas)
                else:
                    preferred_days = self._get_days_with_staff_activities(troop, staff_areas)
            # Remove duplicates while preserving order
            seen = set()
            preferred_days = [d for d in preferred_days if not (d in seen or seen.add(d))]
            preferred_days = self._reorder_days_with_commissioner_priority(preferred_days, troop, activity.name)

        # HANDICRAFTS: CLUSTER-AWARE - prefer days where ANY handicrafts activity is already scheduled
        # This ensures Tie Dye and other handicrafts are back-to-back
        elif is_handicrafts_activity:
            # Find days where ANY handicrafts activity is already scheduled (for clustering)
            handicrafts_days = []
            for hc_act in handicrafts_activities:
                handicrafts_days.extend(self._get_days_with_activity(hc_act))
            handicrafts_days = list(set(handicrafts_days))  # Remove duplicates

            # DEBUG: Print cluster info for Tie Dye
            if activity.name == "Tie Dye":
                if handicrafts_days:
                    print(f"  [Tie Dye Debug] {troop.name}: Found existing HC on {[d.name for d in handicrafts_days]}")
                else:
                    print(f"  [Tie Dye Debug] {troop.name}: No existing HC clusters, starting new")

            if handicrafts_days:
                # HEAVY BIAS: Prioritize existing Handicrafts cluster days
                preferred_days = handicrafts_days.copy()
                # Add other days as fallback, but don't mix with dissimilar activities
                for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
                    if day not in preferred_days:
                        preferred_days.append(day)
            else:
                # No handicrafts scheduled yet - use default day order
                preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

            # Remove duplicates while preserving order
            seen = set()
            preferred_days = [d for d in preferred_days if not (d in seen or seen.add(d))]

        # ALL OTHER STAFFED ACTIVITIES: CLUSTER-AWARE
        elif is_staff_activity:
            # Find days where THIS specific activity is already scheduled
            activity_cluster_days = self._get_days_with_activity(activity.name)

            if activity_cluster_days:
                # Prioritize existing cluster days for this specific activity
                preferred_days = activity_cluster_days
                # Add days with other staff activities as fallback
                for day in self._get_days_with_staff_activities(troop, staff_areas):
                    if day not in preferred_days:
                        preferred_days.append(day)
            else:
                # No instances of this activity yet - use days with other staff activities
                preferred_days = self._get_days_with_staff_activities(troop, staff_areas)

            # Remove duplicates while preserving order
            seen = set()
            preferred_days = [d for d in preferred_days if not (d in seen or seen.add(d))]
        else:
            # Default for non-staff activities: CLUSTER-AWARE
            # Prefer days where troop already has activities (reduces day switching)
            days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
            day_counts = [(day, 
                          self._count_top5_today(troop, day),
                          self._count_activities_on_day(day),
                          self._get_day_clustering_score(troop, day)) for day in days]
            # Sort by: 1) clustering score (higher=better), 2) fewest Top 5, 3) global load balance
            # Negative clustering to sort descending (more activities = higher priority)
            day_counts.sort(key=lambda x: (-x[3], x[1], x[2]))
            preferred_days = [d for d, _, _, _ in day_counts]


        # === GLOBAL STAFF BALANCING ===
        # For activities that require staff, collect ALL slots from preferred days
        # and sort globally by total staff to minimize peak loads across all 14 slots
        if activity.name in self.ACTIVITY_STAFF_COUNT:
            all_slots = []
            for day in preferred_days:
                all_slots.extend([s for s in self.time_slots if s.day == day])

            # Sort ALL slots globally by total staff (lowest first)
            # BATCHING: Prefer slots adjacent to same activity for Tie Dye, Rifle, Shotgun
            def get_batching_score(slot):
                # Only for specific batching targets
                BATCH_TARGETS = ["Tie Dye", "Troop Rifle", "Troop Shotgun"]
                if activity.name not in BATCH_TARGETS:
                    return 0

                # Check for same activity in adjacent slots on same day
                day_entries = [e for e in self.schedule.entries 
                              if e.time_slot.day == slot.day 
                              and e.activity.name == activity.name]

                for e in day_entries:
                    if abs(e.time_slot.slot_number - slot.slot_number) == 1:
                        return -500 # Strong bonus for adjacency (negative penalty)

                # Small bonus if same day at all (clustering)
                if day_entries:
                    return -50
                return 0

            all_slots = sorted(
                all_slots,
                key=lambda s: (
                    get_batching_score(s),  # Primary: Batching (Top priority for targets)
                    self._beach_slot_preference_rank(troop, activity, s, s.day),
                    self._get_total_staff_score(s),  # Secondary: total staff balance
                    self._get_slot_staff_score(s, activity.name),  # Tertiary: zone capacity
                    1 if s.day == Day.FRIDAY else 0,  # Prefer non-Friday for staff activities
                ),
            )
            all_slots = self._rerank_slots_by_projected_score(
                troop, activity, all_slots, pref_rank
            )

            # Try each globally-sorted slot
            for slot in all_slots:
                if self._can_schedule(troop, activity, slot, slot.day):
                    self._add_to_schedule(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    if slot.day == Day.FRIDAY:
                        self._check_and_schedule_reflection(troop)
                    self._try_pair_chain(troop, activity, slot)
                    return True

            # If global search failed, fall through to day-by-day (shouldn't happen normally)

        # Try preferred days first (for non-staff activities or fallback)
        for day in preferred_days:
            day_slots = [s for s in self.time_slots if s.day == day]


            # Order slots by preference (e.g., Showerhouse prefers slot 3)
            preferred_slot_num = self.SLOT_PREFERENCES.get(activity.name)
            if preferred_slot_num:
                # Put preferred slot first
                day_slots = sorted(day_slots, key=lambda s: (0 if s.slot_number == preferred_slot_num else 1, s.slot_number))

            # Aqua Trampoline double-booking: if troop ≤16 scouts+adults, prefer slots where another small troop has AT
            troop_size = troop.scouts + troop.adults
            if activity.name == 'Aqua Trampoline' and troop_size <= 16:
                def aqua_double_book_score(slot):
                    # Check if slot has an existing small troop doing Aqua Trampoline
                    existing_at = [e for e in self.schedule.entries 
                                  if e.time_slot == slot and e.activity.name == 'Aqua Trampoline']
                    if existing_at:
                        existing_troop = existing_at[0].troop
                        existing_size = existing_troop.scouts + existing_troop.adults
                        if existing_size <= 16:
                            return 0  # Prioritize - can double-book (both ≤16 scouts+adults)
                        else:
                            return 2  # Last priority - has large troop
                    else:
                        return 1  # Second priority - empty slot
                day_slots = sorted(day_slots, key=aqua_double_book_score)

            # CLUSTER-AWARE SLOT FILTERING for exclusive activities
            # For exclusive clusterable activities (Tower, Rifle, Shotgun, Archery),
            # AVOID slots already occupied by the same activity to prevent conflicts
            clusterable_exclusive = {'Climbing Tower', 'Troop Rifle', 'Troop Shotgun', 'Archery'}
            if activity.name in clusterable_exclusive:
                # Filter out slots where this activity is already scheduled
                available_slots = []
                for slot in day_slots:
                    # Check if any troop already has this activity in this slot
                    slot_occupied = any(
                        e.time_slot == slot and e.activity.name == activity.name
                        for e in self.schedule.entries
                    )
                    if not slot_occupied:
                        available_slots.append(slot)

                # Use filtered slots if any available, otherwise use all (fallback)
                if available_slots:
                    day_slots = available_slots
                    if activity.name in ['Troop Rifle', 'Troop Shotgun', 'Climbing Tower', 'Archery']:
                        print(f"  [Cluster Smart] {troop.name} {activity.name}: {len(available_slots)}/{len([s for s in self.time_slots if s.day == day])} slots available on {day.name}")

            # STAFF-AWARE SLOT SORTING: Prefer slots with lower TOTAL staff load
            # This applies to ALL activities (not just staffed ones) to spread
            # activities across slots and avoid concentrating everything in slot 1
            # Primary: total staff across all zones (balances peak loads)
            # Secondary: zone-specific score for staffed activities
            day_slots = sorted(
                day_slots,
                key=lambda s: (
                    self._beach_slot_preference_rank(troop, activity, s, day),
                    self._get_total_staff_score(s),  # Primary: prefer low-staff slots
                    self._get_slot_staff_score(s, activity.name)
                    if activity.name in self.ACTIVITY_STAFF_COUNT
                    else 0,
                ),
            )
            day_slots = self._rerank_slots_by_projected_score(
                troop, activity, day_slots, pref_rank
            )


            for slot in day_slots:

                if self._can_schedule(troop, activity, slot, day):
                    self._add_to_schedule(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    # DEBUG: Show where archery was placed
                    if activity.name == "Archery":
                        print(f"  [Cluster Debug] {troop.name} Archery: Scheduled on {slot.day.name}-{slot.slot_number}")
                    # Try to chain a paired activity in adjacent slot
                    self._try_pair_chain(troop, activity, slot)
                    return True
                elif activity.name == "Archery":
                    # DEBUG: Show why slot was rejected
                    print(f"  [Cluster Debug] {troop.name} Archery: REJECTED {day.name}-{slot.slot_number}")
                elif activity.name in ["Troop Rifle", "Troop Shotgun"]:
                    # DEBUG: Show why slot was rejected
                    print(f"  [Rifle Debug] {troop.name} {activity.name}: REJECTED {day.name}-{slot.slot_number}")

        # Fallback: try any available slot, but prefer days with same activity type
        # SPREAD LIMITING: Don't add to new days if existing cluster days have capacity
        clusterable_activities = ['Climbing Tower', 'Troop Rifle', 'Troop Shotgun', 'Archery']
        if activity.name in clusterable_activities:
            days_with_activity = self._get_days_with_activity(activity.name)

            # First pass: ONLY existing cluster days
            if days_with_activity:
                cluster_slots = [s for s in self.time_slots if s.day in days_with_activity]
                cluster_slots = sorted(
                    cluster_slots,
                    key=lambda s: self._beach_slot_preference_rank(troop, activity, s, s.day),
                )
                cluster_slots = self._rerank_slots_by_projected_score(
                    troop, activity, cluster_slots, pref_rank
                )
                for slot in cluster_slots:
                    if self._can_schedule(troop, activity, slot, slot.day):
                        self._add_to_schedule(slot, activity, troop)
                        self._update_progress(troop, activity.name)
                        self._try_pair_chain(troop, activity, slot)
                        return True

            # Second pass: Allow new days only if necessary
            new_day_slots = [s for s in self.time_slots if s.day not in days_with_activity]
            new_day_slots = sorted(
                new_day_slots,
                key=lambda s: self._beach_slot_preference_rank(troop, activity, s, s.day),
            )
            for slot in new_day_slots:
                if self._can_schedule(troop, activity, slot, slot.day):
                    self._add_to_schedule(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    # SMART REFLECTION: Check if this Friday fill triggers Reflection
                    if slot.day == Day.FRIDAY:
                        self._check_and_schedule_reflection(troop)
                    self._try_pair_chain(troop, activity, slot)
                    return True
        else:
            # Non-clusterable: regular fallback
            for slot in sorted(
                self.time_slots,
                key=lambda s: self._beach_slot_preference_rank(troop, activity, s, s.day),
            ):
                if self._can_schedule(troop, activity, slot, slot.day):
                    self._add_to_schedule(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    # SMART REFLECTION: Check if this Friday fill triggers Reflection
                    if slot.day == Day.FRIDAY:
                        self._check_and_schedule_reflection(troop)
                    self._try_pair_chain(troop, activity, slot)
                    return True
        return False


    def _try_pair_chain(self, troop: Troop, just_scheduled: Activity, slot: TimeSlot):
        """After scheduling an activity, try to chain its paired area in an adjacent slot."""
        # Find which area this activity belongs to
        activity_area = None
        for area_name, activities in EXCLUSIVE_AREAS.items():
            if just_scheduled.name in activities:
                activity_area = area_name
                break

        # Special case: Sailing is its own area for pairing
        if just_scheduled.name == "Sailing":
            activity_area = "Sailing"

        if not activity_area:
            return

        # Find the paired area
        paired_area = self.AREA_PAIRS.get(activity_area)

        # User Request: HC/DG need "balls (Gaga/9Sq) or reserve (Free Time)" paired
        if activity_area in self.TUESDAY_ONLY_ACTIVITIES:
             paired_activities = ["Gaga Ball", "9 Square", "Campsite Free Time"]
        elif paired_area:
             # Standard behavior
             paired_activities = EXCLUSIVE_AREAS.get(paired_area, [])
             if paired_area == "Sailing":
                 paired_activities = ["Sailing"]
        else:
             return

        # Get the priority of the just-scheduled activity
        just_scheduled_priority = troop.get_priority(just_scheduled.name)

        # Only chain activities that are in a similar priority tier, UNLESS it's a "Balls" activity (HC/DG support)
        # This prevents lower-priority chains from stealing slots from higher-priority activities
        # Rule: Only chain if paired activity priority is within 5 positions of scheduled activity
        max_chain_priority = just_scheduled_priority + 5

        # EXCEPTION: Always allow chaining for "Balls" (Gaga/9 Square/Free Time) regardless of priority
        # because they are required fillers for HC/DG
        is_balls_chain = any(p in paired_activities for p in ["Gaga Ball", "9 Square", "Campsite Free Time"])

        if not is_balls_chain:
            # Cap at 15 to never chain very low priority activities (unless it's balls)
            max_chain_priority = min(max_chain_priority, 15)

            troop_paired_prefs = [a for a in paired_activities if troop.get_priority(a) < max_chain_priority]
        else:
            # For balls, look for ANY priority (even if > 15, i.e. implicit/low)
            # But specifically check if they have it in prefs or global fallback
            troop_paired_prefs = [a for a in paired_activities if a in troop.preferences]
            # If not in prefs (fillers usually aren't), just try to use them anyway if "balls" are generic
            # But the loop below iterates over `troop_paired_prefs`.
            # If Gaga/9Square are not in prefs, we might need to force add them or handle them?
            # Typically "Balls" are low priority so they ARE in prefs but high number.
            # ALWAYS add fallbacks for Balls Chain to ensure we have options if preferred item is blocked
            if is_balls_chain:
                 if "Campsite Free Time" in paired_activities and "Campsite Free Time" not in troop_paired_prefs:
                     troop_paired_prefs.append("Campsite Free Time")
                 if "Gaga Ball" in paired_activities and "Gaga Ball" not in troop_paired_prefs:
                     troop_paired_prefs.append("Gaga Ball")
                 if "9 Square" in paired_activities and "9 Square" not in troop_paired_prefs:
                     troop_paired_prefs.append("9 Square")

        # === BACK-TO-BACK SPECIFIC LOGIC ===
        # User request: Tie Dye, Troop Rifle, Troop Shotgun should be back-to-back with themselves
        # Valid pairs: Tie Dye <-> Tie Dye, Rifle <-> Rifle, Shotgun <-> Shotgun
        if just_scheduled.name in ["Tie Dye", "Troop Rifle", "Troop Shotgun"]:
             # Check if we can schedule another instance of the SAME activity
             # Only if user wants it multiple times? Assuming yes if it's in preferences multiple times?
             # Or maybe standard is 1? 
             # Usually troops only do 1, but IF they have 2, pair them.
             # Alternatively, maybe they mean back-to-back with OTHER troops? 
             # "add to that the specific activity of a tie dye should be back to back tie dyes ideally"
             # This likely means consecutive slots for SAME troop if they have multiple?
             # OR it means clustering order?
             # "same thing with rifle, back to back rilfes are best, same thing with shotgun"
             # Let's Assume this implies scheduling consecutive slots for the SAME troop if they request multiple.
             # AND/OR if they don't request multiple, we just ensure existing logic clusters them globally.
             # BUT if they mean "Back to Back" for the SAME troop:
             # We should check if they want another one.

             count_needed = troop.preferences.count(just_scheduled.name)
             count_have = sum(1 for e in self.schedule.entries if e.troop == troop and e.activity.name == just_scheduled.name)

             if count_needed > count_have:
                 # Be greedy: try to schedule another one immediately!
                 if just_scheduled.name not in troop_paired_prefs:
                     troop_paired_prefs.append(just_scheduled.name) # Self-pairing

        if not troop_paired_prefs:
            return

        if not troop_paired_prefs:
            return

        # Find adjacent slots (before and after)
        slot_index = self.time_slots.index(slot)
        adjacent_indices = []

        # Check slot before
        if slot_index > 0:
            prev_slot = self.time_slots[slot_index - 1]
            if prev_slot.day == slot.day:  # Same day
                adjacent_indices.append(slot_index - 1)

        # Check slot after (accounting for 1.5 slot activities like Sailing)
        if just_scheduled.slots == 1.5:
            # Sailing uses slot + half of next slot, so chain to slot after next
            if slot_index + 2 < len(self.time_slots):
                next_slot = self.time_slots[slot_index + 2]
                if next_slot.day == slot.day:
                    adjacent_indices.append(slot_index + 2)
        else:
            if slot_index + 1 < len(self.time_slots):
                next_slot = self.time_slots[slot_index + 1]
                if next_slot.day == slot.day:
                    adjacent_indices.append(slot_index + 1)

        # Try to schedule a paired activity in adjacent slots
        for adj_idx in adjacent_indices:
            adj_slot = self.time_slots[adj_idx]
            if not self.schedule.is_troop_free(adj_slot, troop):
                # print(f"  [Pair Debug] {troop.name}: Adj slot {adj_slot} busy")
                continue

            # Try each paired activity from troop's preferences (sorted by priority)
            for paired_name in sorted(troop_paired_prefs, key=lambda x: troop.get_priority(x)):
                paired_activity = get_activity_by_name(paired_name)

                # Check for conflicts
                if self._can_schedule(troop, paired_activity, adj_slot, adj_slot.day):
                     self._add_to_schedule(adj_slot, paired_activity, troop)
                     self._update_progress(troop, paired_name)
                     # print(f"  [Chain] {troop.name}: {just_scheduled.name} -> {slot} (paired with {paired_name} at {adj_slot})")
                     return
                else:
                     pass
                if not paired_activity:
                    continue

                # Skip if troop already has this activity
                if self._troop_has_activity(troop, paired_activity):
                    continue

                if self._can_schedule(troop, paired_activity, adj_slot, adj_slot.day):
                    self.schedule.add_entry(adj_slot, paired_activity, troop)
                    self._update_progress(troop, paired_activity.name)
                    print(f"    [Chain] {troop.name}: {paired_activity.name} -> {adj_slot} (paired with {just_scheduled.name})")
                    return  # Only chain one activity


    def _get_days_with_staff_activities(self, troop: Troop, staff_activities: list) -> list:
        """Get days where troop already has staff activities, to enable consecutive scheduling."""
        days_with_staff = []
        days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

        for day in days:
            day_slots = [s for s in self.time_slots if s.day == day]
            for entry in self.schedule.get_troop_schedule(troop):
                if entry.time_slot in day_slots and entry.activity.name in staff_activities:
                    if day not in days_with_staff:
                        days_with_staff.append(day)
                    break

        # Add remaining days
        for day in days:
            if day not in days_with_staff:
                days_with_staff.append(day)

        return days_with_staff


    def _get_days_with_activity(self, activity_name: str) -> list:
        """Get days where this specific activity is already scheduled (for clustering)."""
        days_with_activity = set()
        for entry in self.schedule.entries:
            if entry.activity.name == activity_name:
                days_with_activity.add(entry.time_slot.day)
        return list(days_with_activity)


    def _count_total_top5(self, troop: Troop) -> int:
        """Count total Top-5 activities scheduled for this troop."""
        count = 0
        for entry in self.schedule.get_troop_schedule(troop):
            if troop.get_priority(entry.activity.name) < 5:
                count += 1
        return count


    def _count_activities_on_day(self, day: Day) -> int:
        """Count total activities scheduled on a day (for load balancing)."""
        return len([e for e in self.schedule.entries if e.time_slot.day == day])


    def _update_staff_load(self, slot: TimeSlot, activity_name: str, delta: int = 1):
        """
        Update the global staff load tracking when an activity is added/removed.

        Args:
            slot: The time slot being updated
            activity_name: Name of the activity
            delta: +1 for adding, -1 for removing
        """
        if activity_name in self.STAFF_ZONE_MAP:
            zone = self.STAFF_ZONE_MAP[activity_name]
            self.staff_load_by_slot[slot][zone] += delta
            # Invalidate troop day counts cache when schedule changes
            self._cache_valid = False


    def _get_slot_staff_score(self, slot: TimeSlot, activity_name: str) -> int:
        """
        Get a penalty score for scheduling a staff activity in this slot.

        Higher penalty = worse choice (slot is already busy).
        Returns 0 for non-staff activities.
        """
        if activity_name not in self.STAFF_ZONE_MAP:
            return 0

        zone = self.STAFF_ZONE_MAP[activity_name]
        current_load = self.staff_load_by_slot[slot][zone]

        # Max capacity depends on zone
        max_capacity = SchedulerConstants.ZONE_CAPACITIES.get(zone, 1)

        # Penalty increases exponentially as we approach max
        if current_load >= max_capacity:
            return 100  # Slot is full for this zone

        # Mild penalty for partially filled slots
        return current_load * 5


    def _get_total_staff_score(self, slot: TimeSlot) -> int:
        """
        Get penalty based on total staff already assigned to this slot.

        Higher score = slot is busier, less preferred for new activities.
        """
        return self.total_staff_by_slot[slot]


    def _get_troop_day_activity_counts(self, troop: Troop) -> dict:
        """
        Get a count of how many activities a troop has scheduled on each day.

        Returns: {Day.MONDAY: 2, Day.TUESDAY: 3, ...}
        """
        # Check cache first
        if self._cache_valid and troop.name in self._troop_day_counts_cache:
            return self._troop_day_counts_cache[troop.name]

        counts = {day: 0 for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]}
        for entry in self.schedule.entries:
            if entry.troop == troop:
                counts[entry.time_slot.day] += 1

        self._troop_day_counts_cache[troop.name] = counts
        return counts


    def _would_create_excess_day(self, activity_name: str, day: Day) -> bool:
        # Delegate to shared validator helper to keep excess-day semantics consistent.
        return would_create_excess_day_for_entries(self.schedule.entries, activity_name, day)


    def _get_day_clustering_score(self, troop: Troop, day: Day) -> int:
        """
        Score how good it is to schedule an activity for this troop on this day.

        Higher score = better choice (more activities already on this day = less switching).
        """
        counts = self._get_troop_day_activity_counts(troop)
        # +10 points for each activity already on this day
        return counts[day] * 10


    def _schedule_friday_reflection(self):
        """Ensure ALL troops get Reflection on Friday, distributed by campsite proximity.

        Nearby campsites (based on north-to-south order) share the same Reflection slot.
        Now decoupled from Commissioner availability (staff-led or troop-led).
        """
        print("\n--- Scheduling Friday Reflection for ALL troops (by campsite proximity) ---")
        reflection = get_activity_by_name("Reflection")
        if not reflection:
            print("  Warning: Reflection activity not found!")
            return

        print("DEBUG: Checking slots for Reflection...")
        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]

        # Group troops by campsite proximity (divide into 3 zones: north, middle, south)
        # Each zone gets a Reflection slot
        troops_sorted = []
        for troop in self.troops:
            # Get campsite index from north-to-south order
            base_name = troop.name.replace("-A", "").replace("-B", "")
            if base_name in self.CAMPSITE_ORDER:
                idx = self.CAMPSITE_ORDER.index(base_name)
            else:
                idx = len(self.CAMPSITE_ORDER)  # Unknown campsites go last
            troops_sorted.append((idx, troop))

        troops_sorted.sort(key=lambda x: x[0])

        # Divide into 3 proximity groups (for 3 Friday slots)
        num_troops = len(troops_sorted)
        group_size = max(1, (num_troops + 2) // 3)  # Ceiling division

        troop_slot_map = {}  # Track assigned slots for base troop names

        for i, (_, troop) in enumerate(troops_sorted):
            # Determine slot based on campsite position
            base_name = troop.name.replace("-A", "").replace("-B", "")

            # Check if split troop already has assigned slot
            if base_name in troop_slot_map:
                slot_idx = troop_slot_map[base_name]
            else:
                # Assign based on campsite proximity group
                slot_idx = min(i // group_size, len(friday_slots) - 1)
                troop_slot_map[base_name] = slot_idx

            # Schedule the Reflection
            slot = friday_slots[slot_idx]
            zone_name = "north" if slot_idx == 0 else ("middle" if slot_idx == 1 else "south")

            if self.schedule.is_troop_free(slot, troop):
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot} ({zone_name} zone)")
            else:
                # Try next available slot
                scheduled = False
                for alt_slot in friday_slots:
                    if self.schedule.is_troop_free(alt_slot, troop):
                        self.schedule.add_entry(alt_slot, reflection, troop)
                        print(f"  {troop.name}: Reflection -> {alt_slot} (fallback)")
                        scheduled = True
                        break
                if not scheduled:
                    print(f"  WARNING: Could not schedule Reflection for {troop.name} (All Friday slots busy?)")
                    # FORCE SCHEDULE mechanism: Overbooking to trigger conflict resolution/recovery
                    # Prefer Slot 3 for force
                    force_slot = friday_slots[-1] 
                    self.schedule.add_entry(force_slot, reflection, troop)
                    print(f"  [FORCE] {troop.name}: Reflection -> {force_slot} (Overbooking to trigger conflict res)")


    def _schedule_friday_reflection_last(self):
        """
        Schedule Reflection in each troop's LAST available Friday slot.
        This is called AFTER most other scheduling is complete, allowing Friday
        to be optimized for clustering first.
        """
        print("\n--- Scheduling Friday Reflection (DELAYED - last slot approach) ---")
        reflection = get_activity_by_name("Reflection")
        if not reflection:
            print("  Warning: Reflection activity not found!")
            return

        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]

        for troop in self.troops:
            # Find remaining free Friday slots
            free_friday_slots = [s for s in friday_slots 
                                if self.schedule.is_troop_free(s, troop)]

            if len(free_friday_slots) == 0:
                print(f"  WARNING: No Friday slots available for {troop.name} Reflection!")
                continue
            elif len(free_friday_slots) == 1:
                # Exactly 1 slot left - perfect!
                slot = free_friday_slots[0]
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot} (only slot remaining)")
            else:
                # Multiple slots still available - take the last one
                # This shouldn't happen if called late enough, but handle gracefully
                slot = free_friday_slots[-1]  # Take last slot
                self.schedule.add_entry(slot, reflection, troop)
                commissioner = self.troop_commissioner.get(troop.name, "")
                print(f"  {troop.name}: Reflection -> {slot} ({len(free_friday_slots)} slots available, {commissioner})")


    def _optimize_friday_reflections(self):
        """Swap Friday Reflection slots within commissioners to improve Tower/ODS/Archery clustering."""
        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]

        # Staff-intensive activities that benefit from clustering
        cluster_activities = EXCLUSIVE_AREAS.get("Tower", []) + \
                           EXCLUSIVE_AREAS.get("Outdoor Skills", []) + \
                           EXCLUSIVE_AREAS.get("Archery", [])

        # Group troops by commissioner
        troops_by_commissioner = {}
        # Consolidate all troops (Ignore commissioner grouping)
        all_troops = self.troops[:]

        # Get each troop's reflection slot
        reflection_slots = {}
        for troop in all_troops:
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.activity.name == "Reflection":
                    reflection_slots[troop.name] = entry.time_slot
                    break

        # Check each pair of troops for beneficial swaps (Global Optimization)
        # Iterate all troops pair-wise
        for i, troop1 in enumerate(all_troops):
            for troop2 in all_troops[i+1:]:
                slot1 = reflection_slots.get(troop1.name)
                slot2 = reflection_slots.get(troop2.name)
                if not slot1 or not slot2 or slot1 == slot2:
                    continue

                # CRITICAL: Verify troops are free in the target slots before checking scores
                # Troop 1 is moving to Slot 2: Check if Troop 1 is free in Slot 2 (ignoring Troop 2's current Reflection there)
                # Use a custom check because is_troop_free(slot2, troop1) is exactly what we need
                # (it checks if troop1 has ANY activity in slot2)
                if not self.schedule.is_troop_free(slot2, troop1):
                    continue

                # Troop 2 is moving to Slot 1
                if not self.schedule.is_troop_free(slot1, troop2):
                    continue

                # Calculate clustering score for current assignment
                score_current = self._friday_clustering_score(troop1, slot1, cluster_activities) + \
                               self._friday_clustering_score(troop2, slot2, cluster_activities)

                # Calculate clustering score if swapped
                score_swapped = self._friday_clustering_score(troop1, slot2, cluster_activities) + \
                               self._friday_clustering_score(troop2, slot1, cluster_activities)

                # Favor spreading distinct slots if score is equal? No, focus on clustering.

                if score_swapped > score_current:
                    # Swap is beneficial - do it
                    self._swap_reflection_slots(troop1, troop2, slot1, slot2)
                    reflection_slots[troop1.name] = slot2
                    reflection_slots[troop2.name] = slot1
                    print(f"  Swapped: {troop1.name} <-> {troop2.name} (improved clustering)")


    def _friday_clustering_score(self, troop, reflection_slot, cluster_activities):
        """Score how well a Reflection slot placement helps cluster staff activities."""
        score = 0
        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]

        # Get troop's Friday activities
        troop_friday = {}
        for entry in self.schedule.entries:
            if entry.troop == troop and entry.time_slot.day == Day.FRIDAY:
                troop_friday[entry.time_slot.slot_number] = entry.activity.name

        ref_slot_num = reflection_slot.slot_number

        # Check if adjacent slots have cluster activities
        for adj_num in [ref_slot_num - 1, ref_slot_num + 1]:
            if adj_num in troop_friday and troop_friday[adj_num] in cluster_activities:
                score += 1  # Adjacent to a cluster activity is good

        return score


    def _swap_reflection_slots(self, troop1, troop2, slot1, slot2):
        """Swap Reflection entries between two troops. Uses add_entry for validation."""
        reflection = get_activity_by_name("Reflection")
        if not reflection:
            return

        # Remove old entries (caller has already verified both troops are free in target slots)
        old_entries = [e for e in self.schedule.entries
                       if e.activity.name == "Reflection" and
                       e.troop in (troop1, troop2) and
                       e.time_slot.day == Day.FRIDAY]
        for e in old_entries:
            self.schedule.entries.remove(e)

        # Add swapped entries via add_entry for validation
        if not self.schedule.add_entry(slot2, reflection, troop1):
            for e in old_entries:
                self.schedule.entries.append(e)
            return
        if not self.schedule.add_entry(slot1, reflection, troop2):
            to_remove = next((e for e in self.schedule.entries
                             if e.troop == troop1 and e.activity.name == "Reflection"
                             and e.time_slot == slot2), None)
            if to_remove:
                self.schedule.entries.remove(to_remove)
            for e in old_entries:
                self.schedule.entries.append(e)
            return


    def _optimize_area_day_filling(self):
        """
        Post-schedule optimization: Check if activities on non-preferred days 
        could be moved to fill empty slots on days where their area is available.

        If the target slot has a low-priority fill activity (like Gaga Ball),
        swap it out for the preferred staff area activity.
        """
        # Define exclusive areas to optimize
        areas_to_optimize = {
            "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
            "Tower": ["Climbing Tower"],
            "Outdoor Skills": ["Knots and Lashings", "Orienteering", "Ultimate Survivor", 
                              "What's Cooking", "Chopped!"],
        }

        # Only these LOW-PRIORITY fill activities can be swapped out
        # Do NOT include Delta, Super Troop, Sailing, Reflection, or multi-slot activities
        SWAPPABLE_FILLS = {
            "Gaga Ball", "9 Square", "Campsite Free Time"
        }

        moves_made = 0
        moved_entries = set()  # Track (troop_name, activity_name) that have already been moved

        for area_name, area_activities in areas_to_optimize.items():
            # Find days with partial usage (some slots used, some empty for this area)
            for target_day in Day:
                if target_day == Day.FRIDAY:
                    continue  # Skip Friday

                day_slots = [s for s in self.time_slots if s.day == target_day]

                # Check each slot on this day
                for target_slot in day_slots:
                    # Is this slot free for the area?
                    area_used_in_slot = False
                    for entry in self.schedule.entries:
                        if entry.time_slot == target_slot and entry.activity.name in area_activities:
                            area_used_in_slot = True
                            break

                    if area_used_in_slot:
                        continue  # Slot already has an area activity

                    # This slot is empty for the area - can we move someone here?
                    # Look for troops who have this area activity on OTHER days
                    # PRIORITY: troops who already have other activities on target_day
                    candidate_entries = []
                    for entry in self.schedule.entries:
                        if entry.activity.name not in area_activities:
                            continue
                        if entry.time_slot.day == target_day:
                            continue  # Already on this day

                        # Skip if this entry has already been moved
                        entry_key = (entry.troop.name, entry.activity.name)
                        if entry_key in moved_entries:
                            continue

                        # Check if this troop has OTHER activities on target_day
                        troop = entry.troop
                        has_activity_on_day = any(
                            e.troop == troop and e.time_slot.day == target_day
                            for e in self.schedule.entries if e != entry
                        )

                        # Check if troop's commissioner has this as their Delta day
                        commissioner = self.troop_commissioner.get(troop.name, "")
                        comm_delta_day = self.COMMISSIONER_DELTA_DAYS.get(commissioner)
                        is_comm_delta_day = (comm_delta_day == target_day)

                        # Priority scoring: (has_activity_on_day * 10) + (is_comm_delta_day * 5)
                        # Higher is better
                        priority = (10 if has_activity_on_day else 0) + (5 if is_comm_delta_day else 0)
                        candidate_entries.append((priority, entry))

                    # Sort by priority (higher first)
                    candidate_entries.sort(key=lambda x: -x[0])

                    for _, entry in candidate_entries:

                        troop = entry.troop
                        current_slot = entry.time_slot
                        activity = entry.activity

                        # Check if troop is free in target slot OR has a swappable fill activity
                        troop_free = self.schedule.is_troop_free(target_slot, troop)
                        fill_entry_to_swap = None

                        if not troop_free:
                            # Check if troop has a fill activity in target slot that we can swap out
                            for other_entry in self.schedule.entries:
                                if (other_entry.time_slot == target_slot and 
                                    other_entry.troop == troop and
                                    other_entry.activity.name in SWAPPABLE_FILLS):

                                    # PROTECTION: Never swap out high-priority preferences (Top 5)
                                    swap_priority = troop.get_priority(other_entry.activity.name)
                                    if swap_priority < 5:
                                        # This is a Top 5 preference - DON'T swap it out!
                                        continue

                                    # Found a fill activity we can swap out!
                                    fill_entry_to_swap = other_entry
                                    break

                            if not fill_entry_to_swap:
                                continue  # Troop has a non-fill activity or Top 5, can't swap

                        # Temporarily remove the area activity entry and any fill to be swapped
                        self.schedule.entries.remove(entry)
                        if fill_entry_to_swap:
                            self.schedule.entries.remove(fill_entry_to_swap)

                        # Check if moving would still respect constraints
                        can_move = self._can_schedule(troop, activity, target_slot, target_day)

                        if can_move:
                            # Move is valid! Add to new slot
                            self.schedule.add_entry(target_slot, activity, troop)
                            moves_made += 1

                            # Mark this entry as moved to prevent cascading
                            moved_entries.add((troop.name, activity.name))

                            swap_info = f" (swapped out {fill_entry_to_swap.activity.name})" if fill_entry_to_swap else ""
                            print(f"  [Optimize] {troop.name}: {activity.name} moved {current_slot} -> {target_slot}{swap_info} (fills {area_name} day)")

                            # Fill the vacated slot with a fill activity
                            self._fill_vacated_slot(troop, current_slot)

                            # Don't re-add the old entry or the fill entry
                            break
                        else:
                            # Can't move - restore the entries
                            self.schedule.entries.append(entry)
                            if fill_entry_to_swap:
                                self.schedule.entries.append(fill_entry_to_swap)

        if moves_made == 0:
            print("  No optimizations possible")
        else:
            print(f"  Made {moves_made} optimization move(s)")


    def _fill_vacated_slot(self, troop: Troop, slot: TimeSlot):
        """Fill a vacated slot with a fill activity after optimization move."""
        # Check if slot is actually empty
        if not self.schedule.is_troop_free(slot, troop):
            return  # Slot is already filled

        scheduled_names = {e.activity.name for e in self.schedule.entries if e.troop == troop}
        remaining_prefs = [p for p in troop.preferences if p not in scheduled_names]
        remaining_prefs.sort(key=lambda p: troop.get_priority(p) if troop.get_priority(p) is not None else 999)

        # Preference-first fill ordering: lower rank number always wins.
        fill_candidates = remaining_prefs + [f for f in self.DEFAULT_FILL_PRIORITY if f not in remaining_prefs]
        area_map = self._get_cluster_areas_map(include_commissioner=False)
        valid_candidates = []

        for index, fill_name in enumerate(fill_candidates):
            activity = get_activity_by_name(fill_name)
            if not activity or self._troop_has_activity(troop, activity):
                continue

            if self._is_exclusive_blocked(slot, activity.name, duration=activity.slots, ignore_troop=troop):
                continue

            strict_ok = self._can_schedule(troop, activity, slot, slot.day, relax_constraints=False)
            relaxed_ok = strict_ok or self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True)
            if not relaxed_ok:
                continue

            pref_rank = troop.get_priority(fill_name)
            if pref_rank is not None and pref_rank >= 999:
                pref_rank = None
            troop_day_count = sum(
                1
                for e in self.schedule.entries
                if e.troop == troop and e.time_slot.day == slot.day
            )
            area_name = self._get_cluster_area_name_for_activity(
                activity.name,
                include_commissioner=False,
            )
            area_day_count = 0
            if area_name:
                area_activities = area_map.get(area_name, set())
                area_day_count = sum(
                    1
                    for e in self.schedule.entries
                    if e.activity.name in area_activities and e.time_slot.day == slot.day
                )

            creates_excess_day = would_create_excess_day_for_entries(
                self.schedule.entries,
                activity.name,
                slot.day,
            )
            opens_new_area_day = bool(area_name and area_day_count == 0)
            fills_official_gap = self._would_fill_cluster_gap(troop, activity, slot)

            score = 0
            if pref_rank is not None:
                score += max(0, 140 - (pref_rank * 6))
            else:
                score += max(0, 40 - (index * 2))
            score += troop_day_count * 25
            score += area_day_count * 40
            if strict_ok:
                score += 30
            if fills_official_gap:
                score += 180
            if creates_excess_day:
                score -= 220
            if opens_new_area_day:
                score -= 90
            if slot.day == Day.FRIDAY and fill_name != "Reflection":
                score -= 15

            valid_candidates.append(
                {
                    "activity": activity,
                    "fill_name": fill_name,
                    "pref_rank": pref_rank,
                    "strict_ok": strict_ok,
                    "creates_excess_day": creates_excess_day,
                    "opens_new_area_day": opens_new_area_day,
                    "score": score,
                    "index": index,
                }
            )

        if not valid_candidates:
            return

        non_excess = [c for c in valid_candidates if not c["creates_excess_day"]]
        if non_excess:
            valid_candidates = non_excess

        existing_area_day = [c for c in valid_candidates if not c["opens_new_area_day"]]
        if existing_area_day:
            valid_candidates = existing_area_day

        best = max(
            valid_candidates,
            key=lambda c: (
                c["score"],
                1 if c["strict_ok"] else 0,
                -(c["pref_rank"] if c["pref_rank"] is not None else 999),
                -c["index"],
            ),
        )

        if self._add_to_schedule(slot, best["activity"], troop):
            print(f"    [Fill vacated] {troop.name}: {best['fill_name']} -> {slot}")
            return


    def _consolidate_staff_areas(self):
        """
        Aggressive post-schedule optimization: Move staff area activities from 
        days with few activities to days with more activities to reduce total days used.

        Goal: If Rifle is on 5 days but most activities are on Mon/Wed, try to 
        move the stragglers from Tue/Thu/Fri to Mon/Wed.
        """
        from collections import defaultdict

        areas_to_consolidate = {
            "Rifle": ["Troop Rifle", "Troop Shotgun"],
            "Tower": ["Climbing Tower"],
            "Commissioner": ["Super Troop", "Delta"],
        }

        SWAPPABLE_FILLS = {"Gaga Ball", "9 Square", "Campsite Free Time"}

        moves_made = 0

        for area_name, area_activities in areas_to_consolidate.items():
            # Count activities per day
            by_day = defaultdict(list)
            for entry in self.schedule.entries:
                if entry.activity.name in area_activities:
                    by_day[entry.time_slot.day].append(entry)

            if len(by_day) <= 2:
                continue  # Already well-clustered

            # Find "heavy" days (3 slots used) and "light" days (1-2 slots)
            heavy_days = [d for d, entries in by_day.items() if len(entries) >= 2]
            light_days = [d for d, entries in by_day.items() if len(entries) == 1]

            if not heavy_days or not light_days:
                continue

            # Try to move activities from light days to heavy days
            for light_day in light_days:
                entries_to_move = by_day[light_day][:]  # Copy list

                for entry in entries_to_move:
                    troop = entry.troop
                    activity = entry.activity
                    current_slot = entry.time_slot

                    # Try each heavy day
                    for heavy_day in heavy_days:
                        if heavy_day == Day.FRIDAY:
                            continue

                        # Find empty slots for this area on the heavy day
                        heavy_day_slots = [s for s in self.time_slots if s.day == heavy_day]

                        for target_slot in heavy_day_slots:
                            # Check if slot is already used by this area
                            area_used = any(
                                e.time_slot == target_slot and e.activity.name in area_activities
                                for e in self.schedule.entries
                            )
                            if area_used:
                                continue

                            # Check if troop is free or has swappable fill
                            troop_free = self.schedule.is_troop_free(target_slot, troop)
                            fill_to_swap = None

                            if not troop_free:
                                for other in self.schedule.entries:
                                    if (other.time_slot == target_slot and 
                                        other.troop == troop and
                                        other.activity.name in SWAPPABLE_FILLS):

                                        # PROTECTION: Never swap out high-priority preferences (Top 5)
                                        swap_priority = troop.get_priority(other.activity.name)
                                        if swap_priority < 5:
                                            continue  # Top 5 - don't swap

                                        fill_to_swap = other
                                        break
                                if not fill_to_swap:
                                    continue

                            # Try the move
                            self.schedule.entries.remove(entry)
                            if fill_to_swap:
                                self.schedule.entries.remove(fill_to_swap)

                            if self._can_schedule(troop, activity, target_slot, heavy_day):
                                # Success!
                                self.schedule.add_entry(target_slot, activity, troop)
                                moves_made += 1

                                swap_info = f" (swapped {fill_to_swap.activity.name})" if fill_to_swap else ""
                                print(f"  [Consolidate] {troop.name}: {activity.name} {current_slot} -> {target_slot}{swap_info}")

                                # Fill vacated slot
                                self._fill_vacated_slot(troop, current_slot)
                                break  # Stop looking at target slots
                            else:
                                # Restore
                                self.schedule.entries.append(entry)
                                if fill_to_swap:
                                    self.schedule.entries.append(fill_to_swap)
                        else:
                            continue  # No target slot found, try next heavy day
                        break  # Successfully moved, stop trying heavy days

        if moves_made == 0:
            print("  No consolidation possible")
        else:
            print(f"  Made {moves_made} consolidation move(s)")


    def _optimize_cross_schedule_clustering(self):
        """
        Comprehensive cross-schedule optimization: swap ANY flexible activity with 
        staff-intensive activities to improve clustering and reduce schedule gaps.

        Strategy:
        1. Identify clusterable activities (Staff + Handicrafts).
        2. Find "Cluster Days" for each troop (days where they already have activity in that area).
        3. Try to move "Cluster Activities" from Non-Cluster Days -> Cluster Days.
        4. Swap with ANY activity in the target slot, provided:
           - Target activity isn't Reflection (Protected).
           - Both activities are valid in their new slots.
           - Clustering improves.
        """
        from collections import defaultdict

        CLUSTERING_AREAS = {
            "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", 
                              "Ultimate Survivor", "What's Cooking", "Chopped!"],
            "Tower": ["Climbing Tower"],
            "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
            "Archery": ["Archery"],
            "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"]
        }

        # Measure baseline clustering
        baseline = self._measure_clustering(CLUSTERING_AREAS)

        swaps_made = 0

        # For each troop, find swap opportunities
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]

            for area_name, area_activities in CLUSTERING_AREAS.items():
                area_entries = [e for e in troop_entries 
                               if e.activity.name in area_activities]

                if not area_entries:
                    continue

                # Get the "Cluster Days" (days where this area is most active for this troop)
                # We want to move stragglers INTO these days
                global_area_days = self._get_cluster_days_for_area(area_name, area_activities)

                # Iterate through entries for this area
                for area_entry in area_entries:
                    area_day = area_entry.time_slot.day
                    area_slot = area_entry.time_slot

                    # If this entry is ON a cluster day, it's already good (mostly).
                    # But we might still swap to improve slot alignment? 
                    # For now, focus on moving OFF-cluster entries TO cluster days.
                    # Or improving slot alignment within cluster days.

                    # Try to swap with ANY other activity
                    for swap_entry in troop_entries:
                        if swap_entry == area_entry:
                            continue

                        # PROTECTED: Do not swap out Reflection (REMOVED: User allows swapping now)
                        # if swap_entry.activity.name == "Reflection":
                        #     continue

                        # Optimization: Don't swap two activities from same area (pointless)
                        if swap_entry.activity.name in area_activities:
                            continue

                        swap_day = swap_entry.time_slot.day
                        swap_slot = swap_entry.time_slot

                        # Optimization: Just trying random swaps is expensive.
                        # Only try if we are moving TO a better day/state.

                        # Check: Would swapping improve clustering?
                        if not self._would_improve_clustering_swap(
                            area_entry, swap_entry, area_name, area_activities, global_area_days
                        ):
                            continue

                        # Check feasibility
                        if not self._can_swap_entries_safe(area_entry, swap_entry):
                            continue

                        # Execute the swap
                        success = self._execute_entry_swap(area_entry, swap_entry)
                        if success:
                            swaps_made += 1
                            print(f"  [Cluster Swap] {troop.name}: {area_entry.activity.name} " +
                                  f"({area_day.name[:3]}-{area_slot.slot_number}) <-> " +
                                  f"{swap_entry.activity.name} ({swap_day.name[:3]}-{swap_slot.slot_number}) " +
                                  f"[{area_name} clustering]")
                            break  # One swap at a time per area entry

        # Measure improvement
        final = self._measure_clustering(CLUSTERING_AREAS)

        if swaps_made > 0:
            print(f"\n  Made {swaps_made} clustering swap(s)")
            print(f"  Clustering improvement:")
            for area_name in CLUSTERING_AREAS:
                before_days = baseline[area_name]['days']
                after_days = final[area_name]['days']
                if before_days != after_days:
                    print(f"    {area_name}: {before_days} days -> {after_days} days")
        else:
            print("  No beneficial swaps found")


    def _measure_clustering(self, clustering_areas):
        """Measure clustering efficiency for each area."""
        from collections import defaultdict

        results = {}
        for area_name, area_activities in clustering_areas.items():
            by_day = defaultdict(int)
            for entry in self.schedule.entries:
                if entry.activity.name in area_activities:
                    by_day[entry.time_slot.day] += 1

            total = sum(by_day.values())
            days_used = len([d for d in by_day if by_day[d] > 0])

            results[area_name] = {
                'days': days_used,
                'total': total,
                'by_day': dict(by_day)
            }

        return results


    def _optimize_super_troop_slots(self):
        """
        Comprehensive Super Troop optimization: move Super Troops to Monday when beneficial.

        Detects smart swaps like:
        - Move ST from Tue→Mon to free up archery slot for Friday
        - Chain multiple swaps to improve overall schedule quality
        - Allow multiple troops to have Super Troop on Monday (not just one)
        """
        from ...models import ScheduleEntry

        print("\n--- Comprehensive Super Troop Optimization ---")

        # Find all Super Troop entries not on Monday
        non_monday_super_troops = []

        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]

            super_troop_entry = next(
                (e for e in troop_entries if e.activity.name == "Super Troop"), 
                None
            )

            if not super_troop_entry:
                continue

            st_day = super_troop_entry.time_slot.day

            # Target: move non-Monday Super Troops to Monday
            if st_day != Day.MONDAY:
                non_monday_super_troops.append((troop, super_troop_entry))

        if not non_monday_super_troops:
            print("  All Super Troops already on Monday or no optimization needed")
            return

        print(f"  Found {len(non_monday_super_troops)} Super Troops not on Monday")

        # Try to move each to Monday
        swaps_made = 0

        for troop, super_troop_entry in non_monday_super_troops:
            # Find best Monday slot for this troop's Super Troop
            monday_slots = [s for s in self.time_slots if s.day == Day.MONDAY]

            for mon_slot in monday_slots:
                # Check if this swap would be beneficial
                swap_result = self._try_super_troop_swap_to_monday(troop, super_troop_entry, mon_slot)

                if swap_result:
                    swaps_made += 1
                    print(f"  [OK] {troop.name}: Super Troop {super_troop_entry.time_slot.day.name}-{super_troop_entry.time_slot.slot_number} -> Monday-{mon_slot.slot_number}")
                    if swap_result['reason']:
                        print(f"    Reason: {swap_result['reason']}")
                    break  # Found a good swap for this troop

        print(f"  Total Super Troop optimizations: {swaps_made}")


    def _try_super_troop_swap_to_monday(self, troop, super_troop_entry, target_monday_slot):
        """
        Try to swap Super Troop to a Monday slot.

        Returns dict with swap details if successful, None otherwise.
        """
        from ...models import ScheduleEntry

        # Check what troop currently has in target Monday slot
        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
        monday_entry = next(
            (e for e in troop_entries if e.time_slot == target_monday_slot),
            None
        )

        if not monday_entry:
            # Monday slot is empty - can't happen in a full schedule
            return None

        # === EXCLUSIVITY CHECK: Only 1 Super Troop per slot! ===
        # Check if another troop already has Super Troop in this Monday slot
        other_super_troops = [e for e in self.schedule.entries 
                              if e.activity.name == "Super Troop" 
                              and e.time_slot == target_monday_slot
                              and e.troop != troop]
        if other_super_troops:
            # Can't put Super Troop here - another troop already has it
            return None

        # Define swappable activities (low-priority fills)
        SWAPPABLE = {"Gaga Ball", "9 Square", "Fishing", "Sauna", 
                    "Shower House", "Trading Post", "Campsite Free Time"}

        # Check if Monday activity is swappable
        if monday_entry.activity.name not in SWAPPABLE:
            # Check if it's a low-priority preference (rank > 10)
            monday_priority = troop.get_priority(monday_entry.activity.name)
            if monday_priority and monday_priority <= 10:
                # Top 10 preference - don't swap it out
                return None

        # Check if swap would violate constraints
        old_st_slot = super_troop_entry.time_slot

        # Temporarily remove both entries
        self.schedule.entries.remove(super_troop_entry)
        self.schedule.entries.remove(monday_entry)

        # Try new configuration
        new_st_entry = ScheduleEntry(
            time_slot=target_monday_slot,
            activity=super_troop_entry.activity,
            troop=troop
        )
        new_swap_entry = ScheduleEntry(
            time_slot=old_st_slot,
            activity=monday_entry.activity,
            troop=troop
        )

        # Check if this violates any constraints
        self.schedule.entries.append(new_st_entry)
        self.schedule.entries.append(new_swap_entry)

        # Validate the swap doesn't break constraints
        valid = True
        reason = ""

        # Check if the swapped activity can go in the old ST slot
        # (e.g., can't put Tower after wet activity)
        if monday_entry.activity.name in self.TOWER_ODS_ACTIVITIES:
            if self._has_wet_before_slot(troop, old_st_slot):
                valid = False

        if monday_entry.activity.name in self.WET_ACTIVITIES:
            if self._has_tower_ods_before_slot(troop, old_st_slot):
                valid = False

        if not valid:
            # Revert the swap
            self.schedule.entries.remove(new_st_entry)
            self.schedule.entries.remove(new_swap_entry)
            self.schedule.entries.append(super_troop_entry)
            self.schedule.entries.append(monday_entry)
            return None

        # Swap is valid! Calculate benefit
        # Benefit: Super Troop on Monday is better than later in week
        # Also check if this frees up a better slot for other activities

        # Check if old ST slot was blocking something valuable
        if old_st_slot.day == Day.FRIDAY:
            reason = "Freed Friday slot for better activities"
        elif old_st_slot.day == Day.TUESDAY and old_st_slot.slot_number == 2:
            # Check if this helps archery clustering
            archery_entries = [e for e in troop_entries 
                             if e.activity.name == "Archery"]
            if archery_entries:
                reason = "Freed Tuesday slot, may help archery clustering"
        else:
            reason = f"Moved from {old_st_slot.day.name} to Monday"

        return {'reason': reason}


    def _get_cluster_days_for_area(self, area_name, area_activities):
        """Get days where this area is most active (top cluster days)."""
        from collections import defaultdict

        by_day = defaultdict(int)
        for entry in self.schedule.entries:
            if entry.activity.name in area_activities:
                by_day[entry.time_slot.day] += 1

        # Sort days by activity count (descending)
        sorted_days = sorted(by_day.items(), key=lambda x: x[1], reverse=True)
        return [day for day, count in sorted_days]


    def _would_improve_clustering_swap(self, area_entry, swap_entry, area_name, area_activities, cluster_days):
        """Check if swapping these entries would improve clustering."""
        area_day = area_entry.time_slot.day
        swap_day = swap_entry.time_slot.day
        area_slot_num = area_entry.time_slot.slot_number
        swap_slot_num = swap_entry.time_slot.slot_number

        # Improvement conditions:
        # 1. Area activity moves TO a cluster day (swap_day is in top cluster days)
        # 2. Area activity moves AWAY from a non-cluster day
        # 3. Reduces gaps in the schedule (slot-level clustering on same day)

        if len(cluster_days) == 0:
            return False

        # Top 2 cluster days
        top_cluster_days = cluster_days[:2] if len(cluster_days) >= 2 else cluster_days

        # Check if this moves the area activity to a better day
        day_level_improvement = (
            swap_day in top_cluster_days and area_day not in top_cluster_days
        ) or (
            # Or if it moves to a day with same area activities (consolidation)
            swap_day in cluster_days and area_day not in cluster_days
        )

        # NEW: Check for within-day slot clustering (reducing gaps)
        # If both are on the same day, prefer having staff activities in earlier or consecutive slots
        slot_level_improvement = False
        if area_day == swap_day:
            # Check if other area activities exist on this day
            other_area_on_day = [e for e in self.schedule.entries 
                                if e.activity.name in area_activities 
                                and e.time_slot.day == area_day
                                and e != area_entry]

            if other_area_on_day:
                # Calculate "gap score" - lower is better (activities closer together)
                current_gap = self._calculate_slot_gap_score(area_slot_num, other_area_on_day)
                after_swap_gap = self._calculate_slot_gap_score(swap_slot_num, other_area_on_day)

                # Improvement if swap reduces gaps
                slot_level_improvement = after_swap_gap < current_gap
            else:
                # No other area activities THIS day for this troop
                # Check if swapping brings us closer to OTHER troops' activities in same area
                global_area_entries = [e for e in self.schedule.entries 
                                      if e.activity.name in area_activities 
                                      and e.time_slot.day == area_day
                                      and e.troop != area_entry.troop]

                if global_area_entries:
                    # There ARE other troops doing this area today - cluster with them
                    current_gap = self._calculate_slot_gap_score(area_slot_num, global_area_entries)
                    after_swap_gap = self._calculate_slot_gap_score(swap_slot_num, global_area_entries)
                    slot_level_improvement = after_swap_gap < current_gap

        return day_level_improvement or slot_level_improvement


    def _calculate_slot_gap_score(self, slot_num, other_entries):
        """Calculate gap score for a slot relative to other entries. Lower = better clustering."""
        other_slots = [e.time_slot.slot_number for e in other_entries]
        if not other_slots:
            return 999  # No other entries, high gap

        # Calculate minimum distance to nearest other activity
        # Pure clustering - no slot preference bias
        min_distance = min(abs(slot_num - s) for s in other_slots)

        return min_distance


    def _can_swap_entries_safe(self, entry1, entry2):
        """Check if two entries can be safely swapped without violating constraints."""
        troop = entry1.troop

        if troop != entry2.troop:
            return False  # Can only swap within same troop

        activity1 = entry1.activity
        activity2 = entry2.activity
        slot1 = entry1.time_slot
        slot2 = entry2.time_slot
        day1 = slot1.day
        day2 = slot2.day

        # Temporarily remove both entries (with safety checks)
        if entry1 not in self.schedule.entries or entry2 not in self.schedule.entries:
            return False  # Entries no longer exist

        self.schedule.entries.remove(entry1)
        self.schedule.entries.remove(entry2)

        # Check if activity1 can go to slot2
        can_swap_1_to_2 = (
            self.schedule.is_troop_free(slot2, troop) and
            self.schedule.is_activity_available(slot2, activity1, troop) and
            self._can_schedule(troop, activity1, slot2, day2)
        )

        # Check if activity2 can go to slot1
        can_swap_2_to_1 = (
            self.schedule.is_troop_free(slot1, troop) and
            self.schedule.is_activity_available(slot1, activity2, troop) and
            self._can_schedule(troop, activity2, slot1, day1)
        )

        # Restore entries
        self.schedule.entries.append(entry1)
        self.schedule.entries.append(entry2)

        return can_swap_1_to_2 and can_swap_2_to_1


    def _execute_entry_swap(self, entry1, entry2):
        """
        Execute a swap between two schedule entries.

        CRITICAL: Validates constraints BEFORE executing swap.
        Constraint compliance is MANDATORY - returns False if validation fails.
        """
        troop1 = entry1.troop
        troop2 = entry2.troop
        slot1 = entry1.time_slot
        slot2 = entry2.time_slot

        # COMPREHENSIVE CONSTRAINT VALIDATION: Use _can_schedule for both activities
        # Constraint compliance is MANDATORY - no exceptions
        can_move_1 = self._can_schedule(troop1, entry1.activity, slot2, slot2.day, relax_constraints=False)
        can_move_2 = self._can_schedule(troop2, entry2.activity, slot1, slot1.day, relax_constraints=False)

        if not (can_move_1 and can_move_2):
            return False  # Constraint violation - abort swap

        # Remove both entries
        self.schedule.entries.remove(entry1)
        self.schedule.entries.remove(entry2)

        # Create new entries with swapped slots
        new_entry1 = ScheduleEntry(time_slot=slot2, activity= entry1.activity, troop= troop1)
        new_entry2 = ScheduleEntry(time_slot=slot1, activity= entry2.activity, troop= troop2)

        self.schedule.entries.append(new_entry1)
        self.schedule.entries.append(new_entry2)

        return True


    def _schedule_delta_early(self):
        """Schedule Delta ONLY for troops that have it in their preferences.

        Delta is now treated like any other requested activity (no longer mandatory).
        It is scheduled based purely on preference rank with early week bias.
        PROMOTED PAIRING: Prefers days where Sailing is already scheduled (+15 bonus per Spine).
        """
        print("\n--- Scheduling Delta (by preference rank, early week bias, Sailing pairing) ---")
        delta = get_activity_by_name("Delta")
        if not delta:
            return

        # Filter to only troops that have Delta in their preferences
        # Sort by preference rank (lower index = higher priority)
        troops_wanting_delta = []
        for troop in self.troops:
            if "Delta" in troop.preferences:
                rank = troop.preferences.index("Delta")
                troops_wanting_delta.append((troop, rank))

        if not troops_wanting_delta:
            print("  No troops requested Delta in their preferences")
            return

        # Sort by preference rank (higher priority = scheduled first)
        troops_wanting_delta.sort(key=lambda x: x[1])

        print(f"  Troops requesting Delta (sorted by rank): {[(t.name, r+1) for t, r in troops_wanting_delta]}")

        scheduled_count = 0
        for troop, rank in troops_wanting_delta:
            if self.troop_has_delta.get(troop.name, False):
                continue  # Already scheduled

            # PROMOTED PAIRING: Check if troop has Sailing scheduled, prefer that day
            sailing_day = None
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.activity.name == "Sailing":
                    sailing_day = entry.time_slot.day
                    break

            # Commissioner priority: assigned day -> fill days -> other commissioner days.
            preferred_days = self._reorder_days_with_commissioner_priority(
                [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY],
                troop,
                "Delta",
            )

            # Keep promoted pairing, but never overtake first-priority commissioner day.
            if sailing_day and sailing_day in preferred_days and sailing_day != preferred_days[0]:
                preferred_days.remove(sailing_day)
                preferred_days.insert(1, sailing_day)
                print(f"  [Promoted Pairing] {troop.name}: Sailing on {sailing_day.value}, preferring Delta there")

            preferred_slot_order = []
            for day in preferred_days:
                preferred_slot_order.extend([s for s in self.time_slots if s.day == day])

            scheduled = False
            for slot in preferred_slot_order:
                if self._can_schedule(troop, delta, slot, slot.day):
                    self.schedule.add_entry(slot, delta, troop)
                    self.troop_has_delta[troop.name] = True
                    self._update_progress(troop, "Delta")
                    pairing_note = " (Sailing paired!)" if sailing_day and slot.day == sailing_day else ""
                    print(f"  {troop.name}: Delta (#{rank+1}) -> {slot}{pairing_note}")
                    scheduled = True
                    scheduled_count += 1
                    break

            if not scheduled:
                print(f"  WARNING: Could not schedule Delta for {troop.name} (#{rank+1})")

        print(f"  Scheduled {scheduled_count}/{len(troops_wanting_delta)} Delta requests")


    def _schedule_delta_sailing_pairs(self):
        """Schedule Delta + Sailing together on the same day when both are requested."""
        from ...models import Day, TimeSlot

        print("\n--- Scheduling Delta + Sailing Pairs ---")
        delta = get_activity_by_name("Delta")
        sailing = get_activity_by_name("Sailing")
        if not delta or not sailing:
            return

        # AGGRESSIVELY prefer days with exactly 1 Sailing (to get to 2 per day)
        sailing_day_counts = defaultdict(int)
        for entry in self.schedule.entries:
            if entry.activity.name == "Sailing":
                sailing_day_counts[entry.time_slot.day] += 1

        scheduled = 0
        for troop in self.troops:
            if "Delta" not in troop.preferences or "Sailing" not in troop.preferences:
                continue
            if self._troop_has_activity(troop, delta) or self._troop_has_activity(troop, sailing):
                continue

            preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]
            # Sort: days with exactly 1 sail first (to get to 2), then days with 0, then days with 2 (full)
            def day_priority(day):
                count = sailing_day_counts.get(day, 0)
                if count == 1:
                    return 0  # Highest priority - can get to 2
                elif count == 0:
                    return 1  # Medium priority - can start a new pair
                else:
                    return 2  # Lowest priority - already at max (2) or over
            preferred_days.sort(key=day_priority)

            paired = False
            for day in preferred_days:
                # Option 1: Sailing slots 1-2, Delta slot 3
                sailing_slot = TimeSlot(day=day, slot_number=1)
                delta_slot = TimeSlot(day=day, slot_number=3)
                if (self._can_schedule(troop, sailing, sailing_slot, day) and
                        self._can_schedule(troop, delta, delta_slot, day)):
                    self._add_to_schedule(sailing_slot, sailing, troop)
                    self._add_to_schedule(delta_slot, delta, troop)
                    self._update_progress(troop, "Sailing")
                    self._update_progress(troop, "Delta")
                    self.troop_has_delta[troop.name] = True
                    scheduled += 1
                    paired = True
                    break

                # Option 2: Delta slot 1, Sailing slots 2-3
                sailing_slot = TimeSlot(day=day, slot_number=2)
                delta_slot = TimeSlot(day=day, slot_number=1)
                if (self._can_schedule(troop, sailing, sailing_slot, day) and
                        self._can_schedule(troop, delta, delta_slot, day)):
                    self._add_to_schedule(sailing_slot, sailing, troop)
                    self._add_to_schedule(delta_slot, delta, troop)
                    self._update_progress(troop, "Sailing")
                    self._update_progress(troop, "Delta")
                    self.troop_has_delta[troop.name] = True
                    scheduled += 1
                    paired = True
                    break

            if paired:
                # Update sailing count for clustering
                sailing_day_counts[day] = sailing_day_counts.get(day, 0) + 1

        if scheduled == 0:
            print("  No Delta+Sailing pairs scheduled")
        else:
            print(f"  Scheduled {scheduled} Delta+Sailing pairs")


    def _schedule_sailing_pairs(self):
        """Proactively schedule overlapping Sailing sessions to maximize Same-Day bonus.

        The evaluation awards points when 2+ different troops sail on the same day.
        This method pairs troops and schedules them with overlapping slots:
        - Troop A: Slots 1-2 (Sailing starts at slot 1)
        - Troop B: Slots 2-3 (Sailing starts at slot 2)
        They share slot 2, which is allowed by the models.py fix.
        """
        from ...models import Day, TimeSlot

        print("\n--- Scheduling Sailing Pairs (Same-Day Bonus) ---")
        sailing = get_activity_by_name("Sailing")
        if not sailing:
            return

        # Find troops wanting Sailing (prioritize Top 5)
        troops_wanting_sailing = []
        for troop in self.troops:
            if "Sailing" in troop.preferences[:10]:  # Top 10 for wider net
                # Skip if already scheduled
                if self._troop_has_activity(troop, sailing):
                    continue
                priority = troop.preferences.index("Sailing") if "Sailing" in troop.preferences else 999
                troops_wanting_sailing.append((troop, priority))

        # Sort by priority (lower = better)
        troops_wanting_sailing.sort(key=lambda x: x[1])
        troops_only = [t for t, _ in troops_wanting_sailing]

        if len(troops_only) < 2:
            print(f"  Only {len(troops_only)} troop(s) want Sailing - skipping pairing")
            return

        # Pair troops: take pairs from sorted list
        pairs_scheduled = 0
        available_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]  # Avoid Thu/Fri

        i = 0
        while i + 1 < len(troops_only) and available_days:
            troop_a = troops_only[i]
            troop_b = troops_only[i + 1]

            # Try to schedule on an available day
            scheduled_day = None
            for day in available_days:
                slot_1 = TimeSlot(day=day, slot_number=1)
                slot_2 = TimeSlot(day=day, slot_number=2)

                # Check if both troops can be scheduled
                # Troop A at slot 1 (occupies 1-2), Troop B at slot 2 (occupies 2-3)
                can_a = self._can_schedule(troop_a, sailing, slot_1, day)
                can_b = self._can_schedule(troop_b, sailing, slot_2, day)

                if can_a and can_b:
                    # Schedule both
                    self._add_to_schedule(slot_1, sailing, troop_a)
                    self._add_to_schedule(slot_2, sailing, troop_b)
                    self._update_progress(troop_a, "Sailing")
                    self._update_progress(troop_b, "Sailing")
                    pairs_scheduled += 1
                    scheduled_day = day
                    print(f"  PAIR: {troop_a.name} (slot 1) + {troop_b.name} (slot 2) on {day.value}")
                    break
                else:
                    # Try reversed slots
                    can_a_alt = self._can_schedule(troop_a, sailing, slot_2, day)
                    can_b_alt = self._can_schedule(troop_b, sailing, slot_1, day)
                    if can_a_alt and can_b_alt:
                        self._add_to_schedule(slot_1, sailing, troop_b)
                        self._add_to_schedule(slot_2, sailing, troop_a)
                        self._update_progress(troop_a, "Sailing")
                        self._update_progress(troop_b, "Sailing")
                        pairs_scheduled += 1
                        scheduled_day = day
                        print(f"  PAIR: {troop_b.name} (slot 1) + {troop_a.name} (slot 2) on {day.value}")
                        break

            if scheduled_day:
                available_days.remove(scheduled_day)  # Each day can only have one pair

            i += 2  # Move to next pair

        if pairs_scheduled == 0:
            print("  No Sailing pairs scheduled")
        else:
            print(f"  Scheduled {pairs_scheduled} Sailing pairs for Same-Day bonus")


    def _schedule_early_ods_clustering(self):
        """Schedule ODS activities early for Top 10 troops on preferred cluster days."""
        from ...models import Day, TimeSlot

        print("\n--- Early ODS Clustering ---")

        ods_activities = ["Knots and Lashings", "Orienteering", "GPS & Geocaching",
                         "Ultimate Survivor", "What's Cooking", "Chopped!"]

        preferred_days = [Day.WEDNESDAY, Day.THURSDAY, Day.MONDAY]

        troops_need_ods = []
        for troop in self.troops:
            for act_name in ods_activities:
                if act_name in troop.preferences[:10]:
                    activity = get_activity_by_name(act_name)
                    if activity and not self._troop_has_activity(troop, activity):
                        rank = troop.preferences.index(act_name) + 1
                        troops_need_ods.append((troop, act_name, rank))

        troops_need_ods.sort(key=lambda x: x[2])

        scheduled = 0
        for troop, act_name, rank in troops_need_ods:
            activity = get_activity_by_name(act_name)
            for day in preferred_days:
                for slot_num in [1, 2, 3]:
                    if day == Day.THURSDAY and slot_num > 2:
                        continue
                    slot = TimeSlot(day=day, slot_number=slot_num)
                    if self.schedule.is_troop_free(slot, troop):
                        if self._can_schedule(troop, activity, slot, day):
                            self.schedule.add_entry(slot, activity, troop)
                            self._update_progress(troop, act_name)
                            scheduled += 1
                            break
                else:
                    continue
                break

        print(f"  Scheduled {scheduled} ODS activities")


    def _schedule_early_handicrafts_clustering(self):
        """Schedule Handicrafts early for Top 10 troops on preferred cluster days."""
        from ...models import Day, TimeSlot

        print("\n--- Early Handicrafts Clustering ---")

        handicraft_activities = ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"]
        preferred_days = [Day.MONDAY, Day.WEDNESDAY, Day.FRIDAY]

        troops_need_hc = []
        for troop in self.troops:
            for act_name in handicraft_activities:
                if act_name in troop.preferences[:10]:
                    activity = get_activity_by_name(act_name)
                    if activity and not self._troop_has_activity(troop, activity):
                        rank = troop.preferences.index(act_name) + 1
                        troops_need_hc.append((troop, act_name, rank))

        troops_need_hc.sort(key=lambda x: x[2])

        scheduled = 0
        for troop, act_name, rank in troops_need_hc:
            activity = get_activity_by_name(act_name)
            for day in preferred_days:
                for slot_num in [1, 2, 3]:
                    if day == Day.THURSDAY and slot_num > 2:
                        continue
                    slot = TimeSlot(day=day, slot_number=slot_num)
                    if self.schedule.is_troop_free(slot, troop):
                        if self._can_schedule(troop, activity, slot, day):
                            self.schedule.add_entry(slot, activity, troop)
                            self._update_progress(troop, act_name)
                            scheduled += 1
                            break
                else:
                    continue
                break

        print(f"  Scheduled {scheduled} Handicrafts activities")


    def _schedule_early_rifle_clustering(self):
        """Schedule Rifle/Shotgun early for Top 10 troops on preferred cluster days."""
        from ...models import Day, TimeSlot

        print("\n--- Early Rifle Range Clustering ---")

        preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]

        troops_need_rifle = []
        for troop in self.troops:
            for act_name in ["Troop Rifle", "Troop Shotgun"]:
                if act_name in troop.preferences[:10]:
                    activity = get_activity_by_name(act_name)
                    if activity and not self._troop_has_activity(troop, activity):
                        rank = troop.preferences.index(act_name) + 1
                        troops_need_rifle.append((troop, act_name, rank))

        troops_need_rifle.sort(key=lambda x: x[2])

        scheduled = 0
        for troop, act_name, rank in troops_need_rifle:
            activity = get_activity_by_name(act_name)
            for day in preferred_days:
                for slot_num in [1, 2, 3]:
                    if day == Day.THURSDAY and slot_num > 2:
                        continue
                    slot = TimeSlot(day=day, slot_number=slot_num)
                    if self.schedule.is_troop_free(slot, troop):
                        if self._can_schedule(troop, activity, slot, day):
                            self.schedule.add_entry(slot, activity, troop)
                            self._update_progress(troop, act_name)
                            scheduled += 1
                            break
                else:
                    continue
                break

        print(f"  Scheduled {scheduled} Rifle/Shotgun activities")


    def _schedule_super_troop(self):
        """Schedule Super Troop for ALL troops with flexible day selection based on scoring."""
        print("\n--- Scheduling Super Troop (flexible commissioner preference) ---")
        super_troop = get_activity_by_name("Super Troop")
        if not super_troop:
            return

        # Schedule all troops with intelligent day selection
        for troop in self.troops:
            assigned_day, fill_days, other_comm_days = self._get_commissioner_day_tiers(troop, "Super Troop")

            # Get Delta slot for this troop (if they have Delta scheduled)
            delta_slot = None
            if self.troop_has_delta.get(troop.name, False):
                for entry in self.schedule.entries:
                    if entry.troop == troop and entry.activity.name == "Delta":
                        delta_slot = entry.time_slot
                        break

            # Score all available slots
            slot_scores = []
            for slot in self.time_slots:
                # Custom Super Troop availability check:
                # - Allow if slot is empty
                # - Allow if slot has 1 troop AND both troops have < 8 scouts
                # - Reject otherwise
                existing_st_troops = [e for e in self.schedule.entries 
                                     if e.activity.name == "Super Troop" 
                                     and e.time_slot == slot]

                can_schedule = False
                if len(existing_st_troops) == 0:
                    # Slot is empty - always OK
                    can_schedule = True
                elif len(existing_st_troops) >= 1:
                    # Super Troop should NEVER share - it's exclusive (one troop per slot)
                    can_schedule = False
                # else: len == 0 means slot is empty and available

                if not can_schedule:
                    continue
                if not self.schedule.is_troop_free(slot, troop):
                    continue

                # If troop has Delta AND Delta wasn't swapped, Super Troop must come AFTER Delta
                # NEW: If Delta was swapped out for a higher preference, we relax this constraint
                if delta_slot and troop.name not in self.delta_was_swapped:
                    slot_idx = self.time_slots.index(slot)
                    delta_idx = self.time_slots.index(delta_slot)
                    if slot_idx <= delta_idx:
                        continue  # Skip slots before or same as Delta

                # Calculate score for this slot
                score = 0

                # Commissioner day ownership priority:
                # assigned day -> fill/overflow -> other commissioner day.
                if assigned_day and slot.day == assigned_day:
                    score += 500
                elif slot.day in fill_days:
                    # Super Troop should avoid Friday unless absolutely necessary.
                    if slot.day == Day.FRIDAY:
                        score -= 400
                    else:
                        score += 200
                elif slot.day in other_comm_days:
                    score += 25
                elif assigned_day:
                    score -= 150

                # HIGH PRIORITY: Distribute evenly (-100 per existing ST on this day)
                st_count_this_day = sum(1 for e in self.schedule.entries 
                                       if e.activity.name == "Super Troop" 
                                       and e.time_slot.day == slot.day)
                score -= st_count_this_day * 100

                # CLUSTERING BONUS: Prefer slots where troop has other activities on same day
                # Extra bonus for back-to-back (adjacent slots) vs separate slots on same day
                troop_day_entries = [e for e in self.schedule.entries 
                                     if e.troop == troop and e.time_slot.day == slot.day]

                if troop_day_entries:
                    # Check for back-to-back (adjacent slot)
                    has_adjacent = False
                    for e in troop_day_entries:
                        if abs(e.time_slot.slot_number - slot.slot_number) == 1:
                            has_adjacent = True
                            break

                    if has_adjacent:
                        score += 300  # Strong bonus for back-to-back
                    else:
                        score += 150  # Weaker bonus for same day but not adjacent

                # PROMOTED PAIRING: Bonus for Super Troop on same day as Rifle/Shotgun (+400)
                # Per Spine: "Super Troop + Rifle Range" is a promoted pairing
                has_rifle_today = any(e.troop == troop and e.time_slot.day == slot.day 
                                     and e.activity.name in ["Troop Rifle", "Troop Shotgun"]
                                     for e in self.schedule.entries)
                if has_rifle_today:
                    score += 400  # Strong bonus for promoted pairing

                # Mild early-week bias, but weaker than commissioner-day tiers.
                day_index = {Day.MONDAY: 0, Day.TUESDAY: 1, Day.WEDNESDAY: 2, Day.THURSDAY: 3, Day.FRIDAY: 4}
                day_idx = day_index.get(slot.day, 4)
                if slot.day in [Day.MONDAY, Day.TUESDAY]:
                    score += 60
                score -= day_idx * 35

                # NEW: Avoid Slot 2 on HC/DG day (Tuesday only) to prevent blocking pairing
                if slot.day == Day.TUESDAY and slot.slot_number == 2:
                     has_hc_dg = False
                     for pref in troop.preferences:
                         if pref in self.TUESDAY_ONLY_ACTIVITIES:
                             has_hc_dg = True
                             break
                     if has_hc_dg:
                         score -= 2000 # Massive penalty to force ST to slot 1 or 3

                slot_scores.append((slot, score))

            # Sort by score (highest first) and take the best slot
            if slot_scores:
                slot_scores.sort(key=lambda x: x[1], reverse=True)
                best_slot, best_score = slot_scores[0]
                non_friday = [ss for ss in slot_scores if ss[0].day != Day.FRIDAY]
                if non_friday:
                    best_slot, best_score = non_friday[0]

                self.schedule.add_entry(best_slot, super_troop, troop)
                self.troop_has_super_troop[troop.name] = True

                # Check if this troop is pairing with another small troop
                paired_troops = [e for e in self.schedule.entries 
                                if e.activity.name == "Super Troop" 
                                and e.time_slot == best_slot
                                and e.troop != troop]

                # Log why this slot was chosen
                if paired_troops:
                    partner = paired_troops[0].troop
                    print(f"  {troop.name} ({troop.scouts} scouts): Super Troop -> {best_slot} [PAIRED with {partner.name} ({partner.scouts} scouts)]")
                elif assigned_day and best_slot.day == assigned_day:
                    print(f"  {troop.name}: Super Troop -> {best_slot} (commissioner day bias)")
                elif best_slot.day in fill_days:
                    print(f"  {troop.name}: Super Troop -> {best_slot} (fill-day fallback)")
                else:
                    st_on_day = sum(1 for e in self.schedule.entries 
                                   if e.activity.name == "Super Troop" 
                                   and e.time_slot.day == best_slot.day)
                    print(f"  {troop.name}: Super Troop -> {best_slot} (best available, {st_on_day} ST on {best_slot.day.name})")
            else:
                print(f"  ERROR: Could not schedule Super Troop for {troop.name} - no available slots!")


    def _pre_cluster_archery(self):
         # DEPRECATED: Commissioner clustering is disabled for preference-based scheduling.
         pass


    def _pre_cluster_ods(self):
        """
        Pre-cluster Outdoor Skills (ODS) activities onto 2 days.
        ODS activities: Knots and Lashings, Orienteering, GPS & Geocaching, 
                       Ultimate Survivor, What's Cooking, Chopped!
        Goal: Reduce ODS from 3-4 days to 2 days for better staffing.
        """
        ods_activities = ["Knots and Lashings", "Orienteering", "GPS & Geocaching",
                          "Ultimate Survivor", "What's Cooking", "Chopped!"]

        # Find all troops who want ODS activities
        troops_wanting_ods = []
        for troop in self.troops:
            for activity_name in ods_activities:
                if activity_name in troop.preferences and not self._troop_has_activity(troop, get_activity_by_name(activity_name)):
                    troops_wanting_ods.append((troop, activity_name))
                    break

        if len(troops_wanting_ods) < 3:
            print("  Not enough ODS demand for pre-clustering")
            return

        print(f"  Found {len(troops_wanting_ods)} troops wanting ODS - attempting clustering")

        # Analyze which days have the most ODS potential (check troop availability)
        # Exclude Friday from ODS clustering
        days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY]
        day_scores = {}

        for day in days:
            day_slots = [s for s in self.time_slots if s.day == day]
            available_count = 0

            for troop, _ in troops_wanting_ods:
                free_slots = sum(1 for slot in day_slots if self.schedule.is_troop_free(slot, troop))
                available_count += free_slots

            day_scores[day] = available_count

        # Select top 2 days with highest availability
        best_days = sorted(day_scores.items(), key=lambda x: x[1], reverse=True)[:2]
        best_days = [day for day, _ in best_days if day_scores[day] > 0]

        print(f"  Targeting days for ODS clustering: {[d.value for d in best_days]}")

        # Pre-schedule ODS activities on these days
        scheduled_count = 0
        for target_day in best_days:
            day_slots = [s for s in self.time_slots if s.day == target_day]

            for slot in day_slots:
                for troop, pref_activity in troops_wanting_ods:
                    if not self.schedule.is_troop_free(slot, troop):
                        continue

                    # Find ODS activity troop prefers
                    for activity_name in troop.preferences:
                        if activity_name not in ods_activities:
                            continue

                        activity = get_activity_by_name(activity_name)
                        if not activity or self._troop_has_activity(troop, activity):
                            continue

                        # Only cluster if ODS is in Top 15 preferences
                        ods_priority = troop.get_priority(activity_name)
                        if ods_priority >= 15:
                            continue  # Don't cluster low-priority ODS

                        if self._can_schedule(troop, activity, slot, target_day):
                            self.schedule.add_entry(slot, activity, troop)
                            self._update_progress(troop, activity.name)
                            print(f"  [ODS Cluster] {troop.name}: {activity.name} -> {slot}")
                            scheduled_count += 1
                            break
                    else:
                        continue
                    break  # Slot filled

        if scheduled_count > 0:
            print(f"  Pre-clustered {scheduled_count} ODS activities onto {len(best_days)} days")
        else:
            print("  No ODS pre-clustering possible")


    def _pre_cluster_tower(self):
        """
        Pre-cluster Tower activities onto 2 days BEFORE wet activities take slots.

        Key insight: Wet activities (Aqua Trampoline, etc.) are popular Top 1-5 choices.
        Once they're scheduled in slot 1, they block Tower from slots 2-3 on that day.
        By pre-clustering Tower, we get Tower onto fewer days before wet activities spread out.
        """
        tower_activity = get_activity_by_name("Climbing Tower")
        if not tower_activity:
            return

        # Find all troops who want Tower (check preferences)
        troops_wanting_tower = []
        for troop in self.troops:
            if "Climbing Tower" in troop.preferences:
                if not self._troop_has_activity(troop, tower_activity):
                    # Check priority - only pre-cluster if Tower is in Top 15
                    priority = troop.get_priority("Climbing Tower")
                    if priority <= 15:
                        troops_wanting_tower.append((troop, priority))

        if len(troops_wanting_tower) < 3:
            print("  Not enough Tower demand to cluster")
            return

        print(f"  Found {len(troops_wanting_tower)} troops wanting Tower in Top 15")

        # Sort by priority (higher priority first)
        troops_wanting_tower.sort(key=lambda x: x[1])

        # Choose target days - Monday, Thursday, and Tuesday slot 1
        target_days = [Day.MONDAY, Day.THURSDAY, Day.TUESDAY]

        scheduled_count = 0
        for target_day in target_days:
            day_slots = [s for s in self.time_slots if s.day == target_day]

            for slot in day_slots:
                # Check if Tower is already scheduled in this slot
                if not self.schedule.is_activity_available(slot, tower_activity):
                    continue

                # Try to schedule Tower for a troop who wants it
                for troop, priority in troops_wanting_tower:
                    if self._troop_has_activity(troop, tower_activity):
                        continue  # Already has Tower

                    if not self.schedule.is_troop_free(slot, troop):
                        continue

                    # Check constraints
                    if self._can_schedule(troop, tower_activity, slot, target_day):
                        self.schedule.add_entry(slot, tower_activity, troop)
                        self._update_progress(troop, "Climbing Tower")
                        print(f"  [Tower Cluster] {troop.name}: Climbing Tower -> {slot} (priority {priority})")
                        scheduled_count += 1
                        break

        if scheduled_count > 0:
            print(f"  Pre-clustered {scheduled_count} Tower activities")
        else:
            print("  No Tower pre-clustering possible")
