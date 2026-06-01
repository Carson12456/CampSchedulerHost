# CampScheduler — Consolidated Findings & Prioritized Fix Backlog (WP12)

> Synthesis of `review/WP0–WP11`. Deduped across packages, severity-ranked, and
> ordered for a regression-gated fix loop.
>
> **Severity key:** **S0** = risks the Top-5 / hard contract (`non_exempt_top5_misses == 0`)
> · **S1** = wrong score or contract mismatch · **S2** = missed optimization / strategy
> · **S3** = quality / dead code.
>
> **Regression gate (WP0 baseline, 2026-05-29):** `pytest -q tests/unit` = 56 passed;
> `regression_checker --fresh-eval` = NO REGRESSIONS, Top-5 100% on all 10 weeks,
> avg week score **793.7**. Every fix must keep Top-5 = 0 misses and score ≥ baseline.

---

## Master backlog (ordered)

| ID | Sev | Title | Primary file:line | Conf | Source WPs |
| :-- | :-- | :--- | :--- | :-- | :--- |
| **F-01** | **S0** | HC/DG Tuesday-saturation exemption masks real non-exempt Top-5 misses | `core/services/unscheduled_source.py:37,106-110` | High | WP3-F1 |
| **F-02** | **S0** | Day-request displacement (Exemption-4) heuristic is wrong both ways | `core/services/unscheduled_source.py:67-87` | High | WP3-F2, WP5-F2 |
| **F-03** | **S0** | Canoe-duplication exemption ignores the "two-hour" qualifier | `core/services/unscheduled_source.py:39,124-130` | High | WP3-F3 |
| **F-04** | **S0** | `force_day_request` predicate bypasses capacity/availability checks; model add only partially saves it | `core/scheduler/legacy_parts/sequencing_and_constraints.py:859,934-944`; `core/models.py:212-387` | High | WP5-F1, WP2, WP5 second-pass |
| **F-04A** | **S0** | Post-seal mutators can undo honored day requests with no final re-seal | `pipeline.py:476-553`; `gap_fill_and_stats.py:1611-1652`; `placement_and_state.py:2179-2230` | High | WP5 second-pass |
| **F-05** | **S1** | Voyageur Commissioner% = 0.0 is a regression-metric bug (0 checks) | `utils/regression_checker.py:450-472` vs `state.py:56-59` | High | WP1-F12 |
| **F-06** | **S1** | Gaga Ball / 9 Square: hard-blocked in code, soft in BRAIN, unscored by judge | `sequencing_and_constraints.py:1896-1902`; SKULL `soft_prohibited_pairs` | High | WP1-F06, WP6-A |
| **F-07** | **S1** | Shower House "before wet/Super Troop": hard in BRAIN+scheduler, soft in judge | judge `regression_checker.py:769-787`; scheduler `:963-974` | High | WP6-E, WP2, WP0 |
| **F-08** | **S1** | Beach slot-2 use double-penalized (soft 10 + beach 3) | `regression_checker.py:601-631,1234-1238` | High | WP6-D |
| **F-09** | **S1** | Judge has no generic `soft_prohibited_pairs` loop → pairs silently unscored | `regression_checker.py:44-106,665-709,789-800` | High | WP6 (#4) |
| **F-10** | **S1** | D.8 `_force_cluster_consolidation` skips `_can_schedule` → undetected Delta+Tower/ODS adjacency (§4) | `clustering_and_optimization.py:1915-1962` | Med | WP7-3 |
| **F-11** | **S1** | §11 Delta/Sailing pair protection missing in recovery, final repair, and D.9 passes | `top5_and_swaps.py:2732`; `placement_and_state.py:2781,3097`; `gap_fill_and_stats.py:3430`; `safety_and_export.py:861` | Med-High | WP3-F4, WP7-2, WP3 second-pass |
| **F-12** | **S1** | `tower_extended_size` orphan; Tower 2-slot hardcoded `scouts > 15` | `core/models.py:207-209` | High | WP1-F01, WP1-F13 |
| **F-13** | **S1** | D.3→D.11 "FORCED→repaired" contract is inaccurate (doc/contract) | `pipeline.py:367-369,387,448`; `placement_and_state.py:1566` | Med | WP7-4 |
| **F-14** | **S1** | Anchor-blocked Thursday opt-out aborts whole run (should tolerate per §10.5) | `placement_and_state.py:1979-1987`; `top5_and_swaps.py:561-565` | Med | WP5-F5 |
| **F-15** | **S1** | Flask grid routes + IO loaders crash on missing/malformed data | `web/gui_web.py:1321-1802,1117-1156,217-228`; `core/io_handler.py:7-8,85` | High | WP10 |
| **F-16** | **S2** | Staff-variance optimizer exists but is never called | `regression_checker.py:1250-1254`; `_optimize_staff_variance` (uncalled) | High | WP6, WP0 |
| **F-17** | **S2** | Run-wide Top-10 leakage: per-step `>2` tolerance, D.11 + terminal repairs unguarded | `pipeline.py:145-162,448-453,505-543` | Med | WP4-F3/F4/F9 |
| **F-18** | **S2** | Sailing same-day consolidation / full-day metrics penalized but untargeted | `regression_checker.py:1185-1191`; `_consolidate_sailing_same_day` (orphan A.9) | Med | WP6, WP10 |
| **F-19** | **S2** | A.6 Thursday Sailing pick can forfeit Delta/Sailing pairing | `top5_and_swaps.py:885-903` (dropped guard `:1007`) | Med | WP9-F9 |
| **F-20** | **S2** | Canoe-26 cap has two divergent paths (relax-gated, scouts-only vs scouts+adults; Kayak ungated) | `sequencing_and_constraints.py:1308-1311,1461-1465` | Med | WP2 |
| **F-21** | **S2** | Reflection=Friday has no `_can_schedule` predicate (post-hoc count only) | `sequencing_and_constraints.py:654-660` (unused) | Med | WP2 |
| **F-22** | **S2** | `sailing_balls_fills` omitted from snapshot/restore (latent S1 if reordered) | `placement_and_state.py:137-166,2724`; `pipeline.py:570` | Med | WP8-F3, WP9 |
| **F-23** | **S2** | Canoe-triple under-count + orphan Fishing soft pairs in judge | `regression_checker.py:697-709`; SKULL Fishing pairs | Med | WP6-B, WP6-C |
| **F-24** | **S2** | Staff caps hardcoded (16/20/24) instead of SKULL `max_/target_staff_global` | `sequencing_and_constraints.py:812-819`; `gap_fill_and_stats.py:908` | Med | WP1-F08 |
| **F-25** | **S2** | Direct `entries` mutations skip `_rebuild_staff_tracking` (stale soft scoring) | `clustering_and_optimization.py`, `safety_and_export.py`, `preference_and_limited.py` (many) | Med | WP8-F4 |
| **F-26** | **S2** | `_fix_multislot_integrity` no staff/cache sync + ineffective slot re-add | `placement_and_state.py:1663-1850` | Med | WP8-F7 |
| **F-27** | **S2** | Orphan SKULL keys: `slot_rules`, `non_consecutive`, optimization toggles, `sailing_extended_size` | `config_loader.py`; SKULL | High | WP1-F02/F03/F04/F05 |
| **F-28** | **S2** | D.9 outlier commit bypasses `add_entry`; no internal per-move guard | `gap_fill_and_stats.py:3687-3702` | Med | WP7-6 |
| **F-29** | **S2** | GUI hardcodes SKULL data (area/staff/commissioner maps); divergent schedule loaders | `web/gui_web.py:1332-1350,1503-1519,65-145` | Med | WP10 |
| **F-30** | **S3** | Phase-stub modules MRO-shadowed (`phase_a_foundation`, `phase_b_core` never run, ~700 lines) | `constrained_scheduler.py:43-60` | High | WP10, WP4, WP3-F6 |
| **F-31** | **S3** | Shadowed `utilities._can_schedule` (weaker gate; latent S0 if MRO reorders) | `utilities.py:129-199` | High | WP2, WP8-F5, WP5-F6 |
| **F-32** | **S3** | `phase_d_cleanup.py` 100% dead; `pass` stubs misrepresent live D.11 | `phase_d_cleanup.py` (whole file) | High | WP7-5 |
| **F-33** | **S3** | Duplicate dead methods: `_ultra_aggressive_top5_recovery`, `_schedule_delta_sailing_pairs`, cut steps | `top5_and_swaps.py:3123/3256`; `phase_a_foundation.py:325`; cut bodies | High | WP3-F5, WP9-F6, WP4-F11, WP10 |
| **F-34** | **S3** | Root `psutil.py` stub shadows PyPI `psutil` when repo root on `sys.path` | `psutil.py:1-22` | High | WP10 |
| **F-35** | **S3** | Misleading docstrings/labels: "Delta 2 slots", "9-slot matrix", per-troop "§6 metric" | `phase_a_foundation.py:329`; `top5_and_swaps.py:907`; `validators.py:301-307` | High | WP9-F7/F10, WP7-7 |
| **F-36** | **S3** | Config foot-guns: divergent SKULL `cluster_areas`, consistency-checker gaps, dead `top5_miss_penalty` | `SKULL.json:839`; `check_brain_skull_consistency.py:58-85`; `regression_checker.py:158` | High | WP7-8, WP1-F09, WP6-G |
| **F-37** | **S3** | `compatibility_bridges.py` entirely dead + bare `except:` | `compatibility_bridges.py:23-168,118` | High | WP10 |
| **T-01..10** | test | Unit suite does not enforce the BRAIN hard contract (see Test Backlog) | `tests/unit/*` | High | WP11 |

---

## Implementation status (updated 2026-06-01)

> **Gate now:** `pytest -q tests/unit` = **67 passed**;
> `regression_checker --fresh-eval --detailed --show-violations` = **PASSED / NO
> REGRESSIONS**, **Top-5 100% / 0 non-exempt misses on all 10 weeks**, avg week
> score **793.4**, avg staff variance **3.09** (week7 was **7.68** at WP0).
> Every remaining violation is soft (within-contract).

### ✅ Done (24 findings + test scaffold)
- **S0 wall:** F-01, F-02, F-03, F-04, F-04A
- **S1:** F-05, F-06, F-07, F-08, F-09, F-10, F-11, F-12, F-13, F-14, F-15
- **S2:** F-16, F-19, F-20, F-21, F-22, F-23, F-24
- **Tests:** T-01 (F-02 exemption matrix, incl. negative cases), T-03 (F-04A
  protect + fail-closed audit), plus F-05/F-08/F-09 scoring-contract tests.

### ⬜ Remaining
- **S2 (score upside):** F-17 (run-wide Top-10 budget), F-18 (sailing same-day
  consolidation), F-25 (`entries` mutations skip `_rebuild_staff_tracking`),
  F-26 (`_fix_multislot_integrity` sync), F-27 (orphan SKULL keys —
  `slot_rules`/`non_consecutive`/optimization toggles/`sailing_extended_size`),
  F-28 (D.9 outlier commit bypasses `add_entry`), F-29 (GUI hardcodes SKULL data).
- **S3 (cleanup / dead code / docs):** F-30, F-31, F-32, F-33, F-34, F-35, F-36,
  F-37 — the dead-code files (`psutil.py`, `core/scheduler/phase_d_cleanup.py`,
  `legacy_parts/compatibility_bridges.py`, and the MRO-shadowed
  `phase_a_foundation.py` / `phase_b_core.py` stubs) are still present.
- **Tests:** T-02, T-04, T-05, T-06, T-07, T-08, T-09, T-10.
- **Tooling:** the new snapshot automations
  (`core/scheduler/snapshot_recorder.py`, `utils/generate_schedule_snapshots.py`)
  are wired and functional but not yet perf-optimized.

### Finishing fixes landed this pass (completing F-16)
- **F-16 wiring repair (was crashing the build):** the D.9b staff-variance step
  crashed `schedule_all()` for every week — the new
  `_balance_staff_loads(self, staff_entries, slot_counts, all_staff_activities)`
  in `clustering_and_optimization.py` (LegacyPart06) collided with the legacy
  `_balance_staff_loads(self)` in `gap_fill_and_stats.py` (LegacyPart05), which
  wins the MRO (`TypeError: takes 1 positional argument but 4 were given`).
  Renamed the F-16 helper to `_balance_staff_loads_across_slots`; D.9b now runs
  as a guarded Phase-D step that rolls back unless it strictly reduces
  staffed-slot load variance. `clustering_and_optimization.py`, `pipeline.py`.
- **Shower-House exclusive-slot reservation (latent regression from F-07):** the
  F-07 Monday-Shower-House block relocated *filler* Shower Houses onto Friday;
  because Shower House is an exclusive area they saturated the only open Friday
  slots and left `Samoset`'s MUST-HONOR Friday Shower House (tc_week7)
  unplaceable, aborting the run at the seal. Fix: a non-requested *filler*
  Shower House may not consume the exclusive Shower House slot on a day another
  troop has MUST-HONOR-requested Shower House — fillers always have
  alternatives, so the day's exclusive capacity is reserved for the requester.
  `sequencing_and_constraints.py`.

---

## S0 — Risk to the Top-5 / hard contract (fix first)

> These do **not** show up in the current WP0 run (all weeks pass Top-5) because the
> baseline weeks don't hit the triggering data shapes — but each can let a genuinely
> failing schedule be **accepted**, or abort a valid run. They are correctness landmines,
> not score deltas. Fix and add the matching regression test before anything else.

### F-01 (S0) — HC/DG Tuesday-saturation exemption masks real non-exempt Top-5 misses
- **File:** `core/services/unscheduled_source.py:37,106-110` (dup logic in dead `top5_and_swaps.py:3146-3152`).
- **Contract:** BRAIN §2 Exemption 2 — only the **top-3 of the combined HC+DG ranking** get the 3 Tuesday slots.
- **Root cause:** `hc_dg_tuesday_full` is pure slot-occupancy (`tuesday_hc_dg_slots >= {1,2,3}`). It (a) never checks ranking, so a rank-1 requester beaten by lower ranks is exempted; (b) treats HC+DG as one 3-slot pool when they are **two independent exclusive areas** (SKULL `exclusive_areas`), so up to 6 placements are possible — a troop missing DG while DG slots are free is wrongly exempted.
- **Fix:** Rank all HC/DG requesters (combined); exempt a miss only if it is outside the combined top-3 **and** no slot of its own activity (HC vs DG) is free on Tuesday.
- **Score impact:** None directly; **prevents false-accept** of a contract-failing schedule. Confidence High.
- **Regression test:** Construct a week where Tuesday slots 1/2/3 each hold HC, a troop ranks DG #1 with a free DG slot → assert `is_exempt(DG)==False` and the gate raises.

### F-02 (S0) — Day-request displacement (Exemption-4) heuristic is wrong both ways
- **File:** `core/services/unscheduled_source.py:67-87` (`_day_request_displaces_preference`).
- **Contract:** BRAIN §2 Exemption 4(b) / §10.2 T6 — exempt only when the honored day-request "occupies a slot the Top-5 would have needed."
- **Root cause:** Uses a pure rank comparison (`honored_rank > missing_rank`) with no day/slot relationship. **Over-loose (S0):** any low/unranked honored day-request (`get_priority`→999) blanket-exempts *every* higher-ranked Top-5 miss → masks real non-exempt misses → contract-failing schedule passes. **Over-strict (also S0):** when T6 legitimately displaces a better-ranked Top-5 to honor a request, that miss is counted non-exempt → the acceptance gate aborts an otherwise valid run.
- **Fix:** Only exempt when an honored day-request actually occupies a day/slot the missed Top-5 needed (or the missed activity is itself day-requested — already handled at `:41`).
- **Score impact:** None directly; restores correct accept/abort behavior. Confidence High. (WP3-F2 and WP5-F2 are the same defect from two angles.)
- **Regression test:** (a) Troop with honored unranked Friday-3 day-request + unrelated missing #1 → assert miss is **non-exempt**. (b) Troop whose better-ranked Top-5 was displaced by a T6-honored request → assert miss is **exempt** and run does not abort.

### F-03 (S0) — Canoe-duplication exemption ignores the "two-hour" qualifier
- **File:** `core/services/unscheduled_source.py:39,124-130`.
- **Contract:** BRAIN §2(c) — exemption applies only between **two-hour** canoe activities.
- **Root cause:** Checks canoe-family membership only; the family mixes 1-hour and 2-hour activities. Two co-fittable 1-hour canoe requests are wrongly treated as exempt duplication, masking a fixable Top-5 miss.
- **Fix:** Require both the scheduled and missed canoe activity to be two-hour (`slots >= 2` / duration ≥ 2).
- **Score impact:** None directly; prevents false-accept. Confidence High.
- **Regression test:** Troop ranks two 1-hour canoe activities, receives one → assert the missed one is **non-exempt**.

### F-04 (S0) — `force_day_request` predicate bypasses capacity/availability checks; model add only partially saves it
- **File:** `core/scheduler/legacy_parts/sequencing_and_constraints.py:859` (gate), `:934-944` (bypassed checks).
- **Contract:** BRAIN §10.3 — `force_day_request` may bypass only the listed soft checks; **physical exclusivity and capacity remain enforced**.
- **Root cause:** The CAPACITY-AWARE AVAILABILITY block (`_check_activity_capacity`, `is_activity_available`) is nested inside the same `and not force_day_request` branch as the beach soft rules, so `_can_schedule(..., force_day_request=True)` can return true for physically unavailable placements. The second pass corrected the blast radius: ordinary T3/T5/T6 adds still call `_add_to_schedule()` → `Schedule.add_entry()`, which re-checks model-level exclusivity and prevents a normal Archery-on-Archery double-book. The hard risk remains because aggregate canoe-family capacity is not enforced by `Schedule.add_entry()` / `is_activity_available()`, and the predicate is unsafe for any caller that trusts `_can_schedule(force=True)` as a complete feasibility answer. The solver also does not reliably distinguish "model rejected / globally unavailable" from a request that should be marked INFEASIBLE.
- **Fix:** Move the physical availability/capacity checks that must remain hard out of the `not force_day_request` block; explicitly keep aggregate canoe capacity enforced under force/relax; make failed force placements log INFEASIBLE rather than generic UNFULFILLED/abort. Add a canoe-capacity check to `_validate_critical_constraints`.
- **Score impact:** None directly; eliminates a run-abort and a silent hard violation. Confidence High.
- **Regression test:** `_can_schedule(..., force=True)` must not return true for a physically unavailable exclusive slot, or callers must prove they never trust it without `add_entry()`. Force a canoe over 26 across canoe-family activities → assert rejected.

### F-04A (S0) — Post-seal mutators can undo honored day requests with no final re-seal
- **File:** final seal `placement_and_state.py:1975-2032`; pipeline tail `pipeline.py:476-553`; filler audit `gap_fill_and_stats.py:1611-1652`; beach saturation fixer `placement_and_state.py:2179-2230`.
- **Contract:** BRAIN §10.1 / §5 — the aggressive day-request pass is supposed to be the terminal seal so honored MUST-HONOR requests are not undone later.
- **Root cause:** The aggressive seal runs inside `_final_comprehensive_validation`, but both that method and `schedule_all()` continue mutating afterward. Two current paths can remove honored requests: `_finalize_filler_replacement_audit()` can treat a day-requested filler such as `Campsite Free Time`, `Gaga Ball`, `9 Square`, `Trading Post`, `Shower House`, or `Sauna` as replaceable filler, and `_fix_beach_activity_saturation()` can remove/move a day-requested staffed beach victim after the seal. The final Top-5 gate does not revalidate day requests, so the schedule can pass while a MUST-HONOR request is gone.
- **Fix:** Add a final day-request revalidation after all post-seal mutators, or protect honored day-request entries from filler replacement / beach saturation fixes unless the request is explicitly reclassified INFEASIBLE. Prefer both: protect during mutation and fail closed with a final day-request audit.
- **Score impact:** None directly; prevents silent loss of authored day requests after the seal. Confidence High.
- **Regression test:** Day-request `Campsite Free Time` or `Shower House` so it is eligible for filler replacement; assert the complete returned schedule still honors it. Add a staffed beach day-request in an over-cap slot; assert it remains honored or is explicitly logged INFEASIBLE, not silently replaced.

---

## S1 — Wrong score / contract mismatch

### F-05 (S1) — Voyageur Commissioner% = 0.0 is a metric bug, not disabled grouping
- **File:** `utils/regression_checker.py:450-472` vs `core/scheduler/state.py:56-59`.
- **Root cause:** Troop JSON uses `"commissioner": "Voyageur A"`; the scheduler aliases `Commissioner X`→`Voyageur X` (grouping **is** active), but the checker only maps `Commissioner A/B/C`, so `commissioner_checks == 0` → `100.0*0/max(1,0) = 0.0`. WP0 shows 0.0 for both Voyageur weeks.
- **Fix:** Mirror the Voyageur alias in the checker (shared helper), or report `N/A` when `commissioner_checks == 0`.
- **Score impact:** Reporting only (commissioner% is advisory, not a scored bucket — see F-16 context). Confidence High.
- **Regression test:** Score a Voyageur week → assert commissioner% is computed over non-zero checks (not 0.0).

### F-06 (S1) — Gaga Ball / 9 Square: hard in code, soft in BRAIN, unscored by judge
- **File:** scheduler hard block `sequencing_and_constraints.py:1896-1902`; absent from SKULL `soft_prohibited_pairs`; judge never scores it.
- **Contract:** BRAIN §4.1 lists Balls (Gaga/9 Square) as a **soft** same-day pair.
- **Fix:** Add `["Gaga Ball","9 Square"]` to SKULL `soft_prohibited_pairs`, soften the scheduler block, and score it through the generic pair loop (F-09). (Or, if intentionally hard, update BRAIN.)
- **Score impact:** Frees the scheduler to place Balls same-day when beneficial; small soft-bucket effect. Confidence High. (Ties WP1-F06.)
- **Regression test:** Two Balls same day → assert one soft violation scored, no hard rejection.

### F-07 (S1) — Shower House "before wet/Super Troop": hard in BRAIN+scheduler, soft in judge
- **File:** judge `regression_checker.py:769-787` (soft); scheduler `sequencing_and_constraints.py:963-974` (hard, but **relax-gated + order-dependent**); BRAIN §4 (hard).
- **Root cause:** Three layers disagree. WP0 shows this as a recurring soft violation (weeks 5,6,7,voy3). Scheduler check only inspects already-placed later activities, so a wet/Super-Troop placed *after* Shower House isn't re-checked; relax passes can also place it.
- **Fix:** Pick one severity. If hard: promote judge to a hard invalidation, make the scheduler check relax-independent and bidirectional, add Monday-Shower-House to judge hard violations. If soft: downgrade scheduler+BRAIN consistently.
- **Score impact:** Resolves recurring violations on ~4 weeks; clarifies whether they are contract breaches or scored softs. Confidence High. (Ties WP2 + WP6-E.)
- **Regression test:** Shower House slot-1 then wet slot-3 same day → assert the chosen severity is enforced consistently in scheduler and judge.

### F-08 (S1) — Beach slot-2 use double-penalized
- **File:** `regression_checker.py:601-631,1234-1238`.
- **Root cause:** Non-Top5 beach slot-2 increments both `soft_violations` (10 pts) and `beach_slot_2_uses` (3 pts) = up to 13 pts/occurrence.
- **Fix:** Choose a single penalty channel per BRAIN §4.2 intent.
- **Score impact:** Removes inflated penalty; recovers up to ~10 pts per occurrence on affected weeks (WP0 avg beach-slot violations = 1.0/week). Confidence High.
- **Regression test:** Single non-Top5 beach slot-2 entry → assert exactly one penalty channel applies.

### F-09 (S1) — Judge has no generic `soft_prohibited_pairs` loop
- **File:** `regression_checker.py:44-106` (category-specific paths only).
- **Root cause:** Soft scoring uses ad-hoc category filters, not a single iteration over SKULL `soft_prohibited_pairs`; any pair outside those filters (Balls, Fishing) is silently unscored, and some are under/over-counted.
- **Fix:** Replace category paths with one SKULL-driven pair loop that scores each configured pair exactly once.
- **Score impact:** Makes the judge faithful to SKULL; prerequisite for F-06/F-23. Confidence High.
- **Regression test:** Add a pair to SKULL → assert it is scored once; remove ad-hoc duplication.

### F-10 (S1, borderline S0) — D.8 `_force_cluster_consolidation` skips `_can_schedule`
- **File:** `clustering_and_optimization.py:1915-1962` (D.8 step 3).
- **Contract:** BRAIN §4 — Delta+Tower/ODS never adjacent.
- **Root cause:** Moves `['Delta','Super Troop','Sailing','Climbing Tower','Aqua Trampoline']` via `is_troop_free` + `_add_to_schedule` only; `add_entry` does **not** enforce Delta/Tower adjacency, back-to-back, or global staff cap (those live in `_can_schedule`). The D.8 guard checks only Top-5/Top-10/excess/gaps, and D.11 doesn't repair adjacency, so a §4 hard violation can ship while still "passing" (gate only checks Top-5).
- **Fix:** Route the forced move through `_can_schedule` (relaxed for soft only), or add an adjacency repair to D.11 + the final normalizer.
- **Score impact:** Prevents an undetected hard violation; rated S1 only because it needs the offender on >2 days and landing adjacent. Confidence Med.
- **Regression test:** Force-consolidate a Tower into a slot adjacent to that troop's Delta → assert rejection or post-pass repair.

### F-11 (S1/S2) — §11 Delta/Sailing pair protection missing in recovery, final repair, and D.9
- **Files:** `_enforce_mandatory_top5` `top5_and_swaps.py:2732` + helpers `placement_and_state.py:2782,2871,2907` (WP3-F4); final repair exposure in `_attempt_global_top5_repair_step` `placement_and_state.py:3097-3115` and `_bounded_top5_reoptimization` helper calls `top5_and_swaps.py:99-147` (WP3 second pass); D.9 `gap_fill_and_stats.py:3430` `_optimize_outlier_activities` and `safety_and_export.py:861` `_optimize_commissioner_day_ownership` (WP7-2).
- **Contract:** BRAIN §11 — pair protection "implemented in all Top 1-5 recovery/enforcement loops" and pending in late Phase-D.
- **Root cause:** Delta is single-slot, so it is never in the multi-slot `PROTECTED` set; only the explicit `_is_pair_protected_delta` check protects a paired Delta, and it is **absent** from `_enforce_mandatory_top5`, the shared window-clear/reclaim helpers, final global Top-5 repair helpers, and the two D.9 passes. Because Delta isn't a cluster area, the Phase-D quality snapshot never measures pairing, so a broken pair is neither prevented nor rolled back. B.6 (the only re-pair) runs before D.9 and before final repair.
- **Fix:** Add `or self._is_pair_protected_delta(e)` to the `_enforce_mandatory_top5` filter and the helpers; add the same guard to `_attempt_global_top5_repair_step`, `_bounded_top5_reoptimization` helper paths, and the two D.9 passes; add a Delta/Sailing pairing term to `_schedule_quality_snapshot`.
- **Score impact:** BRAIN §11 quantifies the late-phase gap at **−0.40 avg excess days / +10.6 avg week score**. Confidence Med-High.
- **Regression test:** Troop with paired Sailing+Delta missing a Top-5 → assert recovery, final repair, and D.9 do not split the pair.

### F-12 (S1) — `tower_extended_size` orphan; Tower 2-slot hardcoded; inconsistent headcount
- **File:** `core/models.py:207-209` (Tower uses `scouts > 15`); `sequencing_and_constraints.py:1019` (Shotgun uses `scouts+adults > 15`); SKULL `tower_extended_size:15` never read.
- **Contract:** BRAIN §4 capacity / §7 large-troop.
- **Root cause:** SKULL value is exposed by `get_capacity_limits()` but never called; two different headcount definitions for "large troop."
- **Fix:** Read `tower_extended_size` from SKULL; standardize the large-troop headcount (scouts vs scouts+adults) per BRAIN.
- **Score impact:** Correct extended-slot sizing on large troops; low-frequency but real. Confidence High.
- **Regression test:** 16-scout troop → assert Tower occupies 2 slots; threshold sourced from SKULL.

### F-13 (S1, doc/contract) — D.3→D.11 "FORCED→repaired" contract is inaccurate
- **File:** `pipeline.py:367-369,387,448`; real D.11 `placement_and_state.py:1566`.
- **Root cause:** D.3 (`_force_clustering_consolidation`) actually validates via `_can_schedule(relax)`+`add_entry`, so it creates no hard violations — there is nothing for D.11 to repair; the genuine bypass is D.8 (F-10). D.11 also runs `guard_top10=False` and is rolled back on Top-5, so it can't be relied on as the repair net.
- **Fix:** Correct the comments/BRAIN §5 D.3 note; document the real safety net (`_final_comprehensive_validation`); pair with F-10.
- **Score impact:** None (documentation/accuracy), but prevents reasoning errors in future fixes. Confidence Med.

### F-14 (S1) — Anchor-blocked Thursday opt-out aborts the whole run
- **File:** `placement_and_state.py:1979-1987` (seal raises on any `unfulfilled`); `top5_and_swaps.py:561-565`.
- **Contract:** BRAIN §10.5 — anchor blockage is "architecturally unavoidable," logged UNFULFILLED and tolerated.
- **Root cause:** The seal raises on any `unfulfilled` entry, including the architecturally-impossible anchor-blocked opt-out, failing the whole week's generation.
- **Fix:** Distinguish `infeasible/anchor-blocked` (tolerate + log) from genuinely `unfulfilled` (raise).
- **Score impact:** Prevents spurious whole-week failures on certain inputs. Confidence Med.
- **Regression test:** Troop with Thursday Super Troop + Thursday `Back of the Moon` day-request → assert run completes with an UNFULFILLED log, not a raise.

### F-15 (S1, robustness — non-contract) — Flask routes + IO loaders crash on bad data
- **File:** `web/gui_web.py:1321-1802` (grid routes, no null guard on `get_week_data`), `:1117-1156` (regenerate, no try/except), `:217-228,291-295` (snapshot loaders); `core/io_handler.py:7-8,85` (`KeyError` on malformed JSON).
- **Root cause:** Missing null/exception guards; `get_week_data` can return `None`.
- **Fix:** Shared `_require_week_data(week)` 404 guard; wrap `generate_schedule`; validate IO schema with `ValueError`.
- **Score impact:** None on scoring; eliminates 500s / unhandled exceptions in the GUI. Confidence High.
- **Regression test:** Request a grid route with an invalid week/snapshot id → assert a clean 404/JSON error, not a stack trace.

---

## S2 — Missed optimization / strategy (score upside)

> These are where the **optimal-strategy** points live. WP0's low weeks (week7 717, week5 724,
> week6 728) are dragged by clustering and staff variance (week7 StVar 7.68).

- **F-16 — Staff-variance optimizer never called.** `_optimize_staff_variance` exists but no phase invokes it; C.2 is consecutive clustering, not variance. Staff bucket = 100 pts; week7 StVar 7.68. **Highest single score opportunity.** Wire it into a guarded Phase-D step (or drop the penalty). Conf High.
- **F-17 — Run-wide Top-10 leakage.** Per-step `>2` Top-10 tolerance isn't bounded across D.2/D.3/D.4/D.8/D.9; D.11 runs `guard_top10=False`; terminal cluster-repair blocks omit a Top-10 guard. Up to ~10 Top-10 placements can erode the 450 bucket with no rollback. Add a run-level Top-10 budget + a Top-10 term to the terminal repair predicates. Conf Med.
- **F-18 — Sailing same-day consolidation untargeted.** Judge penalizes Sailing full-day + same-day pairing misses (250 bucket); `_consolidate_sailing_same_day` is orphaned (cut A.9). Wire a guarded consolidation pass or accept the penalty. Conf Med.
- **F-19 — A.6 Thursday Sailing forfeits Delta pairing.** Restore the dropped `if "Delta" in troop.preferences: continue` guard (`top5_and_swaps.py:1007`) so Thursday's single Sailing isn't given to a Delta-wanter. Conf Med.
- **F-20 — Canoe-26 two divergent paths.** Relax-gated + scouts-only (`:1308`) vs scouts+adults (`:1461`); `Troop Kayak` ungated under relax. Unify on one SKULL-driven scouts+adults cap that also applies on relax fills. Conf Med.
- **F-21 — Reflection=Friday has no `_can_schedule` predicate.** Add `if activity.name=="Reflection" and day!=FRIDAY: return False` (helper `:654` already encodes the rule). Conf Med.
- **F-22 — `sailing_balls_fills` not snapshotted.** Deep-copy it in snapshot/restore now (cheap), before any future move of C.6b inside a guard turns it into an S1 undercount. Conf Med.
- **F-23 — Canoe-triple under-count + orphan Fishing pairs.** Fold into the generic pair loop (F-09): score canoe pairs exactly once; decide Fishing pairs in/out of BRAIN. Conf Med.
- **F-24 — Staff caps hardcoded 16/20/24.** Source placement caps from SKULL `max_staff_global`/`target_staff_global`; document the elevated clustering cap as an explicit SKULL key if intentional. Conf Med.
- **F-25 — Direct `entries` mutations skip `_rebuild_staff_tracking`.** Bounded (hard caps re-sum fresh) but degrades soft staff scoring; route mutations through `_add_to_schedule`/`_remove_from_schedule` or rebuild after. Conf Med.
- **F-26 — `_fix_multislot_integrity` no sync + ineffective re-add.** Rebuild staff/caches and repair missing slots without relying on `add_entry`'s start-anchored `is_troop_free`. Conf Med.
- **F-27 — Orphan SKULL keys.** `slot_rules.*`, `non_consecutive`, `optimization.*` toggles, `sailing_extended_size` are loaded/defined but unread; either wire consumers or prune to remove false authority. Conf High.
- **F-28 — D.9 outlier commit bypasses `add_entry`; no per-move guard.** Route through `add_entry`/`_add_to_schedule` and add a per-move quality gate like the sibling D.9 pass. Conf Med.
- **F-29 — GUI hardcodes SKULL data + divergent schedule loaders.** Load area/staff/commissioner maps from `config_loader`; unify the two `load_schedule_from_json` variants in core IO. Conf Med.

---

## S3 — Quality / dead code (do during or after fixes; some are latent S0)

- **F-30 — Phase-stub modules MRO-shadowed.** `phase_a_foundation.py` / `phase_b_core.py` bodies never execute (~700 lines); legacy_parts win. Confirm authoritative copy, then delete stubs or remove from MRO. (WP3-F6: the `phase_b_core` loops are *unsafe* versions — latent S0 if MRO ever reorders.) Conf High.
- **F-31 — Shadowed `utilities._can_schedule`.** Weaker gate with a cached-map hard reject; dead today, **latent S0** if MRO reorders. Delete or route to the canonical method. Conf High.
- **F-32 — `phase_d_cleanup.py` fully dead + misleading.** `pass` stubs imply D.11 is a no-op. Delete the module or demote to a thin re-export. Conf High.
- **F-33 — Duplicate dead methods.** `_ultra_aggressive_top5_recovery` (`top5_and_swaps.py:3123` & `:3256`, neither called; first `NameError`s), dead `_schedule_delta_sailing_pairs` (`phase_a_foundation.py:325`), dead cut-step bodies (A.8–A.11/A.14/B.4, some doubled). Delete. Conf High.
- **F-34 — Root `psutil.py` stub.** Shadows PyPI `psutil` when repo root is on `sys.path` (Flask adds it); no imports today but dangerous. Rename/move out of root or delete. Conf High.
- **F-35 — Misleading docstrings/labels.** "Delta takes 2 slots" (SKULL=1), "9-slot matrix" (only 8 sessions), per-troop predicate mislabeled "§6 metric." Correct the docs. Conf High.
- **F-36 — Config foot-guns.** Divergent unused SKULL `optimization.cluster_areas` (omits Archery); `check_brain_skull_consistency.py` skips `target_staff_global`/extended sizes; dead `top5_miss_penalty` knob. Align/prune. Conf High.
- **F-37 — `compatibility_bridges.py` dead + bare `except:`.** Entire `LegacyPart08Mixin` + analytics methods have zero callers; `:118` swallows all errors. Delete or narrow. Conf High.

---

## Test backlog (WP11) — add alongside the fixes above

Unit tests currently exercise primitives + a 3-troop smoke path; they **do not enforce** the
BRAIN hard contract (that lives in `regression_checker.py`, integration-level). Several
`test_constraint_system.py` cases (`:160-162,176-177,200-201`) even assert *permissive*
`add_entry` behavior, so scheduler regressions wouldn't fail them. Highest-value additions
(each doubles as the regression test for an S0/S1 above):

1. **T-01** `unscheduled_source` exemption matrix — parametrized, incl. negative `is_exempt==False` cases → guards **F-01/F-02/F-03**.
2. **T-02** Top-5 acceptance gate — a synthetic non-exempt miss must fail; repair drives misses→0.
3. **T-03** Day-request MUST-HONOR ladder T1–T6 + Thursday opt-out trio preservation + post-seal honored-request audit → guards **F-04/F-04A/F-14**.
4. **T-04** Delta↔Tower/ODS adjacency rejection, both directions, via `_can_schedule`.
5. **T-05** Completeness after `schedule_all()` — every troop, every slot (Thu 2-slot vs Fri 3-slot).
6. **T-06** HC/DG Tuesday-only rejection off-Tuesday.
7. **T-07** Cluster metrics — `ceil(n/3)` excess + `1,-,3` gap on constructed schedules.
8. **T-08** Scoring bucket caps sum ≤ 1000; `evaluate_week` raises on pref-vs-`unscheduled` mismatch → guards **F-08/F-09**.
9. **T-09** Sailing placement-time slot-2 overlap (2 troops during search; final caps hold).
10. **T-10** Shower House Monday block + same-day ordering vs wet/Super Troop → guards **F-07**.

---

## Recommended fix order (regression-gated, one item per commit)

1. **Correctness wall (S0):** F-01 → F-02 → F-03 → F-04 → F-04A, each with its test (T-01/T-02/T-03). After each: `pytest -q tests/unit` + `python utils/regression_checker.py --fresh-eval --detailed --show-violations`; Top-5 must stay 0, score ≥ 793.7.
2. **Judge correctness (S1):** F-05, F-09 (then F-06, F-23), F-08, F-07 — fixes the score authority before tuning the scheduler to it.
3. **Contract integrity (S1):** F-11, F-10/F-13, F-12, F-14.
4. **Score upside (S2), highest first:** F-16 (staff variance) → F-17 (Top-10 budget) → F-18/F-19 (sailing) → remaining S2.
5. **Cleanup (S3):** F-30/F-31/F-32/F-33 (dead/latent-S0 code) first, then docs/config foot-guns. F-15 (GUI robustness) any time.

> After all S0/S1 land, re-baseline only intentionally:
> `python utils/regression_checker.py --fresh-eval --set-baseline --force-baseline`.
