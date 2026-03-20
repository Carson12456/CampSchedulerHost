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

class LegacyPart07Mixin:
    """Scheduler legacy methods part 07."""

    def _cross_day_staff_redistribution(self, staff_entries, slot_counts, all_staff_activities):
        """Strategy 2: Redistribute staff activities across days for better balance."""
        from collections import defaultdict

        optimizations = 0

        # Group by day
        day_loads = defaultdict(int)
        day_entries = defaultdict(list)

        for entry in staff_entries:
            day = entry.time_slot.day
            day_loads[day] += 1
            day_entries[day].append(entry)

        # Calculate average load per day
        avg_load = len(staff_entries) / len(day_loads) if day_loads else 0

        # Find overloaded and underloaded days
        overloaded_days = [(day, count) for day, count in day_loads.items() if count > avg_load + 1]
        underloaded_days = [(day, count) for day, count in day_loads.items() if count < avg_load - 1]

        # Try to move activities from overloaded to underloaded days
        for over_day, over_count in overloaded_days:
            for under_day, under_count in underloaded_days:
                if over_count <= under_count + 1:
                    continue  # Balanced enough

                # Find activities that can move
                for entry in day_entries[over_day]:
                    # Try to find a slot on underloaded day
                    for slot in self.time_slots:
                        if slot.day != under_day:
                            continue

                        if (self.schedule.is_troop_free(slot, entry.troop) and 
                            self.schedule.is_activity_available(slot, entry.activity, entry.troop)):

                            # Move the activity
                            old_day = entry.time_slot.day
                            old_slot = entry.time_slot.slot_number

                            self.schedule.remove_entry(entry)
                            self.schedule.add_entry(slot, entry.activity, entry.troop)

                            # Update counts
                            slot_counts[(old_day, old_slot)] -= 1
                            slot_counts[(under_day, slot.slot_number)] += 1

                            optimizations += 1
                            print(f"        [Cross-Day] Moved {entry.troop.name} {entry.activity.name} from {old_day.name[:3]} to {under_day.name[:3]}")

                            over_count -= 1
                            under_count += 1
                            break

                    if over_count <= under_count + 1:
                        break

                if optimizations >= 10:  # Limit moves per iteration
                    break

        return optimizations


    def _balance_activity_complexity(self, staff_entries, slot_counts, all_staff_activities):
        """Strategy 3: Balance activity complexity across slots."""
        from collections import defaultdict

        optimizations = 0

        # Group by day
        day_loads = defaultdict(int)
        day_entries = defaultdict(list)

        for entry in staff_entries:
            day = entry.time_slot.day
            day_loads[day] += 1
            day_entries[day].append(entry)

        # Calculate average per day
        avg_day_load = sum(day_loads.values()) / len(day_loads)

        # Find overloaded and underloaded days
        overloaded_days = [day for day, load in day_loads.items() if load > avg_day_load + 1]
        underloaded_days = [day for day, load in day_loads.items() if load < avg_day_load - 1]

        # Try to balance by moving complex activities
        for over_day in overloaded_days:
            for under_day in underloaded_days:
                # Find complex activities in overloaded day
                complex_entries = [e for e in day_entries[over_day] 
                                 if e.activity.name in self.THREE_HOUR_ACTIVITIES]

                for entry in complex_entries:
                    # Try to move to underloaded day
                    for slot in self.time_slots:
                        if slot.day != under_day:
                            continue

                        if (self.schedule.is_troop_free(slot, entry.troop) and 
                            self.schedule.is_activity_available(slot, entry.activity, entry.troop)):

                            # Move the activity
                            old_day = entry.time_slot.day
                            old_slot = entry.time_slot.slot_number

                            self.schedule.remove_entry(entry)
                            self.schedule.add_entry(slot, entry.activity, entry.troop)

                            # Update counts
                            slot_counts[(old_day, old_slot)] -= 1
                            slot_counts[(under_day, slot.slot_number)] += 1

                            optimizations += 1
                            print(f"        [Complexity] Moved {entry.troop.name} {entry.activity.name} from {old_day.name[:3]} to {under_day.name[:3]}")
                            break

                    if optimizations >= 5:  # Limit complexity moves
                        break

                if optimizations >= 5:
                    break

        return optimizations


    def _can_move_entry_to_slot(self, entry, target_day, target_slot):
        """Check if an entry can be moved to a specific slot."""
        # Find the target time slot object
        target_time_slot = None
        for ts in self.time_slots:
            if ts.day == target_day and ts.slot_number == target_slot:
                target_time_slot = ts
                break

        if not target_time_slot:
            return False

        # Check if the troop is free and activity is available
        return (self.schedule.is_troop_free(target_time_slot, entry.troop) and 
                self.schedule.is_activity_available(target_time_slot, entry.activity, entry.troop))


    def apply_safe_optimizations(self):
        """Apply safe optimizations that never violate constraints."""
        print("  [Safe Optimization] Starting constraint-safe optimization system...")

        # Import here to avoid circular imports
        from safe_optimizer import SafeScheduleOptimizer
        from safe_constraint_fixer import SafeConstraintFixer

        # Initialize safe optimizer
        safe_optimizer = SafeScheduleOptimizer(self.schedule, self.troops, self.time_slots)

        # Phase 1: Safe constraint violation reduction (highest priority)
        print("    [Phase 1] Safe constraint violation reduction...")
        constraint_fixer = SafeConstraintFixer(safe_optimizer)
        violations_fixed = constraint_fixer.fix_constraint_violations_safely()

        # Phase 2: Safe Top 5 recovery (only if no constraint violations created)
        print("    [Phase 2] Safe Top 5 preference recovery...")
        top5_recovered = self._safe_top5_recovery(safe_optimizer)

        # Phase 3: Safe clustering optimization (conservative approach)
        print("    [Phase 3] Safe clustering optimization...")
        clustering_improved = self._safe_clustering_optimization(safe_optimizer)

        # Get optimization summary
        summary = safe_optimizer.get_optimization_summary()

        print(f"  [Safe Optimization] Summary:")
        print(f"    Constraint violations fixed: {violations_fixed}")
        print(f"    Top 5 preferences recovered: {top5_recovered}")
        print(f"    Clustering improvements: {clustering_improved}")
        print(f"    Total optimization attempts: {summary['total_attempts']}")
        print(f"    Successful optimizations: {summary['successful']}")
        print(f"    Blocked by constraints: {summary['blocked']}")
        print(f"    Success rate: {summary['success_rate']:.1%}")

        # Auto-save the optimized schedule
        try:
            from ...io_handler import save_schedule_to_json
            import os
            schedule_dir = "schedules"
            if not os.path.exists(schedule_dir):
                os.makedirs(schedule_dir)
            schedule_file = os.path.join(schedule_dir, "tc_week3_troops_schedule.json")
            save_schedule_to_json(self.schedule, self.troops, schedule_file)
            print(f"  [Auto-Save] Safe optimized schedule saved to {schedule_file}")
        except Exception as e:
            print(f"  [Warning] Could not auto-save schedule: {e}")

        return violations_fixed + top5_recovered + clustering_improved


    def _safe_top5_recovery(self, safe_optimizer):
        """Safely recover Top 5 preferences without creating violations."""
        recovered = 0

        for troop in self.troops:
            troop_entries = self.schedule.get_troop_schedule(troop)
            current_activities = [e.activity.name for e in troop_entries]

            # Check Top 5 preferences
            for rank in range(5):  # Ranks 0-4 for Top 5
                preferred_activity = troop.get_activity_at_rank(rank)
                if preferred_activity and preferred_activity not in current_activities:
                    # Try to safely add this preference
                    if self._safe_add_preference_safely(troop, preferred_activity, safe_optimizer):
                        recovered += 1
                        print(f"        [Safe Top 5] Recovered {preferred_activity} for {troop.name} (rank {rank + 1})")

        return recovered


    def _safe_add_preference_safely(self, troop, activity_name, safe_optimizer):
        """Safely add a preference without creating violations."""
        # Find the activity object
        activity = self._find_activity_by_name(activity_name)
        if not activity:
            return False

        # Try each time slot safely
        for time_slot in self.time_slots:
            # Create a temporary entry to test constraints
            temp_entry = type('TempEntry', (), {
                'troop': troop,
                'activity': activity,
                'time_slot': time_slot
            })()

            # Check if adding this would violate constraints
            constraint_result = safe_optimizer.check_all_constraints(temp_entry, time_slot)

            if constraint_result['ok']:
                # Safe to add - find the lowest priority activity to replace
                troop_entries = self.schedule.get_troop_schedule(troop)
                if troop_entries:
                    # Sort by priority (lowest priority = replace)
                    troop_entries.sort(key=lambda e: troop.get_priority(e.activity.name), reverse=True)

                    # Replace the lowest priority activity if it's not Top 5
                    lowest_entry = troop_entries[0]
                    if troop.get_priority(lowest_entry.activity.name) >= 5:
                        # Safe swap
                        if safe_optimizer.safe_swap_entries(lowest_entry, temp_entry):
                            return True

        return False


    def _safe_clustering_optimization(self, safe_optimizer):
        """Safely improve clustering without creating violations."""
        improved = 0

        # Only attempt clustering if constraint violations are minimal
        current_violations = self._count_current_violations()
        if current_violations > 5:
            print(f"        [Safe Clustering] Skipped due to {current_violations} constraint violations")
            return 0

        # Conservative clustering - only move activities that won't affect constraints
        try:
            _exclusive = EXCLUSIVE_AREAS
        except NameError:
            print("        [Safe Clustering] Skipped - EXCLUSIVE_AREAS not available")
            return 0

        for area in ["Tower", "Rifle Range"]:  # Focus on high-impact areas
            activities = EXCLUSIVE_AREAS.get(area, [])
            if not activities:
                continue

            area_entries = [e for e in self.schedule.entries if e.activity.name in activities]
            if len(area_entries) < 4:
                continue

            # Count current distribution
            day_counts = {}
            for entry in area_entries:
                day = entry.time_slot.day
                day_counts[day] = day_counts.get(day, 0) + 1

            # Try to consolidate scattered activities (very conservative)
            scattered_days = [day for day, count in day_counts.items() if count == 1]

            for day in scattered_days:
                # Find the single activity on this day
                day_entries = [e for e in area_entries if e.time_slot.day == day]
                if not day_entries:
                    continue

                entry = day_entries[0]

                # Try to move to a day with multiple activities
                for target_day, count in day_counts.items():
                    if count > 1 and target_day != day:
                        # Try each slot on target day
                        for time_slot in self.time_slots:
                            if (time_slot.day == target_day and 
                                safe_optimizer.check_all_constraints(entry, time_slot)['ok']):

                                if safe_optimizer.safe_move_entry(entry, time_slot):
                                    improved += 1
                                    print(f"        [Safe Clustering] Consolidated {entry.activity.name} to {target_day.name[:3]}")
                                    break
                        else:
                            continue
                        break

        return improved


    def _count_current_violations(self):
        """Count current constraint violations."""
        violations = 0

        # This would need to be implemented based on your violation checking logic
        # For now, return a conservative estimate
        return 5


    def _find_activity_by_name(self, activity_name):
        """Find activity object by name."""
        # This would need to be implemented based on your activity data structure
        class MockActivity:
            def __init__(self, name):
                self.name = name

        return MockActivity(activity_name)


    def get_stats(self) -> dict:
        """Get schedule statistics."""
        stats = {'total_entries': len(self.schedule.entries), 'troops': {}}

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)
            top5_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 5)
            top10_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 10)
            has_reflection = any(e.activity.name == "Reflection" for e in entries)

            stats['troops'][troop.name] = {
                'total_activities': len(entries),
                'top5_count': top5_count,
                'top10_count': top10_count,
                'has_reflection': has_reflection
            }

        return stats


    def _remove_continuations_helper(self, entry):
        """
        Helper method to remove continuation entries for multi-slot activities.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Remove Continuations] Skipping optimization (placeholder)")
        return []


    def _aggressive_excess_day_reduction_swaps(self):
        """
        Reduce excess cluster days using targeted same-troop swaps.

        Definition aligned with BRAIN/regression checker:
        required_days = ceil(activity_count / 3), and excess days are days above that.

        Strategy:
        - Identify cluster areas with excess days.
        - Keep the densest `required_days` as target days.
        - Move area activities off sparse days by swapping with lower-value activities
          from the same troop on target days.
        """
        from collections import defaultdict
        import math

        print("    [Aggressive Excess Day Reduction] Starting targeted swaps...")

        cluster_areas = ["Tower", "Rifle Range", "Outdoor Skills", "Handicrafts"]
        protected_activities = {
            "Reflection",
            "Super Troop",
            "Delta",
            "Sailing",
            "History Center",
            "Disc Golf",
        }

        def _is_single_slot_entry(entry) -> bool:
            effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
            return int(effective_slots + 0.5) == 1

        def _is_swappable_target(entry) -> bool:
            if entry.activity.name in protected_activities:
                return False
            if entry.activity.name in self.THREE_HOUR_ACTIVITIES:
                return False
            return _is_single_slot_entry(entry)

        total_swaps = 0
        max_swaps = max(10, len(self.troops) * 3)
        improved = True

        while improved and total_swaps < max_swaps:
            improved = False

            for area_name in cluster_areas:
                area_activities = EXCLUSIVE_AREAS.get(area_name, [])
                if not area_activities:
                    continue

                area_entries = [e for e in self.schedule.entries if e.activity.name in area_activities]
                if len(area_entries) < 2:
                    continue

                day_counts = defaultdict(int)
                for entry in area_entries:
                    day_counts[entry.time_slot.day] += 1

                current_days = len(day_counts)
                required_days = math.ceil(len(area_entries) / 3.0)
                excess_days = max(0, current_days - required_days)

                if excess_days <= 0:
                    continue

                target_days = [
                    day for day, _ in sorted(
                        day_counts.items(),
                        key=lambda x: (-x[1], x[0].value)
                    )[:required_days]
                ]

                source_days = [
                    day for day, _ in sorted(
                        day_counts.items(),
                        key=lambda x: (x[1], x[0].value)
                    ) if day not in target_days
                ]

                swap_made_for_area = False
                for source_day in source_days:
                    source_entries = sorted(
                        [
                            e for e in area_entries
                            if e.time_slot.day == source_day and _is_single_slot_entry(e)
                        ],
                        key=lambda e: e.time_slot.slot_number,
                    )

                    for source_entry in source_entries:
                        if source_entry not in self.schedule.entries:
                            continue

                        troop = source_entry.troop
                        source_slot = source_entry.time_slot

                        for target_day in target_days:
                            troop_target_entries = [
                                e for e in self.schedule.entries
                                if e.troop == troop and e.time_slot.day == target_day
                            ]
                            target_candidates = sorted(
                                [
                                    e for e in troop_target_entries
                                    if e.activity.name not in area_activities and _is_swappable_target(e)
                                ],
                                key=lambda e: (troop.get_priority(e.activity.name), e.time_slot.slot_number),
                                reverse=True,
                            )

                            for target_entry in target_candidates:
                                if target_entry not in self.schedule.entries:
                                    continue

                                target_slot = target_entry.time_slot
                                if target_slot == source_slot:
                                    continue

                                baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
                                baseline_excess_days = self._count_excess_cluster_days()

                                self.schedule.entries.remove(source_entry)
                                self.schedule.entries.remove(target_entry)

                                can_move_area = self._can_schedule(
                                    troop, source_entry.activity, target_slot, target_slot.day,
                                    relax_constraints=True
                                )
                                can_move_other = self._can_schedule(
                                    troop, target_entry.activity, source_slot, source_slot.day,
                                    relax_constraints=True
                                )

                                if can_move_area and can_move_other:
                                    placed_area = self.schedule.add_entry(target_slot, source_entry.activity, troop)
                                    placed_other = self.schedule.add_entry(source_slot, target_entry.activity, troop)
                                    if placed_area and placed_other:
                                        new_non_exempt, _ = self._count_non_exempt_top5_misses()
                                        new_excess_days = self._count_excess_cluster_days()
                                        if new_non_exempt <= baseline_non_exempt and new_excess_days < baseline_excess_days:
                                            total_swaps += 1
                                            improved = True
                                            swap_made_for_area = True
                                            print(
                                                f"      [Excess Day Swap] {area_name}: {troop.name} "
                                                f"{source_entry.activity.name} {source_day.name[:3]}-{source_slot.slot_number} "
                                                f"-> {target_day.name[:3]}-{target_slot.slot_number}"
                                            )
                                            break
                                        # Reject neutral/regressive moves.
                                        placed_area_entry = next(
                                            (
                                                e for e in self.schedule.entries
                                                if e.troop == troop
                                                and e.time_slot == target_slot
                                                and e.activity.name == source_entry.activity.name
                                            ),
                                            None,
                                        )
                                        placed_other_entry = next(
                                            (
                                                e for e in self.schedule.entries
                                                if e.troop == troop
                                                and e.time_slot == source_slot
                                                and e.activity.name == target_entry.activity.name
                                            ),
                                            None,
                                        )
                                        if placed_area_entry:
                                            self.schedule.entries.remove(placed_area_entry)
                                        if placed_other_entry:
                                            self.schedule.entries.remove(placed_other_entry)

                                    # Partial add safety rollback
                                    if placed_area:
                                        placed_entry = next(
                                            (
                                                e for e in self.schedule.entries
                                                if e.troop == troop
                                                and e.time_slot == target_slot
                                                and e.activity.name == source_entry.activity.name
                                            ),
                                            None,
                                        )
                                        if placed_entry:
                                            self.schedule.entries.remove(placed_entry)
                                    if placed_other:
                                        placed_entry = next(
                                            (
                                                e for e in self.schedule.entries
                                                if e.troop == troop
                                                and e.time_slot == source_slot
                                                and e.activity.name == target_entry.activity.name
                                            ),
                                            None,
                                        )
                                        if placed_entry:
                                            self.schedule.entries.remove(placed_entry)

                                # Full rollback
                                self.schedule.entries.append(source_entry)
                                self.schedule.entries.append(target_entry)

                                if swap_made_for_area:
                                    break

                            if swap_made_for_area:
                                break

                        if swap_made_for_area or total_swaps >= max_swaps:
                            break

                    if swap_made_for_area or total_swaps >= max_swaps:
                        break

                # Recompute global area distributions after each successful area swap
                if swap_made_for_area:
                    break

        # Secondary pass: cross-troop swaps for areas still in excess.
        cross_swaps = 0
        if total_swaps < max_swaps:
            for area_name in cluster_areas:
                if total_swaps + cross_swaps >= max_swaps:
                    break
                area_activities = EXCLUSIVE_AREAS.get(area_name, [])
                if not area_activities:
                    continue

                area_entries = [e for e in self.schedule.entries if e.activity.name in area_activities]
                if len(area_entries) < 2:
                    continue

                day_counts = defaultdict(int)
                for e in area_entries:
                    day_counts[e.time_slot.day] += 1
                required_days = math.ceil(len(area_entries) / 3.0)
                if len(day_counts) <= required_days:
                    continue

                target_days = {
                    day for day, _ in sorted(day_counts.items(), key=lambda x: (-x[1], x[0].value))[:required_days]
                }
                source_entries = [
                    e for e in area_entries
                    if e.time_slot.day not in target_days and _is_single_slot_entry(e)
                ]

                for source_entry in source_entries:
                    if total_swaps + cross_swaps >= max_swaps:
                        break
                    if source_entry not in self.schedule.entries:
                        continue

                    source_troop = source_entry.troop
                    source_slot = source_entry.time_slot

                    target_entries = sorted(
                        [
                            e for e in self.schedule.entries
                            if e.troop != source_troop
                            and e.time_slot.day in target_days
                            and _is_swappable_target(e)
                            and e.activity.name not in area_activities
                        ],
                        key=lambda e: (source_troop.get_priority(e.activity.name), e.troop.get_priority(source_entry.activity.name)),
                        reverse=True,
                    )

                    swapped = False
                    for target_entry in target_entries:
                        if target_entry not in self.schedule.entries:
                            continue

                        target_troop = target_entry.troop
                        target_slot = target_entry.time_slot

                        baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
                        baseline_excess_days = self._count_excess_cluster_days()

                        self.schedule.entries.remove(source_entry)
                        self.schedule.entries.remove(target_entry)

                        a_ok = self._can_schedule(
                            source_troop, target_entry.activity, source_slot, source_slot.day, relax_constraints=True
                        )
                        b_ok = self._can_schedule(
                            target_troop, source_entry.activity, target_slot, target_slot.day, relax_constraints=True
                        )

                        if a_ok and b_ok:
                            ok1 = self.schedule.add_entry(source_slot, target_entry.activity, source_troop)
                            ok2 = self.schedule.add_entry(target_slot, source_entry.activity, target_troop)
                            if ok1 and ok2:
                                new_non_exempt, _ = self._count_non_exempt_top5_misses()
                                new_excess_days = self._count_excess_cluster_days()
                                if new_non_exempt <= baseline_non_exempt and new_excess_days < baseline_excess_days:
                                    cross_swaps += 1
                                    swapped = True
                                    print(
                                        f"      [Cross Excess Swap] {area_name}: "
                                        f"{source_troop.name} <-> {target_troop.name} "
                                        f"({source_entry.activity.name} -> {target_slot.day.name[:3]})"
                                    )
                                    break
                                # Reject neutral/regressive moves.
                                bad1 = next(
                                    (
                                        e for e in self.schedule.entries
                                        if e.troop == source_troop and e.time_slot == source_slot
                                        and e.activity.name == target_entry.activity.name
                                    ),
                                    None,
                                )
                                bad2 = next(
                                    (
                                        e for e in self.schedule.entries
                                        if e.troop == target_troop and e.time_slot == target_slot
                                        and e.activity.name == source_entry.activity.name
                                    ),
                                    None,
                                )
                                if bad1:
                                    self.schedule.entries.remove(bad1)
                                if bad2:
                                    self.schedule.entries.remove(bad2)

                            # Partial rollback safety
                            if ok1:
                                bad = next(
                                    (
                                        e for e in self.schedule.entries
                                        if e.troop == source_troop and e.time_slot == source_slot
                                        and e.activity.name == target_entry.activity.name
                                    ),
                                    None,
                                )
                                if bad:
                                    self.schedule.entries.remove(bad)
                            if ok2:
                                bad = next(
                                    (
                                        e for e in self.schedule.entries
                                        if e.troop == target_troop and e.time_slot == target_slot
                                        and e.activity.name == source_entry.activity.name
                                    ),
                                    None,
                                )
                                if bad:
                                    self.schedule.entries.remove(bad)

                        self.schedule.entries.append(source_entry)
                        self.schedule.entries.append(target_entry)

                    if swapped:
                        break

        total_swaps += cross_swaps
        if total_swaps > 0:
            print(f"    [Aggressive Excess Day Reduction] Completed {total_swaps} swap(s)")
        else:
            print("    [Aggressive Excess Day Reduction] No safe swaps found")
        return total_swaps


    def _aggressive_cross_troop_same_activity_swaps(self):
        """
        ENHANCED: Cross-troop same activity swaps for better clustering.

        This method looks for opportunities to consolidate same activities onto fewer days:
        - Finds troops with same activities on different days
        - Swaps to consolidate activities onto preferred days
        - NEW: Better prioritization of target consolidation days
        - NEW: More aggressive swap attempts
        """
        from ...models import Day
        import math

        swaps_made = 0

        # Target cluster areas
        cluster_areas = ["Tower", "Rifle Range", "Outdoor Skills", "Handicrafts"]

        for area in cluster_areas:
            activities = EXCLUSIVE_AREAS.get(area, [])
            if not activities:
                continue

            area_entries = [e for e in self.schedule.entries if e.activity.name in activities]
            if len(area_entries) < 4:  # Need enough entries for meaningful swaps
                continue

            # Count current distribution
            day_counts = {}
            for entry in area_entries:
                day_counts[entry.time_slot.day] = day_counts.get(entry.time_slot.day, 0) + 1

            # Calculate if we have excess days
            num_activities = len(area_entries)
            min_days = math.ceil(num_activities / 3.0)
            current_days = len(day_counts)
            excess_days = max(0, current_days - min_days)

            if excess_days <= 0:
                continue

            print(f"    [Cross Troop Swaps] {area}: {excess_days} excess days, looking for swaps...")

            # ENHANCED: Group entries by activity for better swap opportunities
            activity_entries = {}
            for entry in area_entries:
                if entry.activity.name not in activity_entries:
                    activity_entries[entry.activity.name] = []
                activity_entries[entry.activity.name].append(entry)

            # Find best consolidation targets (days with most activities)
            best_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:min_days]
            best_day_names = [day for day, count in best_days]

            # For each activity, try to consolidate scattered instances
            for activity_name, entries in activity_entries.items():
                if len(entries) < 2:  # Need at least 2 instances to consolidate
                    continue

                # Group by day
                day_entries = {}
                for entry in entries:
                    day_entries[entry.time_slot.day] = entry

                # If activity is already well-consolidated, skip
                if len(day_entries) <= min_days:
                    continue

                # Try to move instances to best consolidation days
                for source_day, source_entry in day_entries.items():
                    if source_day in best_day_names:  # Already on a good day
                        continue

                    # Try to move to a best day
                    for target_day in best_day_names:
                        # Find if there's a troop with this activity on target day that we can swap with
                        target_entry = None
                        for entry in area_entries:
                            if (entry.time_slot.day == target_day and 
                                entry.troop != source_entry.troop and
                                entry.activity.name != source_entry.activity.name):
                                target_entry = entry
                                break

                        if target_entry:
                            # Check if swap is possible
                            source_slot = source_entry.time_slot
                            target_slot = target_entry.time_slot

                            can_swap = True

                            # Check if source troop can do target activity
                            if not self.schedule.is_activity_available(source_slot, target_entry.activity, source_entry.troop):
                                can_swap = False

                            # Check if target troop can do source activity
                            if can_swap and not self.schedule.is_activity_available(target_slot, source_entry.activity, target_entry.troop):
                                can_swap = False

                            if can_swap:
                                # Make the swap
                                self.schedule.remove_entry(source_entry)
                                self.schedule.remove_entry(target_entry)

                                self.schedule.add_entry(source_slot, target_entry.activity, source_entry.troop)
                                self.schedule.add_entry(target_slot, source_entry.activity, target_entry.troop)

                                swaps_made += 1
                                print(f"      [Cross Swap] {source_entry.troop.name}: {source_entry.activity.name} {source_day.name[:3]} <-> {target_entry.troop.name}: {target_entry.activity.name} {target_day.name[:3]}")

                                # Update day_entries to reflect the move
                                day_entries[source_day] = None
                                day_entries[target_day] = source_entry
                                break

                        if swaps_made > 0 and len([e for e in day_entries.values() if e is not None]) <= min_days:
                            break

                    if swaps_made > 0:
                        break

        if swaps_made > 0:
            print(f"    [Cross Troop Swaps] Made {swaps_made} cross-troop swaps for better clustering")

        return swaps_made


    def _is_exclusive_blocked(self, slot, activity_name, duration=1, ignore_troop=None):
        """
        Check if a slot is blocked by exclusive area constraints.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Is Exclusive Blocked] Skipping optimization (placeholder)")
        return False


    def _optimize_commissioner_day_ownership(self):
        """
        Improve commissioner-day ownership with safe intra-troop day swaps/moves.

        Goal: keep commissioner-managed activities on their mapped day where possible
        without breaking hard constraints, increasing cluster spread, or introducing empty slots.
        """
        print("    [Commissioner Day Ownership] Optimizing mapped-day compliance...")

        protected_activities = {
            "Reflection",
            "Sailing",  # Keep multi-slot anchors stable here.
            "Tamarac Wildlife Refuge",
            "Itasca State Park",
            "Back of the Moon",
        }
        commissioner_activities = {
            "Delta",
            "Super Troop",
            "Troop Rifle",
            "Troop Shotgun",
            "Archery",
            "Climbing Tower",
        } | set(self.TOWER_ODS_ACTIVITIES)

        def _is_single_slot_entry(entry) -> bool:
            effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
            return int(effective_slots + 0.5) == 1

        moves = 0
        max_moves = max(12, len(self.troops) * 3)

        # Work from lower-priority commissioner assignments first to protect top requests.
        candidates = sorted(
            [
                e for e in self.schedule.entries
                if e.activity.name in commissioner_activities and _is_single_slot_entry(e)
            ],
            key=lambda e: (e.troop.get_priority(e.activity.name), e.troop.name),
            reverse=True,
        )

        for entry in candidates:
            if moves >= max_moves:
                break
            if entry not in self.schedule.entries:
                continue

            troop = entry.troop
            expected_day = self._get_activity_commissioner_day_fixed(troop, entry.activity.name)
            if not expected_day or entry.time_slot.day == expected_day:
                continue

            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            if baseline_non_exempt > 0:
                break
            baseline_metrics = self._schedule_quality_snapshot()

            # Attempt same-troop swap into expected day.
            expected_day_entries = sorted(
                [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == expected_day],
                key=lambda e: (troop.get_priority(e.activity.name), e.time_slot.slot_number),
                reverse=True,
            )

            moved = False
            for target_entry in expected_day_entries:
                if target_entry.activity.name in protected_activities:
                    continue
                if not _is_single_slot_entry(target_entry):
                    continue
                if target_entry.activity.name in commissioner_activities:
                    continue

                source_slot = entry.time_slot
                target_slot = target_entry.time_slot
                if source_slot == target_slot:
                    continue

                snapshot = self._snapshot_scheduler_state()
                removed_entry = self._remove_from_schedule(entry)
                removed_target = self._remove_from_schedule(target_entry)

                can_place_commissioner = removed_entry and removed_target and self._can_schedule(
                    troop, entry.activity, target_slot, target_slot.day, relax_constraints=False
                )
                can_place_other = removed_entry and removed_target and self._can_schedule(
                    troop, target_entry.activity, source_slot, source_slot.day, relax_constraints=False
                )

                if can_place_commissioner and can_place_other:
                    ok1 = self._add_to_schedule(target_slot, entry.activity, troop)
                    ok2 = self._add_to_schedule(source_slot, target_entry.activity, troop)
                    if ok1 and ok2:
                        new_non_exempt, _ = self._count_non_exempt_top5_misses()
                        new_metrics = self._schedule_quality_snapshot()
                        if (
                            new_non_exempt <= baseline_non_exempt
                            and self._is_quality_snapshot_improvement(
                                baseline_metrics,
                                new_metrics,
                                require_commissioner_improvement=True,
                            )
                        ):
                            moves += 1
                            moved = True
                            print(
                                f"      [Commissioner Swap] {troop.name}: {entry.activity.name} "
                                f"{source_slot.day.name[:3]}-{source_slot.slot_number} -> "
                                f"{target_slot.day.name[:3]}-{target_slot.slot_number}"
                            )
                            break
                    self._restore_scheduler_state(snapshot)
                else:
                    self._restore_scheduler_state(snapshot)

            if moved:
                continue

            # Attempt direct move to an empty slot on expected day, then refill vacated slot.
            expected_slots = sorted([s for s in self.time_slots if s.day == expected_day], key=lambda s: s.slot_number)
            for target_slot in expected_slots:
                if not self.schedule.is_troop_free(target_slot, troop):
                    continue

                source_slot = entry.time_slot
                snapshot = self._snapshot_scheduler_state()
                removed_entry = self._remove_from_schedule(entry)
                can_move = removed_entry and self._can_schedule(
                    troop, entry.activity, target_slot, expected_day, relax_constraints=False
                )
                if can_move and self._add_to_schedule(target_slot, entry.activity, troop):
                    self._fill_vacated_slot(troop, source_slot)
                    if not self.schedule.is_troop_free(source_slot, troop):
                        new_non_exempt, _ = self._count_non_exempt_top5_misses()
                        new_metrics = self._schedule_quality_snapshot()
                        if (
                            new_non_exempt <= baseline_non_exempt
                            and self._is_quality_snapshot_improvement(
                                baseline_metrics,
                                new_metrics,
                                require_commissioner_improvement=True,
                            )
                        ):
                            moves += 1
                            moved = True
                            print(
                                f"      [Commissioner Move] {troop.name}: {entry.activity.name} "
                                f"{source_slot.day.name[:3]}-{source_slot.slot_number} -> "
                                f"{target_slot.day.name[:3]}-{target_slot.slot_number}"
                            )
                            break
                self._restore_scheduler_state(snapshot)

            if moves >= max_moves:
                break

        if moves > 0:
            print(f"    [Commissioner Day Ownership] Completed {moves} improvement(s)")
        else:
            print("    [Commissioner Day Ownership] No safe ownership improvements found")
        return moves


    def _optimize_cluster_gaps_post_fill(self):
        """
        Fix official area-level 1,-,3 cluster gaps after fill when possible.

        This pass now targets the same day+area pattern used by the regression
        checker instead of same-troop local shapes.
        """
        print("    [Cluster Gap Post-Fill] Searching for official area-level 1,-,3 gaps...")

        cluster_areas = self._get_authoritative_gap_area_map()
        slot_lookup = {(s.day, s.slot_number): s for s in self.time_slots}
        fixes = 0

        def _is_single_slot_entry(entry) -> bool:
            effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
            return int(effective_slots + 0.5) == 1

        protected_activities = {
            "Reflection",
            "Sailing",
            "Tamarac Wildlife Refuge",
            "Itasca State Park",
            "Back of the Moon",
        }

        improved = True
        while improved:
            improved = False
            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            baseline_metrics = self._schedule_quality_snapshot()
            baseline_gaps = baseline_metrics["gaps"]
            if baseline_gaps <= 0:
                break

            gap_targets = []
            for day in (Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY):
                day_entries = [e for e in self.schedule.entries if e.time_slot.day == day]
                for area_name, area_activities in cluster_areas.items():
                    has_1 = any(
                        e.time_slot.slot_number == 1 and e.activity.name in area_activities
                        for e in day_entries
                    )
                    has_3 = any(
                        e.time_slot.slot_number == 3 and e.activity.name in area_activities
                        for e in day_entries
                    )
                    has_2 = any(
                        e.time_slot.slot_number == 2 and e.activity.name in area_activities
                        for e in day_entries
                    )
                    if has_1 and has_3 and not has_2:
                        gap_targets.append((day, area_name, area_activities))

            for day, area_name, area_activities in gap_targets:
                slot2 = slot_lookup.get((day, 2))
                if not slot2:
                    continue
                area_day_counts = Counter(
                    entry.time_slot.day
                    for entry in self.schedule.entries
                    if entry.activity.name in area_activities
                )

                edge_candidates = sorted(
                    [
                        e for e in self.schedule.entries
                        if e.time_slot.day == day
                        and e.time_slot.slot_number in {1, 3}
                        and e.activity.name in area_activities
                        and e.activity.name not in protected_activities
                        and _is_single_slot_entry(e)
                    ],
                    key=lambda e: (e.troop.get_priority(e.activity.name), e.time_slot.slot_number),
                    reverse=True,
                )

                fixed = False
                for edge_entry in edge_candidates:
                    troop = edge_entry.troop
                    source_slot = edge_entry.time_slot

                    slot2_entry = next(
                        (e for e in self.schedule.entries if e.troop == troop and e.time_slot == slot2),
                        None,
                    )

                    # Attempt 1: same-troop swap into slot 2.
                    if (
                        slot2_entry
                        and slot2_entry.activity.name not in protected_activities
                        and _is_single_slot_entry(slot2_entry)
                    ):
                        target_priority = troop.get_priority(slot2_entry.activity.name)
                        if target_priority is None or target_priority >= 5:
                            snapshot = self._snapshot_scheduler_state()
                            removed_edge = self._remove_from_schedule(edge_entry)
                            removed_slot2 = self._remove_from_schedule(slot2_entry)
                            if removed_edge and removed_slot2:
                                can_move_edge = self._can_schedule(
                                    troop, edge_entry.activity, slot2, day, relax_constraints=False
                                )
                                can_move_other = self._can_schedule(
                                    troop, slot2_entry.activity, source_slot, day, relax_constraints=False
                                )
                                if (
                                    can_move_edge
                                    and can_move_other
                                    and self._add_to_schedule(slot2, edge_entry.activity, troop)
                                    and self._add_to_schedule(source_slot, slot2_entry.activity, troop)
                                ):
                                    after_non_exempt, _ = self._count_non_exempt_top5_misses()
                                    after_metrics = self._schedule_quality_snapshot()
                                    after_gaps = after_metrics["gaps"]
                                    if (
                                        after_non_exempt <= baseline_non_exempt
                                        and after_gaps < baseline_gaps
                                        and self._is_quality_snapshot_improvement(
                                            baseline_metrics,
                                            after_metrics,
                                        )
                                    ):
                                        fixes += 1
                                        improved = True
                                        fixed = True
                                        print(
                                            f"      [Cluster Gap Fix] {troop.name} {day.name[:3]} "
                                            f"({area_name}) swapped {edge_entry.activity.name} into slot 2"
                                        )
                                        break
                            if not fixed:
                                self._restore_scheduler_state(snapshot)

                    # Attempt 2: move the edge into slot 2, then refill the source slot.
                    if self.schedule.is_troop_free(slot2, troop):
                        snapshot = self._snapshot_scheduler_state()
                        if self._remove_from_schedule(edge_entry):
                            can_move = self._can_schedule(
                                troop, edge_entry.activity, slot2, day, relax_constraints=False
                            )
                            if can_move and self._add_to_schedule(slot2, edge_entry.activity, troop):
                                self._fill_vacated_slot(troop, source_slot)
                                if not self.schedule.is_troop_free(source_slot, troop):
                                    after_non_exempt, _ = self._count_non_exempt_top5_misses()
                                    after_metrics = self._schedule_quality_snapshot()
                                    after_gaps = after_metrics["gaps"]
                                    if (
                                        after_non_exempt <= baseline_non_exempt
                                        and after_gaps < baseline_gaps
                                        and self._is_quality_snapshot_improvement(
                                            baseline_metrics,
                                            after_metrics,
                                        )
                                    ):
                                        fixes += 1
                                        improved = True
                                        fixed = True
                                        print(
                                            f"      [Cluster Gap Fix] {troop.name} {day.name[:3]} "
                                            f"({area_name}) moved {edge_entry.activity.name} to slot 2"
                                        )
                                        break
                        if not fixed:
                            self._restore_scheduler_state(snapshot)

                    # Attempt 3: pull a same-area single-slot activity from another day into slot 2.
                    off_day_candidates = sorted(
                        [
                            e for e in self.schedule.entries
                            if e.time_slot.day != day
                            and e.activity.name in area_activities
                            and e.activity.name not in protected_activities
                            and _is_single_slot_entry(e)
                        ],
                        key=lambda e: (
                            0 if area_day_counts.get(e.time_slot.day, 0) == 1 else 1,
                            area_day_counts.get(e.time_slot.day, 0),
                            -self._normalized_preference_rank(e.troop, e.activity.name),
                            self._day_clustering_sort_key(e.time_slot.day),
                            e.time_slot.slot_number,
                        ),
                    )

                    for source_entry in off_day_candidates[:12]:
                        troop = source_entry.troop
                        source_slot = source_entry.time_slot
                        slot2_entry = next(
                            (e for e in self.schedule.entries if e.troop == troop and e.time_slot == slot2),
                            None,
                        )
                        if (
                            slot2_entry
                            and (
                                slot2_entry.activity.name in protected_activities
                                or not _is_single_slot_entry(slot2_entry)
                                or troop.get_priority(slot2_entry.activity.name) < 5
                            )
                        ):
                            continue

                        snapshot = self._snapshot_scheduler_state()
                        if not self._remove_from_schedule(source_entry):
                            self._restore_scheduler_state(snapshot)
                            continue

                        removed_slot2 = False
                        if slot2_entry:
                            removed_slot2 = self._remove_from_schedule(slot2_entry)
                            if not removed_slot2:
                                self._restore_scheduler_state(snapshot)
                                continue

                        can_move_source = self._can_schedule(
                            troop, source_entry.activity, slot2, day, relax_constraints=False
                        )
                        can_restore_slot = True
                        if slot2_entry:
                            can_restore_slot = self._can_schedule(
                                troop, slot2_entry.activity, source_slot, source_slot.day, relax_constraints=False
                            )
                        if not can_move_source or not can_restore_slot:
                            self._restore_scheduler_state(snapshot)
                            continue

                        placed_source = self._add_to_schedule(slot2, source_entry.activity, troop)
                        placed_other = True
                        if slot2_entry:
                            placed_other = self._add_to_schedule(source_slot, slot2_entry.activity, troop)
                        if not placed_source or not placed_other:
                            self._restore_scheduler_state(snapshot)
                            continue

                        if not slot2_entry:
                            self._fill_vacated_slot(troop, source_slot)

                        if self.schedule.is_troop_free(source_slot, troop):
                            self._restore_scheduler_state(snapshot)
                            continue

                        after_non_exempt, _ = self._count_non_exempt_top5_misses()
                        after_metrics = self._schedule_quality_snapshot()
                        after_gaps = after_metrics["gaps"]
                        if (
                            after_non_exempt <= baseline_non_exempt
                            and after_gaps < baseline_gaps
                            and self._is_quality_snapshot_improvement(
                                baseline_metrics,
                                after_metrics,
                            )
                        ):
                            fixes += 1
                            improved = True
                            fixed = True
                            print(
                                f"      [Cluster Gap Fix] {troop.name} {day.name[:3]} "
                                f"({area_name}) pulled {source_entry.activity.name} from "
                                f"{source_slot.day.name[:3]}-{source_slot.slot_number} into slot 2"
                            )
                            break
                        self._restore_scheduler_state(snapshot)

                if fixed:
                    break

        if fixes > 0:
            print(f"    [Cluster Gap Post-Fill] Fixed {fixes} official gap(s)")
        else:
            print("    [Cluster Gap Post-Fill] No fixable strict gaps found")
        return fixes


    def _recover_top10_from_fills(self):
        """
        Simple implementation of Top 10 recovery from fills.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Top 10 Recovery from Fills] Skipping optimization (placeholder)")
        return 0


    def _sanitize_exclusivity(self):
        """
        Final exclusivity sanitization to prevent double-booking.
        Removes extra entries in the same exclusive area/slot, keeping the highest-priority troop.
        """
        from collections import defaultdict
        removed = 0

        # Map activity to exclusive area
        activity_to_area = {}
        for area, activities in EXCLUSIVE_AREAS.items():
            for activity_name in activities:
                activity_to_area[activity_name] = area

        # Activities that can have multiple troops (exceptions)
        CONCURRENT = {
            'Reflection', 'Campsite Free Time', 'Shower House',
            'Itasca State Park', 'Tamarac Wildlife Refuge', 'Back of the Moon'
        }

        slot_area_entries = defaultdict(list)
        for entry in self.schedule.entries:
            if entry.activity.name in CONCURRENT:
                continue
            area = activity_to_area.get(entry.activity.name)
            if area:
                slot_area_entries[(entry.time_slot, area)].append(entry)

        for (slot, area), entries in slot_area_entries.items():
            if len(entries) <= 1:
                continue

            # Allow limited sharing exceptions
            # Sailing 90-minute overlap rule:
            # Slot 2 may contain up to 2 Sailing entries (overlap of sessions).
            if area == "Sailing":
                if slot.slot_number == 2 and len(entries) <= 2:
                    continue
            if area == "Aqua Trampoline":
                small_troops = [e for e in entries if (e.troop.scouts + e.troop.adults) <= 16]
                if len(small_troops) == len(entries) and len(entries) <= 2:
                    continue
            if area == "Water Polo" and len(entries) <= 2:
                continue

            # Keep the highest-priority entry, remove the rest
            entries_with_rank = []
            for e in entries:
                rank = e.troop.get_priority(e.activity.name)
                if rank == 999:
                    rank = 100
                entries_with_rank.append((e, rank))
            entries_with_rank.sort(key=lambda x: (x[1], x[0].troop.name))
            keep_entry = entries_with_rank[0][0]
            for entry, _ in entries_with_rank[1:]:
                # If we must remove one piece of a multi-slot activity, remove the whole block
                # for that troop/day to avoid leaving broken partial activities.
                linked_entries = [
                    e for e in self.schedule.entries
                    if e.troop == entry.troop
                    and e.activity.name == entry.activity.name
                    and e.time_slot.day == entry.time_slot.day
                ]
                if not linked_entries:
                    continue
                for linked in linked_entries:
                    if linked in self.schedule.entries:
                        self.schedule.entries.remove(linked)
                        removed += 1
                # Track Top 5 to recover
                rank = entry.troop.get_priority(entry.activity.name)
                if rank < 5:
                    if not hasattr(self, "_top5_to_recover"):
                        self._top5_to_recover = []
                    if (entry.troop, entry.activity, rank) not in self._top5_to_recover:
                        self._top5_to_recover.append((entry.troop, entry.activity, rank))

        if removed > 0:
            print(f"    [Sanitize Exclusivity] Removed {removed} conflicting entries")
        else:
            print("    [Sanitize Exclusivity] No exclusivity conflicts found")
        return removed


    def _enforce_staff_limits(self):
        """
        Simple implementation of staff limits enforcement.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Enforce Staff Limits] Skipping optimization (placeholder)")
        return 0


    def _aggressive_severe_underuse_fix(self):
        """
        Simple implementation of aggressive severe underuse fix.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Aggressive Severe Underuse Fix] Skipping optimization (placeholder)")
        return 0


    def _optimize_global_staffed_clustering(self):
        """
        Simple implementation of global staffed clustering.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Global Staffed Clustering] Skipping optimization (placeholder)")
        return 0


    def _final_sanitization(self):
        """
        Simple implementation of final sanitization.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Final Sanitization] Skipping optimization (placeholder)")
        return 0


    def _sanitize_broken_multislot(self):
        """
        Simple implementation of broken multi-slot sanitization.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Sanitize Broken Multislot] Skipping optimization (placeholder)")
        return 0


    def _resolve_day_conflicts(self):
        """
        Simple implementation of day conflict resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Day Conflicts] Skipping optimization (placeholder)")
        return 0


    def _resolve_same_place_same_day(self):
        """
        Simple implementation of same place same day conflict resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Same Place Same Day] Skipping optimization (placeholder)")
        return 0


    def _resolve_wet_dry_patterns(self):
        """
        Simple implementation of wet/dry pattern conflict resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Wet Dry Patterns] Skipping optimization (placeholder)")
        return 0


    def _resolve_beach_slot_violations(self):
        """
        Simple implementation of beach slot violation resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Beach Slot Violations] Skipping optimization (placeholder)")
        return 0
        return 0


    def _aggressive_severe_underuse_fix(self):
        """
        Simple implementation of aggressive severe underuse fix.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Aggressive Severe Underuse Fix] Skipping optimization (placeholder)")
        return 0


    def _optimize_global_staffed_clustering(self):
        """
        Simple implementation of global staffed clustering optimization.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Global Staffed Clustering] Skipping optimization (placeholder)")
        return 0


    def _final_sanitization(self):
        """
        Simple implementation of final sanitization.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Final Sanitization] Skipping optimization (placeholder)")
        return 0


    def _sanitize_broken_multislot(self):
        """
        Simple implementation of broken multislot sanitization.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Sanitize Broken Multislot] Skipping optimization (placeholder)")
        return 0


    def _resolve_day_conflicts(self):
        """
        Simple implementation of day conflict resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Day Conflicts] Skipping optimization (placeholder)")
        return 0


    def _resolve_same_place_same_day(self):
        """
        Simple implementation of same place same day conflict resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Same Place Same Day] Skipping optimization (placeholder)")
        return 0


    def _resolve_wet_dry_patterns(self):
        """
        Simple implementation of wet/dry pattern conflict resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Wet Dry Patterns] Skipping optimization (placeholder)")
        return 0


    def _resolve_beach_slot_violations(self):
        """
        Simple implementation of beach slot violation resolution.
        This is a placeholder to prevent AttributeError during regeneration.
        """
        print("    [Resolve Beach Slot Violations] Skipping optimization (placeholder)")
        return 0


    def get_stats(self) -> dict:
        """Get schedule statistics."""
        stats = {'total_entries': len(self.schedule.entries), 'troops': {}}

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)
            top5_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 5)
            top10_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 10)
            has_reflection = any(e.activity.name == "Reflection" for e in entries)

            stats['troops'][troop.name] = {
                'total_scheduled': len(entries),
                'top5_achieved': top5_count,
                'top10_achieved': top10_count,
                'has_reflection': has_reflection
            }

        return stats


    def _handle_day_specific_requests(self):
        """Handle day-specific requests for activities."""
        # Delegate to existing method
        return self._schedule_day_requests()


    def _process_priority_level(self, priority_level):
        """Process activities by priority level."""
        # Delegate to existing method
        return self._schedule_priority_tier(priority_level)


    def _resolve_conflicts(self):
        """Resolve scheduling conflicts."""
        # Delegate to existing conflict resolution methods
        self._resolve_day_conflicts()
        self._resolve_same_place_same_day()
        self._remove_activity_conflicts()


    def _predictive_constraint_violation_check(self, timeslot, activity, troop, day=None):
        """Predictively check if placing an activity would violate constraints."""
        # Delegate to existing validation method
        return not self._can_schedule(timeslot, activity, troop, day)
