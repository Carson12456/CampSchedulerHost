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

class LegacyPart04Mixin:
    """Scheduler legacy methods part 04."""

    def _pre_cluster_rifle_range(self):
        """Pre-cluster Rifle Range activities (Troop Rifle, Troop Shotgun) onto 2-3 days.

        IMPORTANT: Try to schedule Rifles consecutively, then Shotguns consecutively
        (instead of alternating) to reduce staff switching.
        """
        rifle_activities = ['Troop Rifle', 'Troop Shotgun']

        # Find all troops who want rifle range activities
        troops_wanting_rifle = []
        troops_wanting_shotgun = []
        for troop in self.troops:
            for activity_name in rifle_activities:
                if activity_name in troop.preferences:
                    activity = get_activity_by_name(activity_name)
                    if activity and not self._troop_has_activity(troop, activity):
                        priority = troop.get_priority(activity_name)
                        if priority <= 15:  # Cluster if Top 15
                            if activity_name == 'Troop Rifle':
                                troops_wanting_rifle.append((troop, activity_name, priority))
                            else:
                                troops_wanting_shotgun.append((troop, activity_name, priority))
                            break  # One rifle activity per troop

        total_range_demand = len(troops_wanting_rifle) + len(troops_wanting_shotgun)
        if total_range_demand < 3:
            print("  Not enough Rifle Range demand to cluster")
            return

        print(f"  Found {total_range_demand} troops wanting Rifle Range in Top 15")
        print(f"    Rifles: {len(troops_wanting_rifle)}, Shotguns: {len(troops_wanting_shotgun)}")

        # Sort each by priority
        troops_wanting_rifle.sort(key=lambda x: x[2])
        troops_wanting_shotgun.sort(key=lambda x: x[2])

        # Target days - Thursday, Wednesday, and Monday
        target_days = [Day.THURSDAY, Day.WEDNESDAY, Day.MONDAY]

        # Schedule Rifles first (consecutively), then Shotguns (consecutively)
        scheduled_count = 0
        for target_day in target_days:
            day_slots = [s for s in self.time_slots if s.day == target_day]

            # Schedule all Rifles on this day first
            for slot in day_slots:
                for troop, activity_name, priority in troops_wanting_rifle:
                    activity = get_activity_by_name(activity_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    if not self.schedule.is_troop_free(slot, troop):
                        continue

                    if self._can_schedule(troop, activity, slot, target_day):
                        self.schedule.add_entry(slot, activity, troop)
                        self._update_progress(troop, activity_name)
                        print(f"  [Rifle Cluster] {troop.name}: {activity_name} -> {slot}")
                        scheduled_count += 1
                        break

            # Then schedule Shotguns on this day
            for slot in day_slots:
                for troop, activity_name, priority in troops_wanting_shotgun:
                    activity = get_activity_by_name(activity_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    if not self.schedule.is_troop_free(slot, troop):
                        continue

                    if self._can_schedule(troop, activity, slot, target_day):
                        self.schedule.add_entry(slot, activity, troop)
                        self._update_progress(troop, activity_name)
                        print(f"  [Rifle Cluster] {troop.name}: {activity_name} -> {slot}")
                        scheduled_count += 1
                        break

        if scheduled_count > 0:
            print(f"  Pre-clustered {scheduled_count} Rifle Range activities")
        else:
            print("  No Rifle Range pre-clustering possible")


    def _fill_empty_friday_slots(self):
        """Fill any empty Friday slots to prevent gaps in the schedule."""
        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
        filled_count = 0

        for troop in self.troops:
            for slot in friday_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    continue

                # Try to fill with remaining preferences
                scheduled = False
                current_staff_load = self._count_all_staff_in_slot(slot)

                for pref_name in troop.preferences:
                    activity = get_activity_by_name(pref_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    # STAFF LOAD CHECK: Don't add staffed "bonus" activities if slot is heavy
                    activity_staff = self._get_activity_staff_count(activity.name)
                    if activity_staff > 0 and current_staff_load + activity_staff > 14:
                        continue  # Skip staffed activity in heavy slot

                    if self._is_exclusive_blocked(slot, activity.name, duration=activity.slots, ignore_troop=troop):
                        continue
                    if self._can_schedule(troop, activity, slot, Day.FRIDAY, relax_constraints=True):
                        self.schedule.add_entry(slot, activity, troop)
                        self._update_progress(troop, activity.name)
                        print(f"  [Fri Fill] {troop.name}: {activity.name} -> {slot}")
                        filled_count += 1
                        scheduled = True
                        break

                # If still empty, use default fill priority
                if not scheduled:
                    # Sort fills by staff cost for heavy slots
                    fill_candidates = []
                    for fill_name in self.DEFAULT_FILL_PRIORITY:
                        activity = get_activity_by_name(fill_name)
                        if not activity or self._troop_has_activity(troop, activity):
                            continue
                        staff_cost = self._get_activity_staff_count(activity.name)
                        fill_candidates.append((staff_cost, fill_name, activity))

                    # Sort: unstaffed first for heavy slots
                    if current_staff_load > 12:
                        fill_candidates.sort(key=lambda x: x[0])  # Ascending by staff cost

                    for _, fill_name, activity in fill_candidates:
                        if self._is_exclusive_blocked(slot, activity.name, duration=activity.slots, ignore_troop=troop):
                            continue
                        if self._can_schedule(troop, activity, slot, Day.FRIDAY, relax_constraints=True):
                            self.schedule.add_entry(slot, activity, troop)
                            print(f"  [Fri Fill Default] {troop.name}: {activity.name} -> {slot}")
                            filled_count += 1
                            break

        if filled_count > 0:
            print(f"  Filled {filled_count} empty Friday slots")


    def _get_troop_activity_slot(self, troop: Troop, activity_name: str) -> TimeSlot | None:
        """Get the slot where a troop has a specific activity."""
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.activity.name == activity_name:
                return entry.time_slot
        return None


    def _remove_continuations_helper(self, entry):
        """
        Helper method to remove continuation entries for multi-slot activities.
        Returns a list of removed continuation entries.
        """
        removed = []
        if entry.activity.slots <= 1:
            return removed

        # Find and remove continuation entries
        troop_entries = [e for e in self.schedule.entries if e.troop == entry.troop]
        for other_entry in troop_entries:
            if (other_entry.activity.name == entry.activity.name and 
                other_entry.time_slot.day == entry.time_slot.day and
                other_entry.time_slot.slot_number > entry.time_slot.slot_number):
                # This is a continuation entry
                if other_entry in self.schedule.entries:
                    self.schedule.entries.remove(other_entry)
                    removed.append(other_entry)

        return removed


    def _early_staff_area_clustering(self):
        """
        PHASE -1: Pre-schedule staffed activities with strong clustering BEFORE Top 8.

        Strategy:
        1. For each staff area, count how many troops want activities in it
        2. Pre-assign primary days based on demand
        3. Schedule high-priority (Top 8) requests for those activities on primary days

        This establishes cluster patterns early so subsequent scheduling respects them.
        """
        print("\n--- Early Staff Area Clustering (Top 8) ---")

        STAFF_AREAS = {
            'Tower': ['Climbing Tower'],
            'Rifle': ['Troop Rifle', 'Troop Shotgun'],
            'ODS': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                   'Ultimate Survivor', "What's Cooking", 'Chopped!'],
            'Handicrafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
        }

        # Prefer CONSECUTIVE days to reduce gaps in staff area scheduling
        # Monday/Tuesday/Wednesday are consecutive and avoid constraints
        # (Tuesday HC/DG is paired, Friday has Reflection)
        PREFERRED_DAYS = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

        for area_name, area_activities in STAFF_AREAS.items():
            # Count demand: how many troops want activities in this area (Top 8)?
            demand = []
            for troop in self.troops:
                for pref_idx, pref in enumerate(troop.preferences[:8]):
                    if pref in area_activities:
                        demand.append((troop, pref, pref_idx))

            if not demand:
                continue

            # Calculate primary days needed (max 3 per day, cap at 2 primary days for tighter clustering)
            import math
            num_days_needed = min(math.ceil(len(demand) / 3), 2)  # Cap at 2 days for bulletproof clustering
            primary_days = PREFERRED_DAYS[:num_days_needed]

            print(f"  {area_name}: {len(demand)} requests -> {num_days_needed} primary days: {[d.value[:3] for d in primary_days]}")

            # Sort demand by preference priority (lower = higher priority)
            demand.sort(key=lambda x: x[2])

            scheduled_count = 0

            # Try to schedule each activity on primary days
            for troop, activity_name, pref_idx in demand:
                activity = get_activity_by_name(activity_name)
                if not activity:
                    continue

                # Skip if already has this activity
                if self._troop_has_activity(troop, activity):
                    continue

                # Try primary days first, then fallback
                placed = False
                for day in primary_days + [d for d in PREFERRED_DAYS if d not in primary_days]:
                    day_slots = [s for s in self.time_slots if s.day == day]

                    for slot in day_slots:
                        if not self.schedule.is_troop_free(slot, troop):
                            continue

                        # Check if this area is already at capacity in this slot
                        area_in_slot = sum(1 for e in self.schedule.entries 
                                          if e.time_slot == slot and e.activity.name in area_activities)
                        if area_in_slot >= 1:  # Only 1 activity per slot for these areas
                            continue

                        if self._can_schedule(troop, activity, slot, day):
                            self._add_to_schedule(slot, activity, troop)
                            scheduled_count += 1
                            print(f"    {troop.name}: {activity_name} (#{pref_idx+1}) -> {day.value[:3]}-{slot.slot_number}")
                            placed = True
                            break

                    if placed:
                        break

            print(f"    Scheduled {scheduled_count}/{len(demand)} for {area_name}")

        print("")


    def _schedule_staff_optimized_areas(self):
        """Schedule Rifle Range, Tower, and Outdoor Skills to fill consecutive slots or full days."""
        # Staff-intensive areas: prefer consecutive scheduling
        staff_areas = {
            "Rifle Range": EXCLUSIVE_AREAS.get("Rifle Range", []),
            "Tower": EXCLUSIVE_AREAS.get("Tower", []),
            "Outdoor Skills": EXCLUSIVE_AREAS.get("Outdoor Skills", []),
            "Archery": EXCLUSIVE_AREAS.get("Archery", [])
        }

        days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

        for area_name, area_activities in staff_areas.items():
            if not area_activities:
                continue

            # For each day, try to fill consecutive slots for this area
            for day in days:
                day_slots = [s for s in self.time_slots if s.day == day]

                # Find troops who want any activity in this area
                for slot in day_slots:
                    # Check if area is already in use this slot
                    area_in_use = False
                    for entry in self.schedule.get_slot_activities(slot):
                        if entry.activity.name in area_activities:
                            area_in_use = True
                            break

                    if area_in_use:
                        # Area is used this slot, try to fill adjacent slots
                        self._try_fill_adjacent_slots(area_activities, day, slot.slot_number)


    def _try_fill_adjacent_slots(self, area_activities: list, day: Day, filled_slot: int):
        """Aggressively try to fill ALL slots for the same area to create full day blocks."""
        day_slots = [s for s in self.time_slots if s.day == day]

        # Try to fill ALL slots on this day (not just adjacent) for maximum clustering
        target_slots = [1, 2, 3]
        if day == Day.THURSDAY:
            target_slots = [1, 2]  # No slot 3 on Thursday (2-slot day)

        for target_num in target_slots:
            if target_num == filled_slot:
                continue  # Skip the slot that triggered this

            target_slot = next((s for s in day_slots if s.slot_number == target_num), None)
            if not target_slot:
                continue

            # Check if this slot is already used by this area
            already_used = False
            for entry in self.schedule.get_slot_activities(target_slot):
                if entry.activity.name in area_activities:
                    already_used = True
                    break

            if already_used:
                continue  # Already filled

            # AGGRESSIVE: Try to schedule ANY troop for an activity in this area
            # First pass: check ALL troop preferences (not just top 15)
            for troop in self.troops:
                if not self.schedule.is_troop_free(target_slot, troop):
                    continue

                # Check ALL preferences for this area
                for pref_name in troop.preferences:
                    if pref_name not in area_activities:
                        continue

                    activity = get_activity_by_name(pref_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    if self._can_schedule(troop, activity, target_slot, day):
                        self.schedule.add_entry(target_slot, activity, troop)
                        self._update_progress(troop, activity.name)
                        print(f"  [Staff Opt] {troop.name}: {activity.name} -> {target_slot}")
                        break
                else:
                    continue
                break  # Slot filled, move to next slot
            else:
                # Second pass: try to assign even if not in preferences (fill activity)
                # DISABLED: This blocks Top 5 recovery by filling slots with unwanted activities
                # for troop in self.troops:
                #     if not self.schedule.is_troop_free(target_slot, troop):
                #         continue
                #     
                #     for activity_name in area_activities:
                #         activity = get_activity_by_name(activity_name)
                #         if not activity or self._troop_has_activity(troop, activity):
                #             continue
                #         
                #         if self._can_schedule(troop, activity, target_slot, day, relax_constraints=True):
                #             self.schedule.add_entry(target_slot, activity, troop)
                #             print(f"  [Staff Fill] {troop.name}: {activity.name} -> {target_slot}")
                #             break
                #     else:
                #         continue
                pass  # Slot filled


    def _schedule_day(self, day: Day):
        """Schedule activities for a specific day."""
        day_slots = [s for s in self.time_slots if s.day == day]

        # Step 1: Schedule beach activities in preferred slots
        self._schedule_beach_activities(day, day_slots)

        # Step 2: Schedule Top-5 preferences (1 per day)
        self._schedule_priority_tier(day, day_slots, range(0, 5), "Top 5", max_per_day=1)

        # Step 3: Schedule Top-10 preferences (1 per day)
        self._schedule_priority_tier(day, day_slots, range(5, 10), "Top 6-10", max_per_day=1)

        # Step 4: Fill remaining slots
        self._fill_remaining_slots(day, day_slots)


    def _schedule_beach_activities(self, day: Day, day_slots: list[TimeSlot]):
        """Schedule beach activities in preferred slots.

        Thursday is the 2-slot day (only has slots 1 & 2, no slot 3).
        For Thursday: use slots 1 and 2
        For all other days: use slots 1 and 3 (avoid slot 2)
        """
        # Beach slot preference depends on day
        if day == Day.THURSDAY:
            # Thursday only has 2 slots, so use both
            preferred_slots = [s for s in day_slots if s.slot_number in [1, 2]]
        else:
            # Other days: prefer slots 1 and 3 (avoid slot 2 for better flow)
            preferred_slots = [s for s in day_slots if s.slot_number in [1, 3]]

        for troop in self.troops:
            if self._has_beach_today(troop, day):
                continue

            # Find beach activity from preferences
            beach_activity = None
            for pref_name in troop.preferences:
                if pref_name in self.BEACH_ACTIVITIES:
                    activity = get_activity_by_name(pref_name)
                    if activity and not self._troop_has_activity(troop, activity):
                        beach_activity = activity
                        break

            if not beach_activity:
                continue

            # Try preferred slots first
            scheduled = False
            for slot in preferred_slots:
                if self._can_schedule(troop, beach_activity, slot, day):
                    self.schedule.add_entry(slot, beach_activity, troop)
                    self._update_progress(troop, beach_activity.name)
                    scheduled = True
                    break

            # Fallback to any slot
            if not scheduled and beach_activity.slots == 1:
                for slot in day_slots:
                    if self._can_schedule(troop, beach_activity, slot, day):
                        self.schedule.add_entry(slot, beach_activity, troop)
                        self._update_progress(troop, beach_activity.name)
                        break


    def _schedule_priority_tier(self, day: Day, day_slots: list[TimeSlot], 
                                 pref_range: range, tier_name: str, max_per_day: int):
        """Schedule activities from a preference tier."""
        for troop in self.troops:
            if tier_name == "Top 5":
                if self._count_top5_today(troop, day) >= max_per_day:
                    continue
            elif tier_name == "Top 6-10":
                if self._count_top10_today(troop, day) >= max_per_day:
                    continue

            # PASS 1: Schedule 3-hour activities FIRST (they are hardest to fit)
            # ------------------------------------------------------------------
            three_hour_acts = ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"]

            for pref_index in pref_range:
                if pref_index >= len(troop.preferences):
                    continue

                activity_name = troop.preferences[pref_index]
                if activity_name not in three_hour_acts:
                    continue  # Skip regular activities in pass 1

                activity = get_activity_by_name(activity_name)
                if not activity or self._troop_has_activity(troop, activity):
                    continue

                # Per Spine: Allow multiple 3-hour activities per troop - do NOT block here
                # (Removed the exclusivity check that was preventing multiple 3-hour activities)

                if not self._can_schedule_on_day(troop, activity, day):
                    continue

                for slot in day_slots:
                    if self._can_schedule(troop, activity, slot, day):
                        self.schedule.add_entry(slot, activity, troop)
                        self._update_progress(troop, activity_name)
                        print(f"  {troop.name}: {activity_name} ({tier_name}) -> {slot} [PRIORITY]")
                        break

            # PASS 2: Schedule all other activities
            # -------------------------------------
            for pref_index in pref_range:
                if pref_index >= len(troop.preferences):
                    continue

                activity_name = troop.preferences[pref_index]
                if activity_name in three_hour_acts:
                    continue  # Already handled in pass 1

                activity = get_activity_by_name(activity_name)

                if not activity or self._troop_has_activity(troop, activity):
                    continue

                if not self._can_schedule_on_day(troop, activity, day):
                    continue

                for slot in day_slots:
                    if self._can_schedule(troop, activity, slot, day):
                        self.schedule.add_entry(slot, activity, troop)
                        self._update_progress(troop, activity_name)
                        print(f"  {troop.name}: {activity_name} ({tier_name}) -> {slot}")
                        break


    def _fill_remaining_slots(self, day: Day, day_slots: list[TimeSlot]):
        """Fill any empty slots using troop preferences first, then default priority list.

        ENHANCED: Prioritize filling underused slots (< 5 staff) to reduce severe underuse penalty.
        """
        if day == Day.TUESDAY:
             print(f"DEBUG: _fill_remaining_slots called for TUESDAY")

        # ENHANCEMENT: Sort slots by staff count (underused first) to prioritize filling them
        slot_staff_counts = [(slot, self._count_all_staff_in_slot(slot)) for slot in day_slots]
        slot_staff_counts.sort(key=lambda x: x[1])  # Ascending: underused slots first
        sorted_slots = [slot for slot, _ in slot_staff_counts]

        for troop in self.troops:
            for slot in sorted_slots:  # Process underused slots first
                if not self.schedule.is_troop_free(slot, troop):
                    continue
                if troop.name == "Tecumseh" and day == Day.TUESDAY:
                     print(f"DEBUG: Processing Tecumseh Tue slot {slot.slot_number}")

                # First try troop preferences
                scheduled = False
                current_staff_load = self._count_all_staff_in_slot(slot)

                # ENHANCEMENT: If slot is underused (< 5), prefer staffed activities to boost it
                prefer_staffed = current_staff_load < 5

                for pref_name in troop.preferences:
                    activity = get_activity_by_name(pref_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    # STAFF LOAD CHECK: Don't add staffed "bonus" activities if slot is heavy
                    activity_staff = self._get_activity_staff_count(activity.name)
                    if activity_staff > 0 and current_staff_load + activity_staff > 14:
                        continue  # Skip staffed activity in heavy slot

                    if self._can_schedule(troop, activity, slot, day):
                        self.schedule.add_entry(slot, activity, troop)
                        self._update_progress(troop, activity.name)
                        scheduled = True
                        break

                # If still empty, use default fill priority
                if not scheduled:
                    # Sort fills by staff cost for heavy slots
                    fill_candidates = []
                    for fill_name in self.DEFAULT_FILL_PRIORITY:
                        activity = get_activity_by_name(fill_name)
                        if not activity or self._troop_has_activity(troop, activity):
                            continue
                        staff_cost = self._get_activity_staff_count(activity.name)
                        fill_candidates.append((staff_cost, fill_name, activity))

                    # Sort: unstaffed first for heavy slots, staffed first for underused slots
                    if current_staff_load > 12:
                        fill_candidates.sort(key=lambda x: x[0])  # Ascending by staff cost
                    elif prefer_staffed:
                        fill_candidates.sort(key=lambda x: -x[0])  # Descending by staff cost (staffed first)

                    for _, fill_name, activity in fill_candidates:
                        # Use relax_constraints=True to allow same-area activities if needed
                        if self._can_schedule(troop, activity, slot, day, relax_constraints=True):
                            self.schedule.add_entry(slot, activity, troop)
                            print(f"  [Fill] {troop.name}: {fill_name} -> {slot}")
                            break


    def _is_far_apart(self, activity1: str, activity2: str) -> bool:
        """Check if two activities are too far apart for consecutive slots."""
        # Delta and ODS activities are far apart
        if activity1 == 'Delta' and activity2 in self.ODS_ACTIVITIES:
            return True
        if activity2 == 'Delta' and activity1 in self.ODS_ACTIVITIES:
            return True
        return False


    def _get_day_request_days(self, troop: Troop, activity_name: str) -> set[Day]:
        """Return requested days (if any) for a given activity."""
        if not hasattr(troop, 'day_requests') or not troop.day_requests:
            return set()
        day_map = {
            "Monday": Day.MONDAY,
            "Tuesday": Day.TUESDAY,
            "Wednesday": Day.WEDNESDAY,
            "Thursday": Day.THURSDAY,
            "Friday": Day.FRIDAY
        }
        days = set()
        for day_name, activities in troop.day_requests.items():
            if activity_name in activities:
                mapped = day_map.get(day_name)
                if mapped:
                    days.add(mapped)
        return days


    def _is_hard_fixed_day(self, activity_name: str, day: Day) -> bool:
        """Return True if the activity is fixed to a specific day by hard rules."""
        if activity_name == "Reflection" and day == Day.FRIDAY:
            return True
        if activity_name in {"History Center", "Disc Golf"} and day == Day.TUESDAY:
            return True
        return False


    def _same_day_conflicts_for(self, activity_name: str) -> set[str]:
        """Return activities that cannot occur on the same day as activity_name."""
        conflicts = set()
        for a, b in self.SAME_DAY_CONFLICTS:
            if activity_name == a:
                conflicts.add(b)
            elif activity_name == b:
                conflicts.add(a)
        return conflicts


    def _has_fixed_day_conflict(self, troop: Troop, activity: Activity, day: Day) -> bool:
        """Check if requested day is blocked by a fixed-day conflicting activity."""
        conflicts = self._same_day_conflicts_for(activity.name)
        if not conflicts:
            return False
        for entry in self.schedule.entries:
            if entry.troop != troop or entry.time_slot.day != day:
                continue
            if entry.activity.name not in conflicts:
                continue
            # Conflict exists. If the conflicting activity is fixed to this day, we can't move it.
            if self._is_hard_fixed_day(entry.activity.name, day):
                return True
            req_days = self._get_day_request_days(troop, entry.activity.name)
            if day in req_days:
                return True
        return False


    def _should_ignore_day_request_for_recovery(self, troop: Troop, activity: Activity) -> bool:
        """Allow bypassing day requests if requested day is blocked by fixed conflicts."""
        req_days = self._get_day_request_days(troop, activity.name)
        if not req_days:
            return False
        for req_day in req_days:
            if self._has_fixed_day_conflict(troop, activity, req_day):
                return True
        return False


    def _can_schedule(self, *args, **kwargs):
        """
        Check if activity can be scheduled in this slot.
        Supports both signatures:
        - _can_schedule(troop, activity, slot, day, ...)
        - _can_schedule(timeslot, activity, troop, day=None, ...)
        """
        # Handle the test signature: _can_schedule(timeslot, activity, troop, day=None)
        if len(args) == 3 and 'troop' not in kwargs and 'activity' not in kwargs and 'slot' not in kwargs and 'day' not in kwargs:
            # Test signature detected
            timeslot, activity, troop = args
            day = kwargs.get('day', timeslot.day)
            slot = timeslot
            relax_constraints = kwargs.get('relax_constraints', False)
            ignore_day_requests = kwargs.get('ignore_day_requests', False)
            allow_top1_beach_slot2 = kwargs.get('allow_top1_beach_slot2', False)
            enforce_beach_slot1_preference = kwargs.get('enforce_beach_slot1_preference', True)
        else:
            # Original signature
            if len(args) >= 4:
                troop, activity, slot, day = args[:4]
                relax_constraints = kwargs.get('relax_constraints', False)
                ignore_day_requests = kwargs.get('ignore_day_requests', False)
                allow_top1_beach_slot2 = kwargs.get('allow_top1_beach_slot2', False)
                enforce_beach_slot1_preference = kwargs.get('enforce_beach_slot1_preference', True)
            else:
                raise ValueError("Insufficient arguments for _can_schedule")

        # Original method body starts here
        if not self.schedule.is_troop_free(slot, troop):
            return False
        """Check if activity can be scheduled in this slot."""
        if not self.schedule.is_troop_free(slot, troop):
            return False

        # REQUEST-ONLY CHECK: Activities like Tie Dye and Troop Shotgun
        # can only be scheduled if the troop explicitly requested them
        if config_loader.is_request_only_activity(activity.name):
            if hasattr(troop, 'preferences') and activity.name not in troop.preferences:
                return False  # Request-only activity not in troop preferences

        # Commissioner ownership is enforced via day-ranking preferences so
        # overflow/fill days can be used before cross-commissioner borrowing.

        # NOT-BACK-TO-BACK CHECK (Delta + Tower/ODS)
        # Check if this activity would be adjacent to a prohibited activity
        adjacent_slots = []
        if slot.slot_number > 1:
            # Check previous slot
            for existing_slot in generate_time_slots():
                if existing_slot.day == day and existing_slot.slot_number == slot.slot_number - 1:
                    adjacent_slots.append(existing_slot)
                    break
        max_slot = 2 if day == Day.THURSDAY else 3
        if slot.slot_number < max_slot:
            # Check next slot
            for existing_slot in generate_time_slots():
                if existing_slot.day == day and existing_slot.slot_number == slot.slot_number + 1:
                    adjacent_slots.append(existing_slot)
                    break

        for adj_slot in adjacent_slots:
            for entry in self.schedule.entries:
                if entry.time_slot == adj_slot and entry.troop == troop:
                    if config_loader.are_activities_not_back_to_back(activity.name, entry.activity.name):
                        return False  # Would violate not-back-to-back rule

        # ENHANCED: Dynamic staff limit with clustering optimization
        # For staff clustering activities, allow higher limits to improve efficiency
        STAFF_CLUSTERING_ACTIVITIES = {
            'Climbing Tower', 'Troop Rifle', 'Troop Shotgun', 'Archery',
            'Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
            'Ultimate Survivor', "What's Cooking", 'Chopped!'
        }

        # Use higher limit for staff clustering to improve efficiency
        # But also consider clustering quality impact
        base_staff_limit = 20 if activity.name in STAFF_CLUSTERING_ACTIVITIES else 16

        # Check current clustering quality impact
        current_staff = self._count_all_staff_in_slot(slot)

        # Allow higher limits if it improves clustering
        clustering_bonus = 4 if activity.name in STAFF_CLUSTERING_ACTIVITIES else 0
        staff_limit = base_staff_limit + clustering_bonus

        # Calculate what total staff would be if we add this activity
        # Allow adding unstaffed activities (staff=0) even if slot is already full/overfull
        # They don't increase the staff burden.
        activity_staff = self._get_activity_staff_count(activity.name)
        if activity_staff > 0:
            if current_staff + activity_staff > staff_limit:
                return False  # Would exceed staff limit

        # MULTI-SLOT BOUNDARY CHECK: Ensure activity fits in remaining slots of the day
        # Get effective slots (accounting for troop size)
        effective_slots = self.schedule._get_effective_slots(activity, troop)
        slots_needed = int(effective_slots + 0.5)

        max_slot = 2 if day == Day.THURSDAY else 3
        if slot.slot_number + slots_needed - 1 > max_slot:
            return False  # Activity extends beyond end of day

        # DUPLICATE PREVENTION: Ensure troop doesn't already have this activity
        # Exception: Troop Shotgun allows duplicates for large troops (>15 people)
        # This is handled by special logic below
        if activity.name != "Troop Shotgun":
            if self._troop_has_activity(troop, activity):
                return False  # Prevent duplicate activities

        # DAY REQUEST ENFORCEMENT (Hard Constraint)
        # If troop has requested specific days for this activity, generic scheduling must respect it.
        # This prevents optimization phases from moving activities to invalid days.
        if not ignore_day_requests and hasattr(troop, 'day_requests') and troop.day_requests:
            for req_day_name, req_activities in troop.day_requests.items():
                if activity.name in req_activities:
                    # Found a restriction for this activity. Current day MUST match.
                    # normalize case (FRIDAY vs Friday)
                    if day.name.upper() != req_day_name.upper():
                        return False


        # Concurrent activities (Reflection, Campsite Time) can have multiple troops
        if activity.name not in self.CONCURRENT_ACTIVITIES:
            # BEACH SLOT RULE: Beach activities only in Slot 1 or 3 (Exception: Thu-2)
            # Exception: Sailing is allowed in Slot 2 (due to 1.5 slot duration) - handled separately
            # Exception: 2-slot beach activities (Canoe Snorkel, Float for Floats) can start at slot 2
            #            because they span into slot 3 which is valid
            # ENHANCED: Stricter enforcement to reduce violations
            if activity.name in self.BEACH_SLOT_ACTIVITIES:
                # Special handling for 2-slot beach activities
                is_2slot_beach = activity.slots >= 2 and activity.name in set(self.CANOE_ACTIVITIES)

                if is_2slot_beach:
                    # For 2-slot beach activities, slot 1 is preferred.
                    # Slot 2 is fallback only when slot 1 is not actually schedulable.
                    if day == Day.THURSDAY:
                        is_valid_beach_slot = slot.slot_number == 1
                    elif slot.slot_number == 1:
                        is_valid_beach_slot = True
                    elif slot.slot_number == 2:
                        is_valid_beach_slot = True
                        if enforce_beach_slot1_preference:
                            slot1 = next(
                                (ts for ts in self.time_slots if ts.day == day and ts.slot_number == 1),
                                None,
                            )
                            if slot1 is not None:
                                slot1_viable = self._can_schedule(
                                    troop,
                                    activity,
                                    slot1,
                                    day,
                                    relax_constraints=relax_constraints,
                                    ignore_day_requests=ignore_day_requests,
                                    allow_top1_beach_slot2=allow_top1_beach_slot2,
                                    enforce_beach_slot1_preference=False,
                                )
                                if slot1_viable:
                                    is_valid_beach_slot = False
                    else:
                        is_valid_beach_slot = False
                else:
                    # STRICTER: Only allow slot 2 on Thursday or for Top 1 beach with override
                    is_valid_beach_slot = (
                        slot.slot_number == 1 or 
                        slot.slot_number == 3 or
                        (day == Day.THURSDAY and slot.slot_number == 2)
                    )
                    # Top 1 beach override: allow slot 2 when Top 1 beach cannot be placed in 1/3
                    if not is_valid_beach_slot and slot.slot_number == 2 and day != Day.THURSDAY:
                        pref_rank = troop.get_priority(activity.name) if hasattr(troop, 'get_priority') else None
                        is_top1 = pref_rank == 0
                        # STRicter: Only allow slot 2 for Top 1 beach if explicitly enabled AND it's truly Top 1
                        if allow_top1_beach_slot2 and is_top1 and relax_constraints:
                            # Additional check: verify slots 1 and 3 are actually unavailable
                            slot1_available = self.schedule.is_troop_free(
                                next(ts for ts in self.time_slots if ts.day == day and ts.slot_number == 1), troop)
                            slot3_available = self.schedule.is_troop_free(
                                next(ts for ts in self.time_slots if ts.day == day and ts.slot_number == 3), troop)
                            if not slot1_available and not slot3_available:
                                is_valid_beach_slot = True
                if not is_valid_beach_slot:
                    return False

            # BEACH STAFF LIMIT: Max 4 staffed beach activities per slot
            # Top 5 relaxation: allow 5th when relax_constraints and Top 5 AT
            if activity.name in self.BEACH_STAFFED_ACTIVITIES:
                existing_staffed = [e for e in self.schedule.entries 
                                   if e.time_slot == slot and e.activity.name in self.BEACH_STAFFED_ACTIVITIES]
                at_top5 = (activity.name == 'Aqua Trampoline' and relax_constraints and
                    activity.name in (troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences))
                if len(existing_staffed) >= self.MAX_BEACH_STAFFED_ACTIVITIES and not at_top5:
                    return False
                if len(existing_staffed) >= self.MAX_BEACH_STAFFED_ACTIVITIES + 1:
                    return False  # Never more than 5 (4 + 1 Top 5 overload)

            # CAPACITY-AWARE EXCLUSIVITY CHECK
            # Use unified capacity checking for activities with special rules
            CAPACITY_CHECK_ACTIVITIES = SchedulerConstants.CAPACITY_CHECK_ACTIVITIES

            if activity.name in CAPACITY_CHECK_ACTIVITIES:
                allow_top5_overload = (relax_constraints and activity.name == 'Aqua Trampoline' and
                    activity.name in (troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences))
                if not self._check_activity_capacity(slot, activity, troop, allow_top5_at_overload=allow_top5_overload):
                    return False
            elif not self.schedule.is_activity_available(slot, activity, troop):
                return False

        # SAME-DAY CONFLICT CHECK (Trading Post + Campsite/Shower, Canoe pairs, etc.)
        # Spine: AT/WP/GM same-day prohibited - always enforced
        if self._has_same_day_conflict(troop, activity, day, relax_constraints=False):
            return False

        # COMMISSIONER BUSY MAP - for informational purposes only
        # Regular activities (Beach, Tower, etc.) are run by STAFF, not commissioners
        # So we do NOT block troops from doing regular activities when commissioner is busy
        # The busy map is kept for commissioner schedule display and clustering insights
        # (Activities that need commissioners - Delta, Super Troop, Reflection, Archery - 
        #  are scheduled separately before this check runs anyway)

        # GENERAL CAMP RULES (Both TC and Voyageur)
        # Rule: No Showerhouse on Monday (both camps)
        if activity.name == "Shower House" and day == Day.MONDAY:
            return False

        # NEW CONSTRAINT: Showerhouse should ideally not be before Super Troop or a wet activity
        # Check if Showerhouse is being scheduled before Super Troop or wet activities on the same day
        if activity.name == "Shower House" and not relax_constraints:
            day_slots = [s for s in self.time_slots if s.day == day]
            # Check if there's a Super Troop or wet activity later in the day
            for entry in self.schedule.get_troop_schedule(troop):
                if entry.time_slot in day_slots and entry.time_slot.slot_number > slot.slot_number:
                    # There's an activity later in the day
                    if entry.activity.name == "Super Troop" or entry.activity.name in self.WET_ACTIVITIES:
                        # Showerhouse would be before Super Troop or wet activity - this violates the constraint
                        # This is a HARD constraint: Showerhouse should NOT be before Super Troop or wet activities
                        return False

        # SOFT CONSTRAINT: Avoid Tower/ODS activities immediately before wet activities
        # Check if there's already a wet activity in next slot - don't schedule Tower/ODS
        if not relax_constraints and activity.zone in [Zone.TOWER, Zone.OUTDOOR_SKILLS]:
            next_slot_num = slot.slot_number + 1
            max_slot = 2 if day == Day.THURSDAY else 3
            if next_slot_num <= max_slot:
                next_slot = TimeSlot(day=day, slot_number=next_slot_num)
                next_entries = [e for e in self.schedule.entries 
                               if e.troop == troop and e.time_slot == next_slot]
                for next_e in next_entries:
                    if next_e.activity.name in self.WET_ACTIVITIES:
                        return False  # Don't schedule Tower/ODS before wet

        # SOFT CONSTRAINT: Prevent 2+ consecutive all-dry days
        # If this non-wet activity would make 2 consecutive dry days, try to avoid
        if not relax_constraints and activity.name not in self.WET_ACTIVITIES:
            # Check if previous day was all-dry and this day would be all-dry
            day_order = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
            day_idx = day_order.index(day) if day in day_order else -1

            if day_idx > 0:  # Has a previous day
                prev_day = day_order[day_idx - 1]

                # Get all entries for this troop on previous day
                prev_day_entries = [e for e in self.schedule.entries 
                                   if e.troop == troop and e.time_slot.day == prev_day]
                prev_day_wet = any(e.activity.name in self.WET_ACTIVITIES for e in prev_day_entries)

                if not prev_day_wet and len(prev_day_entries) >= 2:
                    # Previous day has activities but no wet - check if current day would also be dry
                    curr_day_entries = [e for e in self.schedule.entries 
                                       if e.troop == troop and e.time_slot.day == day]
                    curr_day_wet = any(e.activity.name in self.WET_ACTIVITIES for e in curr_day_entries)

                    # If current day is already all-dry and we're adding another non-wet, that's 2 dry days
                    if not curr_day_wet and len(curr_day_entries) >= 2:
                        # Two consecutive dry days - avoid adding more dry activities
                        # But allow if it's the first activity of the day
                        pass  # Allow for now - this check is complex

        # Rule: Large troops (> 15 people) need TWO Shotgun sessions to fit everyone
        # If Shotgun is in their Top 5, allow scheduling up to 2 sessions ON DIFFERENT DAYS
        if activity.name == "Troop Shotgun":
            troop_size = troop.scouts + troop.adults
            if troop_size > 15:
                # Check if Shotgun is in Top 5
                shotgun_in_top5 = "Troop Shotgun" in troop.preferences[:5]
                if not shotgun_in_top5:
                    return False  # Large troops can only get Shotgun if Top 5

                # Get existing Shotgun sessions for this troop
                existing_shotgun_entries = [e for e in self.schedule.entries 
                                           if e.troop == troop and e.activity.name == "Troop Shotgun"]

                if len(existing_shotgun_entries) >= 2:
                    return False  # Already have 2 sessions

                # If already have 1 session, ensure new one is on a different day
                if len(existing_shotgun_entries) == 1:
                    existing_day = existing_shotgun_entries[0].time_slot.day
                    if day == existing_day:
                        return False  # Must be on different day

        # VOYAGEUR/GLOBAL CONSTRAINT: HC/DG must have adjacent Balls/Reserve
        # This prevents HC/DG from being sandwiched between incompatible activities.
        if activity.name in self.TUESDAY_ONLY_ACTIVITIES and not relax_constraints:
            max_slot = 2 if day == Day.THURSDAY else 3
            neighbors = []
            if slot.slot_number > 1: neighbors.append(slot.slot_number - 1)
            if slot.slot_number < max_slot: neighbors.append(slot.slot_number + 1)

            day_entries = [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == day]
            balls_reserve = {"Gaga Ball", "9 Square", "Campsite Free Time"} | set(self.TUESDAY_ONLY_ACTIVITIES)

            has_good_neighbor = False
            has_free_neighbor = False

            for n_slot_num in neighbors:
                 existing = next((e for e in day_entries if e.time_slot.slot_number == n_slot_num), None)
                 if existing:
                    if existing.activity.name in balls_reserve:
                         has_good_neighbor = True
                         break
                 else:
                     has_free_neighbor = True

            # If no good neighbor exists AND no free neighbor exists (block), reject
            if not has_good_neighbor and not has_free_neighbor:
                return False

        # SOFT CONSTRAINT: Prevent Delta <-> ODS consecutive transitions (too far apart)
        if not relax_constraints and (activity.name == 'Delta' or activity.name in self.ODS_ACTIVITIES):
            max_slot = 2 if day == Day.THURSDAY else 3

            # Check previous slot for conflict
            if slot.slot_number > 1:
                prev_slot = TimeSlot(day=day, slot_number=slot.slot_number - 1)
                prev_entries = [e for e in self.schedule.entries 
                               if e.troop == troop and e.time_slot == prev_slot]
                for prev_e in prev_entries:
                    if self._is_far_apart(activity.name, prev_e.activity.name):
                        return False  # Don't create Delta-ODS transition

            # Check next slot for conflict
            if slot.slot_number < max_slot:
                next_slot = TimeSlot(day=day, slot_number=slot.slot_number + 1)
                next_entries = [e for e in self.schedule.entries 
                               if e.troop == troop and e.time_slot == next_slot]
                for next_e in next_entries:
                    if self._is_far_apart(activity.name, next_e.activity.name):
                        return False  # Don't create Delta-ODS transition

        # HC/DG Tuesday ONLY (both Ten Chiefs and Voyageur)
        if activity.name in self.TUESDAY_ONLY_ACTIVITIES:
            if day != Day.TUESDAY:
                return False

        # VOYAGEUR SPECIFIC RULES (other than HC/DG)
        if self.voyageur_mode:
            # Rule: Fond Du Lac and Hibbing shouldn't have rifle or shotgun as their first activity any day
            if activity.name in ["Troop Rifle", "Troop Shotgun"] and slot.slot_number == 1:
                if "Fond Du Lac" in troop.name or "Hibbing" in troop.name:
                    return False


        # Fire Tower / History Center slot preferences check (applies to both camps mostly)
        if activity.name == "History Center":
             if not relax_constraints and slot.slot_number != 3:
                # Allow if adjacent to non-staffed (soft check)
                pass 

        # 3-hour activities - limit days to start of week (Mon/Tue) unless commissioner assigned
        if activity.name in self.THREE_HOUR_ACTIVITIES:
            # If commissioner assigned this activity, allow on their day
            commissioner = self.troop_commissioner.get(troop.name, "")
            # ... (logic continues in original code, likely spread across calls or implicitly handled by order)
            # Actually, _can_schedule doesn't check 3-hour day pref, _try_schedule_activity does.
            # But we should enforce hard constraint here if strictly needed.
            # For now, rely on _try_schedule for placement.
            pass

        # Multi-slot activities
        if activity.slots > 1 and activity.name != "Sailing":
            slot_index = self.time_slots.index(slot)
            slots_needed = int(activity.slots + 0.5)
            if not self._check_consecutive_slots(troop, activity, slot_index, slots_needed):
                return False

        # BEACH SLOT RULE: Beach activities must be in slot 1 or 3 (except Thursday allows slot 2)
        # This is a HARD constraint per .cursorrules - ALWAYS ENFORCED (even with relax_constraints)
        # Exception: Sailing is allowed in Slot 2 (due to 1.5 slot duration) - handled separately
        beach_slot_activities = set(self.BEACH_SLOT_ACTIVITIES)
        if activity.name in beach_slot_activities:
            # Special handling for 2-slot beach activities (already checked above, but ensure consistency)
            is_2slot_beach = activity.slots >= 2 and activity.name in set(self.CANOE_ACTIVITIES)
            if not is_2slot_beach:
                # Slot 2 only allowed on Thursday, or Top 5 relaxation (Spine Exception 3)
                if slot.slot_number == 2 and day != Day.THURSDAY:
                    pref_rank = troop.get_priority(activity.name) if hasattr(troop, 'get_priority') else None
                    is_top5 = pref_rank is not None and pref_rank < 5
                    if is_top5:
                        # Allow ANY beach activity in Slot 2 if it's Top 5
                        # We accept the penalty to ensure preference satisfaction
                        pass
                    else:
                        return False  # Not Top 5 - enforce rule

        # Beach activity soft constraint (try to avoid 2+ on same day)
        if not relax_constraints and activity.name in self.BEACH_ACTIVITIES:
            if self._has_beach_activity_conflict(troop, activity, slot.day):
                return False  # Soft constraint: avoid if possible

        # Same-day conflict check (e.g., Trading Post + Campsite Free Time)
        # Spine: AT/WP/GM same-day prohibited - always enforced
        if self._has_same_day_conflict(troop, activity, slot.day, relax_constraints=False):
            return False

        # DELTA CONFLICTS: Spine - "can be same day but not back to back" (adjacent slots only)
        if activity.name == 'Delta':
            day_entries = [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == slot.day]
            for e in day_entries:
                if e.activity.name in self.TOWER_ODS_ACTIVITIES:
                    if abs(e.time_slot.slot_number - slot.slot_number) <= 1:
                        return False  # Adjacent slots - violation
        elif activity.name in self.TOWER_ODS_ACTIVITIES:
            day_entries = [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == slot.day]
            for e in day_entries:
                if e.activity.name == 'Delta':
                    if abs(e.time_slot.slot_number - slot.slot_number) <= 1:
                        return False  # Adjacent slots - violation

        # RIFLE + SHOTGUN SAME DAY: Cannot have both on same day
        # This is a SOFT constraint per .cursorrules - allow if relax_constraints is True
        if not relax_constraints:
            if activity.name == "Troop Rifle":
                if self._troop_has_activity_on_day(troop, "Troop Shotgun", slot.day):
                    return False
            elif activity.name == "Troop Shotgun":
                if self._troop_has_activity_on_day(troop, "Troop Rifle", slot.day):
                    return False

        # ACCURACY LIMIT: Max 1 accuracy activity per day (Rifle, Shotgun, or Archery)
        # This is a SOFT constraint per .cursorrules - allow if relax_constraints is True
        if not relax_constraints:
            if activity.name in self.ACCURACY_ACTIVITIES:
                day_entries = [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == slot.day]
                for e in day_entries:
                    if e.activity.name in self.ACCURACY_ACTIVITIES and e.activity.name != activity.name:
                        return False  # Already has another accuracy activity today

        # SAME PLACE SAME DAY: A troop should never do two activities from the same exclusive area on the same day
        # This is a HARD constraint per .cursorrules - ALWAYS ENFORCED (even with relax_constraints)
        # EXCEPTION: Rifle Range (Rifle + Shotgun) is a SOFT constraint, so allow if relax_constraints is True
        day_entries = [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == slot.day]
        for area_name, area_activities in EXCLUSIVE_AREAS.items():
            if activity.name in area_activities:
                # Exception for Rifle Range if relaxed
                if area_name == "Rifle Range":
                     if relax_constraints:
                         continue

                # Check if troop already has another activity from this same area today
                for e in day_entries:
                    if e.activity.name in area_activities and e.activity.name != activity.name:
                        return False  # Violation: two activities from same exclusive area on same day

        # Campsite Free Time: Smart slot selection based on campsite location
        # Far south campsites should prefer slot 1 or 3 to avoid being sandwiched between far activities
        if activity.name == "Campsite Free Time" and slot.slot_number == 2:
            base_name = troop.name.replace("-A", "").replace("-B", "")
            if base_name in self.CAMPSITE_ORDER:
                campsite_idx = self.CAMPSITE_ORDER.index(base_name)
                # Far south: last 6 campsites (Joseph, Tamanend, Pontiac, Skenandoa, Sequoyah, Roman Nose)
                is_far_south = campsite_idx >= 8

                if is_far_south:
                    # Get what's in slot 1 and slot 3
                    day_slots = [s for s in self.time_slots if s.day == slot.day]
                    slot1 = next((s for s in day_slots if s.slot_number == 1), None)
                    slot3 = next((s for s in day_slots if s.slot_number == 3), None)

                    # Northern activities (far from south campsites)
                    FAR_ACTIVITIES = ["Delta", "Aqua Trampoline", "Water Polo", "Greased Watermelon",
                                     "Troop Swim", "Troop Canoe", "Canoe Snorkel", "Nature Canoe",
                                     "Float for Floats", "Sailing", "Sauna"]

                    slot1_far = slot3_far = False

                    if slot1:
                        for entry in self.schedule.entries:
                            if entry.troop == troop and entry.time_slot == slot1 and entry.activity.name in FAR_ACTIVITIES:
                                slot1_far = True
                                break

                    if slot3:
                        for entry in self.schedule.entries:
                            if entry.troop == troop and entry.time_slot == slot3 and entry.activity.name in FAR_ACTIVITIES:
                                slot3_far = True
                                break

                    # Avoid: Far activity -> Campsite -> Far activity
                    if slot1_far and slot3_far:
                        return False

        # NEW: Wet → Tower/ODS blocking (cannot schedule Tower/ODS after wet activity)
        # Also: Cannot schedule Tower/ODS right before a wet activity
        # This is a HARD constraint per .cursorrules - ALWAYS ENFORCED (even with relax_constraints)
        if activity.name in self.TOWER_ODS_ACTIVITIES:
            if self._has_wet_before_slot(troop, slot):
                return False

            # Check after the LAST slot of this activity
            # (e.g. if Tower is Slots 1-2, check Slot 3)
            end_slot_num = slot.slot_number + slots_needed - 1
            max_slot = 2 if day == Day.THURSDAY else 3
            if end_slot_num < max_slot:
                end_slot = next((s for s in self.time_slots if s.day == slot.day and s.slot_number == end_slot_num), None)
                if end_slot and self._has_wet_after_slot(troop, end_slot):
                    return False

        # NEW: Tower/ODS → Wet blocking (cannot schedule wet activity right after Tower/ODS)
        # This is a HARD constraint per .cursorrules - ALWAYS ENFORCED (even with relax_constraints)
        if activity.name in self.WET_ACTIVITIES:
            if self._has_tower_ods_before_slot(troop, slot):
                return False
            # Also prevent scheduling wet BEFORE Tower/ODS on same day
            if self._has_tower_ods_after_slot(troop, slot):
                return False

        # NEW: Soft same-day conflicts (Fishing with Trading Post/Campsite Time)
        if not relax_constraints and self._has_soft_same_day_conflict(troop, activity, slot.day):
            return False

        # NEW: Major wet beach same-day restriction (avoid 2+ of Polo/Aqua/Watermelon per day)
        if not relax_constraints and activity.name in self.BEACH_ACTIVITIES:
            if self._has_major_wet_beach_conflict(troop, activity, slot.day):
                return False

        # NEW: Wet beach 1-2-3 slot pattern (no wet in slot 3 if slot 1 was wet and slot 2 was not wet)
        # This is a HARD constraint per .cursorrules - ALWAYS ENFORCED (even with relax_constraints)
        if activity.name in self.WET_ACTIVITIES:
            if self._violates_wet_slot_pattern(troop, activity, slot):
                return False

        # NEW CHECK: If scheduling NON-WET in Slot 2, check if it BREAKS the pattern (Wet-X-Wet)
        # If Slot 1 is Wet and Slot 3 is Wet, Slot 2 MUST be Wet (or at least cannot be Dry if rules require valid pattern)
        # This is a HARD constraint per .cursorrules - ALWAYS ENFORCED (even with relax_constraints)
        if slot.slot_number == 2 and activity.name not in self.WET_ACTIVITIES:
            # Check Slot 1
            slot1 = next((s for s in self.time_slots if s.day == slot.day and s.slot_number == 1), None)
            slot3 = next((s for s in self.time_slots if s.day == slot.day and s.slot_number == 3), None)

            if slot1 and slot3:
                s1_wet = False
                s3_wet = False

                # Check existing schedule
                for entry in self.schedule.entries:
                    if entry.troop == troop:
                        if entry.time_slot == slot1 and entry.activity.name in self.WET_ACTIVITIES:
                            s1_wet = True
                        if entry.time_slot == slot3 and entry.activity.name in self.WET_ACTIVITIES:
                            s3_wet = True

                if s1_wet and s3_wet:
                    return False  # Cannot sandwich Dry between Wet-Wet

        # Sailing special constraints
        if activity.name == "Sailing":
            if not self._can_schedule_sailing(troop, slot, day if slot.day == day else slot.day):
                return False

        # Canoe capacity check - max 26 people (13 canoes) per slot
        if not relax_constraints and activity.name in self.CANOE_ACTIVITIES:
            current_canoe_people = self._count_people_in_canoe_activities(slot)
            if current_canoe_people + troop.scouts > self.MAX_CANOE_CAPACITY:
                return False  # Would exceed canoe capacity

        # Float for Floats capacity - only 1 troop at a time unless combined <10 scouts
        if activity.name == 'Float for Floats':
            existing_floats = [e for e in self.schedule.entries 
                              if e.time_slot == slot and e.activity.name == 'Float for Floats']
            if existing_floats:
                # Already has one troop - only allow if both troops combined < 10 scouts
                existing_scouts = sum(e.troop.scouts for e in existing_floats)
                if existing_scouts + troop.scouts >= 10:
                    return False  # Would exceed Float for Floats capacity

        # Canoe Snorkel capacity - only 1 troop at a time unless combined <10 scouts
        if activity.name == 'Canoe Snorkel':
            existing_snorkel = [e for e in self.schedule.entries 
                               if e.time_slot == slot and e.activity.name == 'Canoe Snorkel']
            if existing_snorkel:
                # Already has one troop - only allow if both troops combined < 10 scouts
                existing_scouts = sum(e.troop.scouts for e in existing_snorkel)
                if existing_scouts + troop.scouts >= 10:
                    return False  # Would exceed Canoe Snorkel capacity

        # Aqua Trampoline double-booking - prefer double-booking when troop has <16 scouts
        # This is a soft preference, not a hard constraint - handled in scheduling priority
        # (The actual double-booking logic is in _try_schedule_activity slot ordering)

        # STAFF LIMIT CHECK REMOVED - favoring clustering over staff limits
        # The 15-staff limit is a soft target, not a hard constraint
        # Good clustering (archery, tower, etc.) is more important than staying under 15
        # Staff requirements view will show when slots are crowded, but won't block scheduling

        # Check day-level constraints
        can = self._can_schedule_on_day(troop, activity, day if slot.day == day else slot.day, slot.slot_number, relax_constraints)
        if not can and relax_constraints and troop.name == "Tecumseh":
             print(f"  DEBUG: {troop.name} cannot schedule {activity.name} on {day} even with relax_constraints")

        return can


    def _get_all_staffed_activities(self):
        """Get list of all activities that require staff."""
        return (self.BEACH_STAFFED_ACTIVITIES + 
                ['Sailing', 'Troop Rifle', 'Troop Shotgun', 'Archery',
                 'Climbing Tower', 'Orienteering', 'GPS & Geocaching', 'Knots and Lashings',
                'Ultimate Survivor', 'Back of the Moon', 'Loon Lore', 'Dr. DNA', 'Nature Canoe',
                 'Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist",
                 'Reflection', 'Delta', 'Super Troop'])


    def _get_activity_staff_count(self, activity_name: str) -> int:
        """
        Get the staff count for an activity - matches GUI's activity_to_staff mapping.
        """
        # Match gui_web.py activity_to_staff exactly
        ACTIVITY_TO_STAFF_COUNT = {
            # Beach Staff (2 staff each)
            'Aqua Trampoline': 2, 'Greased Watermelon': 2, 'Underwater Obstacle Course': 2,
            'Troop Swim': 2, 'Water Polo': 2,
            # Boats Staff (2-3 staff)
            'Troop Canoe': 2, 'Troop Kayak': 2, 'Canoe Snorkel': 3, 
            'Float for Floats': 3, 'Nature Canoe': 2,
            # Ass. Aquatics (1)
            'Sailing': 1,
            # Shooting Sports Director (1)
            'Troop Rifle': 1, 'Troop Shotgun': 1,
            # Archery Director (1)
            'Archery': 1,
            # Tower Director (2)
            'Climbing Tower': 2,
            # Outdoor Skills Director (1)
            'Orienteering': 1, 'GPS & Geocaching': 1, 'Knots and Lashings': 1,
            'Ultimate Survivor': 1, 'Back of the Moon': 1, "What's Cooking": 1, 'Chopped!': 1,
            # Nature Director (1)
            'Loon Lore': 1, 'Dr. DNA': 1,
            # Handicrafts Director (1)
            'Tie Dye': 1, 'Hemp Craft': 1, 'Woggle Neckerchief Slide': 1, "Monkey's Fist": 1,
            # Commissioner Activities (1)
            'Reflection': 1, 'Delta': 1, 'Super Troop': 1,
        }
        return ACTIVITY_TO_STAFF_COUNT.get(activity_name, 0)


    def _count_all_staff_in_slot(self, slot: TimeSlot) -> int:
        """
        Count total staff currently needed in this slot - matches GUI calculation.
        """
        count = 0
        for entry in self.schedule.entries:
            if entry.time_slot == slot:
                count += self._get_activity_staff_count(entry.activity.name)
        return count


    def _count_people_in_canoe_activities(self, slot: TimeSlot) -> int:
        """Count total people (scouts) in canoe activities in this slot."""
        count = 0
        for entry in self.schedule.entries:
            if entry.time_slot == slot and entry.activity.name in self.CANOE_ACTIVITIES:
                count += entry.troop.scouts
        return count


    def _check_activity_capacity(self, slot: TimeSlot, activity: Activity, troop: Troop, allow_top5_at_overload: bool = False) -> bool:
        """
        Check if activity can accept this troop in this slot based on capacity rules.

        Returns True if the activity has room for this troop, False otherwise.

        Capacity rules:
        - Aqua Trampoline: 2 troops if both ≤16 scouts
        - Sailing: 1 troop per slot (exclusive per-slot). Up to 2 troops per day allowed since 2 Sailing sessions (1.5 + 1.5 = 3 slots) fit in a 3-slot day.
        - Water Polo: up to 2 troops
        - Canoe activities: total people ≤26 (13 canoes)
        - Gaga Ball / 9 Square: 1 troop (exclusive)
        - Other exclusive activities: 1 troop

        When allow_top5_at_overload is True (Top 5 guarantee phase), allow 3rd troop in AT slot to place Top 5.
        """
        existing = [e for e in self.schedule.entries 
                   if e.time_slot == slot and e.activity.name == activity.name]

        if activity.name == 'Aqua Trampoline':
            # Allow 2 troops if both ≤16 scouts+adults (Spine: scouts+adults)
            # Top 5 placement: allow 3rd troop when allow_top5_at_overload
            AT_MAX = 16
            troop_size = troop.scouts + troop.adults
            if len(existing) >= 2 and not allow_top5_at_overload:
                return False
            if len(existing) >= 3:
                return False  # Never more than 3 (2 normal + 1 Top 5 overload)
            if len(existing) == 1:
                existing_size = existing[0].troop.scouts + existing[0].troop.adults
                return existing_size <= AT_MAX and troop_size <= AT_MAX
            if len(existing) == 2 and allow_top5_at_overload:
                return True  # Allow 3rd troop for Top 5
            return True

        elif activity.name == 'Sailing':
            # Sailing special capacity logic:
            # Allow up to 2 starts per 3-slot day (start at slot 1 and slot 2).
            # We intentionally allow the serialized overlap at slot 2 for staggered
            # 1.5-slot sessions (1-2 and 2-3).
            day = slot.day
            starts_today = set()
            for entry in self.schedule.entries:
                if entry.activity.name != "Sailing" or entry.time_slot.day != day:
                    continue
                start_num = entry.time_slot.slot_number
                prev_num = start_num - 1
                has_prev_same = any(
                    e.troop == entry.troop
                    and e.activity.name == "Sailing"
                    and e.time_slot.day == day
                    and e.time_slot.slot_number == prev_num
                    for e in self.schedule.entries
                )
                if not has_prev_same:
                    starts_today.add(start_num)

            # Cannot duplicate the same start slot.
            if slot.slot_number in starts_today:
                return False

            if day == Day.THURSDAY:
                return slot.slot_number == 1 and len(starts_today) == 0

            return len(starts_today) < 2

        elif activity.name == 'Water Polo':
            # Allow 2 troops if both ≤16 scouts+adults (Same as Aqua Trampoline)
            WP_MAX = 16
            if len(existing) >= 2:
                return False
            if len(existing) == 1:
                es = existing[0].troop.scouts + existing[0].troop.adults
                ts = troop.scouts + troop.adults
                return es <= WP_MAX and ts <= WP_MAX
            return True

        elif activity.name == 'Climbing Tower':
            # Exclusive - only 1 troop at a time
            return len(existing) == 0

        elif activity.name in self.CANOE_ACTIVITIES:
            # Check total capacity (max 26 people = 13 canoes)
            total_people = sum(e.troop.scouts + e.troop.adults for e in existing)
            total_people += troop.scouts + troop.adults
            return total_people <= self.MAX_CANOE_CAPACITY

        elif activity.name in ['Gaga Ball', '9 Square']:
            # Exclusive - only 1 troop at a time
            return len(existing) == 0

        else:
            # Default for non-concurrent activities: allow (checked elsewhere)
            return True


    def _has_beach_activity_conflict(self, troop: Troop, activity: Activity, day: Day) -> bool:
        """Check if scheduling would violate Spine prohibited pair: AT/WP/GM same day.

        Spine: "Any pair of: Aqua Trampoline, Water Polo, Greased Watermelon" - prohibited.
        Troop Swim, Canoe Snorkel, Float for Floats, etc. are NOT in this pair - they may
        share a day with AT. We were incorrectly blocking AT when troop had Troop Swim."""
        if activity.name not in self.SPINE_BEACH_PROHIBITED_PAIR:
            return False

        day_entries = [e for e in self.schedule.entries 
                       if e.troop == troop and e.time_slot.day == day]

        for entry in day_entries:
            if entry.activity.name in self.SPINE_BEACH_PROHIBITED_PAIR and entry.activity.name != activity.name:
                return True  # Spine prohibited pair: AT+WP, AT+GM, or WP+GM same day

        return False


    def _has_same_day_conflict(self, troop: Troop, activity: Activity, day: Day, relax_constraints: bool = False) -> bool:
        """Check if scheduling this activity would violate same-day conflict rules."""
        # Get activities this troop has on this day
        day_entries = [e for e in self.schedule.entries 
                       if e.troop == troop and e.time_slot.day == day]
        top5 = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)

        for conflict_pair in self.SAME_DAY_CONFLICTS:
            if activity.name in conflict_pair:
                # Find the other activity in the conflict pair
                other_activity = conflict_pair[0] if activity.name == conflict_pair[1] else conflict_pair[1]
                # Check if troop already has the conflicting activity today
                for entry in day_entries:
                    if entry.activity.name == other_activity:
                        return True

        return False


    def _has_wet_before_slot(self, troop: Troop, slot: TimeSlot) -> bool:
        """Check if troop has ANY wet activity in ANY slot before this one on the same day."""
        if slot.slot_number == 1:
            return False  # No previous slot on same day

        # Check all previous slots on the same day
        for prev_slot_num in range(1, slot.slot_number):
            prev_slot = next((s for s in self.time_slots 
                             if s.day == slot.day and s.slot_number == prev_slot_num), None)

            if not prev_slot:
                continue

            # Check if troop has a wet activity in that slot
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.time_slot == prev_slot:
                    if entry.activity.name in self.WET_ACTIVITIES:
                        return True  # Found a wet activity earlier in the day

        return False


    def _has_tower_ods_before_slot(self, troop: Troop, slot: TimeSlot) -> bool:
        """Check if troop has Tower/ODS in the immediately preceding slot on the same day."""
        if slot.slot_number == 1:
            return False  # No previous slot on same day

        # Only check the immediately preceding slot (not all previous slots)
        prev_slot_num = slot.slot_number - 1
        prev_slot = next((s for s in self.time_slots 
                         if s.day == slot.day and s.slot_number == prev_slot_num), None)

        if not prev_slot:
            return False

        # Check if troop has a Tower/ODS activity in that slot
        for entry in self.schedule.entries:
            if entry.troop == troop and entry.time_slot == prev_slot:
                if entry.activity.name in self.TOWER_ODS_ACTIVITIES:
                    return True  # Found Tower/ODS in immediately preceding slot

        return False


    def _has_tower_ods_after_slot(self, troop: Troop, slot: TimeSlot) -> bool:
        """Check if troop has Tower/ODS in ANY later slot on the same day."""
        if slot.slot_number >= 3:
            return False  # No slots after slot 3

        # Check all later slots on the same day
        for next_slot_num in range(slot.slot_number + 1, 4):  # slots 2, 3 or just 3
            next_slot = next((s for s in self.time_slots 
                             if s.day == slot.day and s.slot_number == next_slot_num), None)

            if not next_slot:
                continue

            # Check if troop has a Tower/ODS activity in that slot
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.time_slot == next_slot:
                    if entry.activity.name in self.TOWER_ODS_ACTIVITIES:
                        return True  # Found Tower/ODS in a later slot

        return False


    def _has_wet_after_slot(self, troop: Troop, slot: TimeSlot) -> bool:
        """Check if troop has a wet activity in the immediately following slot on the same day."""
        if slot.slot_number >= 3:
            return False  # No next slot on same day

        # Only check the immediately following slot
        next_slot_num = slot.slot_number + 1
        next_slot = next((s for s in self.time_slots 
                         if s.day == slot.day and s.slot_number == next_slot_num), None)

        if not next_slot:
            return False

        # Check if troop has a wet activity in that slot
        for entry in self.schedule.entries:
            if entry.troop == troop and entry.time_slot == next_slot:
                if entry.activity.name in self.WET_ACTIVITIES:
                    return True  # Found wet activity in immediately following slot

        return False


    def _check_wet_dry_violation_for_troop_on_day(self, troop: Troop, day: Day) -> bool:
        """
        Check if troop has any wet/dry pattern violations on the given day.

        Violations checked:
        1. Wet-Dry-Wet pattern (slot 1 wet, slot 2 dry, slot 3 wet)
        2. Wet activity immediately after Tower/ODS
        3. Tower/ODS activity immediately after wet

        FIX 2026-01-30: Added for post-swap validation to catch violations
        that may be created by swaps.

        Returns True if any violation exists, False if day is clean.
        """
        from ...models import Day

        # Get all entries for this troop on this day
        day_entries = [e for e in self.schedule.entries 
                      if e.troop == troop and e.time_slot.day == day]

        if len(day_entries) < 2:
            return False  # Need at least 2 activities to have violations

        # Build slot map for this day
        slot_map = {}
        for entry in day_entries:
            slot_map[entry.time_slot.slot_number] = entry.activity.name

        # Check 1: Wet-Dry-Wet pattern (only valid if all 3 slots are filled)
        if 1 in slot_map and 2 in slot_map and 3 in slot_map:
            s1_wet = slot_map[1] in self.WET_ACTIVITIES
            s2_wet = slot_map[2] in self.WET_ACTIVITIES
            s3_wet = slot_map[3] in self.WET_ACTIVITIES

            if s1_wet and not s2_wet and s3_wet:
                return True  # Wet-Dry-Wet violation

        # Check 2 & 3: Wet/Tower adjacency violations
        for slot_num in range(1, 3):  # Check slots 1-2 and 2-3 pairs
            if slot_num not in slot_map or (slot_num + 1) not in slot_map:
                continue

            curr_act = slot_map[slot_num]
            next_act = slot_map[slot_num + 1]

            # Wet -> Tower/ODS violation
            if curr_act in self.WET_ACTIVITIES and next_act in self.TOWER_ODS_ACTIVITIES:
                return True

            # Tower/ODS -> Wet violation
            if curr_act in self.TOWER_ODS_ACTIVITIES and next_act in self.WET_ACTIVITIES:
                return True

        return False  # No violations


    def _has_soft_same_day_conflict(self, troop: Troop, activity: Activity, day: Day) -> bool:
        """Check soft same-day conflicts (try to avoid but not hard block)."""
        day_entries = [e for e in self.schedule.entries 
                       if e.troop == troop and e.time_slot.day == day]

        for conflict_pair in self.SOFT_SAME_DAY_CONFLICTS:
            if activity.name in conflict_pair:
                other_activity = conflict_pair[0] if activity.name == conflict_pair[1] else conflict_pair[1]
                for entry in day_entries:
                    if entry.activity.name == other_activity:
                        return True

        return False


    def _has_major_wet_beach_conflict(self, troop: Troop, activity: Activity, day: Day) -> bool:
        """Check Spine prohibited pair: AT/WP/GM - no two on same day.

        Spine: "Any pair of: Aqua Trampoline, Water Polo, Greased Watermelon".
        Use same narrow set as _has_beach_activity_conflict - not full BEACH_ACTIVITIES.
        """
        if activity.name not in self.SPINE_BEACH_PROHIBITED_PAIR:
            return False

        day_entries = [e for e in self.schedule.entries 
                       if e.troop == troop and e.time_slot.day == day]

        existing_major_wet = [e for e in day_entries 
                              if e.activity.name in self.SPINE_BEACH_PROHIBITED_PAIR]

        if not existing_major_wet:
            return False  # No conflict - this would be the first

        # Already have one major wet beach activity today
        # Only allow if BOTH this activity AND the existing one are low priority (> top 5)
        this_priority = troop.get_priority(activity.name)
        if this_priority is None:
            this_priority = 100  # Not in preferences = low priority

        for entry in existing_major_wet:
            existing_priority = troop.get_priority(entry.activity.name)
            if existing_priority is None:
                existing_priority = 100

            # If either activity is high priority (in top 5), block the conflict
            if this_priority < 5 or existing_priority < 5:
                return True  # Conflict - one is high priority

        # Both are low priority - still try to avoid but don't hard block
        return True  # Still conflict but can be overridden with relax_constraints


    def _violates_wet_slot_pattern(self, troop: Troop, activity: Activity, slot: TimeSlot) -> bool:
        """Check if scheduling this wet activity would violate the 1-2-3 slot pattern.

        Rule: If slot 1 is wet AND slot 2 is NOT wet, then slot 3 cannot be wet.
        (No wet-dry-wet pattern allowed)
        """
        if activity.name not in self.WET_ACTIVITIES:
            return False  # Only applies to wet activities

        # Get all slots for this day
        slot1 = next((s for s in self.time_slots if s.day == slot.day and s.slot_number == 1), None)
        slot2 = next((s for s in self.time_slots if s.day == slot.day and s.slot_number == 2), None)
        slot3 = next((s for s in self.time_slots if s.day == slot.day and s.slot_number == 3), None)

        if not slot1 or not slot2 or not slot3:
            return False

        # Helper to check if a slot has a wet activity (or will have)
        def is_slot_wet(s):
            if s == slot: return True # The one we are scheduling
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.time_slot == s:
                    if entry.activity.name in self.WET_ACTIVITIES:
                        return True
            return False

        # Helper to check if a slot is strictly DRY (occupied by non-wet)
        def is_slot_dry(s):
            if s == slot: return False # We are scheduling Wet
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.time_slot == s:
                    if entry.activity.name not in self.WET_ACTIVITIES:
                        return True
            return False

        s1_wet = is_slot_wet(slot1)
        # s2_wet = is_slot_wet(slot2) # Not sufficient, we need to know if it's explicitly DRY
        s2_dry = is_slot_dry(slot2)
        s3_wet = is_slot_wet(slot3)

        # If we have Wet at 1, Dry at 2, Wet at 3 => VIOLATION
        if s1_wet and s2_dry and s3_wet:
            return True

        return False


    def _can_schedule_sailing(self, troop: Troop, slot: TimeSlot, day: Day) -> bool:
        """Special check for Sailing.

        Sailing IS exclusive - only 1 troop per slot (duration 1.5 slots).
        Since Sailing is 1.5 slots, 2 Sailing sessions (1.5 + 1.5 = 3 slots) can fit in a 3-slot day.
        This allows up to 2 troops per day with Sailing (one starting at slot 1, one starting at slot 2).
        Exclusivity is enforced per START slot, not by blocking the shared middle slot.

        Thursday Sailing priority for largest troop is handled by 
        _schedule_thursday_sailing_largest_troop phase which runs first.
        All other troops can get Sailing on any day (except Thursday if already taken).
        """
        # Sailing can only be scheduled in Slot 1 or Slot 2 (extends into next slot)
        if slot.slot_number not in [1, 2]:
            return False

        # Get all slots for this day
        day_slots = [s for s in self.time_slots if s.day == day]

        # Track starts for this day. We allow one start at slot 1 and one at slot 2
        # on 3-slot days (staggered sessions). Duplicate starts are not allowed.
        sailing_starts_today = set()
        for entry in self.schedule.entries:
            if not hasattr(entry, 'time_slot') or not hasattr(entry, 'activity'):
                continue
            if entry.activity.name == "Sailing" and entry.time_slot.day == day:
                start_num = entry.time_slot.slot_number
                prev_num = start_num - 1
                has_prev_same = any(
                    e.troop == entry.troop
                    and e.activity.name == "Sailing"
                    and e.time_slot.day == day
                    and e.time_slot.slot_number == prev_num
                    for e in self.schedule.entries
                )
                if not has_prev_same:
                    sailing_starts_today.add(start_num)

        if slot.slot_number in sailing_starts_today:
            return False

        # Check if we'd exceed 2 per day limit (only applies to 3-slot days)
        sailing_sessions_today = len(sailing_starts_today)
        if day != Day.THURSDAY and sailing_sessions_today >= 2:
            return False  # Already have 2 Sailing sessions on this day (max 2 per day)

        # Friday is reflection-sensitive, but not globally blocked.
        # Sailing is allowed if slot-level checks still preserve Reflection and constraints.

        # Thursday only has 2 slots total, so only slot 1 works (extends into slot 2)
        if day == Day.THURSDAY:
            # Thursday Sailing only conflicts with an actually scheduled Thursday Delta,
            # not a mere Delta preference.
            has_thursday_delta = any(
                e.troop == troop and e.activity.name == "Delta" and e.time_slot.day == Day.THURSDAY
                for e in self.schedule.entries
            )
            if has_thursday_delta:
                return False
            if slot.slot_number != 1:
                return False

        # CRITICAL: Check if troop has Reflection in the extended slot
        # Sailing in Slot 1 extends to Slot 2, Sailing in Slot 2 extends to Slot 3
        extended_slot_num = slot.slot_number + 1
        extended_slot = next((s for s in self.time_slots if s.day == day and s.slot_number == extended_slot_num), None)

        if extended_slot:
            # Check if troop has Reflection in the extended slot
            for entry in self.schedule.entries:
                if entry.time_slot == extended_slot and entry.troop == troop and entry.activity.name == "Reflection":
                    return False  # Don't overwrite Reflection!

            # Also check if the slot is free for non-concurrent activities
            if not self.schedule.is_troop_free(extended_slot, troop):
                # Check if what's there is NOT a concurrent activity
                for entry in self.schedule.entries:
                    if entry.time_slot == extended_slot and entry.troop == troop:
                        if entry.activity.name not in self.CONCURRENT_ACTIVITIES:
                            return False

        return True


    def _is_area_available(self, slot: TimeSlot, activity: Activity) -> bool:
        """Check if the activity's area is available (no other activity in exclusive area)."""
        # ENHANCED: Stricter exclusive area checking to prevent violations
        # Find which exclusive area this activity belongs to
        activity_area = None
        for area_name, area_activities in EXCLUSIVE_AREAS.items():
            if activity.name in area_activities:
                activity_area = area_name
                break

        if not activity_area:
            return True  # Not in an exclusive area

        # ENHANCED: Check if any other activity in this area is scheduled for this slot
        # This is a HARD constraint - no exceptions
        for entry in self.schedule.get_slot_activities(slot):
            if entry.activity.name in EXCLUSIVE_AREAS[activity_area]:
                return False  # Area already in use - violation prevented

        return True


    def _can_schedule_on_day(self, troop: Troop, activity: Activity, day: Day, slot_num: int = 1, relax_constraints: bool = False) -> bool:
        """Check day-level constraints."""
        # Check exclusivity for activities that are once per week
        if activity.name in ["Delta", "Super Troop"]:
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.activity.name == activity.name:
                    return False

        # Ideally, don't schedule two activities from same area on same day
        # e.g. "Nature Center" -> ["Dr. DNA", "Loon Lore"]
        # Skip this check if constraints are relaxed (for filling)
        if not relax_constraints:
            if self._has_same_area_activity_today(troop, activity, day):
                return False

        # Accuracy limit: max 1 per day
        # Soft constraint: Allow if relaxed
        if not relax_constraints:
            if activity.name in self.ACCURACY_ACTIVITIES:
                if self._has_accuracy_today(troop, day):
                    return False

        # Per Spine: Allow multiple 3-hour activities per troop if sufficient days available
        # Do NOT enforce a "max 1 per troop" limit
        if activity.name in self.THREE_HOUR_ACTIVITIES:
            # 3-hour activities NOT on Friday
            if day == Day.FRIDAY:
                return False

        # Campsite Free Time: NOT on Monday or Friday
        if activity.name == "Campsite Free Time" and day in [Day.MONDAY, Day.FRIDAY]:
            return False

        # Trading Post: NOT on Monday
        if activity.name == "Trading Post" and day == Day.MONDAY:
            return False

        # Gaga Ball and 9 Square: NOT on same day
        if activity.name == "Gaga Ball":
            if self._troop_has_activity_on_day(troop, "9 Square", day):
                return False
        if activity.name == "9 Square":
            if self._troop_has_activity_on_day(troop, "Gaga Ball", day):
                return False

        # Rifle/Shotgun should NOT be immediately before or after Delta
        if activity.name in ["Troop Rifle", "Troop Shotgun"]:
            if self._is_adjacent_to_delta(troop, day, slot_num):
                return False

        return True


    def _has_same_area_activity_today(self, troop: Troop, activity: Activity, day: Day) -> bool:
        """Check if troop already has an activity from the same exclusive area today.

        HARD CONSTRAINT: A troop should never do two activities that take place in the same place on the same day.
        This checks ALL exclusive areas from EXCLUSIVE_AREAS, not just a subset.
        """
        # Use EXCLUSIVE_AREAS from .models to check ALL areas
        # Find which area this activity belongs to
        activity_area = None
        for area_name, area_activities in EXCLUSIVE_AREAS.items():
            if activity.name in area_activities:
                activity_area = area_name
                break

        if not activity_area:
            return False  # Not in an exclusive area

        # Check if troop already has another activity from this same area today
        day_slots = [s for s in self.time_slots if s.day == day]
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.time_slot in day_slots:
                # Check if this entry is from the same exclusive area
                if entry.activity.name in EXCLUSIVE_AREAS[activity_area] and entry.activity.name != activity.name:
                    return True
        return False


    def _is_adjacent_to_delta(self, troop: Troop, day: Day, slot_num: int) -> bool:
        """Check if this slot is adjacent to Delta on the same day."""
        # Get Delta slot for this troop on this day
        day_slots = [s for s in self.time_slots if s.day == day]
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.time_slot in day_slots and entry.activity.name == "Delta":
                delta_slot = entry.time_slot.slot_number
                # Check if proposed slot is adjacent
                if abs(slot_num - delta_slot) == 1:
                    return True
        return False


    def _troop_has_activity_on_day(self, troop: Troop, activity_name: str, day: Day) -> bool:
        """Check if troop has a specific activity on a specific day."""
        day_slots = [s for s in self.time_slots if s.day == day]
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.time_slot in day_slots and entry.activity.name == activity_name:
                return True
        return False


    def _has_three_hour_activity(self, troop: Troop) -> bool:
        """Check if troop already has one of the 3-hour activities."""
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.activity.name in self.THREE_HOUR_ACTIVITIES:
                return True
        return False
