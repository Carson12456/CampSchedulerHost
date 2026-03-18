# CampSchedulerHost — GPT‑5.4 Extra High Improvement Plan

This repo has grown to be a “frankenstein” of approaches: root-level legacy shims + a `core/` package + split legacy mixins under `core/scheduler/legacy_parts/`. That’s workable, but it creates drift and “two sources of truth” risk.

This document gives:

- A prioritized improvement roadmap (safety-first, BRAIN-aligned).
- Copy/paste prompts you can give **GPT‑5.4 Extra High** for each ticket.
- A workflow for the model to **read the codebase**, implement changes, and verify without violating the **Top‑5 hard contract**.

---

## Non‑negotiable project rules (must be enforced in every change)

- **BRAIN is authoritative**: `config/BRAIN.md`
- **Hard contract**: `non_exempt_top5_misses == 0` is mandatory; any run with >0 is a failed schedule.
- **Priority ladder** (BRAIN): hard constraints → Top‑5 contract → soft constraints.
- **Miss reporting** must come from `schedule_json.unscheduled` (never reconstructed from preferences).
- **After scheduler edits**, verify with:
  - `pytest -q tests/unit`
  - `python utils/regression_checker.py`
  - For official reporting: `python utils/regression_checker.py --fresh-eval --detailed --show-violations`

Key entry points:

- Pipeline flow: `core/scheduler/pipeline.py`
- Scheduler composition: `core/constrained_scheduler.py`
- Split legacy implementation: `core/scheduler/legacy_parts/*`
- Configuration: `config/SKULL.json` via `core/scheduler/config_loader.py`
- Validation + invariants: `core/scheduler/validators.py`
- Top-5 miss source helpers: `core/services/unscheduled_source.py`

--- 

## Pre-flight checklist (do this once before starting tickets)

- Run `python utils/check_brain_skull_consistency.py` and fix any BRAIN↔SKULL mismatches before touching scheduler logic.
- Confirm the phase modules exist and match the orchestration you’ll edit:
  - `core/scheduler/phase_a_foundation.py`
  - `core/scheduler/phase_b_core.py`
  - `core/scheduler/phase_c_optimization.py`
  - `core/scheduler/phase_d_cleanup.py`
- Decide which “validation stack” you are operating in for a given change, and avoid drifting between them mid-ticket:
  - **Scheduler/mixins path**: `core/constrained_scheduler.py` + `core/scheduler/pipeline.py` + `core/scheduler/legacy_parts/*` + `core/scheduler/validators.py`
  - **Service/rules path** (Clean Architecture): `core/services/constraint_validation_service.py` + `core/rules/*`
  - If a ticket is meant to change the live scheduler behavior, ensure the scheduler/mixins path is updated (not only the service layer).

---

## “How GPT‑5.4 Extra High should read this codebase” (implementation workflow)

Use this checklist inside every prompt (or as a shared “system note”):

### Step 0 — Align on intent and constraints

- Read `config/BRAIN.md` and summarize:
  - hard constraints
  - Top‑5 contract
  - any explicit exceptions (Sailing overlap, AT/WP sharing rules, Tuesday-only HC/DG, no empty slots)
- Read `config/SKULL.json` and confirm it contains required anchors and constraint lists.

### Step 1 — Map the architecture and pick the right module to edit

- Read `core/scheduler/legacy_parts/README.md` and use it as the routing map.
- Confirm the pipeline calls and where the behavior lives:
  - `core/scheduler/pipeline.py` (orchestration)
  - `core/scheduler/phase_a_foundation.py` / `phase_b_core.py` / `phase_c_optimization.py` / `phase_d_cleanup.py` (phase implementations)
  - `core/scheduler/legacy_parts/*.py` (legacy-heavy behavior)
- Preserve backward compatibility shims:
  - root `constrained_scheduler.py`, `models.py`, `activities.py`, `io_handler.py`

### Step 2 — Identify “two sources of truth” and eliminate drift

- Search for duplicated policy definitions:
  - activities defined in both `config/SKULL.json` and `core/activities.py`
  - special-case rule logic embedded in `core/models.py` vs config vs rule modules
  - constants duplicated across `SchedulerConstants` and config loader

### Step 3 — Implement changes behind **invariant gates**

After every major mutating step (or “ticket completion”), ensure these invariants:

- **No empty troop slots** (completeness).
- **Multi-slot integrity** (no partial multi-slot blocks).
- **Hard constraints** satisfied (including Tuesday-only HC/DG and anchors).
- **Top‑5 non‑exempt misses do not increase** (unless you are in an explicit recovery sandbox that rolls back on failure).

Concrete places these gates already live (prefer reusing them over inventing new checkers):

- Gap detection/fix: `_count_troop_empty_slots()`, `_comprehensive_gap_check()`, `_immediate_gap_fix_if_needed()` in `core/scheduler/validators.py` / `core/scheduler/pipeline.py`
- Final integrity/anchors/exclusive areas: `_final_comprehensive_validation()` + `_validate_critical_constraints()` in `core/scheduler/validators.py`
- Authoritative miss accounting source (for reports and regression comparisons): `core/services/unscheduled_source.py` + `utils/regression_checker.py`

### Step 4 — Verification protocol (mandatory)

Run, capture, and report:

- `pytest -q tests/unit`
- `python utils/regression_checker.py`
- `python utils/check_brain_skull_consistency.py` (fast safety check; especially important if SKULL/BRAIN were touched)

If behavior changed intentionally (or you are unsure), run:

- `python utils/regression_checker.py --fresh-eval --detailed --show-violations`

Report deltas using `analysis_results.json` when relevant.

---

## Roadmap (prioritized, safety-first)

### Ticket A — Unify availability/capacity rules (remove “inline special cases”)

**Problem**

Capacity/availability rules are split across:

- `core/models.py` (`Schedule.is_activity_available()` contains special-case logic)
- config (`config/SKULL.json` includes `special_activities`, tags, capacities)
- rule modules (`core/rules/*`) and scheduler mixins (note: `core/rules/capacity_rules.py` already exists)

This makes drift and inconsistent enforcement likely.

**Goal**

Create a single “source of enforcement” for **slot-time availability and capacity** that:

- reads policy from `SKULL.json` (where possible)
- implements the BRAIN exceptions precisely (Sailing overlap model, WP/AT sharing)
- is invoked consistently by schedule placement checks

**Deliverables**

- Prefer updating the existing `core/rules/capacity_rules.py` (and friends like `core/rules/activity_rules.py`, `core/rules/scheduling_rules.py`) so one place answers:
  - “can this activity be placed in this slot?”
  - “what is the max concurrent count for this activity or zone?”
- Ensure the **scheduler path** actually uses the unified logic (either:
  - make `Schedule.is_activity_available()` a thin delegator, or
  - route placement checks through the rule layer in the scheduling mixins).
- Unit tests added/updated to cover:
  - Sailing overlap exception
  - Aqua Trampoline sharing constraints
  - Water Polo sharing constraints
  - Tuesday-only enforcement (HC/DG)

**Prompt for GPT‑5.4 Extra High**

Copy/paste:

```text
You are working in the CampSchedulerHost repo.

Hard rules:
- config/BRAIN.md is authoritative.
- non_exempt_top5_misses must remain 0 (fail closed otherwise).
- Never reconstruct misses from troop.preferences; use schedule_json.unscheduled.
- Preserve pipeline ordering intent (A->D) and backward-compatible root imports.

Task:
Unify all activity availability/capacity logic into a single rule layer.

Instructions:
1) Read config/BRAIN.md, config/SKULL.json, core/scheduler/config_loader.py, core/models.py, core/rules/*.
2) Identify every special-case in Schedule.is_activity_available() (Aqua Trampoline, Water Polo, Sailing overlap, concurrent activities, exclusivity areas, beach staff caps).
3) Implement a single API (e.g. core/rules/capacity_rules.py) that determines whether a placement is allowed, using SKULL config where possible (special_activities, tags, capacities, zone_capacities, concurrent activities, exclusivity exceptions).
4) Make Schedule.is_activity_available() delegate to that API; do not duplicate rule logic in multiple places.
5) Add/adjust unit tests to lock in behavior for Sailing overlap, AT/WP sharing, Tuesday-only HC/DG, and global exclusivity.
6) Run pytest -q tests/unit and python utils/regression_checker.py and report results. If any non_exempt_top5_misses > 0 occurs, rollback and adjust until it is 0.

Output:
- A concise summary of changed files and why.
- Evidence from tests/regression runs.
```

---

### Ticket B — Make SKULL the single source of truth for activities

**Problem**

Activities exist in both:

- `config/SKULL.json` (authoritative data-driven config)
- `core/activities.py` (hardcoded Python list)

**Goal**

Generate `Activity` objects from `SKULL.json` so names/tags/staff/duration can’t drift.

**Deliverables**

- Update `core/activities.py` to load activities from `config_loader` / SKULL.
- Ensure the resulting `Activity` objects match existing expectations (names, `Zone`, staff role).
- Add a consistency check script or unit test:
  - fails if SKULL contains an activity not loadable into the model
  - fails if required anchors are missing

**Prompt for GPT‑5.4 Extra High**

```text
You are working in the CampSchedulerHost repo.

Hard rules:
- config/BRAIN.md is authoritative.
- non_exempt_top5_misses must remain 0.
- Preserve backward compatibility shims at repo root (activities.py should continue to re-export core.activities).

Task:
Make SKULL.json the single source of truth for Activity definitions.

Instructions:
1) Read config/SKULL.json, core/scheduler/config_loader.py, core/activities.py, core/models.py.
2) Replace the hardcoded list in core/activities.py with a loader that constructs Activity objects from SKULL's `activities` list (name, duration->slots, zone mapping, staff_needed->staff, conflicts/tags if relevant).
3) Ensure Zone values map correctly to core.models.Zone.
4) Add a validation step (unit test or utility) that fails fast if SKULL activities cannot be instantiated or if required BRAIN anchors are missing.
5) Run pytest -q tests/unit and python utils/regression_checker.py and report results.
```

---

### Ticket C — Make multi-slot scheduling block-safe (eliminate partial mutation)

**Problem**

Multi-slot activities (Sailing 1.5, 2-slot canoe activities, 3-hour blocks) can be corrupted by moves/swaps that treat each `ScheduleEntry` independently.

**Goal**

Prevent corruption by enforcing **block operations**: move/swap/remove multi-slot placements as a single atomic unit.

**Deliverables**

- A block helper abstraction (even lightweight) used by:
  - placement helpers
  - swap/recovery routines
  - cleanup/sanitization passes
- Tests proving:
  - multi-slot activities cannot end up partially scheduled
  - swaps preserve blocks or reject

**Prompt for GPT‑5.4 Extra High**

```text
You are working in the CampSchedulerHost repo.

Hard rules:
- config/BRAIN.md is authoritative.
- Do not allow multi-slot corruption. If a move/swap would split a multi-slot block, reject it.
- non_exempt_top5_misses must remain 0.

Task:
Make multi-slot handling block-safe across scheduling moves/swaps.

Instructions:
1) Read core/models.py (Schedule.add_entry / is_troop_free / is_activity_available), core/scheduler/legacy_parts/placement_and_state.py, and any code that removes or swaps entries.
2) Identify all operations that remove/move single entries without considering multi-slot blocks.
3) Implement an atomic block abstraction (start slot + occupied slots) and update move/swap helpers to operate on blocks.
4) Add unit tests that attempt to trigger partial multi-slot corruption and verify it is prevented.
5) Run pytest -q tests/unit and python utils/regression_checker.py and report results.
```

---

### Ticket D — Refactor the pipeline into explicit “steps” with invariant gates

**Problem**

`core/scheduler/pipeline.py` is a long imperative sequence with “moved/replaced/disabled” logic and limited safety structure.

**Goal**

Make the pipeline easier to maintain and safer to modify by introducing:

- explicit step objects (name, purpose, mutates schedule, allowed relaxations)
- automatic invariant checks after each step

**Deliverables**

- A small step framework (could be internal classes) used by `schedule_all()`
- Standardized logging via `core/scheduler_logging.py` instead of ad-hoc `print()`

**Prompt for GPT‑5.4 Extra High**

```text
You are working in the CampSchedulerHost repo.

Hard rules:
- Preserve A->D phase ordering intent (rocks first).
- Add invariant gates after every mutating pipeline step:
  - no empty troop slots
  - multi-slot integrity
  - hard constraints satisfied
  - non_exempt_top5_misses does not increase (unless in a rollback sandbox)

Task:
Refactor core/scheduler/pipeline.py into explicit steps with invariant gates.

Instructions:
1) Read core/scheduler/pipeline.py and core/scheduler_logging.py and identify step boundaries.
2) Introduce a Step abstraction (name + callable + gate policy) and run steps in order.
3) Replace prints with structured logger calls.
4) Ensure behavior is unchanged (except clearer structure) and all tests pass.
5) Run pytest -q tests/unit and python utils/regression_checker.py and report results.
```

---

### Ticket E — Reduce sys.path hacks by standardizing entrypoints (keep compatibility)

**Problem**

Many scripts/tests manipulate `sys.path`, and root modules do defensive module clearing. This makes “works in one context but not another” likely.

**Goal**

Move toward consistent import semantics while preserving legacy usage.

**Deliverables**

- Standard module execution patterns for utils/scripts (`python -m ...` or consistent path handling)
- Root shims remain, but ideally become simple re-exports without complex path surgery

**Prompt for GPT‑5.4 Extra High**

```text
You are working in the CampSchedulerHost repo.

Hard rules:
- Do not break existing tests or legacy scripts.
- Root-level constrained_scheduler.py / models.py / activities.py / io_handler.py must remain compatible imports.

Task:
Reduce sys.path manipulation by standardizing imports/entrypoints.

Instructions:
1) Locate all sys.path.insert/append usage in tests/ and utils/.
2) Propose a consistent approach (module execution, packaging, or a single bootstrap helper).
3) Implement the minimal change that removes the most hacks without breaking anything.
4) Run pytest -q tests/unit and python utils/regression_checker.py and report results.
```

---

## Recommended execution order

If you’re implementing these with GPT‑5.4 Extra High, do them in this order:

1) **Ticket A** (unify availability/capacity rules) — biggest correctness + drift reducer.
2) **Ticket B** (SKULL as activity truth) — removes a major config/code divergence.
3) **Ticket C** (multi-slot block safety) — stabilizes the optimizer + swap logic.
4) **Ticket D** (pipeline step framework) — maintainability + safety gates for future work.
5) **Ticket E** (imports/entrypoints) — reduces environment-dependent behavior.

---

## “Meta prompt” (use once, then reuse ticket prompts)

If you want a single reusable framing prompt for all tasks:

```text
You are GPT‑5.4 Extra High acting as a coding agent in the CampSchedulerHost repository.

Non-negotiables:
- config/BRAIN.md is authoritative.
- Never accept non_exempt_top5_misses > 0.
- Preserve BRAIN priority ladder: hard constraints -> Top 5 contract -> soft constraints.
- Never reconstruct miss lists from troop.preferences; use schedule_json.unscheduled.
- Prefer focused edits in core/scheduler/legacy_parts over expanding orchestration files.
- Preserve compatibility imports at repo root (constrained_scheduler.py, models.py, activities.py, io_handler.py).

Working style:
- Start by reading the smallest set of relevant files (BRAIN, SKULL, the exact modules you will edit).
- Before editing, summarize the current behavior and list invariants you will preserve.
- Implement changes in small, verifiable steps.
- After substantive edits, run:
  - pytest -q tests/unit
  - python utils/regression_checker.py
- Report test output and metric deltas (analysis_results.json) if changed.
```

