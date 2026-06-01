# WP5 Second-Pass Audit — Day-Request MUST-HONOR Solver

Read-only second-pair-of-eyes audit against `config/BRAIN.md` §1, §2, §5, §10, and §11. Source behavior was traced through the `ConstrainedScheduler` MRO in `core/constrained_scheduler.py:43-60`; the relevant winners are `Top5AndSwapsMixin._schedule_day_requests`, `SequencingAndConstraintsMixin._can_schedule`, `ClusteringAndOptimizationMixin._remove_overlaps`, and `PlacementAndStateMixin._final_comprehensive_validation`.

## Executive verdict: Partially confirmed

I confirm the first WP5 report's core concern that day-request enforcement is not fully sealed at the end, and I confirm the Exemption-4 and anchor-blocked opt-out findings. I dispute one important subclaim in F-04: T3/T6 do not currently double-book ordinary exclusive activities through `_schedule_day_requests`, because `_add_to_schedule()` calls `Schedule.add_entry()`, and `add_entry()` re-checks `is_activity_available()`. However, F-04 should stay high severity after correction: `force_day_request` still makes the winning `_can_schedule()` predicate lie about physical availability, still bypasses aggregate canoe capacity, and the solver's T5/T6 ladder cannot displace global exclusive blockers.

I found one missed current S0/S1-class issue: post-seal mutators can concretely undo honored day requests, especially day-requested filler activities in the final filler audit and day-requested staffed beach activities in the beach saturation fixer. This is stronger than the first report's S2 "seal is not last" framing.

## Findings table

| ID | Severity | Status vs first report | Primary file:line | Short issue |
| --- | --- | --- | --- | --- |
| WP5-SP1 | **S0** | **Upgrade / new concrete form of WP5-F3** | `core/scheduler/pipeline.py:476-553`; `core/scheduler/legacy_parts/gap_fill_and_stats.py:1611-1652`; `core/scheduler/legacy_parts/placement_and_state.py:2179-2230` | Post-seal mutators can remove or replace honored day requests with no final re-seal. |
| WP5-SP2 | **S0** | **Confirm F-02 / WP5-F2** | `core/services/unscheduled_source.py:67-87` | Exemption-4 uses rank-only logic, both masking real Top-5 misses and failing legitimate T6 exemptions. |
| WP5-SP3 | **S0** | **Partially dispute / correct F-04** | `core/scheduler/legacy_parts/sequencing_and_constraints.py:859-944`; `core/models.py:212-265,280-387` | `_can_schedule(force_day_request=True)` bypasses internal capacity/exclusivity checks, but `add_entry()` prevents ordinary exclusive double-booking; aggregate canoe capacity and predicate correctness remain broken. |
| WP5-SP4 | **S0/S1** | **New / related to F-04** | `core/scheduler/legacy_parts/top5_and_swaps.py:650-690` | T5/T6 only displace the requesting troop's own slot occupant, not another troop's non-anchor exclusive blocker. |
| WP5-SP5 | **S1** | **Confirm F-14 / WP5-F5** | `core/scheduler/legacy_parts/top5_and_swaps.py:561-565`; `core/scheduler/legacy_parts/placement_and_state.py:1979-1987` | Anchor-blocked Thursday 3-hour opt-out is logged as `UNFULFILLED` and then aborts the run. |
| WP5-SP6 | S2 | **Confirm WP5-F4, limited blast radius** | `core/scheduler/legacy_parts/clustering_and_optimization.py:616-685`; `core/scheduler/legacy_parts/placement_and_state.py:1663-1850` | `_remove_overlaps` has a Thursday opt-out guard, but the guard is inert in current flow; `_fix_multislot_integrity` is the real post-seal preservation guard. |

## Detailed findings

### WP5-SP1 — Post-seal mutators can undo honored day requests (S0)

BRAIN §10.1 says the aggressive pass runs at the end of `_final_comprehensive_validation` and is the authoritative enforcement point. The code places the seal at `placement_and_state.py:1975-1978`, but then continues mutating both inside final validation and in the pipeline tail:

- Inside final validation, when any troop has day requests, it runs `_fix_multislot_integrity()`, `_guarantee_no_gaps()`, `_guarantee_mandatory_activities()`, `_fix_beach_activity_saturation()`, more integrity/gap work, and cluster repair after the seal at `placement_and_state.py:1995-2032`.
- After `_final_comprehensive_validation()` returns, `pipeline.py:479-553` runs late soft cleanup, final filler audit, final/terminal cluster repairs, more filler audits, more integrity/gap fills, and final soft cleanup. There is a final Top-5 gate at `pipeline.py:555-564`, but no final day-request revalidation.

Two concrete current failure paths:

1. Day-requested filler replacement. `_finalize_filler_replacement_audit()` targets `FINAL_AUDIT_FILLER_ACTIVITIES` from SKULL, including `Campsite Free Time`, `Gaga Ball`, `9 Square`, `Fishing`, `Trading Post`, `Dr. DNA`, `Shower House`, and `Sauna` (`config/SKULL.json:863-871`). It removes a filler entry at `gap_fill_and_stats.py:1648`, checks only whether the replacement preference can schedule into that slot at `:1650-1652`, and commits if Top-5/Top-10 guards pass at `:1674-1684`. It never asks whether the removed filler was the honored day-requested activity. Scenario: a troop has `day_requests["Monday"] = ["Campsite Free Time"]`, the seal honors it, and the final audit later sees that `Campsite Free Time` is a generic filler and replaces it with an unscheduled higher preference in the same Monday slot. The final schedule no longer contains the authored day-requested activity, and no later pass notices.

2. Beach saturation after the seal. `_fix_beach_activity_saturation()` removes the lowest-value staffed beach victim at `placement_and_state.py:2196-2227` and either moves it with direct `schedule.add_entry()` or replaces it with a fallback. It does not protect day-requested victims and does not call `_can_schedule()` with the day-request gate. This matters because BRAIN §10.3 explicitly allows `force_day_request` to bypass beach staff cap/slot soft checks, but final validation re-enforces saturation after the seal at `placement_and_state.py:2002`. Scenario: a non-Top-5 beach activity is day-requested into an already saturated beach slot. The seal places or preserves it; the saturation fixer chooses it as the lowest-value victim and moves/replaces it. The final Top-5 gate still passes, but the day request is gone.

This should be promoted above the first report's S2 "seal is not last" note: there are real current paths, not only future-maintenance risk.

### WP5-SP2 — Exemption-4 / T6 miss tagging is rank-only and wrong both ways (S0)

Confirmed. `unscheduled_source.py:67-87` decides that an honored day request displaced a missing preference only when the honored day request has a worse numeric rank than the missing preference. BRAIN §2 says a miss is exempt when an honored day request occupies a slot the Top-5 would have needed; BRAIN §10.2 says T6-created Top-5 misses are exempt. Neither condition is a pure rank comparison.

Failing scenarios:

- False accept: an unranked or low-ranked honored day request exists somewhere in the week, and an unrelated Top-5 miss exists for a different day/slot. `_day_request_displaces_preference()` returns true because `999 > missing_rank`, masking the real non-exempt miss.
- False abort: T6 honors a day request by displacing a better-ranked Top-5 activity from the needed slot. Because the honored request outranks or equals the missing activity, `honored_rank > missing_rank` is false, so the miss remains non-exempt and the final acceptance gate can raise at `placement_and_state.py:2033-2042`.

The fix needs slot/day evidence or explicit displacement provenance, not only preference rank.

### WP5-SP3 — `force_day_request` behavior needs corrected diagnosis (S0)

The first WP5 report is directionally right that the winning `_can_schedule()` violates BRAIN §10.3, but one subclaim is overstated.

What `force_day_request=True` actually bypasses in `_can_schedule()`:

- Back-to-back Delta/Tower/ODS check: bypassed by `if not force_day_request` at `sequencing_and_constraints.py:795-800`.
- Global staff limit: bypassed at `sequencing_and_constraints.py:825-827`.
- Duplicate prevention: bypassed at `sequencing_and_constraints.py:842-844`.
- Beach slot rule, beach staffed count, capacity-aware availability block, and model-level `is_activity_available()` call: all skipped because they are nested under `if activity.name not in self.CONCURRENT_ACTIVITIES and not force_day_request` at `sequencing_and_constraints.py:859-944`.

But `_schedule_day_requests()` does not directly append ordinary T3/T5/T6 placements. `_try_place()` calls `_add_to_schedule()` after `_can_schedule()` at `top5_and_swaps.py:463-471`, and T5/T6 do the same at `top5_and_swaps.py:674-677`. `_add_to_schedule()` delegates to `Schedule.add_entry()` at `placement_and_state.py:65-72`. `Schedule.add_entry()` re-checks `is_troop_free()` and `is_activity_available()` at `core/models.py:212-219`, plus continuation availability at `:231-255`. `is_activity_available()` rejects same-name conflicts and same exclusive-area conflicts at `core/models.py:293-348`, with explicit exceptions for configured concurrent activities, Aqua Trampoline, Water Polo, and Sailing.

So the ordinary exclusive double-booking scenario in the first report should be downgraded/disputed: a forced Archery placement into an occupied Archery slot makes `_can_schedule()` return true, but `add_entry()` rejects it.

What remains broken:

- The `_can_schedule()` predicate itself is unsafe for callers that trust it as a complete feasibility answer. It says a forced exclusive placement is legal when the model add will reject it.
- Aggregate canoe capacity still can be bypassed. The in-method aggregate canoe cap is relax-gated at `sequencing_and_constraints.py:1308-1311`, T3/T5/T6 call with `relax_constraints=True`, and `Schedule.is_activity_available()` does not enforce the cross-canoe-family 26-person cap. It checks same-name/area conflicts and beach staff limits, but not total canoe people across `Troop Canoe`, `Nature Canoe`, `Canoe Snorkel`, `Float for Floats`, and `Troop Kayak`.
- `force_day_request` does not reliably bypass beach staff cap as BRAIN §10.3 says it may. Even when `_can_schedule()` skips the beach staff check, `Schedule.is_activity_available()` re-applies beach staff/activity limits at `core/models.py:371-385`, so a MUST-HONOR beach request can remain unfulfilled.

Recommended correction to `FINDINGS.md` F-04: keep it S0 because canoe capacity and force-predicate correctness are real hard-contract risks, but change the title away from "bypasses physical exclusivity" to "force predicate bypasses capacity/exclusivity checks; add-entry backstop only partially saves it."

### WP5-SP4 — T5/T6 displacement only clears same-troop blockers (S0/S1)

BRAIN §10.2 says T5 displaces a non-anchor non-Top-5 occupant on the requested day, and T6 displaces a non-anchor Top-5 occupant as the last resort. The implementation's displacement loop only looks for an occupant where `e.troop == troop and e.time_slot == target_slot` at `top5_and_swaps.py:653-657`.

That is enough when the requesting troop's own slot is the blocker. It is not enough when physical availability is blocked by another troop already holding the requested exclusive activity or a capacity-limited resource. Because `Schedule.add_entry()` correctly rejects global exclusive conflicts, a day request can fail even though a BRAIN-authorized displacement exists.

Failing scenario:

- Troop B day-requests `Archery` on Thursday.
- Troop A already holds `Archery` in every Thursday slot, and none of those entries are protected anchors.
- Troop B has displaceable same-troop fillers in those slots.
- T3 `_can_schedule(force=True)` says a target slot is feasible, but `_add_to_schedule()` rejects it because `Archery` is globally unavailable.
- T5/T6 displace only Troop B's own fillers/Top-5s, never Troop A's non-anchor `Archery` occupant.
- The request is logged `UNFULFILLED` at `top5_and_swaps.py:697-701` and the final validation raises at `placement_and_state.py:1979-1987`.

If BRAIN intended "occupant" to mean only the requesting troop's schedule, this should be documented. As written, the MUST-HONOR solver cannot satisfy feasible requests that require displacing another troop's non-anchor exclusive/capacity occupant.

### WP5-SP5 — Anchor-blocked Thursday opt-out aborts instead of being tolerated (S1)

Confirmed. The Thursday 3-hour opt-out path is final-pass only at `top5_and_swaps.py:558-570`. `_force_place_thursday_3slot()` refuses to displace protected Thursday anchors at `top5_and_swaps.py:499-509`; the caller records that as `UNFULFILLED` at `:561-565`. `_final_comprehensive_validation()` then raises on any `unfulfilled` result at `placement_and_state.py:1979-1987`.

BRAIN §10.5 explicitly says anchor blockage is architecturally unavoidable and should be logged `UNFULFILLED`. The current behavior turns that tolerated physical impossibility into a whole-week generation failure.

Failing scenario: a troop has Thursday `Super Troop` and `day_requests["Thursday"] = ["Back of the Moon"]`. The opt-out path cannot clear the protected anchor, logs `UNFULFILLED`, and the final seal raises.

### WP5-SP6 — Thursday opt-out preservation is real in integrity, inert in overlaps (S2)

The opt-out creation path is mostly correct:

- It is final-pass only at `top5_and_swaps.py:558-560`.
- It clears non-anchor Thursday entries and appends `ScheduleEntry` rows for virtual Thursday slots 1, 2, and 3 at `top5_and_swaps.py:511-521`.
- `_is_day_request_thursday_3slot()` gates on literal Thursday day requests and a 3-slot activity at `sequencing_and_constraints.py:704-723`.
- `_fix_multislot_integrity()` preserves and reconstructs virtual Thu-3 through its special cases at `placement_and_state.py:1727-1729`, `:1747-1754`, `:1762-1768`, and `:1786-1796`.

The `_remove_overlaps()` guard at `clustering_and_optimization.py:679-685` is correct in isolation but inert in current flow: `_remove_overlaps()` runs from D.11 `_comprehensive_final_cleanup()` before the aggressive seal, while the opt-out trio is created only inside the aggressive seal. It is still useful as defense if `_remove_overlaps()` is ever invoked post-seal, but it is not currently load-bearing.

## Comparison against `review/FINDINGS.md`

- **F-02 (S0): Confirm.** The rank-only Exemption-4 heuristic is wrong both ways. Keep severity/order.
- **F-04 (S0): Partially confirm, wording should change.** The internal `_can_schedule(force_day_request=True)` check bypasses physical availability/capacity checks, but normal T3/T5/T6 placements still hit `Schedule.add_entry()`, which prevents ordinary exclusive double-booking. Keep S0 due aggregate canoe-capacity bypass and the unsafe predicate, but narrow the title/description.
- **F-14 (S1): Confirm.** Anchor-blocked opt-out currently raises. Keep as S1 unless the team classifies all avoidable generation aborts as S0.
- **Related S2/S3:** Upgrade the first WP5 seal-order finding from S2 risk to a new S0/S1 backlog item because current post-seal code can remove honored day requests. Keep MRO-shadowing as S3, but note that reading `utilities._can_schedule` instead of the MRO winner is exactly how the F-04 physical-exclusivity conclusion can become inaccurate.

## Regression-test recommendations

1. Add a day-request seal test where `Campsite Free Time` or `Shower House` is day-requested and later eligible for `_finalize_filler_replacement_audit()`; assert the returned schedule still honors the day request after the entire `schedule_all()` tail.
2. Add a post-seal beach saturation test with a day-requested staffed beach entry in an over-cap slot; assert either the request remains honored or the request is logged as an accepted infeasible case, not silently replaced.
3. Add a `force_day_request` predicate-vs-add test: `_can_schedule(... force=True)` must not return true for a physically unavailable exclusive slot, or callers must never rely on it without `add_entry()`.
4. Add aggregate canoe-capacity tests for forced/relaxed day requests across different canoe-family activities in the same slot.
5. Add a T5/T6 global-blocker test: another troop's non-anchor exclusive occupant blocks a day request; assert the intended behavior is either displacement or explicit `INFEASIBLE`, not generic `UNFULFILLED` plus whole-run abort.
6. Add Thursday opt-out tests for both success (`Thu-1/2/3` virtual trio survives all final tail passes) and anchor blockage (logged/tolerated per §10.5).
7. Add Exemption-4 unit tests with explicit slot provenance: unrelated honored day requests must not exempt a Top-5 miss; actual T6 displacement must exempt the displaced Top-5.

## Final summary

The day-request architecture is present but not actually terminal.
C.1 is non-aggressive, and the final aggressive ladder exists.
T4 anti-cannibalization is implemented correctly.
Thursday opt-out creation and `_fix_multislot_integrity` preservation are mostly correct.
The first report's Exemption-4 and anchor-blocked opt-out findings are confirmed.
The first report's physical-exclusivity part of F-04 should be corrected, not copied verbatim.
New priority: add an S0/S1 finding for post-seal mutators that can currently undo honored day requests.
FINDINGS.md severity/order should add that new item near the existing S0 day-request findings and revise F-04 wording while keeping it high priority.
