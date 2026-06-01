# WP0 — Baseline (captured 2026-05-29)

## Tests
- `pytest -q tests/unit`: **56 passed** (4.29s), exit 0.

## Regression: `regression_checker.py --fresh-eval --detailed --show-violations`
- **NO REGRESSIONS DETECTED** vs comparison baseline.
- Top 5 Success Rate: **100.0%** (0 total misses — hard contract held on all weeks).
- Average Week Score: **793.7**
- Average Constraint Violations: 1.9 | Avg Beach Slot Violations: 1.0 | Avg Staff Variance: 3.21

### Per-week table
| Week | Score | Top5% | Top10% | Viol | StVar | Clust | Gap | Comm% |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tc_week1 | 886 | 100 | 93.3 | 0 | 1.35 | 2 | 0 | 36.1 |
| tc_week2 | 941 | 100 | 100.0 | 0 | 0.98 | 1 | 0 | 64.3 |
| tc_week3 | 772 | 100 | 92.0 | 3 | 2.54 | 3 | 0 | 37.0 |
| tc_week4 | 751 | 100 | 93.6 | 6 | 2.94 | 3 | 0 | 41.3 |
| tc_week5 | 724 | 100 | 86.4 | 3 | 1.94 | 5 | 0 | 33.9 |
| tc_week6 | 728 | 100 | 92.0 | 2 | 3.64 | 6 | 0 | 41.1 |
| tc_week7 | 717 | 100 | 91.8 | 2 | 7.68 | 5 | 1 | 32.1 |
| tc_week8 | 843 | 100 | 92.5 | 0 | 2.94 | 4 | 0 | 51.9 |
| voyageur_week1 | 787 | 100 | 91.8 | 0 | 4.24 | 4 | 1 | 0.0 |
| voyageur_week3 | 788 | 100 | 91.2 | 3 | 3.88 | 3 | 0 | 0.0 |

## Observations to feed later WPs
- **Lowest scorers:** week7 (717), week5 (724), week6 (728), week4 (751) — clustering (Clust 4-6) and staff variance (week7 StVar 7.68) are the main drags. → WP6/WP7/WP8.
- **Recurring soft violations:**
  - Water Games same-day pairs (AT/Water Polo/Greased Watermelon) appear repeatedly (weeks 3,4,5,6). → WP6 (scored?) + scheduler avoidance (WP7).
  - "Shower House before wet activity / Super Troop" (weeks 5,6,7,voy3) — BRAIN §4 lists this as a HARD rule (strict mode) yet it appears as a soft violation. **Potential hard/soft mismatch** → prioritize in WP2/WP6.
  - AT in Slot 2 (small troop), multiple canoe, multiple accuracy same day.
- **Commissioner% = 0.0 for both Voyageur weeks** — verify expected (no commissioner grouping for Voyageur) vs a bug. → WP1/WP7.
- No cluster gaps except week7 & voyageur_week1 (1 each); excess cluster days are the bigger efficiency loss.
