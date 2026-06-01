# WP8 — Snapshot / Restore & State Integrity Audit (read-only)

**Contract:** BRAIN hard rule `non_exempt_top5_misses == 0`. Every Phase-D safety guard
depends on snapshot/restore being a TRUE deep rollback.
**Scope:** `core/scheduler/legacy_parts/placement_and_state.py`, `core/scheduler/state.py`
(`_snapshot_scheduler_state` / `_restore_scheduler_state`, `_rebuild_staff_tracking`,
`_fix_multislot_integrity`, `_add_to_schedule` / `_remove_from_schedule`).
**Verdict:** Deep-rollback mechanism is **sound**; hard contract is protected. Defects are bounded to
soft scoring/optimization + one latent contract-accounting fragility + dead-but-dangerous code.

## Summary table
| # | Topic | Verdict | Sev | Lines |
| --- | --- | --- | --- | --- |
| 1 | Snapshot/restore deep-copy depth (no aliasing) | **PASS** | — | `placement_and_state.py:137-166`; `models.py:37,62,152,199` |
| 2 | Hard guards recompute fresh from `entries` | **PASS (by design)** | — | `placement_and_state.py:2714-2732`; `pipeline.py:98-108,126-162` |
| 3 | `sailing_balls_fills` not snapshotted, feeds Top-5 counter | **PARTIAL (latent)** | S2→S1 if reordered | `placement_and_state.py:2724`; `state.py:104`; `top5_and_swaps.py:361-363`; `pipeline.py:555,570` |
| 4 | Entry mutations that skip staff rebuild | **FLAG (bounded)** | S2 | wrappers `:65-102,169-240`; bypass paths (see F-4) |
| 5 | Shadowed `utilities._can_schedule` cached-map hard gate | **DEAD-BUT-DANGEROUS** | S3 (S0 if activated) | `utilities.py:129-199` esp `191-197`; `constrained_scheduler.py:43-60` |
| 6 | Multi-slot add/remove contiguity & atomicity | **PASS** | — | `placement_and_state.py:65-102,169-240`; `models.py:212-265` |
| 7 | `_fix_multislot_integrity` repair gaps + no rebuild | **FLAG** | S2 | `placement_and_state.py:1663-1850`; `models.py:389-416` |

Severity: **S0** breaks Top-5/hard contract · **S1** wrong score/contract mismatch · **S2** missed optimization · **S3** quality/dead code.

## Detailed findings

### F-WP8-1 (PASS) — Deep rollback of captured fields is genuine; no aliasing
`_snapshot_scheduler_state` (`placement_and_state.py:137-149`) and `_restore_scheduler_state`
(`:152-166`) copy each mutable at the correct depth, and every leaf is immutable:

- `entries`: `list(self.schedule.entries)` (`:140`) → new list; elements are `ScheduleEntry(frozen=True)` (`models.py:146-152`), as are `Activity` (`:37`) and `TimeSlot` (`:62`). Restore reassigns `self.schedule.entries = list(...)` (`:154`) → another fresh list. `Schedule` has **only** the `entries` field (`models.py:197-199`), so capturing `entries` captures all of `Schedule`'s mutable state — no hidden index/cache on the model to desync.
- `total_staff_by_slot`: `dict(...)` (`:141`) — int values, frozen-`TimeSlot` keys.
- `staff_load_by_slot`: `{slot: dict(z) ...}` (`:142`) — **inner zone dicts are re-copied** (the one place a naive `dict()` would alias); int values.
- `troop_progress`: `{k: set(v) ...}` (`:145`) — **each set re-copied** (naive `dict()` would alias the sets); string elements.
- `troop_top5_scheduled`/`troop_top10_scheduled` (`:143-144`) int values; `troop_has_delta`/`troop_has_super_troop` (`:146-147`) bool values; `delta_was_swapped` `set(...)` (`:148`).

**Proof of correctness:** the only deeply-nested mutables (inner zone dicts, progress sets) are explicitly re-copied, and all leaves (`ScheduleEntry`/`Activity`/`TimeSlot`, int, bool, str) are immutable. Therefore no in-place mutation after a snapshot can leak into the snapshot, and no post-restore mutation can leak back. The dozens of callers (e.g. `top5_and_swaps.py`, `clustering_and_optimization.py`, `pipeline.py:127`) each take an independent `list()`/`dict()`/`set()`, so repeated snapshot→mutate→restore cycles are safe.

### F-WP8-2 (PASS, by design) — hard guards read entries fresh, not snapshotted counters
`_count_non_exempt_top5_misses` (`:2714-2732`) rebuilds misses via
`build_unscheduled_data(self.troops, self.schedule, sailing_balls_fills)` — derived from live
`self.schedule`, **not** from `troop_top5_scheduled`. `_count_top10_in_schedule`
(`pipeline.py:98-108`) likewise scans `self.schedule.entries`. So the Phase-D rollback decisions in
`_safe_phase_d_step` (`pipeline.py:126-162`) hinge only on `entries` (correctly deep-copied, F-1) and
`sailing_balls_fills` (F-3). This is the reason the rollback contract holds even if the auxiliary
snapshotted counters drift from reality — they are a courtesy, not the gate.

### F-WP8-3 (S2 now, S1 latent) — `sailing_balls_fills` feeds the Top-5 counter but is NOT snapshotted
`_count_non_exempt_top5_misses` consumes `self.sailing_balls_fills` (`:2724`) to mark Sailing
half-fill exemptions, yet the snapshot omits it (`:137-149`) and restore never restores it
(`:152-166`). **Currently safe by ordering only:** `_schedule_sailing_balls_fills`
(`top5_and_swaps.py:361-363`) is called exactly once, at `pipeline.py:570` — *after* the final
acceptance gate (`pipeline.py:555`) and *after every* snapshot/restore boundary; during all
transactions it stays the init `{}` (`state.py:104`), so before/after counts use identical fills.

**Latent corruption scenario:** move/clone a Sailing-affecting step into a `_safe_phase_d_step` (or
the cluster-repair blocks at `pipeline.py:501-543`) that recomputes `sailing_balls_fills`. On
rollback, `entries` is restored but `sailing_balls_fills` keeps the new value; the next
`before_top5` is computed against entries+stale-fills. A Sailing Top-5 whose entry was rolled back
could be scored *exempt/satisfied* → `non_exempt_top5_misses` silently undercounts → S1 (and S0 if it
masks a true miss). **Fix:** add `sailing_balls_fills` to snapshot/restore (deep-copy the dict).

### F-WP8-4 (S2) — many entry-mutation paths change `self.schedule.entries` without rebuilding staff tracking
The sync'd wrappers `_add_to_schedule` (`:65-102`) and `_remove_from_schedule` (`:169-240`) keep
`staff_load_by_slot`/`total_staff_by_slot` consistent. But numerous paths mutate entries **directly**
and skip staff updates, e.g.:
- `self.schedule.entries = [...]` rebuilds: `clustering_and_optimization.py:536,610,699,829,1028`.
- `.append()/.remove()` swap pairs: `safety_and_export.py:489-569,646-718`; `preference_and_limited.py:1006-1020,1130-1157,1635-1673,1800-1853`; `phase_d_cleanup.py:130-146`.
- `self.schedule.add_entry/remove_entry` (model-level, no staff hook): `phase_d_cleanup.py:298-374`; `sequencing_and_constraints.py:78-619`; `clustering_and_optimization.py:2180-3038`.
- `_fix_multislot_integrity` itself (F-7).

Between explicit `_rebuild_staff_tracking()` calls the staff maps are stale.
**Impact is bounded — NOT a Top-5 break:** the active `_can_schedule`
(`sequencing_and_constraints.py:725`) computes its hard staff cap from
`_count_all_staff_in_slot` (`:1360-1368`), which **re-sums `self.schedule.entries` fresh** every
call. Stale maps only feed *soft* scoring (`_get_slot_staff_score`
`preference_and_limited.py:714-735`, `_get_total_staff_score` `:738-744`) and the
`_calculate_staff_variance` metric (`validators.py:180-192`). Worst case = suboptimal
staff-balance ordering. Phase D is further protected because `_safe_phase_d_step` rebuilds before
snapshot and after the step (`pipeline.py:126,134,139`) and staff variance is not a rollback guard.

### F-WP8-5 (S3 dead-but-dangerous) — shadowed `utilities._can_schedule` has a cached-map hard gate
`utilities.py:129-199` defines a *second* `_can_schedule`; step 5 (`:191-197`) hard-rejects on the
**cached** map: `current_load = self.staff_load_by_slot.get(slot,{}).get(zone,0); if current_load >= max_load: return False`. In the composed class
(`constrained_scheduler.py:43-60`) `SequencingAndConstraintsMixin` precedes `UtilityMixin` in MRO, so
this method is **shadowed and never executes**. If MRO order changed (or it were called directly),
stale staff maps (F-4) would wrongly reject valid placements → could drop a Top-5 → **S0**. Flag as
dead code that is a latent S0 landmine.

### F-WP8-6 (PASS) — multi-slot add/remove is atomic and contiguous
- **Add:** `_add_to_schedule` (`:65-102`) → `Schedule.add_entry` (`models.py:212-265`) validates ALL
  continuation slots *before* appending any (`:232-254` checks; `:257-264` appends), so a failed add
  leaves zero half-block; staff load is then updated per occupied slot (`:82-97`) using the same
  `slots_needed`/day-boundary logic → counts match entries.
- **Remove:** `_remove_from_schedule` (`:169-240`) anchors to the true block start
  (`start_slot_num` scan `:193-198`), then removes the full contiguous run for that
  `troop+activity+day` (`:214-236`), decrementing staff per removed slot. No orphaned
  start/continuation, no dangling slot. Shared-slot activities (Sailing slot-2, Aqua Trampoline)
  stay consistent because rebuild/add/remove all count +1 per entry.

### F-WP8-7 (S2) — `_fix_multislot_integrity`: ineffective re-add path + no staff/cache sync
`_fix_multislot_integrity` (`:1663-1850`):
- **(a) No rebuild/invalidation.** After mutating entries it only prints (`:1845-1850`); it never
  calls `_rebuild_staff_tracking()` or `_mark_schedule_changed()`, and the model-level
  `add_entry`/`remove` it uses don't either. So staff maps (F-4) and `SchedulerCache`
  constraint/occupancy caches (`scheduler_cache.py:94-101`) are left stale until a later caller
  rebuilds. (The day-count cache at `preference_and_limited.py:754` is incidentally safe — but only
  because `_cache_valid` is set `True` once at init `state.py:134` and **never re-set**, making that
  cache effectively always-recomputed dead weight; itself an S3 dead-cache.)
- **(b) Re-add of a missing slot is frequently defeated by `is_troop_free`.** Filling a missing
  continuation/start via `self.schedule.add_entry(time_slot, …)` (`:1797`) calls
  `is_troop_free(time_slot)` (`models.py:389-416`), which treats the surviving remnant as a
  multi-slot **start** occupying the missing slot → `add_entry` returns False ("troop not free"), so
  the slot is neither filled nor removed and the half-block **silently persists**.
  **Concrete:** Sailing (1.5→2 slots) with slot-1 present, slot-2 missing → `add_entry(slot2)` fails
  because slot-1's start already marks slot-2 occupied → integrity "fix" no-ops, leaving 1/2 entries.
  This does not break Top-5 (the time is still reserved by `is_troop_free`), but yields an
  inconsistent export and can mislead entry-based gap detection. Also note `add_entry` anchors at the
  passed slot as a forward START (`models.py:259-264`), so using it to patch an interior slot can
  over-extend a block in edge cases — bounded in practice by the same `is_troop_free` refusal.

## Executive summary
The transactional core is correct where it matters most. `_snapshot_scheduler_state` /
`_restore_scheduler_state` are a **true deep rollback** of every field they capture: lists, the
nested `staff_load_by_slot` inner dicts, and the per-troop `progress` sets are all re-copied, and all
leaf objects (`ScheduleEntry`/`Activity`/`TimeSlot`, ints, bools, strings) are `frozen`/immutable, so
no mutation can leak across a rollback boundary (F-1). Crucially, the Phase-D guards recompute Top-5
and Top-10 **fresh from `self.schedule.entries`** rather than from snapshotted counters (F-2), so the
hard `non_exempt_top5_misses == 0` contract is protected even when auxiliary state drifts. Multi-slot
add/remove is atomic and keeps Sailing/2-hr/3-hr blocks contiguous (F-6). The real risks are
secondary: `sailing_balls_fills` is omitted from the snapshot yet feeds the Top-5 counter — safe only
because it is computed once after all boundaries, but an S1 landmine if a Sailing step is ever moved
inside a guard (F-3); dozens of direct entry mutations skip `_rebuild_staff_tracking`, leaving stale
staff maps that affect only soft scoring because hard caps re-sum entries fresh (F-4); a shadowed
`utilities._can_schedule` carries a cached-map hard gate that would become an S0 if MRO changed (F-5);
and `_fix_multislot_integrity` both skips staff/cache sync and often fails to re-add a missing slot,
silently leaving half-blocks (F-7). Recommended priorities: (1) snapshot/restore `sailing_balls_fills`;
(2) delete or neutralize the shadowed `utilities._can_schedule`; (3) have `_fix_multislot_integrity`
rebuild staff/caches and repair missing slots without relying on `add_entry`'s start-anchored
`is_troop_free`.
