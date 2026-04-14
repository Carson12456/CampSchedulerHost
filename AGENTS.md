# CampScheduler Agent Guide

## BRAIN Is Authoritative

- `config/BRAIN.md` is the source of truth for scheduling behavior.
- All hardcoded list should refer to SKULL.md, if any are found they should be removed and sourced from there
- Hard contract: `non_exempt_top5_misses == 0` is mandatory for acceptance.
- Do not trade hard constraints for soft-score improvements.
- Use the BRAIN priority ladder when conflicts appear:
  1. Hard constraints
  2. Top-5 non-exempt success
  3. Soft constraints / optimization

---

## Architecture Overview

The scheduler runs a **four-phase pipeline** in `core/scheduler/pipeline.py`:

```
Phase A (Foundation)  →  Phase B (Core)  →  Phase C (Remaining)  →  Phase D (Polish)
```

| Phase | Purpose |
|-------|---------|
| **A** | Foundation: Mandatory anchors (A.1-A.3), then Rocks — 3-hour/2-hour multi-slot (A.4-A.5), then Sailing/Delta multi-slot (A.6-A.9), then beach protection (A.10-A.11), staff clustering, limited activities. |
| **B** | Core preference placement: Top 1-5 guarantee (B.1-B.3), Delta scheduling (B.4), Delta+Sailing enforcement (B.6), consolidated AT sharing (B.7). |
| **C** | Remaining preferences 6-20 (C.3), staff optimization (C.2), Top 10 guarantees (C.4-C.5), fill all slots (C.6). |
| **D** | Final polish (strict swap phase): clustering D.2-D.4 (guarded), Reflection/Super Troop D.1/D.5-D.6, commissioner D.7/D.9, setup D.8, gap close D.10, single cleanup D.11. All destructive steps wrapped in Top-5/Top-10 safety harness. |

Gap checks run after each major phase. The composition uses mixins in `core/constrained_scheduler.py`; implementation lives in `core/scheduler/legacy_parts/`.

---

## Task → Entry Point Map

| Task | Start here |
|------|------------|
| Change Top-5 / swap / preference enforcement | `legacy_parts/top5_and_swaps.py` |
| Change gap-filling or stats | `legacy_parts/gap_fill_and_stats.py` |
| Add/modify placement or state logic | `legacy_parts/placement_and_state.py` |
| Change sequencing or constraints | `legacy_parts/sequencing_and_constraints.py` |
| Change preference-range or limited-activity logic | `legacy_parts/preference_and_limited.py` |
| Change clustering or optimization | `legacy_parts/clustering_and_optimization.py` |
| Add constraint | `core/scheduler/constraints.py` + `config/BRAIN.md` |
| Change validation | `core/scheduler/validators.py` |
| Update regression baseline | `utils/regression_checker.py` + `analysis_results.json` |

---

## Domain Glossary

| Term | Meaning |
|------|---------|
| **HC** | History Center – Tuesday-only activity |
| **DG** | Disc Golf – Tuesday-only activity |
| **Top 5** | Troop preferences ranked 1–5; must be satisfied (non-exempt) |
| **Top 10** | Preferences ranked 1–10; soft target with exemptions |
| **Non-exempt miss** | A Top 5 miss that does NOT qualify for exemption (never acceptable) |
| **Exempt miss** | Miss forgiven by formal rules (3-hour duplication, Tuesday HC/DG saturation, 2-hour canoe duplication) |
| **Reflection** | Friday mandatory activity for all troops |
| **Super Troop** | Weekly mandatory activity for all troops |
| **Mandatory anchors** | Reflection, Super Troop, HC/DG Tuesday, no empty slots |

---

## AI Pitfalls (Avoid These)

- **Reconstructing misses from preferences** – Use `schedule_json.unscheduled` only. Never derive misses from `troop.preferences`.
- **Trading Top 5 for soft score** – Never relax the Top 5 contract to improve soft constraints.
- **Changing phase order casually** – Phase order is intentional (rocks first). Only change with explicit design intent.
- **Editing composition files when split exists** – Prefer `legacy_parts/` modules over expanding `constrained_scheduler.py` or `pipeline.py`.

---

## High-Value Entry Points

- `core/constrained_scheduler.py`: scheduler composition and shared constants.
- `core/scheduler/pipeline.py`: A->D phase flow in execution order.
- `core/scheduler/legacy_parts/`: split modules for legacy-heavy scheduling behavior.
- `core/models.py`: schedule primitives and low-level availability constraints.
- `utils/regression_checker.py`: authoritative 10-week quality/baseline comparison.
- `config/BRAIN.md`: product constraints and expected scheduling policy.

---

## Fast Validation Commands

- `pytest -q tests/unit`
- `pytest -q tests/unit/test_scheduling_algorithm.py`
- `python utils/regression_checker.py`
- `python utils/regression_checker.py --fresh-eval --detailed --show-violations`

---

## Change Safety Rules

- Keep `from constrained_scheduler import ConstrainedScheduler` compatibility intact.
- Preserve `schedule_all()` phase ordering unless intentionally changing behavior.
- After scheduler edits, run both unit tests and `utils/regression_checker.py`.
- Prefer adding methods in focused split modules over expanding composition files.
- Preserve mandatory anchors: Friday `Reflection`, weekly `Super Troop`, Tuesday-only `History Center` + `Disc Golf`.
- Preserve hard completeness: no empty troop slots.
- Respect Sailing slot-2 overlap exception exactly as documented in BRAIN.

---

## Baseline Terminology

| File | Role | Purpose |
|------|------|---------|
| `baseline_prime_10weeks.json` | **Reference Baseline (Prime)** | Original scheduler output before improvement work. Historical record. Not used for regression detection. |
| `baseline_metrics_10weeks.json` | **Comparison Baseline** | Regression comparison point. New changes are compared against this to detect regressions. |

- To update the Comparison Baseline after scheduler changes:  
  `python utils/regression_checker.py --fresh-eval --set-baseline --force-baseline`  
  (Preserves existing Comparison as Reference Prime if Prime does not exist.)
- Regressions are detected when current run is worse than the **Comparison Baseline**.

---

## Metrics + Reporting Rules

- Top-5/Top-10 miss reporting must come from `schedule_json.unscheduled`.
- Never reconstruct authoritative miss lists from raw `troop.preferences`.
- If `unscheduled` payload is missing, fail-fast instead of estimating.
- For official comparisons, use the fresh-run protocol (`--fresh-eval`) before reporting regressions.

---

## Search Tips

- Use `rg "def _method_name\\(" core/scheduler/legacy_parts`
- Use `rg "subsection\\(\" core/scheduler/pipeline.py` to locate phase checkpoints.
- Use `rg "Top 5|Top5|mandatory" core/scheduler` for preference logic hotspots.
- Use `rg "unscheduled|non_exempt_top5_misses|fresh-eval" utils core` for BRAIN compliance points.
