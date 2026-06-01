# CampScheduler Agent Guide

## Operating Posture

- `config/BRAIN.md` is the scheduling contract. Align code, tests, and reporting to it.
- `config/SKULL.json` is the configuration source for scheduler lists. Check it before adding hardcoded activities, areas, staff mappings, priorities, or special cases.
- Preserve the priority ladder: hard constraints -> non-exempt Top-5 success -> soft constraints and optimization.
- `non_exempt_top5_misses == 0` is mandatory. Never trade the Top-5 contract for a softer score improvement.
- Miss reporting must come from `schedule_json.unscheduled`; do not reconstruct authoritative misses from raw preference lists.
- Preserve mandatory anchors: Friday `Reflection`, weekly `Super Troop`, Tuesday-only `History Center` and `Disc Golf`, and no empty troop slots.

## Architecture

The scheduler runs through `core/scheduler/pipeline.py`:

```text
Phase A (Foundation) -> Phase B (Core) -> Phase C (Remaining) -> Phase D (Polish)
```

`core/constrained_scheduler.py` composes the scheduler from mixins. Most legacy-heavy behavior lives in `core/scheduler/legacy_parts/`; use `core/scheduler/legacy_parts/README.md` to choose the right split module before editing.

| Phase | Purpose |
| --- | --- |
| A | Mandatory anchors, rock activities, Sailing/Delta, beach protection, staff clustering, limited activities. |
| B | Top-1 through Top-5 guarantee, Delta/Sailing enforcement, Aqua Trampoline sharing. |
| C | Remaining preferences, staff optimization, Top-10 targets, fill all slots. |
| D | Strict final polish guarded by Top-5/Top-10 safety checks. |

## Entry Points

| Task | Start here |
| --- | --- |
| Top-5, swaps, preference enforcement | `core/scheduler/legacy_parts/top5_and_swaps.py` |
| Gap filling, stats, schedule reports | `core/scheduler/legacy_parts/gap_fill_and_stats.py` |
| Placement/state mutation | `core/scheduler/legacy_parts/placement_and_state.py` |
| Sequencing and placement constraints | `core/scheduler/legacy_parts/sequencing_and_constraints.py` |
| Preference ranges and limited activities | `core/scheduler/legacy_parts/preference_and_limited.py` |
| Clustering and optimization | `core/scheduler/legacy_parts/clustering_and_optimization.py` |
| Safe fallback/export helpers | `core/scheduler/legacy_parts/safety_and_export.py` |
| Pipeline phase order | `core/scheduler/pipeline.py` |
| Models and primitives | `core/models.py` |
| Regression scoring and baselines | `utils/regression_checker.py` |
| Product policy | `config/BRAIN.md` |
| Scheduler configuration | `config/SKULL.json` |

## Safety Rules

- Preserve root compatibility shims: `constrained_scheduler.py`, `models.py`, `activities.py`, and `io_handler.py`.
- Preserve `schedule_all()` phase order unless the task explicitly changes scheduling design.
- Prefer focused edits in split modules over expanding `core/constrained_scheduler.py` or `core/scheduler/pipeline.py`.
- Respect the Sailing slot-2 overlap exception exactly as documented in BRAIN.
- Treat `data/schedules/` as generated but workflow-critical fixtures, not disposable scratch output.
- Keep throwaway reports, debug logs, and generated exports out of the repo; `artifacts/` is ignored for local scratch output.

## Validation

- Focused unit checks: `pytest -q tests/unit`
- Schedule quality authority: `python utils/regression_checker.py`
- Official regression report: `python utils/regression_checker.py --fresh-eval --detailed --show-violations`
- Update comparison baseline only after intentional scheduler changes: `python utils/regression_checker.py --fresh-eval --set-baseline --force-baseline`

Baseline files:

| File | Role |
| --- | --- |
| `baseline_prime_10weeks.json` | Reference Prime, historical record, not the active comparison target. |
| `baseline_metrics_10weeks.json` | Comparison Baseline used for regression detection. |

## Quick Searches

- `rg "def _method_name\\(" core/scheduler/legacy_parts`
- `rg "subsection\\(" core/scheduler/pipeline.py`
- `rg "Top 5|Top5|mandatory" core/scheduler`
- `rg "unscheduled|non_exempt_top5_misses|fresh-eval" utils core`
