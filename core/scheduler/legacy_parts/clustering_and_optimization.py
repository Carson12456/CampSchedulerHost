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

class LegacyPart06Mixin:
    """Scheduler legacy methods part 06."""

    def _cleanup_exclusive_activities(self):
        """
        Cleanup phase: Remove conflicts in exclusive areas.

        Two types of conflicts are handled:
        1. Multiple troops with the SAME exclusive activity in a slot
        2. Multiple troops with DIFFERENT activities from the same exclusive AREA in a slot
           (e.g., one troop has "Knots and Lashings" and another has "Orienteering" - both Outdoor Skills)

        If multiple troops conflict, keep the one with the higher preference rank.
        """
        from collections import defaultdict

        # Build a map of activity -> exclusive area
        activity_to_area = {}
        for area, activities in EXCLUSIVE_AREAS.items():
            for activity_name in activities:
                activity_to_area[activity_name] = area

        # Activities that are exclusions from exclusivity cleanup (SKULL-driven).
        concurrent = set(self.CONCURRENT_EXCLUSIVITY_EXCEPTIONS)

        # Group entries by slot and EXCLUSIVE AREA
        slot_area_entries = defaultdict(list)
        for entry in self.schedule.entries:
            if entry.activity.name in concurrent:
                continue  # Skip concurrent activities
            area = activity_to_area.get(entry.activity.name)
            if area:
                key = (entry.time_slot, area)
                slot_area_entries[key].append(entry)

        # Find and fix area conflicts
        removed_count = 0
        for (slot, area), entries in slot_area_entries.items():
            if len(entries) <= 1:
                continue  # No conflicts

            # SPECIAL HANDLING for certain areas
            # Aqua Trampoline: 2 small troops OK
            if area == "Aqua Trampoline":
                small_troops = [e for e in entries if e.troop.scouts <= 16]
                if len(small_troops) == len(entries) and len(entries) <= 2:
                    continue  # All small, max 2 - OK

            # Water Polo: 2 troops OK
            if area == "Water Polo" and len(entries) <= 2:
                continue

            # Sailing is EXCLUSIVE: Only 1 troop per slot (per Spine rule)
            # No special handling needed - will be caught as violation if > 1

            # Multiple troops have activities from this exclusive area in this slot!
            # Sort by preference rank (lower is better) - keep the best one
            entries_with_rank = []
            for e in entries:
                rank = e.troop.get_priority(e.activity.name)
                if rank == 999:
                    rank = 100  # Not in prefs, treat as low priority
                entries_with_rank.append((e, rank))

            # Sort by rank (lower = better), then by troop name for consistency
            entries_with_rank.sort(key=lambda x: (x[1], x[0].troop.name))

            # Keep the first one (best rank), remove the rest
            keep_entry = entries_with_rank[0][0]
            to_remove = [e for e, _ in entries_with_rank[1:]]

            for entry in to_remove:
                if entry in self.schedule.entries:
                    self.schedule.entries.remove(entry)
                    removed_count += 1

                    # FIX: Multi-slot atomicity - remove siblings!
                    effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
                    if effective_slots > 1:
                        siblings = [s for s in self.schedule.entries 
                                   if s.troop == entry.troop 
                                   and s.activity.name == entry.activity.name 
                                   and s.time_slot.day == entry.time_slot.day
                                   and s != entry]
                        for s in siblings:
                            if s in self.schedule.entries:
                                self.schedule.entries.remove(s)

                    # TRACK TOP 5 TO RECOVER LATER
                    rank = entry.troop.get_priority(entry.activity.name)
                    if rank < 5:
                        if not hasattr(self, "_top5_to_recover"):
                            self._top5_to_recover = []
                        # Check if already in recovery list to avoid duplicates
                        if (entry.troop, entry.activity, rank) not in self._top5_to_recover:
                            self._top5_to_recover.append((entry.troop, entry.activity, rank))

                    # Show what happened
                    if entry.activity.name == keep_entry.activity.name:
                        print(f"  [Cleanup] Removed duplicate {entry.activity.name} for {entry.troop.name} at {slot}")
                        print(f"            Kept {keep_entry.troop.name}'s {keep_entry.activity.name}")
                    else:
                        print(f"  [Cleanup] Area conflict in '{area}' at {slot}")
                        print(f"            Removed {entry.troop.name}'s {entry.activity.name}")
                        print(f"            Kept {keep_entry.troop.name}'s {keep_entry.activity.name}")

        if removed_count > 0:
            print(f"  Removed {removed_count} exclusive area conflict entries")
        else:
            print("  No exclusive area conflicts found")


    def _optimize_friday_super_troop(self):
        """
        Swap valuable activities with fill activities to improve clustering across ALL days equally.

        This optimization:
        1. Finds exclusive activities (Super Troop, Tower, Archery, Rifle) that aren't well-clustered
        2. Finds fill activities that could swap with them
        3. Swaps when it improves clustering by moving to a day with more of the same activity

        All days (Mon-Fri) are treated equally - no bias against Friday.
        """
        from ...models import ScheduleEntry

        print("\n--- Activity Clustering Optimization (All Days) ---")

        # Fill activities that can be freely moved
        FILL_ACTIVITIES = self.MOVABLE_FILL_ACTIVITIES

        # Exclusive activities that benefit from clustering
        EXCLUSIVE_ACTIVITIES = (
            {"Super Troop", "Delta"}
            | set(EXCLUSIVE_AREAS.get("Tower", []))
            | set(EXCLUSIVE_AREAS.get("Archery", []))
            | set(EXCLUSIVE_AREAS.get("Rifle Range", []))
        )

        # Never swap these out
        PROTECTED = {"Reflection", "Sailing"}

        swaps_made = 0
        max_iterations = 3

        for iteration in range(max_iterations):
            iteration_swaps = 0

            for troop in self.troops:
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                # Find exclusive activities that might benefit from better clustering
                exclusive_entries = [e for e in troop_entries 
                                    if e.activity.name in EXCLUSIVE_ACTIVITIES]

                if not exclusive_entries:
                    continue

                # Find available fill activities
                fill_entries = [e for e in troop_entries 
                               if e.activity.name in FILL_ACTIVITIES]

                if not fill_entries:
                    continue

                # Check each exclusive activity for clustering improvement
                for exclusive_entry in exclusive_entries:
                    if self._is_pair_protected_delta(exclusive_entry):
                        continue
                    current_slot = exclusive_entry.time_slot
                    activity_name = exclusive_entry.activity.name

                    # Get cluster days for this activity
                    cluster_days = self._get_days_with_activity(activity_name)

                    # Count how many of this activity are on the current day
                    current_day_count = sum(1 for e in self.schedule.entries 
                                          if e.activity.name == activity_name 
                                          and e.time_slot.day == current_slot.day)

                    # If already on a day with 2+ of this activity, it's well-clustered
                    if current_day_count >= 2:
                        continue

                    # Find a better cluster day (one with more of this activity)
                    best_swap = None
                    best_cluster_count = current_day_count

                    for fill_entry in fill_entries[:]:
                        fill_slot = fill_entry.time_slot

                        # Check if entries still exist
                        if exclusive_entry not in self.schedule.entries or fill_entry not in self.schedule.entries:
                            continue

                        # Count how many of this activity are on the fill day
                        target_day_count = sum(1 for e in self.schedule.entries 
                                              if e.activity.name == activity_name 
                                              and e.time_slot.day == fill_slot.day
                                              and e != exclusive_entry)

                        # Only swap if target day has MORE clustering
                        if target_day_count <= best_cluster_count:
                            continue

                        # Temporarily remove both
                        self.schedule.entries.remove(exclusive_entry)
                        self.schedule.entries.remove(fill_entry)

                        # Check if the target slot is available for this exclusive activity
                        # We must use is_activity_available to check ALL constraints (including adjacency)
                        if self.schedule.is_activity_available(fill_slot, exclusive_entry.activity, troop):
                            # This swap improves clustering!
                            # This swap improves clustering!
                            best_swap = (fill_entry, fill_slot, target_day_count)
                            best_cluster_count = target_day_count

                        # Restore entries
                        self.schedule.entries.append(exclusive_entry)
                        self.schedule.entries.append(fill_entry)

                    # Execute the best swap if found
                    if best_swap:
                        fill_entry, fill_slot, target_count = best_swap

                        self.schedule.entries.remove(exclusive_entry)
                        self.schedule.entries.remove(fill_entry)

                        new_exclusive = ScheduleEntry(time_slot=fill_slot, activity= exclusive_entry.activity, troop= troop)
                        new_fill = ScheduleEntry(time_slot=current_slot, activity= fill_entry.activity, troop= troop)

                        self.schedule.entries.append(new_exclusive)
                        self.schedule.entries.append(new_fill)

                        fill_entries.remove(fill_entry)
                        iteration_swaps += 1
                        print(f"  [Cluster] {troop.name}: {activity_name} {current_slot} -> {fill_slot} (cluster: {current_day_count} -> {target_count+1})")

            swaps_made += iteration_swaps
            if iteration_swaps == 0:
                break
            print(f"  Iteration {iteration + 1}: {iteration_swaps} swaps")

        if swaps_made > 0:
            print(f"  Total clustering swaps: {swaps_made}")
        else:
            print("  No clustering improvements found")


    def _preference_improvement_swaps(self):
        """
        Find opportunities to improve preference satisfaction by swapping activities.

        For each troop:
        1. Find scheduled activities with low preference rank
        2. Find unscheduled activities with higher preference rank
        3. If the higher-ranked activity could fit in the lower-ranked activity's slot, swap

        Example: Powhatan has Archery (rank 12) but no Troop Canoe (rank 8).
        If Troop Canoe can fit in Archery's slot, swap them.
        """
        from ...models import ScheduleEntry
        from ...activities import get_activity_by_name

        print("\n--- Preference Improvement Swaps ---")

        # Protected activities that should never be swapped out
        # NOTE: Sailing and Delta removed - they're preferences and can be swapped for better preferences
        PROTECTED = self.NON_DISPLACEABLE_ACTIVITIES

        swaps_made = 0
        max_iterations = 5  # Increased from 3 for more aggressive optimization

        for iteration in range(max_iterations):
            iteration_swaps = 0

            for troop in self.troops:
                # Get all scheduled activity names for this troop
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                scheduled_activities = {e.activity.name for e in troop_entries}

                # Get all preferences for this troop
                for pref_idx, pref_name in enumerate(troop.preferences[:20]):  # Top 20 (max preferences)
                    if pref_name in scheduled_activities:
                        continue  # Already scheduled

                    pref_activity = get_activity_by_name(pref_name)
                    if not pref_activity:
                        continue

                    pref_rank = pref_idx  # 0-indexed

                    # Refresh troop_entries for each preference check
                    troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                    swap_made = False
                    # Find a scheduled activity with LOWER priority that could be swapped
                    for entry in troop_entries[:]:  # Copy the list for safe iteration
                        if entry.activity.name in PROTECTED:
                            continue

                        # SKIP MULTI-SLOT SWAPS: Moving partials breaks them
                        if entry.activity.slots > 1.0:
                            continue

                        # Verify entry is still in schedule
                        if entry not in self.schedule.entries:
                            continue

                        entry_rank = troop.get_priority(entry.activity.name)
                        if entry_rank <= pref_rank:
                            continue  # Entry is higher priority, don't swap

                        # Check if pref_activity can go in this slot
                        slot = entry.time_slot
                        day = slot.day

                        # Temporarily remove the entry
                        self.schedule.entries.remove(entry)

                        # Check if pref_activity can fit
                        can_fit = (
                            self.schedule.is_activity_available(slot, pref_activity, troop) and
                            self._can_schedule(troop, pref_activity, slot, day)
                        )

                        if can_fit:
                            # Make the swap!
                            new_entry = ScheduleEntry(time_slot=slot, activity= pref_activity, troop= troop)
                            self.schedule.entries.append(new_entry)

                            iteration_swaps += 1
                            print(f"  [Pref Swap] {troop.name}: Replaced {entry.activity.name} (rank {entry_rank+1}) with {pref_name} (rank {pref_rank+1}) at {slot}")

                            # Update tracking
                            scheduled_activities.add(pref_name)
                            scheduled_activities.discard(entry.activity.name)
                            swap_made = True
                            break  # Move to next preference
                        else:
                            # Restore entry
                            self.schedule.entries.append(entry)

            swaps_made += iteration_swaps
            if iteration_swaps == 0:
                break  # No more swaps possible

            print(f"  Iteration {iteration + 1}: {iteration_swaps} swaps")

        if swaps_made > 0:
            print(f"  Total preference improvement swaps: {swaps_made}")
        else:
            print("  No preference improvement swaps found")


    def _balance_staff_distribution(self):
        """
        Balance staff activity distribution across the week.

        Redistributes staff activities from overloaded days to underloaded days
        by swapping with fill activities to achieve more even staff utilization.
        """
        from ...models import ScheduleEntry

        print("\n--- Staff Distribution Balancing ---")

        # Staff activities that need balanced distribution
        # NOTE: Excluded Tower/Rifle/Shotgun/Archery because these should CLUSTER on fewer days
        STAFF_ACTIVITIES = {"Super Troop", "Delta"}

        # Fill activities that can be swapped
        FILL_ACTIVITIES = self.MOVABLE_FILL_ACTIVITIES

        # Exclusive activities need slot availability check
        EXCLUSIVE_ACTIVITIES = (
            {"Super Troop", "Delta"}
            | set(EXCLUSIVE_AREAS.get("Tower", []))
            | set(EXCLUSIVE_AREAS.get("Archery", []))
            | set(EXCLUSIVE_AREAS.get("Rifle Range", []))
        )

        # Calculate staff load per day
        staff_per_day = {Day.MONDAY: 0, Day.TUESDAY: 0, Day.WEDNESDAY: 0, 
                        Day.THURSDAY: 0, Day.FRIDAY: 0}

        for entry in self.schedule.entries:
            if entry.activity.name in STAFF_ACTIVITIES:
                staff_per_day[entry.time_slot.day] += 1

        # Calculate average and identify imbalanced days
        total_staff = sum(staff_per_day.values())
        avg_staff = total_staff / 5.0  # 5 days

        print(f"  Staff per day: {dict((day.name, count) for day, count in staff_per_day.items())}")
        print(f"  Average: {avg_staff:.1f}")

        overloaded = [(day, count) for day, count in staff_per_day.items() if count > avg_staff + 0.5]
        underloaded = [(day, count) for day, count in staff_per_day.items() if count < avg_staff - 0.5]

        if not overloaded or not underloaded:
            print("  Distribution already balanced")
            return

        print(f"  Overloaded days: {[(d.name, c) for d, c in overloaded]}")
        print(f"  Underloaded days: {[(d.name, c) for d, c in underloaded]}")

        swaps_made = 0
        max_swaps = 5  # Limit to avoid over-optimization

        # Try to move activities from overloaded to underloaded days
        for over_day, over_count in overloaded:
            if swaps_made >= max_swaps:
                break

            for under_day, under_count in underloaded:
                if swaps_made >= max_swaps:
                    break
                if staff_per_day[over_day] <= avg_staff + 0.5:
                    break  # This day is now balanced

                # Find staff activities on overloaded day
                staff_on_over_day = [e for e in self.schedule.entries 
                                    if e.activity.name in STAFF_ACTIVITIES
                                    and e.time_slot.day == over_day]

                # Find fill activities on underloaded day
                fills_on_under_day = [e for e in self.schedule.entries
                                     if e.activity.name in FILL_ACTIVITIES  
                                     and e.time_slot.day == under_day]

                if not staff_on_over_day or not fills_on_under_day:
                    continue

                # Try swapping staff activity to underloaded day
                for staff_entry in staff_on_over_day:
                    if swaps_made >= max_swaps:
                        break

                    # SKIP MULTI-SLOT STAFF MOVES: Moving partials breaks them
                    if staff_entry.activity.slots > 1.0:
                        continue

                    for fill_entry in fills_on_under_day:
                        if staff_entry.troop != fill_entry.troop:
                            continue  # Must be same troop

                        # Check if swap is valid
                        if staff_entry not in self.schedule.entries or fill_entry not in self.schedule.entries:
                            continue

                        # Temporarily remove both
                        self.schedule.entries.remove(staff_entry)
                        self.schedule.entries.remove(fill_entry)

                        # Check if swap is valid using comprehensive validation
                        # We must use is_activity_available to check ALL constraints (adjacency, exclusivity, etc.)
                        can_swap = False
                        if (self.schedule.is_activity_available(fill_entry.time_slot, staff_entry.activity, staff_entry.troop) and
                            self.schedule.is_activity_available(staff_entry.time_slot, fill_entry.activity, fill_entry.troop)):
                            can_swap = True

                        if can_swap:
                            # Execute swap
                            new_staff = ScheduleEntry(time_slot=fill_entry.time_slot, activity= staff_entry.activity, troop= staff_entry.troop)
                            new_fill = ScheduleEntry(time_slot=staff_entry.time_slot, activity= fill_entry.activity, troop= fill_entry.troop)

                            self.schedule.entries.append(new_staff)
                            self.schedule.entries.append(new_fill)

                            # Update counts
                            staff_per_day[over_day] -= 1
                            staff_per_day[under_day] += 1

                            swaps_made += 1
                            print(f"  [Balance] {staff_entry.troop.name}: {staff_entry.activity.name} {over_day.name} -> {under_day.name}")
                            break  # Move to next staff activity
                        else:
                            # Restore entries
                            self.schedule.entries.append(staff_entry)
                            self.schedule.entries.append(fill_entry)

        if swaps_made > 0:
            print(f"  Made {swaps_made} balancing swaps")
            print(f"  New distribution: {dict((day.name, count) for day, count in staff_per_day.items())}")
        else:
            print("  No balancing swaps possible")


    def _deduplicate_entries(self):
        """
        Remove duplicate schedule entries.

        1. Exact duplicates: same (troop, activity, slot)
        2. Activity duplicates: same (troop, activity) but different slots
           - For 1-slot activities, keep only the first occurrence
           - For multi-slot activities, keep up to slots_needed occurrences
        """
        # Pass 1: Remove exact duplicates (same troop, activity, slot)
        seen = set()
        unique_entries = []
        removed = 0

        for entry in self.schedule.entries:
            key = (entry.troop.name, entry.activity.name, 
                   entry.time_slot.day.name, entry.time_slot.slot_number)
            if key not in seen:
                seen.add(key)
                unique_entries.append(entry)
            else:
                removed += 1

        if removed > 0:
            self.schedule.entries = unique_entries
            print(f"  Removed {removed} exact duplicate entries")

        # Pass 2: Remove activity duplicates (same troop, same activity on different days)
        # For multi-slot activities, group by (day, starting_slot) to count OCCURRENCES not ENTRIES
        troop_activities = {}  # (troop_name, activity_name) -> list of entries

        for entry in self.schedule.entries:
            key = (entry.troop.name, entry.activity.name)
            if key not in troop_activities:
                troop_activities[key] = []
            troop_activities[key].append(entry)

        duplicates_removed = 0
        entries_to_keep = []

        for (troop_name, activity_name), entries in troop_activities.items():
            activity = entries[0].activity

            # For multi-slot activities, group entries by (day, starting_slot) to find OCCURRENCES
            if activity.slots > 1 or activity.slots == 1.5:  # Include Sailing (1.5 slots)
                # Group by day to find unique occurrences
                day_groups = {}
                for e in entries:
                    day = e.time_slot.day.name
                    if day not in day_groups:
                        day_groups[day] = []
                    day_groups[day].append(e)

                # Should only have 1 occurrence (1 day with this activity)
                if len(day_groups) > 1:
                    # Multiple occurrences - keep only the first day
                    sorted_days = sorted(day_groups.keys(), key=lambda d: getattr(Day, d).value)
                    keep_day = sorted_days[0]

                    # Keep entries from first day (all slots for that day)
                    entries_to_keep.extend(day_groups[keep_day])

                    # Remove entries from other days
                    for day in sorted_days[1:]:
                        for e in day_groups[day]:
                            duplicates_removed += 1
                            print(f"  Removed duplicate: {troop_name} has extra {activity_name} occurrence on {day}")
                else:
                    # Only 1 occurrence - but check if we have the right number of entries
                    # For Sailing (1.5 slots), should have 2 entries (start + continuation)
                    # For 2-slot activities, should have 2 entries
                    # For 3-slot activities, should have 3 entries
                    expected_entries = int(activity.slots + 0.5) if activity.slots != int(activity.slots) else int(activity.slots)
                    if len(entries) > expected_entries:
                        # Too many entries for same day - keep only the first N
                        entries.sort(key=lambda e: e.time_slot.slot_number)
                        entries_to_keep.extend(entries[:expected_entries])
                        for e in entries[expected_entries:]:
                            duplicates_removed += 1
                            print(f"  Removed duplicate: {troop_name} has extra {activity_name} entry @ {e.time_slot.day.name}-{e.time_slot.slot_number}")
                    else:
                        # Correct number of entries - keep all
                        entries_to_keep.extend(entries)
            else:
                # Single-slot activity - should only have 1 entry
                if len(entries) > 1:
                    # Keep first entry, remove the rest
                    entries.sort(key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number))
                    entries_to_keep.append(entries[0])

                    for e in entries[1:]:
                        duplicates_removed += 1
                        print(f"  Removed duplicate: {troop_name} has extra {activity_name} @ {e.time_slot.day.name}-{e.time_slot.slot_number}")
                else:
                    entries_to_keep.extend(entries)

        if duplicates_removed > 0:
            self.schedule.entries = entries_to_keep
            print(f"  Total activity duplicates removed: {duplicates_removed}")
        else:
            print("  No duplicates found")


    def _remove_overlaps(self):
        """
        Remove scheduling conflicts:
        1. Boundary violations (multi-slot activities extending beyond day max)
        2. Direct overlaps (multiple activities starting in same slot)
        3. Extension overlaps (multi-slot activity extending into another activity)
        """
        entries_to_remove = []

        def mark_for_removal(e_to_remove):
            if e_to_remove in entries_to_remove:
                return
            entries_to_remove.append(e_to_remove)

            # If multi-slot, remove ALL other entries for this activity on this day
            effective_slots = self.schedule._get_effective_slots(e_to_remove.activity, e_to_remove.troop)
            if effective_slots > 1:
                siblings = [s for s in self.schedule.entries 
                           if s.troop == e_to_remove.troop 
                           and s.activity.name == e_to_remove.activity.name 
                           and s.time_slot.day == e_to_remove.time_slot.day
                           and s != e_to_remove]
                for s in siblings:
                    if s not in entries_to_remove:
                        entries_to_remove.append(s)

        # PASS 1: Remove multi-slot activities that extend beyond day boundaries
        # IMPORTANT: Only check STARTING entries, not continuations
        seen_activities = set()  # Track (troop, activity, day) to avoid checking continuations

        for entry in list(self.schedule.entries):
            effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
            if effective_slots > 1:
                day = entry.time_slot.day
                start_slot = entry.time_slot.slot_number
                activity_key = (entry.troop.name, entry.activity.name, day.name)

                # Skip if we've already processed this activity on this day for this troop
                if activity_key in seen_activities:
                    continue  # This is a continuation entry, skip it
                seen_activities.add(activity_key)

                # Now check if the STARTING entry would exceed boundaries
                # Use effective slots to handle troop size scaling (e.g. Tower for 16+ scouts)
                effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
                slots_needed = int(effective_slots + 0.5)
                max_slot = 2 if day == Day.THURSDAY else 3
                end_slot = start_slot + slots_needed - 1

                if end_slot > max_slot:
                    # Exception: day-requested 3-slot activity on Thursday is an
                    # authorized opt-out of the mandatory 3rd-slot camp event.
                    # Do NOT remove — the troop intentionally consumes Thu 1+2+3.
                    if (day == Day.THURSDAY
                            and self._is_day_request_thursday_3slot(entry.troop, entry.activity)):
                        continue
                    # Remove ALL entries for this activity (starting + continuations)
                    activity_entries = [e for e in self.schedule.entries 
                                       if e.troop == entry.troop 
                                       and e.activity.name == entry.activity.name
                                       and e.time_slot.day == day]
                    for e in activity_entries:
                        if e not in entries_to_remove:
                            entries_to_remove.append(e)
                            if e == entry:  # Only print once for the starting entry
                                print(f"  Boundary fix: {entry.troop.name} - {entry.activity.name} @ {day.name} slot {start_slot}")

        # Apply pass 1 removals
        if entries_to_remove:
            self.schedule.entries = [e for e in self.schedule.entries if e not in entries_to_remove]

        # PASS 2: Build slot occupation map (which slots are occupied by which entries)
        # Group by troop, then by slot
        troop_slots = {}  # troop_name -> {(day, slot) -> list of entries occupying that slot}

        for entry in self.schedule.entries:
            troop_name = entry.troop.name
            if troop_name not in troop_slots:
                troop_slots[troop_name] = {}

            day = entry.time_slot.day.name
            start_slot = entry.time_slot.slot_number

            # Calculate slots this activity occupies
            effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
            slots_needed = int(effective_slots + 0.5) if effective_slots > 1 else 1

            for offset in range(slots_needed):
                slot = start_slot + offset
                slot_key = (day, slot)
                if slot_key not in troop_slots[troop_name]:
                    troop_slots[troop_name][slot_key] = []
                troop_slots[troop_name][slot_key].append(entry)

        # PASS 3: Find and resolve overlaps
        entries_to_remove = []  # Reset
        already_processed = set()  # Track (troop, day, slot) combos we've already handled

        for troop_name, slots in troop_slots.items():
            for slot_key, entries in slots.items():
                day, slot = slot_key

                PROTECTED = self.NON_DISPLACEABLE_ACTIVITIES
                # Skip if we already processed this slot
                if (troop_name, day, slot) in already_processed:
                    continue
                already_processed.add((troop_name, day, slot))

                # Filter out concurrent activities? NO.
                # Even concurrent activities (Reflection) cannot run simultaneously with others for the SAME troop.
                non_concurrent = entries

                # If >1 non-concurrent activity occupies this slot, we have a conflict
                if len(non_concurrent) > 1:
                    troop = non_concurrent[0].troop

                    # CRITICAL FIX: Filter out continuation entries of the same activity
                    # If we have multiple entries for the SAME activity (e.g., Back of the Moon @ slots 1, 2, 3),
                    # these are NOT overlaps - they're continuations. Only keep ONE entry per unique activity.
                    unique_activities = {}
                    for e in non_concurrent:
                        if e.activity.name not in unique_activities:
                            unique_activities[e.activity.name] = e
                        # else: duplicate continuation entry, will be handled later

                    # Now check if we have multiple DIFFERENT activities (true overlap)
                    non_concurrent = list(unique_activities.values())

                    if len(non_concurrent) > 1:
                       # ABSOLUTE TOP 5 PROTECTION: Separate Top 5 from non-Top-5
                        top5_entries = []
                        non_top5_entries = []

                        for e in non_concurrent:
                            pref_rank = troop.preferences.index(e.activity.name) if e.activity.name in troop.preferences else 999
                            if pref_rank < 5:
                                top5_entries.append((e, pref_rank))
                            else:
                                non_top5_entries.append((e, pref_rank))

                        # RULE 0: PROTECTED activities override everything
                        protected_entries = [e for e in non_concurrent if e.activity.name in PROTECTED]
                        if protected_entries:
                            keep = protected_entries[0] # Keep first protected
                            # Remove EVERYTHING else
                            for e in non_concurrent:
                                if e != keep and e not in entries_to_remove:
                                    mark_for_removal(e)
                                    print(f"  Overlap fix: {troop_name} @ {day} slot {slot}")
                                    print(f"    Kept Protected: {keep.activity.name}")
                                    print(f"    Removed: {e.activity.name}")

                        # RULE 1: If there's ANY Top 5 & NO Protected, keep it and remove ALL non-Top-5
                        elif top5_entries:
                            # Keep the HIGHEST priority Top 5
                            top5_entries.sort(key=lambda x: x[1])
                            keep = top5_entries[0][0]

                            # Remove all non-Top-5 activities
                            for e, rank in non_top5_entries:
                                if e not in entries_to_remove:
                                    mark_for_removal(e)
                                    rank_str = f"#{rank+1}" if rank < 999 else "fill"
                                    print(f"  Overlap fix: {troop_name} @ {day} slot {slot}")
                                    print(f"    Kept Top 5: {keep.activity.name} (#{top5_entries[0][1]+1})")
                                    print(f"    Removed: {e.activity.name} ({rank_str})")

                            # If multiple Top 5 conflict, keep highest priority, warn about others
                            if len(top5_entries) > 1:
                                print(f"  [CRITICAL] Multiple Top 5 conflict at {day}-{slot}:")
                                for e, rank in top5_entries:
                                    print(f"    {troop_name}: {e.activity.name} (#{rank+1})")
                                print(f"    Keeping #{top5_entries[0][1]+1}, removing others")

                                for e, rank in top5_entries[1:]:
                                    if e not in entries_to_remove:
                                        mark_for_removal(e)
                                        # TRACK TOP 5 TO RECOVER LATER
                                        if not hasattr(self, '_top5_to_recover'):
                                            self._top5_to_recover = []
                                        self._top5_to_recover.append((troop, e.activity, rank))
                        else:
                            # RULE 2: No Top 5 involved - use original priority logic
                            def sort_key(e):
                                pref_rank = troop.preferences.index(e.activity.name) if e.activity.name in troop.preferences else 999
                                effective_slots = self.schedule._get_effective_slots(e.activity, troop)
                                is_multislot = 1 if effective_slots > 1 else 0
                                starts_here = 1 if e.time_slot.slot_number == slot else 0
                                return (-is_multislot, -starts_here, pref_rank)

                            sorted_entries = sorted(non_concurrent, key=sort_key)

                            for e in sorted_entries[1:]:
                                if e not in entries_to_remove:
                                    mark_for_removal(e)
                                    print(f"  Overlap fix: {troop_name} @ {day} slot {slot}")
                                    print(f"    Kept: {sorted_entries[0].activity.name}")
                                    print(f"    Removed: {e.activity.name}")

        # Apply pass 3 removals
        if entries_to_remove:
            self.schedule.entries = [e for e in self.schedule.entries if e not in entries_to_remove]
            print(f"  Total issues fixed: {len(entries_to_remove)}")

        # RECOVERY: Try to reschedule any Top 5 that were removed due to conflicts
        # This MUST run regardless of whether we removed overlaps in this pass,
        # because items might have been added to the recovery list elsewhere (e.g. mandatory guarantees)
        if hasattr(self, '_top5_to_recover') and self._top5_to_recover:
            print(f"  [Top 5 Recovery] Attempting to recover {len(self._top5_to_recover)} removed Top 5 activities...")

            # Sort by rank to recover highest priority first
            self._top5_to_recover.sort(key=lambda x: x[2])

            recovered_count = 0
            for troop, activity, rank in list(self._top5_to_recover):
                # Check if troop still doesn't have this activity
                if self._troop_has_activity(troop, activity):
                    self._top5_to_recover.remove((troop, activity, rank))
                    continue

                # STRATEGY 1: Try to find an empty available slot
                for recovery_slot in self.time_slots:
                    if self._can_schedule(troop, activity, recovery_slot, recovery_slot.day):
                        self._add_to_schedule(recovery_slot, activity, troop)
                        print(f"    [RECOVERED] {troop.name}: {activity.name} (#{rank+1}) -> {recovery_slot.day.name[:3]}-{recovery_slot.slot_number}")
                        self._top5_to_recover.remove((troop, activity, rank))
                        recovered_count += 1
                        break

                if (troop, activity, rank) not in self._top5_to_recover:
                    continue # Already recovered

                # STRATEGY 2: Try to displace a non-Top 5 activity
                for recovery_slot in self.time_slots:
                    # Find what's in this slot for this troop
                    blocking = [e for e in self.schedule.entries if e.troop == troop and e.time_slot == recovery_slot]

                    # Only displace if ALL blocking activities are non-Top 5 (rank > 5)
                    if blocking and all(troop.get_priority(e.activity.name) > 5 for e in blocking):
                        # Temporarily remove and check if we can schedule
                        removed_blocking = []
                        for b in list(blocking):
                            self.schedule.entries.remove(b)
                            removed_blocking.append(b)

                        if self._can_schedule(troop, activity, recovery_slot, recovery_slot.day):
                            self._add_to_schedule(recovery_slot, activity, troop)
                            print(f"    [RECOVERED-DISPLACE] {troop.name}: {activity.name} (#{rank+1}) -> {recovery_slot.day.name[:3]}-{recovery_slot.slot_number} (displaced {', '.join(b.activity.name for b in removed_blocking)})")
                            self._top5_to_recover.remove((troop, activity, rank))
                            recovered_count += 1
                            break
                        else:
                            # Put them back
                            for b in removed_blocking:
                                self.schedule.entries.append(b)

                if (troop, activity, rank) in self._top5_to_recover:
                    print(f"    [FAILED] Could not recover {troop.name}: {activity.name} (#{rank+1})")

            # Clear the recovery list
            self._top5_to_recover = []
            if recovered_count > 0:
                print(f"  Successfully recovered {recovered_count} Top 5 activities")
        else:
            print("  No overlaps found")


    def _remove_activity_conflicts(self):
        """
        Remove activity conflicts where multiple troops have the same exclusive activity
        at the same time slot. Keep the first troop (by preference rank) and remove others.
        """
        # Activities that CAN have multiple troops (truly concurrent):
        # - Reflection (all troops do it on Friday)
        # - 3-hour off-camp activities (multiple troops can go together)
        # - Campsite Free Time (in-campsite, no conflict)
        # NOTE: Gaga Ball, 9 Square are EXCLUSIVE (1 troop at a time)
        # NOTE: Delta and Super Troop ARE exclusive (one troop per commissioner)
        concurrent = set(self.CONCURRENT_EXCLUSIVITY_EXCEPTIONS)

        entries_to_remove = []

        # Group entries by (day, slot, activity)
        activity_slot_map = {}  # (day, slot, activity) -> list of entries

        for entry in self.schedule.entries:
            if entry.activity.name not in concurrent:
                key = (entry.time_slot.day.name, entry.time_slot.slot_number, entry.activity.name)
                if key not in activity_slot_map:
                    activity_slot_map[key] = []
                activity_slot_map[key].append(entry)

        # Find and resolve conflicts (multiple troops with same activity at same time)
        for key, entries in activity_slot_map.items():
            if len(entries) > 1:
                day, slot, activity = key

                # SPECIAL: Aqua Trampoline can have TWO small troops (≤16 scouts+adults each)
                if activity == "Aqua Trampoline":
                    small_troops = [e for e in entries if (e.troop.scouts + e.troop.adults) <= 16]
                    if len(small_troops) == len(entries) and len(entries) <= 2:
                        continue  # Allow - all small and max 2

                # Sailing follows the BRAIN 90-minute overlap model:
                # slot 1 max 1, slot 2 max 2, slot 3 max 1.
                # This preserves the legal overlap of a slot-1 start with a slot-2 start.
                if activity == "Sailing":
                    allowed = 2 if day != "THURSDAY" and slot == 2 else 1
                    if len(entries) <= allowed:
                        continue

                # SPECIAL: Water Polo allows up to 2 troops
                if activity == "Water Polo" and len(entries) <= 2:
                    continue

                # SPECIAL: Canoe activities - check total capacity (max 26 people)
                if activity in self.CANOE_ACTIVITIES:
                    total_people = sum(e.troop.scouts + e.troop.adults for e in entries)
                    if total_people <= self.MAX_CANOE_CAPACITY:
                        continue  # Allow - within capacity


                # Sort by TWO criteria:
                # 1. Top 5 status (Top 5 should NEVER be removed if possible)
                # 2. Preference rank within category
                def sort_key(e):
                    priority = e.troop.preferences.index(e.activity.name) if e.activity.name in e.troop.preferences else 999
                    is_top5 = priority < 5
                    return (not is_top5, priority)  # False sorts before True, so Top 5 come first

                sorted_entries = sorted(entries, key=sort_key)

                # For Aqua Trampoline, keep up to 2 small troops (≤16 scouts+adults)
                if activity == "Aqua Trampoline":
                    small_troops = [e for e in sorted_entries if (e.troop.scouts + e.troop.adults) <= 16]
                    large_troops = [e for e in sorted_entries if (e.troop.scouts + e.troop.adults) > 16]

                    # Remove all large troops and extra small troops (keep max 2 small)
                    for e in large_troops[1:]:  # Keep at most 1 large troop
                        if e not in entries_to_remove:
                            entries_to_remove.append(e)
                            print(f"  Activity conflict: {activity} @ {day} slot {slot}")
                            print(f"    Kept: {sorted_entries[0].troop.name}")
                            print(f"    Removed: {e.troop.name}")

                    for e in small_troops[2:]:  # Keep at most 2 small troops
                        if e not in entries_to_remove:
                            entries_to_remove.append(e)
                            print(f"  Activity conflict: {activity} @ {day} slot {slot}")
                            print(f"    Kept: first 2 small troops")
                            print(f"    Removed: {e.troop.name}")
                    continue

                # Define helper to remove siblings
                def mark_for_removal(e_to_remove):
                    if e_to_remove in entries_to_remove:
                        return
                    entries_to_remove.append(e_to_remove)

                    # If multi-slot, remove ALL other entries for this activity on this day
                    effective_slots = self.schedule._get_effective_slots(e_to_remove.activity, e_to_remove.troop)
                    if effective_slots > 1:
                        siblings = [s for s in self.schedule.entries 
                                   if s.troop == e_to_remove.troop 
                                   and s.activity.name == e_to_remove.activity.name 
                                   and s.time_slot.day == e_to_remove.time_slot.day
                                   and s != e_to_remove]
                        for s in siblings:
                            if s not in entries_to_remove:
                                entries_to_remove.append(s)

                # Keep the first (highest priority / Top 5 protected), remove rest
                # But NEVER remove if all are Top 5 - print warning instead
                all_top5 = all(sort_key(e)[0] == False for e in sorted_entries)

                if all_top5 and len(sorted_entries) > 1:
                    print(f"  [WARNING] Activity conflict: {activity} @ {day} slot {slot}")
                    print(f"    All {len(sorted_entries)} troops have this as Top 5:")
                    for e in sorted_entries:
                        priority = e.troop.preferences.index(e.activity.name)
                        print(f"      {e.troop.name} (#{priority+1})")
                    print(f"    Keeping: {sorted_entries[0].troop.name} (first by priority)")
                    # Still have to remove some, keep first
                    for e in sorted_entries[1:]:
                        mark_for_removal(e)
                else:
                    # Normal removal - prioritize keeping Top 5
                    for e in sorted_entries[1:]:
                        mark_for_removal(e)

        # Remove conflicting entries
        if entries_to_remove:
            self.schedule.entries = [e for e in self.schedule.entries if e not in entries_to_remove]
            print(f"  Total activity conflicts removed: {len(entries_to_remove)}")
        else:
            print("  No activity conflicts found")


    def _guarantee_mandatory_activities(self):
        """
        Ensure all troops have mandatory activities (Reflection, Super Troop)
        after overlap removal may have removed them.
        """
        from ...models import ScheduleEntry

        reflection = get_activity_by_name("Reflection")
        super_troop = get_activity_by_name("Super Troop")

        for troop in self.troops:
            entries = [e for e in self.schedule.entries if e.troop == troop]
            has_reflection = any(e.activity.name == "Reflection" for e in entries)
            has_super_troop = any(e.activity.name == "Super Troop" for e in entries)

            # Ensure Reflection on Friday
            if not has_reflection and reflection:
                # Find empty Friday slot
                for slot_num in [1, 2, 3]:
                    slot = TimeSlot(day=Day.FRIDAY, slot_number=slot_num)
                    if self.schedule.is_troop_free(slot, troop):
                        if self.schedule.add_entry(slot, reflection, troop):
                            print(f"  Added Reflection for {troop.name} @ Friday slot {slot_num}")
                            has_reflection = True
                            break

            # If still no reflection, force replace the lowest priority Friday activity
            if not has_reflection and reflection:
                candidates = []
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                for e in troop_entries:
                    if e.time_slot.day == Day.FRIDAY and e.activity.name not in {'Reflection', 'Super Troop'}:
                        priority = troop.get_priority(e.activity.name)
                        candidates.append((e, priority))

                # Sort by priority descending (highest numeric = lowest priority = best to replace)
                candidates.sort(key=lambda x: x[1], reverse=True)

                for existing_entry, priority in candidates:
                    slot = existing_entry.time_slot
                    # Remove existing entry and add Reflection
                    self.schedule.entries.remove(existing_entry)
                    if self.schedule.add_entry(slot, reflection, troop):
                        print(f"  [MANDATORY] Replaced {existing_entry.activity.name} (#{priority+1 if priority < 999 else 'fill'}) with Reflection for {troop.name} @ Friday slot {slot.slot_number}")
                        if priority < 5:
                            if not hasattr(self, '_top5_to_recover'):
                                self._top5_to_recover = []
                            self._top5_to_recover.append((troop, existing_entry.activity, priority))
                            print(f"    Added {existing_entry.activity.name} to recovery list (displaced by mandatory Reflection)")
                        has_reflection = True
                        break
                    else:
                        self.schedule.entries.append(existing_entry)

            # Ensure Super Troop
            # Refresh entries as Reflection logic might have modified schedule
            entries = [e for e in self.schedule.entries if e.troop == troop]
            if not has_super_troop and super_troop:
                # Find any slot where troop is free AND Super Troop is available
                for day in [Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY, Day.MONDAY]:
                    max_slot = 2 if day == Day.THURSDAY else 3
                    for slot_num in range(1, max_slot + 1):
                        slot = TimeSlot(day=day, slot_number=slot_num)
                        if self.schedule.is_troop_free(slot, troop) and self.schedule.is_activity_available(slot, super_troop, troop):
                            if self.schedule.add_entry(slot, super_troop, troop):
                                print(f"  Added Super Troop for {troop.name} @ {day.name} slot {slot_num}")
                                has_super_troop = True
                                break
                    if has_super_troop:
                        break

                # If still no Super Troop, try replacing a low-priority activity
                if not has_super_troop:
                    # Find potential slots where Super Troop is available
                    candidates = []
                    for day in [Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY, Day.MONDAY]:
                        max_slot = 2 if day == Day.THURSDAY else 3
                        for slot_num in range(1, max_slot + 1):
                            slot = TimeSlot(day=day, slot_number=slot_num)
                            slot_entry = next((e for e in entries if e.time_slot == slot), None)

                            # Can only replace if not protected
                            if slot_entry and slot_entry.activity.name not in {'Reflection', 'Super Troop'}:
                                if self.schedule.is_activity_available(slot, super_troop, troop):
                                    priority = troop.get_priority(slot_entry.activity.name)
                                    candidates.append((slot, slot_entry, priority))

                    # Sort candidates: high numeric priority (low rank) first -> replace filler first
                    # get_priority returns 999 for filler, 0..N for Top N.
                    # We want to replace 999 first. So sort descending.
                    candidates.sort(key=lambda x: x[2], reverse=True)

                    for slot, slot_entry, priority in candidates:
                        # Remove the existing entry and add Super Troop
                        self.schedule.entries.remove(slot_entry)
                        if self.schedule.add_entry(slot, super_troop, troop):
                            print(f"  Replaced {slot_entry.activity.name} (#{priority+1 if priority < 999 else 'fill'}) with Super Troop for {troop.name} @ {slot.day.name} slot {slot.slot_number}")
                            has_super_troop = True
                            # If we displaced a Top 5 activity, try to recover it later
                            if priority < 5:
                                if not hasattr(self, '_top5_to_recover'):
                                    self._top5_to_recover = []
                                self._top5_to_recover.append((troop, slot_entry.activity, priority))
                                print(f"    Added {slot_entry.activity.name} to recovery list")
                            break
                        else:
                            self.schedule.entries.append(slot_entry)


    def _fill_empty_slots_final(self):
        """
        Fill any empty slots left after overlap removal with appropriate activities.
        AGGRESSIVE: Will try unique activities first, then allow duplicates to avoid gaps.
        STAFF-AWARE: Prioritizes staffed activities for low-staff slots to balance distribution.
        """
        from ...models import ScheduleEntry

        # Staffed activities (require staff)
        staffed_activities = [
            'Troop Rifle', 'Troop Shotgun', 'Archery', 'Climbing Tower',
            'Hemp Craft', "Monkey's Fist", 'Woggle Neckerchief Slide', 'Tie Dye',
            'Troop Swim', 'Troop Canoe', 'Aqua Trampoline',
            'Dr. DNA', 'Loon Lore'
        ]

        # Unstaffed generic fills follow SKULL fill_priority; Campsite Free
        # Time stays first unless it is already on the troop schedule.
        unstaffed_activities = [
            name for name in self.DEFAULT_FILL_PRIORITY
            if self._get_activity_staff_count(name) == 0
        ]

        for troop in self.troops:
            # Get current activities for this troop
            troop_activities = set(e.activity.name for e in self.schedule.entries if e.troop == troop)

            # CLUSTER-AWARE: Count activities per day for this troop
            activities_per_day = {}
            for day in Day:
                count = len([e for e in self.schedule.entries 
                             if e.troop == troop and e.time_slot.day == day])
                activities_per_day[day] = count

            # APPROACH 3: Weighted scoring - prioritize nearly-full days
            # A day with 2 activities (needs 1 more) is better than a day with 1 (needs 2 more)
            def fill_priority(day):
                count = activities_per_day.get(day, 0)
                max_slots = 2 if day == Day.THURSDAY else 3
                # Score: (activities / max_slots) gives 0.67 for 2/3, 0.5 for 1/2, 0.33 for 1/3
                # But we want to avoid empty days, so add bonus for any activities
                if count == 0:
                    return 0
                return count / max_slots + 0.1  # +0.1 to break ties in favor of busier days

            sorted_days = sorted(Day, key=fill_priority, reverse=True)

            # Check each slot - cluster days first
            for day in sorted_days:
                max_slot = 2 if day == Day.THURSDAY else 3

                # APPROACH 2: Sort slots by adjacency to existing activities
                filled_slots_today = set(e.time_slot.slot_number for e in self.schedule.entries 
                                         if e.troop == troop and e.time_slot.day == day)
                def adjacency_score(s):
                    # Higher score = closer to existing activities
                    if s in filled_slots_today:
                        return -1  # Already filled, lowest priority
                    score = 0
                    if s - 1 in filled_slots_today: score += 2  # Adjacent before
                    if s + 1 in filled_slots_today: score += 2  # Adjacent after
                    if len(filled_slots_today) > 0:
                        score += 1  # Has activities on this day at all
                    return score

                sorted_slots = sorted(range(1, max_slot + 1), key=adjacency_score, reverse=True)

                for slot_num in sorted_slots:
                    slot = TimeSlot(day=day, slot_number=slot_num)

                    # Check if this slot is free (considering multi-slot extensions)
                    if self.schedule.is_troop_free(slot, troop):
                        filled = False

                        # STAFF-AWARE FILL: Check current staff load for this slot
                        current_staff = self._get_total_staff_score(slot)
                        avg_staff = sum(self._get_total_staff_score(s) for s in self.time_slots) / len(self.time_slots)

                        # PREFERENCE-FIRST FILL: Add troop's remaining preferences to candidates
                        # This ensures we try preferences 6-15+ before generic fills
                        remaining_prefs = [p for p in troop.preferences if p not in troop_activities]

                        # Separate requested unstaffed from generic unstaffed
                        requested_unstaffed = [p for p in remaining_prefs if p in unstaffed_activities]
                        requested_staffed = [p for p in remaining_prefs if p not in unstaffed_activities]
                        generic_unstaffed = [a for a in unstaffed_activities if a not in remaining_prefs]
                        generic_staffed = [a for a in staffed_activities if a not in remaining_prefs]

                        # CRITICAL: Requested unstaffed activities should ALWAYS be tried before ANY generic fills
                        # Priority order: requested preferences (staffed/unstaffed) > requested unstaffed > generic unstaffed > generic staffed
                        # This ensures requested unstaffed activities are tried before generic unstaffed fills
                        # Even if staff is low, requested unstaffed should come before generic staffed
                        if current_staff < avg_staff:
                            fill_activities = requested_staffed + requested_unstaffed + generic_staffed + generic_unstaffed
                        else:
                            # When staff is high, still prioritize requested unstaffed over generic staffed
                            fill_activities = requested_staffed + requested_unstaffed + generic_unstaffed + generic_staffed

                        # SMART FILL: Score each candidate activity
                        # Check if this slot is "valuable" for clustering (on a day with cluster activities)
                        CLUSTER_AREAS = self._get_authoritative_gap_area_map()
                        cluster_activity_names = set()
                        for acts in CLUSTER_AREAS.values():
                            cluster_activity_names.update(acts)

                        # Check if day has cluster activities (slot is valuable)
                        day_entries = [e for e in self.schedule.entries 
                                      if e.troop == troop and e.time_slot.day == day]
                        day_entries_global = [e for e in self.schedule.entries if e.time_slot.day == day]
                        day_has_cluster = any(e.activity.name in cluster_activity_names for e in day_entries)

                        # Check for cluster gap (slots 1&3 full, slot 2 empty) - this is a HIGH PRIORITY fill
                        is_cluster_gap = False
                        cluster_gap_area = None
                        if slot_num == 2:  # Only slot 2 can fill a cluster gap
                            slots_filled = {e.time_slot.slot_number for e in day_entries}
                            if 1 in slots_filled and 3 in slots_filled:
                                # Check which cluster area has the gap
                                for area, acts in CLUSTER_AREAS.items():
                                    area_slots = {e.time_slot.slot_number for e in day_entries_global
                                                 if e.activity.name in acts}
                                    if 1 in area_slots and 3 in area_slots and 2 not in area_slots:
                                        is_cluster_gap = True
                                        cluster_gap_area = area
                                        break

                        # Also check GLOBAL cluster density - is this slot valuable for overall clustering?
                        global_day_cluster = sum(1 for e in self.schedule.entries 
                                                if e.time_slot.day == day 
                                                and e.activity.name in cluster_activity_names)
                        is_high_cluster_day = global_day_cluster >= 3  # Day has ≥3 cluster activities globally

                        # If day has cluster activities, PREFER unstaffed fills to leave room
                        # for cluster activities to swap in later
                        if day_has_cluster or is_high_cluster_day:
                            # Prefer "harmless" fills that won't block future clustering
                            fill_activities = unstaffed_activities + fill_activities

                        # Score candidates to find BEST fill, not just first valid.
                        # Floor at -1000 rejects Pass 1 picks that were disqualified
                        # (e.g., unrequested staffed activity that would create an
                        # excess cluster day); those drop to Pass 2's harmless fills.
                        best_fill = None
                        best_score = -1000

                        # PASS 1: Try activities troop doesn't already have
                        # CLUSTERING-AWARE PREFERENCE PRIORITY
                        for activity_name in fill_activities:
                            if activity_name in troop_activities:
                                continue  # Skip - already has this activity
                            activity = get_activity_by_name(activity_name)
                            if not activity or not self._can_schedule(troop, activity, slot, day):
                                continue

                            # Score this fill option
                            score = 0

                            # 0. PREFERENCE RANK PRIORITY (MOST IMPORTANT!)
                            pref_rank = troop.get_priority(activity_name)
                            is_requested = pref_rank is not None
                            is_unstaffed = activity_name in unstaffed_activities

                            if is_requested:
                                # Check clustering impact for lower-priority preferences
                                would_create_excess = False
                                if pref_rank >= 11:  # Top 11+ check clustering
                                    would_create_excess = self._would_create_excess_day(activity_name, day, troop=troop)

                                # Massive bonus inversely proportional to rank
                                # Top 5-10: Always prioritize (even if slight excess)
                                # Top 11-15: Prioritize if doesn't create excess
                                # Top 16+: Only if doesn't create excess
                                if pref_rank < 5:
                                    score += 1000 - (pref_rank * 10)  # 1000, 990, 980, 970, 960
                                elif pref_rank < 10:
                                    score += 950 - (pref_rank * 15)  # 875, 860, 845, 830, 815
                                elif pref_rank < 15:
                                    if would_create_excess:
                                        score -= 500  # Heavy penalty for creating excess day
                                    else:
                                        score += 750 - (pref_rank * 10)  # 650, 640, 630, 620, 610
                                elif pref_rank < 20:
                                    if would_create_excess:
                                        score -= 500  # Heavy penalty for creating excess day
                                    else:
                                        score += 550 - (pref_rank * 7)   # 445, 438, 431, 424, 417
                                else:
                                    if would_create_excess:
                                        score -= 500  # Heavy penalty for creating excess day
                                    else:
                                        score += 200 - (pref_rank * 2)   # Lower tiers still beat generic fills

                            # 1. Prefer unstaffed on high-staff slots
                            if current_staff > avg_staff and is_unstaffed:
                                score += 3
                            elif current_staff < avg_staff and not is_unstaffed:
                                score += 2

                            # 2. Beach activities good for water-adjacent scheduling
                            beach_activities = {'Troop Swim', 'Troop Canoe', 'Aqua Trampoline', 
                                               'Greased Watermelon', 'Water Polo'}
                            if activity_name in beach_activities and slot_num != 2:
                                score += 1  # Beach is OK for slots 1 and 3

                            # 3. Clustering impact - prefer fills that match day's cluster area
                            # CRITICAL: AVOID creating "excess days" by adding staff activities to days
                            # where the troop has no other activities for that area.
                            is_cluster_consistent = True
                            is_staff_activity = False

                            # HUGE BONUS: If this is a cluster gap (slot 2, slots 1&3 full), prioritize cluster activities
                            if is_cluster_gap and cluster_gap_area:
                                gap_area_acts = CLUSTER_AREAS[cluster_gap_area]
                                if activity_name in gap_area_acts:
                                    score += 500  # MASSIVE bonus for filling cluster gap with correct activity
                                elif activity_name in cluster_activity_names:
                                    score += 100  # Good bonus for any cluster activity filling gap

                            for area, acts in CLUSTER_AREAS.items():
                                if activity_name in acts:
                                    is_staff_activity = True
                                    day_area_count = sum(1 for e in day_entries 
                                                        if e.activity.name in acts)

                                    if day_area_count > 0:
                                        score += day_area_count * 20  # HUGE Bonus for clustering (consolidate)
                                    else:
                                        # New area for this day - PENALIZE to avoid excess days.
                                        # An unrequested staff activity that inflates the troop's
                                        # day spread is strictly worse than a harmless unstaffed
                                        # fill. Hard-block via
                                        # a disqualifying negative so Pass 1 only picks it when
                                        # no other option exists.
                                        creates_excess_for_troop = self._would_create_excess_day(activity_name, day, troop=troop)
                                        if not is_requested and is_staff_activity:
                                            if creates_excess_for_troop:
                                                score -= 5000  # Disqualifying: never pick over unstaffed fill
                                            else:
                                                score -= 100
                                        else:
                                            score -= 30  # Moderate penalty for requested new-area
                                            if creates_excess_for_troop:
                                                score -= 50  # Additional penalty for excess
                                        is_cluster_consistent = False
                                    break

                            # MODERATE MODE: Heavily penalize but don't completely block unrequested staff activities
                            if not is_cluster_consistent and is_staff_activity and not is_requested:
                                score -= 150  # Heavy penalty - prefer unstaffed fills instead, but allow if no better option

                            # 4. Variety bonus - slightly prefer activities not yet scheduled
                            if activity_name not in troop_activities:
                                score += 1

                            if score > best_score:
                                best_score = score
                                best_fill = activity


                        if best_fill:
                            if self.schedule.add_entry(slot, best_fill, troop):
                                troop_activities.add(best_fill.name)
                                print(f"  Filled {troop.name} @ {day.name} slot {slot_num} with {best_fill.name}")
                                filled = True

                        # PASS 2: If nothing worked, allow duplicates (better than gaps!)
                        # Two sub-passes: first try fills that do NOT create a new
                        # excess cluster day for this troop, then fall through to
                        # ones that do. This avoids picking a staffed fill when a
                        # harmless alternative exists.
                        if not filled:
                            for allow_excess in (False, True):
                                if filled:
                                    break
                                for activity_name in fill_activities:
                                    activity = get_activity_by_name(activity_name)
                                    if not activity or not self._can_schedule(troop, activity, slot, day):
                                        continue
                                    if not allow_excess and self._would_create_excess_day(activity_name, day, troop=troop):
                                        continue
                                    if self.schedule.add_entry(slot, activity, troop):
                                        troop_activities.add(activity_name)
                                        tag = "[DUPLICATE]" if not allow_excess else "[DUPLICATE-EXCESS]"
                                        print(f"  Filled {troop.name} @ {day.name} slot {slot_num} with {activity_name} {tag}")
                                        filled = True
                                        break

                        # PASS 3: Last resort - try ANY activity from the full list.
                        # Same two-sub-pass excess-aware ordering.
                        if not filled:
                            for allow_excess in (False, True):
                                if filled:
                                    break
                                for activity in self.activities:
                                    if activity.name in ['Delta', 'Super Troop', 'Reflection']:
                                        continue  # Skip mandatory/special activities
                                    if not self._can_schedule(troop, activity, slot, day):
                                        continue
                                    if not allow_excess and self._would_create_excess_day(activity.name, day, troop=troop):
                                        continue
                                    if self.schedule.add_entry(slot, activity, troop):
                                        troop_activities.add(activity.name)
                                        tag = "[LAST RESORT]" if not allow_excess else "[LAST RESORT-EXCESS]"
                                        print(f"  Filled {troop.name} @ {day.name} slot {slot_num} with {activity.name} {tag}")
                                        filled = True
                                        break

                        # PASS 4: ABSOLUTE LAST RESORT - relax constraints (NO GAPS ALLOWED!)
                        # Still prefer non-excess activities even when soft constraints relaxed.
                        if not filled:
                            for allow_excess in (False, True):
                                if filled:
                                    break
                                for activity in self.activities:
                                    if activity.name in ['Delta', 'Super Troop', 'Reflection']:
                                        continue
                                    if not self._can_schedule(troop, activity, slot, day, relax_constraints=True):
                                        continue
                                    if not allow_excess and self._would_create_excess_day(activity.name, day, troop=troop):
                                        continue
                                    if self.schedule.add_entry(slot, activity, troop):
                                        troop_activities.add(activity.name)
                                        tag = "[RELAXED CONSTRAINTS]" if not allow_excess else "[RELAXED-EXCESS]"
                                        print(f"  Filled {troop.name} @ {day.name} slot {slot_num} with {activity.name} {tag}")
                                        filled = True
                                        break

                            if not filled:
                                print(f"  WARNING: Could not fill {troop.name} @ {day.name} slot {slot_num} - all activities blocked by constraints")


    def _optimize_flexible_reflections(self):
        """
        Flexible Reflection DISTRIBUTION - spread commissioner's troops across different slots.

        GOAL: Allow commissioners to attend multiple troop Reflections
        - Each commissioner should have their troops in DIFFERENT slots (1 troop per slot)
        - Ideal: Commissioner A has 3 troops → Fri-1, Fri-2, Fri-3 (one in each)
        - This allows the commissioner to visit all 3 of their troops' Reflections

        OLD BEHAVIOR (BUG): Clustered all troops together in same slot
        NEW BEHAVIOR (FIX): Spread troops across different slots
        """
        from ...models import ScheduleEntry

        print("\n--- Flexible Reflection Distribution (Spread Across Slots) ---")

        reflection = get_activity_by_name("Reflection")
        if not reflection:
            return

        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
        swaps_made = 0

        # Group troops by commissioner
        commissioner_troops = {}
        for troop in self.troops:
            comm = self.troop_commissioner.get(troop.name, "Unknown")
            if comm not in commissioner_troops:
                commissioner_troops[comm] = []
            commissioner_troops[comm].append(troop)

        for commissioner, troops in commissioner_troops.items():
            if len(troops) <= 1:
                continue  # No distribution needed for single-troop commissioners

            # Find reflection entries for this commissioner's troops
            reflection_entries = []
            for troop in troops:
                entry = next(
                    (e for e in self.schedule.entries 
                     if e.troop == troop and e.activity.name == "Reflection"),
                    None
                )
                if entry:
                    reflection_entries.append((troop, entry))

            if len(reflection_entries) <= 1:
                continue

            # Count how many troops in each slot
            slot_distribution = {}
            for _, entry in reflection_entries:
                slot = entry.time_slot
                if slot not in slot_distribution:
                    slot_distribution[slot] = []
                slot_distribution[slot].append(entry.troop)

            # Find slots with multiple troops from same commissioner (BAD - need to spread)
            overcrowded_slots = {slot: troops_list for slot, troops_list in slot_distribution.items() if len(troops_list) > 1}

            if not overcrowded_slots:
                print(f"  {commissioner}: Already distributed (1 per slot) [OK]")
                continue

            # Try to spread troops from overcrowded slots to empty/less-crowded slots
            for overcrowded_slot, troops_in_slot in overcrowded_slots.items():
                # Keep first troop, move others
                troops_to_move = troops_in_slot[1:]  # All but the first

                for troop in troops_to_move:
                    # Find current Reflection entry
                    current_entry = next((e for e in self.schedule.entries 
                                        if e.troop == troop and e.activity.name == "Reflection"), None)
                    if not current_entry:
                        continue

                    # Find a Friday slot that doesn't have this commissioner's troops yet
                    target_slot = None
                    for friday_slot in friday_slots:
                        # Check if this slot already has troops from this commissioner
                        has_commissioner_troop = any(
                            e.troop in troops and e.activity.name == "Reflection"
                            for e in self.schedule.entries if e.time_slot == friday_slot
                        )

                        if not has_commissioner_troop:
                            target_slot = friday_slot
                            break

                    if not target_slot:
                        continue  # No available slot

                    # Move Reflection to new slot; rollback immediately if add fails.
                    self.schedule.entries.remove(current_entry)
                    if not self.schedule.add_entry(target_slot, reflection, troop):
                        self.schedule.entries.append(current_entry)
                        continue

                    print(f"  [Swap] {troop.name}: Reflection {overcrowded_slot.day.name[:3]}-{overcrowded_slot.slot_number} -> {target_slot.day.name[:3]}-{target_slot.slot_number} (spreading {commissioner})")
                    swaps_made += 1

        if swaps_made > 0:
            print(f"  Total Reflection distribution swaps: {swaps_made}")
        else:
            print("  All commissioners already have troops spread across slots")


    def _optimize_commissioner_balance(self):
        """
        Optimize commissioner workload by balancing Reflection slots.

        Ensures commissioners don't have all their Reflections in the same slot,
        allowing them to visit each troop.
        """
        print("\n--- Commissioner Load Balancing ---")

        # Count Reflections per commissioner per slot
        commissioner_slot_counts = {}

        for entry in self.schedule.entries:
            if entry.activity.name != "Reflection":
                continue

            comm = self.troop_commissioner.get(entry.troop.name, "Unknown")
            slot = entry.time_slot

            if comm not in commissioner_slot_counts:
                commissioner_slot_counts[comm] = {}

            slot_key = (slot.day.name, slot.slot_number)
            commissioner_slot_counts[comm][slot_key] = commissioner_slot_counts[comm].get(slot_key, 0) + 1

        # Report on balance
        for comm, slots in sorted(commissioner_slot_counts.items()):
            slot_info = ", ".join(f"{s[0][:3]}-{s[1]}: {c}" for s, c in sorted(slots.items()))
            max_load = max(slots.values()) if slots else 0
            status = "[OK]" if max_load <= 3 else "[HEAVY]"
            print(f"  {comm}: {slot_info} {status}")


    def _optimize_setup_efficiency(self):
        """
        Optimize staff setup/teardown by batching same activities into consecutive slots.

        Target Activities (require significant setup):
        - Troop Shotgun: Shotgun thrower setup/teardown
        - Troop Rifle: Range setup/teardown
        - Tie Dye: Dye station setup/cleanup

        Strategy: For each target activity, try to move isolated instances to slots
        where another troop already has the same activity, creating consecutive blocks.
        """
        from collections import defaultdict

        print("\n--- Staff Batching (Setup Efficiency) ---")

        BATCH_ACTIVITIES = self.BATCH_SETUP_ACTIVITIES

        total_swaps = 0

        for activity_name in BATCH_ACTIVITIES:
            # Find all entries for this activity
            activity_entries = [e for e in self.schedule.entries if e.activity.name == activity_name]

            if len(activity_entries) < 2:
                continue  # Need at least 2 to batch

            # Group by (day, slot) to find existing batches
            slot_groups = defaultdict(list)
            for entry in activity_entries:
                key = (entry.time_slot.day, entry.time_slot.slot_number)
                slot_groups[key].append(entry)

            # Find slots that already have multiple troops (active batch)
            batch_slots = [slot_key for slot_key, entries in slot_groups.items() if len(entries) >= 1]

            # For each isolated entry, try to move it to a batch slot
            for entry in activity_entries:
                entry_key = (entry.time_slot.day, entry.time_slot.slot_number)

                # Check if this entry is isolated (only one in its slot)
                if len(slot_groups[entry_key]) > 1:
                    continue  # Already batched

                # Try to move to existing batch slots
                for batch_key in batch_slots:
                    if batch_key == entry_key:
                        continue  # Same slot

                    batch_day, batch_slot_num = batch_key
                    target_slot = next((s for s in self.time_slots 
                                       if s.day == batch_day and s.slot_number == batch_slot_num), None)

                    if not target_slot:
                        continue

                    # Check if troop is free in target slot
                    if not self.schedule.is_troop_free(target_slot, entry.troop):
                        # Try to swap with what's in target slot
                        target_entry = next((e for e in self.schedule.entries 
                                            if e.troop == entry.troop and e.time_slot == target_slot), None)

                        if not target_entry:
                            continue

                        # Don't swap protected activities
                        PROTECTED = {"Reflection", "Delta", "Super Troop", "Sailing"}
                        if target_entry.activity.name in PROTECTED:
                            continue

                        # Check if target activity can go in original slot
                        activity = get_activity_by_name(activity_name)

                        # Try the swap
                        orig_slot = entry.time_slot

                        # Temporarily remove both
                        self.schedule.entries.remove(entry)
                        self.schedule.entries.remove(target_entry)

                        # Check constraints
                        can_move_batch = self._can_schedule(entry.troop, activity, target_slot, target_slot.day, relax_constraints=True)
                        can_move_other = self._can_schedule(entry.troop, target_entry.activity, orig_slot, orig_slot.day, relax_constraints=True)

                        if can_move_batch and can_move_other:
                            # Execute swap
                            self.schedule.add_entry(target_slot, activity, entry.troop)
                            self.schedule.add_entry(orig_slot, target_entry.activity, entry.troop)
                            total_swaps += 1
                            print(f"  [Batch] {entry.troop.name}: {activity_name} {orig_slot.day.name[:3]}-{orig_slot.slot_number} -> {batch_day.name[:3]}-{batch_slot_num}")
                            break
                        else:
                            # Restore
                            self.schedule.entries.append(entry)
                            self.schedule.entries.append(target_entry)
                    else:
                        # Slot is free - just move
                        activity = get_activity_by_name(activity_name)
                        if self._can_schedule(entry.troop, activity, target_slot, target_slot.day, relax_constraints=True):
                            # Find what to fill original slot with
                            self.schedule.entries.remove(entry)
                            self.schedule.add_entry(target_slot, activity, entry.troop)
                            total_swaps += 1
                            print(f"  [Batch] {entry.troop.name}: {activity_name} {entry.time_slot.day.name[:3]}-{entry.time_slot.slot_number} -> {batch_day.name[:3]}-{batch_slot_num}")

                            # Fill the original slot with a harmless activity
                            self._fill_vacated_slot(entry.troop, entry.time_slot)
                            break

        if total_swaps > 0:
            print(f"  Made {total_swaps} batching swaps")
        else:
            print("  No batching opportunities found")


    def _optimize_activity_clustering(self):
        """
        ENHANCED: Ultra-aggressive clustering optimization to eliminate excess cluster days.

        This is the highest impact optimization after constraint violations:
        - Each excess cluster day costs -8 points
        - Target: Reduce excess days from 3-5 to 0-2 per area
        - Strategy: Smart consolidation with priority-aware moves
        """
        print("\n--- Activity Clustering Optimization ---")

        # Activities that don't count towards clustering (mandatory only)
        IGNORED = {'Reflection', 'Super Troop', 'Campsite Free Time', 'Trading Post', 'Shower House'}

        # Step 1: Standard clustering optimization
        total_swaps = self._standard_clustering_optimization(IGNORED)

        # Step 2: AGGRESSIVE area-based consolidation
        total_swaps += self._aggressive_area_clustering(IGNORED)

        # Step 3: FORCE-MOVE poorly clustered activities
        total_swaps += self._force_cluster_consolidation()

        print(f"  Made {total_swaps} clustering swaps (including aggressive moves)")

        return total_swaps


    def _standard_clustering_optimization(self, IGNORED):
        """Standard clustering optimization for isolated activities."""
        from ...models import Day

        candidates = []

        # Collect candidates
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]

            by_day = {}
            for e in troop_entries:
                if e.time_slot.day not in by_day:
                    by_day[e.time_slot.day] = []
                by_day[e.time_slot.day].append(e)

            # Find isolated activities
            for day, entries in by_day.items():
                significant_entries = [e for e in entries if e.activity.name not in IGNORED]
                if len(significant_entries) != 1: continue

                entry = significant_entries[0]
                candidates.append((troop, entry, day))

        # Sort by urgency
        def get_urgency(item):
            _, _, day = item
            if day == Day.FRIDAY: return 3
            if day == Day.THURSDAY: return 2
            return 1

        candidates.sort(key=get_urgency, reverse=True)

        cluster_area_map = self._get_authoritative_gap_area_map()
        activity_to_area = {
            activity_name: area_name
            for area_name, activities in cluster_area_map.items()
            for activity_name in activities
        }

        # Build global cluster density map from the same activities official scoring sees.
        STAFFED_CLUSTER = sorted(activity_to_area)

        global_density = {}
        for act_name in STAFFED_CLUSTER:
            global_density[act_name] = {}
            for day in Day:
                count = sum(1 for e in self.schedule.entries 
                           if e.activity.name == act_name and e.time_slot.day == day)
                global_density[act_name][day] = count

        def get_best_cluster_day(act_name):
            if act_name not in global_density:
                return None
            day_counts = global_density[act_name]
            best_day = max(day_counts.keys(), key=lambda d: day_counts.get(d, 0))
            if day_counts[best_day] >= 2:
                return best_day
            return None

        total_swaps = 0

        def get_area(name):
            return activity_to_area.get(name)

        # Execute moves
        for troop, entry, day in candidates:
            if entry not in self.schedule.entries: continue

            if entry.activity.slots > 1.0:
                continue

            # Check if already well-clustered
            area = get_area(entry.activity.name)
            if area:
                area_activities = set(cluster_area_map.get(area, []))
                area_entries = [
                    e for e in self.schedule.entries
                    if e.activity.name in area_activities
                ]
                area_days = {e.time_slot.day for e in area_entries}
                required_days = math.ceil(len(area_entries) / 3.0) if area_entries else 0
                if len(area_days) <= required_days:
                    continue

            # Try to move to better cluster day
            best_day = get_best_cluster_day(entry.activity.name)
            if best_day and best_day != day:
                # Find available slot on best_day
                for slot in self.time_slots:
                    if slot.day != best_day: continue
                    if not self.schedule.is_troop_free(slot, troop): continue
                    if not self._can_schedule(troop, entry.activity, slot, best_day, relax_constraints=True):
                        continue

                    # Make the move
                    self.schedule.entries.remove(entry)
                    self.schedule.add_entry(slot, entry.activity, troop)
                    total_swaps += 1
                    break

        return total_swaps


    def _aggressive_area_clustering(self, IGNORED):
        """Aggressive area-based clustering consolidation."""
        from ...models import Day

        total_moves = 0

        for area, activities in EXCLUSIVE_AREAS.items():
            # Count current distribution
            day_counts = {}
            area_entries = []

            for entry in self.schedule.entries:
                if entry.activity.name in activities:
                    day_counts[entry.time_slot.day] = day_counts.get(entry.time_slot.day, 0) + 1
                    area_entries.append(entry)

            if len(day_counts) <= 3:  # Already well clustered
                continue

            # Find the 3 best days (with most activities)
            best_days = sorted(day_counts.keys(), key=lambda d: day_counts[d], reverse=True)[:3]

            # Move activities from other days to best days
            for entry in area_entries[:]:  # Copy list to allow modification
                if entry.time_slot.day in best_days:
                    continue  # Already on a good day

                if entry.activity.name in IGNORED:
                    continue
                if self._is_pair_protected_delta(entry):
                    continue

                # Try to move to a best day
                for best_day in best_days:
                    for slot in self.time_slots:
                        if slot.day != best_day: continue
                        if not self.schedule.is_troop_free(slot, entry.troop): continue
                        if not self._can_schedule(entry.troop, entry.activity, slot, best_day, relax_constraints=True):
                            continue

                        old_slot = entry.time_slot
                        if self._remove_from_schedule(entry):
                            if self._add_to_schedule(slot, entry.activity, entry.troop):
                                total_moves += 1
                                print(f"  [Aggressive Cluster] {entry.troop.name}: {entry.activity.name} {old_slot.day.name[:3]} -> {best_day.name[:3]}")
                                break
                            self._add_to_schedule(old_slot, entry.activity, entry.troop)
                    else:
                        continue
                    break

        return total_moves


    def _force_cluster_consolidation(self):
        """Force consolidation of badly clustered activities."""
        from ...models import Day

        total_forced = 0

        # Target specific problematic activities
        PROBLEMATIC = ['Delta', 'Super Troop', 'Sailing', 'Climbing Tower', 'Aqua Trampoline']

        for act_name in PROBLEMATIC:
            entries = [e for e in self.schedule.entries if e.activity.name == act_name]
            if len(entries) < 2: continue

            # Count distribution
            day_counts = {}
            for entry in entries:
                day_counts[entry.time_slot.day] = day_counts.get(entry.time_slot.day, 0) + 1

            if len(day_counts) <= 2: continue  # Already reasonable

            # Force consolidate to top 2 days
            best_days = sorted(day_counts.keys(), key=lambda d: day_counts[d], reverse=True)[:2]

            for entry in entries[:]:
                if entry.time_slot.day in best_days:
                    continue

                if self._is_pair_protected_delta(entry):
                    continue

                # Force move to best day (ignore most constraints)
                for best_day in best_days:
                    for slot in self.time_slots:
                        if slot.day != best_day: continue
                        if not self.schedule.is_troop_free(slot, entry.troop): continue

                        old_slot = entry.time_slot
                        if self._remove_from_schedule(entry):
                            if self._add_to_schedule(slot, entry.activity, entry.troop):
                                total_forced += 1
                                print(f"  [Force Cluster] {entry.troop.name}: {act_name} {old_slot.day.name[:3]} -> {best_day.name[:3]}")
                                break
                            self._add_to_schedule(old_slot, entry.activity, entry.troop)
                    else:
                        continue
                    break

        return total_forced


    def _force_clustering_consolidation(self):
        """
        BULLETPROOF CLUSTERING: Force activities from excess days to minimum days.

        This method aggressively moves cluster activities from excess days to consolidate
        them into the minimum required number of days, reducing excess cluster day penalties.
        """
        from ...models import Day
        import math

        total_consolidated = 0

        # Target the same cluster areas used by official regression scoring.
        cluster_areas = self._get_authoritative_gap_area_map()

        for area, activities in cluster_areas.items():
            if not activities:
                continue

            # Find all entries for this area
            area_entries = [e for e in self.schedule.entries if e.activity.name in activities]
            if not area_entries:
                continue

            # Count current distribution
            day_counts = {}
            for entry in area_entries:
                day_counts[entry.time_slot.day] = day_counts.get(entry.time_slot.day, 0) + 1

            # Calculate minimum required days
            num_activities = len(area_entries)
            min_days = math.ceil(num_activities / 3.0)  # 3 slots per day capacity

            current_days = len(day_counts)
            excess_days = max(0, current_days - min_days)

            if excess_days <= 0:
                continue  # Already optimal

            # Find the best days (with most activities) to keep
            best_days = sorted(day_counts.keys(), key=lambda d: day_counts[d], reverse=True)[:min_days]

            # Find excess days (days to move activities FROM)
            excess_day_list = [day for day in day_counts.keys() if day not in best_days]

            # Move activities from excess days to best days
            for entry in area_entries[:]:  # Copy list to allow modification
                if entry.time_slot.day not in excess_day_list:
                    continue  # Already on a good day
                if self._is_pair_protected_delta(entry):
                    continue

                # Try to move to each best day
                moved = False
                for best_day in best_days:
                    # Try each slot on the best day
                    for slot in self.time_slots:
                        if slot.day != best_day:
                            continue
                        if not self.schedule.is_troop_free(slot, entry.troop):
                            continue

                        # ENHANCED: Try with relaxed constraints first
                        if self._can_schedule(entry.troop, entry.activity, slot, best_day, relax_constraints=True):
                            # Make the move (transactional: rollback if add fails).
                            old_day = entry.time_slot.day
                            old_slot = entry.time_slot
                            self.schedule.entries.remove(entry)
                            if self.schedule.add_entry(slot, entry.activity, entry.troop):
                                total_consolidated += 1
                                print(f"  [Cluster Consolidate] {entry.troop.name}: {entry.activity.name} {old_day.name[:3]} -> {best_day.name[:3]}")
                                moved = True
                                break
                            self.schedule.add_entry(old_slot, entry.activity, entry.troop)

                    if moved:
                        break

                # Tier 2: relaxed + (conditionally) ignore day-requests. Never bypasses
                # MUST-HONOR for troops that authored day_requests, and never bypasses
                # hard constraints like beach-slot/staff caps.
                if not moved:
                    for best_day in best_days:
                        for slot in self.time_slots:
                            if slot.day != best_day:
                                continue
                            if not self.schedule.is_troop_free(slot, entry.troop):
                                continue
                            ign = self._optimization_may_ignore_day_requests(entry.troop)
                            if not self._can_schedule(
                                entry.troop, entry.activity, slot, best_day,
                                relax_constraints=True, ignore_day_requests=ign,
                            ):
                                continue
                            old_day = entry.time_slot.day
                            old_slot = entry.time_slot
                            self.schedule.entries.remove(entry)
                            if self.schedule.add_entry(slot, entry.activity, entry.troop):
                                total_consolidated += 1
                                print(f"  [Force Cluster] {entry.troop.name}: {entry.activity.name} {old_day.name[:3]} -> {best_day.name[:3]} (relaxed+ignore_dr={ign})")
                                moved = True
                                break
                            self.schedule.add_entry(old_slot, entry.activity, entry.troop)
                        if moved:
                            break

        if total_consolidated > 0:
            print(f"  Consolidated {total_consolidated} activities to reduce excess cluster days")

        return total_consolidated


    def _ultra_aggressive_clustering(self):
        """
        ENHANCED ULTRA-AGGRESSIVE clustering for maximum consolidation.

        This method is even more aggressive than the original:
        - Allows swapping Top 5 activities if they're the ONLY activity on an excess day
        - Tries cross-troop swaps more aggressively  
        - Allows moving activities even if it creates temporary constraint issues
        - NEW: Smart activity prioritization to protect high-value activities
        - NEW: Better cross-day consolidation logic
        """
        from ...models import Day
        import math

        ultra_moves = 0

        # Target the same cluster areas used by official regression scoring.
        cluster_areas = self._get_authoritative_gap_area_map()

        for area, activities in cluster_areas.items():
            if not activities:
                continue

            area_entries = [e for e in self.schedule.entries if e.activity.name in activities]
            if not area_entries:
                continue

            # Count distribution
            day_counts = {}
            for entry in area_entries:
                day_counts[entry.time_slot.day] = day_counts.get(entry.time_slot.day, 0) + 1

            # Calculate if we still have excess days after normal consolidation
            num_activities = len(area_entries)
            min_days = math.ceil(num_activities / 3.0)
            current_days = len(day_counts)
            excess_days = max(0, current_days - min_days)

            if excess_days <= 0:
                continue

            print(f"    [Ultra Cluster] {area}: {excess_days} excess days to eliminate")

            # Sort days by activity count: most populated first (best days to keep)
            sorted_by_count = sorted(day_counts.items(), key=lambda x: -x[1])
            best_days = [d for d, _ in sorted_by_count[:min_days]]
            excess_day_list = [d for d, _ in sorted_by_count[min_days:]]

            # Move FROM excess days (sparse) TO best days (dense)
            for source_day in excess_day_list:
                for target_day in best_days:
                    if source_day == target_day:
                        continue

                    # Find activities on source day that can move to target day
                    source_entries = [e for e in area_entries if e.time_slot.day == source_day]
                    target_entries = [e for e in area_entries if e.time_slot.day == target_day]

                    if len(target_entries) >= 3:  # Target day is full
                        continue

                    # Try to move activities from source to target
                    for source_entry in source_entries[:]:  # Copy list
                        if len(target_entries) >= 3:  # Target day became full
                            break

                        if self._is_pair_protected_delta(source_entry):
                            continue

                        # Skip Top 5 activities - do not displace for clustering
                        rank = source_entry.troop.get_priority(source_entry.activity.name)
                        if rank < 5:  # 0-4 = Top 5 (0-indexed)
                            continue

                        # Check if we can move this activity
                        for slot_num in range(1, 4):
                            # Find the target time slot
                            target_time_slot = None
                            for ts in self.time_slots:
                                if ts.day == target_day and ts.slot_number == slot_num:
                                    target_time_slot = ts
                                    break

                            if not target_time_slot:
                                continue
                            if not self._family_policy_allows_day(
                                source_entry.activity.name,
                                target_day,
                                strict=True,
                            ):
                                continue

                            # Check troop free, activity available, AND full constraint check
                            # (avoid creating violations that could cascade to Top 5 issues)
                            if (self.schedule.is_troop_free(target_time_slot, source_entry.troop)
                                and self.schedule.is_activity_available(target_time_slot, source_entry.activity, source_entry.troop)
                                and self._can_schedule(source_entry.troop, source_entry.activity, target_time_slot, target_day, relax_constraints=False)):

                                # ENHANCED: Prioritize moving lower priority activities
                                troop_priority = source_entry.troop.get_priority(source_entry.activity.name)

                                # Move the activity (rollback on failure)
                                old_slot = source_entry.time_slot
                                self.schedule.remove_entry(source_entry)
                                if not self.schedule.add_entry(target_time_slot, source_entry.activity, source_entry.troop):
                                    self.schedule.add_entry(old_slot, source_entry.activity, source_entry.troop)
                                    continue

                                ultra_moves += 1
                                print(f"      [Ultra Cluster] {source_entry.troop.name}: {source_entry.activity.name} {old_slot.day.name[:3]}->{target_day.name[:3]} (Priority: {troop_priority})")

                                # Update tracking - refresh from schedule since entry was replaced
                                area_entries = [e for e in self.schedule.entries if e.activity.name in activities]
                                source_entries = [e for e in area_entries if e.time_slot.day == source_day]
                                target_entries = [e for e in area_entries if e.time_slot.day == target_day]
                                break

                    # Recalculate day counts after moves
                    area_entries = [e for e in self.schedule.entries if e.activity.name in activities]
                    day_counts = {}
                    for entry in area_entries:
                        day_counts[entry.time_slot.day] = day_counts.get(entry.time_slot.day, 0) + 1

                    # Check if we've eliminated enough excess days
                    current_days = len(day_counts)
                    excess_days = max(0, current_days - min_days)
                    if excess_days <= 0:
                        break

                if excess_days <= 0:
                    break

        if ultra_moves > 0:
            print(f"    [Ultra Cluster] Made {ultra_moves} ultra-aggressive clustering moves")

        return ultra_moves


    def _targeted_cluster_offender_swaps(self, protected_activities, max_swaps: int = 12) -> int:
        """
        Move the entries that directly cause official clustering penalties.

        Targets:
        - activities on excess area days, and
        - slot-1/slot-3 edge activities in official 1,-,3 area gaps.

        Only same-troop strict swaps are committed, so every activity remains
        scheduled and the move must pass normal placement constraints.
        """
        import math
        import time

        if not hasattr(self, "_try_strict_swap_same_troop"):
            return 0

        cluster_areas = self._get_authoritative_gap_area_map()
        activity_to_area = {
            activity_name: area_name
            for area_name, activities in cluster_areas.items()
            for activity_name in activities
        }
        started = time.monotonic()
        time_budget_s = float(os.getenv("CLUSTER_OFFENDER_SWAP_BUDGET_SECONDS", "2.0"))
        moves = 0

        def is_single_slot_entry(entry) -> bool:
            effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
            return int(effective_slots + 0.5) == 1

        def is_swappable(entry) -> bool:
            return (
                entry.activity.name not in protected_activities
                and entry.activity.name not in self.THREE_HOUR_ACTIVITIES
                and is_single_slot_entry(entry)
                and not self._is_pair_protected_delta(entry)
            )

        def beach_slot2_violation(activity, slot) -> bool:
            return (
                activity.name in self.BEACH_SLOT_ACTIVITIES
                and slot.day != Day.THURSDAY
                and slot.slot_number == 2
            )

        def collect_offenders():
            offenders = []

            for area_name, area_activities in cluster_areas.items():
                area_entries = [
                    e for e in self.schedule.entries
                    if e.activity.name in area_activities and is_swappable(e)
                ]
                if not area_entries:
                    continue

                day_counts = defaultdict(int)
                for entry in area_entries:
                    day_counts[entry.time_slot.day] += 1

                required_days = math.ceil(len(area_entries) / 3.0)
                if len(day_counts) > required_days:
                    target_days = {
                        day for day, _ in sorted(
                            day_counts.items(),
                            key=lambda item: (-item[1], self._day_clustering_sort_key(item[0])),
                        )[:required_days]
                    }
                    for entry in area_entries:
                        if entry.time_slot.day not in target_days:
                            offenders.append((
                                entry,
                                area_name,
                                "excess-day",
                                day_counts[entry.time_slot.day],
                            ))

                # Official 1,-,3 area gaps: either edge can move to slot 2 or
                # away to a better clustered day, reducing the gap.
                for day in (Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY):
                    day_entries = [
                        e for e in self.schedule.entries
                        if e.time_slot.day == day and e.activity.name in area_activities
                    ]
                    has_1 = any(e.time_slot.slot_number == 1 for e in day_entries)
                    has_2 = any(e.time_slot.slot_number == 2 for e in day_entries)
                    has_3 = any(e.time_slot.slot_number == 3 for e in day_entries)
                    if not (has_1 and has_3 and not has_2):
                        continue
                    for entry in day_entries:
                        if entry.time_slot.slot_number in {1, 3} and is_swappable(entry):
                            offenders.append((entry, area_name, "gap-edge", 0))

            # Lower-value, sparser-day offenders are safest and most likely to help.
            unique = {}
            for entry, area_name, reason, sparsity in offenders:
                key = (entry.troop.name, entry.activity.name, entry.time_slot.day, entry.time_slot.slot_number)
                existing = unique.get(key)
                if existing is None or reason == "gap-edge":
                    unique[key] = (entry, area_name, reason, sparsity)

            return sorted(
                unique.values(),
                key=lambda item: (
                    item[2] != "gap-edge",
                    item[3],
                    item[0].troop.get_priority(item[0].activity.name) < 5,
                    -item[0].troop.get_priority(item[0].activity.name),
                    item[0].troop.name,
                ),
            )

        while moves < max_swaps and time.monotonic() - started <= time_budget_s:
            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            if baseline_non_exempt > 0:
                break
            baseline_top10 = self._count_top10_in_schedule()
            baseline_metrics = self._schedule_quality_snapshot()
            if baseline_metrics["excess"] <= 0 and baseline_metrics["gaps"] <= 0:
                break

            best_state = None
            best_metrics = None
            best_note = None

            for offender, area_name, reason, _ in collect_offenders():
                if offender not in self.schedule.entries:
                    continue
                if time.monotonic() - started > time_budget_s:
                    break

                troop = offender.troop
                area_activities = cluster_areas.get(area_name, set())
                troop_entries = [
                    e for e in self.schedule.entries
                    if e.troop == troop and e != offender and is_swappable(e)
                ]

                def candidate_key(entry):
                    target_area_count = sum(
                        1 for e in self.schedule.entries
                        if e.activity.name in area_activities and e.time_slot.day == entry.time_slot.day
                    )
                    fills_same_day_gap = (
                        reason == "gap-edge"
                        and entry.time_slot.day == offender.time_slot.day
                        and entry.time_slot.slot_number == 2
                    )
                    target_area = activity_to_area.get(entry.activity.name)
                    return (
                        not fills_same_day_gap,
                        -target_area_count,
                        target_area == area_name,
                        entry.troop.get_priority(entry.activity.name) < 5,
                        -entry.troop.get_priority(entry.activity.name),
                    )

                for candidate in sorted(troop_entries, key=candidate_key):
                    # Same-day swaps only help when moving a gap edge into slot 2.
                    if candidate.time_slot.day == offender.time_slot.day:
                        if not (
                            reason == "gap-edge"
                            and candidate.time_slot.slot_number == 2
                        ):
                            continue

                    if beach_slot2_violation(offender.activity, candidate.time_slot):
                        continue
                    if beach_slot2_violation(candidate.activity, offender.time_slot):
                        continue
                    if not self._family_policy_allows_day(
                        offender.activity.name,
                        candidate.time_slot.day,
                        strict=True,
                    ):
                        continue
                    if not self._family_policy_allows_day(
                        candidate.activity.name,
                        offender.time_slot.day,
                        strict=True,
                    ):
                        continue

                    snapshot = self._snapshot_scheduler_state()
                    if not self._try_strict_swap_same_troop(offender, candidate):
                        self._restore_scheduler_state(snapshot)
                        continue

                    after_non_exempt, _ = self._count_non_exempt_top5_misses()
                    after_top10 = self._count_top10_in_schedule()
                    after_metrics = self._schedule_quality_snapshot()
                    improved = (
                        after_metrics["excess"] < baseline_metrics["excess"]
                        or after_metrics["gaps"] < baseline_metrics["gaps"]
                    )
                    if (
                        after_non_exempt <= baseline_non_exempt
                        and after_top10 >= baseline_top10
                        and improved
                        and self._is_quality_snapshot_improvement(baseline_metrics, after_metrics)
                        and (
                            best_metrics is None
                            or after_metrics["composite"] < best_metrics["composite"]
                        )
                    ):
                        best_state = self._snapshot_scheduler_state()
                        best_metrics = after_metrics
                        best_note = (
                            troop.name,
                            offender.activity.name,
                            offender.time_slot,
                            candidate.activity.name,
                            candidate.time_slot,
                            reason,
                        )

                    self._restore_scheduler_state(snapshot)

            if best_state is None:
                break

            self._restore_scheduler_state(best_state)
            moves += 1
            troop_name, offender_name, offender_slot, candidate_name, candidate_slot, reason = best_note
            print(
                f"    [Cluster Offender Swap] {troop_name}: {offender_name} "
                f"{offender_slot.day.name[:3]}-{offender_slot.slot_number} <-> "
                f"{candidate_name} {candidate_slot.day.name[:3]}-{candidate_slot.slot_number} "
                f"({reason}; excess {baseline_metrics['excess']}->{best_metrics['excess']}, "
                f"gaps {baseline_metrics['gaps']}->{best_metrics['gaps']})"
            )

        if moves == 0:
            print("    [Cluster Offender Swap] No guarded offender swaps found")
        return moves


    def _aggressive_excess_day_reduction_swaps(self):
        """
        Find same-troop swaps that specifically reduce official clustering penalties.

        The original implementation compared two entries from the same cluster
        area, so swapping them could not change area day counts. This pass
        instead swaps different single-slot activities for the same troop, then
        accepts the candidate only when the authoritative quality snapshot
        improves without increasing non-exempt Top-5 misses.
        """
        import time

        print("    [Excess Day Reduction] Starting guarded cross-area swaps...")

        if not hasattr(self, "_try_strict_swap_same_troop"):
            print("    [Excess Day Reduction] Skipped - strict swap helper unavailable")
            return 0

        cluster_areas = self._get_authoritative_gap_area_map()
        activity_to_area = {
            activity_name: area_name
            for area_name, activities in cluster_areas.items()
            for activity_name in activities
        }
        protected = set(self.NON_DISPLACEABLE_ACTIVITIES) | {
            "Sailing",
            "Tamarac Wildlife Refuge",
            "Itasca State Park",
            "Back of the Moon",
        }

        swaps_made = 0
        max_swaps = min(max(6, len(self.troops)), 18)
        candidate_cap = max(80, len(self.troops) * 40)
        time_budget_s = float(os.getenv("EXCESS_DAY_SWAP_BUDGET_SECONDS", "2.0"))
        started = time.monotonic()

        swaps_made += self._targeted_cluster_offender_swaps(
            protected,
            max_swaps=max(4, max_swaps // 2),
        )

        def _try_relaxed_swap_same_troop(entry_a, entry_b) -> bool:
            if entry_a.troop != entry_b.troop:
                return False
            if entry_a.activity.slots > 1 or entry_b.activity.slots > 1:
                return False
            troop = entry_a.troop
            slot_a = entry_a.time_slot
            slot_b = entry_b.time_slot
            act_a = entry_a.activity
            act_b = entry_b.activity

            self.schedule.remove_entry(entry_a)
            self.schedule.remove_entry(entry_b)
            if not self._can_schedule(troop, act_a, slot_b, slot_b.day, relax_constraints=True):
                return False
            if not self._can_schedule(troop, act_b, slot_a, slot_a.day, relax_constraints=True):
                return False
            return (
                self.schedule.add_entry(slot_b, act_a, troop)
                and self.schedule.add_entry(slot_a, act_b, troop)
            )

        improved = True
        while improved and swaps_made < max_swaps:
            if time.monotonic() - started > time_budget_s:
                break

            improved = False
            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            if baseline_non_exempt > 0:
                break
            baseline_top10 = self._count_top10_in_schedule()
            baseline_metrics = self._schedule_quality_snapshot()
            if baseline_metrics["excess"] <= 0 and baseline_metrics["gaps"] <= 0:
                break

            best_state = None
            best_metrics = None
            best_note = None
            candidate_checks = 0

            for troop in sorted(self.troops, key=lambda t: t.name):
                if time.monotonic() - started > time_budget_s:
                    break

                troop_entries = [
                    e for e in self.schedule.entries
                    if e.troop == troop
                    and e.activity.slots <= 1
                    and e.activity.name not in protected
                    and not self._is_pair_protected_delta(e)
                ]
                cluster_entries = [
                    e for e in troop_entries
                    if e.activity.name in activity_to_area
                ]
                if not cluster_entries:
                    continue

                for cluster_entry in cluster_entries:
                    if candidate_checks >= candidate_cap:
                        break
                    area_a = activity_to_area.get(cluster_entry.activity.name)
                    for other in troop_entries:
                        if candidate_checks >= candidate_cap:
                            break
                        if other == cluster_entry:
                            continue
                        if other.time_slot.day == cluster_entry.time_slot.day:
                            continue
                        if self._is_pair_protected_delta(other):
                            continue

                        area_b = activity_to_area.get(other.activity.name)
                        if area_b == area_a:
                            continue
                        if not self._family_policy_allows_day(
                            cluster_entry.activity.name,
                            other.time_slot.day,
                            strict=True,
                        ):
                            continue
                        if not self._family_policy_allows_day(
                            other.activity.name,
                            cluster_entry.time_slot.day,
                            strict=True,
                        ):
                            continue

                        candidate_checks += 1
                        trial_snapshot = self._snapshot_scheduler_state()
                        if not self._try_strict_swap_same_troop(cluster_entry, other):
                            self._restore_scheduler_state(trial_snapshot)
                            trial_snapshot = self._snapshot_scheduler_state()
                            if not _try_relaxed_swap_same_troop(cluster_entry, other):
                                self._restore_scheduler_state(trial_snapshot)
                                continue

                        after_non_exempt, _ = self._count_non_exempt_top5_misses()
                        after_top10 = self._count_top10_in_schedule()
                        after_metrics = self._schedule_quality_snapshot()
                        excess_improved = after_metrics["excess"] < baseline_metrics["excess"]
                        if (
                            after_non_exempt <= baseline_non_exempt
                            and after_top10 >= baseline_top10
                            and excess_improved
                            and after_metrics["gaps"] <= baseline_metrics["gaps"]
                            and (
                                best_metrics is None
                                or after_metrics["composite"] < best_metrics["composite"]
                                or (
                                    after_metrics["excess"] < best_metrics["excess"]
                                    and after_metrics["gaps"] <= best_metrics["gaps"]
                                )
                            )
                        ):
                            best_state = self._snapshot_scheduler_state()
                            best_metrics = after_metrics
                            best_note = (
                                troop.name,
                                cluster_entry.activity.name,
                                cluster_entry.time_slot,
                                other.activity.name,
                                other.time_slot,
                            )

                        self._restore_scheduler_state(trial_snapshot)

                    if candidate_checks >= candidate_cap:
                        break
                if candidate_checks >= candidate_cap:
                    break

            if best_state:
                self._restore_scheduler_state(best_state)
                swaps_made += 1
                improved = True
                troop_name, act_a, slot_a, act_b, slot_b = best_note
                print(
                    f"    [Excess Day Reduction] {troop_name}: "
                    f"{act_a} {slot_a.day.name[:3]}-{slot_a.slot_number} <-> "
                    f"{act_b} {slot_b.day.name[:3]}-{slot_b.slot_number} "
                    f"(excess {baseline_metrics['excess']}->{best_metrics['excess']}, "
                    f"gaps {baseline_metrics['gaps']}->{best_metrics['gaps']})"
                )

        if swaps_made == 0:
            print("    [Excess Day Reduction] No guarded improving swaps found")
        return swaps_made


    def _reduce_constraint_violations(self):
        """
        ENHANCED: Comprehensive constraint violation reduction with iterative fixing.
        Runs multiple passes until no more violations can be fixed.
        """
        print("    [Constraint Fix] Starting ENHANCED comprehensive violation reduction...")

        total_fixed = 0
        max_iterations = 5  # Prevent infinite loops

        for iteration in range(max_iterations):
            print(f"      [Iteration {iteration + 1}]")
            iteration_fixed = 0

            # Fix accuracy activity conflicts
            iteration_fixed += self._fix_accuracy_conflicts()

            # Fix wet-dry-wet patterns
            iteration_fixed += self._fix_wet_dry_wet_patterns()

            # Fix same area same day conflicts
            iteration_fixed += self._fix_same_area_same_day_conflicts()

            # Fix beach slot violations
            iteration_fixed += self._fix_beach_slot_conflicts()

            # Fix capacity violations
            iteration_fixed += self._fix_capacity_violations()

            # NEW: Fix overlapping activities for same troop
            iteration_fixed += self._fix_overlapping_activities()

            # NEW: Fix exclusive area conflicts
            iteration_fixed += self._fix_exclusive_area_conflicts()

            print(f"      [Iteration {iteration + 1}] Fixed {iteration_fixed} violations")

            total_fixed += iteration_fixed

            # If no violations fixed in this iteration, we're done
            if iteration_fixed == 0:
                print(f"      [Complete] No more violations fixable after {iteration + 1} iterations")
                break

        print(f"    [Constraint Fix] Total violations fixed: {total_fixed}")
        return total_fixed


    def _fix_accuracy_conflicts(self):
        """Fix conflicts where troops have multiple accuracy activities scheduled."""
        print("      [Accuracy] Checking accuracy activity conflicts...")
        fixed = 0

        accuracy_activities = set(self.ACCURACY_ACTIVITIES)

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)
            accuracy_entries = [e for e in entries if e.activity.name in accuracy_activities]

            if len(accuracy_entries) > 1:
                print(f"        [Accuracy] {troop.name}: {len(accuracy_entries)} accuracy activities - fixing...")
                # Keep the highest priority accuracy activity, replace others
                accuracy_entries.sort(key=lambda e: troop.get_priority(e.activity.name))
                for entry in accuracy_entries[1:]:  # Keep first, replace others
                    # Top-10 stability guard: this is a soft fix, so do not sacrifice Top 10.
                    if troop.get_priority(entry.activity.name) < 10:
                        continue
                    # Find a suitable replacement activity
                    replacement = self._find_suitable_replacement(entry, troop, accuracy_activities)
                    if replacement:
                        # Validate replacement before mutation; rollback-safe apply.
                        if self._can_schedule(troop, replacement, entry.time_slot, entry.time_slot.day, relax_constraints=False):
                            self.schedule.remove_entry(entry)
                            if self.schedule.add_entry(entry.time_slot, replacement, troop):
                                fixed += 1
                                print(f"        [Accuracy] Replaced {entry.activity.name} with {replacement.name}")
                            else:
                                self.schedule.add_entry(entry.time_slot, entry.activity, troop)

        return fixed


    def _fix_wet_dry_wet_patterns(self):
        """Fix wet-dry-wet patterns in troop schedules."""
        print("      [Wet-Dry] Checking wet-dry-wet patterns...")
        fixed = 0

        # SKULL-driven wet activity set (authoritative).
        wet_activities = set(self.WET_ACTIVITIES)

        for troop in self.troops:
            for day in Day:
                # Get all entries for this troop and day
                troop_entries = self.schedule.get_troop_schedule(troop)
                day_entries = [e for e in troop_entries if e.time_slot.day == day]

                if len(day_entries) >= 3:
                    # Check for wet-dry-wet pattern
                    # Sort by slot number
                    day_entries.sort(key=lambda e: e.time_slot.slot_number)
                    pattern = []
                    for entry in day_entries:
                        is_wet = entry.activity.name in wet_activities
                        pattern.append(is_wet)

                    # Look for wet-dry-wet pattern
                    for i in range(len(pattern) - 2):
                        if pattern[i] and not pattern[i+1] and pattern[i+2]:
                            # Found wet-dry-wet, fix the middle dry activity
                            middle_entry = day_entries[i+1]
                            if middle_entry.activity.name not in wet_activities:
                                # Top-10 stability guard: this is a soft fix, so do not sacrifice Top 10.
                                if troop.get_priority(middle_entry.activity.name) < 10:
                                    continue
                                # Try to find a wet replacement
                                wet_replacement = self._find_wet_replacement(middle_entry, troop)
                                if wet_replacement:
                                    # Find the time slot object
                                    time_slot = None
                                    for ts in self.time_slots:
                                        if ts.day == day and ts.slot_number == middle_entry.time_slot.slot_number:
                                            time_slot = ts
                                            break
                                    if time_slot:
                                        if self._can_schedule(
                                            troop, wet_replacement, time_slot, day, relax_constraints=False
                                        ):
                                            self.schedule.remove_entry(middle_entry)
                                            if self.schedule.add_entry(time_slot, wet_replacement, troop):
                                                fixed += 1
                                                print(
                                                    f"        [Wet-Dry] Fixed {troop.name} {day.name}: "
                                                    f"{middle_entry.activity.name} -> {wet_replacement.name}"
                                                )
                                                break
                                            # Roll back on failed insertion to avoid data loss/gaps.
                                            self.schedule.add_entry(time_slot, middle_entry.activity, troop)

        return fixed


    def _fix_same_area_same_day_conflicts(self):
        """
        Fix conflicts where a troop has multiple activities from the same exclusive area on the same day.

        FIX 2026-01-30: Added missing method that was called but not implemented.
        """
        # EXCLUSIVE_AREAS already at module scope

        print("      [Same Area] Checking same area same day conflicts...")
        fixed = 0

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)

            # Group entries by day
            for day in Day:
                day_entries = [e for e in entries if e.time_slot.day == day]
                if len(day_entries) < 2:
                    continue

                # Check for same area conflicts
                for area, activities in EXCLUSIVE_AREAS.items():
                    area_entries = [e for e in day_entries if e.activity.name in activities]

                    if len(area_entries) > 1:
                        # Conflict: more than one activity from same area on same day
                        # Keep the highest priority one, move others
                        area_entries.sort(key=lambda e: troop.get_priority(e.activity.name))

                        for entry in area_entries[1:]:
                            # Try to move to a different day
                            moved = False
                            for alt_day in Day:
                                if alt_day == day:
                                    continue
                                for slot_num in [1, 2, 3]:
                                    alt_slot = next((s for s in self.time_slots 
                                                   if s.day == alt_day and s.slot_number == slot_num), None)
                                    if alt_slot and self.schedule.is_troop_free(alt_slot, troop):
                                        if self._can_schedule(troop, entry.activity, alt_slot, alt_day):
                                            self.schedule.remove_entry(entry)
                                            self.schedule.add_entry(alt_slot, entry.activity, troop)
                                            fixed += 1
                                            print(f"        [Same Area] Moved {troop.name} {entry.activity.name} to {alt_day.name}")
                                            moved = True
                                            break
                                if moved:
                                    break

        return fixed


    def _fix_beach_slot_violations(self):
        """
        ENHANCED: Fix Beach Slot Rule violations with comprehensive swapping logic.
        Beach activities only allowed in Slot 1 or 3 (Slot 2 only on Thursday).
        """
        # Use config-driven beach slot list; Sailing has its own slot-2 exception.
        beach_activities = set(self.BEACH_SLOT_ACTIVITIES)

        fixed = 0  # FIX 2026-01-30: Initialize fixed counter

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)

            for entry in entries:
                if entry.activity.name in beach_activities:
                    day = entry.time_slot.day
                    slot = entry.time_slot.slot_number
                    is_multislot_continuation = (
                        self.schedule._get_effective_slots(entry.activity, troop) > 1.0
                        and any(
                            e.troop == troop
                            and e.activity.name == entry.activity.name
                            and e.time_slot.day == day
                            and e.time_slot.slot_number == slot - 1
                            for e in entries
                        )
                    )

                    # Check if this is a violation (beach activity in slot 2 on non-Thursday)
                    if slot == 2 and day != Day.THURSDAY and not is_multislot_continuation:
                        print(f"        [Beach] Found violation: {troop.name} {entry.activity.name} in {day.name} Slot 2")

                        # ENHANCED: Try multiple strategies to fix this violation

                        # Strategy 1: Swap into preferred start slots on same day.
                        target_slots = [1] if entry.activity.slots > 1 else [1, 3]
                        swap_found = False
                        for target_slot in target_slots:
                            target_entry = None
                            for e in entries:
                                if e.time_slot.day == day and e.time_slot.slot_number == target_slot:
                                    target_entry = e
                                    break

                            if target_entry and target_entry.activity.name not in beach_activities:
                                # Check if swap would maintain constraints
                                if self._would_swap_maintain_constraints(entry, target_entry):
                                    # Perform the swap using schedule methods
                                    self.schedule.remove_entry(entry)
                                    self.schedule.remove_entry(target_entry)

                                    # Create new entries with swapped activities
                                    self.schedule.add_entry(entry.time_slot, target_entry.activity, troop)
                                    self.schedule.add_entry(target_entry.time_slot, entry.activity, troop)

                                    fixed += 1
                                    print(f"        [Beach] Swapped {entry.activity.name} (Slot 2) with {target_entry.activity.name} (Slot {target_slot})")
                                    swap_found = True
                                    break

                        if swap_found:
                            continue

                        # Strategy 2: Move to different day if no same-day swap possible
                        moved_cross_day = False
                        for alt_day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
                            if alt_day == day:
                                continue

                            alt_slots = [1] if entry.activity.slots > 1 else [1, 3]
                            for alt_slot in alt_slots:
                                # Find the time slot object
                                time_slot = None
                                for ts in self.time_slots:
                                    if ts.day == alt_day and ts.slot_number == alt_slot:
                                        time_slot = ts
                                        break

                                if time_slot and self.schedule.is_troop_free(time_slot, troop):
                                    if self._can_schedule(troop, entry.activity, time_slot, alt_day):
                                        # Move the activity
                                        self.schedule.remove_entry(entry)
                                        self.schedule.add_entry(time_slot, entry.activity, troop)
                                        fixed += 1
                                        moved_cross_day = True
                                        print(f"        [Beach] Moved {entry.activity.name} to {alt_day.name} Slot {alt_slot}")
                                        break
                            if moved_cross_day:
                                break

        print(f"      [Beach] Fixed {fixed} beach slot violations")
        return fixed


    def _would_break_multislot_continuity(self, entry, day_entries):
        """Check if removing this entry would break multi-slot activity continuity."""
        # Get all entries for this activity on this day
        activity_entries = [e for e in day_entries if e.activity.name == entry.activity.name]

        if len(activity_entries) <= 1:
            return False  # Single entry, no continuity to break

        # Sort by slot number
        activity_entries.sort(key=lambda e: e.time_slot.slot_number)

        # Check if this entry is in the middle of a sequence
        entry_slot = entry.time_slot.slot_number
        slots = [e.time_slot.slot_number for e in activity_entries]

        # Find the position of this entry in the sequence
        if entry_slot not in slots:
            return False

        position = slots.index(entry_slot)

        # If this is not the first or last entry, removing it would break continuity
        return 0 < position < len(slots) - 1


    def _fix_beach_slot_conflicts(self):
        """
        ENHANCED: Fix beach slot rule violations with comprehensive swapping logic.
        Beach activities only allowed in Slot 1 or 3 (Slot 2 only on Thursday).
        Now includes cross-day moving when same-day swaps aren't possible.
        """
        print("      [Beach] Fixing beach slot violations...")
        fixed = 0

        # Use the configured beach-slot list plus Sailing's documented exception path.
        beach_activities = set(self.BEACH_SLOT_ACTIVITIES) | {"Sailing"}

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)

            for entry in entries:
                if entry.activity.name in beach_activities:
                    day = entry.time_slot.day
                    slot = entry.time_slot.slot_number
                    is_multislot_continuation = (
                        self.schedule._get_effective_slots(entry.activity, troop) > 1.0
                        and any(
                            e.troop == troop
                            and e.activity.name == entry.activity.name
                            and e.time_slot.day == day
                            and e.time_slot.slot_number == slot - 1
                            for e in entries
                        )
                    )

                    # Check if this is a violation (beach activity in slot 2 on non-Thursday)
                    if slot == 2 and day != Day.THURSDAY and not is_multislot_continuation:
                        print(f"        [Beach] Found violation: {troop.name} {entry.activity.name} in {day.name} Slot 2")

                        # ENHANCED: Try multiple strategies to fix this violation

                        # Strategy 1: Swap with slot 1 or 3 in same day
                        swap_found = False
                        for target_slot in [1, 3]:
                            target_entry = None
                            for e in entries:
                                if e.time_slot.day == day and e.time_slot.slot_number == target_slot:
                                    target_entry = e
                                    break

                            if target_entry and target_entry.activity.name not in beach_activities:
                                # Check if swap would maintain constraints
                                if self._would_swap_maintain_constraints(entry, target_entry):
                                    # Perform the swap using schedule methods
                                    self.schedule.remove_entry(entry)
                                    self.schedule.remove_entry(target_entry)

                                    # Create new entries with swapped activities
                                    self.schedule.add_entry(entry.time_slot, target_entry.activity, troop)
                                    self.schedule.add_entry(target_entry.time_slot, entry.activity, troop)

                                    fixed += 1
                                    print(f"        [Beach] Swapped {entry.activity.name} (Slot 2) with {target_entry.activity.name} (Slot {target_slot})")
                                    swap_found = True
                                    break

                        if swap_found:
                            continue

                        # Strategy 2: Move to different day if no same-day swap possible
                        for alt_day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
                            if alt_day == day:
                                continue

                            for alt_slot in [1, 3]:
                                # Find the time slot object
                                time_slot = None
                                for ts in self.time_slots:
                                    if ts.day == alt_day and ts.slot_number == alt_slot:
                                        time_slot = ts
                                        break

                                if time_slot and self.schedule.is_troop_free(time_slot, troop):
                                    if self._can_schedule(troop, entry.activity, time_slot, alt_day):
                                        # Move the activity
                                        self.schedule.remove_entry(entry)
                                        self.schedule.add_entry(time_slot, entry.activity, troop)
                                        fixed += 1
                                        print(f"        [Beach] Moved {entry.activity.name} to {alt_day.name} Slot {alt_slot}")
                                        break
                            if fixed > 0:
                                break

        print(f"      [Beach] Fixed {fixed} beach slot violations")
        return fixed


    def _would_swap_maintain_constraints(self, entry1, entry2):
        """Check if swapping two entries would maintain all constraints."""
        troop1 = entry1.troop
        troop2 = entry2.troop

        # If same troop, check if activities can be in each other's slots
        if troop1 == troop2:
            return (self._can_schedule(troop1, entry1.activity, entry2.time_slot, entry2.time_slot.day) and
                   self._can_schedule(troop1, entry2.activity, entry1.time_slot, entry1.time_slot.day))

        # Different troops - check each can do the other's activity
        return (self._can_schedule(troop1, entry2.activity, entry1.time_slot, entry1.time_slot.day) and
               self._can_schedule(troop2, entry1.activity, entry2.time_slot, entry2.time_slot.day))


    def _fix_capacity_violations(self):
        """Fix capacity constraint violations."""
        print("      [Capacity] Checking capacity violations...")
        fixed = 0

        # Check for activities that exceed capacity per slot
        for day in Day:
            for slot in range(1, 4):
                activity_counts = {}
                # Find the time slot object
                time_slot = None
                for ts in self.time_slots:
                    if ts.day == day and ts.slot_number == slot:
                        time_slot = ts
                        break

                if not time_slot:
                    continue

                entries = self.schedule.get_slot_activities(time_slot)

                for entry in entries:
                    activity_name = entry.activity.name
                    if activity_name not in activity_counts:
                        activity_counts[activity_name] = []
                    activity_counts[activity_name].append(entry)

                # Check for overcapacity (most activities max 2 troops per slot)
                for activity_name, activity_entries in activity_counts.items():
                    if len(activity_entries) > 2 and activity_name not in ["Super Troop", "Reflection"]:
                        # Too many troops in same activity - move some
                        excess_entries = activity_entries[2:]  # Keep first 2
                        for entry in excess_entries:
                            replacement = self._find_capacity_replacement(entry, day, slot)
                            if replacement:
                                self.schedule.remove_entry(entry)
                                new_entry = ScheduleEntry(time_slot=time_slot, activity= replacement, troop= entry.troop)
                                self.schedule.add_entry(time_slot, replacement, entry.troop)
                                fixed += 1
                                print(f"        [Capacity] Moved {entry.troop.name} from {activity_name} to {replacement.name}")

        return fixed


    def _fix_overlapping_activities(self):
        """Fix overlapping activities for the same troop in the same time slot."""
        print("      [Overlap] Checking overlapping activities...")
        fixed = 0

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)

            # Group entries by time slot
            slot_entries = {}
            for entry in entries:
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                if slot_key not in slot_entries:
                    slot_entries[slot_key] = []
                slot_entries[slot_key].append(entry)

            # Find overlaps (more than 1 activity in same slot)
            for (day, slot), overlapping_entries in slot_entries.items():
                if len(overlapping_entries) > 1:
                    print(f"        [Overlap] {troop.name} has {len(overlapping_entries)} activities in {day.name}-{slot}")

                    # Keep the highest priority activity, move others
                    overlapping_entries.sort(key=lambda e: troop.get_priority(e.activity.name))
                    keep_entry = overlapping_entries[0]
                    move_entries = overlapping_entries[1:]

                    for move_entry in move_entries:
                        # Find an alternative time slot
                        alternative_found = False
                        for alt_day in Day:
                            for alt_slot in range(1, 4):
                                if alt_day == day and alt_slot == slot:
                                    continue  # Skip same slot

                                # Find the time slot object
                                alt_time_slot = None
                                for ts in self.time_slots:
                                    if ts.day == alt_day and ts.slot_number == alt_slot:
                                        alt_time_slot = ts
                                        break

                                if alt_time_slot and self.schedule.is_troop_free(alt_time_slot, troop):
                                    # Check if activity is available
                                    if self.schedule.is_activity_available(alt_time_slot, move_entry.activity, troop):
                                        # Move the entry
                                        self.schedule.remove_entry(move_entry)
                                        self.schedule.add_entry(alt_time_slot, move_entry.activity, troop)
                                        fixed += 1
                                        print(f"        [Overlap] Moved {move_entry.activity.name} to {alt_day.name}-{alt_slot}")
                                        alternative_found = True
                                        break

                            if alternative_found:
                                break

                        if not alternative_found:
                            # Couldn't move, try to replace with a different activity
                            replacement = self._find_suitable_replacement(move_entry, troop, {move_entry.activity.name})
                            if replacement:
                                self.schedule.remove_entry(move_entry)
                                # Find the original time slot object
                                orig_time_slot = None
                                for ts in self.time_slots:
                                    if ts.day == day and ts.slot_number == slot:
                                        orig_time_slot = ts
                                        break
                                if orig_time_slot:
                                    self.schedule.add_entry(orig_time_slot, replacement, troop)
                                    fixed += 1
                                    print(f"        [Overlap] Replaced {move_entry.activity.name} with {replacement.name}")

        return fixed


    def _fix_exclusive_area_conflicts(self):
        """Fix conflicts where multiple troops are in exclusive areas simultaneously."""
        print("      [Exclusive] Checking exclusive area conflicts...")
        fixed = 0

        # EXCLUSIVE_AREAS already at module scope

        for area, activities in EXCLUSIVE_AREAS.items():
            # Check each time slot for exclusive area conflicts
            for day in Day:
                for slot_num in range(1, 4):
                    # Find the time slot object
                    time_slot = None
                    for ts in self.time_slots:
                        if ts.day == day and ts.slot_number == slot_num:
                            time_slot = ts
                            break

                    if not time_slot:
                        continue

                    entries = self.schedule.get_slot_activities(time_slot)
                    area_entries = [e for e in entries if e.activity.name in activities]

                    if len(area_entries) > 1:
                        print(f"        [Exclusive] {area} has {len(area_entries)} troops in {day.name}-{slot_num}")

                        # Keep the highest priority troop(s), move others
                        area_entries.sort(key=lambda e: e.troop.get_priority(e.activity.name))

                        # Move excess entries
                        for move_entry in area_entries[1:]:  # Keep first, move others
                            # Find alternative time slot
                            for alt_day in Day:
                                for alt_slot in range(1, 4):
                                    if alt_day == day and alt_slot == slot_num:
                                        continue

                                    # Find the alternative time slot object
                                    alt_time_slot = None
                                    for ts in self.time_slots:
                                        if ts.day == alt_day and ts.slot_number == alt_slot:
                                            alt_time_slot = ts
                                            break

                                    if alt_time_slot:
                                        # Check if troop is free and activity is available
                                        if (self.schedule.is_troop_free(alt_time_slot, move_entry.troop) and 
                                            self.schedule.is_activity_available(alt_time_slot, move_entry.activity, move_entry.troop)):

                                            # Move the entry
                                            self.schedule.remove_entry(move_entry)
                                            self.schedule.add_entry(alt_time_slot, move_entry.activity, move_entry.troop)
                                            fixed += 1
                                            print(f"        [Exclusive] Moved {move_entry.troop.name} {move_entry.activity.name} to {alt_day.name}-{alt_slot}")
                                            break

                                if fixed > 0:  # Only move one entry per conflict
                                    break

        return fixed


    def _find_suitable_replacement(self, entry, troop, avoid_activities):
        """Find a suitable replacement activity that avoids conflicts."""
        avoid = set(avoid_activities)
        fill_rank = {
            name: idx for idx, name in enumerate(
                self.DEFAULT_FILL_PRIORITY if self.DEFAULT_FILL_PRIORITY else []
            )
        }

        candidates = []
        for activity in self.activities:
            if activity.name in avoid:
                continue
            if activity.name in self.NON_DISPLACEABLE_ACTIVITIES:
                continue
            if self._troop_has_activity(troop, activity):
                continue
            if not self._can_schedule(troop, activity, entry.time_slot, entry.time_slot.day, relax_constraints=False):
                continue
            pref_rank = troop.get_priority(activity.name)
            candidates.append((activity, pref_rank, fill_rank.get(activity.name, 999)))

        if candidates:
            # Prefer better-ranked preferences first, then SKULL fill-priority.
            candidates.sort(key=lambda x: (x[1], x[2], x[0].name))
            return candidates[0][0]
        return None


    def _find_wet_replacement(self, entry, troop):
        """Find a wet activity replacement."""
        wet_activities = [
            a
            for a in self.activities
            if a.name in set(self.WET_ACTIVITIES)
            and a.name not in self.NON_DISPLACEABLE_ACTIVITIES
            and not self._troop_has_activity(troop, a)
            and self._can_schedule(troop, a, entry.time_slot, entry.time_slot.day, relax_constraints=False)
        ]

        if wet_activities:
            # Prefer SKULL fill-priority wet options first to reduce disruption.
            fill_rank = {
                name: idx for idx, name in enumerate(
                    self.DEFAULT_FILL_PRIORITY if self.DEFAULT_FILL_PRIORITY else []
                )
            }
            wet_activities.sort(key=lambda a: (troop.get_priority(a.name), fill_rank.get(a.name, 999), a.name))
            return wet_activities[0]
        return None


    def _find_different_area_replacement(self, entry, troop, current_area):
        """Find an activity from a different area."""
        canonical_area = current_area
        alias_to_area = {
            "Rifle": "Rifle Range",
            "Waterfront": "Beach",
        }
        canonical_area = alias_to_area.get(current_area, canonical_area)

        avoid_activities = set(EXCLUSIVE_AREAS.get(canonical_area, []))
        if not avoid_activities and canonical_area == "Beach":
            avoid_activities = set(self.BEACH_ACTIVITIES)

        return self._find_suitable_replacement(entry, troop, avoid_activities)


    def _find_available_morning_slot(self, day, troop):
        """Find an available morning slot (1-2) for the given day and troop."""
        for slot in [1, 2]:
            # Find the time slot object
            time_slot = None
            for ts in self.time_slots:
                if ts.day == day and ts.slot_number == slot:
                    time_slot = ts
                    break

            if time_slot and not self.schedule.get_slot_activities(time_slot):
                # Check if any troop is already in this slot
                slot_activities = self.schedule.get_slot_activities(time_slot)
                troop_in_slot = any(e.troop == troop for e in slot_activities)
                if not troop_in_slot:
                    return slot
        return None


    def _find_capacity_replacement(self, entry, day, slot):
        """Find a replacement activity for capacity violations."""
        available_activities = [a for a in self.activities 
                              if a.name != entry.activity.name
                              and a.name not in entry.troop.preferences]  # Avoid activities already preferred

        if available_activities:
            # Prefer activities with low current usage in this slot
            activity_counts = {}
            # Find the time slot object
            time_slot = None
            for ts in self.time_slots:
                if ts.day == day and ts.slot_number == slot:
                    time_slot = ts
                    break

            if time_slot:
                existing_entries = self.schedule.get_slot_activities(time_slot)
                for existing in existing_entries:
                    activity_counts[existing.activity.name] = activity_counts.get(existing.activity.name, 0) + 1

            available_activities.sort(key=lambda a: activity_counts.get(a.name, 0))
            return available_activities[0]
        return None


    def _optimize_staff_variance(self):
        """
        ENHANCED: Advanced staff variance optimization to achieve <1.0 variance.

        Uses multiple sophisticated strategies:
        - Load balancing across all time slots
        - Activity complexity consideration
        - Cross-day staff redistribution
        - Priority-aware moves to protect Top 5
        """
        from collections import defaultdict

        STAFF_MAP = self.STAFF_ROLE_MAP

        all_staff_activities = set()
        for acts in STAFF_MAP.values():
            all_staff_activities.update(acts)

        # Count current staff load per slot
        slot_counts = defaultdict(int)
        staff_entries = []

        for entry in self.schedule.entries:
            if entry.activity.name in all_staff_activities:
                slot_counts[(entry.time_slot.day, entry.time_slot.slot_number)] += 1
                staff_entries.append(entry)

        if not staff_entries:
            return 0

        # Calculate current variance
        counts_list = list(slot_counts.values())
        avg_load = sum(counts_list) / len(counts_list)
        current_variance = sum((c - avg_load) ** 2 for c in counts_list) / len(counts_list)

        print(f"  [Enhanced Staff Balance] Current variance: {current_variance:.2f}, target: <1.0")

        optimizations = 0
        max_iterations = 3  # Prevent infinite loops

        for iteration in range(max_iterations):
            iteration_optimizations = 0

            # ENHANCED: Multi-strategy approach

            # Strategy 1: Move from overloaded to underloaded slots
            optimization_moves = self._balance_staff_loads(staff_entries, slot_counts, all_staff_activities)
            iteration_optimizations += optimization_moves

            # Strategy 2: Cross-day redistribution
            optimization_moves = self._cross_day_staff_redistribution(staff_entries, slot_counts, all_staff_activities)
            iteration_optimizations += optimization_moves

            # Strategy 3: Activity complexity balancing
            optimization_moves = self._balance_activity_complexity(staff_entries, slot_counts, all_staff_activities)
            iteration_optimizations += optimization_moves

            optimizations += iteration_optimizations

            # Recalculate variance
            counts_list = list(slot_counts.values())
            avg_load = sum(counts_list) / len(counts_list)
            new_variance = sum((c - avg_load) ** 2 for c in counts_list) / len(counts_list)

            print(f"    [Iteration {iteration + 1}] Made {iteration_optimizations} moves, variance: {new_variance:.2f}")

            # If we achieved target variance, stop
            if new_variance < 1.0:
                print(f"  [Enhanced Staff Balance] Target variance achieved: {new_variance:.2f}")
                break

            # If no improvements this iteration, stop
            if iteration_optimizations == 0:
                break

        # Final variance calculation
        counts_list = list(slot_counts.values())
        avg_load = sum(counts_list) / len(counts_list)
        final_variance = sum((c - avg_load) ** 2 for c in counts_list) / len(counts_list)

        improvement = current_variance - final_variance
        print(f"  [Enhanced Staff Balance] Final variance: {final_variance:.2f} (improved by {improvement:.2f})")

        return optimizations


    def _balance_staff_loads(self, staff_entries, slot_counts, all_staff_activities):
        """
        ENHANCED: Ultra-aggressive staff load balancing to achieve <1.0 variance.

        Strategy: Move activities from overloaded slots to underloaded slots,
        with priority-aware moves to protect Top 5 preferences.
        """
        from collections import defaultdict

        optimizations = 0

        # Calculate target load per slot
        total_staffed_activities = len(staff_entries)
        total_slots = len(slot_counts)
        target_load = total_staffed_activities / total_slots

        print(f"      [Staff Balance] Target load: {target_load:.1f} per slot")

        # Sort slots by load (overloaded first, underloaded last)
        sorted_slots = sorted(slot_counts.items(), key=lambda x: x[1], reverse=True)

        # Identify overloaded and underloaded slots
        overloaded_slots = [(slot, count) for slot, count in sorted_slots if count > target_load + 0.5]
        underloaded_slots = [(slot, count) for slot, count in sorted_slots if count < target_load - 0.5]

        if not overloaded_slots or not underloaded_slots:
            print(f"      [Staff Balance] Already well balanced (variance already low)")
            return 0

        print(f"      [Staff Balance] Found {len(overloaded_slots)} overloaded, {len(underloaded_slots)} underloaded slots")

        # Try to move activities from overloaded to underloaded slots
        for (overloaded_day, overloaded_slot), overloaded_count in overloaded_slots:
            if overloaded_count <= target_load + 0.5:
                break  # No longer significantly overloaded

            # Find staff activities in this overloaded slot
            overloaded_entries = [e for e in staff_entries 
                                if e.time_slot.day == overloaded_day and e.time_slot.slot_number == overloaded_slot]

            # Sort by priority (lower priority = easier to move)
            overloaded_entries.sort(key=lambda e: e.troop.get_priority(e.activity.name))

            for overloaded_entry in overloaded_entries:
                if overloaded_count <= target_load + 0.5:
                    break

                # Try to move to underloaded slots
                for (underloaded_day, underloaded_slot), underloaded_count in underloaded_slots:
                    if underloaded_count >= target_load - 0.5:
                        continue  # No longer significantly underloaded

                    # Find the time slot object
                    target_time_slot = None
                    for ts in self.time_slots:
                        if ts.day == underloaded_day and ts.slot_number == underloaded_slot:
                            target_time_slot = ts
                            break

                    if not target_time_slot:
                        continue

                    # Check if move is possible
                    if (self.schedule.is_troop_free(target_time_slot, overloaded_entry.troop) and 
                        self.schedule.is_activity_available(target_time_slot, overloaded_entry.activity, overloaded_entry.troop)):

                        # ENHANCED: Check if this move would improve variance significantly
                        current_variance = self._calculate_slot_variance(slot_counts)

                        # Simulate the move
                        new_slot_counts = slot_counts.copy()
                        new_slot_counts[(overloaded_day, overloaded_slot)] -= 1
                        new_slot_counts[(underloaded_day, underloaded_slot)] += 1

                        new_variance = self._calculate_slot_variance(new_slot_counts)

                        if new_variance < current_variance - 0.1:  # Significant improvement
                            # Make the move
                            self.schedule.remove_entry(overloaded_entry)
                            self.schedule.add_entry(target_time_slot, overloaded_entry.activity, overloaded_entry.troop)

                            # Update counts
                            slot_counts[(overloaded_day, overloaded_slot)] -= 1
                            slot_counts[(underloaded_day, underloaded_slot)] += 1
                            overloaded_count -= 1
                            underloaded_count += 1

                            optimizations += 1
                            print(f"        [Staff Balance] Moved {overloaded_entry.troop.name} {overloaded_entry.activity.name} from {overloaded_day.name[:3]}-{overloaded_slot} to {underloaded_day.name[:3]}-{underloaded_slot}")
                            break

                if optimizations >= 10:  # Limit moves per iteration
                    break

        return optimizations


    def _calculate_slot_variance(self, slot_counts):
        """Calculate variance of staff loads across slots."""
        if not slot_counts:
            return 0.0

        counts_list = list(slot_counts.values())
        avg_load = sum(counts_list) / len(counts_list)
        variance = sum((c - avg_load) ** 2 for c in counts_list) / len(counts_list)
        return variance
