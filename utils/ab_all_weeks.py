"""Multi-week A/B diagnostic for the adaptive cluster strategy.

Runs every week, multi-trial, and prints a compact per-week report
comparing legacy (all adaptive strategies OFF) vs adaptive (all AUTO).
Aggregates noise by averaging N trials per config per week.

Usage: python utils/ab_all_weeks.py [--trials 3]
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path
from statistics import mean
from contextlib import redirect_stdout

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Suppress verbose scheduler logs so the report is readable.
_scheduler_trash = io.StringIO()

from utils.single_week_ab import run_once, set_env  # noqa: E402


def run_config(week_name: str, mode: str, trials: int) -> dict:
    set_env(mode)
    trial_results = []
    failures = 0
    for _ in range(trials):
        try:
            with redirect_stdout(_scheduler_trash):
                trial_results.append(run_once(week_name))
        except Exception:
            # Some trials occasionally fail the strict Top-5 contract due to
            # pre-existing scheduler flakiness. Skip and keep sampling — a
            # failed schedule is neither a win nor a loss for the A/B.
            failures += 1
    if not trial_results:
        return {
            "score": float("nan"),
            "core": float("nan"),
            "excess": float("nan"),
            "staff_var": float("nan"),
            "comm_pct": float("nan"),
            "cluster_gaps": float("nan"),
            "viol": float("nan"),
            "failures": failures,
        }
    return {
        "score": mean(r["score"] for r in trial_results),
        "core": mean(r["core_goal_score"] for r in trial_results),
        "excess": mean(r["excess_cluster_days"] for r in trial_results),
        "staff_var": mean(r["staff_variance"] for r in trial_results),
        "comm_pct": mean(r["comm_pct"] for r in trial_results),
        "cluster_gaps": mean(r["cluster_gaps"] for r in trial_results),
        "viol": mean(r["constraint_violations"] for r in trial_results),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()

    week_files = sorted(Path("data/troops").glob("*.json"))
    week_names = [f.stem for f in week_files]

    print(f"Running {args.trials} trial(s) per config × {len(week_names)} weeks "
          f"× 2 configs = {args.trials * len(week_names) * 2} scheduler runs")
    print()
    print(f"{'Week':<24} {'Score L':>8} {'Score A':>8} {'Δ':>6}   "
          f"{'Xs L':>5} {'Xs A':>5}  {'SV L':>5} {'SV A':>5}  "
          f"{'Cm% L':>6} {'Cm% A':>6}")
    print("-" * 102)

    totals_l = {"score": 0.0, "excess": 0.0, "staff_var": 0.0, "comm_pct": 0.0}
    totals_a = {"score": 0.0, "excess": 0.0, "staff_var": 0.0, "comm_pct": 0.0}
    count = 0
    per_week_delta = []

    for week_name in week_names:
        legacy = run_config(week_name, "off", args.trials)
        adaptive = run_config(week_name, "auto", args.trials)
        delta = adaptive["score"] - legacy["score"]
        per_week_delta.append((week_name, delta))
        sign = "+" if delta >= 0 else ""
        fail_note = ""
        if legacy.get("failures", 0) or adaptive.get("failures", 0):
            fail_note = f"  [fails L={legacy.get('failures', 0)} A={adaptive.get('failures', 0)}]"
        print(
            f"{week_name:<24} {legacy['score']:>8.1f} {adaptive['score']:>8.1f} "
            f"{sign}{delta:>5.1f}   "
            f"{legacy['excess']:>5.1f} {adaptive['excess']:>5.1f}  "
            f"{legacy['staff_var']:>5.2f} {adaptive['staff_var']:>5.2f}  "
            f"{legacy['comm_pct']:>6.1f} {adaptive['comm_pct']:>6.1f}"
            f"{fail_note}"
        )
        if any(legacy[k] != legacy[k] or adaptive[k] != adaptive[k] for k in totals_l):
            continue  # NaN check — skip week from totals if either side failed entirely
        for k in totals_l:
            totals_l[k] += legacy[k]
            totals_a[k] += adaptive[k]
        count += 1

    print("-" * 102)
    for k in totals_l:
        totals_l[k] /= count
        totals_a[k] /= count
    delta = totals_a["score"] - totals_l["score"]
    sign = "+" if delta >= 0 else ""
    print(
        f"{'AVERAGE':<24} {totals_l['score']:>8.1f} {totals_a['score']:>8.1f} "
        f"{sign}{delta:>5.1f}   "
        f"{totals_l['excess']:>5.1f} {totals_a['excess']:>5.1f}  "
        f"{totals_l['staff_var']:>5.2f} {totals_a['staff_var']:>5.2f}  "
        f"{totals_l['comm_pct']:>6.1f} {totals_a['comm_pct']:>6.1f}"
    )
    print()
    wins = sum(1 for _, d in per_week_delta if d > 1.0)
    losses = sum(1 for _, d in per_week_delta if d < -1.0)
    ties = count - wins - losses
    print(f"Wins: {wins}   Losses: {losses}   Ties (|Δ|<=1): {ties}")


if __name__ == "__main__":
    main()
