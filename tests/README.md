# CampScheduler Tests

The unit tests cover focused contracts around models, constraints, scheduler behavior, and regression scoring. Full schedule-quality evaluation belongs to `utils/regression_checker.py`.

## Test Files

- `tests/unit/test_core_entities.py`: model and schedule primitive behavior.
- `tests/unit/test_constraint_system.py`: low-level scheduling constraints and capacity rules.
- `tests/unit/test_scheduling_algorithm.py`: focused scheduler behavior checks that are useful below the full regression workflow.
- `tests/unit/test_scoring_contract.py`: unit-level locks for `utils/regression_checker.py` scoring helpers and bounded point components.

## Validation Commands

Run focused unit tests:

```bash
pytest -q tests/unit
```

Run the scheduler quality comparison:

```bash
python utils/regression_checker.py
```

Run the official fresh-cycle report when reporting regression status:

```bash
python utils/regression_checker.py --fresh-eval --detailed --show-violations
```

## Policy

- `config/BRAIN.md` defines the scheduling contract.
- `utils/regression_checker.py` is the authoritative 10-week quality and baseline comparison tool.
- Tests should prefer concrete behavior over method-existence checks.
- Top-5 and Top-10 miss reporting must follow the `schedule_json.unscheduled` path used by the regression checker.
- Do not add machine-dependent time or memory assertions to unit tests; use targeted profiling outside the normal test suite.
