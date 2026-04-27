"""Legacy ConstrainedScheduler methods (split mixin part)."""

from __future__ import annotations

import math
import os
import random
import time
import typing
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

from ...activities import get_activity_by_name, get_all_activities
from ...models import Activity, Day, ScheduleEntry, TimeSlot, Troop, Zone, generate_time_slots
from .. import config_loader
from ..constants import SchedulerConstants
from ..validators import would_create_excess_day_for_entries

EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()
WATER_GAMES_SOFT_ACTIVITIES = {"Aqua Trampoline", "Water Polo", "Greased Watermelon"}
WATER_GAMES_SOFT_CONFLICTS = tuple(
    tuple(pair)
    for pair in SchedulerConstants.SOFT_SAME_DAY_CONFLICTS
    if len(pair) == 2 and set(pair).issubset(WATER_GAMES_SOFT_ACTIVITIES)
)

class LegacyPart01Mixin:
    """Scheduler legacy methods part 01."""

    def _check_and_schedule_reflection(self, troop: Troop) -> bool:
        """
        SMART REFLECTION: Check if troop has only 1 Friday slot remaining.
        If so, immediately schedule Reflection in that slot.

        Call this after ANY Friday slot is filled for a troop.
        Returns True if Reflection was scheduled, False otherwise.
        """
        # Check if troop already has Reflection
        has_reflection = any(e.activity.name == "Reflection" 
                            for e in self.schedule.entries 
                            if e.troop == troop)

        if has_reflection:
            return False  # Already have Reflection

        # Get Friday slots
        if self._friday_slots is None:
            self._friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]

        # Count free Friday slots
        free_friday = [s for s in self._friday_slots if self.schedule.is_troop_free(s, troop)]

        if len(free_friday) == 1:
            # Only 1 slot left - schedule Reflection NOW
            reflection = get_activity_by_name("Reflection")
            if reflection:
                slot = free_friday[0]
                self._add_to_schedule(slot, reflection, troop)
                print(f"  [Smart Reflection] {troop.name}: Reflection -> {slot} (triggered: 1 slot left)")
                return True

        return False


    def _add_to_schedule(self, slot: TimeSlot, activity: Activity, troop: Troop) -> bool:
        """
        Wrapper to add an entry to the schedule and update staff load tracking.
        Relies on Schedule.add_entry() for atomic multi-slot scheduling and validation.
        """
        # 1. Try to add via Schedule model (handles multi-slot logic and atomic check)
        if not self.schedule.add_entry(slot, activity, troop):
            return False

        # 2. Update staff load for ALL slots occupied
        # Calculate derived slots strictly matching add_entry logic
        effective_slots = self.schedule._get_effective_slots(activity, troop)
        slots_needed = int(effective_slots + 0.5)

        all_slots = generate_time_slots()
        try:
            start_idx = all_slots.index(slot)
            for offset in range(slots_needed):
                if start_idx + offset >= len(all_slots):
                    break

                next_slot = all_slots[start_idx + offset]

                # add_entry logic stops at day boundary
                if next_slot.day != slot.day:
                    break

                # Update staff load
                self._update_staff_load(next_slot, activity.name, delta=1)

                # Update total staff tracking
                if activity.name in self.ACTIVITY_STAFF_COUNT:
                    self.total_staff_by_slot[next_slot] += self.ACTIVITY_STAFF_COUNT[activity.name]
        except ValueError:
            pass

        self._mark_schedule_changed()
        return True


    def _mark_schedule_changed(self):
        """Central cache invalidation hook for any schedule mutation."""
        self._cache_valid = False
        self._troop_day_counts_cache.clear()
        if hasattr(self, "cache") and self.cache:
            self.cache.invalidate_schedule_caches()

    def _rebuild_staff_tracking(self) -> None:
        """Recompute staff-load caches from schedule entries after direct mutations."""
        self.total_staff_by_slot = defaultdict(int)
        self.staff_load_by_slot = defaultdict(lambda: defaultdict(int))
        for entry in self.schedule.entries:
            self._update_staff_load(entry.time_slot, entry.activity.name, delta=1)
            if entry.activity.name in self.ACTIVITY_STAFF_COUNT:
                self.total_staff_by_slot[entry.time_slot] += self.ACTIVITY_STAFF_COUNT[entry.activity.name]
        self._mark_schedule_changed()


    def _snapshot_scheduler_state(self) -> dict:
        """Capture mutable scheduler state for transactional swap rollback."""
        return {
            "entries": list(self.schedule.entries),
            "total_staff_by_slot": dict(self.total_staff_by_slot),
            "staff_load_by_slot": {slot: dict(z) for slot, z in self.staff_load_by_slot.items()},
            "troop_top5_scheduled": dict(self.troop_top5_scheduled),
            "troop_top10_scheduled": dict(self.troop_top10_scheduled),
            "troop_progress": {k: set(v) for k, v in self.troop_progress.items()},
            "troop_has_delta": dict(self.troop_has_delta),
            "troop_has_super_troop": dict(self.troop_has_super_troop),
            "delta_was_swapped": set(self.delta_was_swapped),
        }


    def _restore_scheduler_state(self, snapshot: dict) -> None:
        """Rollback to a known-good scheduler state."""
        self.schedule.entries = list(snapshot["entries"])
        self.total_staff_by_slot = defaultdict(int, snapshot["total_staff_by_slot"])
        restored_staff = defaultdict(lambda: defaultdict(int))
        for slot, zone_counts in snapshot["staff_load_by_slot"].items():
            restored_staff[slot].update(zone_counts)
        self.staff_load_by_slot = restored_staff
        self.troop_top5_scheduled = dict(snapshot["troop_top5_scheduled"])
        self.troop_top10_scheduled = dict(snapshot["troop_top10_scheduled"])
        self.troop_progress = {k: set(v) for k, v in snapshot["troop_progress"].items()}
        self.troop_has_delta = dict(snapshot["troop_has_delta"])
        self.troop_has_super_troop = dict(snapshot["troop_has_super_troop"])
        self.delta_was_swapped = set(snapshot["delta_was_swapped"])
        self._mark_schedule_changed()


    def _remove_from_schedule(self, entry: ScheduleEntry) -> bool:
        """Remove an entry and continuation slots with staff/caches kept in sync."""
        if entry not in self.schedule.entries:
            return False

        effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
        slots_needed = int(effective_slots + 0.5)
        day = entry.time_slot.day

        # Anchor removal to the real activity instance start so continuation-slot removals
        # do not leave orphaned pieces of multi-slot activities behind.
        same_instance_entries = sorted(
            [
                e for e in self.schedule.entries
                if e.troop == entry.troop
                and e.activity.name == entry.activity.name
                and e.time_slot.day == day
            ],
            key=lambda e: e.time_slot.slot_number,
        )
        slot_numbers = {e.time_slot.slot_number for e in same_instance_entries}
        target_slot_num = entry.time_slot.slot_number
        start_slot_num = target_slot_num

        if slots_needed > 1:
            min_candidate = max(1, target_slot_num - slots_needed + 1)
            for candidate_start in range(min_candidate, target_slot_num + 1):
                if all((candidate_start + i) in slot_numbers for i in range(slots_needed)):
                    start_slot_num = candidate_start
                    break

        all_slots = generate_time_slots()
        start_slot = next(
            (s for s in all_slots if s.day == day and s.slot_number == start_slot_num),
            None,
        )
        if not start_slot:
            return False

        try:
            start_idx = all_slots.index(start_slot)
        except ValueError:
            return False

        removed_any = False
        for offset in range(slots_needed):
            if start_idx + offset >= len(all_slots):
                break
            next_slot = all_slots[start_idx + offset]
            if next_slot.day != day:
                break
            target = next(
                (
                    e
                    for e in self.schedule.entries
                    if e.troop == entry.troop
                    and e.activity.name == entry.activity.name
                    and e.time_slot == next_slot
                ),
                None,
            )
            if not target:
                continue
            self.schedule.entries.remove(target)
            self._update_staff_load(next_slot, entry.activity.name, delta=-1)
            if entry.activity.name in self.ACTIVITY_STAFF_COUNT:
                self.total_staff_by_slot[next_slot] -= self.ACTIVITY_STAFF_COUNT[entry.activity.name]
            removed_any = True

        if removed_any:
            self._mark_schedule_changed()
        return removed_any


    def _beach_slot_preference_rank(
        self,
        troop: Troop,
        activity: Activity,
        slot: TimeSlot,
        day: Day,
        *,
        relax_constraints: bool = False,
        allow_top1_beach_slot2: bool = False,
    ) -> int:
        """
        Rank beach slot desirability for scheduling order.
        Lower is better.

        0: preferred slot (1/3 on non-Thu, 1 on Thu)
        1: slot 2 is acceptable only when no valid preferred slot exists
        2: slot 2 should be avoided because a valid slot 1/3 exists
        """
        if activity.name not in self.BEACH_SLOT_ACTIVITIES:
            return 0

        # Thursday has only two slots; prefer 1 over 2.
        if day == Day.THURSDAY:
            if slot.slot_number == 1:
                return 0
            if slot.slot_number == 2:
                return 1
            return 2

        # Preferred non-Thursday beach slots are 1 and 3.
        if slot.slot_number in (1, 3):
            return 0

        # For slot 2 on non-Thursday, identify whether slot 1/3 is actually feasible now.
        if slot.slot_number == 2:
            alternative_exists = False
            for alt_num in (1, 3):
                alt_slot = next(
                    (
                        ts
                        for ts in self.time_slots
                        if ts.day == day and ts.slot_number == alt_num
                    ),
                    None,
                )
                if alt_slot is None:
                    continue
                if self._can_schedule(
                    troop,
                    activity,
                    alt_slot,
                    day,
                    relax_constraints=relax_constraints,
                    allow_top1_beach_slot2=allow_top1_beach_slot2,
                ):
                    alternative_exists = True
                    break
            return 2 if alternative_exists else 1

        return 2


    def _projected_preference_gain(self, pref_rank: int) -> float:
        """Approximate regression-checker preference gain for placing this rank."""
        if pref_rank is None:
            return 0.0
        if pref_rank < 0:
            return 0.0
        if pref_rank < 5:
            return [5.4, 4.7, 4.1, 3.4, 2.7][pref_rank]
        if pref_rank < 10:
            return [2.6, 2.4, 2.3, 2.2, 2.0][pref_rank - 5]
        if pref_rank < 14:
            return [1.8, 1.6, 1.4, 1.2][pref_rank - 10]
        if pref_rank < 20:
            # Deep hits are bonuses in evaluate_week.
            return [1.0, 0.8, 0.6, 0.4, 0.2, 0.0][min(pref_rank - 14, 5)]
        return 0.0


    def _would_fill_cluster_gap(self, troop: Troop, activity: Activity, slot: TimeSlot) -> bool:
        """Check if placing this activity fills an official area-level 1,-,3 gap."""
        if slot.day == Day.THURSDAY or slot.slot_number != 2:
            return False

        area_name = self._get_cluster_area_name_for_activity(
            activity.name,
            include_commissioner=False,
            authoritative_gap=True,
        )
        if not area_name:
            return False
        activity_area_set = self._get_authoritative_gap_area_map().get(area_name, set())

        day_entries = [
            e for e in self.schedule.entries
            if e.time_slot.day == slot.day
        ]
        has_1 = any(e.time_slot.slot_number == 1 and e.activity.name in activity_area_set for e in day_entries)
        has_3 = any(e.time_slot.slot_number == 3 and e.activity.name in activity_area_set for e in day_entries)
        has_2 = any(e.time_slot.slot_number == 2 and e.activity.name in activity_area_set for e in day_entries)
        return (
            has_1
            and has_3
            and not has_2
        )


    def _projected_score_delta_for_slot(
        self,
        troop: Troop,
        activity: Activity,
        slot: TimeSlot,
        pref_rank: Optional[int],
    ) -> float:
        """
        Lightweight projected score delta aligned to evaluate_week/BRAIN priorities.
        Used as a re-ranking signal, not as a hard constraint override.
        """
        delta = self._projected_preference_gain(pref_rank)
        troop_day_count = sum(
            1
            for e in self.schedule.entries
            if e.troop == troop and e.time_slot.day == slot.day
        )
        delta += troop_day_count * 0.45

        area_name = self._get_cluster_area_name_for_activity(
            activity.name,
            include_commissioner=False,
            authoritative_gap=True,
        )
        area_day_count = 0
        opens_new_area_day = False
        if area_name:
            area_activities = self._get_authoritative_gap_area_map().get(area_name, set())
            area_day_count = sum(
                1
                for e in self.schedule.entries
                if e.activity.name in area_activities and e.time_slot.day == slot.day
            )
            opens_new_area_day = area_day_count == 0
            if area_day_count > 0:
                delta += min(2.4, 0.9 + (area_day_count * 0.5))
            else:
                delta -= 1.2

        # Efficiency: avoid troop-local area spread; reward filling true 1,-,3 gaps.
        if self._would_create_excess_day(activity.name, slot.day, troop=troop):
            delta -= 4.5
        if opens_new_area_day:
            delta -= 1.1
        if self._would_fill_cluster_gap(troop, activity, slot):
            delta += 3.0

        # Soft constraints: beach slot-2 is always a score penalty in evaluate_week.
        if activity.name in self.BEACH_SLOT_ACTIVITIES and slot.day != Day.THURSDAY and slot.slot_number == 2:
            delta -= 0.6
            if pref_rank is None or pref_rank >= 5:
                delta -= 1.5

        # Staff balancing approximation aligned with scoring: ease heavy slots
        # and build up light ones, without treating staff as a hard override.
        activity_staff = self._get_activity_staff_count(activity.name)
        if activity_staff > 0:
            current_staff = self._get_total_staff_score(slot)
            staff_loads = [self._get_total_staff_score(s) for s in self.time_slots]
            avg_staff = sum(staff_loads) / len(staff_loads) if staff_loads else 0
            target_staff = config_loader.get_target_staff_global()
            max_staff = config_loader.get_max_staff_global()

            def staff_cost(load: int) -> float:
                cost = abs(load - avg_staff)
                if load > target_staff:
                    cost += (load - target_staff) * 1.5
                if load > max_staff:
                    cost += (load - max_staff) * 3.0
                return cost

            projected_slot_staff = current_staff + activity_staff
            cost_delta = staff_cost(projected_slot_staff) - staff_cost(current_staff)
            if cost_delta > 0:
                delta -= min(1.2, cost_delta * 0.25)
            elif not opens_new_area_day and not self._would_create_excess_day(activity.name, slot.day, troop=troop):
                delta += min(0.6, abs(cost_delta) * 0.18)

        # Expectation alignment: keep this pass focused on staff and AT sharing;
        # Delta timing is measured by the scorer, but broad Delta day nudges can
        # compete with official cluster scoring.
        if activity.name == "Super Troop" and slot.day in {Day.MONDAY, Day.TUESDAY}:
            delta += 0.5
        if activity.name == "Aqua Trampoline" and (troop.scouts + troop.adults) <= 16:
            sharing_exists = any(
                e.time_slot == slot
                and e.activity.name == "Aqua Trampoline"
                and (e.troop.scouts + e.troop.adults) <= 16
                for e in self.schedule.entries
            )
            if sharing_exists:
                delta += 4.0
        if slot.day == Day.FRIDAY and activity.name != "Reflection":
            delta -= 0.35

        return delta


    def _rerank_slots_by_projected_score(
        self,
        troop: Troop,
        activity: Activity,
        ordered_slots: List[TimeSlot],
        pref_rank: Optional[int],
        top_n: int = 8,
    ) -> List[TimeSlot]:
        """
        Re-rank top candidate slots by projected regression-score improvement.
        Keeps original ordering as tie-breaker and only applies to higher-priority prefs.
        """
        if pref_rank is None or pref_rank < 5 or pref_rank >= self.REGRESSION_ALIGNMENT_PREF_CUTOFF:
            return ordered_slots
        if not ordered_slots:
            return ordered_slots

        head = ordered_slots[:top_n]
        tail = ordered_slots[top_n:]
        scored = []
        for idx, slot in enumerate(head):
            projected = self._projected_score_delta_for_slot(troop, activity, slot, pref_rank)
            scored.append((projected, idx, slot))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [slot for _, _, slot in scored] + tail


    def _comprehensive_clustering_optimization(self):
        """
        Single comprehensive optimization phase for clustering and swaps.

        Consolidates phases 17, 18, 20, 21, 23, 24:
        - Consolidate staff areas onto fewer days
        - Cross-schedule clustering optimization
        - Slot swap optimization
        - Comprehensive smart swaps
        - Preference improvement swaps
        - Staff distribution balancing
        """
        # Staff distribution balance (run BEFORE consolidation so clustering wins)
        self._balance_staff_distribution()

        # Consolidate staff onto fewer days (run AFTER balance to override spreads)
        self._consolidate_staff_areas()

        # Smart swaps for clustering and preferences (most comprehensive)
        self._comprehensive_smart_swaps()

        # Neutral-beneficial cross-troop swaps (same-slot swaps for clustering)
        self._neutral_beneficial_swaps()

        # NEW: Aggressive excess day reduction swaps (finds swaps like BH Archery+Hemp Craft)
        # This specifically targets swaps that reduce excess days for multiple areas
        self._aggressive_excess_day_reduction_swaps()

        # NEW: Cross-troop same-activity swaps (e.g., Pow's Super Troop <-> another troop's Super Troop)
        # This consolidates same activities onto fewer days
        self._aggressive_cross_troop_same_activity_swaps()

        # NEW: Targeted de-dup pass for same-day accuracy activity conflicts.
        # Uses strict same-troop swaps with rollback checks.
        self._targeted_accuracy_day_dedup_swaps()

        # NEW: Targeted de-dup pass for Water Games same-day soft conflicts.
        # Avoids Aqua Trampoline / Water Polo / Greased Watermelon pairings when safe.
        self._targeted_water_games_day_dedup_swaps()

        # NEW: Targeted wet/dry violation repairs with week-wide strict swaps.
        self._targeted_wet_dry_dedup_swaps()

        # NEW: Allow controlled Top-5 slot swaps when they improve global quality.
        self._targeted_top5_metric_swaps()


    def _count_accuracy_same_day_violations(self) -> int:
        """Count global same-day accuracy violations (Rifle/Shotgun/Archery per troop/day)."""
        violations = 0
        for troop in self.troops:
            for day in Day:
                acts = {
                    e.activity.name
                    for e in self.schedule.entries
                    if e.troop == troop and e.time_slot.day == day and e.activity.name in self.ACCURACY_ACTIVITIES
                }
                if len(acts) >= 2:
                    violations += 1
        return violations


    def _count_excess_cluster_days(self) -> int:
        """
        Count excess cluster days using the same definition as regression checker:
        required_days = ceil(activity_count / 3) for authoritative SKULL cluster areas.
        """
        import math

        cluster_areas = self._get_authoritative_gap_area_map()
        total_excess = 0

        for activities in cluster_areas.values():
            activities = set(activities)
            if not activities:
                continue
            entries = [e for e in self.schedule.entries if e.activity.name in activities]
            if not entries:
                continue
            unique_days = {e.time_slot.day for e in entries}
            required_days = math.ceil(len(entries) / 3.0)
            total_excess += max(0, len(unique_days) - required_days)

        return total_excess


    def _count_wet_dry_violations(self) -> int:
        """Count global wet/dry violations across all troops and days."""
        violations = 0
        for troop in self.troops:
            for day in Day:
                if self._check_wet_dry_violation_for_troop_on_day(troop, day):
                    violations += 1
        return violations


    def _count_global_tp_pair_violations(self) -> int:
        """Count global same-day Trading Post pair violations."""
        return sum(
            1
            for troop in self.troops
            for day in Day
            if self._has_tp_pair_violation_on_day(troop, day)
        )


    def _count_global_water_games_pair_violations(self) -> int:
        """Count configured Water Games same-day soft violations."""
        return sum(
            1
            for troop in self.troops
            for day in Day
            for _ in self._water_games_pair_violations_on_day(troop, day)
        )


    def _count_global_shower_order_violations(self) -> int:
        """Count global shower ordering violations."""
        return sum(
            1
            for troop in self.troops
            for day in Day
            if self._has_shower_order_violation_on_day(troop, day)
        )


    def _count_area_cluster_gaps(self) -> int:
        """Count area-level 1,-,3 cluster gaps without logging side effects."""
        cluster_areas = self._get_authoritative_gap_area_map()
        total = 0
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            day_entries = [e for e in self.schedule.entries if e.time_slot.day == day]
            for area_acts in cluster_areas.values():
                has_1 = any(e.time_slot.slot_number == 1 and e.activity.name in area_acts for e in day_entries)
                has_3 = any(e.time_slot.slot_number == 3 and e.activity.name in area_acts for e in day_entries)
                has_2 = any(e.time_slot.slot_number == 2 and e.activity.name in area_acts for e in day_entries)
                if has_1 and has_3 and not has_2:
                    total += 1
        return total


    def _count_commissioner_day_misses_for_metrics(self) -> int:
        """Count commissioner-managed entries that are off their fixed commissioner day."""
        commissioner_activities = {
            "Delta",
            "Super Troop",
            "Troop Rifle",
            "Troop Shotgun",
            "Archery",
            "Climbing Tower",
        } | set(self.TOWER_ODS_ACTIVITIES)

        misses = 0
        for entry in self.schedule.entries:
            if entry.activity.name not in commissioner_activities:
                continue
            expected = self._get_activity_commissioner_day_fixed(entry.troop, entry.activity.name)
            if expected and entry.time_slot.day != expected:
                misses += 1
        return misses

    def _schedule_quality_snapshot(self) -> dict:
        """Capture the current optimization metrics with official clustering emphasis."""
        excess = self._count_excess_cluster_days()
        gaps = self._count_area_cluster_gaps()
        commissioner = self._count_commissioner_day_misses_for_metrics()
        wet = self._count_wet_dry_violations()
        accuracy = self._count_accuracy_same_day_violations()
        tp = self._count_global_tp_pair_violations()
        water_games = self._count_global_water_games_pair_violations()
        shower = self._count_global_shower_order_violations()
        soft_total = wet + accuracy + tp + water_games + shower
        composite = (
            25 * excess
            + 15 * gaps
            + 4 * wet
            + 4 * accuracy
            + 2 * tp
            + 2 * water_games
            + 2 * shower
            + commissioner
        )
        return {
            "excess": excess,
            "gaps": gaps,
            "commissioner": commissioner,
            "wet": wet,
            "accuracy": accuracy,
            "tp": tp,
            "water_games": water_games,
            "shower": shower,
            "soft_total": soft_total,
            "composite": composite,
        }

    def _is_quality_snapshot_improvement(
        self,
        baseline: dict,
        candidate: dict,
        *,
        require_commissioner_improvement: bool = False,
    ) -> bool:
        """Compare two snapshots with clustering prioritized over commissioner ownership."""
        if candidate["excess"] > baseline["excess"]:
            return False
        if candidate["gaps"] > baseline["gaps"]:
            return False
        if candidate["soft_total"] > baseline["soft_total"]:
            return False
        if require_commissioner_improvement and candidate["commissioner"] >= baseline["commissioner"]:
            return False

        if candidate["composite"] < baseline["composite"]:
            return True
        if candidate["excess"] < baseline["excess"]:
            return True
        if candidate["gaps"] < baseline["gaps"]:
            return True
        if candidate["soft_total"] < baseline["soft_total"]:
            return True
        if candidate["commissioner"] < baseline["commissioner"] and candidate["composite"] <= baseline["composite"]:
            return True
        return False


    def _composite_schedule_quality_score(self) -> int:
        """
        Lower is better.
        Emphasize clustering quality while also accounting for commissioner-day fit
        and known soft-pattern regressions.
        """
        return self._schedule_quality_snapshot()["composite"]


    def _targeted_top5_metric_swaps(self) -> int:
        """
        Try strict same-troop swaps that move Top-5 activities to better slots/days.

        Acceptance guardrails:
        - never increase non-exempt Top 5 misses
        - must strictly improve composite schedule-quality score
        """
        print("    [Top5 Metric Swaps] Starting targeted Top-5 swap pass...")
        if os.getenv("ENABLE_TOP5_METRIC_SWAPS", "1").strip().lower() in {"0", "false", "no", "off"}:
            print("    [Top5 Metric Swaps] Disabled by environment")
            return 0
        protected = self._get_protected_activity_names({"Sailing"})
        fixes = 0
        max_fixes = min(max(6, len(self.troops)), 18)
        time_budget_s = float(os.getenv("TOP5_METRIC_SWAP_BUDGET_SECONDS", "1.5"))
        started = time.monotonic()
        candidate_checks = 0
        candidate_check_cap = max(30, len(self.troops) * 8)

        improved = True
        while improved and fixes < max_fixes:
            if time.monotonic() - started > time_budget_s:
                break
            improved = False
            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            if baseline_non_exempt > 0:
                # Avoid expensive quality swaps while Top-5 recovery is still pending.
                break
            baseline_metrics = self._schedule_quality_snapshot()
            baseline_score = baseline_metrics["composite"]

            for troop in sorted(self.troops, key=lambda t: t.name):
                troop_entries = [e for e in self.schedule.entries if e.troop == troop and e.activity.slots <= 1]
                if not troop_entries:
                    continue

                top5_set = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
                top5_entries = [
                    e for e in troop_entries
                    if e.activity.name in top5_set and e.activity.name not in protected
                ]
                if not top5_entries:
                    continue

                # Start with lower-value Top-5 items (rank 5 -> 1).
                top5_entries.sort(
                    key=lambda e: (troop.get_priority(e.activity.name), e.time_slot.day.value, e.time_slot.slot_number),
                    reverse=True,
                )
                top5_entries = top5_entries[:3]

                non_top5_entries = [
                    e for e in troop_entries
                    if e.activity.name not in top5_set and e.activity.name not in protected
                ]
                if not non_top5_entries:
                    continue
                non_top5_entries.sort(
                    key=lambda e: (troop.get_priority(e.activity.name), e.time_slot.day.value, e.time_slot.slot_number),
                    reverse=True,
                )
                non_top5_entries = non_top5_entries[:6]

                moved_for_troop = False
                for top5_entry in top5_entries:
                    for other in non_top5_entries:
                        if time.monotonic() - started > time_budget_s:
                            break
                        if other == top5_entry:
                            continue
                        if top5_entry.time_slot == other.time_slot:
                            continue
                        if top5_entry.time_slot.day == other.time_slot.day:
                            continue

                        slot_top5 = top5_entry.time_slot
                        name_top5 = top5_entry.activity.name
                        slot_other = other.time_slot
                        name_other = other.activity.name

                        candidate_checks += 1
                        if candidate_checks > candidate_check_cap:
                            break
                        if not self._try_strict_swap_same_troop(top5_entry, other):
                            continue

                        new_non_exempt, _ = self._count_non_exempt_top5_misses()
                        new_metrics = self._schedule_quality_snapshot()
                        new_score = new_metrics["composite"]
                        if (
                            new_non_exempt <= baseline_non_exempt
                            and self._is_quality_snapshot_improvement(
                                baseline_metrics,
                                new_metrics,
                            )
                        ):
                            fixes += 1
                            improved = True
                            moved_for_troop = True
                            print(
                                f"      [Top5 Swap] {troop.name}: {name_top5} "
                                f"{slot_top5.day.name[:3]}-{slot_top5.slot_number} <-> "
                                f"{name_other} {slot_other.day.name[:3]}-{slot_other.slot_number} "
                                f"(score {baseline_score}->{new_score})"
                            )
                            baseline_non_exempt = new_non_exempt
                            baseline_metrics = new_metrics
                            baseline_score = new_score
                            break

                        # Undo if guardrails/objective not satisfied.
                        self._undo_same_troop_swap(troop, slot_top5, name_top5, slot_other, name_other)

                    if moved_for_troop or fixes >= max_fixes:
                        break
                    if candidate_checks > candidate_check_cap:
                        break
                if fixes >= max_fixes:
                    break
                if candidate_checks > candidate_check_cap:
                    break

        if fixes > 0:
            print(f"    [Top5 Metric Swaps] Completed {fixes} improving swap(s)")
        else:
            print("    [Top5 Metric Swaps] No improving swaps found")
        return fixes


    def _targeted_accuracy_day_dedup_swaps(self) -> int:
        """
        Reduce same-day accuracy duplicates via week-wide same-troop strict swaps.
        Guardrails:
        - must reduce accuracy violations
        - must not increase non-exempt Top 5 misses
        - must not increase excess cluster days
        """
        protected = self._get_protected_activity_names({"Sailing"})
        fixes = 0
        max_fixes = max(8, len(self.troops) * 2)

        print("    [Accuracy De-dup] Starting targeted strict swaps...")

        improved = True
        while improved and fixes < max_fixes:
            improved = False
            baseline_accuracy = self._count_accuracy_same_day_violations()
            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            baseline_excess_days = self._count_excess_cluster_days()

            if baseline_accuracy == 0:
                break

            for troop in sorted(self.troops, key=lambda t: t.name):
                made_for_troop = False
                for day in Day:
                    day_accuracy = [
                        e for e in self.schedule.entries
                        if e.troop == troop and e.time_slot.day == day and e.activity.name in self.ACCURACY_ACTIVITIES
                    ]
                    if len({e.activity.name for e in day_accuracy}) < 2:
                        continue

                    # Prefer moving the lower-value accuracy activity.
                    day_accuracy.sort(
                        key=lambda e: (troop.get_priority(e.activity.name), e.time_slot.slot_number),
                        reverse=True,
                    )
                    source = day_accuracy[0]
                    swap_candidates = [
                        e for e in self.schedule.entries
                        if e.troop == troop
                        and e.time_slot.day != day
                        and e.activity.slots <= 1
                        and e.activity.name not in protected
                        and e.activity.name not in self.ACCURACY_ACTIVITIES
                    ]
                    swap_candidates.sort(
                        key=lambda e: (
                            troop.get_priority(e.activity.name) < 5,
                            troop.get_priority(e.activity.name),
                            e.time_slot.day.value,
                            e.time_slot.slot_number,
                        )
                    )

                    for other in swap_candidates:
                        slot_a = source.time_slot
                        act_a = source.activity.name
                        slot_b = other.time_slot
                        act_b = other.activity.name
                        if not self._try_strict_swap_same_troop(source, other):
                            continue

                        new_accuracy = self._count_accuracy_same_day_violations()
                        new_non_exempt, _ = self._count_non_exempt_top5_misses()
                        new_excess_days = self._count_excess_cluster_days()
                        if (
                            new_accuracy < baseline_accuracy
                            and new_non_exempt <= baseline_non_exempt
                            and new_excess_days <= baseline_excess_days
                        ):
                            fixes += 1
                            improved = True
                            made_for_troop = True
                            print(
                                f"      [Accuracy Swap] {troop.name}: {act_a} "
                                f"{slot_a.day.name[:3]}-{slot_a.slot_number} <-> "
                                f"{act_b} {slot_b.day.name[:3]}-{slot_b.slot_number}"
                            )
                            break

                        # Undo when guardrails are not met.
                        self._undo_same_troop_swap(troop, slot_a, act_a, slot_b, act_b)

                    if made_for_troop or fixes >= max_fixes:
                        break

                if made_for_troop or fixes >= max_fixes:
                    break

        if fixes > 0:
            print(f"    [Accuracy De-dup] Applied {fixes} strict swap fix(es)")
        else:
            print("    [Accuracy De-dup] No safe swaps found")
        return fixes


    def _targeted_water_games_day_dedup_swaps(self) -> int:
        """
        Reduce same-day Water Games pairs via week-wide same-troop strict swaps.
        Guardrails preserve hard metrics, cluster shape, and existing soft metrics.
        """
        protected = self._get_protected_activity_names({"Sailing"})
        fixes = 0
        max_fixes = max(8, len(self.troops) * 2)

        print("    [Water Games De-dup] Starting targeted strict swaps...")

        improved = True
        while improved and fixes < max_fixes:
            improved = False
            baseline_water_games = self._count_global_water_games_pair_violations()
            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            baseline_excess_days = self._count_excess_cluster_days()
            baseline_cluster_gaps = self._count_area_cluster_gaps()
            baseline_wet = self._count_wet_dry_violations()
            baseline_accuracy = self._count_accuracy_same_day_violations()
            baseline_tp_pairs = self._count_global_tp_pair_violations()
            baseline_shower_order = self._count_global_shower_order_violations()

            if baseline_water_games == 0:
                break

            for troop in sorted(self.troops, key=lambda t: t.name):
                made_for_troop = False
                for day in Day:
                    if not self._water_games_pair_violations_on_day(troop, day):
                        continue

                    day_entries = [
                        e for e in self.schedule.entries
                        if e.troop == troop
                        and e.time_slot.day == day
                        and e.activity.name in WATER_GAMES_SOFT_ACTIVITIES
                        and e.activity.slots <= 1
                        and e.activity.name not in protected
                    ]
                    if len(day_entries) < 2:
                        continue

                    def conflict_count(entry: ScheduleEntry) -> int:
                        return sum(
                            1
                            for pair in WATER_GAMES_SOFT_CONFLICTS
                            if entry.activity.name in pair
                            and any(
                                other.activity.name in pair
                                and other.activity.name != entry.activity.name
                                for other in day_entries
                            )
                        )

                    day_entries.sort(
                        key=lambda e: (
                            -conflict_count(e),
                            -troop.get_priority(e.activity.name),
                            e.time_slot.slot_number,
                        )
                    )

                    for source in day_entries:
                        swap_candidates = [
                            e for e in self.schedule.entries
                            if e.troop == troop
                            and e.time_slot.day != day
                            and e.activity.slots <= 1
                            and e.activity.name not in protected
                            and e.activity.name not in WATER_GAMES_SOFT_ACTIVITIES
                        ]
                        swap_candidates.sort(
                            key=lambda e: (
                                troop.get_priority(e.activity.name) < 5,
                                troop.get_priority(e.activity.name),
                                e.time_slot.day.value,
                                e.time_slot.slot_number,
                            )
                        )

                        best_signature = None
                        best_score = None
                        for other in swap_candidates[:30]:
                            slot_a = source.time_slot
                            act_a = source.activity.name
                            slot_b = other.time_slot
                            act_b = other.activity.name
                            if not self._try_strict_swap_same_troop(source, other):
                                continue

                            new_water_games = self._count_global_water_games_pair_violations()
                            new_non_exempt, _ = self._count_non_exempt_top5_misses()
                            new_excess_days = self._count_excess_cluster_days()
                            new_cluster_gaps = self._count_area_cluster_gaps()
                            new_wet = self._count_wet_dry_violations()
                            new_accuracy = self._count_accuracy_same_day_violations()
                            new_tp_pairs = self._count_global_tp_pair_violations()
                            new_shower_order = self._count_global_shower_order_violations()
                            if (
                                new_water_games < baseline_water_games
                                and new_non_exempt <= baseline_non_exempt
                                and new_excess_days <= baseline_excess_days
                                and new_cluster_gaps <= baseline_cluster_gaps
                                and new_wet <= baseline_wet
                                and new_accuracy <= baseline_accuracy
                                and new_tp_pairs <= baseline_tp_pairs
                                and new_shower_order <= baseline_shower_order
                            ):
                                pref_delta = troop.get_priority(act_b) - troop.get_priority(act_a)
                                score = (
                                    baseline_water_games - new_water_games,
                                    baseline_excess_days - new_excess_days,
                                    baseline_cluster_gaps - new_cluster_gaps,
                                    baseline_wet - new_wet,
                                    baseline_accuracy - new_accuracy,
                                    baseline_tp_pairs - new_tp_pairs,
                                    baseline_shower_order - new_shower_order,
                                    -max(0, pref_delta),
                                )
                                if best_score is None or score > best_score:
                                    best_score = score
                                    best_signature = (slot_a, act_a, slot_b, act_b)

                            self._undo_same_troop_swap(troop, slot_a, act_a, slot_b, act_b)

                        if best_signature:
                            slot_a, act_a, slot_b, act_b = best_signature
                            src_now = next(
                                (
                                    e for e in self.schedule.entries
                                    if e.troop == troop and e.time_slot == slot_a and e.activity.name == act_a
                                ),
                                None,
                            )
                            other_now = next(
                                (
                                    e for e in self.schedule.entries
                                    if e.troop == troop and e.time_slot == slot_b and e.activity.name == act_b
                                ),
                                None,
                            )
                            if src_now and other_now and self._try_strict_swap_same_troop(src_now, other_now):
                                fixes += 1
                                improved = True
                                made_for_troop = True
                                print(
                                    f"      [Water Games Swap] {troop.name}: {act_a} "
                                    f"{slot_a.day.name[:3]}-{slot_a.slot_number} <-> "
                                    f"{act_b} {slot_b.day.name[:3]}-{slot_b.slot_number}"
                                )
                                break

                        if made_for_troop or fixes >= max_fixes:
                            break

                    if made_for_troop or fixes >= max_fixes:
                        break

                if made_for_troop or fixes >= max_fixes:
                    break

        if fixes > 0:
            print(f"    [Water Games De-dup] Applied {fixes} strict swap fix(es)")
        else:
            print("    [Water Games De-dup] No safe swaps found")
        return fixes


    def _targeted_wet_dry_dedup_swaps(self) -> int:
        """
        Reduce wet/dry violations via week-wide strict same-troop swaps.
        Guardrails:
        - must reduce wet/dry violations
        - must not increase non-exempt Top 5 misses
        - must not increase excess cluster days
        - must not increase accuracy same-day violations
        """
        protected = self._get_protected_activity_names({"Sailing"})
        fixes = 0
        max_fixes = max(8, len(self.troops) * 2)

        print("    [Wet/Dry De-dup] Starting targeted strict swaps...")

        improved = True
        while improved and fixes < max_fixes:
            improved = False
            baseline_wet = self._count_wet_dry_violations()
            baseline_non_exempt, _ = self._count_non_exempt_top5_misses()
            baseline_excess_days = self._count_excess_cluster_days()
            baseline_accuracy = self._count_accuracy_same_day_violations()
            baseline_tp_pairs = self._count_global_tp_pair_violations()
            baseline_water_games = self._count_global_water_games_pair_violations()
            baseline_shower_order = self._count_global_shower_order_violations()

            if baseline_wet == 0:
                break

            for troop in sorted(self.troops, key=lambda t: t.name):
                made_for_troop = False
                for day in Day:
                    if not self._check_wet_dry_violation_for_troop_on_day(troop, day):
                        continue

                    day_entries = [
                        e for e in self.schedule.entries
                        if e.troop == troop and e.time_slot.day == day and e.activity.slots <= 1
                    ]
                    by_slot = {e.time_slot.slot_number: e for e in day_entries}

                    # Prefer moving "problematic" activities first.
                    preferred = []
                    preferred_keys = set()
                    if (
                        1 in by_slot and 2 in by_slot and 3 in by_slot
                        and by_slot[1].activity.name in self.WET_ACTIVITIES
                        and by_slot[2].activity.name not in self.WET_ACTIVITIES
                        and by_slot[3].activity.name in self.WET_ACTIVITIES
                    ):
                        preferred.extend([by_slot[1], by_slot[3]])
                        preferred_keys.update({(1, by_slot[1].activity.name), (3, by_slot[3].activity.name)})
                    # Add wet/tower adjacency candidates.
                    preferred.extend(
                        [
                            e for e in day_entries
                            if e.activity.name in self.WET_ACTIVITIES
                            or e.activity.name in self.TOWER_ODS_ACTIVITIES
                        ]
                    )
                    # De-duplicate and drop protected/invalid.
                    seen = set()
                    source_candidates = []
                    for e in preferred + day_entries:
                        key = (e.time_slot.day, e.time_slot.slot_number, e.activity.name)
                        if key in seen:
                            continue
                        seen.add(key)
                        if e.activity.name in protected:
                            continue
                        source_candidates.append(e)

                    # Move lower-value source entries first, but prioritize clear WDW edge offenders.
                    source_candidates.sort(
                        key=lambda e: (
                            ((e.time_slot.slot_number, e.activity.name) not in preferred_keys),
                            troop.get_priority(e.activity.name),
                            e.time_slot.slot_number,
                        ),
                        reverse=True,
                    )

                    for source in source_candidates:
                        swap_candidates = [
                            e for e in self.schedule.entries
                            if e.troop == troop
                            and e.time_slot.day != day
                            and e.activity.slots <= 1
                            and e.activity.name not in protected
                            and e.activity.name not in self.WET_ACTIVITIES
                            and e.activity.name not in self.TOWER_ODS_ACTIVITIES
                        ]
                        swap_candidates.sort(
                            key=lambda e: (
                                troop.get_priority(e.activity.name) < 5,
                                troop.get_priority(e.activity.name),
                                e.time_slot.day.value,
                                e.time_slot.slot_number,
                            )
                        )

                        # Evaluate multiple options and apply only the best safe move.
                        best_signature = None
                        best_score = None
                        for other in swap_candidates[:24]:
                            slot_a = source.time_slot
                            act_a = source.activity.name
                            slot_b = other.time_slot
                            act_b = other.activity.name
                            if not self._try_strict_swap_same_troop(source, other):
                                continue

                            new_wet = self._count_wet_dry_violations()
                            new_non_exempt, _ = self._count_non_exempt_top5_misses()
                            new_excess_days = self._count_excess_cluster_days()
                            new_accuracy = self._count_accuracy_same_day_violations()
                            new_tp_pairs = self._count_global_tp_pair_violations()
                            new_water_games = self._count_global_water_games_pair_violations()
                            new_shower_order = self._count_global_shower_order_violations()
                            if (
                                new_wet < baseline_wet
                                and new_non_exempt <= baseline_non_exempt
                                and new_excess_days <= baseline_excess_days
                                and new_accuracy <= baseline_accuracy
                                and new_tp_pairs <= baseline_tp_pairs
                                and new_water_games <= baseline_water_games
                                and new_shower_order <= baseline_shower_order
                            ):
                                pref_delta = troop.get_priority(act_b) - troop.get_priority(act_a)
                                score = (
                                    baseline_wet - new_wet,
                                    baseline_accuracy - new_accuracy,
                                    baseline_excess_days - new_excess_days,
                                    baseline_tp_pairs - new_tp_pairs,
                                    baseline_water_games - new_water_games,
                                    baseline_shower_order - new_shower_order,
                                    -max(0, pref_delta),
                                )
                                if best_score is None or score > best_score:
                                    best_score = score
                                    best_signature = (slot_a, act_a, slot_b, act_b)

                            # Undo when guardrails are not met.
                            self._undo_same_troop_swap(troop, slot_a, act_a, slot_b, act_b)

                        if best_signature:
                            slot_a, act_a, slot_b, act_b = best_signature
                            src_now = next(
                                (
                                    e for e in self.schedule.entries
                                    if e.troop == troop and e.time_slot == slot_a and e.activity.name == act_a
                                ),
                                None,
                            )
                            other_now = next(
                                (
                                    e for e in self.schedule.entries
                                    if e.troop == troop and e.time_slot == slot_b and e.activity.name == act_b
                                ),
                                None,
                            )
                            if src_now and other_now and self._try_strict_swap_same_troop(src_now, other_now):
                                fixes += 1
                                improved = True
                                made_for_troop = True
                                print(
                                    f"      [Wet/Dry Swap] {troop.name}: {act_a} "
                                    f"{slot_a.day.name[:3]}-{slot_a.slot_number} <-> "
                                    f"{act_b} {slot_b.day.name[:3]}-{slot_b.slot_number}"
                                )
                                break

                        if made_for_troop or fixes >= max_fixes:
                            break

                    if made_for_troop or fixes >= max_fixes:
                        break

                if made_for_troop or fixes >= max_fixes:
                    break

        if fixes > 0:
            print(f"    [Wet/Dry De-dup] Applied {fixes} strict swap fix(es)")
        else:
            print("    [Wet/Dry De-dup] No safe swaps found")
        return fixes


    def _comprehensive_final_cleanup(self):
        """
        Single comprehensive cleanup phase that handles all final validation
        and gap-filling in the correct order.

        Consolidates phases 22-42 into one well-ordered cleanup with iteration limit.
        Prevents the excessive back-and-forth of the original 20+ cleanup phases.
        """
        print("  [Comprehensive Final Cleanup - Max 3 iterations]")
        max_iterations = 3  # Prevent infinite loops

        for iteration in range(1, max_iterations + 1):
            print(f"    Iteration {iteration}...")
            changes_made = False
            entries_before = len(self.schedule.entries)

            # 1. Remove conflicts (exclusive activities, activity conflicts)
            self._remove_activity_conflicts()
            self._cleanup_exclusive_activities()
            if len(self.schedule.entries) != entries_before:
                changes_made = True
                print(f"      Removed conflicts: {entries_before - len(self.schedule.entries)} entries")

            # 2. Remove overlaps
            entries_before = len(self.schedule.entries)
            self._remove_overlaps()
            if len(self.schedule.entries) != entries_before:
                changes_made = True
                print(f"      Removed overlaps: {entries_before - len(self.schedule.entries)} entries")

            # 3. Deduplicate
            self._deduplicate_entries()

            # 4. Guarantee mandatory activities (Reflection, Super Troop)
            self._guarantee_mandatory_activities()

            # 5. Fill empty slots
            self._fill_empty_slots_final()

            # 6. Fix beach slot violations (move slot 2 -> slot 1/3)
            self._fix_beach_slot_violations()

            # 7. Ensure HC/DG pairing (must have Gaga Ball or 9 Square)
            self._ensure_hc_dg_pairing()

            # If no changes, we're stable - break early
            if not changes_made:
                print(f"      No changes detected - cleanup stable after {iteration} iteration(s)")
                break

        # Final gap guarantee (force-fill if needed)
        print("    Final gap guarantee...")
        self._guarantee_no_gaps()

        # Final safety check for exclusivity violations
        self._sanitize_exclusivity()
        print("  [Cleanup Complete]")


    def _comprehensive_gap_check(self, phase_name: str) -> int:
        """Detect area-level cluster gaps using the 1,-,3 same-area definition."""
        from ...models import Day
        cluster_areas = self._get_authoritative_gap_area_map()

        total_gaps = 0
        gap_details = []
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            day_entries = [e for e in self.schedule.entries if e.time_slot.day == day]
            for area_name, area_acts in cluster_areas.items():
                has_1 = any(
                    e.time_slot.slot_number == 1 and e.activity.name in area_acts
                    for e in day_entries
                )
                has_3 = any(
                    e.time_slot.slot_number == 3 and e.activity.name in area_acts
                    for e in day_entries
                )
                has_2 = any(
                    e.time_slot.slot_number == 2 and e.activity.name in area_acts
                    for e in day_entries
                )
                if has_1 and has_3 and not has_2:
                    total_gaps += 1
                    gap_details.append(f"{day.name[:3]}: {area_name} pattern 1,-,3")

        if total_gaps > 0:
            print(f"  [GAP CHECK] {phase_name}: {total_gaps} area cluster gaps (1,-,3) detected!")
            for detail in gap_details[:8]:
                print(f"    {detail}")
            if len(gap_details) > 8:
                print(f"    ... and {len(gap_details) - 8} more area/day entries")
        else:
            print(f"  [GAP CHECK] {phase_name}: No area cluster gaps detected [OK]")

        return total_gaps


    def _fix_multislot_integrity(self):
        """
        Fix any multi-slot activities that have lost their continuation slots.

        This runs at the very end to catch any corruption from earlier phases.
        For each multi-slot activity, ensures all required slots exist.
        """
        from ...models import Day, TimeSlot, ScheduleEntry

        print("  [Multi-Slot Integrity] Checking all multi-slot activities...")

        # Get all multi-slot activities and their required slot counts
        # Dynamically build multi-slot activity map from source of truth
        # This ensures we catch ALL multi-slot activities defined in activities.py
        MULTI_SLOT_ACTIVITIES = {}

        if self.activities:
            for activity in self.activities:
                if activity.slots > 1:
                    # Round 1.5 -> 2, 2 -> 2, 3 -> 3
                    slots = int(activity.slots + 0.5)
                    MULTI_SLOT_ACTIVITIES[activity.name] = slots

        # Fallback from configured activity metadata if self.activities is empty.
        if not MULTI_SLOT_ACTIVITIES:
            for activity_name in self._get_multi_slot_activity_names():
                activity = get_activity_by_name(activity_name)
                if activity and activity.slots > 1:
                    MULTI_SLOT_ACTIVITIES[activity.name] = int(activity.slots + 0.5)

        print(f"  [Multi-Slot Integrity] Verifying {len(MULTI_SLOT_ACTIVITIES)} activity types: {sorted(list(MULTI_SLOT_ACTIVITIES.keys()))}")

        fixed_count = 0
        removed_count = 0

        # Group entries by (troop, activity, day) to find incomplete multi-slot activities
        activity_groups = {}
        for entry in self.schedule.entries:
            if entry.activity.name in MULTI_SLOT_ACTIVITIES:
                key = (entry.troop.name, entry.activity.name, entry.time_slot.day.name)
                if key not in activity_groups:
                    activity_groups[key] = []
                activity_groups[key].append(entry)

        # Check each group for completeness
        all_slots = generate_time_slots()

        for (troop_name, activity_name, day_name), entries in activity_groups.items():
            # Expected slots are troop-specific for some activities (e.g., Climbing Tower),
            # so compute from effective slot model, not static map.
            expected_slots = int(self.schedule._get_effective_slots(entries[0].activity, entries[0].troop) + 0.5)
            actual_slots = len({e.time_slot.slot_number for e in entries})

            if actual_slots < expected_slots:
                print(f"    [DEBUG] INCOMPLETE: {troop_name} {activity_name} @ {day_name} - has {actual_slots}/{expected_slots} slots")
                # Missing slots! Try to add them
                troop = entries[0].troop
                activity = entries[0].activity
                day = entries[0].time_slot.day

                # Find the starting slot (lowest slot number).
                # Exception: Thursday 3-slot day-request opt-out always starts
                # at slot 1 (consumes Thu 1+2+3), regardless of which remnants
                # survived earlier cleanup passes.
                if (day == Day.THURSDAY
                        and self._is_day_request_thursday_3slot(troop, activity)):
                    start_slot = 1
                else:
                    start_slot = min(e.time_slot.slot_number for e in entries)

                # Determine which slots are missing
                existing_slot_nums = {e.time_slot.slot_number for e in entries}
                needed_slot_nums = set(range(start_slot, start_slot + expected_slots))
                missing_slot_nums = needed_slot_nums - existing_slot_nums

                # Try to add missing slots
                for slot_num in sorted(missing_slot_nums):
                    # Find the TimeSlot object
                    time_slot = None
                    for ts in all_slots:
                        if ts.day == day and ts.slot_number == slot_num:
                            time_slot = ts
                            break

                    # Missing slot object means this slot is not valid for the day (e.g. Thu-3).
                    if not time_slot:
                        # Exception: Thursday 3-slot day-request opt-out authorizes
                        # a virtual Thu-3 (troop skips mandatory 3rd-slot camp event).
                        if (day == Day.THURSDAY
                                and self._is_day_request_thursday_3slot(troop, activity)):
                            time_slot = TimeSlot(day=Day.THURSDAY, slot_number=slot_num)
                        else:
                            print(f"    [REMOVE] {troop_name} {activity_name} @ {day_name} - slot {slot_num} is not a valid timeslot")
                            for e in entries:
                                if e in self.schedule.entries:
                                    self.schedule.entries.remove(e)
                                    removed_count += 1
                            break

                    # Check if slot is within day bounds
                    max_slot = 2 if day == Day.THURSDAY else 3
                    # Exception: Thursday 3-slot day-request opt-out extends to slot 3.
                    if (day == Day.THURSDAY
                            and self._is_day_request_thursday_3slot(troop, activity)):
                        max_slot = 3
                    if slot_num > max_slot:
                        # Can't add - would exceed day bounds
                        # Remove the incomplete activity instead
                        print(f"    [REMOVE] {troop_name} {activity_name} @ {day_name} - slot {slot_num} exceeds day bounds")
                        for e in entries:
                            if e in self.schedule.entries:
                                self.schedule.entries.remove(e)
                                removed_count += 1
                        break

                    # Check if troop is free in this slot
                    troop_busy = any(
                        e.troop == troop 
                        and e.time_slot.day == time_slot.day 
                        and e.time_slot.slot_number == time_slot.slot_number 
                        for e in self.schedule.entries
                    )

                    if not troop_busy:
                        # Exception: Thu-3 opt-out uses direct append because
                        # add_entry relies on generate_time_slots which doesn't
                        # include Thu-3.
                        if (day == Day.THURSDAY and slot_num == 3
                                and self._is_day_request_thursday_3slot(troop, activity)):
                            self.schedule.entries.append(ScheduleEntry(
                                time_slot=time_slot, activity=activity, troop=troop
                            ))
                            fixed_count += 1
                            print(f"    [FIXED] {troop_name} {activity_name} @ {day_name} - added virtual slot {slot_num} (Thu-3hr opt-out)")
                        elif self.schedule.add_entry(time_slot, activity, troop):
                            fixed_count += 1
                            print(f"    [FIXED] {troop_name} {activity_name} @ {day_name} - added slot {slot_num}")
                    else:
                        # Slot is occupied by another activity - try moving blocker first
                        blocker = next(
                            (e for e in self.schedule.entries
                             if e.troop == troop
                             and e.time_slot.day == time_slot.day
                             and e.time_slot.slot_number == time_slot.slot_number),
                            None
                        )
                        if blocker:
                            # ROOT CAUSE: Don't remove multi-slot activity and create gaps.
                            # Try moving the blocker to free the slot.
                            moved_blocker = False
                            for alt in self.time_slots:
                                if alt.day != day or alt.slot_number == slot_num:
                                    continue
                                if not self.schedule.is_troop_free(alt, troop):
                                    continue
                                if not self.schedule.is_activity_available(alt, blocker.activity, troop):
                                    continue
                                self.schedule.entries.remove(blocker)
                                if self.schedule.add_entry(alt, blocker.activity, troop):
                                    moved_blocker = True
                                    if self.schedule.add_entry(time_slot, activity, troop):
                                        fixed_count += 1
                                        print(f"    [FIXED] {troop_name} {activity_name} @ {day_name} (moved blocker {blocker.activity.name})")
                                    else:
                                        # Rollback blocker move
                                        new_entry = next((e for e in self.schedule.entries
                                                         if e.troop == troop and e.activity == blocker.activity
                                                         and e.time_slot == alt), None)
                                        if new_entry:
                                            self.schedule.entries.remove(new_entry)
                                        self.schedule.entries.append(blocker)
                                    break
                                self.schedule.entries.append(blocker)
                            if not moved_blocker:
                                # Last resort: remove incomplete activity (gap fill will replace)
                                print(f"    [CONFLICT] {troop_name} {activity_name} @ {day_name} slot {slot_num} blocked by {blocker.activity.name} (could not move)")
                                for e in entries:
                                    if e in self.schedule.entries:
                                        self.schedule.entries.remove(e)
                                        removed_count += 1
                        break

        if fixed_count > 0:
            print(f"  [Multi-Slot Integrity] Fixed {fixed_count} missing slots")
        if removed_count > 0:
            print(f"  [Multi-Slot Integrity] Removed {removed_count} entries from incomplete activities")
        if fixed_count == 0 and removed_count == 0:
            print("  [Multi-Slot Integrity] All multi-slot activities complete")


    def _final_comprehensive_validation(self):
        """Perform final comprehensive validation of the schedule."""
        print("  [Final Validation] Checking schedule integrity...")

        # ALWAYS run gap guarantee - ensures 100% slot completeness (Spine: No Empty Slots)
        gaps = self._comprehensive_gap_check("Final Validation")
        if gaps > 0:
            print(f"    Found {gaps} gaps - fixing...")
        self._guarantee_no_gaps()  # Unconditional: fill any gaps before return

        # Re-run multi-slot integrity check AFTER gap filling
        # Gap filling can introduce incomplete multi-slot activities
        print("  [Final Validation] Re-checking multi-slot integrity after gap fill...")
        self._fix_multislot_integrity()

        # FINAL SAFETY NET: If integrity check removed activities, fill the new gaps!
        self._guarantee_no_gaps()

        # Enforce hard adjacency rule: Delta cannot be adjacent to Tower/ODS.
        self._fix_delta_tower_ods_adjacency()
        self._fix_beach_activity_saturation()
        self._final_shower_trading_soft_cleanup()
        self._guarantee_no_gaps()
        # Late hard-normalization passes belong inside final validation so the returned
        # schedule is not mutated again after being marked valid.
        self._sanitize_exclusivity()
        self._enforce_sailing_slot_exclusivity()
        # Gap fill can reintroduce staffed beach overloads; enforce saturation again at the end.
        self._fix_beach_activity_saturation()
        self._fix_multislot_integrity()
        self._guarantee_no_gaps()
        self._guarantee_mandatory_activities()

        # Check critical constraints
        self._validate_critical_constraints()

        # Hard acceptance gate: non-exempt Top 5 misses must be zero.
        # Retry targeted recovery passes before failing the run.
        max_repair_passes = 3
        for repair_pass in range(1, max_repair_passes + 1):
            non_exempt_miss_count, miss_details = self._count_non_exempt_top5_misses()
            if non_exempt_miss_count == 0:
                print("  [Final Validation] Non-exempt Top 5 misses: 0 [OK]")
                break

            print(
                f"  [Final Validation] Non-exempt Top 5 misses: {non_exempt_miss_count} "
                f"[REPAIR PASS {repair_pass}/{max_repair_passes}]"
            )
            for troop_name, activity_name, rank in miss_details[:10]:
                print(f"    - {troop_name}: {activity_name} (Top {rank})")

            # Run the strongest available Top 5 recovery sequence.
            self._guarantee_all_top5()
            self._enforce_mandatory_top5()
            self._recover_missing_top5()
            # Global hill-climb: keep only moves that strictly reduce miss count.
            for _ in range(20):
                if not self._attempt_global_top5_repair_step():
                    break
            # Bounded local search over targeted move candidates.
            self._bounded_top5_reoptimization(max_steps=64)
            self._guarantee_no_gaps()
            self._fix_multislot_integrity()

            # Keep hard constraints in view between repair passes.
            self._validate_critical_constraints()
        else:
            # We exhausted repair passes and still have non-exempt misses.
            final_count, final_details = self._count_non_exempt_top5_misses()
            preview = ", ".join(
                f"{troop}/{activity}#${rank}".replace("#$", "#")
                for troop, activity, rank in final_details[:5]
            )
            raise ValueError(
                f"Final acceptance failed: {final_count} non-exempt Top 5 misses remain. "
                f"Examples: {preview}"
            )

        # Final Top-5 repair can reclaim slots after Phase D and leave the
        # delivered schedule with avoidable excess cluster days. Run one
        # guarded cleanup now that the hard Top-5 contract is restored.
        post_top5_snapshot = self._snapshot_scheduler_state()
        post_top5_non_exempt, _ = self._count_non_exempt_top5_misses()
        post_top5_excess = self._count_excess_cluster_days()
        post_top5_gaps = self._count_area_cluster_gaps()
        if post_top5_non_exempt == 0 and (post_top5_excess > 0 or post_top5_gaps > 0):
            cluster_moves = self._aggressive_excess_day_reduction_swaps()
            if cluster_moves:
                self._fix_multislot_integrity()
                self._guarantee_no_gaps()
                after_cluster_non_exempt, _ = self._count_non_exempt_top5_misses()
                after_cluster_excess = self._count_excess_cluster_days()
                after_cluster_gaps = self._count_area_cluster_gaps()
                if (
                    after_cluster_non_exempt > post_top5_non_exempt
                    or after_cluster_excess > post_top5_excess
                    or after_cluster_gaps > post_top5_gaps
                ):
                    print("  [Final Validation] Rolling back post-Top5 cluster repair")
                    self._restore_scheduler_state(post_top5_snapshot)
                else:
                    print(
                        "  [Final Validation] Post-Top5 cluster repair OK "
                        f"(excess {post_top5_excess}->{after_cluster_excess}, "
                        f"gaps {post_top5_gaps}->{after_cluster_gaps})"
                    )

        final_gap_count = self._count_area_cluster_gaps()
        if final_gap_count > 0:
            print(
                f"  [Final Validation] Re-running official gap repair on {final_gap_count} remaining gap(s)..."
            )
            self._optimize_cluster_gaps_post_fill()
            self._fix_multislot_integrity()
            self._guarantee_no_gaps()
            self._validate_critical_constraints()

        # MUST-HONOR seal (runs after all repairs / gap fill / multi-slot fixes).
        # Earlier passes may use ignore_day_requests or relocations that push
        # day-requested activities off their authored days; this is the last
        # authoritative placement before the returned schedule is considered final.
        print("  [Final Validation] MUST-HONOR day-request seal (post-repair)...")
        day_request_result = self._schedule_day_requests(
            pass_label="Final Validation — MUST-HONOR seal", aggressive=True
        )
        if day_request_result and day_request_result.get("unfulfilled"):
            preview = ", ".join(
                f"{troop}/{activity} on {day} ({reason})"
                for troop, activity, day, reason in day_request_result["unfulfilled"][:5]
            )
            raise ValueError(
                "Final acceptance failed: feasible day request(s) remain unfulfilled. "
                f"Examples: {preview}"
            )
        # Fast-path: skip terminal re-sanitization work when no day-request
        # seal moves were made. This keeps the no-day-request troop path
        # identical to the pre-seal legacy behavior and avoids disrupting
        # placements that are already clean (e.g. tight unit-test fixtures).
        troops_with_day_requests = any(
            getattr(t, "day_requests", None) for t in self.troops
        )
        if troops_with_day_requests:
            self._fix_multislot_integrity()
            self._guarantee_no_gaps()
            self._guarantee_mandatory_activities()
            # Gap-fill or MUST-HONOR placements can reintroduce beach-slot
            # saturation on a per-slot basis. Re-enforce the hard cap as the
            # very last mutating step before validation.
            self._fix_beach_activity_saturation()
            self._fix_multislot_integrity()
            self._guarantee_no_gaps()
            self._validate_critical_constraints()
            seal_cluster_snapshot = self._snapshot_scheduler_state()
            seal_non_exempt, _ = self._count_non_exempt_top5_misses()
            seal_excess = self._count_excess_cluster_days()
            seal_gaps = self._count_area_cluster_gaps()
            if seal_non_exempt == 0 and (seal_excess > 0 or seal_gaps > 0):
                print("  [Final Validation] Post-day-request cluster offender repair...")
                seal_cluster_moves = self._aggressive_excess_day_reduction_swaps()
                if seal_cluster_moves:
                    self._fix_multislot_integrity()
                    self._guarantee_no_gaps()
                    self._validate_critical_constraints()
                    after_seal_non_exempt, _ = self._count_non_exempt_top5_misses()
                    after_seal_excess = self._count_excess_cluster_days()
                    after_seal_gaps = self._count_area_cluster_gaps()
                    if (
                        after_seal_non_exempt > seal_non_exempt
                        or after_seal_excess > seal_excess
                        or after_seal_gaps > seal_gaps
                    ):
                        print("  [Final Validation] Rolling back post-day-request cluster repair")
                        self._restore_scheduler_state(seal_cluster_snapshot)
                    else:
                        print(
                            "  [Final Validation] Post-day-request cluster repair OK "
                            f"(excess {seal_excess}->{after_seal_excess}, "
                            f"gaps {seal_gaps}->{after_seal_gaps})"
                        )
            final_count, final_details = self._count_non_exempt_top5_misses()
            if final_count > 0:
                preview = ", ".join(
                    f"{troop}/{activity}#{rank}"
                    for troop, activity, rank in final_details[:5]
                )
                raise ValueError(
                    f"Final acceptance failed after day-request seal: "
                    f"{final_count} non-exempt Top 5 misses remain. Examples: {preview}"
                )

        print("  [Final Validation] Complete")


    def _fix_delta_tower_ods_adjacency(self):
        """Fix hard constraint: Delta cannot be adjacent to Tower/ODS on same day."""
        tower_ods_activities = set(EXCLUSIVE_AREAS.get("Tower", [])) | set(EXCLUSIVE_AREAS.get("Outdoor Skills", []))
        fixes = 0

        for troop in self.troops:
            for day in Day:
                day_entries = [
                    e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == day
                ]
                if not day_entries:
                    continue

                max_slot = 2 if day == Day.THURSDAY else 3
                delta_entries = [e for e in day_entries if e.activity.name == "Delta"]
                if not delta_entries:
                    continue

                tower_ods_entries = [e for e in day_entries if e.activity.name in tower_ods_activities]
                if not tower_ods_entries:
                    continue

                for delta_entry in list(delta_entries):
                    ds = delta_entry.time_slot.slot_number
                    conflicting = [
                        e for e in tower_ods_entries
                        if abs(e.time_slot.slot_number - ds) <= 1
                    ]
                    if not conflicting:
                        continue

                    # First, try moving Delta to a non-adjacent free slot on the same day.
                    moved = False
                    for target_slot_num in range(1, max_slot + 1):
                        if target_slot_num == ds:
                            continue
                        if any(abs(e.time_slot.slot_number - target_slot_num) <= 1 for e in tower_ods_entries):
                            continue

                        target_slot = TimeSlot(day=day, slot_number=target_slot_num)
                        if not self.schedule.is_troop_free(target_slot, troop):
                            continue
                        if not self.schedule.is_activity_available(target_slot, delta_entry.activity, troop):
                            continue

                        self.schedule.remove_entry(delta_entry)
                        self.schedule.add_entry(target_slot, delta_entry.activity, troop)
                        fixes += 1
                        moved = True
                        break

                    if moved:
                        continue

                    # Next, try moving the conflicting Tower/ODS entry.
                    conflict_entry = conflicting[0]
                    ts = conflict_entry.time_slot.slot_number
                    for target_slot_num in range(1, max_slot + 1):
                        if target_slot_num == ts:
                            continue
                        if abs(target_slot_num - ds) <= 1:
                            continue

                        target_slot = TimeSlot(day=day, slot_number=target_slot_num)
                        if not self.schedule.is_troop_free(target_slot, troop):
                            continue
                        if not self.schedule.is_activity_available(target_slot, conflict_entry.activity, troop):
                            continue

                        self.schedule.remove_entry(conflict_entry)
                        self.schedule.add_entry(target_slot, conflict_entry.activity, troop)
                        fixes += 1
                        moved = True
                        break

                    if moved:
                        continue

                    # Broader attempt 3: move Delta to another day/slot this week.
                    for alt in self.time_slots:
                        if alt.day == day:
                            continue
                        if not self.schedule.is_troop_free(alt, troop):
                            continue
                        if not self.schedule.is_activity_available(alt, delta_entry.activity, troop):
                            continue
                        self.schedule.remove_entry(delta_entry)
                        if self.schedule.add_entry(alt, delta_entry.activity, troop):
                            fixes += 1
                            moved = True
                            break
                        # Restore if add fails unexpectedly.
                        self.schedule.add_entry(delta_entry.time_slot, delta_entry.activity, troop)

                    if moved:
                        continue

                    # Broader attempt 4: move conflicting Tower/ODS entry to another day/slot.
                    conflict_entry = conflicting[0]
                    for alt in self.time_slots:
                        if alt.day == day:
                            continue
                        if not self.schedule.is_troop_free(alt, troop):
                            continue
                        if not self.schedule.is_activity_available(alt, conflict_entry.activity, troop):
                            continue
                        self.schedule.remove_entry(conflict_entry)
                        if self.schedule.add_entry(alt, conflict_entry.activity, troop):
                            fixes += 1
                            moved = True
                            break
                        # Restore if add fails unexpectedly.
                        self.schedule.add_entry(conflict_entry.time_slot, conflict_entry.activity, troop)

                    if moved:
                        continue

                    # ROOT CAUSE: Never drop Delta and create an empty slot.
                    # Replace with filler in same slot so gap fill is unnecessary.
                    if delta_entry in self.schedule.entries:
                        slot = delta_entry.time_slot
                        self.schedule.remove_entry(delta_entry)
                        filler = get_activity_by_name("Campsite Free Time") or get_activity_by_name("Gaga Ball")
                        if filler and self.schedule.add_entry(slot, filler, troop):
                            fixes += 1
                        else:
                            self.schedule.entries.append(delta_entry)  # Restore - don't leave gap

        if fixes > 0:
            print(f"    [Delta/Tower-ODS] Fixed {fixes} adjacency issue(s)")


    def _fix_beach_activity_saturation(self):
        """Enforce hard cap for staffed beach activities per slot."""
        max_beach_acts = config_loader.get_constraints().get("max_beach_staffed_activities", 4)
        beach_staffed = set(SchedulerConstants.BEACH_STAFFED_ACTIVITIES)

        fallback_names = list(self._get_swappable_fill_names())
        fallbacks = [get_activity_by_name(n) for n in fallback_names]
        fallbacks = [f for f in fallbacks if f is not None]

        fixes = 0
        for slot in self.time_slots:
            while True:
                slot_entries = [e for e in self.schedule.entries if e.time_slot == slot]
                beach_entries = [e for e in slot_entries if e.activity.name in beach_staffed]
                if len(beach_entries) <= max_beach_acts:
                    break

                # Remove lowest-value beach entries first (non-Top5 preferred for displacement).
                def displacement_key(entry):
                    rank = entry.troop.get_priority(entry.activity.name)
                    is_top5 = rank < 5
                    return (is_top5, -rank, entry.troop.name)

                beach_entries.sort(key=displacement_key)
                victim = beach_entries[0]
                troop = victim.troop

                moved = False
                # Try moving the same activity to another slot where troop is free.
                for alt in self.time_slots:
                    if alt == slot:
                        continue
                    if not self.schedule.is_troop_free(alt, troop):
                        continue
                    if not self.schedule.is_activity_available(alt, victim.activity, troop):
                        continue
                    self.schedule.remove_entry(victim)
                    if self.schedule.add_entry(alt, victim.activity, troop):
                        fixes += 1
                        moved = True
                        break
                    # Restore if add fails unexpectedly.
                    self.schedule.add_entry(slot, victim.activity, troop)

                if moved:
                    continue

                # Fallback: replace with a non-beach filler in the same slot.
                self.schedule.remove_entry(victim)
                replaced = False
                for fallback in fallbacks:
                    if self.schedule.add_entry(slot, fallback, troop):
                        fixes += 1
                        replaced = True
                        break

                if not replaced:
                    # ROOT CAUSE: Never leave slot empty. Restore victim rather than creating gap.
                    self.schedule.entries.append(victim)

        if fixes > 0:
            print(f"    [Beach Saturation] Fixed {fixes} saturation issue(s)")


    def _try_strict_swap_same_troop(self, entry_a, entry_b) -> bool:
        """Swap two entries for same troop only if strict constraints still pass."""
        if entry_a.troop != entry_b.troop:
            return False
        if entry_a.activity.slots > 1 or entry_b.activity.slots > 1:
            return False
        troop = entry_a.troop
        slot_a = entry_a.time_slot
        slot_b = entry_b.time_slot
        act_a = entry_a.activity
        act_b = entry_b.activity

        # Do not let local cleanup swaps make staff distribution materially
        # worse. Same-staff swaps are neutral; only check unequal staff moves.
        staff_a = self._get_activity_staff_count(act_a.name)
        staff_b = self._get_activity_staff_count(act_b.name)
        if staff_a != staff_b:
            staff_loads = [self._get_total_staff_score(s) for s in self.time_slots]
            avg_staff = sum(staff_loads) / len(staff_loads) if staff_loads else 0
            load_a = self._get_total_staff_score(slot_a)
            load_b = self._get_total_staff_score(slot_b)

            before_cost = (load_a - avg_staff) ** 2 + (load_b - avg_staff) ** 2
            after_a = load_a - staff_a + staff_b
            after_b = load_b - staff_b + staff_a
            after_cost = (after_a - avg_staff) ** 2 + (after_b - avg_staff) ** 2
            if after_cost > before_cost + 2.0:
                return False

        self.schedule.remove_entry(entry_a)
        self.schedule.remove_entry(entry_b)
        can_a = self._can_schedule(troop, act_a, slot_b, slot_b.day, relax_constraints=False)
        can_b = self._can_schedule(troop, act_b, slot_a, slot_a.day, relax_constraints=False)
        if can_a and can_b:
            ok_a = self.schedule.add_entry(slot_b, act_a, troop)
            ok_b = self.schedule.add_entry(slot_a, act_b, troop)
            if ok_a and ok_b:
                return True
            # Defensive restore if partial add succeeded.
            partial_a = next(
                (e for e in self.schedule.entries if e.troop == troop and e.time_slot == slot_b and e.activity.name == act_a.name),
                None,
            )
            partial_b = next(
                (e for e in self.schedule.entries if e.troop == troop and e.time_slot == slot_a and e.activity.name == act_b.name),
                None,
            )
            if partial_a:
                self.schedule.remove_entry(partial_a)
            if partial_b:
                self.schedule.remove_entry(partial_b)
        self.schedule.add_entry(slot_a, act_a, troop)
        self.schedule.add_entry(slot_b, act_b, troop)
        return False


    def _has_tp_pair_violation_on_day(self, troop: Troop, day: Day) -> bool:
        day_acts = {
            e.activity.name
            for e in self.schedule.entries
            if e.troop == troop and e.time_slot.day == day
        }
        return "Trading Post" in day_acts and (
            "Shower House" in day_acts or "Campsite Free Time" in day_acts
        )


    def _water_games_pair_violations_on_day(self, troop: Troop, day: Day) -> List[tuple[str, str]]:
        day_acts = {
            e.activity.name
            for e in self.schedule.entries
            if e.troop == troop and e.time_slot.day == day
        }
        return [
            pair
            for pair in WATER_GAMES_SOFT_CONFLICTS
            if set(pair).issubset(day_acts)
        ]


    def _has_shower_order_violation_on_day(self, troop: Troop, day: Day) -> bool:
        """True when Shower House appears before a later wet/Super Troop activity on a day."""
        day_entries = [
            e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == day
        ]
        by_slot = {e.time_slot.slot_number: e for e in day_entries}
        shower = next((e for e in day_entries if e.activity.name == "Shower House"), None)
        if not shower:
            return False
        return any(
            s > shower.time_slot.slot_number
            and (
                by_slot[s].activity.name == "Super Troop"
                or by_slot[s].activity.name in self.WET_ACTIVITIES
            )
            for s in by_slot
        )


    def _count_shower_order_violations(self, troop: Troop) -> int:
        return sum(1 for day in Day if self._has_shower_order_violation_on_day(troop, day))


    def _count_tp_pair_violations(self, troop: Troop) -> int:
        return sum(1 for day in Day if self._has_tp_pair_violation_on_day(troop, day))


    def _undo_same_troop_swap(self, troop: Troop, slot_a: TimeSlot, act_a: str, slot_b: TimeSlot, act_b: str) -> bool:
        """
        Undo a previously applied same-troop strict swap using entry signatures.
        Returns True if undo succeeded.
        """
        moved_a = next(
            (
                e for e in self.schedule.entries
                if e.troop == troop and e.time_slot == slot_b and e.activity.name == act_a
            ),
            None,
        )
        moved_b = next(
            (
                e for e in self.schedule.entries
                if e.troop == troop and e.time_slot == slot_a and e.activity.name == act_b
            ),
            None,
        )
        if not moved_a or not moved_b:
            return False
        return self._try_strict_swap_same_troop(moved_a, moved_b)


    def _final_shower_trading_soft_cleanup(self):
        """
        Low-risk final soft cleanup:
        - Fix Shower House before wet/Super Troop via strict swaps only.
        - Reduce Trading Post + Shower/Campsite same-day via strict swaps only.
        """
        print("    [Soft Cleanup] Shower/Trading targeted pass...")
        fixes = 0
        protected = self._get_protected_activity_names()

        # Pass 1: Shower ordering (same-day strict swaps only).
        for troop in sorted(self.troops, key=lambda t: t.name):
            for day in Day:
                day_entries = [
                    e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == day
                ]
                by_slot = {e.time_slot.slot_number: e for e in day_entries}
                shower = next((e for e in day_entries if e.activity.name == "Shower House"), None)
                if not shower:
                    continue
                has_later_wet_or_super = any(
                    s > shower.time_slot.slot_number
                    and (by_slot[s].activity.name == "Super Troop" or by_slot[s].activity.name in self.WET_ACTIVITIES)
                    for s in by_slot
                )
                if not has_later_wet_or_super:
                    continue

                max_slot = 2 if day == Day.THURSDAY else 3
                resolved = False
                for slot_num in range(max_slot, shower.time_slot.slot_number, -1):
                    target = by_slot.get(slot_num)
                    if not target:
                        continue
                    if target.activity.name in protected:
                        continue
                    if self._try_strict_swap_same_troop(shower, target):
                        fixes += 1
                        resolved = True
                        break
                if resolved:
                    continue

                # Fallback: cross-day strict swap that improves shower ordering without
                # increasing same-day Trading Post pair violations for this troop.
                baseline_shower = self._count_shower_order_violations(troop)
                baseline_tp = self._count_tp_pair_violations(troop)
                candidates = [
                    e for e in self.schedule.entries
                    if e.troop == troop
                    and e.time_slot.day != day
                    and e.activity.slots <= 1
                    and e.activity.name not in protected
                    and e.activity.name != "Shower House"
                ]
                candidates.sort(key=lambda e: (e.activity.name in self.WET_ACTIVITIES, e.time_slot.day.value, e.time_slot.slot_number))
                for other in candidates:
                    slot_a = shower.time_slot
                    act_a = shower.activity.name
                    slot_b = other.time_slot
                    act_b = other.activity.name
                    if not self._try_strict_swap_same_troop(shower, other):
                        continue
                    new_shower = self._count_shower_order_violations(troop)
                    new_tp = self._count_tp_pair_violations(troop)
                    if new_shower < baseline_shower and new_tp <= baseline_tp:
                        fixes += 1
                        resolved = True
                        break
                    self._undo_same_troop_swap(troop, slot_a, act_a, slot_b, act_b)

        # Pass 2: Trading pair violations (cross-day strict swaps only).
        for troop in sorted(self.troops, key=lambda t: t.name):
            for day in Day:
                if not self._has_tp_pair_violation_on_day(troop, day):
                    continue
                day_entries = [
                    e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == day
                ]
                problem_entries = [
                    e for e in day_entries if e.activity.name in {"Trading Post", "Shower House", "Campsite Free Time"}
                ]
                # Prefer moving Shower/Campsite before moving Trading Post.
                problem_entries.sort(key=lambda e: (e.activity.name == "Trading Post", e.time_slot.slot_number))

                resolved = False
                for problem in problem_entries:
                    if problem.activity.slots > 1 or problem.activity.name in protected:
                        continue
                    for other in [
                        e
                        for e in self.schedule.entries
                        if e.troop == troop
                        and e.time_slot.day != day
                        and e.activity.slots <= 1
                        and e.activity.name not in protected
                    ]:
                        other_day = other.time_slot.day
                        if self._has_tp_pair_violation_on_day(troop, other_day):
                            continue
                        if not self._try_strict_swap_same_troop(problem, other):
                            continue
                        if self._has_tp_pair_violation_on_day(troop, day):
                            # Swap didn't resolve original day; undo.
                            swapped_back = next(
                                (
                                    e for e in self.schedule.entries
                                    if e.troop == troop and e.time_slot == other.time_slot and e.activity.name == problem.activity.name
                                ),
                                None,
                            )
                            swapped_other = next(
                                (
                                    e for e in self.schedule.entries
                                    if e.troop == troop and e.time_slot == problem.time_slot and e.activity.name == other.activity.name
                                ),
                                None,
                            )
                            if swapped_back and swapped_other:
                                self._try_strict_swap_same_troop(swapped_back, swapped_other)
                            continue
                        fixes += 1
                        resolved = True
                        break
                    if resolved:
                        break

        if fixes > 0:
            print(f"    [Soft Cleanup] Applied {fixes} shower/trading fix(es)")


    def _enforce_super_troop_non_friday(self) -> int:
        """
        Enforce non-Friday Super Troop placement where feasible.
        Uses strict moves/swaps and keeps mandatory anchors protected.
        """
        moved = 0
        unresolved = 0
        protected = self._get_protected_activity_names({"Sailing"})

        for troop in self.troops:
            friday_st = next(
                (
                    e for e in self.schedule.entries
                    if e.troop == troop and e.activity.name == "Super Troop" and e.time_slot.day == Day.FRIDAY
                ),
                None,
            )
            if not friday_st:
                continue

            super_troop = friday_st.activity
            moved_this_troop = False

            for slot in self.time_slots:
                if slot.day == Day.FRIDAY:
                    continue
                if not self.schedule.is_troop_free(slot, troop):
                    continue
                if not self._can_schedule(troop, super_troop, slot, slot.day, relax_constraints=False):
                    continue

                src_slot = friday_st.time_slot
                if self._remove_from_schedule(friday_st):
                    if self._add_to_schedule(slot, super_troop, troop):
                        moved += 1
                        moved_this_troop = True
                        print(
                            f"    [Super Troop Non-Friday] {troop.name}: "
                            f"Fri-{src_slot.slot_number} -> {slot.day.name[:3]}-{slot.slot_number}"
                        )
                        break
                    self._add_to_schedule(src_slot, super_troop, troop)

            if moved_this_troop:
                continue

            friday_st = next(
                (
                    e for e in self.schedule.entries
                    if e.troop == troop and e.activity.name == "Super Troop" and e.time_slot.day == Day.FRIDAY
                ),
                None,
            )
            if not friday_st:
                continue

            candidates = [
                e for e in self.schedule.entries
                if e.troop == troop
                and e.time_slot.day != Day.FRIDAY
                and e.activity.slots <= 1
                and e.activity.name not in protected
            ]
            candidates.sort(
                key=lambda e: (
                    troop.get_priority(e.activity.name) < 5,
                    troop.get_priority(e.activity.name),
                    e.time_slot.day.value,
                    e.time_slot.slot_number,
                ),
                reverse=True,
            )
            for other in candidates:
                slot_fr = friday_st.time_slot
                slot_ot = other.time_slot
                if self._try_strict_swap_same_troop(friday_st, other):
                    moved += 1
                    moved_this_troop = True
                    print(
                        f"    [Super Troop Non-Friday Swap] {troop.name}: "
                        f"Fri-{slot_fr.slot_number} <-> {other.activity.name} "
                        f"{slot_ot.day.name[:3]}-{slot_ot.slot_number}"
                    )
                    break

            if not moved_this_troop:
                unresolved += 1

        if moved > 0:
            print(f"    [Super Troop Non-Friday] moved={moved}, unresolved={unresolved}")
        elif unresolved > 0:
            print(f"    [Super Troop Non-Friday] no safe move for {unresolved} troop(s)")
        return moved


    def _validate_critical_constraints(self):
        """Validate critical constraints are satisfied."""
        from ...models import Day

        self._rebuild_staff_tracking()
        hard_errors = []

        # Check Friday Reflection
        missing_reflection = 0
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries if e.troop == troop
            )
            if not has_reflection:
                missing_reflection += 1

        if missing_reflection > 0:
            print(f"    [WARNING] {missing_reflection} troops missing Friday Reflection")
            hard_errors.append(f"{missing_reflection} troop(s) missing Friday Reflection")
        else:
            print("    [OK] All troops have Friday Reflection")

        missing_super_troop = 0
        for troop in self.troops:
            has_super_troop = any(
                e.activity.name == "Super Troop"
                for e in self.schedule.entries if e.troop == troop
            )
            if not has_super_troop:
                missing_super_troop += 1
        if missing_super_troop > 0:
            print(f"    [WARNING] {missing_super_troop} troops missing Super Troop")
            hard_errors.append(f"{missing_super_troop} troop(s) missing Super Troop")
        else:
            print("    [OK] All troops have Super Troop")

        empty_slots = self._count_troop_empty_slots()
        if empty_slots > 0:
            print(f"    [WARNING] {empty_slots} troop empty slots")
            hard_errors.append(f"{empty_slots} troop empty slot(s)")
        else:
            print("    [OK] No troop empty slots")

        tuesday_only_violations = [
            e for e in self.schedule.entries
            if e.activity.name in {"History Center", "Disc Golf"}
            and e.time_slot.day != Day.TUESDAY
        ]
        if tuesday_only_violations:
            print(f"    [WARNING] {len(tuesday_only_violations)} HC/DG day violations")
            hard_errors.append(f"{len(tuesday_only_violations)} HC/DG Tuesday-only violation(s)")
        else:
            print("    [OK] HC/DG Tuesday-only constraints")

        exclusive_violations = 0
        concurrent = set(self.CONCURRENT_ACTIVITIES)
        for slot in self.time_slots:
            slot_entries = [e for e in self.schedule.entries if e.time_slot == slot]
            for area_name, area_activities in EXCLUSIVE_AREAS.items():
                area_entries = [
                    e for e in slot_entries
                    if e.activity.name in area_activities
                    and e.activity.name not in concurrent
                ]
                if len(area_entries) <= 1:
                    continue
                if area_name == "Sailing" and slot.slot_number == 2 and len(area_entries) <= 2:
                    continue
                if area_name == "Aqua Trampoline":
                    small_troops = [
                        e for e in area_entries
                        if (e.troop.scouts + e.troop.adults) <= 16
                    ]
                    if len(small_troops) == len(area_entries) and len(area_entries) <= 2:
                        continue
                if area_name == "Water Polo" and len(area_entries) <= 2:
                    continue
                exclusive_violations += len(area_entries) - 1

        if exclusive_violations > 0:
            print(f"    [WARNING] {exclusive_violations} exclusive area violations")
            hard_errors.append(f"{exclusive_violations} exclusive area violation(s)")
        else:
            print("    [OK] Exclusive areas")

        # Check beach slot violations using SKULL-driven beach slot restrictions.
        # Sailing is intentionally excluded here; it has a separate slot-2 exception path.
        beach_activities = set(self.BEACH_SLOT_ACTIVITIES)


        beach_violations = 0
        for entry in self.schedule.entries:
            if (hasattr(entry, 'time_slot') and hasattr(entry.time_slot, 'slot_number') and hasattr(entry.time_slot, 'day')):
                if (entry.activity.name in beach_activities and 
                    entry.time_slot.slot_number == 2 and entry.time_slot.day != Day.THURSDAY):
                    troop = entry.troop
                    pref_rank = troop.get_priority(entry.activity.name) if hasattr(troop, 'get_priority') else None
                    if pref_rank is not None and pref_rank < 5:
                        pass  # Valid Top 5 exception (penalty applies but not a violation)
                        # Remove AT exclusive check completely as requested
                    else:
                        beach_violations += 1


        if beach_violations > 0:
            print(f"    [WARNING] {beach_violations} beach slot violations")
        else:
            print("    [OK] No beach slot violations")

        if hard_errors:
            raise ValueError("Critical schedule validation failed: " + "; ".join(hard_errors))


    def _count_non_exempt_top5_misses(self):
        """
        Count non-exempt missed Top 5 preferences using the same unscheduled
        payload builder that feeds schedule JSON and regression reporting.
        """
        from core.services.unscheduled_source import build_unscheduled_data

        unscheduled = build_unscheduled_data(
            self.troops,
            self.schedule,
            getattr(self, "sailing_balls_fills", None),
        )
        misses = []
        for troop_name, troop_data in unscheduled.items():
            for item in troop_data.get("top5", []):
                if not item.get("is_exempt", False):
                    misses.append((troop_name, item.get("name", ""), item.get("rank", 0)))

        return len(misses), misses


    def _get_troop_activity_priority(self, troop: Troop, activity_name: str) -> int:
        """Return troop preference index; 999 if not requested."""
        try:
            return troop.preferences.index(activity_name)
        except ValueError:
            return 999


    def _force_place_with_window_clearing(
        self,
        troop: Troop,
        activity: Activity,
        required_rank: int,
        protected_names: set,
    ) -> bool:
        """
        General-purpose aggressive placement:
        clear a contiguous window of lower-priority activities for multi-slot fit.
        """
        slots_needed = int(self.schedule._get_effective_slots(activity, troop) + 0.5)
        days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
        day_order_default = {Day.MONDAY: 0, Day.TUESDAY: 1, Day.WEDNESDAY: 2, Day.THURSDAY: 3, Day.FRIDAY: 4}
        # For harder Top-5 recoveries, prefer mid-week windows where large 2-slot activities
        # are often recoverable by dropping lower-value fills.
        day_order_scarce = {Day.TUESDAY: 0, Day.WEDNESDAY: 1, Day.MONDAY: 2, Day.THURSDAY: 3, Day.FRIDAY: 4}
        scarce_two_slot = {"Sailing", "Canoe Snorkel", "Float for Floats"}

        candidates = []
        for day in days:
            day_slots = sorted([s for s in self.time_slots if s.day == day], key=lambda s: s.slot_number)
            if len(day_slots) < slots_needed:
                continue

            for start_idx in range(0, len(day_slots) - slots_needed + 1):
                start_slot = day_slots[start_idx]
                window = day_slots[start_idx:start_idx + slots_needed]
                window_nums = {s.slot_number for s in window}

                troop_day_entries = [
                    e for e in self.schedule.entries
                    if e.troop == troop and e.time_slot.day == day and e.time_slot.slot_number in window_nums
                ]

                # Only clear lower-priority, non-protected activities.
                blocked = False
                displacement_cost = 0
                for entry in troop_day_entries:
                    if entry.activity.name in protected_names:
                        blocked = True
                        break
                    entry_rank = self._get_troop_activity_priority(troop, entry.activity.name)
                    if entry_rank <= required_rank:
                        blocked = True
                        break
                    # Lower-value activities (high rank index / non-requested) are cheaper to displace.
                    displacement_cost += max(0, 30 - min(entry_rank, 30))
                if blocked:
                    continue

                day_bias = (
                    day_order_scarce.get(day, 99)
                    if activity.name in scarce_two_slot
                    else day_order_default.get(day, 99)
                )
                # For 2-slot activities on 3-slot days, prefer slot 2-3 windows first.
                slot_bias = 0
                if activity.name in scarce_two_slot and slots_needed == 2:
                    if day != Day.THURSDAY and start_slot.slot_number == 2:
                        slot_bias = -1
                candidates.append(
                    (displacement_cost, day_bias, slot_bias, len(troop_day_entries), start_slot, day, troop_day_entries)
                )

        candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4].slot_number))

        for _, _, _, _, start_slot, day, troop_day_entries in candidates:
            snapshot = self._snapshot_scheduler_state()
            removed_any = False
            unique_entries = sorted(
                troop_day_entries,
                key=lambda e: (e.time_slot.slot_number, e.activity.name),
            )
            for entry in unique_entries:
                if entry not in self.schedule.entries:
                    continue
                if self._remove_from_schedule(entry):
                    removed_any = True

            if not removed_any and not self.schedule.is_troop_free(start_slot, troop):
                self._restore_scheduler_state(snapshot)
                continue

            if self._can_schedule(troop, activity, start_slot, day, relax_constraints=True) and self._add_to_schedule(start_slot, activity, troop):
                return True

            self._restore_scheduler_state(snapshot)

        return False


    def _is_activity_instance_start(self, entry: ScheduleEntry) -> bool:
        """True if this entry is the first slot of its activity instance for this troop/day."""
        slots_needed = int(self.schedule._get_effective_slots(entry.activity, entry.troop) + 0.5)
        if slots_needed <= 1:
            return True
        prev_slot_num = entry.time_slot.slot_number - 1
        if prev_slot_num < 1:
            return True
        return not any(
            e.troop == entry.troop
            and e.activity.name == entry.activity.name
            and e.time_slot.day == entry.time_slot.day
            and e.time_slot.slot_number == prev_slot_num
            for e in self.schedule.entries
        )


    def _reclaim_activity_from_lower_priority_troop(
        self,
        target_troop: Troop,
        activity: Activity,
        required_rank: int,
        protected_names: set,
    ) -> bool:
        """
        General scarce-resource recovery:
        reclaim activity instance from a lower-priority troop and assign to target troop.
        """
        candidate_entries = []
        for entry in self.schedule.entries:
            if entry.activity.name != activity.name:
                continue
            if entry.troop == target_troop:
                continue
            if not self._is_activity_instance_start(entry):
                continue
            if entry.activity.name in protected_names:
                continue

            other_rank = self._get_troop_activity_priority(entry.troop, activity.name)
            # Only reclaim from non-Top5 or lower-priority requests to avoid creating new Top5 misses.
            if other_rank <= 4:
                continue
            if other_rank <= required_rank:
                continue
            candidate_entries.append((entry, other_rank))

        # Reclaim from the worst-priority holders first.
        candidate_entries.sort(key=lambda x: x[1], reverse=True)

        for entry, other_rank in candidate_entries:
            snapshot = self._snapshot_scheduler_state()
            start_slot = entry.time_slot

            if not self._remove_from_schedule(entry):
                self._restore_scheduler_state(snapshot)
                continue

            # Clear target troop conflicts in the required window if they are lower-priority.
            slots_needed = int(self.schedule._get_effective_slots(activity, target_troop) + 0.5)
            window_slots = [
                TimeSlot(day=start_slot.day, slot_number=start_slot.slot_number + i)
                for i in range(slots_needed)
            ]
            blocked = False
            target_conflicts = [
                e for e in self.schedule.entries
                if e.troop == target_troop
                and e.time_slot.day == start_slot.day
                and any(e.time_slot.slot_number == ws.slot_number for ws in window_slots)
            ]
            for conflict in target_conflicts:
                if conflict.activity.name in protected_names:
                    blocked = True
                    break
                if self._get_troop_activity_priority(target_troop, conflict.activity.name) <= required_rank:
                    blocked = True
                    break
            if blocked:
                self._restore_scheduler_state(snapshot)
                continue

            for conflict in target_conflicts:
                if conflict in self.schedule.entries:
                    self._remove_from_schedule(conflict)

            if not self._can_schedule(target_troop, activity, start_slot, start_slot.day, relax_constraints=True):
                self._restore_scheduler_state(snapshot)
                continue
            if not self._add_to_schedule(start_slot, activity, target_troop):
                self._restore_scheduler_state(snapshot)
                continue

            # Best-effort: fill displaced troop's vacated slot using normal filler logic.
            self._fill_vacated_slot(entry.troop, start_slot)
            print(
                f"    [RECLAIM] {target_troop.name}: {activity.name} (Top {required_rank + 1}) "
                f"<- {entry.troop.name} (rank #{other_rank + 1}) @ {start_slot}"
            )
            return True

        return False


    def _try_place_with_displacement_recovery(
        self,
        troop: Troop,
        activity: Activity,
        required_rank: int,
        protected_names: set,
    ) -> bool:
        """
        Aggressive Top-5 repair:
        place target activity by clearing a contiguous window, then recover any displaced
        higher-priority same-troop activities to avoid trading one Top-5 miss for another.
        """
        slots_needed = int(self.schedule._get_effective_slots(activity, troop) + 0.5)
        days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

        def _relocate_friday_reflection_for_window(window_slots: set[int]) -> bool:
            reflection_entries = [
                e for e in self.schedule.entries
                if e.troop == troop and e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
            ]
            if not reflection_entries:
                return True
            reflection_entry = reflection_entries[0]
            if reflection_entry.time_slot.slot_number not in window_slots:
                return True

            friday_slots = sorted([s for s in self.time_slots if s.day == Day.FRIDAY], key=lambda s: s.slot_number)
            top5_activities = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
            protected = set(protected_names) | top5_activities

            for cand_slot in friday_slots:
                if cand_slot.slot_number in window_slots:
                    continue
                if cand_slot == reflection_entry.time_slot:
                    continue

                occupant = next(
                    (
                        e for e in self.schedule.entries
                        if e.troop == troop and e.time_slot == cand_slot and e.activity.name != "Reflection"
                    ),
                    None,
                )

                if occupant and occupant.activity.name in protected:
                    continue
                if occupant:
                    self._remove_from_schedule(occupant)

                self._remove_from_schedule(reflection_entry)
                if self._add_to_schedule(cand_slot, reflection_entry.activity, troop):
                    return True
                return False

            return False

        for day in days:
            day_slots = sorted([s for s in self.time_slots if s.day == day], key=lambda s: s.slot_number)
            if len(day_slots) < slots_needed:
                continue

            for start_idx in range(0, len(day_slots) - slots_needed + 1):
                start_slot = day_slots[start_idx]
                window = day_slots[start_idx:start_idx + slots_needed]
                window_nums = {s.slot_number for s in window}

                troop_day_entries = [
                    e for e in self.schedule.entries
                    if e.troop == troop and e.time_slot.day == day and e.time_slot.slot_number in window_nums
                ]

                if any(e.activity.name in protected_names for e in troop_day_entries):
                    continue

                snapshot = self._snapshot_scheduler_state()
                displaced = []

                if day == Day.FRIDAY and activity.name == "Sailing":
                    if not _relocate_friday_reflection_for_window(window_nums):
                        self._restore_scheduler_state(snapshot)
                        continue

                for entry in sorted(troop_day_entries, key=lambda e: (e.time_slot.slot_number, e.activity.name)):
                    entry_rank = self._get_troop_activity_priority(troop, entry.activity.name)
                    displaced.append((entry.activity.name, entry_rank))
                    self._remove_from_schedule(entry)

                if not self._can_schedule(troop, activity, start_slot, day, relax_constraints=True):
                    self._restore_scheduler_state(snapshot)
                    continue
                if not self._add_to_schedule(start_slot, activity, troop):
                    self._restore_scheduler_state(snapshot)
                    continue

                # Recover displaced high-priority activities first.
                recover_ok = True
                displaced.sort(key=lambda x: x[1])
                for displaced_name, displaced_rank in displaced:
                    if displaced_rank > 4:
                        continue
                    displaced_activity = get_activity_by_name(displaced_name)
                    if not displaced_activity:
                        continue
                    if any(e.troop == troop and e.activity.name == displaced_name for e in self.schedule.entries):
                        continue

                    restored = False
                    for cand_slot in self._get_cluster_ordered_slots(troop, displaced_activity):
                        if self._can_schedule(troop, displaced_activity, cand_slot, cand_slot.day, relax_constraints=True) and self._add_to_schedule(cand_slot, displaced_activity, troop):
                            restored = True
                            break

                    if not restored:
                        restored = self._force_place_with_window_clearing(
                            troop=troop,
                            activity=displaced_activity,
                            required_rank=max(0, displaced_rank),
                            protected_names=protected_names,
                        )

                    if not restored:
                        restored = self._reclaim_activity_from_lower_priority_troop(
                            target_troop=troop,
                            activity=displaced_activity,
                            required_rank=max(0, displaced_rank),
                            protected_names=protected_names,
                        )

                    if not restored:
                        recover_ok = False
                        break

                if recover_ok:
                    return True

                self._restore_scheduler_state(snapshot)

        return False


    def _attempt_global_top5_repair_step(self) -> bool:
        """
        Try one global move that strictly reduces non-exempt Top 5 misses.
        Returns True if an improving move was found and kept.
        """
        current_count, misses = self._count_non_exempt_top5_misses()
        if current_count == 0:
            return False

        # Try hardest misses first (higher rank priority first).
        misses = sorted(misses, key=lambda m: m[2])

        for troop_name, activity_name, rank in misses:
            target_troop = next((t for t in self.troops if t.name == troop_name), None)
            activity = get_activity_by_name(activity_name)
            if not target_troop or not activity:
                continue

            holders = []
            for entry in self.schedule.entries:
                if entry.activity.name != activity_name:
                    continue
                if entry.troop.name == troop_name:
                    continue
                if not self._is_activity_instance_start(entry):
                    continue
                holder_rank = self._get_troop_activity_priority(entry.troop, activity_name)
                holders.append((entry, holder_rank))

            # Worst-ranked holders first (best reclaim candidates).
            holders.sort(key=lambda x: x[1], reverse=True)

            for holder_entry, holder_rank in holders:
                snapshot = self._snapshot_scheduler_state()
                start_slot = holder_entry.time_slot

                if not self._remove_from_schedule(holder_entry):
                    self._restore_scheduler_state(snapshot)
                    continue
                if not self._can_schedule(target_troop, activity, start_slot, start_slot.day, relax_constraints=True):
                    self._restore_scheduler_state(snapshot)
                    continue
                if not self._add_to_schedule(start_slot, activity, target_troop):
                    self._restore_scheduler_state(snapshot)
                    continue

                donor_troop = holder_entry.troop
                donor_still_has = any(
                    e.troop == donor_troop and e.activity.name == activity_name
                    for e in self.schedule.entries
                )
                if holder_rank <= 4 and not donor_still_has:
                    # Try to avoid trading one Top 5 miss for another.
                    recovered_donor = self._try_place_with_displacement_recovery(
                        troop=donor_troop,
                        activity=activity,
                        required_rank=holder_rank,
                        protected_names=self.NON_DISPLACEABLE_ACTIVITIES,
                    )
                    if not recovered_donor:
                        recovered_donor = self._force_place_with_window_clearing(
                            troop=donor_troop,
                            activity=activity,
                            required_rank=holder_rank,
                            protected_names=self.NON_DISPLACEABLE_ACTIVITIES,
                        )
                    if not recovered_donor:
                        self._reclaim_activity_from_lower_priority_troop(
                            target_troop=donor_troop,
                            activity=activity,
                            required_rank=holder_rank,
                            protected_names=self.NON_DISPLACEABLE_ACTIVITIES,
                        )

                # Keep schedule complete while evaluating the move impact.
                self._guarantee_no_gaps()
                new_count, _ = self._count_non_exempt_top5_misses()
                if new_count < current_count:
                    print(
                        f"  [Global Top5 Repair] {troop_name}:{activity_name}#${rank}".replace("#$", "#")
                        + f" improved {current_count}->{new_count} via reclaim from "
                        + f"{holder_entry.troop.name} (rank #{holder_rank + 1})"
                    )
                    return True

                self._restore_scheduler_state(snapshot)

        return False
