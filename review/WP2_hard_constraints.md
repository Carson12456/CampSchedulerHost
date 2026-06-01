# WP2 — HARD Constraint Audit (BRAIN §4)

Read-only logic audit. Scope: `core/scheduler/validators.py`, `core/scheduler/constraints.py`,
`core/scheduler/legacy_parts/sequencing_and_constraints.py` (`_can_schedule` + helpers), and
`_enforce_sailing_slot_exclusivity` in `core/scheduler/pipeline.py`. No source code was modified.

## MRO context (load-bearing)
`ConstrainedScheduler` base order (`core/constrained_scheduler.py:43-60`):
`LegacyInterface → PlacementAndState(#2) → Top5AndSwaps(#3) → PreferenceAndLimited(#4) →
SequencingAndConstraints(#5) → … → SchedulerState → Pipeline → Utility(#12) → Validator(#13) → PhaseA/B/D`.

Authoritative predicate sources after MRO resolution:
- `_can_schedule` → **`sequencing_and_constraints.py:725`** wins. `utilities.py:129` (`_can_schedule(slot, activity, troop)`) is **dead/shadowed**.
- `_final_comprehensive_validation` → **`placement_and_state.py:1853`** wins; `validators.py:72` is **dead/shadowed**.
- `_comprehensive_gap_check` → **`placement_and_state.py:1625`** (cluster-gap semantics) wins; `validators.py:218` is shadowed.

## Summary table

| HARD rule | Verdict | Severity | Key predicate (file:line) |
| --- | --- | --- | --- |
| Exclusive double-booking (general) | PASS | — | `sequencing_and_constraints.py:938-944`; `models.py:217,280-355` |
| Sailing slot-2 overlap (search-time 1-or-2) | PASS | — | `_can_schedule_sailing` `sequencing_and_constraints.py:1757`; `_check_activity_capacity` `:1415-1444` |
| Sailing final normalization (s1≤1,s2≤2,s3≤1) | PASS | — | `_enforce_sailing_slot_exclusivity` `pipeline.py:13-76` |
| `force_day_request` skips exclusivity/capacity predicate | FLAG | S2 | `sequencing_and_constraints.py:859` (`not force_day_request` gate) |
| Completeness (no empty troop slots) | PASS* | S3 | `validators.py:198`; `placement_and_state.py:1853,1861,1869,1875,1883` |
| Reflection = Friday | FLAG (no predicate) | S2 | absent in `_can_schedule`; helper `:654-660` unused |
| Super Troop weekly ×1 (upper bound) | PASS | — | `_can_schedule_on_day` `:1865-1869` |
| History Center / Disc Golf = Tuesday only | PASS | — | `_can_schedule` `:1088-1091` (unconditional) |
| Delta ↔ Tower/ODS not adjacent (both directions) | PASS | — | `_can_schedule` `:1152-1164`; cfg `config_loader.py:274-304` |
| Canoe capacity 26 | FLAG | S2 | `:1308-1311` (relax-gated, scouts-only) vs `:1461-1465` (scouts+adults) |
| Global staff 16 (elevated for clustering) | PASS | — | `_can_schedule` `:802-827` |
| Beach staff 12 / slot | PASS (model only) | S3 | not in `_can_schedule`; `models.py:371-385` |
| Beach saturation 4 (→5 Top-5 AT) | PASS | — | `_can_schedule` `:922-932` |
| Shower House — no Monday | PASS | — | `_can_schedule` `:959-961` (unconditional) |
| Shower House — not before later Super Troop/wet | FLAG | S2 | `_can_schedule` `:963-974` (relax-gated + order-dependent) |
| Dead/shadowed predicates | NOTE | S3 | `utilities.py:129`; `validators.py:72,218` |

\*Completeness delegates the actual fill to `_guarantee_no_gaps` (`gap_fill_and_stats.py:1779`, out of scope); the in-scope detection/gating is correct.

---

## Detailed findings

### 1. Exclusive double-booking + Sailing slot-2 exception — PASS (with S2 caveat)

**Search-time, non-Sailing exclusives.** `_can_schedule` routes capacity-checked activities through
`_check_activity_capacity` and everything else through the model gate:

```938:944:core/scheduler/legacy_parts/sequencing_and_constraints.py
            if activity.name in CAPACITY_CHECK_ACTIVITIES:
                allow_top5_overload = (relax_constraints and activity.name == 'Aqua Trampoline' and
                    activity.name in (troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences))
                if not self._check_activity_capacity(slot, activity, troop, allow_top5_at_overload=allow_top5_overload):
                    return False
            elif not self.schedule.is_activity_available(slot, activity, troop):
                return False
```

`Schedule.is_activity_available` (`models.py:280-355`) enforces per-area/per-name exclusivity, and
`Schedule.add_entry` (`models.py:212-219`) re-runs both `is_troop_free` and `is_activity_available`
on **every** add — so exclusivity has a model-layer backstop independent of `_can_schedule`.

**Sailing slot-2 overlap.** Two independent layers agree with BRAIN §4 (search-time slot 2 may hold 1-or-2):
- `_can_schedule_sailing` (`:1757-1838`): start detected via "no same-troop Sailing in `prev_num`"; duplicate starts blocked (`:1795`); ≤2 starts/day non-Thursday (`:1800`), Thursday ⇒ slot 1 only.
- `_check_activity_capacity` Sailing branch (`:1415-1444`): identical start logic, max 2 starts/day.

A start at slot 1 occupies {1,2}; a start at slot 2 occupies {2,3}; two starts (slot 1 + slot 2) put exactly 2 occupancies in slot 2 — the formal overlap. Verified correct.

**S2 — `force_day_request` bypasses the exclusivity/capacity predicate.** The entire capacity/exclusivity/beach block is gated:

```859:859:core/scheduler/legacy_parts/sequencing_and_constraints.py
        if activity.name not in self.CONCURRENT_ACTIVITIES and not force_day_request:
```

So `_can_schedule(..., force_day_request=True)` returns `True` without checking `_check_activity_capacity`
or `is_activity_available`. BRAIN §10.3 explicitly states that under `force_day_request` "physical
exclusivity" **remains enforced** — the predicate violates that contract. In practice the model-layer
`add_entry` backstop (`models.py:217`) prevents a real double-booking, and the T5/T6 tiers displace the
occupant before adding. The exception is the Thursday-3hr opt-out path (BRAIN §10.4) which "directly
appends three `ScheduleEntry` rows," bypassing `add_entry` validation entirely. **Concrete risk:** any
future caller that places on the strength of `_can_schedule(force_day_request=True)` alone, or appends
entries directly, can double-book an exclusive area. Severity S2: contract/comment mismatch, currently
defended in depth, not independently safe.

### 2. Sailing final normalizer `_enforce_sailing_slot_exclusivity` — PASS

```13:52:core/scheduler/pipeline.py
    def _enforce_sailing_slot_exclusivity(self) -> None:
        ...
        sailing_starts = []
        for entry in self.schedule.entries:
            if entry.activity.name != "Sailing":
                continue
            prev_slot_num = entry.time_slot.slot_number - 1
            has_prev = any(
                e.activity.name == "Sailing"
                and e.troop == entry.troop
                and e.time_slot.day == entry.time_slot.day
                and e.time_slot.slot_number == prev_slot_num
                for e in self.schedule.entries
            )
            if not has_prev:
                sailing_starts.append(entry)
        ...
            allowed = 2 if day != Day.THURSDAY and slot_num == 2 else 1
```

**`has_prev` 3-slot mis-count check (requested):** `has_prev` matches only the **same troop** in the
immediately-preceding slot. A troop has at most one Sailing instance (duplicate prevention +
`is_troop_free`), so a real start can never be masked by another troop's continuation ⇒ **no under-count**
(over-capacity cannot slip through). Occupancy fan-out `occupied = [n] + ([n+1] if n < 3]` is correct at
the slot-3 boundary (start@1⇒{1,2}, start@2⇒{2,3}, illegal start@3⇒{3} only). Result: slot 1 only
receives slot-1 starts (≤1), slot 2 receives slot-1 + slot-2 starts (≤2), slot 3 receives slot-2 starts
(≤1) — exactly the BRAIN model. A degenerate orphan continuation (start removed elsewhere) is treated as
a start, which **over**-counts — the safe direction.

`_remove_from_schedule` (`placement_and_state.py:169-240`) removes the whole multi-slot instance
(start + continuation), so removal at `pipeline.py:76` leaves no orphaned Sailing half. The resulting
empty slots are refilled by `_guarantee_no_gaps()` called immediately after (`placement_and_state.py:1883`).
Minor note: when no legal relocation exists, the lowest-priority Sailing is dropped (`:74-76`); if 3+ troops
genuinely over-saturate, a Top-5 Sailing could be dropped, but the subsequent Top-5 repair loop
(`placement_and_state.py:1892+`) is the recovery path. Not a normalizer defect.

### 3. Completeness — PASS* (S3 diagnostic)

Empty-slot detection is correct and Thursday-aware:

```204:216:core/scheduler/validators.py
        slots_per_day = {
            Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
            Day.THURSDAY: 2, Day.FRIDAY: 3
        }
        ...
                    if slot and self.schedule.is_troop_free(slot, troop):
                        total += 1
```

The **active** final gate (`placement_and_state.py:1853`) calls `_guarantee_no_gaps()` unconditionally
five times, including after every destructive normalization (`:1861, :1869, :1875, :1883`). So completeness
is structurally re-asserted at the last exit.

**S3 (diagnostic):** inside that gate `self._comprehensive_gap_check("Final Validation")` resolves (MRO) to
the **cluster-gap** override (`placement_and_state.py:1625`), not the troop-empty-slot counter, so the
"Found N gaps" log measures area `1,-,3` patterns rather than empty troop slots. Harmless because
`_guarantee_no_gaps` runs unconditionally regardless of the printed count, but the log is misleading and the
actual completeness guarantee lives in the out-of-scope `_guarantee_no_gaps` (`gap_fill_and_stats.py:1779`).

### 4. Mandatory anchors

- **HC/DG Tuesday-only — PASS.** Unconditional gate (not relaxed, not force-bypassed):

```1088:1091:core/scheduler/legacy_parts/sequencing_and_constraints.py
        if activity.name in self.TUESDAY_ONLY_ACTIVITIES:
            if day != Day.TUESDAY:
                return False
```

`TUESDAY_ONLY_ACTIVITIES = {History Center, Disc Golf}` (SKULL `tuesday_only_activities`). Even a Monday
day-request for HC/DG is correctly rejected (matches §1 ladder: anchor days are hard).

- **Super Troop weekly ×1 — PASS (upper bound).** `_can_schedule_on_day:1865-1869` blocks a 2nd
`Delta`/`Super Troop`. "At least one" placement is owned by the Super-Troop phase /
`_guarantee_mandatory_activities` (`placement_and_state.py:1884`), not `_can_schedule`.

- **Reflection = Friday — FLAG (S2).** `_can_schedule` has **no** predicate forcing Reflection onto Friday;
the only helper that knows the rule is unused by the predicate:

```654:660:core/scheduler/legacy_parts/sequencing_and_constraints.py
    def _is_hard_fixed_day(self, activity_name: str, day: Day) -> bool:
        """Return True if the activity is fixed to a specific day by hard rules."""
        if activity_name == "Reflection" and day == Day.FRIDAY:
            return True
```

Reflection is `concurrent`, so the concurrent branch (`:858`) skips exclusivity, and nothing rejects a
non-Friday Reflection. Today Reflection is only placed by the dedicated Friday phase, so the gap is latent,
but **scenario:** a swap/fill pass (or a `relax`/`force` placement) that calls `_can_schedule` for
`Reflection` on, say, Wednesday would pass the predicate. Validators only *count* missing Friday Reflections
(`validators.py:146-157`) after the fact; they do not prevent an off-Friday placement. Recommend a hard
`if activity.name == "Reflection" and day != FRIDAY: return False` gate.

### 5. Delta ↔ Tower/ODS adjacency (both directions) — PASS

Explicit hard check covers both orderings, with `abs(slot_diff) <= 1`, and is **not** gated by `relax` or `force`:

```1152:1164:core/scheduler/legacy_parts/sequencing_and_constraints.py
        if activity.name == 'Delta':
            day_entries = [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == slot.day]
            for e in day_entries:
                if e.activity.name in self.TOWER_ODS_ACTIVITIES:
                    if abs(e.time_slot.slot_number - slot.slot_number) <= 1:
                        return False  # Adjacent slots - violation
        elif activity.name in self.TOWER_ODS_ACTIVITIES:
            day_entries = [e for e in self.schedule.entries if e.troop == troop and e.time_slot.day == slot.day]
            for e in day_entries:
                if e.activity.name == 'Delta':
                    if abs(e.time_slot.slot_number - slot.slot_number) <= 1:
                        return False  # Adjacent slots - violation
```

`TOWER_ODS_ACTIVITIES` = SKULL `tower_ods` tag (Climbing Tower + 6 ODS), matching BRAIN. The SKULL-driven
`config_loader.are_activities_not_back_to_back` (`config_loader.py:274-304`) also reads
`sequence_rules.not_back_to_back` and checks **both** `act1==activity_a`/`act2 in tag` and the reverse;
it is used at `:795-800` (an earlier gate that `force_day_request` may bypass). Because the hard explicit
check at `:1152` is unconditional, Delta/Tower-ODS adjacency holds even under `force`. A post-pass repair
`_fix_delta_tower_ods_adjacency()` runs in final validation (`placement_and_state.py:1872`). Defense in
depth, both directions. Note: `_is_far_apart`/`ODS_ACTIVITIES` (the *soft* transition check, `:1066-1086`)
uses only the Outdoor-Skills area set (excludes Climbing Tower) — acceptable because the hard check above
uses the full `TOWER_ODS_ACTIVITIES`.

### 6. Capacity

- **Canoe 26 — FLAG (S2): two divergent paths.**

```1308:1311:core/scheduler/legacy_parts/sequencing_and_constraints.py
        if not relax_constraints and activity.name in self.CANOE_ACTIVITIES:
            current_canoe_people = self._count_people_in_canoe_activities(slot)
            if current_canoe_people + troop.scouts > self.MAX_CANOE_CAPACITY:
                return False  # Would exceed canoe capacity
```

This cross-canoe-activity 26-person cap is **relax-gated** (bypassed in fill/T2+ passes) and counts
**scouts only** (`_count_people_in_canoe_activities:1371-1377` also scouts-only). The
`_check_activity_capacity` canoe branch (`:1461-1465`) instead counts **scouts + adults** but only sums the
**same** activity name (each canoe activity is its own exclusive area, so it rarely binds). **Scenario:**
two canoe activities (e.g. `Troop Canoe` 18 + `Nature Canoe` 12 = 30 people) placed during a `relax`
fill pass exceed 26; and even on the strict path adults are not counted, so a 24-scout + 4-adult troop
(28 people) reads as 24 ≤ 26. `Troop Kayak` is in the `canoe` tag but **not** in
`capacity_check_activities`, so under relax it has no capacity gate at all.

- **Global staff 16 — PASS.**

```812:827:core/scheduler/legacy_parts/sequencing_and_constraints.py
        base_staff_limit = 20 if activity.name in STAFF_CLUSTERING_ACTIVITIES else 16
        ...
        clustering_bonus = 4 if activity.name in STAFF_CLUSTERING_ACTIVITIES else 0
        staff_limit = base_staff_limit + clustering_bonus
        ...
        if activity_staff > 0 and not force_day_request:
            if current_staff + activity_staff > staff_limit:
                return False
```

Base 16; clustering activities get a controlled elevated cap of 24 — consistent with BRAIN ("base max 16;
clustering-targeted scheduling can use controlled elevated limits"). `force` bypass is sanctioned by §10.3.

- **Beach staff 12 — PASS (model layer only, S3 note).** Not present in `_can_schedule`; enforced in
`Schedule.is_activity_available` (`models.py:371-385`, role `Beach Staff`, limit `beach_staff_per_slot=12`)
and scored by `regression_checker.py:846`. In practice it is dominated by saturation-4 (4 two-staff
activities = 8 ≤ 12). Minor inconsistency: the saturation set (`BEACH_STAFFED_ACTIVITIES`, any
beach-tagged activity with staff>0, e.g. Nature Canoe) differs from the model 12-staff set (role
== "Beach Staff", which excludes Nature Canoe/Sailing).

- **Beach saturation 4 (→5 for Top-5 AT) — PASS.**

```924:932:core/scheduler/legacy_parts/sequencing_and_constraints.py
            if activity.name in self.BEACH_STAFFED_ACTIVITIES:
                existing_staffed = [e for e in self.schedule.entries 
                                   if e.time_slot == slot and e.activity.name in self.BEACH_STAFFED_ACTIVITIES]
                at_top5 = (activity.name == 'Aqua Trampoline' and relax_constraints and
                    activity.name in (troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences))
                if len(existing_staffed) >= self.MAX_BEACH_STAFFED_ACTIVITIES and not at_top5:
                    return False
                if len(existing_staffed) >= self.MAX_BEACH_STAFFED_ACTIVITIES + 1:
                    return False  # Never more than 5 (4 + 1 Top 5 overload)
```

Max 4; the 5th is allowed only when it is a Top-5 Aqua Trampoline under `relax`; never 6. Matches BRAIN exactly.

### 7. Shower House

- **No Monday — PASS.** Unconditional (cannot be relaxed or forced):

```959:961:core/scheduler/legacy_parts/sequencing_and_constraints.py
        if activity.name == "Shower House" and day == Day.MONDAY:
            return False
```

- **Not before a later Super Troop / wet activity (same day) — FLAG (S2).**

```965:974:core/scheduler/legacy_parts/sequencing_and_constraints.py
        if activity.name == "Shower House" and not relax_constraints:
            day_slots = [s for s in self.time_slots if s.day == day]
            for entry in self.schedule.get_troop_schedule(troop):
                if entry.time_slot in day_slots and entry.time_slot.slot_number > slot.slot_number:
                    if entry.activity.name == "Super Troop" or entry.activity.name in self.WET_ACTIVITIES:
                        return False
```

Two weaknesses for a rule BRAIN lists under HARD ("strict mode"): (a) `not relax_constraints` ⇒ any fill/recovery
pass that relaxes can place Shower House before a wet/Super-Troop slot; (b) it is **order-dependent** — it only
inspects activities **already** placed later in the day. **Scenario:** Shower House placed in slot 1 while
slots 2-3 are empty passes; a wet activity or Super Troop is then placed in slot 3. The wet/Super-Troop
placement does not re-check for an earlier Shower House (wet placement only guards Tower/ODS adjacency and the
1-2-3 wet pattern), so the forbidden ordering survives. There is no final-validation repair for this ordering.

---

## MRO shadowing notes (S3)
- **`utilities.py:129 _can_schedule(slot, activity, troop)` is dead.** It implements a *weaker* constraint
  set (e.g. beach slot-2 only allows `priority < 5`, no canoe/Delta/wet-pattern/Shower-House logic). It is
  shadowed by `sequencing_and_constraints.py:725` purely due to base-class order; reordering the mixins would
  silently swap in the weaker predicate. Recommend deleting it or routing it to the canonical method.
- **`validators.py:72 _final_comprehensive_validation` and `:218 _comprehensive_gap_check` are dead**,
  shadowed by the `placement_and_state.py` copies. The active and dead `_final_comprehensive_validation`
  differ substantially (the active one runs the Sailing/exclusivity/Delta-adjacency normalizers); auditing the
  validators.py copy alone would misrepresent runtime behavior.

---

## Executive summary
The HARD physical invariants are largely correct and defended in depth. Exclusive double-booking, the Sailing
slot-2 overlap (search-time 1-or-2) and its final normalizer (slot1≤1/slot2≤2/slot3≤1), Delta↔Tower/ODS
non-adjacency (both directions), HC/DG Tuesday-only, Super Troop once-weekly, global staff 16, beach
saturation 4→5, and Shower-House-no-Monday all verify. The `has_prev` start detection in
`_enforce_sailing_slot_exclusivity` is sound: it keys on the same troop only, so it cannot under-count a
3-slot day, and its slot-3 fan-out boundary is correct. No S0/S1 break was found in the audited predicates.
Five issues warrant attention: (S2) `force_day_request` skips the entire exclusivity/capacity predicate
block, contradicting BRAIN §10.3 and relying solely on the `add_entry` model backstop — fragile for the
direct-append Thursday opt-out path; (S2) canoe-26 has two divergent enforcement paths (relax-gated +
scouts-only vs scouts+adults), so >26 real people can be seated under relaxed fills and `Troop Kayak` is
ungated; (S2) Reflection=Friday has no predicate in `_can_schedule` (only a post-hoc counter); (S2) the
Shower-House "not before wet/Super-Troop" rule is relax-gated and order-dependent, so the forbidden ordering
can survive; (S3) several dead/shadowed copies (`utilities.py:129`, `validators.py:72/218`) — notably a
weaker `_can_schedule` that would activate if mixin order changed. Completeness is structurally re-asserted
by the active final gate but the actual fill lives in the out-of-scope `_guarantee_no_gaps`.
