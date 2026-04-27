# Scheduler Structure

`config/BRAIN.md` is the source of truth for scheduling behavior. The folder structure should keep scheduler policy, implementation, fixtures, generated artifacts, and compatibility imports easy to distinguish.

## Current Contracts

- Keep root compatibility shims: `constrained_scheduler.py`, `models.py`, `activities.py`, and `io_handler.py`.
- Keep scheduler implementation under `core/` unless a larger package migration also updates imports and tests.
- Keep policy and scheduler configuration in `config/`, especially `BRAIN.md` and `SKULL.json`.
- Keep troop inputs in `data/troops/`.
- Treat `data/schedules/` as generated but workflow-critical schedule fixtures, not disposable scratch output.
- Keep regression baselines at the repository root until `utils/regression_checker.py` is updated to load them elsewhere.

## Target Layout

```text
CampSchedulerHost/
  core/
    constrained_scheduler.py
    scheduler/
      pipeline.py
      phase_a_foundation.py
      phase_b_core.py
      phase_d_cleanup.py
      legacy_parts/
    services/
  config/
    BRAIN.md
    SKULL.json
  data/
    troops/
    schedules/
  docs/
    scheduler_structure.md
  artifacts/
    logs/
    reports/
    schedules/
  utils/
    regression_checker.py
    regenerate_all_schedules.py
    check_brain_skull_consistency.py
  tests/
  web/
  constrained_scheduler.py
  models.py
  activities.py
  io_handler.py
```

## Cleanup Policy

Generated scheduler exports, debug reports, stale regression reports, local logs, Python caches, and agent worktrees should not be committed. Put future ad-hoc outputs under `artifacts/` and keep official regression data in the existing baseline files unless the regression checker is migrated deliberately.

Old A/B tuning scripts were removed because they were temporary revision tools and are no longer part of the scheduler workflow.
