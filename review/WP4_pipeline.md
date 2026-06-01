# WP4 — Pipeline Ordering & Phase-D Guards (READ-ONLY AUDIT)

**Scope:** `core/scheduler/pipeline.py` — `schedule_all`, `_safe_phase_d_step`,
`_immediate_gap_fix_if_needed`, `_count_top10_in_schedule`, and the terminal
repair/audit loops (lines ~485–553).
**Contract:** `config/BRAIN.md` §5 (phase order), §1/§2 (Top-5 hard contract),
§6 (excess-day / cluster-gap definitions).
**Method:** Verified the MRO in `core/constrained_scheduler.py:43-60` to resolve
which body executes for each call; traced guard helpers in
`placement_and_state.py`, `gap_fill_and_stats.py`, `clustering_and_optimization.py`,
`preference_and_limited.py`; confirmed `ScheduleEntry` is frozen
(`core/models.py:152`).

---

## Summary table

| # | Area | Verdict | Severity | File:line |
| :-- | :--- | :--- | :--- | :--- |
| 1 | Phase order vs BRAIN §5 (A.1→A.3→A.4→A.6→A.7→A.5→A.2→A.12; B; C; D; final) | **Correct** | — | `pipeline.py:204-571` |
| 2 | `_record_…` / exit-gate presence | **Correct** (B.5 intentionally none) | — | `pipeline.py:205-571` |
| 3 | `_safe_phase_d_step` snapshot/restore symmetry | **Correct** | — | `pipeline.py:127-166` |
| 4 | `_safe_phase_d_step` rollback thresholds (Top-5/Top-10/excess/gaps) | Correct **per step**; Top-10 tolerance not cumulative | **S2** | `pipeline.py:145-162` |
| 5 | D.11 runs `guard_top10=False, guard_soft_metrics=False` | Only Top-5 guarded; can shed Top-10 | **S2** | `pipeline.py:448-453` |
| 6 | Unguarded D.1 cannot drop preferred activity | **Confirmed** (and effectively inert on full board) | S3 | `preference_and_limited.py:913-971` |
| 7 | Unguarded D.5 cannot drop preferred activity | **Confirmed** (same-troop slot exchange) | S3 | `clustering_and_optimization.py:137-270` |
| 8 | Unguarded D.6 cannot drop preferred activity | **Confirmed** (relocates Reflection anchor only) | S3 | `clustering_and_optimization.py:1474-1578` |
| 9 | Terminal loops cannot infinite-loop / leave gaps | **Confirmed** (straight-line; ends on `_guarantee_no_gaps`) | — | `pipeline.py:485-553` |
| 10 | Terminal cluster-repair blocks omit Top-10 guard | Can shed a Top-10 with no rollback | **S2** | `pipeline.py:505-519, 529-543` |
| 11 | Final acceptance gate is fail-closed | **Confirmed** (raises if `final_top5 > 0`) | — | `pipeline.py:554-564` |
| 12 | Cut steps A.8–A.11, A.14, B.4 are dead | **Confirmed** zero call sites; not half-wired | S3 (stale doc/dupes) | see #16 |
| 13 | `_optimize_friday_reflections` defined twice (shadowed body is dead) | MRO confusion | S3 | `preference_and_limited.py:913` vs `phase_d_cleanup.py:40` |

No **S0** (Top-5 hard contract is guarded at every mutating step and enforced
fail-closed by the final gate) and no **S1** (phase order matches BRAIN §5
exactly) were found.

---

## Detailed findings

### F1 — Phase order matches BRAIN §5 (PASS)
`schedule_all` executes the documented relocated order with every step's
snapshot present:

- A.1 `_schedule_friday_reflection` `pipeline.py:204-205`
- A.3 `_schedule_hc_dg_tuesday` `:209-210`
- A.4 `_schedule_three_hour_activities` `:214-215`
- A.6 `_schedule_sailing_optimize_all` `:222-223`
- A.7 `_schedule_delta_sailing_pairs` `:229-230`
- A.5 `_schedule_two_hour_activities_priority` `:236-237`
- A.2 `_schedule_super_troop` `:242-243`
- A.12 `_early_staff_area_clustering` `:247-248`
- Exit Gate A `_immediate_gap_fix_if_needed` + `phase-exit` snapshot `:251-252`

Phase B: B.1/B.1b/B.1c `:262-273`, B.2 `:277`, B.3 `:282`, B.5
`_build_commissioner_busy_map` `:286` (diagnostic — intentionally no snapshot,
matching BRAIN §5 "diagnostic/tracking"), B.6 `:290`, Exit Gate B `:294`, then
B.7 `:299` (correctly after the exit gate, per §5).

Phase C: C.1 `_schedule_day_requests()` `:308`. **Verified default is
`aggressive=False`** (`top5_and_swaps.py:413-414`), so C.1 is the non-aggressive
pass per §10.1. C.2 `:313`, C.3 `_schedule_preferences_range(5,20)` `:318`, C.4
`:325`, C.5 `:333`, C.6 `:342`, Exit Gate C `:350`. C.6b correctly relocated to
final verification `:566-570`.

Phase D: D.1 `:378`, D.2 `:383`, D.3 `:387`, D.4 `:391`, D.5 `:404`, D.6 `:417`,
D.7 relocated to a diagnostic at `:470-473`, D.8 `:426`, D.9 `:433`, D.10 `:440`,
D.11 `:448`. Final verification / acceptance gate `:455-571`. **No order
defect.**

### F2 — `_safe_phase_d_step` snapshot/restore is symmetric (PASS)
`pipeline.py:126-166`. The snapshot is taken at `:127` *before* the
`before_*` metrics and *before* `step_fn()`; every rollback branch
(`:149/153/157/161`) restores that same snapshot. The post-step gap fill
(`:138`) runs **inside** the boundary, so a destructive fill is rolled back with
the step. `_restore_scheduler_state` rebuilds `entries`, staff maps, and all
progress dicts/sets from the snapshot (`placement_and_state.py:152-166`), and
because `ScheduleEntry` is frozen (`core/models.py:152`) the shallow
`list(self.schedule.entries)` copy (`placement_and_state.py:140`) is a genuine
rollback — entries are only added/removed, never mutated in place. Staff
tracking is restored from the snapshot, so no stale-cache leak. **Symmetric and
correct.**

### F3 — Rollback thresholds correct per step; Top-10 tolerance is not cumulative (S2)
`pipeline.py:147-162`. The `elif` ladder enforces the right priority order:
Top-5 increase (`:147`) → >2 Top-10 loss (`:151`) → excess-day increase (`:155`)
→ cluster-gap increase (`:159`). `top10_lost = before_top10 - after_top10`
(`:145`) is the *combined* step+gap-fill delta, matching the docstring's
"globally". Thresholds match stated intent.

**Defect:** the Top-10 tolerance of `> 2` is applied **independently per guarded
step**. D.2, D.3, D.4, D.8, and D.9 are each separate `_safe_phase_d_step` calls
(`:383,387,391,426,433`), so each may legitimately shed up to 2 Top-10
placements without rollback. There is no run-level Top-10 budget, so cumulative
loss across the five guarded steps is unbounded (worst case up to ~10 Top-10
placements dropped while each individual step "passes").

*Failing scenario:* a week where D.2/D.3/D.4 each trade exactly 2 Top-10
placements (ranks 6–10) for excess-day reductions. Every step reports `OK`, but
6 Top-10 preferences are lost — a direct hit to the 450-point Preference bucket
(BRAIN §6) that no single guard or the final gate detects (the final gate checks
only Top-5).

### F4 — D.11 disables both Top-10 and soft guards (S2)
`pipeline.py:448-453` calls `_safe_phase_d_step("D.11 Final Cleanup",
self._comprehensive_final_cleanup, guard_top10=False, guard_soft_metrics=False)`.
Only Top-5 is guarded. The stated rationale (`:443-446`) is that soft clustering
metrics must not roll back hard overlap/dedup cleanup — reasonable for *soft*
metrics, but `guard_top10=False` also lets cleanup drop ranks 6–10 with no
rollback. The winning body is `placement_and_state.py:1566`
(`_comprehensive_final_cleanup` is also defined at `phase_d_cleanup.py:195`, but
`PlacementAndStateMixin` precedes `PhaseDCleanupMixin` in the MRO, so the
placement_and_state body executes).

*Failing scenario:* a dedup pass in final cleanup removes one of two entries it
considers "duplicate" where the removed entry was the troop's only copy of a
rank-8 preference; Top-5 is unaffected, so the step passes and the Top-10 loss is
permanent. Lower confidence than F3 because cleanup mostly removes true
overlaps, but the guard gap is real.

### F5 — Unguarded D.1 cannot drop a preferred activity (PASS; S3 note)
D.1 calls `_optimize_friday_reflections`, which resolves via MRO to
`preference_and_limited.py:913-971` (NOT the shadowed `phase_d_cleanup.py:40`).
The body only swaps **Reflection** (an anchor, never a preference) between two
troops, and only after `is_troop_free(slot2, troop1)` and
`is_troop_free(slot1, troop2)` both pass (`:948-953`); the actual move
(`_swap_reflection_slots`, `:994-1021`) re-adds via validated `add_entry` and
rolls back on failure. It never removes a non-Reflection entry. **Cannot drop a
preferred activity — confirmed.**

*S3 note:* because D.1 runs first in Phase D when the board is already 100% full,
both `is_troop_free` preconditions can essentially never hold (every Friday slot
is occupied), so D.1 is effectively inert at its pipeline position. Harmless, but
dead-ish optimization. The duplicate shadowed body (`phase_d_cleanup.py:40`) is
unreachable dead code (finding F13).

### F6 — Unguarded D.5 cannot drop a preferred activity (PASS; S3 note)
`_optimize_friday_super_troop` (`clustering_and_optimization.py:137-270`)
performs a **same-troop slot exchange**: it builds `new_exclusive` at the fill's
slot and `new_fill` at the exclusive's slot (`:252-256`); both activities remain
scheduled, only their slots swap. Pair-protected Delta is skipped (`:191-192`)
and Sailing/Reflection are PROTECTED (`:164`). The exclusive activity's new slot
is validated via `is_activity_available` (`:235`) before commit. The pipeline
comment's claim (`:393-402`, "cannot remove a preferred activity") is
**accurate**.

*S3 note:* the fill activity's destination (the vacated `current_slot`) is **not**
re-validated before placement. Because movable fills are constraint-light and any
residual issue is swept by later `_fix_multislot_integrity` / `_guarantee_no_gaps`
/ `_comprehensive_final_cleanup`, this is cosmetic, not a preference-loss path.

### F7 — Unguarded D.6 cannot drop a preferred activity (PASS)
`_optimize_flexible_reflections` (`clustering_and_optimization.py:1474-1578`)
only relocates **Reflection** anchors: it removes the current Reflection entry
and re-adds via `add_entry` to a target Friday slot, rolling back immediately if
the add fails (`:1567-1570`). The only `entries.remove` target is a Reflection
entry; no preference is ever removed. **Confirmed safe.** (Like D.1, it is mostly
inert on a full board; any transient Friday gap it could create is repaired by
the later `_guarantee_no_gaps` calls.)

### F8 — Terminal repair/audit loops: no non-termination, no surviving gaps (PASS)
`pipeline.py:485-553` contains **no `while`/recursion** — it is a fixed,
straight-line sequence of audit + conditional cluster-repair blocks. Therefore
infinite-looping is structurally impossible at this level. Each block ends with
`_guarantee_no_gaps()` (`:499,510,523,534,548,552`); the very last gap operation
before the acceptance gate is `:552`, so the delivered schedule is gap-free.
Both conditional cluster-repair blocks are gated on `top5 == 0 and (excess > 0 or
gaps > 0)` (`:505,529`), and their rollback snapshots (`:501,525`) are taken
*after* a `_guarantee_no_gaps()`, so a restore returns to a gap-free state —
**snapshot/restore is symmetric here too.** `_finalize_filler_replacement_audit`
(`gap_fill_and_stats.py:1559-1720`) is internally Top-5/Top-10 guarded
(`:1674-1681`), so the audit passes cannot raise misses.

### F9 — Terminal cluster-repair blocks omit a Top-10 guard (S2)
`pipeline.py:514-518` and `:538-542` roll back only when **Top-5, excess, or
gaps increase** — Top-10 is never measured. The repair runs
`_aggressive_excess_day_reduction_swaps()` (winning body
`clustering_and_optimization.py:2453`, since `ClusteringAndOptimizationMixin`
precedes `SafetyAndExportMixin` in the MRO) and `_optimize_cluster_gaps_post_fill()`
followed by `_guarantee_no_gaps()`.

*Failing scenario:* the excess-day reduction displaces a rank-7 activity to
collapse an excess day; `_guarantee_no_gaps` backfills the vacated slot with a
generic filler. Top-5 = 0, excess decreased, gaps not increased → **not rolled
back**, so a Top-10 placement is permanently lost (450-bucket regression). The
first block (`:505-519`) has no compensating audit afterward; the second block's
non-rollback branch does re-run the Top-10-guarded filler audit (`:545-546`),
which only *partially* mitigates (it can re-place a dropped Top-10 only if a
filler now occupies a compatible slot). Recommend adding a Top-10 term to both
rollback predicates, consistent with `_safe_phase_d_step`.

### F10 — Final acceptance gate is fail-closed (PASS)
`pipeline.py:554-564`: `_validate_critical_constraints()` then
`final_top5, _ = self._count_non_exempt_top5_misses()`; if `final_top5 > 0` it
**raises `ValueError`** rather than returning a failed schedule. This measurement
occurs *after* the last `_guarantee_no_gaps()` (`:552`), so nothing mutates Top-5
between measurement and return. This satisfies BRAIN §1 rule 3 (fail-closed) and
the hard contract `non_exempt_top5_misses == 0`.

### F11 — Cut steps A.8–A.11, A.14, B.4 are dead, not half-wired (PASS; S3)
Confirmed each cut step has a body but **zero `self.<method>()` call sites**
anywhere in the repo:

- A.8 `_schedule_early_sailing_top10` `top5_and_swaps.py:1302`
- A.9 `_consolidate_sailing_same_day` `top5_and_swaps.py:1609`
- A.10 `_schedule_early_aqua_trampoline_top5` `top5_and_swaps.py:1031`
- A.11 `_guarantee_top1_beach` `top5_and_swaps.py:1090`
- A.14 `_schedule_thursday_sailing_largest_troop` `phase_a_foundation.py:273` &
  `top5_and_swaps.py:954`
- B.4 `_schedule_delta_early` `phase_b_core.py:198` & `preference_and_limited.py:2094`

`pipeline.py:199` references them only in a comment. **Not half-wired.**

*S3 notes:* (a) `_schedule_thursday_sailing_largest_troop` and
`_schedule_delta_early` each have **two** dead bodies (duplicate dead code);
(b) `sequencing_and_constraints.py:1766` carries a stale comment claiming
"`_schedule_thursday_sailing_largest_troop` phase which runs first" — it no
longer runs at all.

### F12 — Duplicate/shadowed Phase-D bodies (S3)
Beyond F5/F11, two pipeline-invoked names have shadowed duplicate definitions
resolved by MRO order (`constrained_scheduler.py:44-59`):
`_optimize_friday_reflections` (winner `preference_and_limited.py:913`; dead
`phase_d_cleanup.py:40`) and `_comprehensive_final_cleanup` (winner
`placement_and_state.py:1566`; dead `phase_d_cleanup.py:195`). Also
`_total_excess_cluster_days` (`gap_fill_and_stats.py:1539`, used by the filler
audit) and `_count_excess_cluster_days` (`placement_and_state.py:538`, used by
the guards/terminal repair) are two implementations of the same `ceil(n/3)`
definition. Functionally equivalent (each guard uses one consistently for
before/after), but the duplication is a maintenance hazard and a candidate for
WP8/WP10 consolidation.

---

## Executive summary

1. **Phase order is correct.** `schedule_all` matches BRAIN §5 exactly
   (A.1→A.3→A.4→A.6→A.7→A.5→A.2→A.12, then B, C, D, final), every `_record_…`
   snapshot/exit-gate is present (B.5 is intentionally diagnostic-only), C.6b is
   correctly relocated to final verification, and C.1 runs non-aggressive.
2. **No S0/S1.** The Top-5 hard contract is guarded at every mutating Phase-D
   step and enforced fail-closed by the final gate, which `raise`s on any
   non-exempt Top-5 miss (`pipeline.py:554-564`).
3. **`_safe_phase_d_step` is sound:** snapshot/restore is symmetric, the gap fill
   lives inside the boundary, the rollback `elif` ladder follows the BRAIN
   priority order, and `ScheduleEntry` immutability makes the shallow snapshot a
   true rollback.
4. **Unguarded D.1/D.5/D.6 cannot drop a preferred activity** — D.1/D.6 only
   relocate the Reflection anchor with validated adds + rollback, and D.5 is a
   same-troop slot exchange that keeps both activities. (D.1/D.6 are largely
   inert on a full board — harmless.)
5. **Terminal loops cannot infinite-loop or leave gaps:** they are straight-line,
   end on `_guarantee_no_gaps`, and their conditional repair blocks roll back
   symmetrically.
6. **Top-10 leakage is the recurring weakness (all S2):** the per-step `>2`
   Top-10 tolerance is not bounded run-wide (F3), D.11 disables the Top-10 guard
   entirely (F4), and the two terminal cluster-repair blocks omit a Top-10 guard
   (F9). None breaks Top-5, but each can silently erode the 450-point Preference
   bucket. Tightening these guards is the highest-value WP4 follow-up.
7. **Dead code is clean but messy (S3):** all cut steps (A.8–A.11, A.14, B.4) are
   truly unwired, but several have duplicate/shadowed bodies and one stale
   comment; consolidation is a quality (not correctness) item.
