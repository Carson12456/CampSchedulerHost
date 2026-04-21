"""Run the all-weeks A/B under several configurations and compare averages.

This lets us isolate which family (Delta, Super Troop, Tower, Rifle, ODS)
is helping vs hurting without running each one by hand.
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from statistics import mean

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.single_week_ab import run_once  # noqa: E402


TRIALS = 2  # keep runtime reasonable; noise is small

CONFIGS = {
    "all_off":     dict(DELTA="off",  SUPER_TROOP="off",  TOWER="off",  RIFLE="off",  ODS="off"),
    "all_on":      dict(DELTA="auto", SUPER_TROOP="auto", TOWER="auto", RIFLE="auto", ODS="auto"),
    "delta_only":  dict(DELTA="auto", SUPER_TROOP="off",  TOWER="off",  RIFLE="off",  ODS="off"),
    "no_super":    dict(DELTA="auto", SUPER_TROOP="off",  TOWER="auto", RIFLE="auto", ODS="auto"),
    "super_only":  dict(DELTA="off",  SUPER_TROOP="auto", TOWER="off",  RIFLE="off",  ODS="off"),
    "staff_only":  dict(DELTA="off",  SUPER_TROOP="off",  TOWER="auto", RIFLE="auto", ODS="auto"),
}


def apply_env(cfg: dict) -> None:
    for key, val in cfg.items():
        os.environ[f"CLUSTER_CONSOLIDATE_{key}"] = val


def run_all_weeks(cfg: dict) -> dict:
    apply_env(cfg)
    totals = []
    trash = io.StringIO()
    for tf in sorted(Path("data/troops").glob("*.json")):
        week_name = tf.stem
        scores = []
        for _ in range(TRIALS):
            try:
                with redirect_stdout(trash):
                    scores.append(run_once(week_name)["score"])
            except Exception:
                pass
        if scores:
            totals.append(mean(scores))
    if not totals:
        return {"avg_score": float("nan")}
    return {"avg_score": mean(totals), "n_weeks": len(totals)}


def main() -> None:
    print(f"Running each config across 10 weeks × {TRIALS} trials = "
          f"{len(CONFIGS) * 10 * TRIALS} scheduler runs")
    print()
    print(f"{'Config':<14} {'Avg Score':>10}   {'Δ vs all_off':>14}")
    print("-" * 44)
    baseline = None
    for name, cfg in CONFIGS.items():
        result = run_all_weeks(cfg)
        avg = result["avg_score"]
        if baseline is None:
            baseline = avg
            delta_str = " (baseline)"
        else:
            delta = avg - baseline
            sign = "+" if delta >= 0 else ""
            delta_str = f"  {sign}{delta:.2f}"
        print(f"{name:<14} {avg:>10.2f}{delta_str:>14}")


if __name__ == "__main__":
    main()
