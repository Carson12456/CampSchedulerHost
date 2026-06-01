# WP3 Second-Pass Audit - Top-5 Contract

Read-only second-pair-of-eyes logic audit. No source code was edited.

## Executive Verdict

Confirmed, with one scope expansion under F-11.

The first WP3 report's core conclusion is sound: the final acceptance gate raises when `_count_non_exempt_top5_misses()` returns a positive count, but the gate is only as correct as the `is_exempt` flags produced by `core/services/unscheduled_source.py`. I independently confirm F-01, F-02, and F-03 as S0 false-accept risks. I also confirm F-11 as a real Delta/Sailing pair-protection gap and found additional live final Top-5 repair call sites that should be included in that same finding, not promoted ahead of the S0 items.

## Findings Table

| ID | Severity | Status vs first report | Primary file:line | Short issue |
| --- | --- | --- | --- | --- |
| WP3-SP1 / F-01 | S0 | Confirmed | `core/services/unscheduled_source.py:37`, `core/services/unscheduled_source.py:106` | HC/DG exemption uses Tuesday slot occupancy only; it does not enforce combined top-3 ranking and has conflicting capacity semantics. |
| WP3-SP2 / F-02 | S0 | Confirmed | `core/services/unscheduled_source.py:41`, `core/services/unscheduled_source.py:67` | Day-request displacement exemption is a rank heuristic, not proof that an honored day request occupied a needed Top-5 slot. |
| WP3-SP3 / F-03 | S0 | Confirmed | `core/services/unscheduled_source.py:39`, `core/services/unscheduled_source.py:124` | Canoe-family exemption ignores BRAIN's two-hour qualifier. |
| WP3-SP4 / F-11 | S1/S2 | Confirmed and expanded | `core/scheduler/legacy_parts/top5_and_swaps.py:2732`, `core/scheduler/legacy_parts/placement_and_state.py:2781`, `core/scheduler/legacy_parts/placement_and_state.py:3097` | Pair-protected Delta can still be removed by Top-5 enforcement and final repair helpers. |
| WP3-SP5 | S3 | Confirmed latent only | `core/scheduler/phase_b_core.py:34`, `core/scheduler/phase_b_core.py:109`, `core/scheduler/phase_b_core.py:145` | Shadowed Phase B methods are unsafe if MRO changes, but not live with current composition. |

## Detailed Findings

### WP3-SP1 / F-01 - HC/DG Tuesday Saturation Exemption Is Unsound - S0

BRAIN requires HC/DG exemption to respect combined top-3 semantics. The source builder instead computes a single boolean from whether Tuesday slots 1, 2, and 3 contain any HC-or-DG entry:

- `core/services/unscheduled_source.py:106-110` builds `tuesday_hc_dg_slots`.
- `core/services/unscheduled_source.py:37` exempts every missing `History Center` or `Disc Golf` when that boolean is true.
- `core/scheduler/legacy_parts/top5_and_swaps.py:1763-1884` schedules HC and DG in separate top-three loops, not from one combined ranked list.
- `core/models.py:287-348` and SKULL `exclusive_areas` model HC and DG as separate exclusive activities, so physical capacity semantics differ from the BRAIN wording and from the exemption's one-pool boolean.

Failing scenario: Tuesday slot 1, 2, and 3 each contain History Center entries. A troop whose combined HC/DG request is rank 1 misses Disc Golf. The exemption sees `{1, 2, 3}` and marks the miss exempt, even though the troop is inside the combined top-3 and should be non-exempt. Depending on which capacity model is intended, the same code either ignores combined ranking or prematurely declares the combined pool saturated. Both interpretations can mask a real Top-5 miss.

This is a false-accept path: `is_exempt=True` suppresses the miss, `_count_non_exempt_top5_misses()` sees zero, and the final gate passes a schedule that violates BRAIN.

### WP3-SP2 / F-02 - Day-Request Displacement Exemption Is Not Slot-Based - S0

BRAIN's exemption is slot-causal: a missed Top-5 is exempt when the missed activity is itself day-requested, or an honored day-request occupies a slot the Top-5 would have needed. The implementation does not check a slot, day, activity duration, or actual displacement.

- `core/services/unscheduled_source.py:41-44` trusts the boolean `day_request_displaces`.
- `core/services/unscheduled_source.py:67-87` sets that boolean when any honored day-request is lower-ranked or unranked relative to the miss.
- `core/models.py:139-143` returns `999` for unranked activities, so an honored unranked day request blanket-exempts higher-ranked Top-5 misses.

False-accept scenario: a troop has an honored unranked day request on Friday slot 3, and independently misses its rank-1 activity that could have fit on Tuesday. `_day_request_displaces_preference()` returns true because `999 > 1`; the rank-1 miss becomes exempt even though the honored day request did not occupy a needed slot.

False-reject scenario: a legitimate T6 day-request placement displaces a better-ranked Top-5 in the only feasible slot. If the honored request outranks the missed activity, the rank comparison returns false even though BRAIN says day requests supersede Top-5. That direction fails closed by aborting a valid run, but it is still contract drift.

### WP3-SP3 / F-03 - Canoe Duplication Exemption Ignores Two-Hour Scope - S0

BRAIN exempts a missed canoe only when the troop already has one two-hour activity and misses another two-hour canoe activity. The implementation checks only canoe-family membership.

- `core/services/unscheduled_source.py:21-24` loads all `canoe` tagged activities.
- `core/services/unscheduled_source.py:39` exempts any canoe-family miss when `has_other_canoe_family_scheduled` is true.
- `core/services/unscheduled_source.py:124-130` sets that boolean for any other scheduled canoe-family activity.
- SKULL includes one-hour canoe-family activities (`Troop Canoe`, `Nature Canoe`, `Troop Kayak`) and two-hour canoe-family activities (`Canoe Snorkel`, `Float for Floats`).

Failing scenario: a troop ranks `Troop Canoe` and `Nature Canoe` in its Top 5. It receives `Nature Canoe` and misses `Troop Canoe`. Both are one-hour activities and can plausibly co-fit, but the code treats the miss as exempt because another canoe-family activity is scheduled.

This is another false-accept path because the final count relies on `is_exempt`.

### WP3-SP4 / F-11 - Pair-Protected Delta Coverage Is Incomplete - S1/S2

BRAIN section 11 says a `Delta` entry is protected when the same troop has `Sailing` scheduled. The helper exists and works as a predicate:

- `core/scheduler/legacy_parts/top5_and_swaps.py:382-402` defines `_is_pair_protected_delta()`.

Several live displacement sites use it correctly:

- `_force_top1_preferences()` skips pair-protected Delta at `core/scheduler/legacy_parts/top5_and_swaps.py:1236-1242`.
- `_schedule_preferences_range()` skips it at `core/scheduler/legacy_parts/top5_and_swaps.py:1995-2002`.
- `_guarantee_all_top5()` skips it at `core/scheduler/legacy_parts/top5_and_swaps.py:2372-2376`.
- The day-request T5/T6 displacement loop skips it at `core/scheduler/legacy_parts/top5_and_swaps.py:640-690`.

But the coverage is not complete:

- `_enforce_mandatory_top5()` filters only `PROTECTED` and priority at `core/scheduler/legacy_parts/top5_and_swaps.py:2730-2733`; Delta is single-slot and is not in the multi-slot protected set.
- `_force_place_with_window_clearing()` blocks only names in `protected_names` at `core/scheduler/legacy_parts/placement_and_state.py:2781-2788`.
- `_reclaim_activity_from_lower_priority_troop()` blocks only names in `protected_names` at `core/scheduler/legacy_parts/placement_and_state.py:2871` and target conflicts at `core/scheduler/legacy_parts/placement_and_state.py:2907`.
- `_try_place_with_displacement_recovery()` skips windows only by `protected_names` at `core/scheduler/legacy_parts/placement_and_state.py:3010-3024`.
- `_attempt_global_top5_repair_step()` can directly remove a lower-priority holder at `core/scheduler/legacy_parts/placement_and_state.py:3097-3115` without checking `_is_pair_protected_delta()`.
- `_bounded_top5_reoptimization()` calls these helpers with only `self.NON_DISPLACEABLE_ACTIVITIES` at `core/scheduler/legacy_parts/top5_and_swaps.py:99-147`, so final repair can be less protective than the earlier Top-5 loops.

Failing scenario: a troop has `Sailing` scheduled and a paired `Delta` entry, with Delta ranked outside Top 5. During mandatory or final Top-5 repair, the scheduler needs a lower-priority occupant to clear a slot/window. Because Delta is single-slot and not in `PROTECTED`, these paths can remove it, keep the Top-5 count at zero, and leave the Delta/Sailing pair split after B.6 has already run.

I keep this at S1/S2 rather than S0 because it does not itself create a non-exempt Top-5 miss. It is still a BRAIN section 11 contract mismatch and can affect scoring/quality because late final repair has no guaranteed B.6 re-pairing backstop.

### Source-of-Truth and Gate Clearances

I confirm the main acceptance/reporting path is not using an independent authoritative miss list:

- `_count_non_exempt_top5_misses()` builds the canonical unscheduled payload through `build_unscheduled_data()` and counts only `unscheduled[*].top5[*].is_exempt == False` at `core/scheduler/legacy_parts/placement_and_state.py:2714-2732`.
- `UnscheduledAnalyzer` fails fast if schedule JSON lacks `unscheduled` at `core/services/unscheduled_analyzer.py:90-99`, then reads `top5` items directly at `core/services/unscheduled_analyzer.py:141-179`.
- `summarize_non_exempt_misses()` counts only the unscheduled payload at `core/services/unscheduled_source.py:187-201`.
- `utils/regression_checker.py:1006-1020` loads `schedule_json.unscheduled`, uses `summarize_non_exempt_misses()`, and raises if its provisional preference reconstruction disagrees.

The final gate fails closed when the count is positive:

- `_final_comprehensive_validation()` repairs and raises after three unsuccessful passes at `core/scheduler/legacy_parts/placement_and_state.py:1889-1930`.
- It rechecks after day-request seal when day requests exist at `core/scheduler/legacy_parts/placement_and_state.py:2033-2042`.
- `schedule_all()` runs a final post-mutation gate at `core/scheduler/pipeline.py:554-564` before returning.

Residual note: `core/io_handler.py:30-62` can serialize `{}` when `unscheduled_data` is omitted, and the dead `apply_safe_optimizations()` path calls it without unscheduled data at `core/scheduler/legacy_parts/safety_and_export.py:167-211`. I do not rate this as a live WP3 S0 because the official regeneration and GUI paths pass rebuilt unscheduled data, and the auto-save path has no callers, but the serializer default is a source-of-truth foot-gun.

## Comparison Against FINDINGS.md

### F-01 - Confirm

Confirmed as S0. Keep it first in the backlog. The report language should emphasize both parts: missing combined top-3 ranking and inconsistent HC/DG capacity semantics. I do not recommend downgrading.

### F-02 - Confirm

Confirmed as S0. FINDINGS.md is more complete than the first WP3 report because it captures both false-exempt and false-non-exempt directions. Keep current severity/order.

### F-03 - Confirm

Confirmed as S0. The implementation never checks the missed or scheduled canoe duration, so one-hour canoe duplicates can be wrongly exempt. Keep current severity/order.

### F-11 - Confirm, Expand Scope, Keep Order

Confirmed as S1/S2. I recommend updating the F-11 text to include `_attempt_global_top5_repair_step()` and `_bounded_top5_reoptimization()` as live final repair exposure, in addition to `_enforce_mandatory_top5()`, the shared helpers, and D.9. I do not recommend moving F-11 ahead of F-01/F-02/F-03 because it is not a Top-5 false-accept path by itself.

## Missed S0/S1 Check

Within WP3 scope, I did not find a new standalone S0 that is absent from `review/FINDINGS.md`. The main second-pass addition is an F-11 scope expansion: final Top-5 repair can also split pair-protected Delta through `_attempt_global_top5_repair_step()` and helper calls from `_bounded_top5_reoptimization()`.

Out of WP3 primary scope, the already-recorded F-04 `force_day_request` physical-capacity/exclusivity bypass remains a higher-priority S0 than F-11, but it is already present in FINDINGS.md and does not change this WP3 comparison.

## Regression-Test Recommendations

1. Add a parametrized `unscheduled_source` exemption matrix covering negative cases for F-01/F-02/F-03: top-1 DG missed while HC occupies Tuesday slots, unrelated honored day request plus missing rank-1, and one-hour canoe duplicate.
2. Add a positive day-request displacement case: T6 legitimately displaces a Top-5 in the needed slot and the resulting miss is exempt.
3. Add a final gate test where a synthetic non-exempt Top-5 miss in the canonical unscheduled payload causes `schedule_all()` or `_final_comprehensive_validation()` to raise.
4. Add pair-protected Delta tests for `_enforce_mandatory_top5()`, `_force_place_with_window_clearing()`, `_reclaim_activity_from_lower_priority_troop()`, `_try_place_with_displacement_recovery()`, `_attempt_global_top5_repair_step()`, and D.9 outlier/commissioner ownership paths.
5. Add a serializer guard test: saving without `unscheduled_data` should either rebuild it or fail loudly for official schedule outputs.

## Final Summary

F-01, F-02, and F-03 are confirmed S0 false-accept risks.
F-11 is confirmed as a real Delta/Sailing pair-protection contract gap.
F-11 should be expanded to include final repair/global repair call sites.
The final acceptance gate itself fails closed when the count is positive.
The count/reporting path consistently uses the canonical unscheduled payload.
No new standalone WP3 S0 should be inserted above the existing S0 backlog.
No FINDINGS.md severity/order change is recommended, only an F-11 scope update.
