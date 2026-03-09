#!/usr/bin/env python3
"""
Commissioner-day strategy experiments.

Runs multiple scheduler strategies and compares:
- commissioner-day compliance
- area-level cluster gaps (1,-,3 pattern)
- excess cluster days
"""

from __future__ import annotations

import math
import os
import random
import sys
import io
from collections import defaultdict
from contextlib import contextmanager
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.activities import get_all_activities
from core.constrained_scheduler import ConstrainedScheduler
from core.io_handler import load_troops_from_json
from core.models import Day
from core.scheduler import config_loader
from core.scheduler.constants import SchedulerConstants
from core.scheduler.legacy_parts.gap_fill_and_stats import LegacyPart05Mixin


@dataclass
class WeekMetrics:
    week: str
    commissioner_compliance_pct: float
    commissioner_checks: int
    cluster_gaps: int
    excess_cluster_days: int


def _target_week_files(root: Path) -> list[Path]:
    troops_dir = root / "data" / "troops"
    files = sorted(troops_dir.glob("*_troops.json"))
    return [p for p in files if p.name.startswith("tc_week") or p.name.startswith("voyageur_week")]


def _cluster_area_map() -> dict[str, list[str]]:
    return {
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


def _compute_excess_cluster_days(schedule) -> int:
    ex = 0
    areas = _cluster_area_map()
    for area_acts in areas.values():
        entries = [e for e in schedule.entries if e.activity.name in area_acts]
        if not entries:
            continue
        days_used = len({e.time_slot.day for e in entries})
        required_days = math.ceil(len(entries) / 3.0)
        ex += max(0, days_used - required_days)
    return ex


def _compute_area_cluster_gaps(schedule) -> int:
    gaps = 0
    areas = _cluster_area_map()
    for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
        day_entries = [e for e in schedule.entries if e.time_slot.day == day]
        for area_acts in areas.values():
            has_1 = any(e.time_slot.slot_number == 1 and e.activity.name in area_acts for e in day_entries)
            has_3 = any(e.time_slot.slot_number == 3 and e.activity.name in area_acts for e in day_entries)
            has_2 = any(e.time_slot.slot_number == 2 and e.activity.name in area_acts for e in day_entries)
            if has_1 and has_3 and not has_2:
                gaps += 1
    return gaps


def _compute_commissioner_compliance(schedule, troops) -> tuple[float, int]:
    commissioner_by_troop = {}
    for comm, troop_names in SchedulerConstants.COMMISSIONER_TROOPS.items():
        for troop_name in troop_names:
            commissioner_by_troop[troop_name] = comm
    for troop in troops:
        if getattr(troop, "commissioner", None):
            commissioner_by_troop[troop.name] = troop.commissioner

    comm_day_maps = {
        "Delta": config_loader.get_commissioner_activity_days("Delta"),
        "Super Troop": config_loader.get_commissioner_activity_days("Super Troop"),
        "Troop Rifle": config_loader.get_commissioner_activity_days("Troop Rifle"),
        "Troop Shotgun": config_loader.get_commissioner_activity_days("Troop Rifle"),
        "Archery": config_loader.get_commissioner_activity_days("Archery"),
        "Sailing": config_loader.get_commissioner_activity_days("Sailing"),
        "Climbing Tower": config_loader.get_commissioner_activity_days("Climbing Tower"),
    }
    exclusive = config_loader.get_exclusive_areas()
    tower_ods_map = config_loader.get_commissioner_activity_days("Climbing Tower")
    tower_ods_acts = set(exclusive.get("Tower", []) + exclusive.get("Outdoor Skills", []))
    for act_name in tower_ods_acts:
        comm_day_maps.setdefault(act_name, tower_ods_map)

    checks = 0
    misses = 0
    for e in schedule.entries:
        comm = commissioner_by_troop.get(e.troop.name)
        if not comm:
            continue
        day_map = comm_day_maps.get(e.activity.name)
        if not day_map:
            continue
        expected_day = day_map.get(comm)
        if not expected_day:
            continue
        checks += 1
        if e.time_slot.day != expected_day:
            misses += 1

    compliance = 100.0 * (checks - misses) / max(1, checks)
    return compliance, checks


def _unique_days(days: list[Day]) -> list[Day]:
    seen = set()
    out = []
    for d in days:
        if d not in seen:
            out.append(d)
            seen.add(d)
    return out


def _day_order_key(d: Day) -> int:
    order = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
    return order.index(d)


def _likely_group_demand(self, commissioner: str, group_activities: set[str]) -> float:
    """
    Predict likely scheduled demand for a commissioner/group from preference ranks.

    Heuristic weights:
    - rank <= 5: high likelihood
    - rank <= 10: medium-high likelihood
    - rank <= 20: medium likelihood
    """
    likely = 0.0
    for t in self.troops:
        t_comm = self.troop_commissioner.get(t.name) or getattr(t, "commissioner", None)
        if t_comm != commissioner:
            continue
        for act in group_activities:
            rank = t.get_priority(act)
            if rank <= 5:
                likely += 1.0
            elif rank <= 10:
                likely += 0.75
            elif rank <= 20:
                likely += 0.35
    return likely


@contextmanager
def _patched_strategy(name: str):
    orig_mode = os.environ.get("COMM_CLUSTER_MODE")
    orig_reorder = LegacyPart05Mixin._reorder_days_with_commissioner_priority
    orig_get_day = LegacyPart05Mixin._get_activity_commissioner_day
    orig_tiers = LegacyPart05Mixin._get_commissioner_day_tiers

    def _reorder_fill_existing(self, candidate_days, troop, activity_name):
        candidates = _unique_days(list(candidate_days))
        day_counts = defaultdict(int)
        for e in self.schedule.entries:
            if e.troop == troop:
                day_counts[e.time_slot.day] += 1
        return sorted(candidates, key=lambda d: (-day_counts[d], _day_order_key(d)))

    def _reorder_identity(self, candidate_days, troop, activity_name):
        return _unique_days(list(candidate_days))

    def _half_threshold(self):
        return int(max(1, len(self.troops) * 14 * 0.5))

    def _top5_only(self, troop, activity_name):
        return troop.get_priority(activity_name) <= 5

    if name == "baseline_mixed":
        os.environ["COMM_CLUSTER_MODE"] = "mixed"
    elif name == "strict_commissioner":
        os.environ["COMM_CLUSTER_MODE"] = "strong"

        def _strict_tiers(self, troop, activity_name):
            assigned_day, fill_days, other_days = orig_tiers(self, troop, activity_name)
            return assigned_day, [], other_days

        LegacyPart05Mixin._get_commissioner_day_tiers = _strict_tiers
    elif name == "half_then_disregard":
        os.environ["COMM_CLUSTER_MODE"] = "strong"

        def _get_day_half(self, troop, activity_name):
            if len(self.schedule.entries) < _half_threshold(self):
                return orig_get_day(self, troop, activity_name)
            return None

        def _reorder_half(self, candidate_days, troop, activity_name):
            if len(self.schedule.entries) < _half_threshold(self):
                return orig_reorder(self, candidate_days, troop, activity_name)
            return _reorder_fill_existing(self, candidate_days, troop, activity_name)

        LegacyPart05Mixin._get_activity_commissioner_day = _get_day_half
        LegacyPart05Mixin._reorder_days_with_commissioner_priority = _reorder_half
    elif name == "disregard_commissioner":
        os.environ["COMM_CLUSTER_MODE"] = "strong"

        def _get_day_none(self, troop, activity_name):
            return None

        LegacyPart05Mixin._get_activity_commissioner_day = _get_day_none
        LegacyPart05Mixin._reorder_days_with_commissioner_priority = _reorder_identity
    elif name == "ownership_mode":
        os.environ["COMM_CLUSTER_MODE"] = "ownership"
    elif name == "thursday_open_day":
        os.environ["COMM_CLUSTER_MODE"] = "strong"

        def _get_day_thu_open(self, troop, activity_name):
            day = orig_get_day(self, troop, activity_name)
            if day == Day.THURSDAY:
                return None
            return day

        def _tiers_thu_open(self, troop, activity_name):
            assigned_day, fill_days, other_days = orig_tiers(self, troop, activity_name)
            if assigned_day == Day.THURSDAY:
                assigned_day = None
            fill = [Day.THURSDAY] + [d for d in fill_days if d != Day.THURSDAY]
            other = [d for d in other_days if d != Day.THURSDAY]
            return assigned_day, _unique_days(fill), _unique_days(other)

        LegacyPart05Mixin._get_activity_commissioner_day = _get_day_thu_open
        LegacyPart05Mixin._get_commissioner_day_tiers = _tiers_thu_open
    elif name == "demand_aware_commissioner":
        os.environ["COMM_CLUSTER_MODE"] = "strong"

        def _get_day_demand_aware(self, troop, activity_name):
            commissioner = self.troop_commissioner.get(troop.name) or getattr(troop, "commissioner", None)
            if not commissioner:
                return None
            _, group_activities = self._get_activity_commissioner_group(activity_name)
            if not group_activities:
                return None
            likely = _likely_group_demand(self, commissioner, set(group_activities))
            # Strongly anchor only when group demand is materially clusterable.
            if likely >= 2.3:
                return orig_get_day(self, troop, activity_name)
            return None

        def _reorder_demand_aware(self, candidate_days, troop, activity_name):
            commissioner = self.troop_commissioner.get(troop.name) or getattr(troop, "commissioner", None)
            _, group_activities = self._get_activity_commissioner_group(activity_name)
            if commissioner and group_activities:
                likely = _likely_group_demand(self, commissioner, set(group_activities))
                if likely >= 2.3:
                    return orig_reorder(self, candidate_days, troop, activity_name)
            return _reorder_fill_existing(self, candidate_days, troop, activity_name)

        LegacyPart05Mixin._get_activity_commissioner_day = _get_day_demand_aware
        LegacyPart05Mixin._reorder_days_with_commissioner_priority = _reorder_demand_aware
    elif name == "top5_cluster_then_fill":
        os.environ["COMM_CLUSTER_MODE"] = "strong"

        def _get_day_top5(self, troop, activity_name):
            if _top5_only(self, troop, activity_name):
                return orig_get_day(self, troop, activity_name)
            return None

        def _reorder_top5(self, candidate_days, troop, activity_name):
            if _top5_only(self, troop, activity_name):
                return orig_reorder(self, candidate_days, troop, activity_name)
            return _reorder_fill_existing(self, candidate_days, troop, activity_name)

        LegacyPart05Mixin._get_activity_commissioner_day = _get_day_top5
        LegacyPart05Mixin._reorder_days_with_commissioner_priority = _reorder_top5
    elif name == "adaptive_combo":
        os.environ["COMM_CLUSTER_MODE"] = "strong"

        def _get_day_combo(self, troop, activity_name):
            # Thursday is globally open in this strategy.
            if _top5_only(self, troop, activity_name):
                day = orig_get_day(self, troop, activity_name)
                return None if day == Day.THURSDAY else day

            commissioner = self.troop_commissioner.get(troop.name) or getattr(troop, "commissioner", None)
            _, group_activities = self._get_activity_commissioner_group(activity_name)
            if not commissioner or not group_activities:
                return None

            likely = _likely_group_demand(self, commissioner, set(group_activities))
            if likely >= 2.8 and len(self.schedule.entries) < _half_threshold(self):
                day = orig_get_day(self, troop, activity_name)
                return None if day == Day.THURSDAY else day
            return None

        def _reorder_combo(self, candidate_days, troop, activity_name):
            if _top5_only(self, troop, activity_name):
                return orig_reorder(self, candidate_days, troop, activity_name)
            return _reorder_fill_existing(self, candidate_days, troop, activity_name)

        LegacyPart05Mixin._get_activity_commissioner_day = _get_day_combo
        LegacyPart05Mixin._reorder_days_with_commissioner_priority = _reorder_combo
    else:
        raise ValueError(f"Unknown strategy: {name}")

    try:
        yield
    finally:
        # Restore monkey patches + env
        LegacyPart05Mixin._reorder_days_with_commissioner_priority = orig_reorder
        LegacyPart05Mixin._get_activity_commissioner_day = orig_get_day
        LegacyPart05Mixin._get_commissioner_day_tiers = orig_tiers
        if orig_mode is None:
            os.environ.pop("COMM_CLUSTER_MODE", None)
        else:
            os.environ["COMM_CLUSTER_MODE"] = orig_mode


def _run_strategy(root: Path, strategy: str) -> tuple[list[WeekMetrics], dict[str, float]]:
    week_files = _target_week_files(root)
    all_acts = get_all_activities()
    rows: list[WeekMetrics] = []
    with _patched_strategy(strategy):
        for idx, week_file in enumerate(week_files):
            random.seed(1000 + idx)
            troops = load_troops_from_json(str(week_file))
            scheduler = ConstrainedScheduler(troops, all_acts, voyageur_mode=week_file.name.startswith("voyageur"))
            try:
                with redirect_stdout(io.StringIO()):
                    schedule = scheduler.schedule_all()
            except Exception:
                # Strategy may be too strict and fail acceptance gates for some weeks.
                continue
            compliance, checks = _compute_commissioner_compliance(schedule, troops)
            rows.append(
                WeekMetrics(
                    week=week_file.stem,
                    commissioner_compliance_pct=compliance,
                    commissioner_checks=checks,
                    cluster_gaps=_compute_area_cluster_gaps(schedule),
                    excess_cluster_days=_compute_excess_cluster_days(schedule),
                )
            )

    if rows:
        summary = {
            "avg_commissioner_compliance": sum(r.commissioner_compliance_pct for r in rows) / len(rows),
            "avg_cluster_gaps": sum(r.cluster_gaps for r in rows) / len(rows),
            "avg_excess_cluster_days": sum(r.excess_cluster_days for r in rows) / len(rows),
            "evaluated_weeks": len(rows),
            "failed_weeks": len(week_files) - len(rows),
        }
    else:
        summary = {
            "avg_commissioner_compliance": float("nan"),
            "avg_cluster_gaps": float("nan"),
            "avg_excess_cluster_days": float("nan"),
            "evaluated_weeks": 0,
            "failed_weeks": len(week_files),
        }
    return rows, summary


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    strategies = [
        "baseline_mixed",
        "strict_commissioner",
        "half_then_disregard",
        "disregard_commissioner",
        "ownership_mode",
        "thursday_open_day",
        "demand_aware_commissioner",
        "top5_cluster_then_fill",
        "adaptive_combo",
    ]

    print("Commissioner-Day Strategy Experiments")
    print("=" * 80)
    results = {}
    for s in strategies:
        print(f"\nRunning: {s}")
        rows, summary = _run_strategy(root, s)
        results[s] = (rows, summary)
        print(
            f"  avg_comm%={summary['avg_commissioner_compliance']:.1f} | "
            f"avg_cluster_gaps={summary['avg_cluster_gaps']:.2f} | "
            f"avg_excess_cluster_days={summary['avg_excess_cluster_days']:.2f} | "
            f"weeks_ok={summary['evaluated_weeks']}/10"
        )

    print("\n" + "=" * 80)
    print("Summary Table")
    print("=" * 80)
    print(f"{'strategy':<24} | {'avg_comm%':<9} | {'avg_gap':<7} | {'avg_excess_days':<15} | {'weeks_ok':<8}")
    print("-" * 80)
    for s in strategies:
        _, sm = results[s]
        print(
            f"{s:<24} | {sm['avg_commissioner_compliance']:<9.1f} | "
            f"{sm['avg_cluster_gaps']:<7.2f} | {sm['avg_excess_cluster_days']:<15.2f} | "
            f"{sm['evaluated_weeks']}/10"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

