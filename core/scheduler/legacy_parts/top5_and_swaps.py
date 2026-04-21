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

class LegacyPart02Mixin:
    """Scheduler legacy methods part 02."""

    def _top5_objective(self) -> tuple:
        """Objective tuple: minimize miss count, then total miss rank."""
        miss_count, misses = self._count_non_exempt_top5_misses()
        rank_sum = sum(rank for _, _, rank in misses)
        return miss_count, rank_sum


    def _bounded_top5_reoptimization(self, max_steps: int = 24) -> int:
        """
        Bounded local search for remaining Top 5 misses.
        Keeps only state changes that strictly improve the miss objective.
        """
        improvements = 0

        for _ in range(max_steps):
            current_obj = self._top5_objective()
            if current_obj[0] == 0:
                break

            _, misses = self._count_non_exempt_top5_misses()
            misses = sorted(misses, key=lambda m: m[2])[:8]

            best_obj = current_obj
            best_state = None
            best_note = ""

            # Candidate 0: one generic global repair move.
            base_snapshot = self._snapshot_scheduler_state()
            try:
                moved = self._attempt_global_top5_repair_step()
                if moved:
                    self._guarantee_no_gaps()
                    self._fix_multislot_integrity()
                    self._validate_critical_constraints()
                    cand_obj = self._top5_objective()
                    if cand_obj < best_obj:
                        best_obj = cand_obj
                        best_state = self._snapshot_scheduler_state()
                        best_note = "global-step"
            except Exception:
                pass
            finally:
                self._restore_scheduler_state(base_snapshot)

            for troop_name, activity_name, rank in misses:
                troop = next((t for t in self.troops if t.name == troop_name), None)
                activity = get_activity_by_name(activity_name)
                if not troop or not activity:
                    continue

                # Candidate 1: direct relaxed placement.
                snapshot = self._snapshot_scheduler_state()
                try:
                    placed = False
                    for slot in self._get_cluster_ordered_slots(troop, activity):
                        if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True) and self._add_to_schedule(slot, activity, troop):
                            placed = True
                            break
                    if placed:
                        self._guarantee_no_gaps()
                        self._fix_multislot_integrity()
                        self._validate_critical_constraints()
                        cand_obj = self._top5_objective()
                        if cand_obj < best_obj:
                            best_obj = cand_obj
                            best_state = self._snapshot_scheduler_state()
                            best_note = f"direct:{troop_name}/{activity_name}"
                except Exception:
                    pass
                finally:
                    self._restore_scheduler_state(snapshot)

                # Candidate 2: window-clearing placement.
                snapshot = self._snapshot_scheduler_state()
                try:
                    if self._force_place_with_window_clearing(
                        troop=troop,
                        activity=activity,
                        required_rank=max(0, rank - 1),
                        protected_names=self.NON_DISPLACEABLE_ACTIVITIES,
                    ):
                        self._guarantee_no_gaps()
                        self._fix_multislot_integrity()
                        self._validate_critical_constraints()
                        cand_obj = self._top5_objective()
                        if cand_obj < best_obj:
                            best_obj = cand_obj
                            best_state = self._snapshot_scheduler_state()
                            best_note = f"window:{troop_name}/{activity_name}"
                except Exception:
                    pass
                finally:
                    self._restore_scheduler_state(snapshot)

                # Candidate 3: cross-troop reclaim.
                snapshot = self._snapshot_scheduler_state()
                try:
                    if self._reclaim_activity_from_lower_priority_troop(
                        target_troop=troop,
                        activity=activity,
                        required_rank=max(0, rank - 1),
                        protected_names=self.NON_DISPLACEABLE_ACTIVITIES,
                    ):
                        self._guarantee_no_gaps()
                        self._fix_multislot_integrity()
                        self._validate_critical_constraints()
                        cand_obj = self._top5_objective()
                        if cand_obj < best_obj:
                            best_obj = cand_obj
                            best_state = self._snapshot_scheduler_state()
                            best_note = f"reclaim:{troop_name}/{activity_name}"
                except Exception:
                    pass
                finally:
                    self._restore_scheduler_state(snapshot)

                # Candidate 4: displace-and-recover for hard local jams.
                snapshot = self._snapshot_scheduler_state()
                try:
                    if self._try_place_with_displacement_recovery(
                        troop=troop,
                        activity=activity,
                        required_rank=max(0, rank - 1),
                        protected_names=self.NON_DISPLACEABLE_ACTIVITIES,
                    ):
                        self._guarantee_no_gaps()
                        self._fix_multislot_integrity()
                        self._validate_critical_constraints()
                        cand_obj = self._top5_objective()
                        if cand_obj < best_obj:
                            best_obj = cand_obj
                            best_state = self._snapshot_scheduler_state()
                            best_note = f"displace-recover:{troop_name}/{activity_name}"
                except Exception:
                    pass
                finally:
                    self._restore_scheduler_state(snapshot)

            if best_state is None:
                break

            self._restore_scheduler_state(best_state)
            improvements += 1
            print(f"  [Bounded Top5 Reopt] Improvement {improvements}: {current_obj} -> {best_obj} ({best_note})")

        return improvements


    def _comprehensive_gap_check(self, phase_name):
        """Detect area-level cluster gaps using the 1,-,3 same-area definition."""
        from ...models import Day

        cluster_areas = {
            "Tower": ["Climbing Tower"],
            "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
            "Outdoor Skills": [
                "Knots and Lashings",
                "Orienteering",
                "GPS & Geocaching",
                "Ultimate Survivor",
                "What's Cooking",
                "Chopped!",
            ],
            "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
        }

        total_gaps = 0
        details = []
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            day_entries = [e for e in self.schedule.entries if e.time_slot.day == day]
            for area_name, area_acts in cluster_areas.items():
                has_1 = any(e.time_slot.slot_number == 1 and e.activity.name in area_acts for e in day_entries)
                has_3 = any(e.time_slot.slot_number == 3 and e.activity.name in area_acts for e in day_entries)
                has_2 = any(e.time_slot.slot_number == 2 and e.activity.name in area_acts for e in day_entries)
                if has_1 and has_3 and not has_2:
                    total_gaps += 1
                    details.append(f"{day.name[:3]}: {area_name} pattern 1,-,3")

        if total_gaps > 0:
            print(f"  [{phase_name}] Found {total_gaps} total area cluster gaps [FAIL]")
            for detail in details[:8]:
                print(f"    {detail}")
        else:
            print(f"  [{phase_name}] No area cluster gaps detected [OK]")

        return total_gaps


    def _get_activity_score(self, troop, activity, slot, day):
        """
        Calculate score for an activity placement.
        Higher scores = better placement.
        """
        score = 0.0
        # COMMISSIONER CLUSTERING: Prefer slot where commissioner's other troops have Reflection
        commissioner = self.troop_commissioner.get(troop.name, "")
        preferred_slot = None

        if commissioner:
            # Find which slots this commissioner's other troops are using for Reflection
            from collections import defaultdict
            commissioner_reflection_slots = defaultdict(int)
            for other_troop in self.troops:
                if other_troop == troop:
                    continue
                if self.troop_commissioner.get(other_troop.name) == commissioner:
                    # Check if this troop has Reflection
                    for entry in self.schedule.entries:
                        if entry.troop == other_troop and entry.activity.name == "Reflection":
                            commissioner_reflection_slots[entry.time_slot] += 1

            # Prefer slots where commissioner already has troops
            if commissioner_reflection_slots:
                for slot in sorted(commissioner_reflection_slots, key=commissioner_reflection_slots.get, reverse=True):
                    if slot in self.time_slots:
                        preferred_slot = slot
                        break

        if preferred_slot:
            score += 1.0

        return score


    def _guarantee_friday_reflection(self):
        """
        GUARANTEE: Ensure every troop has Reflection scheduled on Friday.
        If not already scheduled, find or create a Friday slot for it.
        This is the final safety net for 100% Reflection coverage.
        """
        reflection = get_activity_by_name("Reflection")
        if not reflection:
            print("  Warning: Reflection activity not found!")
            return

        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
        guaranteed_count = 0
        swapped_count = 0

        for troop in self.troops:
            # Check if troop already has Reflection
            has_reflection = any(e.activity.name == "Reflection" 
                                for e in self.schedule.entries 
                                if e.troop == troop)

            if has_reflection:
                continue  # Already have Reflection

            # Find a free Friday slot
            free_slots = [s for s in friday_slots if self.schedule.is_troop_free(s, troop)]

            if free_slots:
                # COMMISSIONER CLUSTERING: Prefer slot where commissioner's other troops have Reflection
                commissioner = self.troop_commissioner.get(troop.name, "")
                preferred_slot = None

                if commissioner:
                    # Find which slots this commissioner's other troops are using for Reflection
                    from collections import defaultdict
                    commissioner_reflection_slots = defaultdict(int)
                    for other_troop in self.troops:
                        if other_troop == troop:
                            continue
                        if self.troop_commissioner.get(other_troop.name) == commissioner:
                            # Check if this troop has Reflection
                            for entry in self.schedule.entries:
                                if entry.troop == other_troop and entry.activity.name == "Reflection":
                                    commissioner_reflection_slots[entry.time_slot] += 1

                    # Prefer slotswhere commissioner already has troops
                    if commissioner_reflection_slots:
                        for slot in sorted(commissioner_reflection_slots, key=commissioner_reflection_slots.get, reverse=True):
                            if slot in free_slots:
                                preferred_slot = slot
                                break

                slot = preferred_slot if preferred_slot else free_slots[0]
                self.schedule.add_entry(slot, reflection, troop)
                cluster_note = " (joined commissioner)" if preferred_slot else ""
                print(f"  [Guaranteed] {troop.name}: Reflection -> {slot}{cluster_note}")
                guaranteed_count += 1
            else:
                # No free Friday slots - need to SWAP out a low-priority activity
                # Find the lowest priority activity on Friday for this troop
                friday_entries = [e for e in self.schedule.entries 
                                 if e.troop == troop and e.time_slot.day == Day.FRIDAY
                                 and e.activity.name != "Reflection"]

                if not friday_entries:
                    print(f"  WARNING: Cannot guarantee Reflection for {troop.name} - no Friday entries!")
                    continue

                # Find lowest priority activity to swap out
                # PRIORITY: Avoid swapping Top 5 preferences
                PROTECTED_ACTIVITIES = {"Sailing", "Climbing Tower", "Troop Rifle", "Troop Shotgun",
                                       "Archery", "Delta", "Super Troop"}

                # First, try to find non-Top-5 activities to swap
                top5_activities = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
                non_top5_swappable = [e for e in friday_entries 
                                      if e.activity.name not in PROTECTED_ACTIVITIES
                                      and e.activity.name not in top5_activities]

                if non_top5_swappable:
                    # Great! We can swap a non-Top-5 activity
                    swappable = non_top5_swappable
                else:
                    # No safe non-Top-5 option remains. Do NOT evict Top 5 here.
                    swappable = []
                    print(f"  WARNING: Reflection for {troop.name} requires Top-5 eviction on Friday; skipping forced swap.")
                    continue

                # Sort by preference priority (higher index = less important)
                def get_priority(entry):
                    try:
                        priority_idx = troop.preferences.index(entry.activity.name)
                        # Extra penalty if it's Top 5
                        if priority_idx < 5:
                            return priority_idx - 1000  # Make Top 5 less likely to be swapped
                        return priority_idx
                    except ValueError:
                        return 999  # Not in preferences = lowest priority

                swappable.sort(key=get_priority, reverse=True)

                # Swap the lowest priority entry
                entry_to_remove = swappable[0]
                slot = entry_to_remove.time_slot
                removed_activity = entry_to_remove.activity.name

                # Remove the old entry
                self.schedule.entries.remove(entry_to_remove)

                # Add Reflection - rollback if add fails (root cause: never remove without replace)
                if not self.schedule.add_entry(slot, reflection, troop):
                    self.schedule.entries.append(entry_to_remove)
                    continue

                # Check if we swapped a Top 5
                is_top5 = removed_activity in top5_activities
                swap_type = "Top 5 SWAP" if is_top5 else "SWAP"
                print(f"  [Guaranteed {swap_type}] {troop.name}: Reflection -> {slot} (replaced {removed_activity})")
                swapped_count += 1

        if guaranteed_count > 0 or swapped_count > 0:
            print(f"  Guaranteed {guaranteed_count} Reflections, swapped {swapped_count}")


    def _schedule_sailing_balls_fills(self):
        """Add balls (Gaga Ball/9 Square) during sailing if not in troop's top 5."""
        balls_activities = ["Gaga Ball", "9 Square"]

        for entry in self.schedule.entries:
            if entry.activity.name != "Sailing":
                continue

            troop = entry.troop
            slot = entry.time_slot

            # Check if either balls activity is NOT in top 5
            for balls_name in balls_activities:
                priority = troop.get_priority(balls_name)
                if priority is None or priority >= 5:  # Not in top 5
                    # Check if troop doesn't already have this balls activity scheduled
                    if not self._troop_has_activity(troop, get_activity_by_name(balls_name)):
                        self.sailing_balls_fills[(slot, troop.name)] = balls_name
                        print(f"  {troop.name}: {balls_name} (30 min) during Sailing at {slot}")
                        break  # Only one balls activity per sailing


    def _schedule_day_requests(self):
        """Schedule day-specific activity requests (MUST be fulfilled)."""
        print("\n--- Scheduling Day-Specific Requests (REQUIRED) ---")

        day_map = {
            "Monday": Day.MONDAY,
            "Tuesday": Day.TUESDAY,
            "Wednesday": Day.WEDNESDAY,
            "Thursday": Day.THURSDAY,
            "Friday": Day.FRIDAY
        }

        for troop in self.troops:
            if not troop.day_requests:
                continue

            for day_name, activities in troop.day_requests.items():
                day = day_map.get(day_name)
                if not day:
                    continue

                day_slots = [s for s in self.time_slots if s.day == day]

                for activity_name in activities:
                    activity = get_activity_by_name(activity_name)
                    if not activity:
                        print(f"  WARNING: Activity '{activity_name}' not found!")
                        continue

                    # Try to schedule on requested day
                    scheduled = False
                    for slot in day_slots:
                        if self._can_schedule(troop, activity, slot, day):
                            if self._add_to_schedule(slot, activity, troop):
                                self._update_progress(troop, activity_name)
                                print(f"  {troop.name}: {activity_name} -> {day_name} [OK]")
                                scheduled = True
                                break

                    if not scheduled:
                        print(f"  ERROR: Could not schedule {activity_name} on {day_name} for {troop.name}!")


    def _schedule_two_hour_activities_priority(self):
        """Schedule Top 10 2-hour activities early to prevent blocking."""
        print("\n--- Scheduling Top 10 2-Hour Activities (Priority) ---")

        # Hardcode list of known 2-hour activities or check duration dynamically
        # Assuming duration is available in activity object, but we need to find them first.
        # Ideally, iterate over all activities and check slots == 2?
        # For now, let's look for activities with slots >= 2 that are NOT 3-hour ones.

        for troop in self.troops:
             # Check Top 10 preferences
             for pref_index, pref_name in enumerate(troop.preferences[:10]):
                 if pref_name in self.THREE_HOUR_ACTIVITIES:
                     continue # Already handled

                 activity = get_activity_by_name(pref_name)
                 if not activity: 
                     continue

                 effective_slots = self.schedule._get_effective_slots(activity, troop)
                 if effective_slots >= 1.5:
                      # Special handling for 2-slot activities
                      if self._troop_has_activity(troop, activity):
                          continue

                      # Try to schedule early
                      if self._try_schedule_activity(troop, activity):
                          print(f"  [Priority 2-Hour] {troop.name}: {pref_name} (Rank #{pref_index+1})")


    def _schedule_three_hour_activities(self):
        """Schedule 3-hour activities first - they need the most consecutive slots."""
        print("\n--- Scheduling 3-hour activities (Top Priority) ---")

        # Collect all requests for 3-hour activities first
        requests = []
        for troop in self.troops:
            # Check preferences for 3-hour activities
            for pref_index, pref_name in enumerate(troop.preferences[:10]):  # Check top 10
                if pref_name in self.THREE_HOUR_ACTIVITIES:
                    # Special rule: Back of the Moon only if Top 3
                    if pref_name == "Back of the Moon" and pref_index >= 3:
                        continue  # Skip - not in Top 3

                    activity = get_activity_by_name(pref_name)
                    if not activity:
                        continue

                    # Store as tuple: (troop, rank, activity)
                    requests.append((troop, pref_index, activity))

        if not requests:
            print("  No 3-hour activity requests found.")
            return

        # Sort by preference rank (lower index = higher priority)
        # Secondary sort by troop name for determinism
        requests.sort(key=lambda x: (x[1], x[0].name))

        print(f"  Found {len(requests)} requests for 3-hour activities. Scheduling in priority order...")

        count = 0
        for troop, rank, activity in requests:
            # Each troop should only get 1 three-hour activity (multiple troops can have them on same day)
            existing_3hr = sum(1 for e in self.schedule.entries 
                             if e.troop == troop and e.activity.name in self.THREE_HOUR_ACTIVITIES)

            if existing_3hr >= 1:
                print(f"  [SKIP] {troop.name}: Already has a 3-hour activity, skipping {activity.name}")
                continue

            # Try to schedule it
            scheduled = self._try_schedule_activity(troop, activity)
            if scheduled:
                print(f"  [SUCCESS] {troop.name}: {activity.name} (Rank #{rank+1})")
                count += 1
            else:
                print(f"  [FAIL] {troop.name}: Could not schedule {activity.name}")

        print(f"  Scheduled {count} / {len(requests)} 3-hour activities.")


    def _schedule_sailing_optimize_all(self):
        """
        Consolidated Sailing Optimization Phase (9 Slots Logic).

        1. Identifies all demand (Top 10 preferences).
        2. Sorts by: Preference Rank (Primary) -> Scout Count (Secondary).
        3. Assigns slots to maximize capacity (9 slots/week):
           - Thursday: 2 slots (reserved for Largest High Priority).
           - Mon/Tue/Wed: Up to 2 sessions per day (Slots 1-2 & 2-3).
           - Friday: 1 session (Slots 1-2, avoiding Reflection).

        This replaces previous scattered Sailing phases to ensure prioritization 
        and maximum capacity utilization.
        """
        from ...models import Day, TimeSlot

        print("\n--- Sailing Optimization (9-Slot Max Capacity) ---")

        sailing = get_activity_by_name("Sailing")
        if not sailing:
            print("  Sailing activity not found!")
            return

        # 1. Identify Troop Demand
        troops_demand = []
        for troop in self.troops:
            # Check if already scheduled (shouldn't be, as this runs early)
            if self._troop_has_activity(troop, sailing):
                continue

            # Check preferences (Top 10)
            if "Sailing" in troop.preferences[:10]:
                rank = troop.preferences.index("Sailing") + 1
                scouts = troop.scouts if hasattr(troop, 'scouts') else 0
                troops_demand.append((troop, rank, scouts))

        if not troops_demand:
            print("  No troops need Sailing in User Preferences.")
            return

        # 2. Sort Demand
        # Primary: Preference Rank (Ascending - 1 is best)
        # Secondary: Troop Size (Descending - largest first)
        troops_demand.sort(key=lambda x: (x[1], -x[2]))

        print(f"  Troop Demand ({len(troops_demand)} troops):")
        for t, r, s in troops_demand:
            print(f"    {t.name}: Rank #{r}, Size {s}")

        # 3. Schedule - Strategy: Fill slots in specific order
        # Order: 
        # A. Thursday (2 slots) - Largest High Priority
        # B. Mon/Tue/Wed (Double Sessions) - Fill remaining demand

        scheduled_count = 0

        # Helper to try scheduling
        def try_schedule(troop, day, start_slot):
            slot1 = TimeSlot(day=day, slot_number=start_slot)

            # Check if slots are free
            if not self.schedule.is_troop_free(slot1, troop):
                return False

            # Check second slot (Sailing is 1.5 slots, rounds to 2)
            slot2_num = start_slot + 1
            if slot2_num > (2 if day == Day.THURSDAY else 3):
                return False
            slot2 = TimeSlot(day=day, slot_number=slot2_num)
            if not self.schedule.is_troop_free(slot2, troop):
                return False

            if self._can_schedule(troop, sailing, slot1, day):
                self.schedule.add_entry(slot1, sailing, troop)
                self._update_progress(troop, "Sailing")
                print(f"  [SUCCESS] {troop.name} -> {day.name} Slot {start_slot}")
                return True
            return False

        # A. Thursday Assignment for Largest High Priority
        # Find the largest troop with Top 5 preference
        largest_top5 = None
        # Filter for Top 5 only first
        top5_demand = [x for x in troops_demand if x[1] <= 5]
        if top5_demand:
            # Sort by Size DESC
            top5_demand.sort(key=lambda x: -x[2])
            largest_top5 = top5_demand[0] # Tuple (Troop, Rank, Size)

            # Try to schedule them on Thursday Slot 1
            start_slot = 1
            # Verify Thursday is valid
            if try_schedule(largest_top5[0], Day.THURSDAY, 1):
                scheduled_count += 1
                # Remove from demand list
                troops_demand = [x for x in troops_demand if x[0] != largest_top5[0]]
            else:
                print(f"  [WARN] Could not place largest troop {largest_top5[0].name} on Thursday.")

        # B. Fill remaining demand on Mon/Tue/Wed/Fri
        # Priority: Mon/Tue/Wed (Double Capacity) -> Fri (Single Capacity)
        target_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]

        # We need to fill 2 sessions per day: Slot 1 start (1-2) and Slot 2 start (2-3)
        # Iterate through demand list (already sorted by Rank -> Size)

        for idx, (troop, rank, size) in enumerate(list(troops_demand)):
            placed = False

            # Prefer Delta pairing if exists
            delta_day = None
            if "Delta" in troop.preferences:
                 # If Delta is not yet scheduled, use configured commissioner-day mapping.
                 delta_day = self._get_activity_commissioner_day(troop, "Delta")

            # Prioritize Delta day if available
            day_order = list(target_days)
            if delta_day and delta_day in day_order:
                day_order.remove(delta_day)
                day_order.insert(0, delta_day)

            # Try Slot 1 starts first (standard), then Slot 2 starts (overlap)
            # Actually, to maximize 2/day, we should check which slots are open

            for day in day_order:
                # Try Start Slot 1 (occupies 1-2)
                if try_schedule(troop, day, 1):
                    placed = True
                    break
                # Try Start Slot 2 (occupies 2-3) - Only valid if Slot 1-2 session exists or free?
                # Actually _can_schedule handles the overlap validation logic I saw earlier
                if try_schedule(troop, day, 2):
                    placed = True
                    break

            if not placed:
                 # Try Friday as last resort (Slot 1 only usually, avoiding Reflection)
                 if try_schedule(troop, Day.FRIDAY, 1):
                     placed = True

            if placed:
                 scheduled_count += 1
            else:
                 print(f"  [FAIL] Could not schedule Sailing for {troop.name} (Rank {rank})")

        print(f"  Scheduled {scheduled_count} Sailing sessions.")


    def _schedule_thursday_sailing_largest_troop(self):
        """
        Schedule Thursday Sailing for the LARGEST troop that wants it.

        Thursday only has 2 slots total, so only 1 Sailing can fit (takes 1.5 slots).
        This must go to the troop with the most scouts to maximize attendance.
        """
        from ...models import Day

        print("\n--- Thursday Sailing for Largest Troop ---")

        sailing = get_activity_by_name("Sailing")
        if not sailing:
            print("  Sailing activity not found!")
            return

        # Find all troops that want Sailing in their Top 10 preferences
        troops_wanting_sailing = []
        for troop in self.troops:
            if "Sailing" in troop.preferences[:10]:
                pref_rank = troop.preferences.index("Sailing") + 1
                scouts = troop.scouts if hasattr(troop, 'scouts') else 0
                troops_wanting_sailing.append((troop, scouts, pref_rank))

        if not troops_wanting_sailing:
            print("  No troops want Sailing in Top 10")
            return

        # Sort by scout count (largest first), then by preference rank (lower is better)
        troops_wanting_sailing.sort(key=lambda x: (-x[1], x[2]))

        print(f"  Troops wanting Sailing (sorted by size):")
        for troop, scouts, rank in troops_wanting_sailing:
            print(f"    {troop.name}: {scouts} scouts, Sailing is #{rank}")

        # Give Thursday Sailing to the largest troop that can take it
        thursday_slot1 = next((s for s in self.time_slots 
                               if s.day == Day.THURSDAY and s.slot_number == 1), None)

        if not thursday_slot1:
            print("  ERROR: Thursday slot 1 not found!")
            return

        # Check if Thursday slot 1 is already taken
        thu_slot1_entries = [e for e in self.schedule.entries 
                            if e.time_slot == thursday_slot1]
        if thu_slot1_entries:
            print(f"  Thursday slot 1 already taken by: {[e.activity.name for e in thu_slot1_entries]}")
            return

        # Try to schedule for the largest troop
        for troop, scouts, pref_rank in troops_wanting_sailing:
            # If troop also wants Delta, avoid Thursday (can't pair Delta+Sailing on Thu)
            if "Delta" in troop.preferences:
                continue
            # Check if troop already has Sailing
            if self._troop_has_activity(troop, sailing):
                print(f"  {troop.name} already has Sailing")
                continue

            # Check if troop is free on Thursday slot 1
            if not self.schedule.is_troop_free(thursday_slot1, troop):
                print(f"  {troop.name} not free on Thursday slot 1")
                continue

            # Check Sailing-specific constraints
            if self._can_schedule_sailing(troop, thursday_slot1, Day.THURSDAY):
                self.schedule.add_entry(thursday_slot1, sailing, troop)
                self._update_progress(troop, "Sailing")
                print(f"  [SUCCESS] {troop.name} ({scouts} scouts) gets Thursday Sailing!")
                return
            else:
                print(f"  {troop.name} blocked by Sailing constraints")

        print("  Could not schedule Thursday Sailing for any troop")


    def _schedule_early_aqua_trampoline_top5(self):
        """
        Schedule Aqua Trampoline early for troops with it in Top 5.
        Pattern: 67% of Top 5 misses are Aqua Trampoline; large troops (17+) need exclusive slots.
        Reserve beach slots (1 or 3 on Mon/Tue/Wed/Fri, 1-2 on Thu) before preferences fill them.
        """
        from ...models import Day

        at = get_activity_by_name("Aqua Trampoline")
        if not at:
            return

        troops_need_at = []
        for troop in self.troops:
            top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            if "Aqua Trampoline" not in top5:
                continue
            if self._troop_has_activity(troop, at):
                continue
            rank = troop.preferences.index("Aqua Trampoline") + 1
            size = troop.scouts + troop.adults
            troops_need_at.append((troop, rank, size))

        if not troops_need_at:
            return

        # Large troops (17+) need exclusive slot - schedule first. Then by rank.
        def sort_key(x):
            troop, rank, size = x
            is_large = 1 if size > 16 else 0
            return (-is_large, rank, -size)
        troops_need_at.sort(key=sort_key)

        # Valid slots: 1, 3, then 2 (Top 5 relaxation) on Mon/Tue/Wed/Fri; 1, 2 on Thu
        valid_slots = []
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
            if day == Day.THURSDAY:
                valid_slots.extend([(day, 1), (day, 2)])
            else:
                valid_slots.extend([(day, 1), (day, 3), (day, 2)])  # Slot 2 last (Top 5 relaxation)

        scheduled = 0
        for troop, rank, size in troops_need_at:
            placed = False
            for day, slot_num in valid_slots:
                slot = next((s for s in self.time_slots if s.day == day and s.slot_number == slot_num), None)
                if not slot or not self.schedule.is_troop_free(slot, troop):
                    continue
                if self._can_schedule(troop, at, slot, day):
                    self._add_to_schedule(slot, at, troop)
                    scheduled += 1
                    placed = True
                    break
            if not placed:
                pass  # Will be retried in Top 5 phase
        if scheduled > 0:
            print(f"  [Early AT] Scheduled Aqua Trampoline for {scheduled} troops (Top 5)")


    def _guarantee_top1_beach(self):
        """
        GUARANTEE: If a troop's #1 preference is a beach activity, force it early.
        This prevents top-1 beach activities (AT/WP/GM/etc.) from being crowded out.
        """
        from ...activities import get_activity_by_name

        # Protect multi-slot activities (Rocks) from being shredded
        PROTECTED = set(self.NON_DISPLACEABLE_ACTIVITIES).union({"Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"})
        missed = []
        placed = 0

        for troop in self.troops:
            if not troop.preferences:
                continue
            top1 = troop.preferences[0]
            if top1 not in self.BEACH_ACTIVITIES and top1 not in self.BEACH_SLOT_ACTIVITIES:
                continue

            # Already scheduled?
            if self._troop_has_activity(troop, get_activity_by_name(top1)):
                continue

            activity = get_activity_by_name(top1)
            if not activity:
                continue

            # PASS 1: Try any slot (relaxed constraints)
            ordered_slots = self._get_cluster_ordered_slots(troop, activity)
            placed_this = False
            for slot in ordered_slots:
                if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True, allow_top1_beach_slot2=False):
                    self._add_to_schedule(slot, activity, troop)
                    placed += 1
                    placed_this = True
                    break

            if placed_this:
                continue

            # PASS 2: Swap out lower-priority activity (any slot, relaxed)
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            replaceable = []
            top5_set = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)

            # Option 1 (guarded): for Top 1 beach, displace NON-Top5 beach first
            if top1 in self.BEACH_ACTIVITIES or top1 in self.BEACH_SLOT_ACTIVITIES:
                for entry in troop_entries:
                    if entry.activity.name in PROTECTED:
                        continue
                    if entry.activity.name in self.BEACH_ACTIVITIES and entry.activity.name not in top5_set:
                        replaceable.append((entry, -1))  # highest priority to displace

            # Fallback: displace any lower-priority non-Top5 activities
            if not replaceable:
                for entry in troop_entries:
                    if entry.activity.name in PROTECTED:
                        continue
                    if entry.activity.name in top5_set:
                        continue  # never displace Top 5
                    try:
                        entry_priority = troop.preferences.index(entry.activity.name)
                    except ValueError:
                        entry_priority = 999
                    if entry_priority > 0:  # lower priority than top-1
                        replaceable.append((entry, entry_priority))

            # Protect multi-slot activities (Rocks) from being displaced by Sand
            replaceable.sort(key=lambda x: (0 if getattr(x[0].activity, 'slots', 1.0) > 1.0 else 1, x[1]), reverse=True)

            for candidate, _ in replaceable:
                slot = candidate.time_slot
                self.schedule.entries.remove(candidate)
                if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True, allow_top1_beach_slot2=False):
                    self._add_to_schedule(slot, activity, troop)
                    placed += 1
                    placed_this = True
                    break
                self.schedule.entries.append(candidate)

            if placed_this:
                continue

            # PASS 3: Cross-slot swap (remove low-priority, place anywhere relaxed)
            for candidate, _ in replaceable:
                removed_slot = candidate.time_slot
                self.schedule.entries.remove(candidate)
                for slot in self.time_slots:
                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True, allow_top1_beach_slot2=False):
                        self._add_to_schedule(slot, activity, troop)
                        self._fill_vacated_slot(troop, removed_slot)
                        placed += 1
                        placed_this = True
                        break
                if placed_this:
                    break
                self.schedule.entries.append(candidate)

            if not placed_this:
                missed.append((troop.name, top1))

        if missed:
            print(f"  [Top1 Beach] Missed {len(missed)} top-1 beach preferences:")
            for troop_name, activity_name in missed:
                print(f"    - {troop_name}: {activity_name}")
        else:
            print("  [Top1 Beach] All top-1 beach preferences placed")


    def _force_top1_preferences(self):
        """
        GUARANTEE: Force Top 1 preferences for all troops before Top 2-5.
        This aggressively makes space for Top 1 by displacing lower-priority activities.
        """
        from ...activities import get_activity_by_name

        # Protect multi-slot activities (Rocks) from being shredded
        PROTECTED = set(self.NON_DISPLACEABLE_ACTIVITIES).union({"Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"})
        forced = 0
        missed = []

        for troop in self.troops:
            if not troop.preferences:
                continue
            top1 = troop.preferences[0]
            activity = get_activity_by_name(top1)
            if not activity:
                continue
            if self._troop_has_activity(troop, activity):
                continue

            placed = False
            ordered_slots = self._get_cluster_ordered_slots(troop, activity)
            for slot in ordered_slots:
                if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True, allow_top1_beach_slot2=False):
                    self._add_to_schedule(slot, activity, troop)
                    forced += 1
                    placed = True
                    break
            if placed:
                continue

            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            replaceable = []
            for entry in troop_entries:
                if entry.activity.name in PROTECTED:
                    continue
                try:
                    entry_priority = troop.preferences.index(entry.activity.name)
                except ValueError:
                    entry_priority = 999
                if entry_priority > 0:  # lower priority than top-1
                    replaceable.append((entry, entry_priority))
            # Protect multi-slot activities (Rocks) from being displaced by Sand
            replaceable.sort(key=lambda x: (0 if getattr(x[0].activity, 'slots', 1.0) > 1.0 else 1, x[1]), reverse=True)

            # Same-slot swap (relaxed)
            for candidate, _ in replaceable:
                slot = candidate.time_slot
                self.schedule.entries.remove(candidate)
                if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True, allow_top1_beach_slot2=False):
                    self._add_to_schedule(slot, activity, troop)
                    forced += 1
                    placed = True
                    break
                self.schedule.entries.append(candidate)

            if placed:
                continue

            # Cross-slot swap (relaxed)
            for candidate, _ in replaceable:
                removed_slot = candidate.time_slot
                self.schedule.entries.remove(candidate)
                for slot in self.time_slots:
                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True, allow_top1_beach_slot2=False):
                        self._add_to_schedule(slot, activity, troop)
                        self._fill_vacated_slot(troop, removed_slot)
                        forced += 1
                        placed = True
                        break
                if placed:
                    break
                self.schedule.entries.append(candidate)

            # Option 2: allow slot 2 for Top 1 beach only if still missing
            if not placed and (top1 in self.BEACH_ACTIVITIES or top1 in self.BEACH_SLOT_ACTIVITIES):
                ordered_slots = self._get_cluster_ordered_slots(troop, activity)
                for slot in ordered_slots:
                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True, allow_top1_beach_slot2=True):
                        self._add_to_schedule(slot, activity, troop)
                        forced += 1
                        placed = True
                        break

            if not placed:
                missed.append((troop.name, top1))

        if missed:
            print(f"  [Top1 Force] Missed {len(missed)} Top 1 preferences:")
            for troop_name, activity_name in missed:
                print(f"    - {troop_name}: {activity_name}")
        else:
            print("  [Top1 Force] All Top 1 preferences placed")


    def _schedule_early_sailing_top10(self):
        """
        Schedule Sailing early for troops that have it in their Top 10.

        Sailing requires 1.5 consecutive slots - this must be done early
        before the schedule fills up and no consecutive slots remain.
        """
        from ...models import Day

        print("\n--- Early Sailing for Top 10 Troops ---")

        sailing = get_activity_by_name("Sailing")
        if not sailing:
            print("  Sailing activity not found!")
            return

        # Find troops with Sailing in Top 10 that don't have it yet
        troops_need_sailing = []
        for troop in self.troops:
            if "Sailing" in troop.preferences[:10]:
                if not self._troop_has_activity(troop, sailing):
                    rank = troop.preferences.index("Sailing") + 1
                    scouts = troop.scouts if hasattr(troop, 'scouts') else 0
                    troops_need_sailing.append((troop, rank, scouts))

        if not troops_need_sailing:
            print("  No troops need Sailing in Top 10")
            return

        # Sort by preference rank (lower=better), then by size
        troops_need_sailing.sort(key=lambda x: (x[1], -x[2]))

        print(f"  Troops needing Sailing (Top 10):")
        for troop, rank, scouts in troops_need_sailing:
            print(f"    {troop.name}: #{rank}, {scouts} scouts")

        scheduled_count = 0

        for troop, rank, scouts in troops_need_sailing:
            # Top-5 Sailing needs broader fallback to avoid avoidable misses.
            preferred_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]
            if rank <= 5:
                preferred_days.append(Day.THURSDAY)

            # AGGRESSIVELY prefer days that already have exactly 1 Sailing (to get to 2 per day)
            # This maximizes the "2 sails per day" pattern for scoring
            sailing_day_counts = {}
            for entry in self.schedule.entries:
                if entry.activity.name != "Sailing":
                    continue
                day = entry.time_slot.day
                slot_num = entry.time_slot.slot_number
                # Count sailing starts only; continuation slots should not consume day capacity.
                if slot_num == 1:
                    sailing_day_counts[day] = sailing_day_counts.get(day, 0) + 1
                elif slot_num == 2:
                    has_slot1_same_troop = any(
                        e.troop == entry.troop
                        and e.activity.name == "Sailing"
                        and e.time_slot.day == day
                        and e.time_slot.slot_number == 1
                        for e in self.schedule.entries
                    )
                    if not has_slot1_same_troop:
                        sailing_day_counts[day] = sailing_day_counts.get(day, 0) + 1

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

            # Pair with Delta if already scheduled
            delta_day = None
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.activity.name == "Delta":
                    delta_day = entry.time_slot.day
                    break
            if delta_day and delta_day != Day.FRIDAY:
                preferred_days = [delta_day] + [d for d in preferred_days if d != delta_day]
                print(f"  [Delta Pairing] {troop.name}: preferring Sailing on {delta_day.value}")

            # Try each preferred day
            for day in preferred_days:
                # Sailing needs slots 1-2 (consecutive)
                slot1 = TimeSlot(day=day, slot_number=1)
                slot2 = TimeSlot(day=day, slot_number=2)

                # Check both slots are free
                if not self.schedule.is_troop_free(slot1, troop):
                    continue
                if not self.schedule.is_troop_free(slot2, troop):
                    continue

                # Check sailing constraints
                if self._can_schedule(troop, sailing, slot1, day):
                    self.schedule.add_entry(slot1, sailing, troop)
                    self._update_progress(troop, "Sailing")
                    scheduled_count += 1
                    print(f"  [SUCCESS] {troop.name}: Sailing at {day.value[:3]}-1 (Top {rank})")
                    break
            else:
                # Try slots 2-3 as fallback
                for day in preferred_days:
                    slot2 = TimeSlot(day=day, slot_number=2)
                    slot3 = TimeSlot(day=day, slot_number=3)

                    if not self.schedule.is_troop_free(slot2, troop):
                        continue
                    if not self.schedule.is_troop_free(slot3, troop):
                        continue

                    if self._can_schedule(troop, sailing, slot2, day):
                        self.schedule.add_entry(slot2, sailing, troop)
                        self._update_progress(troop, "Sailing")
                        scheduled_count += 1
                        print(f"  [SUCCESS] {troop.name}: Sailing at {day.value[:3]}-2 (Top {rank})")
                        break
                else:
                    print(f"  [FAILED] {troop.name}: No consecutive slots available")

        print(f"  Scheduled Sailing for {scheduled_count}/{len(troops_need_sailing)} troops")


    def _enforce_delta_sailing_pairing(self):
        """Force Delta + Sailing to occur on the same day when both are scheduled.

        AGGRESSIVE: For troops with BOTH Delta and Sailing, ensures Delta is in slot 1 or 3
        (never 2), and Sailing takes the other two slots on the same day.

        NOTE: Deltas NOT paired with Sailing can be in slot 2 to reduce gaps and excess days.
        This restriction ONLY applies to Deltas that are paired with Sailing.

        Will move activities to achieve this pairing, respecting spine constraints.
        """
        from ...models import TimeSlot, Day

        print("\n--- Enforcing Delta + Sailing Same-Day Pairing ---")
        fixes = 0
        protected = {"Reflection", "Super Troop"}
        delta_policy = self._get_family_day_policy(family_name="Delta/Sailing")
        if delta_policy is None and hasattr(self, "_ensure_delta_sailing_family_policy"):
            delta_policy = self._ensure_delta_sailing_family_policy()

        def is_protected(occupant_entry) -> bool:
            """Never displace Reflection, Super Troop, or any Top 5 preference."""
            if occupant_entry.activity.name in protected:
                return True
            troop = occupant_entry.troop
            rank = troop.get_priority(occupant_entry.activity.name) if hasattr(troop, 'get_priority') else None
            return rank is not None and rank < 5

        for troop in self.troops:
            # Only enforce slot 1/3 restriction for troops that have BOTH Delta and Sailing
            # Deltas NOT paired with Sailing can be in slot 2 to reduce gaps and excess days
            if "Delta" not in troop.preferences or "Sailing" not in troop.preferences:
                continue

            top5 = set(troop.preferences[:5])
            sailing_entries = [e for e in self.schedule.entries if e.troop == troop and e.activity.name == "Sailing"]
            delta_entry = next((e for e in self.schedule.entries if e.troop == troop and e.activity.name == "Delta"), None)
            if not sailing_entries or not delta_entry:
                continue  # Skip if either is not scheduled yet

            def move_entry_to_slot(entry, target_slot):
                """Move a single-slot entry to target_slot, swapping out any non-protected occupant."""
                if entry.activity.name in {"Delta", "Sailing"} and delta_policy:
                    if not self._family_policy_allows_day(
                        entry.activity.name,
                        target_slot.day,
                        strict=False,
                    ):
                        return False
                occupant = next((e for e in self.schedule.entries
                                 if e.troop == troop and e.time_slot == target_slot), None)
                if occupant and is_protected(occupant):
                    return False
                removed = []
                if occupant:
                    self.schedule.entries.remove(occupant)
                    removed.append(occupant)
                    removed.extend(self._remove_continuations_helper(occupant))
                if entry in self.schedule.entries:
                    self.schedule.entries.remove(entry)
                if self._can_schedule(troop, entry.activity, target_slot, target_slot.day):
                    self.schedule.add_entry(target_slot, entry.activity, troop)
                    if occupant:
                        old_slot = entry.time_slot
                        if self._can_schedule(troop, occupant.activity, old_slot, old_slot.day):
                            self.schedule.add_entry(old_slot, occupant.activity, troop)
                        else:
                            self._fill_vacated_slot(troop, old_slot)
                    return True
                # Restore
                if entry not in self.schedule.entries:
                    self.schedule.entries.append(entry)
                for r in removed:
                    if r not in self.schedule.entries:
                        self.schedule.entries.append(r)
                return False

            # CRITICAL: For Delta+Sailing pairs, Delta MUST be in slot 1 or 3 (never 2)
            # This allows Sailing to take the other two slots on the same day
            # If Delta is in slot 2, we need to move it to allow Sailing pairing
            if delta_entry.time_slot.slot_number == 2:
                # Try slot 1 first, then slot 3 on the same day
                for slot_num in (1, 3):
                    target = TimeSlot(day=delta_entry.time_slot.day, slot_number=slot_num)
                    if move_entry_to_slot(delta_entry, target):
                        delta_entry = next((e for e in self.schedule.entries if e.troop == troop and e.activity.name == "Delta"), delta_entry)
                        fixes += 1
                        print(f"  {troop.name}: Delta moved from slot 2 to slot {slot_num} (Sailing pairing requirement)")
                        break
                # If still in slot 2, try moving to Sailing's day
                if delta_entry.time_slot.slot_number == 2:
                    if sailing_entries:
                        sailing_day = sailing_entries[0].time_slot.day
                        if delta_entry.time_slot.day != sailing_day:
                            for slot_num in (1, 3):
                                target = TimeSlot(day=sailing_day, slot_number=slot_num)
                                if move_entry_to_slot(delta_entry, target):
                                    delta_entry = next((e for e in self.schedule.entries if e.troop == troop and e.activity.name == "Delta"), delta_entry)
                                    fixes += 1
                                    print(f"  {troop.name}: Delta moved to {sailing_day.value} slot {slot_num} (Sailing pairing requirement)")
                                    break

            # Determine sailing day + start slot
            sailing_days = sorted({e.time_slot.day for e in sailing_entries}, key=lambda d: list(Day).index(d))
            if delta_policy:
                sailing_days.sort(
                    key=lambda day: (
                        0 if self._family_policy_allows_day("Sailing", day, strict=True) else 1,
                        list(Day).index(day),
                    )
                )
            sailing_day = sailing_days[0]
            sailing_slots = sorted({e.time_slot.slot_number for e in sailing_entries if e.time_slot.day == sailing_day})
            if not sailing_slots:
                continue

            start_slot = 1 if 1 in sailing_slots else min(sailing_slots)
            target_slot_num = 3 if start_slot == 1 else 1
            target_slot = TimeSlot(day=sailing_day, slot_number=target_slot_num)

            if delta_entry.time_slot.day == sailing_day and delta_entry.time_slot.slot_number == target_slot_num:
                continue  # Already paired correctly

            # Try to move Delta to the open slot on the Sailing day
            if move_entry_to_slot(delta_entry, target_slot):
                fixes += 1
                print(f"  {troop.name}: Delta paired with Sailing on {sailing_day.value} (slot {target_slot_num})")
                continue

            # Otherwise, try moving Sailing to Delta's day
            delta_day = delta_entry.time_slot.day
            delta_slot_num = delta_entry.time_slot.slot_number
            if delta_slot_num not in (1, 3):
                continue
            sailing_start_slot = 2 if delta_slot_num == 1 else 1
            start_slot = TimeSlot(day=delta_day, slot_number=sailing_start_slot)
            target_slots = [TimeSlot(day=delta_day, slot_number=sailing_start_slot), TimeSlot(day=delta_day, slot_number=sailing_start_slot + 1)]

            # Remove existing sailing for this troop first
            removed_sailing = []
            for entry in sailing_entries:
                if entry in self.schedule.entries:
                    self.schedule.entries.remove(entry)
                    removed_sailing.append(entry)

            # Clear target slots (do not remove Top 5)
            removed_block = []
            can_clear = True
            for ts in target_slots:
                if not self.schedule.is_troop_free(ts, troop):
                    occupant = next((e for e in self.schedule.entries if e.troop == troop and e.time_slot == ts), None)
                    if occupant and is_protected(occupant):
                        can_clear = False
                        break
                    if occupant:
                        self.schedule.entries.remove(occupant)
                        removed_block.append(occupant)
                        removed_block.extend(self._remove_continuations_helper(occupant))
            if can_clear and self._can_schedule(troop, get_activity_by_name("Sailing"), start_slot, delta_day):
                self.schedule.add_entry(start_slot, get_activity_by_name("Sailing"), troop)
                fixes += 1
                print(f"  {troop.name}: Sailing moved to {delta_day.value} to pair with Delta")
                continue

            # Restore if failed
            for entry in removed_block:
                if entry not in self.schedule.entries:
                    self.schedule.entries.append(entry)
            for entry in removed_sailing:
                if entry not in self.schedule.entries:
                    self.schedule.entries.append(entry)

        if fixes == 0:
            print("  No Delta+Sailing pair adjustments needed")
        else:
            print(f"  Paired Delta+Sailing for {fixes} troop(s)")


    def _consolidate_sailing_same_day(self):
        """AGGRESSIVELY consolidate Sailing to cluster 2 sails per day.

        Moves Sailing activities to days that already have 1 sail, maximizing
        the "2 sails per day" pattern for scoring (20 points in evaluation).
        Respects spine constraints and does not create overlaps/gaps.

        FIX 2026-01-30: Corrected logic - find days with 1 sail as TARGETS,
        then find ISOLATED sails (alone on their day) as SOURCES to move TO targets.
        """
        from ...models import Day, TimeSlot
        from collections import defaultdict

        print("\n--- Consolidating Sailing to Cluster 2 Per Day ---")

        sailing = get_activity_by_name("Sailing")
        if not sailing:
            return

        # Build sailing count per day
        def count_sails_per_day():
            sailing_by_day = defaultdict(list)
            for entry in self.schedule.entries:
                if entry.activity.name == "Sailing":
                    day = entry.time_slot.day
                    slot = entry.time_slot.slot_number
                    # Only count start entries (slot 1, or slot 2 if no slot 1 for same troop/day)
                    if slot == 1:
                        sailing_by_day[day].append((entry, entry.troop))
                    elif slot == 2:
                        # Slot 2 is a start only if slot 1 isn't Sailing for the same troop/day
                        has_slot1 = any(
                            e.troop == entry.troop and e.activity.name == "Sailing" and
                            e.time_slot.day == day and e.time_slot.slot_number == 1
                            for e in self.schedule.entries
                        )
                        if not has_slot1:
                            sailing_by_day[day].append((entry, entry.troop))
            return sailing_by_day

        sailing_starts_by_day = count_sails_per_day()

        # Log current state
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY]:
            count = len(sailing_starts_by_day.get(day, []))
            troops = [t.name for _, t in sailing_starts_by_day.get(day, [])]
            if count > 0:
                print(f"  {day.value}: {count} sail(s) - {troops}")

        moves = 0
        max_iterations = 5  # Safety limit

        for iteration in range(max_iterations):
            # Refresh counts each iteration
            sailing_starts_by_day = count_sails_per_day()

            # TARGET: Days with exactly 1 sail (want to add a 2nd)
            target_days = [day for day, starts in sailing_starts_by_day.items() 
                          if len(starts) == 1 and day != Day.FRIDAY and day != Day.THURSDAY]

            # SOURCE: Days with exactly 1 sail that could move TO a target
            # (An isolated sail on a day can move to join another isolated sail)
            source_days = [day for day, starts in sailing_starts_by_day.items() 
                          if len(starts) == 1 and day != Day.FRIDAY and day != Day.THURSDAY]

            if len(target_days) < 2:
                # Need at least 2 isolated sails to consolidate
                print(f"  Iteration {iteration+1}: Not enough isolated sails to consolidate ({len(target_days)} found)")
                break

            moved_this_iteration = False

            # Pick first target, find a source that can move to it
            target_day = target_days[0]
            existing_entry, existing_troop = sailing_starts_by_day[target_day][0]
            existing_slot = existing_entry.time_slot.slot_number

            # Find a source day (different from target)
            for source_day in source_days:
                if source_day == target_day:
                    continue

                source_entry, source_troop = sailing_starts_by_day[source_day][0]

                # Check if source_troop is free on target_day
                # Sailing needs 2 consecutive slots (1-2 or 2-3)
                # If existing sail is at slot 1, new sail should be at slot 2
                # If existing sail is at slot 2, new sail should be at slot 1
                if existing_slot == 1:
                    target_slot = TimeSlot(day=target_day, slot_number=2)
                else:
                    target_slot = TimeSlot(day=target_day, slot_number=1)

                # Check if source_troop can move to target_day
                # First, is the troop free on those slots?
                if not self.schedule.is_troop_free(target_slot, source_troop):
                    # Try swapping slot number
                    alt_slot = TimeSlot(day=target_day, slot_number=(1 if target_slot.slot_number == 2 else 2))
                    if not self.schedule.is_troop_free(alt_slot, source_troop):
                        continue
                    target_slot = alt_slot

                # Also check slot+1 for sailing continuation
                next_slot_num = target_slot.slot_number + 1
                if next_slot_num <= 3:
                    next_slot = TimeSlot(day=target_day, slot_number=next_slot_num)
                    if not self.schedule.is_troop_free(next_slot, source_troop):
                        # Troop busy in continuation slot, can't move here
                        continue

                # Check if we can actually schedule sailing there
                if not self._can_schedule(source_troop, sailing, target_slot, target_day):
                    continue

                # Remove source sailing (including continuation)
                source_entries = [e for e in self.schedule.entries 
                                 if e.activity.name == "Sailing" and 
                                 e.troop == source_troop and 
                                 e.time_slot.day == source_day]
                removed_entries = []
                for entry in source_entries:
                    if entry in self.schedule.entries:
                        self.schedule.entries.remove(entry)
                        removed_entries.append(entry)

                # Add sailing at new location
                self.schedule.add_entry(target_slot, sailing, source_troop)
                moves += 1
                moved_this_iteration = True
                print(f"  [MOVE] {source_troop.name}: Sailing {source_day.value} -> {target_day.value} slot {target_slot.slot_number}")

                # Fill the vacated slots on source day
                for entry in removed_entries:
                    vacated_slot = entry.time_slot
                    if self.schedule.is_troop_free(vacated_slot, source_troop):
                        self._fill_vacated_slot(source_troop, vacated_slot)

                break  # Move one sail per iteration

            if not moved_this_iteration:
                print(f"  Iteration {iteration+1}: No valid moves found")
                break

        # Final summary
        sailing_starts_by_day = count_sails_per_day()
        days_with_2 = sum(1 for day, starts in sailing_starts_by_day.items() if len(starts) >= 2)
        total_sail_days = len([d for d, s in sailing_starts_by_day.items() if len(s) > 0])

        if moves == 0:
            print(f"  No Sailing moves made. Current: {days_with_2}/{total_sail_days} days with 2+ sails")
        else:
            print(f"  Consolidated {moves} Sailing activity(ies). Now: {days_with_2}/{total_sail_days} days with 2+ sails")


    def _schedule_hc_dg_tuesday(self):
        """
        Schedule History Center and Disc Golf for the top 3 troops that want them.

        NEW RULE: If a troop wants BOTH, they MUST be scheduled back-to-back.
        """
        from ...models import Day

        print("\n--- Early HC/DG Scheduling (Tuesday Only, Top 3) ---")

        hc = get_activity_by_name("History Center")
        dg = get_activity_by_name("Disc Golf")

        tuesday_slots = [s for s in self.time_slots if s.day == Day.TUESDAY]

        # 1. Handle History Center (and Pairs)
        print("  Processing History Center requests...")
        troops_wanting_hc = []
        for troop in self.troops:
            if "History Center" in troop.preferences:
                rank = troop.preferences.index("History Center") + 1
                troops_wanting_hc.append((troop, rank))

        troops_wanting_hc.sort(key=lambda x: x[1])

        for troop, rank in troops_wanting_hc[:3]:
            if self._troop_has_activity(troop, hc):
                continue

            # Check for Pairing Requirement
            wants_dg = "Disc Golf" in troop.preferences
            dg_scheduled = False

            if wants_dg:
                print(f"    {troop.name} wants BOTH HC and DG - attempting back-to-back...")
                # Try consecutive slots (1-2 or 2-3)
                # Note: HC/DG allowed neighbors logic updated in _can_schedule

                # Try 1-2 (HC then DG)
                slot1 = tuesday_slots[0] # Slot 1
                slot2 = tuesday_slots[1] # Slot 2

                slot1_free = self.schedule.is_troop_free(slot1, troop)
                slot2_free = self.schedule.is_troop_free(slot2, troop)
                print(f"      Slot 1 free: {slot1_free}, Slot 2 free: {slot2_free}")

                if slot1_free and slot2_free:
                     # Temporarily add HC to check if DG works next to it
                     if self._can_schedule(troop, hc, slot1, Day.TUESDAY):
                         self._add_to_schedule(slot1, hc, troop)
                         if self._can_schedule(troop, dg, slot2, Day.TUESDAY):
                             self._add_to_schedule(slot2, dg, troop)
                             print(f"    [PAIR SUCCESS] {troop.name}: HC (Tue-1) -> DG (Tue-2)")
                             self._update_progress(troop, "History Center")
                             self._update_progress(troop, "Disc Golf")
                             continue
                         else:
                             print(f"      DG at Slot 2 blocked by constraints")
                             # Revert HC constraint failure
                             e = next(e for e in self.schedule.entries if e.troop==troop and e.time_slot==slot1)
                             self.schedule.entries.remove(e)
                     else:
                         print(f"      HC at Slot 1 blocked by constraints")

                # Try 2-3 (HC then DG)
                slot2 = tuesday_slots[1] # Slot 2
                slot3 = tuesday_slots[2] # Slot 3
                slot2_free = self.schedule.is_troop_free(slot2, troop)
                slot3_free = self.schedule.is_troop_free(slot3, troop)
                print(f"      Slot 2 free: {slot2_free}, Slot 3 free: {slot3_free}")

                if slot2_free and slot3_free:
                     if self._can_schedule(troop, hc, slot2, Day.TUESDAY):
                         self._add_to_schedule(slot2, hc, troop)
                         if self._can_schedule(troop, dg, slot3, Day.TUESDAY):
                             self._add_to_schedule(slot3, dg, troop)
                             print(f"    [PAIR SUCCESS] {troop.name}: HC (Tue-2) -> DG (Tue-3)")
                             self._update_progress(troop, "History Center")
                             self._update_progress(troop, "Disc Golf")
                             continue
                         else:
                             print(f"      DG at Slot 3 blocked by constraints")
                             e = next(e for e in self.schedule.entries if e.troop==troop and e.time_slot==slot2)
                             self.schedule.entries.remove(e)
                     else:
                         print(f"      HC at Slot 2 blocked by constraints")

                # Try reverse? DG then HC? (Usually doesn't matter, but let's stick to standard order or fail to single)
                print(f"    [PAIR FAIL] Could not schedule back-to-back. Falling back to single HC.")

            # Single HC Scheduling
            for slot in tuesday_slots:
                if self.schedule.is_troop_free(slot, troop):
                    if self._can_schedule(troop, hc, slot, Day.TUESDAY):
                        self._add_to_schedule(slot, hc, troop)
                        self._update_progress(troop, "History Center")
                        print(f"    [SUCCESS] {troop.name}: History Center at Tue-{slot.slot_number}")
                        break

        # 2. Handle Disc Golf (Remaining)
        print("  Processing Disc Golf requests...")
        troops_wanting_dg = []
        for troop in self.troops:
            if "Disc Golf" in troop.preferences:
                rank = troop.preferences.index("Disc Golf") + 1
                troops_wanting_dg.append((troop, rank))

        troops_wanting_dg.sort(key=lambda x: x[1])

        for troop, rank in troops_wanting_dg[:3]:
            if self._troop_has_activity(troop, dg):
                # Already scheduled (likely via Pair)
                continue

            # Single DG Scheduling
            for slot in tuesday_slots:
                if self.schedule.is_troop_free(slot, troop):
                    if self._can_schedule(troop, dg, slot, Day.TUESDAY):
                        self._add_to_schedule(slot, dg, troop)
                        self._update_progress(troop, "Disc Golf")
                        print(f"    [SUCCESS] {troop.name}: Disc Golf at Tue-{slot.slot_number}")
                        break


    def _schedule_limited_activities_by_priority(self, max_rank=None):
        """
        Schedule limited-capacity activities by GLOBAL priority across all troops.

        For activities like Troop Shotgun (max 1 per slot) and 3-hour activities (1 per day),
        sort ALL troops who want them by preference rank and schedule highest-ranked first.

        This ensures that if:
        - Troop A wants Shotgun as #2
        - Troop B wants Shotgun as #9
        Then Troop A gets it first, regardless of scheduling phase.

        Also ensures each troop gets at most 1 three-hour activity.

        Args:
            max_rank (int, optional): If set, only schedule requests with preference_index <= max_rank.
                                      Used to prioritize Top 5 Limited before Top 5 General.
        """
        print(f"\n--- Priority Scheduling for Limited Activities (Max Rank: {max_rank if max_rank is not None else 'ALL'}) ---")

        # Per Spine: Allow multiple 3-hour activities per troop - do NOT track or limit

        # Define limited activities that need priority scheduling
        # Added Canoe activities and limited beach activities (Aqua Trampoline, Water Polo)
        # to ensure Top 5 preference priority over lower-ranked requests
        LIMITED_ACTIVITIES = (
            set(self.ACCURACY_ACTIVITIES) | 
            set(self.THREE_HOUR_ACTIVITIES) |
            set(self.CANOE_ACTIVITIES) |
            {'Aqua Trampoline', 'Water Polo'}
        )

        print(f"  Limited activities to check: {LIMITED_ACTIVITIES}")

        # For each limited activity, collect all troops who want it and their ranks
        activity_requests = {}  # activity_name: [(troop, pref_rank), ...]

        for activity_name in LIMITED_ACTIVITIES:
            requests = []
            for troop in self.troops:
                if activity_name in troop.preferences:
                    pref_rank = troop.preferences.index(activity_name)

                    # Filter by max_rank if specified
                    if max_rank is not None and pref_rank > max_rank:
                        continue

                    # Skip if already has this activity
                    activity = get_activity_by_name(activity_name)
                    if not activity:
                        print(f"  WARNING: Activity '{activity_name}' not found by get_activity_by_name!")
                        continue
                    if self._troop_has_activity(troop, activity):
                        # print(f"  {troop.name} already has {activity_name}")
                        continue
                    requests.append((troop, pref_rank))
                    # print(f"  {troop.name} wants {activity_name} at rank #{pref_rank+1}")

            if requests:
                # Sort by preference rank (lower = higher priority)
                requests.sort(key=lambda x: x[1])
                activity_requests[activity_name] = requests

        print(f"  Found {len(activity_requests)} limited activities with requests")

        # Schedule each limited activity in priority order
        scheduled_count = 0
        for activity_name, requests in activity_requests.items():
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue

            is_3hour = activity_name in self.THREE_HOUR_ACTIVITIES
            print(f"  Attempting to schedule {activity_name} for {len(requests)} troops...")

            for troop, pref_rank in requests:
                # Skip if troop already has this activity
                if self._troop_has_activity(troop, activity):
                    continue

                # Get current entries for this troop
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                # Per Spine: Allow multiple 3-hour activities per troop if sufficient days available
                # No limit check needed

                # Try to schedule (Tuesday is allowed for 3-hour activities per Spine rule)
                scheduled = self._try_schedule_activity(troop, activity)
                if scheduled:
                    scheduled_count += 1
                    print(f"  [OK] {troop.name}: {activity_name} (rank #{pref_rank+1})")
                else:
                    print(f"    [FAIL] {troop.name}: {activity_name} failed to schedule")

        print(f"  Scheduled {scheduled_count} limited activities by priority")


    def _schedule_preferences_range(self, start_rank, end_rank):
        """
        Unified per-preference scheduling: iterate through preference ranks start_rank to end_rank.
        """
        print(f"\n--- Per-Preference Scheduling (ranks {start_rank+1}-{end_rank}) ---")

        # Protected activities that cannot be displaced (BRAIN mandatory anchors).
        PROTECTED = set(self.NON_DISPLACEABLE_ACTIVITIES)
        # Protect Multi-Slot Top-10 preferences (Rocks) from being shredded for single-slot Top-5s.
        PROTECTED.update(["Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"])

        placed_count = 0
        failed_top5 = []  # Track Top 5 failures separately (critical)
        failed_top10 = []  # Top 6-10 failures (important)

        # Batch processing (Spine): collect at each priority, resolve conflicts, then place
        for pref_rank in range(start_rank, end_rank):
            if pref_rank < 5:
                print(f"\n  [Top 5 - Batch {pref_rank + 1}] Placing preference #{pref_rank + 1}...")
            elif pref_rank < 10:
                if pref_rank == 5:
                    print(f"\n  [Top 6-10] Prioritizing preferences 6-10...")
                else:
                    print(f"    Preference #{pref_rank+1}...")
            elif pref_rank == 10:
                 print(f"\n  [Top 11-15] Prioritizing preferences 11-15...")
            elif pref_rank == 15:
                 print(f"\n  [Top 16-20] Prioritizing preferences 16-20...")

            # Collect batch: all (troop, activity) at this priority (Spine: batch by priority)
            batch = []
            for troop in self.troops:
                if pref_rank >= len(troop.preferences):
                    continue
                activity_name = troop.preferences[pref_rank]
                activity = get_activity_by_name(activity_name)
                if not activity or self._troop_has_activity(troop, activity):
                    continue
                # Score for conflict resolution (Spine: commissioner day, troop size, early week)
                score = (1 if activity_name in ("Super Troop", "Delta") else 0) * 100
                score += (troop.scouts + troop.adults)
                # Commissioner-day activities get priority (Rifle, Tower, ODS, Archery, Sailing)
                if activity_name in ("Troop Rifle", "Troop Shotgun", "Climbing Tower", "Archery", "Sailing") or \
                   activity_name in self.TOWER_ODS_ACTIVITIES:
                    score += 30
                # Aqua Trampoline: high miss rate (67% of Top 5 misses) - large troops need exclusive
                if activity_name == "Aqua Trampoline":
                    score += 50
                    if (troop.scouts + troop.adults) > 16:
                        score += 40  # Large troops need exclusive slot - prioritize
                batch.append((troop, activity, activity_name, score))

            # Resolve conflicts: sort by score desc (Spine: commissioner day, troop size, early week)
            batch.sort(key=lambda x: -x[3])
            batch = [(t, a, an) for t, a, an, _ in batch]

            for troop, activity, activity_name in batch:
                placed = False
                # ===========================================
                # PASS 1: Try slots prioritized by clustering
                # ===========================================

                # Get slots ordered by clustering preference
                ordered_slots = self._get_cluster_ordered_slots(troop, activity)
                ordered_slots = self._rerank_slots_by_projected_score(
                    troop,
                    activity,
                    ordered_slots,
                    pref_rank,
                )

                # For Top 6-15, prioritize slots that don't create excess days
                # But still try all slots if needed (preference satisfaction > slight clustering cost)
                slots_to_try = ordered_slots.copy()
                clustered_activity_names = set()
                for acts in self._get_cluster_areas_map(include_commissioner=False).values():
                    clustered_activity_names.update(acts)

                # For clustered activities, prefer non-excess-day placements earlier.
                # Keep Top 1-5 flexible to protect satisfaction.
                if activity_name in clustered_activity_names and pref_rank >= 5:
                    # Use per-troop excess check (BRAIN §6 is a per-troop metric).
                    non_excess_slots = [s for s in slots_to_try if not self._would_create_excess_day(activity_name, s.day, troop=troop)]
                    excess_slots = [s for s in slots_to_try if self._would_create_excess_day(activity_name, s.day, troop=troop)]
                    slots_to_try = non_excess_slots + excess_slots  # Try non-excess first

                for slot in slots_to_try:
                    # FIXED: Ensure constraint check passes before scheduling
                    # This prevents improvements from overriding constraint validation
                    if self._can_schedule(troop, activity, slot, slot.day):
                        # Double-check: verify no constraint violations would be created
                        # This is a safety check to ensure improvements don't bypass constraints
                        self._add_to_schedule(slot, activity, troop)
                        # Only print for Top 5
                        if pref_rank < 5:
                            print(f"    {troop.name}: {activity_name} (#{pref_rank + 1}) -> {slot.day.name[:3]}-{slot.slot_number}")
                        placed = True
                        placed_count += 1
                        break

                if placed:
                    continue

                # ===========================================
                # PASS 2: Displace a lower-priority activity (in same slot)
                # ===========================================
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                # Find activities we can displace (lower priority than current)
                displaceable = []
                for entry in troop_entries:
                    if entry.activity.name in PROTECTED:
                        continue
                    try:
                        entry_rank = troop.preferences.index(entry.activity.name)
                    except ValueError:
                        entry_rank = 999  # Not in preferences = very low priority

                    if entry_rank > pref_rank:
                        displaceable.append((entry, entry_rank))

                # Sort by priority (lowest priority first = best to displace)
                displaceable.sort(key=lambda x: x[1], reverse=True)

                for candidate, _ in displaceable:
                    slot = candidate.time_slot
                    snapshot = self._snapshot_scheduler_state()

                    if candidate.activity.name == "Delta":
                        self.delta_was_swapped.add(troop.name)

                    if not self._remove_from_schedule(candidate):
                        self._restore_scheduler_state(snapshot)
                        continue

                    # Try to place the preference
                    if self._can_schedule(troop, activity, slot, slot.day):
                        self._add_to_schedule(slot, activity, troop)
                        if pref_rank < 5:
                            print(f"    {troop.name}: {activity_name} (#{pref_rank + 1}) <- {candidate.activity.name} @ {slot}")
                        placed = True
                        placed_count += 1
                        break
                    self._restore_scheduler_state(snapshot)

                if placed:
                    continue

                # ===========================================
                # PASS 3: Try displacing and placing in ANY other slot
                # ===========================================
                for candidate, _ in displaceable:
                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(candidate):
                        self._restore_scheduler_state(snapshot)
                        continue

                    # Try ALL slots now
                    projected_slots = self._rerank_slots_by_projected_score(
                        troop,
                        activity,
                        list(self.time_slots),
                        pref_rank,
                    )
                    for slot in projected_slots:
                        if self._can_schedule(troop, activity, slot, slot.day):
                            self._add_to_schedule(slot, activity, troop)
                            if pref_rank < 5:
                                print(f"    {troop.name}: {activity_name} (#{pref_rank + 1}) -> {slot} (displaced {candidate.activity.name})")
                            placed = True
                            placed_count += 1
                            break

                    if placed:
                        break
                    self._restore_scheduler_state(snapshot)

                if placed:
                    continue

                # ===========================================
                # PASS 4: Try ANY slot with relaxed constraints
                # ===========================================
                # For higher preferences, we prioritize placement over soft constraints.
                projected_slots = self._rerank_slots_by_projected_score(
                    troop,
                    activity,
                    list(self.time_slots),
                    pref_rank,
                )
                for slot in projected_slots:
                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                        self._add_to_schedule(slot, activity, troop)
                        if pref_rank < 15:
                            print(f"    {troop.name}: {activity_name} (#{pref_rank + 1}) -> {slot} (RELAXED)")
                        placed = True
                        placed_count += 1
                        break

                # Track failures by priority tier
                if not placed:
                    if pref_rank < 5:
                        failed_top5.append((troop.name, activity_name, pref_rank + 1))
                    elif pref_rank < 10:
                        failed_top10.append((troop.name, activity_name, pref_rank + 1))

        print(f"\n  Placement complete: {placed_count} activities scheduled")

        if failed_top5:
            print(f"  [CRITICAL] {len(failed_top5)} Top 5 preferences could not be placed:")
            for troop_name, activity_name, rank in failed_top5:
                print(f"    - {troop_name}: {activity_name} (#{rank})")

        if failed_top10:
            print(f"  [WARNING] {len(failed_top10)} Top 6-10 preferences could not be placed")


    def _aggressive_preference_recovery_clustering_aware(self):
        """
        Aggressively recover Top 6-15 preferences that weren't scheduled in Phase C.4.
        Uses clustering-aware logic: prioritizes preferences that don't create excess days.

        Strategy:
        1. For each troop, find missing Top 6-15 preferences
        2. Try to schedule them, prioritizing ones that don't create excess cluster days
        3. For Top 6-10: Always try (even if creates slight excess)
        4. For Top 11-15: Only if doesn't create excess day
        """
        from ...models import ScheduleEntry
        from ...activities import get_activity_by_name

        print("\n--- Aggressive Top 6-15 Preference Recovery (Clustering-Aware) ---")

        # Protect multi-slot activities (Rocks) from being shredded
        PROTECTED = set(self.NON_DISPLACEABLE_ACTIVITIES).union({"Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"})

        total_recovered = 0

        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled_activities = {e.activity.name for e in troop_entries}

            # Find missing Top 6-15 preferences
            missing_top6_10 = []
            missing_top11_15 = []

            for i in range(5, 15):  # Ranks 6-15 (0-indexed: 5-14)
                if i >= len(troop.preferences):
                    continue
                pref_name = troop.preferences[i]
                if pref_name not in scheduled_activities:
                    activity = get_activity_by_name(pref_name)
                    if activity:
                        if i < 10:
                            missing_top6_10.append((i, pref_name, activity))
                        else:
                            missing_top11_15.append((i, pref_name, activity))

            # Process Top 6-10 first (always prioritize)
            for pref_rank, pref_name, activity in missing_top6_10:
                # Try all slots, prioritizing clustering
                ordered_slots = self._get_cluster_ordered_slots(troop, activity)

                for slot in ordered_slots:
                    if self._can_schedule(troop, activity, slot, slot.day):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"  {troop.name}: {pref_name} (Pref #{pref_rank + 1}) -> {slot.day.name[:3]}-{slot.slot_number}")
                        total_recovered += 1
                        scheduled_activities.add(pref_name)
                        break

                if pref_name in scheduled_activities:
                    continue  # Successfully scheduled

                # If strict failed, try displacing lower-priority activities
                displaceable = []
                for entry in troop_entries:
                    if entry.activity.name in PROTECTED:
                        continue
                    try:
                        entry_rank = troop.preferences.index(entry.activity.name)
                    except ValueError:
                        entry_rank = 999

                    if entry_rank > pref_rank:  # Lower priority
                        displaceable.append((entry, entry_rank))

                displaceable.sort(key=lambda x: x[1], reverse=True)

                for candidate, _ in displaceable:
                    slot = candidate.time_slot

                    # Check if scheduling here would create excess day for this troop
                    if self._would_create_excess_day(pref_name, slot.day, troop=troop):
                        continue  # Skip to preserve clustering

                    # Check if candidate still exists
                    if candidate not in self.schedule.entries:
                        continue

                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(candidate):
                        self._restore_scheduler_state(snapshot)
                        continue
                    if self._can_schedule(troop, activity, slot, slot.day) and self._add_to_schedule(slot, activity, troop):
                        print(f"  {troop.name}: {pref_name} (Pref #{pref_rank + 1}) <- {candidate.activity.name} @ {slot}")
                        total_recovered += 1
                        scheduled_activities.add(pref_name)
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        break
                    else:
                        # Restore if scheduling failed
                        self._restore_scheduler_state(snapshot)

            # Process Top 11-15 (only if doesn't create excess day)
            for pref_rank, pref_name, activity in missing_top11_15:
                # Try all slots, but skip ones that would create excess day
                ordered_slots = self._get_cluster_ordered_slots(troop, activity)

                for slot in ordered_slots:
                    # Check clustering impact - skip if would create excess day for this troop
                    if self._would_create_excess_day(pref_name, slot.day, troop=troop):
                        continue

                    if self._can_schedule(troop, activity, slot, slot.day):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"  {troop.name}: {pref_name} (Pref #{pref_rank + 1}) -> {slot.day.name[:3]}-{slot.slot_number}")
                        total_recovered += 1
                        scheduled_activities.add(pref_name)
                        break

                if pref_name in scheduled_activities:
                    continue  # Successfully scheduled

                # If strict failed, try displacing lower-priority activities (with clustering check)
                displaceable = []
                for entry in troop_entries:
                    if entry.activity.name in PROTECTED:
                        continue
                    try:
                        entry_rank = troop.preferences.index(entry.activity.name)
                    except ValueError:
                        entry_rank = 999

                    if entry_rank > pref_rank:  # Lower priority
                        # Check if swapping would create excess day for this troop
                        if not self._would_create_excess_day(pref_name, entry.time_slot.day, troop=troop):
                            displaceable.append((entry, entry_rank))

                displaceable.sort(key=lambda x: x[1], reverse=True)

                for candidate, _ in displaceable:
                    slot = candidate.time_slot

                    # Check if candidate still exists
                    if candidate not in self.schedule.entries:
                        continue

                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(candidate):
                        self._restore_scheduler_state(snapshot)
                        continue
                    if self._can_schedule(troop, activity, slot, slot.day) and self._add_to_schedule(slot, activity, troop):
                        print(f"  {troop.name}: {pref_name} (Pref #{pref_rank + 1}) <- {candidate.activity.name} @ {slot}")
                        total_recovered += 1
                        scheduled_activities.add(pref_name)
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        break
                    else:
                        # Restore if scheduling failed
                        self._restore_scheduler_state(snapshot)

        if total_recovered > 0:
            print(f"  Recovered {total_recovered} Top 6-15 preferences")
        else:
            print("  No additional Top 6-15 preferences recovered")


    def _guarantee_all_top5(self):
        """
        MANDATORY: GUARANTEE 100% Top 5 satisfaction - ALL Top 5 preferences MUST be scheduled.

        This is MANDATORY - Top 1-5 are required. For any troop missing a Top 5 preference:
        1. Find which Top 5 is missing
        2. Find ANY slot with a lower-priority activity (6+ or fill)
        3. FORCE swap it out for the missing Top 5
        4. Use relaxed constraints if needed to make it work
        """
        from ...models import ScheduleEntry
        from ...activities import get_activity_by_name

        print("\n--- ENHANCED: Guaranteeing 100% non-exempt Top 5 Satisfaction ---")

        # Protect multi-slot activities (Rocks) from being shredded
        PROTECTED = set(self.NON_DISPLACEABLE_ACTIVITIES).union({"Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"})

        swaps_made = 0
        total_recovered = 0
        total_missing = 0
        forced_placements = 0

        for troop in self.troops:
            # Get troop's scheduled activities
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled_activities = {e.activity.name for e in troop_entries}

            # Find missing Top 5 (excluding exempt activities)
            top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            missing_top5 = []

            # Check for exempt activities (capacity-constrained, 2nd+ 3-hour)
            # NOTE: Each troop should only get 1 three-hour activity (multiple troops can have them on same day)
            has_3hr_scheduled = any(e.activity.name in self.THREE_HOUR_ACTIVITIES for e in troop_entries)

            for i, pref in enumerate(top5):
                if pref not in scheduled_activities:
                    # EXEMPT: 2nd+ 3-hour activity if troop already has one
                    if pref in self.THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
                        print(f"    [EXEMPT] {troop.name}: {pref} - troop already has a 3-hour activity")
                        continue
                    missing_top5.append((i, pref))

            if not missing_top5:
                continue

            total_missing += len(missing_top5)
            print(f"  {troop.name}: Missing Top 5 = {[p[1] for p in missing_top5]} [TARGETING 100% NON-EXEMPT RECOVERY]")

            # Try to recover each missing Top 5 preference - MANDATORY
            for pref_rank, missing_pref in missing_top5:
                missing_activity = get_activity_by_name(missing_pref)
                if not missing_activity:
                    print(f"    [SKIP] Activity '{missing_pref}' not found")
                    continue

                # MANDATORY: Try ALL slots, even with relaxed constraints
                placed = False

                # PASS 1: Try normal scheduling
                ordered_slots = self._get_cluster_ordered_slots(troop, missing_activity)
                for slot in ordered_slots:
                    if self._can_schedule(troop, missing_activity, slot, slot.day):
                        self._add_to_schedule(slot, missing_activity, troop)
                        print(f"    [MANDATORY Top 5] {troop.name}: {missing_pref} (#{pref_rank + 1}) -> {slot}")
                        placed = True
                        total_recovered += 1
                        scheduled_activities.add(missing_pref)
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        break

                if placed:
                    continue

                # PASS 2: Try with relaxed constraints
                for slot in ordered_slots:
                    if self._can_schedule(troop, missing_activity, slot, slot.day, relax_constraints=True):
                        self._add_to_schedule(slot, missing_activity, troop)
                        print(f"    [MANDATORY Top 5 RELAXED] {troop.name}: {missing_pref} (#{pref_rank + 1}) -> {slot}")
                        placed = True
                        total_recovered += 1
                        scheduled_activities.add(missing_pref)
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        break

                if placed:
                    continue

                # PASS 3: FORCE swap - displace ANY lower-priority activity (MANDATORY)
                # Find replaceable activities (prefer lowest priority)
                replaceable = []
                for entry in troop_entries:
                    # Get this activity's priority
                    try:
                        entry_priority = troop.preferences.index(entry.activity.name)
                    except ValueError:
                        entry_priority = 999  # Not in preferences at all

                    # Only replace if lower priority than the missing Top 5
                    if entry_priority > pref_rank:
                        # Don't replace mandatory activities (Spine)
                        if entry.activity.name not in PROTECTED:
                            replaceable.append((entry, entry_priority))

                # Sort by priority (highest index = lowest priority = best to replace)
                # Protect multi-slot activities (Rocks) from being displaced by Sand
                replaceable.sort(key=lambda x: (0 if getattr(x[0].activity, 'slots', 1.0) > 1.0 else 1, x[1]), reverse=True)

                success = False

                # PASS 1: Try swapping in the same slot (original behavior)
                for candidate, cand_priority in replaceable:
                    slot = candidate.time_slot

                    # Temporarily remove candidate to test if missing activity fits
                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(candidate):
                        self._restore_scheduler_state(snapshot)
                        continue

                    # NEW: Track if we're swapping out Delta
                    # This allows Super Troop to be scheduled before Delta for this troop
                    if candidate.activity.name == "Delta":
                        self.delta_was_swapped.add(troop.name)

                    if self._can_schedule(troop, missing_activity, slot, slot.day) or self._can_schedule(troop, missing_activity, slot, slot.day, relax_constraints=True):
                        # Success! Add the Top 5 preference (try relaxed if strict failed)
                        if not self._add_to_schedule(slot, missing_activity, troop):
                            self._restore_scheduler_state(snapshot)
                            continue
                        self._update_progress(troop, missing_pref)

                        old_name = candidate.activity.name
                        old_rank = f"#{cand_priority+1}" if cand_priority < 999 else "fill"
                        print(f"    [SWAP] {missing_pref} (Top {pref_rank+1}) <- {old_name} ({old_rank}) at {slot}")
                        swaps_made += 1
                        success = True

                        # Update troop_entries for next iteration
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        break
                    else:
                        # Restore the candidate and try next
                        self._restore_scheduler_state(snapshot)

                        # Un-mark Delta swap if restore happened
                        if candidate.activity.name == "Delta":
                            self.delta_was_swapped.discard(troop.name)

                # PASS 2: If same-slot swap failed, try replacing ANY lower-priority activity
                # and placing the Top 5 in ANY available slot
                # ENHANCED: Now also tries clusterable activities - Top 5 takes priority over clustering
                # clusterable_activities = {'Climbing Tower', 'Troop Rifle', 'Troop Shotgun', 'Archery',
                #                          'Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', 'Monkey\'s Fist'}

                if not success and replaceable:
                    print(f"    [AGGRESSIVE] Trying cross-slot swap for {missing_pref}")

                    # Try removing lowest-priority activity and placing Top 5 anywhere
                    for candidate, cand_priority in replaceable:
                        # Remove the low-priority activity
                        snapshot = self._snapshot_scheduler_state()
                        if not self._remove_from_schedule(candidate):
                            self._restore_scheduler_state(snapshot)
                            continue
                        removed_slot = candidate.time_slot

                        if candidate.activity.name == "Delta":
                            self.delta_was_swapped.add(troop.name)

                        # Try placing Top 5 in ANY slot (strict first, then relaxed)
                        placed = False
                        for slot in self.time_slots:
                            if self._can_schedule(troop, missing_activity, slot, slot.day):
                                if not self._add_to_schedule(slot, missing_activity, troop):
                                    self._restore_scheduler_state(snapshot)
                                    continue
                                self._update_progress(troop, missing_pref)
                                old_name = candidate.activity.name
                                old_rank = f"#{cand_priority+1}" if cand_priority < 999 else "fill"
                                print(f"    [CROSS-SWAP] {missing_pref} (Top {pref_rank+1}) @ {slot} <- {old_name} ({old_rank}) from {removed_slot}")
                                swaps_made += 1
                                placed = True
                                success = True
                                self._fill_vacated_slot(troop, removed_slot)
                                troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                                break
                        if not placed:
                            for slot in self.time_slots:
                                if self._can_schedule(troop, missing_activity, slot, slot.day, relax_constraints=True):
                                    if not self._add_to_schedule(slot, missing_activity, troop):
                                        self._restore_scheduler_state(snapshot)
                                        continue
                                    self._update_progress(troop, missing_pref)
                                    old_name = candidate.activity.name
                                    old_rank = f"#{cand_priority+1}" if cand_priority < 999 else "fill"
                                    print(f"    [CROSS-SWAP RELAXED] {missing_pref} (Top {pref_rank+1}) @ {slot} <- {old_name} ({old_rank}) from {removed_slot}")
                                    swaps_made += 1
                                    placed = True
                                    success = True
                                    self._fill_vacated_slot(troop, removed_slot)
                                    troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                                    break

                        if placed:
                            break
                        else:
                            # Couldn't place Top 5 anywhere, restore candidate
                            self._restore_scheduler_state(snapshot)
                            if candidate.activity.name == "Delta":
                                self.delta_was_swapped.discard(troop.name)

                if not success:
                    # MANDATORY: Try one more time with relaxed constraints on replaceable
                    for candidate, cand_priority in replaceable:
                        slot = candidate.time_slot
                        if candidate not in self.schedule.entries:
                            continue
                        snapshot = self._snapshot_scheduler_state()
                        if not self._remove_from_schedule(candidate):
                            self._restore_scheduler_state(snapshot)
                            continue
                        if self._can_schedule(troop, missing_activity, slot, slot.day, relax_constraints=True) and self._add_to_schedule(slot, missing_activity, troop):
                            print(f"    [MANDATORY Top 5 FORCED] {troop.name}: {missing_pref} (#{pref_rank + 1}) <- {candidate.activity.name} @ {slot} [RELAXED]")
                            total_recovered += 1
                            swaps_made += 1
                            success = True
                            scheduled_activities.add(missing_pref)
                            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                            break
                        else:
                            self._restore_scheduler_state(snapshot)

                if not success:
                    # PASS 5: Reclaim scarce activity from lower-priority troop (global fairness).
                    if self._reclaim_activity_from_lower_priority_troop(
                        target_troop=troop,
                        activity=missing_activity,
                        required_rank=pref_rank,
                        protected_names=PROTECTED,
                    ):
                        total_recovered += 1
                        swaps_made += 1
                        success = True
                        scheduled_activities.add(missing_pref)
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                if not success:
                    # PASS 5: Multi-slot aware window clearing (general fallback).
                    if self._force_place_with_window_clearing(
                        troop=troop,
                        activity=missing_activity,
                        required_rank=pref_rank,
                        protected_names=PROTECTED,
                    ):
                        print(f"    [WINDOW-CLEAR] {troop.name}: {missing_pref} (#{pref_rank + 1}) placed by clearing lower-priority window")
                        total_recovered += 1
                        swaps_made += 1
                        success = True
                        scheduled_activities.add(missing_pref)
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                if not success:
                    print(f"    [CRITICAL FAILURE] Could not schedule MANDATORY Top 5: {missing_pref} for {troop.name}")

        if total_recovered > 0:
            satisfaction_rate = (total_recovered / total_missing * 100) if total_missing > 0 else 100
            print(f"  ENHANCED: Recovered {total_recovered}/{total_missing} Top 5 preferences ({satisfaction_rate:.1f}% satisfaction)")
            print(f"  Swaps made: {swaps_made}, Forced placements: {forced_placements}")

            if satisfaction_rate >= 100:
                print("  [SUCCESS] Achieved 100% non-exempt Top 5 satisfaction target.")
            else:
                print(f"  [CRITICAL] NEEDS WORK: {100 - satisfaction_rate:.1f}% short of non-exempt Top 5 target")
        else:
            print("  All Top 5 already satisfied")


    def _guarantee_minimum_top10(self):
        """
        GUARANTEE: Each troop gets at least 2-3 of their Top 10 preferences.

        Strategy:
        1. Count how many Top 10 preferences each troop has scheduled
        2. If a troop has < 2-3 Top 10 preferences, aggressively schedule more
        3. Prioritize Top 6-10 preferences that aren't scheduled yet
        """
        from ...activities import get_activity_by_name

        print("\n--- Guaranteeing Minimum Top 10 (2-3 per troop) ---")

        # Protect multi-slot activities (Rocks) from being shredded
        PROTECTED = set(self.NON_DISPLACEABLE_ACTIVITIES).union({"Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"})
        MIN_TOP10_REQUIRED = 3  # Require at least 3 of Top 10

        total_recovered = 0

        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled_activities = {e.activity.name for e in troop_entries}

            # Count Top 10 preferences scheduled
            top10 = troop.preferences[:10] if len(troop.preferences) >= 10 else troop.preferences
            top10_scheduled = [p for p in top10 if p in scheduled_activities]
            top10_count = len(top10_scheduled)

            if top10_count >= MIN_TOP10_REQUIRED:
                continue  # Already has minimum

            # Find missing Top 6-10 preferences (Top 1-5 should already be handled)
            missing_top6_10 = []
            for i in range(5, 10):  # Ranks 6-10 (0-indexed: 5-9)
                if i >= len(troop.preferences):
                    break
                pref_name = troop.preferences[i]
                if pref_name not in scheduled_activities:
                    activity = get_activity_by_name(pref_name)
                    if activity:
                        missing_top6_10.append((i, pref_name, activity))

            if not missing_top6_10:
                continue  # No Top 6-10 to schedule

            needed = MIN_TOP10_REQUIRED - top10_count
            print(f"  {troop.name}: Has {top10_count}/10 Top 10, needs {needed} more (missing: {[p[1] for p in missing_top6_10[:needed]]})")

            # Try to schedule up to 'needed' more Top 6-10 preferences
            recovered_this_troop = 0
            for pref_rank, pref_name, activity in missing_top6_10[:needed]:
                if recovered_this_troop >= needed:
                    break

                # Try normal scheduling first
                ordered_slots = self._get_cluster_ordered_slots(troop, activity)
                placed = False

                for slot in ordered_slots:
                    if self._can_schedule(troop, activity, slot, slot.day):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"    {troop.name}: {pref_name} (Pref #{pref_rank + 1}) -> {slot.day.name[:3]}-{slot.slot_number}")
                        recovered_this_troop += 1
                        total_recovered += 1
                        scheduled_activities.add(pref_name)
                        placed = True
                        break

                if placed:
                    continue

                # If normal failed, try displacing lower-priority activities
                # NEVER displace Top 5 to add Top 6-10
                displaceable = []
                for entry in troop_entries:
                    if entry.activity.name in PROTECTED:
                        continue
                    try:
                        entry_rank = troop.preferences.index(entry.activity.name)
                    except ValueError:
                        entry_rank = 999

                    if entry_rank < 5:
                        continue  # Never displace Top 5 for Top 6-10
                    if entry_rank > pref_rank:  # Lower priority
                        displaceable.append((entry, entry_rank))

                displaceable.sort(key=lambda x: x[1], reverse=True)

                for candidate, _ in displaceable:
                    slot = candidate.time_slot
                    if candidate not in self.schedule.entries:
                        continue

                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(candidate):
                        self._restore_scheduler_state(snapshot)
                        continue
                    if self._can_schedule(troop, activity, slot, slot.day):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"    {troop.name}: {pref_name} (Pref #{pref_rank + 1}) <- {candidate.activity.name} @ {slot}")
                        recovered_this_troop += 1
                        total_recovered += 1
                        scheduled_activities.add(pref_name)
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        placed = True
                        break
                    else:
                        self._restore_scheduler_state(snapshot)

                if not placed:
                    # Try with relaxed constraints
                    for slot in ordered_slots:
                        if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                            self._add_to_schedule(slot, activity, troop)
                            print(f"    {troop.name}: {pref_name} (Pref #{pref_rank + 1}) -> {slot.day.name[:3]}-{slot.slot_number} [RELAXED]")
                            recovered_this_troop += 1
                            total_recovered += 1
                            scheduled_activities.add(pref_name)
                            break

        if total_recovered > 0:
            print(f"  Recovered {total_recovered} Top 6-10 preferences to meet minimum requirement")
        else:
            print("  All troops already meet minimum Top 10 requirement")


    def _enforce_mandatory_top5(self):
        """
        MANDATORY ENFORCEMENT - Top 1-5 MUST be satisfied for every troop.

        This is MANDATORY - Top 5 preferences are required. Forcibly displace ANY activity
        (except Reflection and Super Troop - Spine protected) to make room for missing Top 5.
        """
        print("\n--- MANDATORY Top 5 Enforcement (ALL Top 1-5 Required) ---")

        # Activities that cannot be displaced (Spine protected)
        # Protect multi-slot activities (Rocks) from being shredded
        PROTECTED = set(self.NON_DISPLACEABLE_ACTIVITIES).union({"Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"})

        enforcements = 0
        failures = []

        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled = {e.activity.name for e in troop_entries}

            top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            missing = []

            # Exclude exempt activities (2nd+ 3-hour, capacity-constrained)
            # NOTE: Each troop should only get 1 three-hour activity (multiple troops can have them on same day)
            has_3hr_scheduled = any(e.activity.name in self.THREE_HOUR_ACTIVITIES for e in troop_entries)

            for i, pref in enumerate(top5):
                if pref not in scheduled:
                    # EXEMPT: 2nd+ 3-hour activity if troop already has one
                    if pref in self.THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
                        continue  # Exempt - skip
                    # All other missing Top 5 should be recovered
                    missing.append((i, pref))

            if not missing:
                continue

            def get_priority(entry):
                try:
                    return troop.preferences.index(entry.activity.name)
                except ValueError:
                    return 999

            for rank, missing_pref in missing:
                activity = get_activity_by_name(missing_pref)
                if not activity:
                    continue

                # Only displace activities LOWER priority than the missing Top 5 we're placing.
                # Never displace another Top 5 (would create a new miss and prevent near-100% Top 5).
                displaceable = [e for e in troop_entries
                               if e.activity.name not in PROTECTED and get_priority(e) > rank]

                # Sort by priority (lowest priority = best to displace)
                displaceable.sort(key=get_priority, reverse=True)

                placed = False

                # ENHANCED: Try same-slot first, then try ANY slot
                # Pass 1: Try same-slot swaps
                for entry in displaceable:
                    slot = entry.time_slot

                    # Remove and try to place
                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(entry):
                        self._restore_scheduler_state(snapshot)
                        continue

                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True) and self._add_to_schedule(slot, activity, troop):
                        print(f"  [ENFORCED] {troop.name}: {missing_pref} (Top {rank+1}) <- {entry.activity.name} @ {slot}")
                        enforcements += 1
                        placed = True
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        break
                    else:
                        self._restore_scheduler_state(snapshot)

                # Pass 2: If same-slot failed, try ANY slot (more aggressive)
                if not placed and displaceable:
                    # Remove lowest priority activity
                    entry = displaceable[0]
                    removed_slot = entry.time_slot
                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(entry):
                        self._restore_scheduler_state(snapshot)
                        continue

                    # Try placing Top 5 in ANY slot
                    for slot in self.time_slots:
                        if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                            self._add_to_schedule(slot, activity, troop)
                            print(f"  [ENFORCED-ANY] {troop.name}: {missing_pref} (Top {rank+1}) @ {slot} <- {entry.activity.name} from {removed_slot}")
                            enforcements += 1
                            placed = True

                            # Fill vacated slot
                            self._fill_vacated_slot(troop, removed_slot)
                            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                            break

                    if not placed:
                        # Restore if couldn't place
                        self._restore_scheduler_state(snapshot)

                if not placed:
                    if self._reclaim_activity_from_lower_priority_troop(
                        target_troop=troop,
                        activity=activity,
                        required_rank=rank,
                        protected_names=PROTECTED,
                    ):
                        print(f"  [ENFORCED-RECLAIM] {troop.name}: {missing_pref} (Top {rank+1}) via lower-priority reclaim")
                        enforcements += 1
                        placed = True
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                if not placed:
                    if self._force_place_with_window_clearing(
                        troop=troop,
                        activity=activity,
                        required_rank=rank,
                        protected_names=PROTECTED,
                    ):
                        print(f"  [ENFORCED-WINDOW] {troop.name}: {missing_pref} (Top {rank+1}) by clearing lower-priority window")
                        enforcements += 1
                        placed = True
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                if not placed:
                    failures.append((troop.name, missing_pref, rank + 1))

        if enforcements > 0:
            print(f"  Enforced {enforcements} Top 5 preferences")

        if failures:
            print(f"  [ERROR] {len(failures)} Top 5 STILL MISSING:")
            for troop_name, pref, rank in failures:
                print(f"    - {troop_name}: {pref} (Top {rank})")
        else:
            print("  All troops have 100% Top 5 satisfaction!")


    def _recover_missing_top5(self):
        """
        ENHANCED: Ultra-aggressive recovery of missing Top 5 preferences.

        Each missed Top 5 preference costs -24 points (tripled penalty).
        This is the final optimization pass after all other improvements.

        Strategy: Multi-tiered recovery from least to most aggressive:
        1. Smart swaps with same-day activities
        2. Cross-troop activity exchanges  
        3. Constraint-aware displacement of lower priority activities
        4. Emergency placement with relaxed constraints (last resort)
        """
        print("    [Top 5 Recovery] Starting ENHANCED missing Top 5 recovery...")

        recoveries = 0
        total_missing = 0

        for troop in self.troops:
            # Check which Top 5 preferences are missing
            scheduled_activities = set(e.activity.name for e in self.schedule.entries if e.troop == troop)
            top5_preferences = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences

            missing_preferences = []
            for i, pref in enumerate(top5_preferences):
                if pref not in scheduled_activities:
                    # Check exemption rules
                    if pref in ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"]:
                        # Check if troop already has any 3-hour activity
                        has_3hr = any(e.activity.name in ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"] 
                                     for e in self.schedule.entries if e.troop == troop)
                        if has_3hr:
                            continue  # Exempt - already has a 3-hour activity

                    if pref in ("History Center", "Disc Golf"):
                        # Check Tuesday HC/DG exemption
                        tuesday_hc_dg_slots = set()
                        for e in self.schedule.entries:
                            if e.time_slot.day == Day.TUESDAY and e.activity.name in ("History Center", "Disc Golf"):
                                tuesday_hc_dg_slots.add(e.time_slot.slot_number)
                        if tuesday_hc_dg_slots >= {1, 2, 3}:
                            continue  # Exempt - all Tuesday slots full with HC/DG

                    missing_preferences.append((i, pref))  # (rank, activity)

            if not missing_preferences:
                continue

            total_missing += len(missing_preferences)
            print(f"      [Top 5] {troop.name}: Missing {len(missing_preferences)} Top 5 preferences")

            # Try to recover each missing preference
            for rank, missing_pref in missing_preferences:
                # ENHANCED: Multi-strategy recovery

                # Strategy 1: Smart same-day swaps
                recovered = self._smart_same_day_swap(troop, missing_pref, rank)
                if recovered:
                    recoveries += 1
                    continue

                # Strategy 2: Cross-troop activity exchanges
                recovered = self._cross_troop_exchange(troop, missing_pref, rank)
                if recovered:
                    recoveries += 1
                    continue

                # Strategy 3: Constraint-aware displacement (for rank 1-2 only)
                if rank < 2:
                    recovered = self._constraint_aware_displacement(troop, missing_pref, rank)
                    if recovered:
                        recoveries += 1
                        continue

                # Strategy 4: Emergency placement (rank 0 only - absolute priority)
                if rank == 0:
                    recovered = self._emergency_placement(troop, missing_pref, rank)
                    if recovered:
                        recoveries += 1
                        continue

        print(f"    [Top 5 Recovery] Recovered {recoveries} out of {total_missing} missing Top 5 preferences")
        return recoveries


    def _smart_same_day_swap(self, troop, missing_pref, rank):
        """Strategy 1: Smart swap with same-day activity."""
        activity = get_activity_by_name(missing_pref)
        if not activity:
            return False

        # Find all available slots for this activity
        available_slots = []
        for slot in self.time_slots:
            if (self.schedule.is_troop_free(slot, troop) and 
                self.schedule.is_activity_available(slot, activity, troop)):
                available_slots.append(slot)

        for target_slot in available_slots:
            # Find what the troop is doing on that day
            day_entries = [e for e in self.schedule.entries 
                          if e.troop == troop and e.time_slot.day == target_slot.day]

            for entry in day_entries:
                # Don't swap with protected activities
                if entry.activity.name in {"Reflection", "Super Troop"}:
                    continue

                # Don't swap with higher priority activities
                if troop.get_priority(entry.activity.name) < rank:
                    continue

                # Check if swap is valid
                if self._can_swap_for_top5(entry, activity, target_slot):
                    # Perform the swap
                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(entry):
                        self._restore_scheduler_state(snapshot)
                        continue
                    if not self._add_to_schedule(target_slot, activity, troop):
                        self._restore_scheduler_state(snapshot)
                        continue

                    print(f"        [Smart Swap] {troop.name}: {entry.activity.name} -> {missing_pref} ({target_slot.day.name[:3]})")
                    return True

        return False


    def _cross_troop_exchange(self, troop, missing_pref, rank):
        """Strategy 2: Cross-troop activity exchange."""
        activity = get_activity_by_name(missing_pref)
        if not activity:
            return False

        # Find troops that have the missing activity but might prefer something else
        for other_troop in self.troops:
            if other_troop == troop:
                continue

            # Check if other troop has the missing activity
            other_entries = [e for e in self.schedule.entries 
                           if e.troop == other_troop and e.activity.name == missing_pref]

            if not other_entries:
                continue

            for other_entry in other_entries:
                # Check if our troop can take that slot
                if not self.schedule.is_troop_free(other_entry.time_slot, troop):
                    continue

                # Find what our troop could offer in exchange
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                for troop_entry in troop_entries:
                    if troop_entry.activity.name in {"Reflection", "Super Troop"}:
                        continue

                    # Check if other troop is free and would prefer this activity
                    if not self.schedule.is_troop_free(troop_entry.time_slot, other_troop):
                        continue

                    # Check if other troop prefers this activity
                    other_priority = other_troop.get_priority(troop_entry.activity.name)
                    if other_priority >= 20:  # Not in their top 20
                        continue

                    # Check if swap is valid for both
                    if (self._can_schedule(troop, activity, other_entry.time_slot, other_entry.time_slot.day) and
                        self._can_schedule(other_troop, troop_entry.activity, troop_entry.time_slot, troop_entry.time_slot.day)):

                        # Perform the exchange
                        snapshot = self._snapshot_scheduler_state()
                        if not self._remove_from_schedule(other_entry):
                            self._restore_scheduler_state(snapshot)
                            continue
                        if not self._remove_from_schedule(troop_entry):
                            self._restore_scheduler_state(snapshot)
                            continue

                        if not self._add_to_schedule(other_entry.time_slot, activity, troop):
                            self._restore_scheduler_state(snapshot)
                            continue
                        if not self._add_to_schedule(troop_entry.time_slot, troop_entry.activity, other_troop):
                            self._restore_scheduler_state(snapshot)
                            continue

                        print(f"        [Cross Exchange] {troop.name} <-> {other_troop.name}: {missing_pref} for {troop_entry.activity.name}")
                        return True

        return False


    def _constraint_aware_displacement(self, troop, missing_pref, rank):
        """Strategy 3: Displace lower priority activities with constraint awareness."""
        activity = get_activity_by_name(missing_pref)
        if not activity:
            return False

        # Find all available slots (even if currently occupied)
        for slot in self.time_slots:
            if not self.schedule.is_activity_available(slot, activity, troop):
                continue

            # Check what's currently in this slot
            current_entries = [e for e in self.schedule.entries 
                             if e.time_slot == slot and e.troop != troop]

            for current_entry in current_entries:
                # Don't displace from same troop
                if current_entry.troop == troop:
                    continue

                # Check if this is a low-priority activity we can displace
                current_priority = current_entry.troop.get_priority(current_entry.activity.name)

                # Only displace if current priority is much lower than our missing preference
                if current_priority <= rank + 5:
                    continue

                # Try to find an alternative for the displaced troop
                if self._find_alternative_for_displaced(current_entry):
                    # Perform the displacement
                    self.schedule.remove_entry(current_entry)
                    self.schedule.add_entry(slot, activity, troop)

                    print(f"        [Displacement] {troop.name}: {missing_pref} (displaced {current_entry.troop.name} {current_entry.activity.name})")
                    return True

        return False


    def _emergency_placement(self, troop, missing_pref, rank):
        """Strategy 4: Emergency placement with relaxed constraints (rank 0 only)."""
        activity = get_activity_by_name(missing_pref)
        if not activity:
            return False

        # Try ANY available slot with relaxed constraints
        for slot in self.time_slots:
            if self.schedule.is_troop_free(slot, troop):
                # Use relaxed constraints for emergency placement
                if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                    self.schedule.add_entry(slot, activity, troop)
                    print(f"        [Emergency] {troop.name}: {missing_pref} placed with relaxed constraints")
                    return True

        return False


    def _can_swap_for_top5(self, entry, new_activity, target_slot):
        """Check if a swap for Top 5 recovery is valid."""
        troop = entry.troop

        # Check if new activity can go in target slot
        if not self._can_schedule(troop, new_activity, target_slot, target_slot.day):
            return False

        # Check if current activity can be moved elsewhere (same day)
        for slot in self.time_slots:
            if slot.day == entry.time_slot.day and slot.slot_number != entry.time_slot.slot_number:
                if self.schedule.is_troop_free(slot, troop):
                    if self._can_schedule(troop, entry.activity, slot, slot.day):
                        return True

        return False


    def _find_alternative_for_displaced(self, displaced_entry):
        """Find an alternative activity/slot for a displaced entry."""
        troop = displaced_entry.troop

        # Try to find any available slot for this activity
        for slot in self.time_slots:
            if self.schedule.is_troop_free(slot, troop):
                if self._can_schedule(troop, displaced_entry.activity, slot, slot.day):
                    return slot

        # Try to find a different activity the troop might like
        for pref in troop.preferences[:10]:  # Top 10
            if pref == displaced_entry.activity.name:
                continue

            activity = get_activity_by_name(pref)
            if not activity:
                continue

            for slot in self.time_slots:
                if self.schedule.is_troop_free(slot, troop):
                    if self._can_schedule(troop, activity, slot, slot.day):
                        # Place the alternative activity
                        self.schedule.add_entry(slot, activity, troop)
                        return slot

        return None


    def _ultra_aggressive_top5_recovery(self, troop, activity, missing_pref, rank):
        """
        Ultra-aggressive recovery for Top 3 activities using cross-day consolidation.
        """
        failures = []
        PROTECTED = {"Reflection", "Super Troop", "Delta", "Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"}

        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled = {e.activity.name for e in troop_entries}

            top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            missing = []

            # Check for missing Top 5 (with exemptions)
            has_3hr_scheduled = any(e.activity.name in self.THREE_HOUR_ACTIVITIES for e in troop_entries)

            for i, pref in enumerate(top5):
                if pref not in scheduled:
                    # EXEMPT: 2nd+ 3-hour activity if troop already has one
                    if pref in self.THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
                        continue
                    # EXEMPT: History Center/Disc Golf if Tuesday is full
                    tuesday_hc_dg_slots = set()
                    for e in self.schedule.entries:
                        if e.time_slot.day == Day.TUESDAY and e.activity.name in ("History Center", "Disc Golf"):
                            tuesday_hc_dg_slots.add(e.time_slot.slot_number)
                    hc_dg_tuesday_full = tuesday_hc_dg_slots >= {1, 2, 3}
                    if pref in ("History Center", "Disc Golf") and hc_dg_tuesday_full:
                        continue
                    missing.append((i, pref))

            if not missing:
                continue

            for rank, missing_pref in missing:
                activity = get_activity_by_name(missing_pref)
                if not activity:
                    continue

                # ENHANCED: Try more aggressive displacement strategies

                # Strategy 1: Find lowest priority displaceable entries
                displaceable = [e for e in troop_entries if e.activity.name not in PROTECTED]

                def get_priority(entry):
                    try:
                        return troop.preferences.index(entry.activity.name)
                    except ValueError:
                        return 999

                displaceable.sort(key=get_priority, reverse=True)

                placed = False

                # Strategy 2: Try ANY available slot with relaxed constraints
                for slot in self.time_slots:
                    # Remove lowest priority activity to make room
                    if displaceable:
                        entry = displaceable[0]
                        removed_slot = entry.time_slot

                        # Temporarily remove the entry
                        try:
                            self.schedule.entries.remove(entry)
                        except ValueError:
                            # Entry already removed, skip
                            continue

                        # Try placing the missing Top 5 activity
                        if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                            self._add_to_schedule(slot, activity, troop)
                            print(f"  [RECOVERED] {troop.name}: {missing_pref} (Top {rank+1}) @ {slot} <- {entry.activity.name}")
                            recoveries += 1
                            placed = True

                            # Try to place the displaced activity back in a different slot
                            self._fill_vacated_slot(troop, removed_slot)
                            break
                        else:
                            # Restore if couldn't place
                            self.schedule.entries.append(entry)

                # Strategy 3: If still not placed, try swapping with another troop
                if not placed:
                    for other_troop in self.troops:
                        if other_troop == troop:
                            continue

                        other_entries = [e for e in self.schedule.entries if e.troop == other_troop]
                        other_displaceable = [e for e in other_entries if e.activity.name not in PROTECTED]

                        for other_entry in other_displaceable:
                            # Check if we can swap
                            other_slot = other_entry.time_slot

                            # Temporarily remove both entries
                            try:
                                self.schedule.entries.remove(other_entry)
                            except ValueError:
                                # Entry already removed, skip
                                continue

                            if self._can_schedule(troop, activity, other_slot, other_slot.day, relax_constraints=True):
                                self._add_to_schedule(other_slot, activity, troop)
                                print(f"  [SWAPPED] {troop.name}: {missing_pref} (Top {rank+1}) @ {other_slot} <- {other_troop.name}:{other_entry.activity.name}")
                                recoveries += 1
                                placed = True
                                break
                            else:
                                # Restore if couldn't place
                                self.schedule.entries.append(other_entry)

                        if placed:
                            break

                # ENHANCED: Strategy 4 - Ultra-aggressive cross-day activity consolidation
                if not placed and rank < 3:  # Only for Top 3 activities
                    # Temporarily disabled due to bug - main optimizations working well
                    # placed = self._ultra_aggressive_top5_recovery(troop, activity, missing_pref, rank)
                    # if placed:
                    #     recoveries += 1
                    pass

                if not placed:
                    failures.append((troop.name, missing_pref, rank + 1))

        if recoveries > 0:
            print(f"  Recovered {recoveries} missing Top 5 preferences")

        if failures:
            print(f"  [WARNING] {len(failures)} Top 5 still missing:")
            for troop_name, pref, rank in failures:
                print(f"    - {troop_name}: {pref} (Top {rank})")
        else:
            print("  All missing Top 5 preferences recovered!")


    def _ultra_aggressive_top5_recovery(self, troop, activity, missing_pref, rank):
        """
        Ultra-aggressive recovery for Top 3 activities using cross-day consolidation.

        This method:
        - Creates space by consolidating scattered activities
        - Moves activities to create optimal slots
        - Uses constraint-aware placement
        """
        # Get all troop entries
        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

        # Group activities by day to find consolidation opportunities
        day_activities = {}
        for entry in troop_entries:
            day = entry.time_slot.day
            if day not in day_activities:
                day_activities[day] = []
            day_activities[day].append(entry)

        # Look for days with scattered activities that could be consolidated
        for day, entries in day_activities.items():
            if len(entries) <= 1:
                continue

            # Try to consolidate activities on this day to free up a slot
            for entry in entries:
                if entry.activity.name in {"Reflection", "Super Troop"}:
                    continue  # Don't move protected activities

                # Try to move this activity to another day where it fits better
                for other_day, other_entries in day_activities.items():
                    if other_day == day:
                        continue

                    # Check if we can move this activity to the other day
                    for other_entry in other_entries:
                        if other_entry.activity.name in {"Reflection", "Super Troop"}:
                            continue

                        # Try swapping the activities between days
                        entry_slot = entry.time_slot
                        other_slot = other_entry.time_slot

                        # Temporarily remove both entries
                        try:
                            self.schedule.entries.remove(entry)
                            self.schedule.entries.remove(other_entry)
                        except ValueError:
                            # Entry already removed, skip
                            continue

                        # Check if we can place the missing Top 5 in the freed slot
                        if self._can_schedule(troop, activity, entry_slot, entry_slot.day, relax_constraints=True):
                            # Place the Top 5 activity
                            self._add_to_schedule(entry_slot, activity, troop)

                            # Try to place the displaced activities
                            can_place_others = True

                            # Try to place entry in other_slot
                            if not self._can_schedule(troop, entry.activity, other_slot, other_slot.day, relax_constraints=True):
                                can_place_others = False
                            else:
                                self._add_to_schedule(other_slot, entry.activity, troop)

                            # Try to place other_entry in its original slot
                            if can_place_others:
                                if not self._can_schedule(troop, other_entry.activity, other_entry.time_slot, other_entry.time_slot.day, relax_constraints=True):
                                    # Remove entry and try to restore
                                    try:
                                        self.schedule.entries.remove(entry)
                                    except:
                                        pass
                                    can_place_others = False
                                else:
                                    self._add_to_schedule(other_entry.time_slot, other_entry.activity, troop)

                            if can_place_others:
                                print(f"  [ULTRA RECOVERY] {troop.name}: {missing_pref} (Top {rank+1}) @ {entry_slot.day.name}-{entry_slot.slot_number}")
                                print(f"                  Consolidated: {entry.activity.name} -> {other_slot.day.name}-{other_slot.slot_number}")
                                return True
                            else:
                                # Restore everything if couldn't place
                                try:
                                    if entry in self.schedule.entries:
                                        self.schedule.entries.remove(entry)
                                    if other_entry in self.schedule.entries:
                                        self.schedule.entries.remove(other_entry)
                                except:
                                    pass
                                self._add_to_schedule(entry_slot, entry.activity, troop)
                                self._add_to_schedule(other_slot, other_entry.activity, troop)
                        else:
                            # Restore if couldn't place Top 5
                            self._add_to_schedule(entry_slot, entry.activity, troop)
                            self._add_to_schedule(other_slot, other_entry.activity, troop)

        return False


    def _guarantee_top10_with_exceptions(self):
        """
        Guarantee Top 10 preferences unless legitimate exceptions apply.

        Exceptions (activities that may not fit due to constraints):
        - 3-hour off-camp activities (limited to 1 per day)
        - Sailing (beach slot constraints)
        """
        print("\n--- Guaranteeing Top 10 (with exceptions) ---")

        # Activities that can be skipped if constraints don't allow
        EXCEPTIONS = {
            'Itasca State Park',       # 3-hour, limited
            'Tamarac Wildlife Refuge', # 3-hour, limited
            'Back of the Moon',        # 3-hour, limited
            'Sailing',                 # Beach slot constraints
        }

        PROTECTED = {"Reflection", "Delta", "Super Troop", "Sailing", "Float for Floats", "Canoe Snorkel", "Climbing Tower"}

        recoveries = 0
        skipped = []

        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled = {e.activity.name for e in troop_entries}

            top10 = troop.preferences[:10] if len(troop.preferences) >= 10 else troop.preferences
            missing = [(i, pref) for i, pref in enumerate(top10) if pref not in scheduled]

            if not missing:
                continue

            for rank, missing_pref in missing:
                # Skip exceptions
                if missing_pref in EXCEPTIONS:
                    skipped.append((troop.name, missing_pref, rank + 1))
                    continue

                activity = get_activity_by_name(missing_pref)
                if not activity:
                    continue

                # Find replaceable activities (non-Top 10, non-protected)
                # NEVER replace Top 5 preferences to add Top 10 - Top 5 has strict priority
                replaceable = []
                for entry in troop_entries:
                    try:
                        entry_rank = troop.preferences.index(entry.activity.name)
                    except ValueError:
                        entry_rank = 999

                    if entry_rank < 5:
                        continue  # Never replace Top 5 for Top 10 recovery
                    if entry_rank > rank and entry.activity.name not in PROTECTED:
                        replaceable.append((entry, entry_rank))

                # Protect multi-slot activities (Rocks) from being displaced by Sand
                replaceable.sort(key=lambda x: (0 if getattr(x[0].activity, 'slots', 1.0) > 1.0 else 1, x[1]), reverse=True)

                for entry, _ in replaceable:
                    slot = entry.time_slot

                    snapshot = self._snapshot_scheduler_state()
                    if not self._remove_from_schedule(entry):
                        self._restore_scheduler_state(snapshot)
                        continue

                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"  [Top10] {troop.name}: {missing_pref} (#{rank+1}) <- {entry.activity.name}")
                        recoveries += 1
                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                        break
                    else:
                        self._restore_scheduler_state(snapshot)

        if recoveries > 0:
            print(f"  Recovered {recoveries} Top 10 preferences")

        if skipped:
            print(f"  Skipped {len(skipped)} exceptions (3-hour/constrained activities)")


    def _schedule_all_top6_10(self):
        """Schedule Top 6-10 for all troops (after all Top 5 done).

        Multi-slot activities are prioritized within each round.
        ENHANCED: Better troop ordering and slot selection for improved satisfaction.
        """
        MULTI_SLOT_ACTIVITIES = {"Sailing", "Climbing Tower", "Float for Floats", "Canoe Snorkel",
                                 "Itasca State Park", "Tamarac Wildlife Refuge", "Back of the Moon"}

        # ENHANCED: Order troops by priority (larger troops first for limited activities)
        def troop_priority_key(troop):
            # Larger troops get priority for limited activities
            size = troop.scouts + troop.adults
            # Also consider how many Top 6-10 preferences they have
            top6_10_count = sum(1 for i in range(5, 10) if i < len(troop.preferences))
            return (-size, -top6_10_count)  # Negative for descending order

        sorted_troops = sorted(self.troops, key=troop_priority_key)

        for round_num in range(5):  # 5 preferences (6-10)
            # PHASE 1: Multi-slot activities first
            for troop in sorted_troops:
                for pref_index in range(5, 10):
                    if pref_index >= len(troop.preferences):
                        continue

                    activity_name = troop.preferences[pref_index]
                    if activity_name not in MULTI_SLOT_ACTIVITIES:
                        continue

                    activity = get_activity_by_name(activity_name)

                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    scheduled = self._try_schedule_activity(troop, activity)
                    if scheduled:
                        print(f"    {troop.name}: {activity_name} (Top {pref_index+1}) [MULTI-SLOT PRIORITY]")
                        break # Schedule only one activity per troop per round

            # PHASE 2: Regular activities
            for troop in sorted_troops:
                for pref_index in range(5, 10):
                    if pref_index >= len(troop.preferences):
                        continue

                    activity_name = troop.preferences[pref_index]
                    if activity_name in MULTI_SLOT_ACTIVITIES:
                        continue

                    activity = get_activity_by_name(activity_name)

                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    scheduled = self._try_schedule_activity(troop, activity)
                    if scheduled:
                        print(f"    {troop.name}: {activity_name} (Top {pref_index+1})")
                        break # Schedule only one activity per troop per round


    def _schedule_all_top11_15(self):
        """Schedule Top 11-15 for all troops, one rank at a time.

        Each rank is prioritized individually:
        - All #11s first (highest priority in this group)
        - Then all #12s
        - Then all #13s, etc.
        This ensures preference #11 > #12 > #13 > #14 > #15.

        WITHIN each rank, multi-slot activities (Sailing, Climbing Tower) are scheduled FIRST
        because they're harder to fit and need priority slot selection.
        """
        MULTI_SLOT_ACTIVITIES = {"Sailing", "Climbing Tower", "Float for Floats", "Canoe Snorkel",
                                 "Itasca State Park", "Tamarac Wildlife Refuge", "Back of the Moon"}

        for pref_index in range(10, 15):  # 10=11th, 11=12th, etc.
            pref_rank = pref_index + 1
            print(f"  --- Scheduling all #{pref_rank} preferences ---")

            # PHASE 1: Schedule multi-slot activities first (harder to fit)
            for troop in self.troops:
                if pref_index >= len(troop.preferences):
                    continue

                activity_name = troop.preferences[pref_index]
                if activity_name not in MULTI_SLOT_ACTIVITIES:
                    continue  # Skip, will do in phase 2

                activity = get_activity_by_name(activity_name)

                if not activity or self._troop_has_activity(troop, activity):
                    continue

                scheduled = self._try_schedule_activity(troop, activity)
                if scheduled:
                    print(f"    {troop.name}: {activity_name} (Top {pref_rank}) [MULTI-SLOT PRIORITY]")

            # PHASE 2: Schedule regular activities
            for troop in self.troops:
                if pref_index >= len(troop.preferences):
                    continue

                activity_name = troop.preferences[pref_index]
                if activity_name in MULTI_SLOT_ACTIVITIES:
                    continue  # Already did in phase 1

                activity = get_activity_by_name(activity_name)

                if not activity or self._troop_has_activity(troop, activity):
                    continue

                scheduled = self._try_schedule_activity(troop, activity)
                if scheduled:
                    print(f"    {troop.name}: {activity_name} (Top {pref_rank})")


    def _schedule_all_top16_20(self):
        """Schedule Top 16-20 for all troops, one rank at a time.

        Each rank is prioritized individually:
        - All #16s first (highest priority in this group)
        - Then all #17s
        - Then all #18s, etc.
        This ensures preference #16 > #17 > #18 > #19 > #20.

        WITHIN each rank, multi-slot activities are scheduled FIRST.
        """
        MULTI_SLOT_ACTIVITIES = {"Sailing", "Climbing Tower", "Float for Floats", "Canoe Snorkel",
                                 "Itasca State Park", "Tamarac Wildlife Refuge", "Back of the Moon"}

        for pref_index in range(15, 20):  # 15=16th, 16=17th, etc.
            pref_rank = pref_index + 1
            print(f"  --- Scheduling all #{pref_rank} preferences ---")

            # PHASE 1: Multi-slot activities
            for troop in self.troops:
                if pref_index >= len(troop.preferences):
                    continue

                activity_name = troop.preferences[pref_index]
                if activity_name not in MULTI_SLOT_ACTIVITIES:
                    continue

                activity = get_activity_by_name(activity_name)

                if not activity or self._troop_has_activity(troop, activity):
                    continue

                scheduled = self._try_schedule_activity(troop, activity)
                if scheduled:
                    print(f"    {troop.name}: {activity_name} (Top {pref_rank}) [MULTI-SLOT PRIORITY]")

            # PHASE 2: Regular activities
            for troop in self.troops:
                if pref_index >= len(troop.preferences):
                    continue

                activity_name = troop.preferences[pref_index]
                if activity_name in MULTI_SLOT_ACTIVITIES:
                    continue

                activity = get_activity_by_name(activity_name)

                if not activity or self._troop_has_activity(troop, activity):
                    continue

                scheduled = self._try_schedule_activity(troop, activity)
                if scheduled:
                    print(f"    {troop.name}: {activity_name} (Top {pref_rank})")


    def _fill_all_remaining(self):
        """Fill any empty slots with remaining preferences, then default activities.

        IMPORTANT: Reserves one Friday slot per troop if Reflection hasn't been scheduled yet.
        IMPROVED: Prioritizes ANY remaining preferences (even beyond Top 15) before default fills.
        AGGRESSIVE: First pass fills ALL remaining preferences (especially Top 5) before default fills.
        """
        cluster_map = {
            "Tower": ["Climbing Tower"],
            "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
            "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"],
            "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
        }
        activity_to_area = {}
        for area_name, acts in cluster_map.items():
            for act in acts:
                activity_to_area[act] = area_name

        def _ordered_slots_for_activity(troop: Troop, activity: Activity):
            """Prefer slots that help the official clustering metrics."""
            day_index = {
                Day.MONDAY: 0,
                Day.TUESDAY: 1,
                Day.WEDNESDAY: 2,
                Day.THURSDAY: 3,
                Day.FRIDAY: 4,
            }
            troop_day_counts = defaultdict(int)
            for e in self.schedule.entries:
                if e.troop == troop:
                    troop_day_counts[e.time_slot.day] += 1

            area_name = activity_to_area.get(activity.name)
            area_activities = cluster_map.get(area_name, [])
            area_day_counts = defaultdict(int)
            if area_activities:
                for e in self.schedule.entries:
                    if e.activity.name in area_activities:
                        area_day_counts[e.time_slot.day] += 1

            free_slots = [s for s in self.time_slots if self.schedule.is_troop_free(s, troop)]
            scored = []
            pref_rank = troop.get_priority(activity.name)
            for slot in free_slots:
                score = self._projected_score_delta_for_slot(troop, activity, slot, pref_rank)
                score += troop_day_counts[slot.day] * 0.25
                score += area_day_counts[slot.day] * 0.3
                if would_create_excess_day_for_entries(self.schedule.entries, activity.name, slot.day):
                    score -= 1.0
                scored.append((score, troop_day_counts[slot.day], area_day_counts[slot.day], day_index.get(slot.day, 4), slot.slot_number, slot))
            scored.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3], item[4]))
            return [s for *_, s in scored]

        # PASS 1: Fill remaining preferences using HYBRID priority strategy
        # - Top 10 (ranks 1-10): RANK-BY-RANK across all troops to prevent priority
        #   inversion (e.g. troop A's #13 stealing a slot troop B needed for #9)
        # - Ranks 11+: TROOP-BY-TROOP to preserve existing clustering patterns
        #   where the priority difference matters less

        # --- PASS 1a: Top 10 preferences, globally rank-ordered ---
        top10_remaining = []
        for troop in self.troops:
            for i, pref_name in enumerate(troop.preferences[:10]):
                activity = get_activity_by_name(pref_name)
                if activity and not self._troop_has_activity(troop, activity):
                    top10_remaining.append((troop, pref_name, i))

        # Sort globally by rank (lower = higher priority).
        # Secondary: troop size descending (larger troops harder to place later).
        top10_remaining.sort(key=lambda x: (x[2], -(x[0].scouts + x[0].adults)))

        for troop, pref_name, pref_rank_0 in top10_remaining:
            activity = get_activity_by_name(pref_name)
            if not activity or self._troop_has_activity(troop, activity):
                continue  # May have been placed by an earlier iteration

            for slot in _ordered_slots_for_activity(troop, activity):
                if slot.day == Day.FRIDAY:
                    has_reflection = any(e.activity.name == "Reflection" 
                                        for e in self.schedule.entries 
                                        if e.troop == troop)
                    if not has_reflection:
                        free_friday = sum(1 for s in self.time_slots 
                                         if s.day == Day.FRIDAY and self.schedule.is_troop_free(s, troop))
                        if free_friday <= 1:
                            continue

                if self._can_schedule(troop, activity, slot, slot.day):
                    self._add_to_schedule(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    self.logger.info(f"  [Fill Pref] {troop.name}: {pref_name} -> {slot} (#{pref_rank_0 + 1})")
                    break
                elif self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                    self._add_to_schedule(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    self.logger.info(f"  [Fill Pref Relaxed] {troop.name}: {pref_name} -> {slot} (#{pref_rank_0 + 1})")
                    break

        # --- PASS 1b: Remaining preferences (11+), troop-by-troop ---
        for troop in self.troops:
            for i, pref_name in enumerate(troop.preferences):
                if i < 10:
                    continue  # Already handled in PASS 1a
                activity = get_activity_by_name(pref_name)
                if not activity or self._troop_has_activity(troop, activity):
                    continue

                for slot in _ordered_slots_for_activity(troop, activity):
                    if slot.day == Day.FRIDAY:
                        has_reflection = any(e.activity.name == "Reflection" 
                                            for e in self.schedule.entries 
                                            if e.troop == troop)
                        if not has_reflection:
                            free_friday = sum(1 for s in self.time_slots 
                                             if s.day == Day.FRIDAY and self.schedule.is_troop_free(s, troop))
                            if free_friday <= 1:
                                continue

                    if self._can_schedule(troop, activity, slot, slot.day):
                        self._add_to_schedule(slot, activity, troop)
                        self._update_progress(troop, activity.name)
                        self.logger.info(f"  [Fill Pref] {troop.name}: {pref_name} -> {slot} (#{i + 1})")
                        break
                    elif self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                        self._add_to_schedule(slot, activity, troop)
                        self._update_progress(troop, activity.name)
                        self.logger.info(f"  [Fill Pref Relaxed] {troop.name}: {pref_name} -> {slot} (#{i + 1})")
                        break

        # PASS 2: Fill any remaining empty slots - PREFERENCES FIRST, then default fills
        for troop in self.troops:
            # Build prioritized fill list: remaining preferences (sorted by rank) + default fills
            scheduled_activities = {e.activity.name for e in self.schedule.entries if e.troop == troop}
            remaining_prefs = [p for p in troop.preferences if p not in scheduled_activities]

            # Simple priority: remaining preferences first (in rank order), then defaults
            fill_priority = remaining_prefs + [f for f in self.DEFAULT_FILL_PRIORITY if f not in remaining_prefs]
            troop_day_counts = defaultdict(int)
            for e in self.schedule.entries:
                if e.troop == troop:
                    troop_day_counts[e.time_slot.day] += 1

            ordered_open_slots = sorted(
                [s for s in self.time_slots if self.schedule.is_troop_free(s, troop)],
                key=lambda s: (-troop_day_counts[s.day], 1 if s.day == Day.FRIDAY else 0, s.day.value, s.slot_number),
            )

            for slot in ordered_open_slots:

                # Reserve one Friday slot for Reflection if not scheduled yet
                if slot.day == Day.FRIDAY:
                    has_reflection = any(e.activity.name == "Reflection" 
                                        for e in self.schedule.entries 
                                        if e.troop == troop)
                    if not has_reflection:
                        free_friday = sum(1 for s in self.time_slots 
                                         if s.day == Day.FRIDAY and self.schedule.is_troop_free(s, troop))
                        if free_friday <= 1:
                            continue  # Skip this slot - reserve for Reflection

                # Use prioritized fill list (preferences first, then defaults)
                scheduled = False
                strict_candidates = []
                for fill_name in fill_priority:
                    activity = get_activity_by_name(fill_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue

                    pref_rank = troop.get_priority(fill_name)
                    if pref_rank is not None and pref_rank >= 999:
                        pref_rank = None
                    if (
                        would_create_excess_day_for_entries(self.schedule.entries, activity.name, slot.day)
                        and any(
                            alt != slot
                            and self.schedule.is_troop_free(alt, troop)
                            and not would_create_excess_day_for_entries(self.schedule.entries, activity.name, alt.day)
                            and self._can_schedule(troop, activity, alt, alt.day, relax_constraints=False)
                            for alt in self.time_slots
                        )
                    ):
                        # Delay this placement and prefer an alternative slot/day that
                        # does not create extra day spread for clustered activities.
                        continue

                    # Try strict constraints first
                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=False):
                        strict_candidates.append(
                            (
                                self._projected_score_delta_for_slot(troop, activity, slot, pref_rank),
                                -(pref_rank if pref_rank is not None else 999),
                                fill_name,
                                activity,
                                pref_rank,
                            )
                        )

                if strict_candidates:
                    strict_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
                    _, _, fill_name, activity, pref_rank = strict_candidates[0]
                    self._add_to_schedule(slot, activity, troop)
                    rank_info = f" (Pref #{pref_rank + 1})" if pref_rank is not None else ""
                    self.logger.info(f"  [Fill] {troop.name}: {fill_name}{rank_info} -> {slot}")
                    scheduled = True
                    scheduled_activities.add(fill_name)

                # If strict failed, try with relaxed constraints (especially for preferences)
                if not scheduled:
                    relaxed_candidates = []
                    for fill_name in fill_priority:
                        activity = get_activity_by_name(fill_name)
                        if not activity or self._troop_has_activity(troop, activity):
                            continue

                        pref_rank = troop.get_priority(fill_name)
                        if pref_rank is not None and pref_rank >= 999:
                            pref_rank = None
                        # Only relax constraints for preferences (not generic fills)
                        if pref_rank is not None:
                            if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                                relaxed_candidates.append(
                                    (
                                        self._projected_score_delta_for_slot(troop, activity, slot, pref_rank),
                                        -pref_rank,
                                        fill_name,
                                        activity,
                                        pref_rank,
                                    )
                                )
                    if relaxed_candidates:
                        relaxed_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
                        _, _, fill_name, activity, pref_rank = relaxed_candidates[0]
                        self._add_to_schedule(slot, activity, troop)
                        rank_info = f" (Pref #{pref_rank + 1} RELAXED)"
                        self.logger.info(f"  [Fill] {troop.name}: {fill_name}{rank_info} -> {slot}")
                        scheduled = True
                        scheduled_activities.add(fill_name)


    def _schedule_smart_balls(self):
        """
        Smart balls scheduling: Place deferred Gaga Ball and 9 Square activities
        as flexible transition fills after long-distance activities.

        Strategy:
        1. Find troops needing balls activities (had them in Top 6+)
        2. Prefer Slot 2 after Delta/Tower/ODS/Wet activities (good transitions)
        3. Fill remaining empty slots
        """
        from ...activities import get_activity_by_name

        BALLS_ACTIVITIES = ["Gaga Ball", "9 Square"]
        LONG_DISTANCE_ACTIVITIES = [
            "Delta", "Super Troop",  # Far from center
            "Climbing Tower", "Knots and Lashings", "Orienteering",  # Tower/ODS
            "Ultimate Survivor", "What's Cooking", "Chopped!",
            "Aqua Trampoline", "Troop Swim", "Underwater Obstacle Course",  # Wet activities
        ]

        # Find troops needing balls
        troops_needing_balls = []
        for troop in self.troops:
            for pref_name in troop.preferences:
                if pref_name in BALLS_ACTIVITIES:
                    activity = get_activity_by_name(pref_name)
                    if activity and not self._troop_has_activity(troop, activity):
                        troops_needing_balls.append((troop, activity))
                        break

        if not troops_needing_balls:
            print("  No deferred balls activities to schedule")
            return

        scheduled_count = 0

        # Priority 1: Slot 2 after long-distance activities
        for troop, balls_activity in troops_needing_balls[:]:
            if balls_activity.name not in [e.activity.name for e in self.schedule.entries if e.troop == troop]:
                for day in Day:
                    day_slots = [s for s in self.time_slots if s.day == day]
                    slot_2 = [s for s in day_slots if s.slot_number == 2][0] if len(day_slots) >= 2 else None

                    if not slot_2 or not self.schedule.is_troop_free(slot_2, troop):
                        continue

                    # Check if Slot 1 has a long-distance activity
                    slot_1 = [s for s in day_slots if s.slot_number == 1][0]
                    slot_1_activities = [e.activity.name for e in self.schedule.entries 
                                        if e.troop == troop and e.time_slot == slot_1]

                    if slot_1_activities and slot_1_activities[0] in LONG_DISTANCE_ACTIVITIES:
                        # Perfect spot! After a long-distance activity
                        if self._can_schedule(troop, balls_activity, slot_2, day):
                            self.schedule.add_entry(slot_2, balls_activity, troop)
                            self._update_progress(troop, balls_activity.name)
                            print(f"  [Smart Ball] {troop.name}: {balls_activity.name} -> {slot_2} " +
                                  f"(after {slot_1_activities[0]})")
                            troops_needing_balls.remove((troop, balls_activity))
                            scheduled_count += 1
                            break

        # Priority 2: Fill any remaining empty slots
        for troop, balls_activity in troops_needing_balls[:]:
            for slot in self.time_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    continue

                if self._can_schedule(troop, balls_activity, slot, slot.day, relax_constraints=True):
                    self.schedule.add_entry(slot, balls_activity, troop)
                    self._update_progress(troop, balls_activity.name)
                    print(f"  [Smart Ball] {troop.name}: {balls_activity.name} -> {slot}")
                    troops_needing_balls.remove((troop, balls_activity))
                    scheduled_count += 1
                    break

        if scheduled_count > 0:
            print(f"  Scheduled {scheduled_count} balls activities as smart fills")
        else:
            print("  No slots available for balls activities")


    def _aggressive_aqua_trampoline_sharing(self):
        """
        Aggressively identify and pair troops that can share Aqua Trampoline.
        Strategy:
        1. Find all troops with Aqua Trampoline scheduled solo (not sharing)
        2. Find compatible troops (≤16 scouts+adults) that want Aqua Trampoline
        3. Try to move/swap to pair them together
        4. Protect existing sharing unless swap enables sharing elsewhere
        """
        from ...activities import get_activity_by_name

        AT_ACTIVITY = get_activity_by_name("Aqua Trampoline")
        if not AT_ACTIVITY:
            return

        AT_MAX_SIZE = 16  # scouts + adults

        # Find all troops with Aqua Trampoline scheduled
        at_entries = [e for e in self.schedule.entries if e.activity.name == "Aqua Trampoline"]

        # Group by slot to identify sharing opportunities
        slot_groups = defaultdict(list)
        for entry in at_entries:
            key = (entry.time_slot.day, entry.time_slot.slot_number)
            slot_groups[key].append(entry)

        # Find troops that are sharing (2 per slot)
        sharing_slots = {slot: entries for slot, entries in slot_groups.items() if len(entries) >= 2}

        # Find troops that are solo (1 per slot) and could share
        solo_slots = {slot: entries[0] for slot, entries in slot_groups.items() if len(entries) == 1}

        # Find troops that want Aqua Trampoline but don't have it
        troops_wanting_at = []
        for troop in self.troops:
            troop_size = troop.scouts + troop.adults
            if troop_size <= AT_MAX_SIZE:
                has_at = any(e.activity.name == "Aqua Trampoline" for e in self.schedule.entries if e.troop == troop)
                wants_at = "Aqua Trampoline" in troop.preferences
                if wants_at and not has_at:
                    troops_wanting_at.append((troop, troop_size))

        # Sort by size (smaller first for better pairing)
        troops_wanting_at.sort(key=lambda x: x[1])

        swaps_made = 0

        # Strategy 1: Try to pair solo AT troops with compatible troops wanting AT
        for (day, slot_num), solo_entry in list(solo_slots.items()):
            solo_troop = solo_entry.troop
            solo_size = solo_troop.scouts + solo_troop.adults

            if solo_size > AT_MAX_SIZE:
                continue  # Can't share - too large

            # Find a compatible troop that wants AT
            for wanting_troop, wanting_size in troops_wanting_at:
                if wanting_troop == solo_troop:
                    continue

                # Check if they can share (both ≤16)
                if wanting_size <= AT_MAX_SIZE:
                    # Try to schedule wanting_troop in the same slot
                    slot = TimeSlot(day=day, slot_number=slot_num)
                    if self.schedule.is_troop_free(slot, wanting_troop):
                        if self._can_schedule(wanting_troop, AT_ACTIVITY, slot, day):
                            self._add_to_schedule(slot, AT_ACTIVITY, wanting_troop)
                            self._update_progress(wanting_troop, "Aqua Trampoline")
                            print(f"  [AT Share] Paired {wanting_troop.name} ({wanting_size}) with {solo_troop.name} ({solo_size}) at {day.name} slot {slot_num}")
                            swaps_made += 1
                            # Remove from wanting list
                            troops_wanting_at = [(t, s) for t, s in troops_wanting_at if t != wanting_troop]
                            break

        # Strategy 2: Try to move solo AT troops to slots where another small troop has AT
        for (day, slot_num), solo_entry in list(solo_slots.items()):
            solo_troop = solo_entry.troop
            solo_size = solo_troop.scouts + solo_troop.adults

            if solo_size > AT_MAX_SIZE:
                continue

            # Look for other slots with solo AT troops that could share
            for (other_day, other_slot), other_entry in solo_slots.items():
                if (other_day, other_slot) == (day, slot_num):
                    continue

                other_troop = other_entry.troop
                other_size = other_troop.scouts + other_troop.adults

                if other_size > AT_MAX_SIZE:
                    continue

                # Try moving solo_troop to other_slot
                other_slot_obj = TimeSlot(day=other_day, slot_number=other_slot)
                if self.schedule.is_troop_free(other_slot_obj, solo_troop):
                    # Check if we can move the activity
                    if self._can_schedule(solo_troop, AT_ACTIVITY, other_slot_obj, other_day):
                        # Remove old entry via safe wrapper
                        if self._remove_from_schedule(solo_entry):
                            # Add to new slot
                            self._add_to_schedule(other_slot_obj, AT_ACTIVITY, solo_troop)
                            print(f"  [AT Share] Moved {solo_troop.name} ({solo_size}) to share with {other_troop.name} ({other_size}) at {other_day.name} slot {other_slot}")
                            swaps_made += 1
                            # Fill vacated slot
                            vacated_slot = TimeSlot(day=day, slot_number=slot_num)
                            self._fill_vacated_slot(solo_troop, vacated_slot)
                            break

        if swaps_made > 0:
            print(f"  Created {swaps_made} Aqua Trampoline sharing pairs")
        else:
            print("  No additional Aqua Trampoline sharing opportunities found")
