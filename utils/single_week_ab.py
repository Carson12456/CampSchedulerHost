"""Single-week A/B diagnostic for the adaptive cluster strategy.

Runs one week (default: tc_week8) twice — once with all adaptive strategies
forced OFF, once with them forced ON — and prints a side-by-side breakdown
of per-area placements, excess-day counts, and scores. Lets us reason about
WHY a specific week gained or lost points without being drowned in
whole-suite noise.

Usage:
    python utils/single_week_ab.py [week_name] [--trials N]

    week_name defaults to "tc_week8_troops".
    --trials N averages over N fresh runs per config (default 3) to smooth
    the known ~10pt run-to-run variance.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

# Fix encoding for Windows when stdout is redirected.
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.io_handler import load_troops_from_json, save_schedule_to_json  # noqa: E402
from core.activities import get_all_activities  # noqa: E402
from core.constrained_scheduler import ConstrainedScheduler  # noqa: E402
from core.services.unscheduled_source import build_unscheduled_data  # noqa: E402


STRATEGY_ENV_KEYS = [
    "CLUSTER_CONSOLIDATE_DELTA",
    "CLUSTER_CONSOLIDATE_SUPER_TROOP",
    "CLUSTER_CONSOLIDATE_TOWER",
    "CLUSTER_CONSOLIDATE_RIFLE",
    "CLUSTER_CONSOLIDATE_ODS",
]


# Cluster families we want to report on. Names here are activity names used
# in the schedule entries. Order matters for display.
AREAS = [
    ("Delta", ["Delta"]),
    ("Super Troop", ["Super Troop"]),
    ("Tower", ["Climbing Tower"]),
    (
        "Rifle",
        ["Troop Rifle", "Troop Shotgun"],
    ),
    (
        "ODS",
        [
            "Knots and Lashings",
            "Orienteering",
            "GPS & Geocaching",
            "Ultimate Survivor",
            "What's Cooking",
            "Chopped!",
        ],
    ),
    ("Sailing", ["Sailing"]),
]


def set_env(mode: str) -> None:
    """mode is either 'off' or 'auto'."""
    for key in STRATEGY_ENV_KEYS:
        os.environ[key] = mode


def run_once(week_name: str) -> dict:
    """Run the scheduler once for ``week_name`` and return per-area day counts
    plus the evaluator's metrics dict."""
    troop_file = Path("data/troops") / f"{week_name}.json"
    schedule_file = Path("data/schedules") / f"{week_name}_schedule.json"
    troops = load_troops_from_json(str(troop_file))
    activities = get_all_activities()
    voyageur = "voyageur" in week_name.lower()
    scheduler = ConstrainedScheduler(troops, activities, voyageur_mode=voyageur)
    schedule = scheduler.schedule_all()

    unscheduled_data = build_unscheduled_data(scheduler.troops, schedule)
    save_schedule_to_json(schedule, troops, str(schedule_file), unscheduled_data)

    # Per-area day counts read directly from the live schedule object.
    area_days: dict[str, Counter] = {name: Counter() for name, _ in AREAS}
    for entry in schedule.entries:
        for name, activities_list in AREAS:
            if entry.activity.name in activities_list:
                area_days[name][entry.time_slot.day] += 1
                break

    from utils.regression_checker import evaluate_week  # type: ignore

    metrics = evaluate_week(str(troop_file))
    return {
        "area_days": area_days,
        "score": metrics.get("final_score", 0),
        "core_goal_score": metrics.get("core_goal_score", 0),
        "excess_cluster_days": metrics.get("excess_cluster_days", 0),
        "staff_variance": metrics.get("staff_variance", 0),
        "constraint_violations": metrics.get("constraint_violations", 0),
        "top10_pct": metrics.get("top_10_pct", metrics.get("top10_percentage", 0)),
        "comm_pct": metrics.get("commissioner_day_compliance_pct", 0),
        "cluster_gaps": metrics.get("cluster_gaps", metrics.get("cluster_gap_count", 0)),
    }


def summarize(entry: dict) -> dict:  # noqa: D401 - simple passthrough
    return entry


def fmt_days(counter: Counter) -> str:
    if not counter:
        return "-"
    return ", ".join(
        f"{d.value[:3]}:{n}" for d, n in sorted(counter.items(), key=lambda x: x[0].value)
    )


def average(summaries: list[dict]) -> dict:
    agg = {
        "score": mean(s["score"] for s in summaries),
        "core_goal_score": mean(s["core_goal_score"] for s in summaries),
        "excess_cluster_days": mean(s["excess_cluster_days"] for s in summaries),
        "staff_variance": mean(s["staff_variance"] for s in summaries),
        "constraint_violations": mean(s["constraint_violations"] for s in summaries),
        "top10_pct": mean(s["top10_pct"] for s in summaries),
        "comm_pct": mean(s["comm_pct"] for s in summaries),
        "cluster_gaps": mean(s["cluster_gaps"] for s in summaries),
    }
    # Last summary's area distribution (representative, not averaged).
    agg["area_days"] = summaries[-1]["area_days"]
    return agg


def run_config(week_name: str, mode: str, trials: int) -> dict:
    set_env(mode)
    summaries = []
    for _ in range(trials):
        summaries.append(run_once(week_name))
    return average(summaries)


def print_report(week_name: str, baseline: dict, adaptive: dict) -> None:
    print("\n" + "=" * 78)
    print(f"  Single-week A/B: {week_name}")
    print("=" * 78)

    def row(label, b, a, fmt="{:.2f}"):
        delta = a - b
        sign = "+" if delta >= 0 else ""
        print(
            f"  {label:<26} legacy={fmt.format(b):>8}   "
            f"adaptive={fmt.format(a):>8}   "
            f"Δ={sign}{fmt.format(delta)}"
        )

    row("Overall Score", baseline["score"], adaptive["score"], "{:.1f}")
    row("Core Goal Score", baseline["core_goal_score"], adaptive["core_goal_score"], "{:.1f}")
    row("Excess Cluster Days", baseline["excess_cluster_days"], adaptive["excess_cluster_days"], "{:.2f}")
    row("Cluster Gaps", baseline["cluster_gaps"], adaptive["cluster_gaps"], "{:.2f}")
    row("Staff Variance", baseline["staff_variance"], adaptive["staff_variance"], "{:.2f}")
    row("Constraint Violations", baseline["constraint_violations"], adaptive["constraint_violations"], "{:.2f}")
    row("Commissioner Day %", baseline["comm_pct"], adaptive["comm_pct"], "{:.1f}")
    row("Top10 %", baseline["top10_pct"], adaptive["top10_pct"], "{:.1f}")

    print("\n  Per-area day distribution (last trial):")
    print(f"  {'Area':<14} {'Legacy':<42} {'Adaptive':<42}")
    print(f"  {'-'*14} {'-'*42} {'-'*42}")
    for name, _ in AREAS:
        b_days = fmt_days(baseline["area_days"].get(name, Counter()))
        a_days = fmt_days(adaptive["area_days"].get(name, Counter()))
        print(f"  {name:<14} {b_days:<42} {a_days:<42}")

    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("week_name", nargs="?", default="tc_week8_troops")
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()

    print(f"Running {args.trials} trial(s) per config for {args.week_name}...")
    print("  [legacy] all adaptive strategies OFF")
    baseline = run_config(args.week_name, "off", args.trials)
    print("  [adaptive] all adaptive strategies AUTO")
    adaptive = run_config(args.week_name, "auto", args.trials)
    print_report(args.week_name, baseline, adaptive)


if __name__ == "__main__":
    main()
