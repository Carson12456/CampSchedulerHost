# WP7 — Clustering / Excess-Day / Cluster-Gap Audit

**Scope (read-only):** `core/scheduler/legacy_parts/clustering_and_optimization.py`,
`core/scheduler/legacy_parts/gap_fill_and_stats.py`, `core/scheduler/phase_d_cleanup.py`,
`core/scheduler/validators.py:would_create_excess_day_for_entries`.
**Cross-referenced judge:** `utils/regression_checker.py` lines 330–418 (§6 excess-day + cluster-gap formulas).
**Contract:** BRAIN §6 (scoring math), §11 (Delta/Sailing pair protection — flagged PENDING), `non_exempt_top5_misses == 0`.

> Note on MRO: `ConstrainedScheduler` (`core/constrained_scheduler.py:43-60`) lists mixins
> with `PlacementAndStateMixin`/`ClusteringAndOptimizationMixin`/`GapFillAndStatsMixin`/`SafetyAndExportMixin`
> **before** `PhaseDCleanupMixin` (last). So the *real* D.x bodies are the legacy-part versions;
> `phase_d_cleanup.py` is fully shadowed (see WP7-5). Pipeline wiring: `core/scheduler/pipeline.py:376-453`.

## Summary

| ID | Area | Finding | Severity |
| --- | --- | --- | --- |
| WP7-1 | Metric alignment | `_count_excess_cluster_days` / `_count_area_cluster_gaps` / `would_create_excess_day_for_entries` exactly match the judge's §6 formulas and area set | **PASS** |
| WP7-2 | §11 Delta/Sailing | D.9 `_optimize_outlier_activities` + `_optimize_commissioner_day_ownership` lack `_is_pair_protected_delta`; the Phase-D guard cannot measure pairing → silent §3 "missed Delta/Sailing pairing" drift | **S1** |
| WP7-3 | D.8 force move | `_force_cluster_consolidation` bypasses `_can_schedule` (only `is_troop_free`+`add_entry`); `add_entry` does not enforce Delta+Tower/ODS adjacency, back-to-back, or global staff cap → can create §4 hard violation undetected by the metric guard | **S1** |
| WP7-4 | D.3 → D.11 contract | The documented "D.3 FORCED bypass repaired by D.11" is inaccurate: D.3 (`_force_clustering_consolidation`) does **not** force hard violations, and D.11's repair scope excludes adjacency/soft, so the stated repair contract does not actually hold for the real bypass | **S1** |
| WP7-5 | Dead/misleading code | `phase_d_cleanup.py` is 100% shadowed by earlier mixins; its placeholder `pass` cleanup bodies imply D.11 is a no-op, contradicting the live D.11 | **S3** |
| WP7-6 | D.9 outlier commit | `_optimize_outlier_activities` commits via raw `entries.remove/append`, bypassing `add_entry`; it is also the only D.9 sub-pass with no internal per-move quality guard | **S2** |
| WP7-7 | Per-troop metric label | `_would_create_excess_day(troop=…)` measures troop-local spread, not the judge's *global* excess; only a soft re-rank signal, but the docstring mislabels it "BRAIN §6 metric" | **S3** |
| WP7-8 | Config foot-gun | SKULL `optimization.cluster_areas` (`config/SKULL.json:839`) is a second, divergent area list neither the judge nor the gap metric uses (both use `area_clustering_priority` + ≥3-activity extension) | **S3** |

D.2 (`_comprehensive_clustering_optimization`), D.4 (`_ultra_aggressive_clustering`), and D.10
(`_optimize_cluster_gaps_post_fill`) were verified **SAFE** — see WP7-1 notes.

---

## WP7-1 — Internal metric == judge metric (PASS)

**Judge (`utils/regression_checker.py`):**
- Area set: `area_clustering_priority ∩ EXCLUSIVE_AREAS`, then extended with any area having ≥3 activities (lines 334-339). With current SKULL (`config/SKULL.json:822-826,626-662`) this resolves to `{Tower, Rifle Range, Archery, Outdoor Skills, Handicrafts}`.
- Excess days: `required_days = ceil(num_activities/3)`, `excess = max(0, len(days_used) - required_days)`, summed over all entries in the area (lines 343-362).
- Cluster gap: area-level `1,-,3` over `[MON,TUE,WED,FRI]` (Thursday excluded), `has_1 and has_3 and not has_2` (lines 389-406).

**Scheduler:**
- `gap_fill_and_stats.py:252-267` `_get_authoritative_gap_area_map()` reproduces the judge's area set with identical logic (priority ∩ areas, then ≥3 extension). ✅ same `{Tower, Rifle Range, Archery, Outdoor Skills, Handicrafts}`.
- `placement_and_state.py:538-559` `_count_excess_cluster_days()` — `ceil(len(entries)/3)`, `max(0, len(unique_days)-required_days)`, summed. **Byte-for-byte equivalent** to the judge.
- `placement_and_state.py:626-638` `_count_area_cluster_gaps()` — same `[MON,TUE,WED,FRI]`, same `has_1 and has_3 and not has_2`. **Equivalent.**
- `validators.py:33-58` `would_create_excess_day_for_entries()` — prospective form using the same area map (`validators.py:16-25`) and the same `ceil(new_total/3)` rule. Correct as a *would-adding* predicate.

**Verdict:** The metric the Phase-D guards optimize (`_safe_phase_d_step`, `pipeline.py:130-162`) is exactly the metric the judge scores. No drift. Verified that Delta is **not** a cluster area (single-activity, not in `area_clustering_priority`), so excess/gap math correctly ignores it.

---

## WP7-2 — §11 Delta/Sailing pair protection missing in D.9 (S1)

BRAIN §11 protects a Delta entry whose troop has Sailing scheduled via `_is_pair_protected_delta`
(`top5_and_swaps.py:382-402`) and lists "pair protection in late-phase D clustering and swap passes"
as **Pending**. Two live D.9 passes are exactly that gap:

1. **`gap_fill_and_stats.py:3430` `_optimize_outlier_activities` (D.9).**
   `PROTECTED = NON_DISPLACEABLE_ACTIVITIES | THREE_HOUR | {"Sailing"}` (lines 3450-3454).
   `NON_DISPLACEABLE` = mandatory anchors only, so **Delta is not protected** and there is **no
   `_is_pair_protected_delta` check**. Delta is single-slot, so it is flagged as an "only-on-day"
   outlier (lines 3507-3513) and moved to a clustering / gap-fill / consecutiveness day
   (Strategies 1-3, lines 3552-3685) — potentially **off Sailing's day**, breaking the pair.

2. **`safety_and_export.py:861` `_optimize_commissioner_day_ownership` (D.9).**
   `commissioner_activities` includes `"Delta"` (lines 877-884). Delta is removed from that set
   only if an *optional* `_get_family_day_policy("Delta/Sailing")` returns `protect_from_phase_d`
   (lines 889-900) — which is off in the default baseline (BRAIN §9). With the default policy,
   the pass actively **moves Delta to its fixed commissioner day** (`_get_activity_commissioner_day_fixed`,
   lines 926, 962-971); if Sailing landed on a different day during A.6 packing, the pair breaks.

**Why the guard cannot catch it:** Both passes run inside D.9's `_safe_phase_d_step`
(`pipeline.py:433-436`), whose soft-metric guard only watches `excess_cluster_days` and
`cluster_gaps` (`pipeline.py:155-162`), and the internal `_schedule_quality_snapshot`
(`placement_and_state.py:661-693`) counts excess/gaps/commissioner/wet/accuracy/tp/water-games/shower —
**not Delta/Sailing pairing.** Because Delta is not in any cluster area, breaking the pair changes
none of those metrics, so neither the outer rollback nor `_is_quality_snapshot_improvement` detects it.

**Measurable drift:** the judge penalizes a broken pair in §3 ("missed Delta/Sailing pairing",
BRAIN §6 line 234). The only re-pair net, `B.6 _enforce_delta_sailing_pairing`, runs in Phase B
(`pipeline.py:288-291`) — **before** D.9 — and is never re-run in FINAL VERIFICATION
(`pipeline.py:455-573`). BRAIN §11 itself quantifies the partial-coverage gap (−0.40 avg excess
days / +10.6 avg week score), confirming this is real, not theoretical. **S1.**

> By contrast, the clustering-module swaps DO honor the pair (`clustering_and_optimization.py:1890,
> 1942, 2014, 2143, 2251, 2545, 2565`), and D.10 cannot touch Delta (not a cluster-area edge),
> so the gap is specifically the two D.9 passes above.

---

## WP7-3 — D.8 `_force_cluster_consolidation` can create a §4 hard violation (S1)

`clustering_and_optimization.py:1915-1962` `_force_cluster_consolidation` (reached via D.8 →
`_optimize_activity_clustering` step 3, lines 1750 & `pipeline.py:424-429`) moves
`PROBLEMATIC = ['Delta','Super Troop','Sailing','Climbing Tower','Aqua Trampoline']` (line 1922)
using **only** `is_troop_free` + `_add_to_schedule` (lines 1949-1957) — it **never calls
`_can_schedule`** (unlike step 1/2, lines 1849, 1898).

`Schedule.add_entry` (`core/models.py:212-265`) enforces `is_troop_free`, exclusivity, and beach
caps, but does **not** enforce the Delta+Tower/ODS **non-adjacency hard rule** (BRAIN §4;
SKULL `config/SKULL.json:998-1002` "NEVER adjacent slots"), back-to-back, or the global staff cap —
those live only in `_can_schedule` (`sequencing_and_constraints.py:795-800, 825-827`). So a forced
move of `Climbing Tower` (or `Delta`) into a slot adjacent to that troop's Delta/Tower creates a
**§4 hard-constraint violation**.

D.8's `_safe_phase_d_step` guard checks Top-5/Top-10/excess/gaps only (`pipeline.py:147-162`) — it
does **not** detect adjacency — and D.11's repair set (WP7-4) handles same-slot exclusivity, not
adjacency, so the violation can survive into the delivered schedule. The acceptance gate only
enforces `non_exempt_top5_misses == 0` (`pipeline.py:554-564`), so such a schedule can still "pass."
Borderline S0 (hard contract), rated **S1** because it requires the offender to be on >2 days
(line 1933) and to land adjacent to the conflicting activity.

---

## WP7-4 — D.3 "FORCED → repaired by D.11" contract does not hold as documented (S1)

The pipeline comment (`pipeline.py:367-369`) and BRAIN §5 D.3 ("bypass path … relying on D.11
cleanup … to repair") attribute a hard-constraint bypass to D.3. In code:

- **D.3 = `_force_clustering_consolidation`** (`clustering_and_optimization.py:1965-2074`, wired at
  `pipeline.py:387`). Both its tiers gate on `_can_schedule(relax_constraints=True[, ignore_day_requests])`
  **then** `add_entry` (lines 2028-2038, 2054-2067). `relax_constraints=True` only drops *soft*
  checks (beach-slot pref, etc.); it does **not** drop adjacency/exclusivity/staff/multi-slot/duplicate
  (`sequencing_and_constraints.py:795, 825, 842, 943, 948`). So **D.3 produces no hard violations** —
  there is nothing for D.11 to "repair." The print label `[Force Cluster] … (relaxed+ignore_dr=…)`
  is the only "force," and it is bounded by `_optimization_may_ignore_day_requests` (never bypasses
  MUST-HONOR troops, `top5_and_swaps.py:404-411`). D.3 is additionally rolled back by its own
  `_safe_phase_d_step` if excess/gaps rise.
- The **genuine** constraint-skipping force is WP7-3's D.8 method, **not** D.3.

**Does D.11 always run after and repair?** Structurally yes — D.11 follows D.3 unconditionally
(`pipeline.py:387 → 448`). But the real D.11 (`placement_and_state.py:1566-1622`, **not** the
shadowed `phase_d_cleanup.py:195`) only runs: `_remove_activity_conflicts` (same-slot same-activity,
`clustering_and_optimization.py:896`), `_cleanup_exclusive_activities` (same-slot same-area,
`clustering_and_optimization.py:23`), `_remove_overlaps`, dedup, mandatory-anchor guarantee, gap
fill, beach-slot-2 fix, exclusivity sanitize. It does **not** repair Delta+Tower adjacency or any
soft constraint. Furthermore D.11 is wrapped with `guard_soft_metrics=False, guard_top10=False`
(`pipeline.py:448-453`) and is **rolled back if it raises Top-5 misses** — which would *undo* the
very repair it was relied on to perform (the following `_final_comprehensive_validation` is the real
safety net, not D.11). Net: the documented D.3↔D.11 repair contract is inaccurate, and for the real
bypass (WP7-3) the repair is **not** guaranteed. **S1 (contract/doc mismatch).**

---

## WP7-5 — `phase_d_cleanup.py` is entirely dead, and misleading (S3)

`PhaseDCleanupMixin` is **last** in the MRO (`constrained_scheduler.py:59`), so every one of its
methods is shadowed by an earlier mixin:

| `phase_d_cleanup.py` method | Live override |
| --- | --- |
| `_optimize_friday_reflections` / `_friday_clustering_score` / `_swap_reflection_slots` (40,96,116) | `preference_and_limited.py:913,973,994` |
| `_comprehensive_clustering_optimization` (153) | `placement_and_state.py:476` |
| `_comprehensive_final_cleanup` (195) | `placement_and_state.py:1566` |
| `_deduplicate_entries` (262) | `clustering_and_optimization.py:512` |
| `_guarantee_mandatory_activities` (279) | `clustering_and_optimization.py:1034` |
| `_fix_beach_slot_violations` (328) | `clustering_and_optimization.py:2839` |
| `_remove_activity_conflicts`/`_cleanup_exclusive_activities`/`_remove_overlaps`/`_fill_empty_slots_final`/`_ensure_hc_dg_pairing`/`_sanitize_exclusivity` (247-388, bodies = `pass`) | `clustering_and_optimization.py:896,23,616,1143`; `gap_fill_and_stats.py:1158`; `safety_and_export.py:1223` |

The danger is not just dead code: the in-scope file presents D.11's conflict/overlap/exclusivity
repairs as **`pass`** no-ops (`phase_d_cleanup.py:247-260,323-391`). A reviewer auditing the D.3→D.11
contract from this file would wrongly conclude D.11 repairs nothing. Recommend deleting the module or
demoting it to a thin re-export. **S3 (high-value clarity defect).**

---

## WP7-6 — D.9 outlier commits bypass `add_entry`; no internal guard (S2)

`gap_fill_and_stats.py:3687-3702` commits the chosen outlier move with raw
`self.schedule.entries.remove(entry)` + `entries.append(ScheduleEntry(...))`, bypassing
`add_entry`'s atomic/exclusivity re-validation and `_add_to_schedule`'s staff-cache update
(`placement_and_state.py:65-102`). It is mitigated because each candidate was pre-checked with
`_can_schedule(relax_constraints=True)` (lines 3574, 3625, 3668) and the schedule is unmodified for
that troop until commit; multi-slot is skipped (line 3486). But unlike the sibling D.9 pass
(`_optimize_commissioner_day_ownership`, which snapshots + `_is_quality_snapshot_improvement`-gates
every move) and D.10/offender-swaps, the outlier pass has **no internal per-move quality guard** — it
relies entirely on D.9's outer `_safe_phase_d_step`, and `_fill_vacated_slot` (line 3702) can change
metrics inside that boundary. Staff tracking is only rebuilt by the outer wrapper
(`pipeline.py:134,139`), so any intra-pass staff-aware decision runs on stale caches. **S2.**

---

## WP7-7 — Per-troop excess predicate mislabeled "§6 metric" (S3)

`validators.py:301-307` `_would_create_excess_day(activity, day, troop=…)` filters entries to a
single troop, so it measures **troop-local** area spread — not the judge's **camp-global** excess
(`regression_checker.py:343-362`). It is consumed only as a soft re-rank nudge
(`placement_and_state.py:391`, `_projected_score_delta_for_slot`), so impact is low, but the
docstring/comment calling it "the BRAIN §6 metric" (`validators.py:302`) is misleading. The
authoritative guard path (`_count_excess_cluster_days`) is global and correct (WP7-1), so no contract
breach. **S3.**

---

## WP7-8 — Divergent SKULL `cluster_areas` key (S3)

`config/SKULL.json:839-844` defines `optimization.cluster_areas = [Tower, Rifle Range, Outdoor Skills,
Handicrafts]` — note it **omits Archery**, which both the judge and the gap metric include via
`area_clustering_priority` (`SKULL.json:822-826`) + the ≥3-activity extension. Neither the judge nor
`_get_authoritative_gap_area_map` reads this `cluster_areas` key, so there is no live drift today, but
it is a config foot-gun: any future code that wires the wrong key would silently desync from the judge.
**S3.**

---

## Executive Summary

The core arithmetic is sound: `_count_excess_cluster_days`, `_count_area_cluster_gaps`, and
`would_create_excess_day_for_entries` reproduce the judge's §6 formulas and resolve to the identical
cluster-area set, so Phase-D guards optimize exactly what `regression_checker.py` scores (WP7-1).
D.2, D.4, and D.10 are properly guarded (strict `_can_schedule` and/or quality-snapshot rollback) and
cannot raise excess/gaps or Top-5 misses. The real risks are at the edges. **§11 is a confirmed,
measurable gap (WP7-2):** D.9's `_optimize_outlier_activities` and `_optimize_commissioner_day_ownership`
omit `_is_pair_protected_delta`, and because the Phase-D guard never measures Delta/Sailing pairing
(Delta isn't a cluster area), a broken pair is neither prevented nor rolled back — it silently costs §3
points, and B.6 (the only re-pair) runs before D.9. The "FORCED" story is also miswired: D.3 does **not**
create hard violations (it validates via `_can_schedule`+`add_entry`), whereas D.8's
`_force_cluster_consolidation` skips `_can_schedule` and can manufacture a Delta+Tower/ODS §4 adjacency
violation that no guard or D.11 step repairs (WP7-3, WP7-4). Finally, the in-scope `phase_d_cleanup.py`
is 100% dead and actively misleading — its `pass` cleanup stubs misrepresent the live D.11 (WP7-5).
Recommended priorities: add pair protection (and a pairing term in `_schedule_quality_snapshot`) to the
two D.9 passes; route D.8's force move through `_can_schedule`; delete/neuter `phase_d_cleanup.py`.
