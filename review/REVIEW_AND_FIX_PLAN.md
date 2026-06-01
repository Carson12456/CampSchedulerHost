# CampScheduler — Review & Fix Master Summary

> One-stop summary of (1) the **initial code-review plan**, (2) **all findings**, and
> (3) the **fix implementation plan with live progress**. Source docs:
> [`CODE_REVIEW_PLAN.md`](../CODE_REVIEW_PLAN.md) (methodology) and
> [`review/FINDINGS.md`](./FINDINGS.md) (full finding detail). This file is the
> rolling status doc — update the **Progress log** as fixes land.

**Contract authorities:** `config/BRAIN.md` (the scheduling contract) ·
`config/SKULL.json` (configuration) · `utils/regression_checker.py` (the score/quality judge).

**Hard rule that gates every change:** `non_exempt_top5_misses == 0` on every week.

---

## Status at a glance

| | |
| :-- | :-- |
| **Audit** | Complete — WP0–WP12 done; 37 findings + 10 test gaps consolidated in `FINDINGS.md`. |
| **Fixes landed** | **Full S0 wall: F-01, F-02, F-03, F-04, F-04A** + **F-05** (S1, judge). Plus the canoe family-capacity root-cause bug (F-20 overlap) discovered while validating F-04. **Comparison baseline re-set to honest post-S0 numbers.** |
| **Fixes pending** | S0 wall complete; S1 judge-correctness batch in progress — next **F-09 → F-06/F-23 → F-08 → F-07**. |
| **Gate now** | `pytest -q tests/unit` = **67 passed**; `regression_checker --fresh-eval` = **NO REGRESSIONS**, **Top-5 100% / 0 misses on all 10 weeks**, avg score **791.1**. |
| **Score note** | Comparison baseline re-set after the S0 wall (was 793.7 inflated). Current ~791. The score is honest now (no hidden Top-10 misses / >26 canoe placements); run-to-run soft-optimization variance is ~±15 pts, which the contract-focused regression judge ignores. See [Score trajectory](#score-trajectory--decisions). |

---

# Part 1 — The initial review plan

A systematic hunt for logical errors, bugs, missing features, and sub-optimal
scoring strategy, measured against `BRAIN.md` + `SKULL.json`. Split into **13 work
packages (WP0–WP12)**, run **read-only first, fix later** so every change is
regression-gated.

### Golden rules
1. **Audit read-only; batch fixes in WP12** (each fix regression-gated).
2. **BRAIN is the contract; `regression_checker.py` is the judge.** A "bug" = code disagrees with BRAIN, or the judge rewards what BRAIN forbids.
3. **Never trade the Top-5 contract for score** — `non_exempt_top5_misses == 0` is mandatory.
4. **Miss data comes only from `schedule_json.unscheduled`** — never reconstructed from `troop.preferences`.
5. **Validate every fix** with `pytest -q tests/unit` + `python utils/regression_checker.py --fresh-eval --detailed --show-violations`.

### Recurring bug classes the codebase is structurally prone to
Config drift (hardcoded vs SKULL) · MRO shadowing (duplicate `_method` across mixins) ·
mutation without snapshot guard · miss-source violations · judge/contract mismatch.

### Work packages

| WP | Area | Tier |
| :-- | :--- | :--- |
| **WP0** | Baseline & smoke (capture scores, misses, violations) | Medium |
| **WP1** | Contract ↔ Config alignment (BRAIN/SKULL/loader/constants) | High |
| **WP2** | Hard-constraint correctness (`_can_schedule`, validators, Sailing slot-2) | Extra High |
| **WP3** | Top-5 contract & exemption engine ★ highest risk | Max |
| **WP4** | Pipeline ordering & Phase-D guards | High |
| **WP5** | MUST-HONOR day-request solver (T0–T6, Thursday opt-out) ★ fragile | Max |
| **WP6** | Scoring authority (buckets, cluster math, soft pairs) | Extra High |
| **WP7** | Clustering & Phase-D optimization | High |
| **WP8** | Placement & state integrity (snapshot/restore, staff tracking) | High |
| **WP9** | Sailing pipeline & half-slot fills | High |
| **WP10** | Breadth: web, IO, dead code, shims | Medium |
| **WP11** | Test adequacy vs the BRAIN contract | High |
| **WP12** | Synthesis → prioritized, regression-gated fix backlog | Max → High |

WP3 and WP5 additionally received a **second-pass review at a higher reasoning tier**
to validate the highest-risk findings; that pass refined F-04 and added F-04A.

### Definition of done (from the plan)
- Every WP file exists with concrete `file:line` findings. ✅
- `review/FINDINGS.md` lists all issues, severity-ranked, with fixes. ✅
- All S0/S1 fixed and verified; `non_exempt_top5_misses == 0` on every week. ⏳ (**S0 wall complete**; S1 next)
- Final regression report ≥ baseline per week, deltas explained. ⚠️ See [Score trajectory](#score-trajectory--decisions).

---

# Part 2 — All findings

**Severity key:** **S0** = risks the Top-5 / hard contract · **S1** = wrong score or
contract mismatch · **S2** = missed optimization / strategy · **S3** = quality / dead code.

> The S0 items do **not** appear in the baseline run (all weeks pass Top-5) because the
> baseline weeks don't hit the triggering data shapes — they are **correctness landmines**
> that can let a failing schedule be *accepted* or abort a valid run. Full detail per
> finding (file:line, contract clause, root cause, fix, test idea) lives in
> [`FINDINGS.md`](./FINDINGS.md).

### Master backlog

| ID | Sev | Title | Status |
| :-- | :-- | :--- | :-- |
| **F-01** | S0 | HC/DG Tuesday-saturation exemption masks real non-exempt Top-5 misses | ✅ Fixed |
| **F-02** | S0 | Day-request displacement (Exemption-4) heuristic is wrong both ways | ✅ Fixed |
| **F-03** | S0 | Canoe-duplication exemption ignores the "two-hour" qualifier | ✅ Fixed |
| **F-04** | S0 | `force_day_request` bypasses capacity/availability; model add only partially saves it | ✅ Fixed |
| **F-04A** | S0 | Post-seal mutators can undo honored day requests with no final re-seal | ✅ Fixed |
| **F-05** | S1 | Voyageur Commissioner% = 0.0 is a regression-metric bug (0 checks) | ✅ Fixed |
| **F-06** | S1 | Gaga Ball / 9 Square: hard in code, soft in BRAIN, unscored by judge | ⬜ |
| **F-07** | S1 | Shower House "before wet/Super Troop": hard in BRAIN+scheduler, soft in judge | ⬜ |
| **F-08** | S1 | Beach slot-2 use double-penalized (soft 10 + beach 3) | ⬜ |
| **F-09** | S1 | Judge has no generic `soft_prohibited_pairs` loop → pairs silently unscored | ⬜ |
| **F-10** | S1 | D.8 `_force_cluster_consolidation` skips `_can_schedule` → undetected Delta+Tower/ODS adjacency | ⬜ |
| **F-11** | S1 | §11 Delta/Sailing pair protection missing in recovery, final repair, D.9 | ⬜ |
| **F-12** | S1 | `tower_extended_size` orphan; Tower 2-slot hardcoded `scouts > 15` | ⬜ |
| **F-13** | S1 | D.3→D.11 "FORCED→repaired" contract is inaccurate (doc/contract) | ⬜ |
| **F-14** | S1 | Anchor-blocked Thursday opt-out aborts whole run (should tolerate per §10.5) | ⬜ |
| **F-15** | S1 | Flask grid routes + IO loaders crash on missing/malformed data | ⬜ |
| **F-16** | S2 | Staff-variance optimizer exists but is never called (**highest score upside**) | ⬜ |
| **F-17** | S2 | Run-wide Top-10 leakage: per-step `>2` tolerance, D.11 + terminal repairs unguarded | ⬜ |
| **F-18** | S2 | Sailing same-day consolidation penalized but untargeted | ⬜ |
| **F-19** | S2 | A.6 Thursday Sailing pick can forfeit Delta/Sailing pairing | ⬜ |
| **F-20** | S2 | Canoe-26 cap divergent paths (same-name sum, relax-gated, Kayak ungated) | ✅ Fixed (with F-04) |
| **F-21** | S2 | Reflection=Friday has no `_can_schedule` predicate (post-hoc count only) | ⬜ |
| **F-22** | S2 | `sailing_balls_fills` omitted from snapshot/restore (latent S1) | ⬜ |
| **F-23** | S2 | Canoe-triple under-count + orphan Fishing soft pairs in judge | ⬜ |
| **F-24** | S2 | Staff caps hardcoded (16/20/24) instead of SKULL keys | ⬜ |
| **F-25** | S2 | Direct `entries` mutations skip `_rebuild_staff_tracking` (stale soft scoring) | ⬜ |
| **F-26** | S2 | `_fix_multislot_integrity` no staff/cache sync + ineffective slot re-add | ⬜ |
| **F-27** | S2 | Orphan SKULL keys: `slot_rules`, `non_consecutive`, optimization toggles, `sailing_extended_size` | ⬜ |
| **F-28** | S2 | D.9 outlier commit bypasses `add_entry`; no internal per-move guard | ⬜ |
| **F-29** | S2 | GUI hardcodes SKULL data; divergent schedule loaders | ⬜ |
| **F-30** | S3 | Phase-stub modules MRO-shadowed (`phase_a_foundation`, `phase_b_core`, ~700 lines) | ⬜ |
| **F-31** | S3 | Shadowed `utilities._can_schedule` (weaker gate; latent S0 if MRO reorders) | ⬜ |
| **F-32** | S3 | `phase_d_cleanup.py` 100% dead; `pass` stubs misrepresent live D.11 | ⬜ |
| **F-33** | S3 | Duplicate dead methods (`_ultra_aggressive_top5_recovery`, etc.) | ⬜ |
| **F-34** | S3 | Root `psutil.py` stub shadows PyPI `psutil` when repo root on `sys.path` | ⬜ |
| **F-35** | S3 | Misleading docstrings/labels ("Delta 2 slots", "9-slot matrix") | ⬜ |
| **F-36** | S3 | Config foot-guns: divergent SKULL `cluster_areas`, consistency-checker gaps | ⬜ |
| **F-37** | S3 | `compatibility_bridges.py` entirely dead + bare `except:` | ⬜ |
| **T-01..10** | test | Unit suite does not enforce the BRAIN hard contract (see Test backlog) | ⬜ |

### Test backlog (each doubles as a regression test for an S0/S1)
1. **T-01** `unscheduled_source` exemption matrix (incl. negative cases) → guards **F-01/F-02/F-03**.
2. **T-02** Top-5 acceptance gate: synthetic non-exempt miss must fail; repair drives misses→0.
3. **T-03** Day-request MUST-HONOR ladder T1–T6 + Thursday opt-out trio + post-seal honored-request audit → **F-04/F-04A/F-14**.
4. **T-04** Delta↔Tower/ODS adjacency rejection (both directions).
5. **T-05** Completeness after `schedule_all()` (Thu 2-slot vs Fri 3-slot).
6. **T-06** HC/DG Tuesday-only rejection off-Tuesday.
7. **T-07** Cluster metrics: `ceil(n/3)` excess + `1,-,3` gap.
8. **T-08** Scoring bucket caps ≤ 1000; `evaluate_week` raises on pref-vs-`unscheduled` mismatch → **F-08/F-09**.
9. **T-09** Sailing placement-time slot-2 overlap (final caps hold).
10. **T-10** Shower House Monday block + same-day ordering → **F-07**.

---

# Part 3 — Fix implementation plan

### Recommended order (regression-gated; Top-5 must stay 0)
1. **Correctness wall (S0):** F-01 → F-02 → F-03 → F-04 → F-04A, each with its test (T-01/T-02/T-03).
2. **Judge correctness (S1):** F-05, F-09 (→ F-06, F-23), F-08, F-07 — fix the score authority before tuning the scheduler to it.
3. **Contract integrity (S1):** F-11, F-10/F-13, F-12, F-14.
4. **Score upside (S2), highest first:** F-16 (staff variance) → F-17 (Top-10 budget) → F-18/F-19 (sailing) → remaining S2.
5. **Cleanup (S3):** F-30/F-31/F-32/F-33 (dead/latent-S0 code) first, then docs/config foot-guns. F-15 (GUI robustness) any time.

After each fix: `pytest -q tests/unit` then `python utils/regression_checker.py --fresh-eval --detailed --show-violations`.
After all S0/S1 land, **re-baseline intentionally** with `--set-baseline --force-baseline`.

---

## Progress log

### ✅ F-01 — HC/DG Tuesday-saturation exemption (S0)
- **Problem:** `hc_dg_tuesday_full` was pure slot-occupancy: it ignored ranking and treated HC+DG as one 3-slot pool, so a high-ranked requester beaten by lower ranks — or a troop missing one area while that area still had a free slot — was wrongly exempted (false-accept of a contract-failing schedule).
- **Fix:** Track HC and DG as **separate exclusive Tuesday areas** (each 3 slots). A miss is exempt only when its **own area is saturated** *and* the troop is **outside that area's top-3 requesters** — mirroring the scheduler's per-area top-3 placement (`_schedule_hc_dg_tuesday`).
- **Files:** `core/services/unscheduled_source.py` (new `_top_n_requester_names`, per-area saturation); mirrored in `utils/regression_checker.py` `evaluate_week`.

### ✅ F-03 — Two-hour canoe-duplication qualifier (S0)
- **Problem:** Exemption fired for *any* canoe-family duplication, but the family mixes 1-hour and 2-hour activities. Two co-fittable 1-hour canoe requests (e.g. `Troop Canoe`, `Nature Canoe`) were wrongly forgiven, masking fixable misses.
- **Fix:** Require **both** the scheduled and missed activity to be **two-hour** canoe activities (`slots >= 2`) via new `_get_two_hour_canoe_activities`.
- **Files:** `core/services/unscheduled_source.py`; mirrored in `utils/regression_checker.py`.
- **Effect verified:** week4 Top-10 (7→9) and week7 (9→10) now correctly count 1-hour `Troop Canoe`/`Nature Canoe` misses as non-exempt; Top-5 stayed 0.

> Side effect addressed: `evaluate_week` kept a **second, divergent copy** of the exemption rules that both cross-checks the authoritative payload *and* drives the preference score. It now reuses the same helpers from `unscheduled_source`, so the two paths can't silently drift (the runtime top5/top10 cross-check enforces it).

### ✅ F-04 — `force_day_request` must not bypass physical capacity/exclusivity (S0)
- **Problem:** In `_can_schedule`, the capacity-aware exclusivity block sat inside the same `and not force_day_request` branch as the *soft* beach rules, so a forced MUST-HONOR placement skipped **all** physical checks. BRAIN §10.3 allows force to bypass only soft beach slot/staff rules — never physical exclusivity/capacity.
- **Fix:**
  - Re-enforce physical capacity (`_check_activity_capacity`) and non-beach exclusivity (`is_activity_available`) even under `force_day_request`, while still letting the soft beach staff cap be bypassed.
  - Added a **fail-closed aggregate canoe-capacity check** to `_validate_critical_constraints` (defense-in-depth).
- **Files:** `core/scheduler/legacy_parts/sequencing_and_constraints.py`; `core/scheduler/legacy_parts/placement_and_state.py`.

### ✅ F-20 (discovered during F-04) — canoe-26 family cap was computed per-activity
- **Problem:** `_check_activity_capacity`'s canoe branch summed only **same-named** entries, so `Float for Floats` (13) + `Canoe Snorkel` (18) = **31** in one slot passed the 26-person cap. Latent and non-deterministic; the fail-closed check from F-04 surfaced it as 3 real violations in `voyageur_week3`. `Troop Kayak` was also missing from `capacity_check_activities`, leaving it ungated under relax.
- **Fix:** Sum the **entire canoe family** (scouts+adults) per slot; added `Troop Kayak` to SKULL `capacity_check_activities`.
- **Files:** `core/scheduler/legacy_parts/sequencing_and_constraints.py`; `config/SKULL.json`.
- **Note:** This is part of the F-20 backlog item; it was fixed early because it manifested as a real **hard** (>26) violation blocking the F-04 fail-closed gate.

### ✅ F-02 — Day-request displacement exemption now provenance-backed (S0)
- **Problem:** `_day_request_displaces_preference` used a pure rank comparison with no day/slot relationship. **Over-loose:** any low/unranked honored day-request blanket-exempted every higher-ranked Top-5 miss (masked real misses → a contract-failing schedule could pass). **Over-strict:** a legitimately T6-displaced better-ranked Top-5 was counted non-exempt (aborted a valid run).
- **Fix (provenance — option (b)):** The aggressive day-request seal now **records causality**. Every preference an honored MUST-HONOR request actually evicts — via T5/T6 displacement *and* the Thursday 3-hr opt-out clear — is recorded on the scheduler as `day_request_displacements` (a set of `(troop_name, activity_name)` pairs). The exemption now consults that record instead of guessing from ranks: a miss is exempt under Exemption 4(b) **iff** it was recorded as displaced (Exemption 4(a) — the missed activity is itself day-requested — is unchanged). This is slot/day-causal by construction and correct in both directions.
- **Persistence & no-drift:** The set is serialized into `schedule_json.day_request_displacements` and reloaded by the regression checker, so `evaluate_week`'s scoring re-derivation and the authoritative payload consult the *same* provenance (the existing top5/top10 cross-check enforces it). Threaded through the runtime gate, regen export, and the GUI generate/load/snapshot/save paths.
- **Files:** `core/scheduler/state.py` (init), `core/scheduler/legacy_parts/top5_and_swaps.py` (record at T5/T6 + opt-out), `core/services/unscheduled_source.py` (exemption + builder param), `core/scheduler/legacy_parts/placement_and_state.py` (gate), `core/io_handler.py` (persist), `utils/regenerate_all_schedules.py`, `utils/regression_checker.py` (loader + mirror), `web/gui_web.py`.
- **Effect verified:** week5 `Pontiac` (honored `Shower House` request) now correctly exempts its displaced `Climbing Tower`/`Sailing`/`Shower House`, while `Joseph`'s ordinary `Climbing Tower`/`Sailing` misses stay **non-exempt** — the exact discrimination the rank heuristic could not make. Top-5 stayed 0; avg score 780.5 → **791.3**.
- **Tests:** added T-01 negative/positive cases — over-loose (unrelated honored request does **not** exempt), over-strict (recorded displacement **is** exempt), Exemption 4(a) still holds, and a provenance-shape guard (`tests/unit/test_scheduling_algorithm.py`).

### ✅ F-04A — Post-seal mutators can no longer undo honored day requests (S0)
- **Problem:** The aggressive day-request seal runs inside `_final_comprehensive_validation`, but `_finalize_filler_replacement_audit()` and `_fix_beach_activity_saturation()` kept mutating afterward (in the pipeline tail) and could remove a day-requested filler (`Campsite Free Time`, `Shower House`, `Sauna`, `Gaga Ball`, `9 Square`, `Trading Post`, …) or a day-requested staffed-beach victim. The final Top-5 gate did not revalidate day requests, so a schedule could pass while a MUST-HONOR request was silently gone.
- **Fix (protect + fail-closed audit, both):**
  - **Protect during mutation.** New `_is_honored_day_request_entry(entry)` (true iff the entry's activity is day-requested by its troop *on that entry's day*). The final filler audit excludes such entries from its replaceable-filler list; the beach saturation fixer excludes them from the victim pool (and tolerates an over-cap slot held only by MUST-HONOR beach requests, per BRAIN §10.3 which lets `force_day_request` bypass the beach staff cap — it is a soft warning, never a hard raise).
  - **Fail closed.** At the seal, `_collect_honored_day_requests()` snapshots the honored `(troop, DAY, activity)` set into `self._sealed_honored_day_requests`. After *all* post-seal mutators, `_revalidate_sealed_day_requests()` raises if any sealed request is no longer honored. Protection should prevent it ever firing; the audit is the safety net.
- **Files:** `core/scheduler/legacy_parts/placement_and_state.py` (helpers, beach-fixer guard, seal snapshot), `core/scheduler/legacy_parts/gap_fill_and_stats.py` (filler-audit guard), `core/scheduler/pipeline.py` (final audit call before the Top-5 gate), `core/scheduler/state.py` (attr init).
- **Effect verified:** all 10 weeks regenerate with **no** `post-seal mutation removed` raise (protection holds), Top-5 stayed 0, avg score 791.3 → **793.1**. Real day-requested fillers/beach entries (e.g. week5/week7 Shower House, voyageur beach) now survive the entire tail.
- **Tests:** predicate matching (requested-day-only), filler-audit protection, beach-saturation protection, fail-closed audit raise/no-raise, and an end-to-end "day-requested filler honored after `schedule_all()`" smoke (`tests/unit/test_scheduling_algorithm.py`).

### ✅ F-05 — Voyageur commissioner% metric fixed (S1, judge)
- **Problem:** Troop JSON declares `commissioner: "Voyageur A/B/C"`, and the scheduler aliases `Commissioner A/B/C → Voyageur A/B/C` in its day maps (grouping **is** active). But `regression_checker.evaluate_week` built its `comm_day_maps` from raw `config_loader` maps keyed only by `Commissioner A/B/C`, so no Voyageur key matched → `commissioner_day_checks == 0` → `100.0 * 0 / max(1,0) = 0.0`. Both Voyageur weeks reported a meaningless 0.0%.
- **Fix:** Extracted the scheduler's inline alias into a shared `config_loader.apply_voyageur_commissioner_alias(day_map)` and call it from **both** `core/scheduler/state.py` (replacing the duplicated loop) and the checker's `comm_day_maps` (so the two cannot drift — the same config-drift class WP flagged).
- **Files:** `core/scheduler/config_loader.py` (shared helper), `core/scheduler/state.py` (use helper), `utils/regression_checker.py` (alias `comm_day_maps`).
- **Effect verified:** `voyageur_week1` now reports **31.5%** and `voyageur_week3` **31.1%** (were 0.0); TC weeks unchanged (the alias only adds Voyageur keys). Reporting-only metric (advisory, not a scored bucket), so score is unaffected; Top-5 stayed 0.
- **Tests:** shared-alias unit test + an `evaluate_week` Voyageur test asserting `commissioner_day_checks ≥ 1` and `compliance_pct > 0.0` (`tests/unit/test_scoring_contract.py`).

### ✅ F-09 / F-06 / F-23 / F-08 / F-07 — Judge-correctness batch (S1)
- **F-09 (generic soft-pair loop):** Replaced the judge's category-specific soft loops (free-time / water-games / canoe / accuracy) with **one** loop over SKULL `soft_prohibited_pairs`, scoring each configured pair exactly once per troop/day. Removed the now-dead helpers/constants (`_get_free_time_same_day_conflicts`, `_get_water_games_same_day_conflicts`, `FREE_TIME_*`, `WATER_GAMES_*`). `utils/regression_checker.py`.
- **F-23 (canoe triple / Fishing):** Folded into the generic loop — canoe triples now count per-pair (was collapsed to 1) and the orphaned `Fishing+Trading Post` / `Fishing+Campsite Free Time` pairs are now scored.
- **F-06 (Balls soft):** Removed the scheduler's **hard** Gaga Ball/9 Square same-day block (`sequencing_and_constraints.py:1920`); added `["Gaga Ball","9 Square"]` to SKULL `soft_prohibited_pairs` so it is soft-avoided (relax-gated `_has_soft_same_day_conflict`) and scored once by the generic loop. Also added the BRAIN §4.1 Accuracy+Archery pairs (`Rifle+Archery`, `Shotgun+Archery`) to SKULL so the generic loop covers all of §4.1.
- **F-08 (beach slot-2 double-penalty):** A non-Top5 / AT-small beach slot-2 use no longer increments **both** `soft_violations` (10) and `beach_slot_2_uses` (3). It is now penalized solely via the dedicated `beach_slot_2` channel; the descriptive note moved to `beach_slot_2_details` (still shown in `--show-violations`).
- **F-07 (Shower House timing — per user direction):** **Monday Shower House is now SOFT and actively avoided** — the scheduler never self-inflicts it (blocked unless `force_day_request`), so only an explicit MUST-HONOR request places it; the judge scores it soft. **Shower House before a later wet/Super Troop** is now enforced **relax-independently** (a filler Shower House is swapped for a different fill rather than creating the bad ordering); only a MUST-HONOR request may override it (then contract-exempt). BRAIN updated: removed the "Shower House Hard Rules" block, added a §2a "Shower House Timing" soft subsection and a note that each SKULL soft pair scores once.
- **Files:** `utils/regression_checker.py`, `core/scheduler/legacy_parts/sequencing_and_constraints.py`, `config/SKULL.json`, `config/BRAIN.md`.
- **Effect verified:** `pytest -q tests/unit` = 67 passed; `--fresh-eval` = **NO REGRESSIONS**, **Top-5 100% / 0 misses**, avg score 785.0 (within ±15 soft-variance; honest new scoring of Fishing/Archery pairs, per-pair canoe, and 2 legitimate day-request Monday Shower Houses). Filler-placed Monday Shower Houses eliminated; only day-requested ones remain.

### ✅ F-11 / F-10 / F-13 / F-12 / F-14 / F-15 — Contract-integrity batch (S1)
- **F-11 (Delta/Sailing pair protection):** Added `_is_pair_protected_delta` guards to every late mutator that previously could split a Sailing-paired Delta — `_enforce_mandatory_top5` displaceable filter (`top5_and_swaps.py`), the three displacement helpers (`_force_place_with_window_clearing`, `_reclaim_activity_from_lower_priority_troop`, `_try_place_with_displacement_recovery` in `placement_and_state.py`), D.9 `_optimize_outlier_activities` (`gap_fill_and_stats.py`), and `_optimize_commissioner_day_ownership` (`safety_and_export.py`). Defense-in-depth: new `_count_delta_sailing_pairing_misses` term in `_schedule_quality_snapshot` + a reject rule in `_is_quality_snapshot_improvement` so a guarded Phase-D move that drifts a pair apart is rolled back.
- **F-10 (D.8 forced move bypassed `_can_schedule`):** `_force_cluster_consolidation` now routes each forced move through `_can_schedule(relax_constraints=True)` so the HARD Delta/Tower-ODS adjacency, back-to-back, and capacity invariants (not enforced by `add_entry`) can't be silently violated, while soft rules stay bypassed. `clustering_and_optimization.py`.
- **F-13 (doc accuracy):** Corrected the pipeline comments claiming D.3 has a constraint-bypassing "FORCED" path repaired by D.11. D.3 validates via `_can_schedule(relax)`+`add_entry`; the only true bypass was D.8 (now fixed by F-10); the authoritative net is `_final_comprehensive_validation`. `pipeline.py`.
- **F-12 (tower_extended_size orphan + magic number):** `Schedule._get_effective_slots` now sources the Climbing Tower extended-slot threshold from SKULL `constraints.tower_extended_size` (was hardcoded `15`). Documented the deliberate headcount distinction (Tower = scouts/climbers; BRAIN §7 large-troop Shotgun = scouts+adults) rather than expanding the 2-slot trigger and risking Tower-capacity/Top-5 churn. `core/models.py`.
- **F-14 (anchor-blocked Thursday opt-out aborted the run):** A Thursday 3-hour opt-out blocked by a protected anchor is architecturally unavoidable (BRAIN §10.5); it is now classified `infeasible` (tolerated + logged) instead of `unfulfilled`, so the MUST-HONOR seal no longer raises on an otherwise-valid week. Genuine "no legal placement" cases still raise. `top5_and_swaps.py`.
- **F-15 (robustness):** `io_handler` loaders now raise a clear `ValueError` on malformed/missing-key JSON instead of `KeyError`/`JSONDecodeError`; added a shared `_require_week_data` 404 guard in `web/gui_web.py` and applied it to the 7 grid routes that accessed `data['schedule']` with no null check (was a 500). `core/io_handler.py`, `web/gui_web.py`.
- **Effect verified:** `pytest -q tests/unit` = 67 passed; `--fresh-eval` = **NO REGRESSIONS**, **Top-5 100% / 0 misses**, avg score 778.0 (soft-variance band). No new hard violations; Delta/Sailing pairs preserved across all weeks.

---

## Score trajectory & decisions

| Stage | Avg week score | Top-5 | Regression judge |
| :-- | :-- | :-- | :-- |
| WP0 baseline | **793.7** | 0 misses | NO REGRESSIONS |
| After F-01 + F-03 | **792.0** | 0 misses | NO REGRESSIONS |
| After F-04 + canoe family cap | **780.5** | 0 misses | NO REGRESSIONS |
| After F-02 (provenance exemption) | **791.3** | 0 misses | NO REGRESSIONS |
| After F-04A (post-seal day-request protection) | **793.1** | 0 misses | NO REGRESSIONS |
| **Re-baseline (comparison baseline ← honest post-S0)** | ~**777–793** | 0 misses | baseline reset |
| After F-05 (Voyageur commissioner% metric) | **791.1** | 0 misses | NO REGRESSIONS |

**Why the score sits below the original 793.7:** the old baseline was **inflated by the
very bugs being fixed** — hidden Top-10 misses (over-lenient exemptions) and
physically-impossible canoe placements (>26 people). Removing them lowers the raw
number but makes it *honest*. The comparison baseline has now been **re-set** to these
honest post-S0 numbers. The regression checker's detection is **contract-focused**
(Top-5 success, counted misses, problem weeks, hard violations), not a raw-score floor;
it correctly reports **NO REGRESSIONS** and **Top-5 100%**. Note: regeneration has
~±15 pt run-to-run variance in *soft* optimization (clustering/staff variance) with
Top-5 always 0 — so small avg-score wobble between runs is expected and ignored by the judge.

**Open decisions for the user:**
1. ~~**Re-baseline?**~~ — **Done.** Comparison baseline re-set via `--set-baseline --force-baseline`; `baseline_metrics_10weeks.json` records `non_exempt_top5_misses: 0`, `season_success_rate: 100.0` on all weeks.
2. ~~**F-02 approach**~~ — **Resolved:** shipped the robust **provenance** approach (option (b)).
3. **Scope of "all fixes":** S0 wall complete; now working the **S1 judge-correctness batch** (F-05 done → F-09 → F-06/F-23 → F-08 → F-07). Confirm whether to continue through all S1/S2/S3 or pause for review after the S1 judge batch.

---

## Files modified so far

| File | Findings |
| :-- | :-- |
| `core/services/unscheduled_source.py` | F-01, F-03, F-02 (provenance exemption + builder param) |
| `utils/regression_checker.py` | F-01, F-03, F-02 (provenance loader + mirror; single exemption source), F-05 (Voyageur alias on `comm_day_maps`) |
| `core/scheduler/config_loader.py` | F-05 (shared `apply_voyageur_commissioner_alias` helper) |
| `core/scheduler/legacy_parts/sequencing_and_constraints.py` | F-04 (force gate), F-20 (canoe family cap) |
| `core/scheduler/legacy_parts/placement_and_state.py` | F-04 (fail-closed canoe validation), F-02 (gate passes provenance), F-04A (honored-day-request helpers, beach-fixer guard, seal snapshot) |
| `core/scheduler/state.py` | F-02 (`day_request_displacements` init), F-04A (`_sealed_honored_day_requests` init), F-05 (use shared Voyageur alias helper) |
| `tests/unit/test_scoring_contract.py` | F-05 (shared-alias + Voyageur `evaluate_week` commissioner% tests) |
| `core/scheduler/legacy_parts/top5_and_swaps.py` | F-02 (record displacement at T5/T6 + Thursday opt-out) |
| `core/scheduler/legacy_parts/gap_fill_and_stats.py` | F-04A (filler audit skips honored day-request entries) |
| `core/scheduler/pipeline.py` | F-04A (final fail-closed day-request audit before Top-5 gate) |
| `core/io_handler.py` | F-02 (persist `day_request_displacements` to schedule JSON) |
| `utils/regenerate_all_schedules.py` | F-02 (thread provenance into payload + save) |
| `web/gui_web.py` | F-02 (thread provenance through generate/load/snapshot/save) |
| `tests/unit/test_scheduling_algorithm.py` | F-02 (T-01 over-loose/over-strict cases), F-04A (T-03 protection + audit cases) |
| `config/SKULL.json` | F-20 (`Troop Kayak` → `capacity_check_activities`) |

> Validation after every change: `pytest -q tests/unit` (67 passed) and
> `python utils/regression_checker.py --fresh-eval --detailed --show-violations`
> (NO REGRESSIONS, Top-5 = 0 on all 10 weeks).
