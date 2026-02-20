#!/usr/bin/env python3
"""
Trace where hard violations first appear by scheduler phase.
"""

from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.activities import get_all_activities
from core.constrained_scheduler import ConstrainedScheduler
from core.io_handler import load_troops_from_json
from core.models import Day, TimeSlot, generate_time_slots
from core.scheduler import config_loader


SLOTS_PER_DAY = {
    Day.MONDAY: 3,
    Day.TUESDAY: 3,
    Day.WEDNESDAY: 3,
    Day.THURSDAY: 2,
    Day.FRIDAY: 3,
}


def hard_violations(scheduler: ConstrainedScheduler, include_slot_completeness: bool = False) -> list[str]:
    schedule = scheduler.schedule
    troops = scheduler.troops
    details: list[str] = []

    # Optional: slot completeness checks are noisy before fill phases.
    if include_slot_completeness:
        all_slots = list(generate_time_slots())
        for troop in troops:
            for day in Day:
                for slot_num in range(1, SLOTS_PER_DAY[day] + 1):
                    slot = next((s for s in all_slots if s.day == day and s.slot_number == slot_num), None)
                    if slot and schedule.is_troop_free(slot, troop):
                        details.append(f"GAP: {troop.name} {day.value} Slot {slot_num}")

        for troop in troops:
            has_ref = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in schedule.entries
                if e.troop == troop
            )
            if not has_ref:
                details.append(f"MISSING_REFLECTION: {troop.name}")

    # 3) Delta adjacent Tower/ODS
    exclusive = config_loader.get_exclusive_areas()
    tower_ods = set(exclusive.get("Tower", [])) | set(exclusive.get("Outdoor Skills", []))
    for troop in troops:
        by_day_slot: dict[Day, dict[int, str]] = defaultdict(dict)
        for e in schedule.entries:
            if e.troop == troop:
                by_day_slot[e.time_slot.day][e.time_slot.slot_number] = e.activity.name
        for day, slot_acts in by_day_slot.items():
            delta_slots = [s for s, a in slot_acts.items() if a == "Delta"]
            tower_slots = [s for s, a in slot_acts.items() if a in tower_ods]
            for ds in delta_slots:
                for ts in tower_slots:
                    if abs(ds - ts) <= 1:
                        details.append(f"DELTA_ADJ_TOWER_ODS: {troop.name} {day.value}")
                        break
                else:
                    continue
                break

    # 4) Exclusive double-book
    exclusive_one_troop = {
        "Climbing Tower",
        "Troop Rifle",
        "Troop Shotgun",
        "Archery",
        "Delta",
        "Super Troop",
        "Sailing",
        "Gaga Ball",
        "9 Square",
    }
    slot_activity_count = defaultdict(lambda: defaultdict(int))
    for e in schedule.entries:
        key = (e.time_slot.day, e.time_slot.slot_number)
        slot_activity_count[key][e.activity.name] += 1
    for (day, slot_num), counts in slot_activity_count.items():
        for act_name, count in counts.items():
            if act_name in exclusive_one_troop and count >= 2:
                details.append(f"EXCLUSIVE_DOUBLE_BOOK: {act_name} {day.value} Slot {slot_num} ({count})")

    # 5) Beach hard caps
    beach_staff_max = config_loader.get_constraints().get("beach_staff_per_slot", 12)
    beach_acts_max = config_loader.get_constraints().get("max_beach_staffed_activities", 4)
    beach_staffed = set(
        a
        for a in config_loader.get_activities_with_tag("beach")
        if config_loader.get_staff_need(a) > 0
    )
    slot_beach_staff = defaultdict(int)
    slot_beach_acts = defaultdict(int)
    for e in schedule.entries:
        if e.activity.name in beach_staffed:
            key = (e.time_slot.day, e.time_slot.slot_number)
            slot_beach_staff[key] += config_loader.get_staff_need(e.activity.name)
            slot_beach_acts[key] += 1
    for (day, slot), count in slot_beach_staff.items():
        if count > beach_staff_max:
            details.append(f"BEACH_STAFF_OVERLOAD: {day.value} Slot {slot} ({count}>{beach_staff_max})")
    for (day, slot), count in slot_beach_acts.items():
        if count > beach_acts_max:
            details.append(f"BEACH_ACTIVITY_SATURATION: {day.value} Slot {slot} ({count}>{beach_acts_max})")

    return sorted(set(details))


def run_week(week_file: Path) -> None:
    print(f"\n=== {week_file.stem} ===")
    troops = load_troops_from_json(str(week_file))
    scheduler = ConstrainedScheduler(troops, get_all_activities())

    phases = [
        ("A.0", "_schedule_friday_reflection"),
        ("A.0b", "_schedule_super_troop"),
        ("A.3", "_schedule_hc_dg_tuesday"),
        ("A.5", "_schedule_sailing_optimize_all"),
        ("A.5b", "_schedule_early_aqua_trampoline_top5"),
        ("A.5c", "_guarantee_top1_beach"),
        ("A.1", "_schedule_three_hour_activities"),
        ("A.7", "_schedule_delta_sailing_pairs"),
        ("A.2", "_schedule_two_hour_activities_priority"),
        ("A.4", "_early_staff_area_clustering"),
        ("A.6", "_schedule_limited_activities_by_priority"),
        ("A.8", "_schedule_sailing_pairs"),
        ("B.1a", "_schedule_preferences_range", (0, 1)),
        ("B.1b", "_force_top1_preferences"),
        ("B.1c", "_schedule_preferences_range", (1, 5)),
        ("B.2", "_guarantee_all_top5"),
        ("B.3", "_enforce_mandatory_top5"),
        ("B.6", "_schedule_delta_early"),
        ("B.7", "_build_commissioner_busy_map"),
        ("B.8", "_schedule_early_sailing_top10"),
        ("B.9", "_enforce_delta_sailing_pairing"),
        ("B.10", "_consolidate_sailing_same_day"),
        ("B.11", "_aggressive_aqua_trampoline_sharing"),
        ("C.1", "_schedule_day_requests"),
        ("C.2", "_schedule_staff_optimized_areas"),
        ("C.4", "_schedule_preferences_range", (5, 20)),
        ("C.4.5", "_guarantee_minimum_top10"),
        ("C.5", "_guarantee_top10_with_exceptions"),
        ("C.6", "_fill_all_remaining"),
        ("C.6b", "_schedule_sailing_balls_fills"),
        ("C.7", "_aggressive_aqua_trampoline_sharing"),
        ("D.1", "_optimize_friday_reflections"),
        ("D.2", "_comprehensive_clustering_optimization"),
        ("D.3", "_force_clustering_consolidation"),
        ("D.4", "_optimize_friday_super_troop"),
        ("D.5", "_optimize_flexible_reflections"),
        ("D.6", "_optimize_commissioner_balance"),
        ("D.7a", "_optimize_setup_efficiency"),
        ("D.7b", "_optimize_activity_clustering"),
        ("D.8a", "_optimize_outlier_activities"),
        ("D.8b", "_optimize_commissioner_day_ownership"),
        ("D.9a", "_optimize_cluster_gaps_post_fill"),
        ("D.9b", "_recover_top10_from_fills"),
        ("D.9c", "_comprehensive_final_cleanup"),
        ("FINAL.1", "_fix_multislot_integrity"),
        ("FINAL.2", "_final_comprehensive_validation"),
        ("FINAL.3", "_sanitize_exclusivity"),
    ]

    previous: set[str] = set()
    first_seen: dict[str, str] = {}
    for item in phases:
        phase = item[0]
        method_name = item[1]
        args = item[2] if len(item) > 2 else ()
        method = getattr(scheduler, method_name)
        method(*args)

        current = set(hard_violations(scheduler, include_slot_completeness=False))
        new = sorted(current - previous)
        for v in new:
            first_seen[v] = phase
        previous = current

    if not first_seen:
        print("No hard violations introduced.")
    else:
        print("First-introduced hard violations:")
        for violation, phase in sorted(first_seen.items()):
            print(f"  - {phase}: {violation}")

    final_hard = hard_violations(scheduler, include_slot_completeness=False)
    if final_hard:
        print("Final hard violations still present:")
        for violation in final_hard:
            print(f"  - {violation}")
    else:
        print("Final hard violations: none")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    targets = [
        root / "data" / "troops" / "tc_week6_troops.json",
        root / "data" / "troops" / "tc_week7_troops.json",
        root / "data" / "troops" / "voyageur_week3_troops.json",
    ]
    for week in targets:
        run_week(week)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
