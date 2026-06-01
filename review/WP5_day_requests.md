# WP5 — Day-Request (MUST-HONOR) Solver Audit

Read-only audit of the day-request subsystem against `config/BRAIN.md` §1, §2, §4, §5, §10–11.
No source code was modified. MRO winners were confirmed by runtime introspection of
`ConstrainedScheduler` (see "MRO / shadowing" below), because the class composes duplicate
`_method` names across mixins (`core/constrained_scheduler.py:43`).

## Executive Summary

The two-pass architecture is wired correctly: C.1 non-aggressive (`pipeline.py:308`, tiers
effectively T1–T2, non-destructive via snapshot/restore) and the aggressive T1–T6 seal inside
`_final_comprehensive_validation` (`placement_and_state.py:1976`). T4 correctly avoids
cannibalizing multi-day same-activity requests, pair-protected Delta and protected anchors are
honored at displacement sites, and INFEASIBLE/UNFULFILLED are logged. However, the subsystem
has two **S0** defects. (1) `force_day_request=True` does not merely bypass the §10.3 soft checks —
it also bypasses **physical exclusivity and capacity**, because those checks are nested inside the
same `and not force_day_request` block (`sequencing_and_constraints.py:859`, exclusivity/capacity
at `:934`–`:944`). This lets T3/T6 force-place a day-requested exclusive activity into a slot held
by another troop (hard exclusivity violation → run aborts at the critical-constraint gate) or
exceed canoe capacity (no canoe check in the final gate → silent >26 breach). (2) The Exemption-4
computation in `unscheduled_source.py:67` (`_day_request_displaces_preference`) uses a rank
heuristic that diverges from BRAIN §2/§10.2: it fails to exempt a Top-5 that T6 legitimately
displaced when the honored request out-ranks it (→ post-seal acceptance gate raises and the whole
run aborts despite honoring MUST-HONOR), and conversely it exempts unrelated Top-5 misses whenever
any lower-ranked honored day-request exists (→ masks real non-exempt misses, violating the hard
contract). Lower-severity issues: the seal is not actually the last mutating step (`pipeline.py:476`
runs many more passes after it), the `_remove_overlaps` Thursday guard never fires for a real
opt-out, anchor-blocked opt-outs abort the run instead of being tolerated per §10.5, and four
shadowed duplicate methods are latent MRO hazards.

## Summary Table

| ID | Severity | Area | Location | One-line |
| --- | --- | --- | --- | --- |
| F1 | **S0** | `force_day_request` bypasses hard invariants | `sequencing_and_constraints.py:859,934-944` | Exclusivity + capacity checks sit inside the `not force_day_request` block; force bypasses them (contra §10.3). |
| F2 | **S0** | T6 exemption diverges from BRAIN §2/§10.2 | `unscheduled_source.py:67-87` | Rank heuristic both fails to exempt legit T6 misses (run aborts) and exempts unrelated misses (masks real failures). |
| F3 | S2 | Seal is not the last mutating step | `pipeline.py:476-553` | ~7 mutating passes run after the seal with no re-seal; "locked in / not undone" claim is false. |
| F4 | S2 | `_remove_overlaps` guard is inert | `clustering_and_optimization.py:683-685` vs `placement_and_state.py:1591` | Only caller runs in D.11 (pre-seal); opt-out trios exist only post-seal, so the guard never protects one. |
| F5 | S1 | Anchor-blocked opt-out aborts run | `top5_and_swaps.py:561-565` + `placement_and_state.py:1979-1987` | §10.5 says anchor blockage is unavoidable/UNFULFILLED-tolerated; seal raises on ANY unfulfilled. |
| F6 | S3 | Shadowed duplicate methods (MRO hazard) | `utilities.py:129`, `validators.py:72`, `phase_d_cleanup.py:257` | Dead variants enforce/omit different rules than the winners; reorder would silently change behavior. |

---

## Detailed Findings

### F1 — `force_day_request` bypasses physical exclusivity and capacity (S0)

**Where:** `core/scheduler/legacy_parts/sequencing_and_constraints.py:725` (`_can_schedule`, the MRO
winner). Guard at `:859`; bypassed hard checks at `:934`–`:944`.

```859:944:core/scheduler/legacy_parts/sequencing_and_constraints.py
        if activity.name not in self.CONCURRENT_ACTIVITIES and not force_day_request:
            # BEACH SLOT RULE ...
            if activity.name in self.BEACH_SLOT_ACTIVITIES:
                ...
            # BEACH STAFF LIMIT ...
            if activity.name in self.BEACH_STAFFED_ACTIVITIES:
                ...
            # CAPACITY-AWARE EXCLUSIVITY CHECK
            if activity.name in CAPACITY_CHECK_ACTIVITIES:
                ...
                if not self._check_activity_capacity(slot, activity, troop, ...):
                    return False
            elif not self.schedule.is_activity_available(slot, activity, troop):
                return False
```

BRAIN §10.3 (`config/BRAIN.md:365`) lists exactly which checks `force_day_request` may bypass
(back-to-back, staff limit, duplicate prevention, beach slot rule, beach staff cap) and states the
invariants that **remain enforced**: `is_troop_free`, multi-slot boundary, request-only, **and
physical exclusivity**. The code bypasses the listed soft checks correctly (back-to-back `:795`,
staff `:825`, duplicate `:842`, beach slot `:866`, beach cap `:924`). But the **CAPACITY-AWARE
EXCLUSIVITY CHECK** (`is_activity_available` at `:943`, `_check_activity_capacity` at `:941`) is
nested inside the *same* `and not force_day_request` block, so a forced placement skips it entirely.

Confirmed enforced-always (good): `is_troop_free` (`:763`), request-only (`:771`), multi-slot
boundary (`:835`), day-request day gate (`:849`).

**Scenario (silent drop / displaced-anchor / hard breach):**
- Troop B has `day_requests[Thursday] = ["Archery"]` (Archery is exclusive, single-slot). Troop A
  already holds Archery in Thursday slot 1. In the aggressive seal, T1/T2 fail (exclusivity blocks),
  then **T3** calls `_can_schedule(..., force_day_request=True)` (`top5_and_swaps.py:603` → `:465`).
  `is_troop_free(Thu-1, B)` is True, day gate passes (Thursday is requested), and the exclusivity
  check is skipped → B is force-placed into Archery Thu-1 alongside A = **exclusive double-booking**
  (BRAIN §4 HARD). The later critical-constraint gate counts it
  (`placement_and_state.py:2655-2682`) and **raises** (`:2710`), aborting the whole run — even though
  the correct outcome is to reject the request and log it INFEASIBLE (a single exclusive slot cannot
  hold two troops, and T5/T6 only clear the *same* troop's slots, so it is genuinely infeasible).
- Capacity variant (silent): a troop day-requests a canoe activity on a day already at the 26-person
  cap. T3 force bypasses `_check_activity_capacity` → >26 in canoes. `_validate_critical_constraints`
  (`placement_and_state.py:2600-2711`) has **no canoe-capacity check**, so this hard violation is
  delivered silently.

**Note:** the 3-hour Thursday opt-out activities (`Tamarac`, `Itasca`, `Back of the Moon`) are in
`concurrent_exclusivity_exceptions` (`config/SKULL.json:794`), so the opt-out path itself does not
trip exclusivity; this finding is about force-placing genuinely exclusive single-slot activities and
capacity-limited activities.

---

### F2 — T6 exempt-miss computation diverges from BRAIN §2 / §10.2 (S0)

**Where:** `core/services/unscheduled_source.py:67-87` (`_day_request_displaces_preference`), used by
`_is_exempt_missing` (`:43`) → `build_unscheduled_data` → the authoritative hard gate
`_count_non_exempt_top5_misses` (`placement_and_state.py:2714`).

```67:87:core/services/unscheduled_source.py
def _day_request_displaces_preference(troop, missing_activity_name, missing_rank, honored_day_request_names):
    for activity_name in honored_day_request_names:
        if activity_name == missing_activity_name:
            continue
        priority = troop.get_priority(activity_name) if hasattr(troop, "get_priority") else 999
        honored_rank = priority + 1 if priority != 999 else 999
        if honored_rank > missing_rank:
            return True
    return False
```

BRAIN §2 Exemption 4 (`config/BRAIN.md:54`) and §10.2 T6 (`config/BRAIN.md:357`): a Top-5 miss is
exempt when the troop has an honored day-request that "occupies a slot the Top-5 would have needed."
The implementation substitutes a pure **rank comparison** (`honored_rank > missing_rank`) with no
day/slot relationship. This breaks in **both directions**:

- **Over-strict → run abort (S0).** When T6 honors a day-request `X` by displacing a *better-ranked*
  Top-5 `Y` (rank(X) > rank(Y)), `honored_rank(X) > missing_rank(Y)` is False, so `Y` is counted
  **non-exempt**. The post-seal acceptance gate `_count_non_exempt_top5_misses` then trips at
  `placement_and_state.py:2033-2042` (and again at `pipeline.py:555-564`) and **raises** —
  aborting an otherwise valid run that correctly honored a MUST-HONOR request. This is reachable: the
  T6 loop displaces the first eligible Top-5 occupant in slot order (`top5_and_swaps.py:652-689`),
  which can out-rank the day-requested activity it is making room for. Per §1 the day-request is
  supposed to supersede that Top-5 and the miss is supposed to be **exempt**.
- **Over-loose → masks real misses (S1, also a hard-contract breach).** Any troop with a low-ranked
  or unranked honored day-request gets a blanket exemption for *every* higher-ranked Top-5 miss,
  regardless of day/slot. A genuine Top-5 failure (unrelated to the day-request) is silently marked
  `is_exempt=True`, so `non_exempt_top5_misses` under-counts and a contract-failing schedule passes
  the gate (BRAIN §1 hard contract: `non_exempt_top5_misses == 0`).

`get_priority` is 0-indexed (`core/models.py:139-143`, returns `999` when unranked), so the
`+1`/`!=999` arithmetic is internally consistent; the defect is the heuristic itself, not an off-by-one.

---

### F3 — The aggressive seal is not the final mutating step (S2)

**Where:** `core/scheduler/pipeline.py:476` calls `_final_comprehensive_validation()` (which contains
the seal at `placement_and_state.py:1976`), but `pipeline.py:478-553` then runs many more mutating
passes with **no re-seal**:

- `_final_soft_constraint_cleanup()` (`:480`, `:550`)
- `_finalize_filler_replacement_audit()` (`:496`, `:521`, `:546`)
- `_aggressive_excess_day_reduction_swaps()` (`:507`, `:531`)
- `_optimize_cluster_gaps_post_fill()` (`:508`, `:532`)
- repeated `_fix_multislot_integrity()` / `_guarantee_no_gaps()`

This contradicts BRAIN §5 "FINAL Day-Request Enforcement … Runs at the **very end** … Ensures
MUST-HONOR placements are … not undone by any previous repair/gap-fill pass" (`config/BRAIN.md:212`)
and §10.1 (`config/BRAIN.md:331`). In practice the tail is *mostly* safe because (a)
`_can_schedule`'s day-request gate (`sequencing_and_constraints.py:849-855`) refuses to move a
day-requested activity to a wrong day — and `ignore_day_requests=True` is used **nowhere** in the
codebase — and (b) `_aggressive_excess_day_reduction_swaps` only swaps single-slot entries
(`clustering_and_optimization.py:2543`, `:2498`) and protects the 3-hour names via its `protected`
set (`:2477-2482`). But the documented invariant ("seal is last / cannot be undone") is false, and any
future unguarded removal/move added to this tail (or any pass that calls `schedule.add_entry` /
`entries.remove` directly without the day-request gate) can silently drop a honored request with no
final re-validation of day-requests.

---

### F4 — `_remove_overlaps` Thursday-opt-out guard never protects a real opt-out (S2)

**Where:** guard at `core/scheduler/legacy_parts/clustering_and_optimization.py:683-685`:

```683:685:core/scheduler/legacy_parts/clustering_and_optimization.py
                    if (day == Day.THURSDAY
                            and self._is_day_request_thursday_3slot(entry.troop, entry.activity)):
                        continue
```

`_remove_overlaps` (MRO winner = clustering version) is only invoked from
`_comprehensive_final_cleanup` (`placement_and_state.py:1591`), which is **D.11** (`pipeline.py:448`)
— strictly *before* the seal (`pipeline.py:476`). The Thursday opt-out trio is created **only** in the
aggressive seal (`top5_and_swaps.py:558-569`, gated on `aggressive`), and C.1 never creates one. So at
every point `_remove_overlaps` runs, no opt-out trio exists, and its guard is dead for the documented
flow. BRAIN §10.4 (`config/BRAIN.md:383`) presents both `_remove_overlaps` and
`_fix_multislot_integrity` as load-bearing opt-out guards; in reality only `_fix_multislot_integrity`
(`placement_and_state.py:1727,1751,1765,1790` — all guarded) runs after the seal and actually protects
the trio. The `_remove_overlaps` guard is defensive-only.

**Strip scenario (the §10.5 fragility, made concrete):** because the seal is not last (F3) and the
opt-out trio includes a *virtual* `Thu-3` not emitted by `generate_time_slots()`
(`top5_and_swaps.py:516-521`), any post-seal pass that iterates `schedule.entries` and removes by a
max-slot/boundary heuristic *without* consulting `_is_day_request_thursday_3slot` will strip the trio.
The two correct guard sites are `_remove_overlaps` (inert here, per above) and
`_fix_multislot_integrity` (guarded). A maintainer adding a boundary/overlap cleanup to the
`pipeline.py:478-553` tail — or re-invoking `_remove_overlaps` post-seal expecting it to help — would
remove `Thu-3` (slot 3 > Thursday max 2), dropping the MUST-HONOR opt-out. Additional fragility:
`_is_day_request_thursday_3slot` keys off raw `activity.slots >= 3`
(`sequencing_and_constraints.py:715-719`) while integrity math uses troop-scaled
`_get_effective_slots` (`placement_and_state.py:1713`); an activity whose raw slots round below 3 but
whose effective slots reach 3 would defeat the guard.

---

### F5 — Anchor-blocked Thursday opt-out aborts the run instead of being tolerated (S1)

**Where:** `top5_and_swaps.py:561-565` logs `UNFULFILLED` when a protected Thursday anchor blocks the
opt-out (`_force_place_thursday_3slot` returns `None` at `:504-509`); the seal then raises on **any**
unfulfilled entry:

```1979:1987:core/scheduler/legacy_parts/placement_and_state.py
        if day_request_result and day_request_result.get("unfulfilled"):
            preview = ", ".join(...)
            raise ValueError(
                "Final acceptance failed: feasible day request(s) remain unfulfilled. "
                f"Examples: {preview}"
            )
```

BRAIN §10.5 (`config/BRAIN.md:398`) states anchor blockage "cannot be placed and is logged
UNFULFILLED. This is architecturally unavoidable given anchor semantics" — i.e. it should be tolerated,
not fail the run. **Scenario:** a troop already has `Super Troop` on Thursday and
`day_requests[Thursday] = ["Back of the Moon"]`. The opt-out path detects the protected anchor and
returns `None` → appended to `unfulfilled` → seal raises → the entire week's schedule fails to
generate. The code raises on `unfulfilled` but not on `infeasible`, yet classifies this architectural
impossibility as `unfulfilled`; the two should be distinguished so anchor-blocked requests are logged
and accepted.

---

### F6 — Shadowed duplicate methods are latent MRO hazards (S3)

The class composes mixins where several in-scope methods are defined twice
(`core/constrained_scheduler.py:43-60`). Runtime introspection confirms the winners; the losers are
dead but misleading:

| Method | Winner (MRO) | Dead / shadowed | Risk |
| --- | --- | --- | --- |
| `_can_schedule` | `sequencing_and_constraints.py:725` (`*args`, has `force_day_request`) | `utilities.py:129` (positional, **enforces exclusivity unconditionally**, no force concept) | Reading the dead version implies exclusivity is always enforced — masks F1. |
| `_final_comprehensive_validation` | `placement_and_state.py:1853` (seal + acceptance gate) | `validators.py:72` (gap check only, **no seal, no gate**) | Reading the dead version implies there is no MUST-HONOR enforcement at all. |
| `_remove_overlaps` | `clustering_and_optimization.py:616` (guarded) | `phase_d_cleanup.py:257` (`pass` placeholder) | A mixin reorder would silently disable overlap removal entirely. |
| `_validate_critical_constraints` | `placement_and_state.py:2600` (**raises** on hard errors) | `validators.py:87` (print-only) | Reading the dead version implies hard violations only warn, not abort. |

MRO order is load-bearing: any reordering of the mixin list at `core/constrained_scheduler.py:43`
flips which of these wins.

---

## What is implemented correctly (verified, no action)

- **Both passes exist and are placed per §10.1:** C.1 non-aggressive at `pipeline.py:308`
  (`aggressive=False`); aggressive T1–T6 seal at `placement_and_state.py:1976`
  (`aggressive=True`, inside final validation).
- **C.1 is non-destructive:** wrong-day pulls are snapshotted and rolled back in the non-aggressive
  branch (`top5_and_swaps.py:623,642-646`); T3/T6 are gated on `aggressive`
  (`:602,:631,:642`). Only free-slot T1/T2 placements occur.
- **T4 does not cannibalize multi-day same-activity requests:** wrong-day removal is restricted to
  days *not* in the activity's requested-day set (`top5_and_swaps.py:610-622`).
- **Protected anchors + pair-protected Delta are never displaced by T5/T6:**
  `protected_anchor_names` skip (`top5_and_swaps.py:661`) and `_is_pair_protected_delta`
  (`:663`, helper `:382-402`) per §10.2/§11.
- **`force` bypasses exactly the §10.3 soft checks** (back-to-back `:795`, staff `:825`, duplicate
  `:842`, beach slot `:866`, beach cap `:924`) — the only over-reach is the exclusivity/capacity
  nesting in F1.
- **Observability (§10.6):** honored/relaxed/forced/relocated/displaced and
  INFEASIBLE/UNFULFILLED lines plus a Summary are emitted (`top5_and_swaps.py:569,579,586,
  593,607,637,683-687,701-713`).
- **`_fix_multislot_integrity` correctly preserves the opt-out trio** (virtual Thu-3) at every
  removal/boundary branch (`placement_and_state.py:1727,1751,1765,1790-1796`).
