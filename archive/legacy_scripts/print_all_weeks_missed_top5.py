#!/usr/bin/env python3
"""
Print every week's missed Top 5 preferences flawlessly.

- Discovers weeks the same way as evaluate_week_success.py (tc_week*.json, voyageur_week*.json).
- Uses the same schedule path: schedules/{week_basename}_schedule.json.
- Applies the same exemption rules as the evaluator:
  - 3-hour 2nd+: Tamarac Wildlife Refuge, Itasca State Park, Back of the Moon (if troop already has one 3-hour, missing 2nd+ does not count).
  - HC/DG Tuesday full: History Center, Disc Golf (if all 3 Tuesday slots are HC or DG, missing HC/DG does not count).

Output: Per-week list of every missed Top 5 (troop, activity, rank, EXEMPT or not), then season summary.
"""

import json
import os
import sys
from pathlib import Path

# Must match evaluate_week_success.py exactly
THREE_HOUR_ACTIVITIES = {"Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}
HC_DG_ACTIVITIES = {"History Center", "Disc Golf"}
BEACH_ACTIVITIES = {
    "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim",
    "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
    "Nature Canoe", "Float for Floats", "Sailing"
}


def get_week_files():
    """Discover week troop files: same as evaluate_week_success (cwd glob)."""
    cwd = Path(os.getcwd())
    week_files = sorted(cwd.glob("tc_week*.json")) + sorted(cwd.glob("voyageur_week*.json"))
    # Prefer cwd; if empty, try troops/ subdir
    if not week_files and (cwd / "troops").is_dir():
        troops_dir = cwd / "troops"
        week_files = sorted(troops_dir.glob("tc_week*_troops.json")) + sorted(troops_dir.glob("voyageur_week*_troops.json"))
    return week_files


def load_troops_list(week_path):
    """Load list of troop dicts (name, preferences, scouts, adults) from week JSON."""
    path = Path(week_path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    troops = data.get("troops", [])
    return troops


def load_schedule_entries(schedule_path):
    """Load schedule JSON and return list of entry dicts (troop_name, activity_name, day, slot)."""
    path = Path(schedule_path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("entries", [])


def compute_tuesday_hc_dg_full(entries):
    """True if all 3 Tuesday slots are filled with History Center or Disc Golf."""
    tuesday_slots = set()
    for e in entries:
        if e.get("day") == "TUESDAY" and e.get("activity_name") in HC_DG_ACTIVITIES:
            tuesday_slots.add(e.get("slot"))
    return tuesday_slots >= {1, 2, 3}


def get_misses_for_week(week_label, troops_list, entries):
    """
    Compute missed Top 5 for one week. Exemption logic matches evaluate_week_success.py.
    Returns: list of dicts with keys: troop, activity, rank, is_exempt.
    """
    if not troops_list or entries is None:
        return [], 0, 0

    troop_scheduled = {}
    for e in entries:
        name = e.get("troop_name")
        act = e.get("activity_name")
        if name and act:
            troop_scheduled.setdefault(name, set()).add(act)

    hc_dg_tuesday_full = compute_tuesday_hc_dg_full(entries)

    misses = []
    total_top5_slots = 0
    missed_counted = 0  # misses that count toward score (non-exempt)

    for t in troops_list:
        troop_name = t.get("name", "")
        prefs = t.get("preferences", [])[:5]
        total_top5_slots += len(prefs)
        scheduled = troop_scheduled.get(troop_name, set())
        has_3hr = bool(scheduled & THREE_HOUR_ACTIVITIES)

        for i, pref in enumerate(prefs):
            if pref in scheduled:
                continue
            rank = i + 1
            is_exempt = False
            if pref in THREE_HOUR_ACTIVITIES and has_3hr:
                is_exempt = True
            elif pref in HC_DG_ACTIVITIES and hc_dg_tuesday_full:
                is_exempt = True

            misses.append({
                "troop": troop_name,
                "activity": pref,
                "rank": rank,
                "is_exempt": is_exempt,
            })
            if not is_exempt:
                missed_counted += 1

    return misses, total_top5_slots, missed_counted


def main():
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)

    week_files = get_week_files()
    if not week_files:
        print("No week files found (tc_week*.json, voyageur_week*.json in cwd or troops/).")
        sys.exit(1)

    schedules_dir = Path("schedules")
    all_misses_by_week = []
    season_total_top5 = 0
    season_missed_counted = 0
    season_missed_exempt = 0

    print("=" * 72)
    print("ALL WEEKS - MISSED TOP 5 (flawless report)")
    print("=" * 72)

    for week_path in week_files:
        week_basename = week_path.stem  # e.g. tc_week1_troops
        week_label = week_basename.replace("_troops", "").replace("_", " ").strip()
        schedule_path = schedules_dir / f"{week_basename}_schedule.json"

        troops_list = load_troops_list(week_path)
        if not troops_list:
            print(f"\n--- {week_label} ---")
            print("  [SKIP] No troops file or empty troops.")
            continue

        entries = load_schedule_entries(schedule_path)
        if entries is None:
            print(f"\n--- {week_label} ---")
            print("  [SKIP] No schedule file.")
            misses = []
            total_top5_slots = sum(len(t.get("preferences", [])[:5]) for t in troops_list)
            missed_counted = total_top5_slots  # all count as missed if no schedule
            missed_exempt = 0
        else:
            misses, total_top5_slots, missed_counted = get_misses_for_week(week_label, troops_list, entries)
            missed_exempt = sum(1 for m in misses if m["is_exempt"])

        season_total_top5 += total_top5_slots
        season_missed_counted += missed_counted
        season_missed_exempt += missed_exempt

        # Top-1 beach misses (diagnostic)
        top1_beach_misses = []
        if entries is not None:
            troop_scheduled = {}
            for e in entries:
                name = e.get("troop_name")
                act = e.get("activity_name")
                if name and act:
                    troop_scheduled.setdefault(name, set()).add(act)
            for t in troops_list:
                prefs = t.get("preferences", [])
                if not prefs:
                    continue
                top1 = prefs[0]
                if top1 in BEACH_ACTIVITIES:
                    scheduled = troop_scheduled.get(t.get("name", ""), set())
                    if top1 not in scheduled:
                        top1_beach_misses.append((t.get("name", ""), top1))

        print(f"\n--- {week_label} ---")
        if not misses:
            print("  (none)")
        else:
            for m in misses:
                exempt_tag = "  [EXEMPT]" if m["is_exempt"] else ""
                print(f"  {m['troop']}: {m['activity']} (Top #{m['rank']}){exempt_tag}")

        if top1_beach_misses:
            print(f"  Top 1 beach missed: {len(top1_beach_misses)}")
            for troop_name, act in top1_beach_misses:
                print(f"    - {troop_name}: {act}")

        total_misses = len(misses)
        top5_pct = 100.0 * (total_top5_slots - missed_counted) / max(1, total_top5_slots)
        print(f"  Missed: {total_misses} total ({missed_counted} counted, {missed_exempt} exempt)  |  Top 5 success: {top5_pct:.1f}%")
        all_misses_by_week.append((week_label, misses, missed_counted, total_top5_slots))

    # Season summary
    print("\n" + "=" * 72)
    print("SEASON SUMMARY")
    print("=" * 72)
    top5_success_pct = 100.0 * (season_total_top5 - season_missed_counted) / max(1, season_total_top5)
    print(f"  Total Top 5 slots (all troops, all weeks): {season_total_top5}")
    print(f"  Missed (counted toward score):            {season_missed_counted}")
    print(f"  Missed (exempt):                           {season_missed_exempt}")
    print(f"  Top 5 success (counted):                  {top5_success_pct:.1f}%")
    print()

    # Per-week summary table
    print("Per-week Top 5 missed (counted):")
    for week_label, misses, counted, total in all_misses_by_week:
        pct = 100.0 * (total - counted) / max(1, total)
        print(f"  {week_label}: {counted} missed, {pct:.1f}% success")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
