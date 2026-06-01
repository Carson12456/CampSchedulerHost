# WP3 — Top-5 Contract Audit (HIGHEST-RISK)

Read-only logic audit. No source files were modified. Scope: `core/scheduler/legacy_parts/top5_and_swaps.py`,
`core/services/unscheduled_source.py`, `core/services/unscheduled_analyzer.py`, and
`_count_non_exempt_top5_misses` (defined once at `core/scheduler/legacy_parts/placement_and_state.py:2714`).

Hard contract under test: `non_exempt_top5_misses == 0`. The acceptance gate (`pipeline.py:556`) is mechanically
sound — it raises — but it is only as strong as `is_exempt`. The highest-risk surface is the **exemption logic that
feeds the gate**, where three rules over-fire and can mark a genuine non-exempt Top-5 miss as exempt, letting `count`
fall to 0 and the gate pass a failing schedule.

## Executive Summary (read me first)

1. The gate sources misses from a single builder (`build_unscheduled_data` → `_is_exempt_missing`) and is the only
   authoritative count — that part is correct and consistent across regression_checker, regen, and the GUI.
2. **HC/DG saturation exemption is unsound (S0).** It exempts ANY troop missing History Center / Disc Golf the moment
   each Tuesday slot holds one HC-or-DG entry. It never checks the top-3 combined ranking, and it treats HC+DG as one
   3-slot pool when they are two independent exclusive areas (up to 6 placements). A top-1 requester beaten by lower
   ranks — or one missing DG while DG slots are free — is wrongly exempted and slips past the gate.
3. **Day-request displacement exemption is an unbounded heuristic (S0).** Any honored day-request that is lower-ranked
   (or unranked) than a missed Top-5 exempts that miss, without verifying it ever occupied a slot the Top-5 needed.
4. **Canoe-duplication exemption ignores the "two-hour" qualifier (S0/S1).** Two 1-hour canoe requests that easily
   co-fit are treated as exempt duplication.
5. **`_enforce_mandatory_top5` (and shared window-clear/reclaim helpers) lack the `_is_pair_protected_delta` guard
   (S2).** Delta is a 1-slot activity, so it is not in the multi-slot PROTECTED set; the explicit guard is the only
   protection, and it is missing here — contradicting BRAIN §11's claim that all four loops implement it. Impact is
   the soft Delta/Sailing pairing (no Top-5 miss is created), so S2.
6. Anchors (Reflection/Super Troop/HC/DG) are protected at every displacement site in the four named loops and are
   re-checked by `_validate_critical_constraints` just before the gate (raises). Two dead/shadowed code paths
   (duplicate `_ultra_aggressive_top5_recovery`; the naive `PhaseBCoreMixin` overrides) are misleading safety traps.

## Findings Summary

| ID | Severity | Location | Issue |
| --- | --- | --- | --- |
| F1 | **S0** | `unscheduled_source.py:37,106-110` | HC/DG "Tuesday full" exemption ignores combined top-3 ranking AND conflates per-slot HC+DG capacity into one pool |
| F2 | **S0** | `unscheduled_source.py:41-44,67-87` | Day-request displacement exemption fires for any lower/unranked honored request; no slot-need verification |
| F3 | **S0/S1** | `unscheduled_source.py:39,124-130` | Canoe-duplication exemption ignores the "two-hour" requirement; exempts 1-hour canoe duplicates |
| F4 | **S2** | `top5_and_swaps.py:2732-2733`; `placement_and_state.py:2782,2871,2907` | `_enforce_mandatory_top5` + window-clear/reclaim helpers omit `_is_pair_protected_delta`; Delta is 1-slot so not in PROTECTED → pair drift (BRAIN §11 mismatch) |
| F5 | S3 | `top5_and_swaps.py:3123,3256` | Duplicate, never-called `_ultra_aggressive_top5_recovery`; first def also `NameError`s on `recoveries` |
| F6 | S3 | `phase_b_core.py:34,109,145` | Shadowed, unsafe `_schedule_preferences_range`/`_guarantee_all_top5`/`_enforce_mandatory_top5` (no anchor/pair/constraint checks); latent S0 if MRO changes |
| F7 | S3 | `unscheduled_source.py:35`; `regenerate_all_schedules.py:38-67` | (a) 3-hr exemption relies on "3-hr never gap-filled" invariant; gate raise leaves stale `*_schedule.json` on disk |
| OK | — | `placement_and_state.py:2714`; `pipeline.py:556` | Single source of truth + gate raises confirmed (see "Confirmed Correct") |

---

## Detailed Findings

### F1 — HC/DG Tuesday saturation exemption is unsound — **S0**
`core/services/unscheduled_source.py`

```106:110:core/services/unscheduled_source.py
    tuesday_hc_dg_slots = set()
    for entry in schedule.entries:
        if entry.time_slot.day.name == "TUESDAY" and entry.activity.name in HC_DG_ACTIVITIES:
            tuesday_hc_dg_slots.add(entry.time_slot.slot_number)
    hc_dg_tuesday_full = tuesday_hc_dg_slots >= {1, 2, 3}
```
```37:37:core/services/unscheduled_source.py
    if activity_name in HC_DG_ACTIVITIES and hc_dg_tuesday_full:
```

BRAIN §2 (and the WP3 brief) define the rule as: *only the top-3 of the COMBINED DG+HC ranking get the 3 Tuesday
slots.* The code implements neither half of that:

- **No ranking check.** `hc_dg_tuesday_full` is purely about slot occupancy. Once each of Tuesday slots 1/2/3 holds at
  least one HC-or-DG entry, **every** troop missing HC or DG is exempt — including a troop whose request outranks the
  troops that actually hold the slots. Phase A.3 placement order is not a guaranteed global-priority ordering, so a
  rank-1 HC requester can be displaced by a rank-5 troop and then have its miss forgiven.
- **Wrong capacity model.** HC and DG are *separate* exclusive areas: SKULL `exclusive_areas` has
  `"History Center": ["History Center"]` and `"Disc Golf": ["Disc Golf"]`, and `concurrent_activities` is only
  `["Reflection", "Campsite Free Time"]`. So each Tuesday slot can hold one HC **and** one DG → up to 6 HC/DG
  placements. The check declares "full" at 3 (one per slot), even when DG capacity is still open.

**Scenario (miss slips past gate):** Tuesday slots 1/2/3 each contain a History Center (3 troops). Troop X ranks Disc
Golf #1 and did not get it. Three Disc Golf slots are physically free, so this is a fixable, non-exempt Top-1 miss —
but `tuesday_hc_dg_slots == {1,2,3}` ⇒ `hc_dg_tuesday_full` ⇒ X's miss is `is_exempt=True` ⇒ gate counts 0 ⇒ accepts.

**Negative case the code gets wrong:** the top-1 DG requester with a free DG slot MUST be `is_exempt=False`; the code
returns True. (Same broken `>= {1,2,3}` logic is duplicated in the dead `_ultra_aggressive_top5_recovery`,
`top5_and_swaps.py:3146-3152`.)

### F2 — Day-request displacement exemption is an unbounded heuristic — **S0**
`core/services/unscheduled_source.py`

```41:45:core/services/unscheduled_source.py
    if activity_name in (day_requested_names or set()):
        return True
    if day_request_displaces:
        return True
    return False
```
```80:87:core/services/unscheduled_source.py
    for activity_name in honored_day_request_names:
        if activity_name == missing_activity_name:
            continue
        priority = troop.get_priority(activity_name) if hasattr(troop, "get_priority") else 999
        honored_rank = priority + 1 if priority != 999 else 999
        if honored_rank > missing_rank:
            return True
    return False
```

BRAIN §2 Exemption 4(b) requires that the honored day-request **"occupies a slot the Top 5 would have needed."** The
implementation never checks any slot/day relationship between the honored request and the missed preference. It
exempts the miss whenever *any* honored day-request is lower-ranked than the miss — and `Troop.get_priority` returns
`999` for unranked activities (`core/models.py:139-143`), so `honored_rank` becomes `999`, which is `> ` every Top-5
rank. Net effect: **a troop with any honored low-priority/unranked day-request gets blanket exemption for all of its
higher-ranked Top-5 misses.**

**Scenario (miss slips past gate):** Troop T = prefs `[A#1, B#2, …]`, with a day-request for activity Z (rank 12, or
not in prefs) honored on Friday-3. A genuine, unrelated failure leaves A (rank 1) unscheduled. `_day_request_displaces_
preference(T, "A", 1, {"Z"})` → for Z, `honored_rank = 13` (or `999`) `> 1` → returns True → A is `is_exempt=True`.
The gate accepts a schedule missing the troop's #1 pick, even though Z (Friday-3) had nothing to do with A's slot.

**Negative case the code gets wrong:** a missed #1 with no honored day-request occupying its needed slot MUST be
non-exempt; the heuristic exempts it. (The function is intentionally *stricter* in the opposite direction — it
withholds exemption when the honored request outranks the miss — which can also cause false **over**-counting, but
that direction only fails closed and is not S0.)

### F3 — Canoe duplication exemption ignores the "two-hour" qualifier — **S0/S1**
`core/services/unscheduled_source.py`

```124:130:core/services/unscheduled_source.py
                has_other_canoe_family_scheduled = (
                    pref_name in canoe_family_activities
                    and any(
                        name in canoe_family_activities and name != pref_name
                        for name in scheduled_activity_names
                    )
                )
```
```39:39:core/services/unscheduled_source.py
    if activity_name in _get_canoe_family_activities() and has_other_canoe_family_scheduled:
```

BRAIN §2(c): *"If a troop is already scheduled for one **two hour** activity, a missed request for another **two hour**
canoe activity is exempt."* The canoe family from SKULL (`canoe` tag group) is
`[Nature Canoe, Canoe Snorkel, Float for Floats, Troop Canoe, Troop Kayak]` — a mix of 1-hour and 2-hour activities.
The code checks family membership only; it verifies neither the scheduled activity nor the missed activity is
two-hour. So two 1-hour canoe requests that fit comfortably in separate single slots are treated as exempt
duplication.

**Scenario (miss slips past gate):** Troop ranks Troop Canoe #3 and Nature Canoe #4 (both 1-hour). It receives Nature
Canoe and misses Troop Canoe. The miss is fixable (no contiguous-block contention), but
`has_other_canoe_family_scheduled` is True ⇒ exempt ⇒ gate accepts.

**Negative case the code gets wrong:** a missed 1-hour canoe when only another 1-hour canoe is scheduled MUST be
non-exempt; the code exempts it. (Correctly handles the no-other-canoe case = non-exempt.)

### F4 — `_enforce_mandatory_top5` + helpers omit pair-protected-Delta guard — **S2** (BRAIN §11 mismatch)
`core/scheduler/legacy_parts/top5_and_swaps.py`, `core/scheduler/legacy_parts/placement_and_state.py`

Delta is a **1-slot** activity: SKULL `"Delta": {"duration": 1}` and `activities.py:26` sets
`slots=activity_data["duration"]`. Therefore Delta is **not** returned by `_get_multi_slot_activity_names()` and is
**not** in the `PROTECTED` set from `_get_protected_activity_names(...)`. The only thing that protects a paired Delta in
recovery is the explicit `_is_pair_protected_delta(entry)` check (BRAIN §7 deliberately makes unpaired Delta
displaceable). That guard exists in three of the four loops:

- `_force_top1_preferences` — `top5_and_swaps.py:1241`
- `_schedule_preferences_range` — `top5_and_swaps.py:2001`
- `_guarantee_all_top5` — `top5_and_swaps.py:2375`

…but is **absent** in `_enforce_mandatory_top5`:

```2732:2733:core/scheduler/legacy_parts/top5_and_swaps.py
                displaceable = [e for e in troop_entries
                               if e.activity.name not in PROTECTED and get_priority(e) > rank]
```

It is likewise absent in the shared helpers these loops hand `protected_names` to, which gate only on
`name in protected_names` (Delta is never in it):

```2781:2784:core/scheduler/legacy_parts/placement_and_state.py
                for entry in troop_day_entries:
                    if entry.activity.name in protected_names:
                        blocked = True
                        break
```
(`_reclaim_activity_from_lower_priority_troop` at `placement_and_state.py:2871,2907`, and
`_try_place_with_displacement_recovery`, have the same gap.)

**Scenario:** Troop has Sailing (rank 2, multi-slot → protected) + paired Delta (rank 8). It is missing a rank-3 Top-5.
`_enforce_mandatory_top5` sees Delta as `not in PROTECTED` and `get_priority(Delta)=7 > rank=2` ⇒ displaceable ⇒ evicts
Delta to seat the Top-5. Sailing stays; the Delta/Sailing pair drifts apart.

**Why S2 (not S0):** evicting the lower-ranked Delta does not create a Top-5 miss; the damage is the soft
Delta/Sailing pairing (BRAIN §3 soft / §6 "missed Delta/Sailing pairing"), and B.6 is a backstop. But BRAIN §11
explicitly states pair protection is *"Implemented in all Top 1-5 recovery and enforcement displacement loops
(`_force_top1_preferences`, `_guarantee_all_top5`, `_enforce_mandatory_top5`, `_schedule_preferences_range`)."* — so
this is a real documented-contract divergence (borderline S1).

### F5 — Duplicate, dead `_ultra_aggressive_top5_recovery` — **S3**
`top5_and_swaps.py:3123` and `:3256` define the same method twice in class `LegacyPart02Mixin`; the second shadows the
first, and **neither is called anywhere** (no call sites). The first body ignores its arguments, loops all troops, and
references an undefined `recoveries` (`:3196`) → `NameError` if ever invoked; it also re-implements the broken HC/DG
`>= {1,2,3}` exemption. The live (second) body only protects `{"Reflection","Super Troop"}` while it cross-day-moves
entries — it would happily relocate History Center/Disc Golf/Delta. Dead today, but a maintenance trap that violates
the anchor/pair invariants if anyone wires it in.

### F6 — Shadowed unsafe `PhaseBCoreMixin` overrides — **S3 (latent S0)**
`phase_b_core.py` defines naive versions of the three core loops:

```135:139:core/scheduler/phase_b_core.py
                for slot in self.time_slots:
                    if self.schedule.is_troop_free(slot, troop):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"    -> {activity_name} forced to {slot}")
                        break
```
`_guarantee_all_top5` force-adds into ANY free slot with no constraint/anchor/pair check; `_enforce_mandatory_top5`
displaces only `FILL_ACTIVITIES`. These are shadowed because in `ConstrainedScheduler`'s base list (`constrained_
scheduler.py:43-60`) `Top5AndSwapsMixin` is at index 2 and wins the MRO over `PhaseBCoreMixin` near the end. The safe
top5_and_swaps versions therefore run. **Risk:** if the mixin order is ever reordered, these unsafe versions activate
and can evict anchors / break Delta — an S0 regression hiding behind MRO. Recommend deleting or clearly retiring them.

### F7 — Secondary / residual observations — **S3**
- **3-hour exemption** (`unscheduled_source.py:35`) checks only "troop has any 3-hour scheduled," not "the scheduled
  3-hour was itself requested." It is safe **only because** 3-hour activities (Tamarac/Itasca/Back of the Moon) are
  tagged `off_camp`/`3_hour` and not `fill`, so gap-fill never places them; thus `has_3hr_scheduled` implies a
  requested 3-hour. The exemption relies on this external invariant rather than asserting it.
- **Stale-JSON / eval bypass:** `regenerate_all_schedules.py:38-67` wraps `schedule_all()` in `try/except Exception`
  and only writes the JSON on success, then raises `RuntimeError` if not all weeks succeeded. So a gate `ValueError`
  is surfaced (not silently swallowed) *within a run*, but the failed week's previous `*_schedule.json` remains on
  disk. A fresh-eval that ignores the `RuntimeError` and reads existing schedule JSONs could report 0 misses for a
  week that actually failed the gate.

---

## Confirmed Correct (explicit clearances)

- **Single source of truth (item 2).** `_count_non_exempt_top5_misses` is defined exactly **once**
  (`placement_and_state.py:2714`) and is built from `build_unscheduled_data(...)`. The reporting consumers all use the
  same builder/payload: `utils/regression_checker.py:1007` (`summarize_non_exempt_misses` on `schedule_json.unscheduled`),
  `utils/regenerate_all_schedules.py:49`, `web/gui_web.py:143/159/264`, and `unscheduled_analyzer.py` (reads the JSON,
  fails fast if `unscheduled` is absent — `:90-99`). No parallel/disagreeing authoritative miss recomputation from
  `troop.preferences` exists. The per-loop `missing`/`has_3hr_scheduled` computations inside the recovery methods are
  placement-effort only and are *stricter* than the gate (they ignore HC/DG, canoe, and day-request exemptions, so
  they try harder, never less) — safe direction.
- **Sailing half-fill credit cannot mask a Top-5 miss.** `get_request_credit_fill_activities` only credits activities
  with `counts_as_request = 10 <= priority < 20` (`sailing_half_fills.py:103`), i.e. ranks 11-20 only. The gate passing
  `sailing_balls_fills=None` (it is computed *after* the gate, `pipeline.py:570`) is therefore benign for Top-5.
- **The gate truly raises (item 4).** `pipeline.py:556-564` raises `ValueError` when `final_top5 > 0`, before the only
  `return self.schedule` (`:573`). Immediately prior, `_validate_critical_constraints` (`placement_and_state.py:2600-
  2711`) hard-raises on missing Friday Reflection, missing Super Troop, troop empty slots, HC/DG-on-non-Tuesday, and
  exclusive-area violations — so anchor eviction is caught, not silently accepted.
- **Anchors protected at every displacement site in the four named loops.** `_get_protected_activity_names` always
  unions `NON_DISPLACEABLE_ACTIVITIES` + `MANDATORY_ANCHORS` (Reflection, Super Troop, History Center, Disc Golf —
  SKULL `mandatory_anchors`), and every displaceable filter excludes `PROTECTED`. `_can_schedule`/`is_troop_free`
  prevents placing on top of an existing anchor entry. The only protection gap found is pair-protected **Delta** (F4),
  not anchors.

## Recommended fixes (not applied — audit only)
1. F1: rank all HC/DG requesters; exempt a miss only if it is outside the top-3 combined ranking *and* no slot of its
   own activity (HC vs DG) is free on Tuesday.
2. F2: only exempt when an honored day-request actually occupies a day/slot the missed Top-5 needed (or the missed
   activity is itself day-requested, which is already handled at `:41`).
3. F3: require both the scheduled and the missed canoe activity to be two-hour (`slots >= 2` / duration ≥ 2).
4. F4: add `or self._is_pair_protected_delta(e)` to the `_enforce_mandatory_top5` filter and to
   `_force_place_with_window_clearing` / `_reclaim_activity_from_lower_priority_troop` /
   `_try_place_with_displacement_recovery`.
5. F5/F6: delete the dead duplicate and the shadowed `PhaseBCoreMixin` loops.
