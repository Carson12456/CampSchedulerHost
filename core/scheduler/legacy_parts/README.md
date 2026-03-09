# Legacy Parts Map

This package contains the split method body for `ConstrainedScheduler`.

Use this map to jump quickly:

- `placement_and_state.py`: schedule mutation helpers, snapshots, low-level placement utilities.
- `top5_and_swaps.py`: Top-5 recovery and swap-heavy preference enforcement.
- `preference_and_limited.py`: preference range scheduling and limited-activity placement.
- `sequencing_and_constraints.py`: sequencing rules and constraint-aware placement checks.
- `gap_fill_and_stats.py`: gap elimination, score/stats helpers, and reporting helpers.
- `clustering_and_optimization.py`: clustering passes and optimization routines.
- `safety_and_export.py`: safe-fallback flows and export/integration helpers.
- `compatibility_bridges.py`: legacy compatibility wrappers and analytics convenience methods.

Constrained composition happens in `core/constrained_scheduler.py`.
