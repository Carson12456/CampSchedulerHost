# CampScheduler — Thorough Code Review & Optimization Plan

> Goal: Systematically hunt for logical errors, bugs, missing features, poor
> implementation, and sub‑optimal scoring strategy across the whole codebase,
> measured against the contract in `config/BRAIN.md` and the configuration in
> `config/SKULL.json`.
>
> This document is the **map + method + work packages + ready‑to‑paste prompts +
> recommended model reasoning tier** for that review. Work top‑to‑bottom.

---

## 0. How to read this plan

The review is split into **13 work packages (WP0–WP12)**. Each package has:

- **Scope** — exactly which files/areas it covers.
- **What to check** — the contract clauses and bug classes to verify.
- **Model tier** — which Claude 4.8 reasoning level to run it at (see below).
- **Prompt** — a copy‑paste prompt scoped to that package.

Do the packages **in order**. WP0 establishes a baseline; WP1–WP9 are deep
audits; WP10–WP11 are breadth/quality; WP12 synthesizes everything into a
prioritized, regression‑gated fix backlog.

### Golden rules for the whole review

1. **Audit read‑only first, fix later.** Each deep package produces *findings*
   (file:line, severity, contract clause, proposed fix). Do **not** edit code
   during the audit pass — batch fixes in WP12 so every change is regression‑gated.
2. **`config/BRAIN.md` is the contract; `utils/regression_checker.py` is the
   judge.** A "bug" is any place where code disagrees with BRAIN, or where the
   judge rewards behavior BRAIN forbids (or vice‑versa).
3. **Never trade the Top‑5 contract for score.** `non_exempt_top5_misses == 0`
   is mandatory. Any finding that would risk it is automatically high‑severity.
4. **Miss data comes only from `schedule_json.unscheduled`.** Flag any code path
   that reconstructs misses from `troop.preferences`.
5. **Validate every fix** with `pytest -q tests/unit` and
   `python utils/regression_checker.py --fresh-eval --detailed --show-violations`.

---

## 1. Model reasoning tier guide (Claude 4.8)

Pick the tier per package based on reasoning depth, not file size. Higher tiers
cost more and are slower — spend them where subtle cross‑file logic lives.

| Tier | Use it for | In this plan |
| :--- | :--- | :--- |
| **Medium** | Mechanical/breadth work, running commands, summarizing, dead‑code sweeps, doc/consistency diffs. | WP0, WP10 |
| **High** | Single‑module logic review, pipeline ordering, clustering math, test adequacy, synthesis. | WP1, WP4, WP7, WP8, WP9, WP11 |
| **Extra High** | Multi‑file constraint correctness where one wrong predicate silently corrupts every schedule. | WP2, WP6 |
| **Max** | The two highest‑risk, most subtle subsystems where BRAIN itself documents fragility: the Top‑5 exemption engine and the MUST‑HONOR day‑request solver. | WP3, WP5, WP12(final) |

**Cost discipline:** run Medium/High packages as background subagents in
parallel; reserve Max for the two packages that genuinely need it (WP3, WP5)
and for the final synthesis decision in WP12.

---

## 2. Codebase map & interdependencies

Understanding *how* the pieces connect is required before judging any one piece.

### 2.1 Composition (the spine)

`core/constrained_scheduler.py` builds `ConstrainedScheduler` by multiple
inheritance from ~15 mixins. **MRO order is load‑bearing** — if two mixins define
the same method, the earlier one in the class bases list wins. Any review of a
`_method` must confirm there isn't a second definition shadowing it.

```text
ConstrainedScheduler(MRO, abbreviated)
├── LegacyInterfaceMixin
├── legacy_parts/  ← the ~18k lines of real behavior
│   ├── placement_and_state.py        (2.8k) mutation, snapshot/restore, low-level placement
│   ├── top5_and_swaps.py             (3.5k) Top-5 recovery + swaps   ★ highest risk
│   ├── preference_and_limited.py     (2.4k) preference ranges, limited activities
│   ├── sequencing_and_constraints.py (1.6k) _can_schedule, adjacency, sequence rules
│   ├── gap_fill_and_stats.py         (3.3k) gap fill, stats/score helpers, reporting
│   ├── clustering_and_optimization.py(2.9k) Phase D clustering passes
│   ├── safety_and_export.py          (1.2k) safe fallbacks, export
│   └── compatibility_bridges.py      (0.1k) legacy wrappers
├── SchedulerState                    state.py — _initialize_state, attributes
├── SchedulingPipelineMixin           pipeline.py — schedule_all() A→D order  ★ orchestration
├── UtilityMixin                      utilities.py
├── ValidatorMixin                    validators.py — excess-day / validation predicates
├── PhaseAFoundationMixin             phase_a_foundation.py
├── PhaseBCoreMixin                   phase_b_core.py
└── PhaseDCleanupMixin                phase_d_cleanup.py
```

### 2.2 Data & config flow

```text
config/SKULL.json ──► core/scheduler/config_loader.py ──► core/scheduler/constants.py (SchedulerConstants)
                                                              │
core/activities.py ◄── SKULL activities                       └──► class attrs on ConstrainedScheduler
core/models.py  (Activity, Troop, ScheduleEntry, TimeSlot, Day, Zone, Schedule, generate_time_slots)
core/services/unscheduled_source.py  ──► builds schedule_json.unscheduled (authoritative misses)
core/services/unscheduled_analyzer.py ──► classifies exempt vs non-exempt
core/services/sailing_half_fills.py   ──► C.6b sidecar half-slot fills
utils/regression_checker.py            ──► THE score (450/250/200/100 buckets) + violation report
utils/regenerate_all_schedules.py      ──► fresh-run regeneration of data/schedules/*.json
web/gui_web.py                         ──► Flask UI consuming schedules
```

### 2.3 Backward‑compat shims (do not break)

Root `constrained_scheduler.py`, `models.py`, `activities.py`, `io_handler.py`
re‑export from `core/`. Any rename in `core/` must keep these resolving.

### 2.4 First reading order (for any reviewer/subagent)

`BRAIN.md` → `SKULL.json` → `config_loader.py` → `constants.py` →
`models.py` → `pipeline.py` → then the relevant `legacy_parts/*` module →
`regression_checker.py`.

---

## 3. Cross‑cutting questions to answer everywhere

Carry these five questions into every package; they are the recurring bug classes
this codebase is structurally prone to:

1. **Config drift:** Is this behavior hardcoded when it should read SKULL? Does a
   SKULL list exist that the code ignores? (e.g. `prohibited_pairs` is empty `[]`
   while `soft_prohibited_pairs` is populated — confirm nothing reads the empty one
   expecting content.)
2. **MRO shadowing:** Is this `_method` defined in more than one mixin?
3. **Mutation without guard:** Does this pass mutate `self.schedule.entries`
   outside a `_safe_phase_d_step` / snapshot boundary, risking a Top‑5 regression
   with no rollback?
4. **Miss‑source violation:** Does this compute misses from `troop.preferences`
   instead of `schedule_json.unscheduled`?
5. **Judge/contract mismatch:** Does `regression_checker.py` score this the way
   BRAIN §4/§6 says it should?

---

## 4. Work packages

### WP0 — Baseline & smoke (Tier: Medium)

**Scope:** Establish ground truth before judging anything.
**What to check:** Tests pass; regression checker runs; capture current scores per
week; note any runtime warnings, exceptions, or `UNFULFILLED`/`INFEASIBLE` logs.

**Prompt:**
> Run `pytest -q tests/unit` and
> `python utils/regression_checker.py --fresh-eval --detailed --show-violations`.
> Capture: per‑week score, `non_exempt_top5_misses`, excess cluster days, cluster
> gaps, soft violations, staff variance, and any exceptions or `UNFULFILLED`/
> `INFEASIBLE` lines. Produce a baseline table I can diff future runs against. Do
> not change any code. Save findings to `review/WP0_baseline.md`.

---

### WP1 — Contract ↔ Config alignment (Tier: High)

**Scope:** `config/BRAIN.md`, `config/SKULL.json`, `config_loader.py`,
`constants.py`, `core/activities.py`, `utils/check_brain_skull_consistency.py`.
**What to check:**
- Every activity/zone/staff/limit in BRAIN §4 exists and matches SKULL.
- Every SKULL list is actually consumed by `config_loader`→`constants`→scheduler
  (find orphan config and orphan hardcoded lists).
- Numeric limits agree across all three sources: canoe 26, beach staff 12, global
  staff base 16 / target 14, beach saturation 4 (Top‑5 AT overload to 5),
  `tower_extended_size` 15, `sailing_extended_size` 12.
- `prohibited_pairs: []` vs `soft_prohibited_pairs` — confirm intentional.
- `mandatory_anchors`, `tuesday_only_activities`, `request_only_activities`,
  `concurrent_*` lists are wired to enforcement.

**Prompt:**
> Read `config/BRAIN.md` and `config/SKULL.json` as the contract. Trace every
> SKULL key through `core/scheduler/config_loader.py` and
> `core/scheduler/constants.py` into how `ConstrainedScheduler` uses it. Report:
> (a) any BRAIN rule or numeric limit not represented in SKULL/constants, (b) any
> SKULL list that no code reads, (c) any hardcoded list/limit in code that should
> come from SKULL, (d) mismatched numbers across the three. Cite file:line. Read
> only; write findings to `review/WP1_contract_alignment.md`.

---

### WP2 — Hard‑constraint correctness (Tier: Extra High)

**Scope:** `validators.py`, `constraints.py`,
`legacy_parts/sequencing_and_constraints.py` (`_can_schedule` and helpers),
plus the final normalizer `_enforce_sailing_slot_exclusivity` in `pipeline.py`.
**What to check** (BRAIN §4 HARD list — each predicate, including the boundary cases):
- Exclusive double‑booking + the **Sailing slot‑2 overlap exception** (search‑time
  1‑or‑2; final output: slot1≤1, slot2≤2, slot3≤1). Verify the "has_prev" start
  detection in `_enforce_sailing_slot_exclusivity` can't mis‑count a 3‑slot day.
- Completeness (no empty slots) — is it actually guaranteed at every exit gate?
- Anchors: Reflection=Friday, Super Troop weekly×1, HC/DG Tuesday‑only.
- **Delta + Tower/ODS adjacency** (never in slots N and N+1, either order) —
  verify `sequence_rules.not_back_to_back` is read and applied both directions.
- Capacity: canoe 26, global staff 16, beach staff 12, beach saturation 4→5.
- Shower House: none Monday; not before later Super Troop/wet activity same day.

**Prompt:**
> Audit hard‑constraint enforcement against `config/BRAIN.md` §4. For each HARD
> rule, find the exact predicate in `core/scheduler/validators.py`,
> `core/scheduler/constraints.py`, and
> `core/scheduler/legacy_parts/sequencing_and_constraints.py`, and prove it is
> correct including off‑by‑one and both‑direction cases (esp. Delta↔Tower/ODS
> adjacency and the Sailing slot‑2 overlap exception normalized in
> `pipeline.py:_enforce_sailing_slot_exclusivity`). Flag any rule that is missing,
> one‑directional, mis‑indexed, or bypassable. Cite file:line and give a concrete
> failing scenario for each. Read only; write `review/WP2_hard_constraints.md`.

---

### WP3 — Top‑5 contract & exemption engine (Tier: Max) ★ highest risk

**Scope:** `legacy_parts/top5_and_swaps.py`,
`core/services/unscheduled_source.py`, `core/services/unscheduled_analyzer.py`,
and `_count_non_exempt_top5_misses` (wherever defined).
**What to check** (BRAIN §2 exactly):
- The four exemption rules implemented faithfully: 3‑hour duplication; Tuesday
  HC/DG saturation (only top‑3 of combined DG+HC get the 3 Tuesday slots);
  two‑hour canoe duplication; day‑request displacement (Exemption 4/5).
- `_count_non_exempt_top5_misses` agrees with `unscheduled.<troop>.top5[]` and is
  the single source of truth — no parallel/disagreeing miss computation anywhere.
- Every recovery/enforcement loop (`_force_top1_preferences`, `_guarantee_all_top5`,
  `_enforce_mandatory_top5`, `_schedule_preferences_range`) honors anchor and
  **pair‑protected Delta** (`_is_pair_protected_delta`) at *every* displacement site.
- The final acceptance gate truly raises when `final_top5 > 0`.

**Prompt:**
> This is the hard contract: `non_exempt_top5_misses == 0`. Audit the Top‑5
> subsystem against `config/BRAIN.md` §2, §11. (1) Verify each of the four exempt‑
> miss rules is implemented correctly in `core/services/unscheduled_analyzer.py` /
> `unscheduled_source.py`, with correct Tuesday HC/DG saturation (top‑3 combined)
> and canoe/3‑hour duplication logic. (2) Confirm `_count_non_exempt_top5_misses`
> sources from `schedule_json.unscheduled` and that no other code reconstructs
> misses from `troop.preferences`. (3) In every Top‑5 recovery loop in
> `core/scheduler/legacy_parts/top5_and_swaps.py`, confirm anchors AND
> pair‑protected Delta are excluded from displacement. Give concrete scenarios
> where a non‑exempt Top‑5 miss could slip past the gate. Read only; write
> `review/WP3_top5_contract.md`.

---

### WP4 — Pipeline ordering & Phase‑D guards (Tier: High)

**Scope:** `pipeline.py` (`schedule_all`, `_safe_phase_d_step`,
`_immediate_gap_fix_if_needed`, `_count_top10_in_schedule`).
**What to check:**
- Phase order matches BRAIN §5 (A.1→A.3→A.4→A.6→A.7→A.5→A.2→A.12; B; C; D; final).
- `_safe_phase_d_step` rollback math is correct: it rolls back on Top‑5 increase,
  >2 Top‑10 loss, excess‑day increase, or gap increase — confirm thresholds match
  intent and that snapshot/restore is symmetric.
- The **intentionally unguarded** steps (D.5, D.6, D.1) — verify the BRAIN
  rationale still holds and that they truly can't drop a preferred activity.
- The terminal repair/audit loops at the end of `schedule_all` (lines ~485–553)
  can't infinite‑loop or leave gaps; rollback conditions are complete.
- Cut steps (A.8–A.11, A.14, B.4) are dead and not silently half‑wired.

**Prompt:**
> Audit `core/scheduler/pipeline.py` against `config/BRAIN.md` §5. Confirm the A→D
> step order matches the documented (relocated) order and that each `_record_…`/
> exit‑gate is present. Scrutinize `_safe_phase_d_step` rollback logic and the
> terminal filler‑audit/cluster‑repair loops at the end of `schedule_all` for:
> incomplete rollback conditions, asymmetric snapshot/restore, gaps left behind,
> or non‑termination. Verify the unguarded D.1/D.5/D.6 steps cannot remove a
> preferred activity. Cite file:line; write `review/WP4_pipeline.md`. Read only.

---

### WP5 — MUST‑HONOR day‑request solver (Tier: Max) ★ BRAIN flags this fragile

**Scope:** `_schedule_day_requests` (both passes), the T0–T6 tier ladder,
`force_day_request` semantics in `_can_schedule`, Thursday 3‑hour opt‑out, and the
downstream guards `_remove_overlaps` / `_fix_multislot_integrity` /
`_is_day_request_thursday_3slot`.
**What to check** (BRAIN §10):
- Two‑pass architecture: C.1 non‑aggressive (T1–T2, non‑destructive) vs final
  aggressive (T1–T6) inside `_final_comprehensive_validation`.
- Each tier T0–T6 does exactly what §10.2 says; T4 wrong‑day relocation must not
  cannibalize other day‑requests for the same activity.
- `force_day_request` bypasses only the listed soft checks and still enforces the
  listed physical invariants.
- Thursday 3‑slot opt‑out appends Thu‑1/2/3 with a virtual slot‑3 and is preserved
  by the two guarded removal sites (BRAIN §10.5 explicitly warns these are fragile).
- Protected anchors + pair‑protected Delta never displaced; UNFULFILLED/INFEASIBLE
  logged with reasons.

**Prompt:**
> Audit the MUST‑HONOR day‑request solver against `config/BRAIN.md` §10 (and §1
> priority ladder where day‑requests supersede Top‑5). Trace `_schedule_day_requests`
> in both passes and verify tiers T0–T6 match §10.2 exactly — especially T4 not
> cannibalizing sibling day‑requests, T6 producing only Exemption‑4/5 exempt
> misses, and `force_day_request` bypassing only the §10.3 soft checks while keeping
> physical invariants. Verify the Thursday 3‑hour opt‑out (virtual Thu‑slot‑3) is
> preserved by `_remove_overlaps` and `_fix_multislot_integrity` via
> `_is_day_request_thursday_3slot`. Construct scenarios that would strip an opt‑out
> trio or silently drop a day‑request. Read only; write `review/WP5_day_requests.md`.

---

### WP6 — Scoring authority (Tier: Extra High)

**Scope:** `utils/regression_checker.py` (`evaluate_week`, `DEFAULT_WEIGHTS`,
`_calculate_delta_timing_penalty`, `_calculate_at_sharing_misses`, the soft‑
violation and cluster/staff blocks).
**What to check** (BRAIN §6 + §4 SOFT):
- Buckets sum to 1000 (450 pref / 250 efficiency / 200 soft+expect / 100 staff)
  and "innocent‑until‑proven‑guilty" base never exceeds bucket caps.
- Excess‑day formula `ceil(activity_count/3)` and the canonical `1,-,3` cluster‑gap
  definition implemented exactly as §6 states.
- Every SOFT pair from BRAIN §4 / SKULL `soft_prohibited_pairs` is scored (free
  time, accuracy, water games, boats, balls) — none missing, none double‑counted.
- Delta timing penalty matches §7 (earliest needed window; demand‑aware).
- Reported Top‑5/Top‑10 come from `unscheduled`, not recomputed.
- Look for **score‑gaming mismatches**: places where the scheduler optimizes a
  metric the judge doesn't reward, or ignores a penalty the judge does apply
  (this is the core "optimal strategy" question).

**Prompt:**
> Treat `utils/regression_checker.py` as the score authority and `config/BRAIN.md`
> §6/§4/§7 as the spec. Verify: bucket weights sum to 1000 and respect caps; the
> excess‑day `ceil(n/3)` and `1,-,3` cluster‑gap definitions are implemented
> exactly; every SOFT pair in SKULL `soft_prohibited_pairs` is penalized once;
> Delta timing and AT‑sharing penalties match §7; Top‑5/Top‑10 are read from
> `unscheduled`. Then identify strategic gaps: metrics the scheduler tries to
> improve that the judge ignores, and penalties the judge applies that no phase
> targets. Cite file:line; write `review/WP6_scoring.md`. Read only.

---

### WP7 — Clustering & Phase‑D optimization (Tier: High)

**Scope:** `legacy_parts/clustering_and_optimization.py`,
`legacy_parts/gap_fill_and_stats.py`, `phase_d_cleanup.py`,
`validators.py:would_create_excess_day_for_entries`.
**What to check:**
- `_count_excess_cluster_days` / `_count_area_cluster_gaps` match the §6
  definitions used by the judge (the scheduler must measure what the judge scores).
- D.2/D.3/D.4/D.8/D.9/D.10 actually reduce excess days / gaps without creating
  hard violations; D.3 "FORCED" bypass relies on D.11 cleanup — verify that
  contract holds.
- Delta/Sailing envelope protection respected in late clustering (BRAIN §11 lists
  this as *pending* coverage — likely real findings here).

**Prompt:**
> Audit clustering/optimization (`clustering_and_optimization.py`,
> `gap_fill_and_stats.py`, `phase_d_cleanup.py`). Confirm the scheduler's
> `_count_excess_cluster_days` and `_count_area_cluster_gaps` use the same
> definitions the judge uses (`utils/regression_checker.py`, BRAIN §6). Verify each
> Phase‑D clustering pass reduces the intended metric without hard violations, that
> D.3's FORCED bypass is always repaired by D.11, and that Delta/Sailing pair
> protection (BRAIN §11) is honored in late swaps. Note where §11 "pending"
> coverage causes measurable drift. Cite file:line; write `review/WP7_clustering.md`.

---

### WP8 — Placement & state integrity (Tier: High)

**Scope:** `legacy_parts/placement_and_state.py`, `state.py`,
`_snapshot_scheduler_state` / `_restore_scheduler_state`, `_rebuild_staff_tracking`,
`_fix_multislot_integrity`, `_add_to_schedule` / `_remove_from_schedule`.
**What to check:**
- Snapshot/restore is deep and complete (no shared references that leak mutations
  across a rollback). This underpins every Phase‑D guard — if it's shallow, guards
  silently fail.
- Multi‑slot add/remove keeps Sailing/2‑hr/3‑hr blocks contiguous and consistent.
- Staff tracking is rebuilt whenever entries change (stale staff maps → wrong caps).

**Prompt:**
> Audit `core/scheduler/legacy_parts/placement_and_state.py` and `state.py`.
> Prove `_snapshot_scheduler_state`/`_restore_scheduler_state` produce a true deep
> rollback (no aliased lists/dicts leaking mutations), since every Phase‑D guard
> depends on it. Verify multi‑slot add/remove keeps blocks contiguous and that
> staff tracking is rebuilt after every mutation that changes entries. Give
> concrete corruption scenarios. Cite file:line; write `review/WP8_state.md`.

---

### WP9 — Sailing pipeline & half‑slot fills (Tier: High)

**Scope:** `core/services/sailing_half_fills.py`, `_schedule_sailing_balls_fills`,
`_schedule_sailing_optimize_all`, `_schedule_delta_sailing_pairs`, C.6b in pipeline.
**What to check** (BRAIN §5 A.6/A.7, §3, C.6b):
- 90‑min/2‑slot Sailing model consistent from search → final normalization.
- C.6b candidate order (Gaga Ball, 9 Square, Trading Post → Campsite Free Time),
  rank‑override rule, and the "11–20 counts / 1–10 doesn't substitute" rule.
- A.6 before A.5 actually prevents A.5 first‑fit from scooping Sailing.

**Prompt:**
> Audit the Sailing subsystem against BRAIN §5 (A.6/A.7, C.6b) and §3. Verify the
> 90‑minute 2‑slot model is consistent across `_schedule_sailing_optimize_all`,
> `_schedule_delta_sailing_pairs`, the final `_enforce_sailing_slot_exclusivity`,
> and the half‑slot sidecar in `core/services/sailing_half_fills.py`. Confirm the
> C.6b candidate order, rank‑override, and the 11–20‑counts / 1–10‑doesn't‑substitute
> rule. Confirm A.6 running before A.5 prevents Sailing from being grabbed by
> first‑fit. Cite file:line; write `review/WP9_sailing.md`. Read only.

---

### WP10 — Breadth: web, IO, dead code, shims (Tier: Medium)

**Scope:** `web/gui_web.py`, `io_handler.py`, root compat shims,
`compatibility_bridges.py`, `psutil.py` (note: a local stub — confirm intentional),
cut phase bodies (A.8–A.11, A.14, B.4).
**What to check:** dead/unreachable code, duplicated logic, error handling in the
GUI, the local `psutil.py` shadowing the real package, and broken compat shims.

**Prompt:**
> Do a breadth sweep of `web/gui_web.py`, `io_handler.py`, the root compatibility
> shims (`constrained_scheduler.py`, `models.py`, `activities.py`, `io_handler.py`),
> `compatibility_bridges.py`, and the local `psutil.py`. Flag dead/unreachable code,
> duplicated logic, missing error handling, and whether the local `psutil.py` stub
> is intentional or dangerously shadowing the real package. List cut phase bodies
> (A.8–A.11, A.14, B.4) and confirm they're fully disconnected. Write
> `review/WP10_breadth.md`. Read only.

---

### WP11 — Test adequacy (Tier: High)

**Scope:** `tests/unit/*` (`test_constraint_system.py`, `test_core_entities.py`,
`test_scheduling_algorithm.py`, `test_scoring_contract.py`).
**What to check:** Do the tests actually enforce the BRAIN contract, or just
exercise code? Coverage gaps for: Top‑5 exemptions, Delta/Tower adjacency, Sailing
capacity, MUST‑HONOR ladder, Thursday opt‑out, cluster‑gap definition, scoring caps.

**Prompt:**
> Review `tests/unit/*` against `config/BRAIN.md`. For each hard contract clause
> (Top‑5 zero non‑exempt, anchors, Delta↔Tower/ODS adjacency, Sailing capacity,
> MUST‑HONOR tiers, Thursday opt‑out, cluster‑gap/excess‑day math, scoring caps),
> state whether a test would catch a regression in it. List the highest‑value
> missing tests. Write `review/WP11_tests.md`. Read only.

---

### WP12 — Synthesis & prioritized fix backlog (Tier: Max for triage, then High to fix)

**Scope:** all `review/WP*.md` findings.
**What to do:**
1. Merge findings, dedupe, and classify each by severity:
   **S0** (breaks Top‑5/hard contract), **S1** (wrong score / contract mismatch),
   **S2** (missed optimization / strategy), **S3** (quality/dead code).
2. Order S0→S3; within a tier order by score impact × confidence.
3. Fix in small, regression‑gated commits: after each fix run
   `pytest -q tests/unit` then `python utils/regression_checker.py --fresh-eval
   --detailed --show-violations`; compare to the WP0 baseline; never regress Top‑5.

**Prompt (triage, Max):**
> Read every file in `review/`. Produce one consolidated, deduped backlog with
> severity S0–S3 (S0 = risks the Top‑5/hard contract), each item: title, file:line,
> contract clause, root cause, proposed fix, expected score impact, confidence,
> and a regression‑test idea. Order by severity then score‑impact×confidence. Do
> not edit code yet — output `review/FINDINGS.md`.

**Prompt (fix loop, High, one item at a time):**
> Implement backlog item <ID> from `review/FINDINGS.md` only. Make the minimal
> focused edit in the correct `legacy_parts/` module (per AGENTS.md), then run
> `pytest -q tests/unit` and `python utils/regression_checker.py --fresh-eval
> --detailed --show-violations`. Report the score delta vs `review/WP0_baseline.md`.
> If Top‑5 non‑exempt misses rise above 0 or the score regresses, revert and
> explain. Do not start the next item until I confirm.

---

## 5. Recommended execution schedule

| Step | Packages | Tier | Parallelizable? |
| :--- | :--- | :--- | :--- |
| 1 | WP0 baseline | Medium | — (run first) |
| 2 | WP1, WP10, WP11 | High/Med | Yes — 3 background subagents |
| 3 | WP2, WP6 | Extra High | Yes — 2 subagents |
| 4 | WP4, WP7, WP8, WP9 | High | Yes — 4 subagents |
| 5 | WP3, WP5 | **Max** | Run focused, not parallel; these need full attention |
| 6 | WP12 triage | **Max** | — |
| 7 | WP12 fixes | High | Sequential, regression‑gated |

> Each subagent should be told: *read‑only*, cite `file:line`, map findings to the
> specific BRAIN/SKULL clause, and write to its `review/WP*.md`. Keep the `review/`
> folder out of commits (per AGENTS.md, scratch/reports stay local; `artifacts/`
> is git‑ignored — you can put `review/` there if you prefer).

---

## 6. Definition of done

- Every WP file exists in `review/` with concrete `file:line` findings.
- `review/FINDINGS.md` lists all issues, severity‑ranked, with proposed fixes.
- All S0/S1 items fixed and verified; `non_exempt_top5_misses == 0` on every week.
- Final regression report shows score ≥ WP0 baseline on every week (ideally higher),
  with the deltas explained.
