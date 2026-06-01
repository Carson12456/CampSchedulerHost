# WP9 — Sailing Slot Model & C.6b Half-Fill Audit (read-only)

**Contract:** BRAIN §4 (Sailing slot-2 overlap exception + final normalization), §5 A.5/A.6/A.7,
§5 C.6b, §3 rotation, §6 (missed `Delta/Sailing` pairing penalty). Hard rule
`non_exempt_top5_misses == 0`. `utils/regression_checker.py` is the judge.
**Scope:** `core/services/sailing_half_fills.py`; scheduler methods `_schedule_sailing_balls_fills`,
`_schedule_sailing_optimize_all`, `_schedule_delta_sailing_pairs`, `_enforce_sailing_slot_exclusivity`
(`pipeline.py`), and the C.6b step in `pipeline.py`.
**Verdict:** All three required checks **PASS**. The 90-minute / 2-slot model is consistent search→normalize→sidecar,
C.6b candidate-order and the 11-20-count / 1-10-no-substitute rule are implemented exactly, and A.6-before-A.5
is genuinely load-bearing. Defects are bounded to soft optimization, dead code, and misleading docstrings — **no S0/S1**.

## Summary table
| # | Topic | Verdict | Sev | Lines |
| --- | --- | --- | --- | --- |
| 1 | 90-min/2-slot model consistent (search → normalize → half-fill) | **PASS** | — | `models.py:212-265,322-339`; `sequencing_and_constraints.py:1757-1838`; `top5_and_swaps.py:806-951`; `preference_and_limited.py:2201-2305`; `pipeline.py:13-76`; `sailing_half_fills.py:118-151` |
| 2 | C.6b candidate order + rank-override | **PASS** | — | `sailing_half_fills.py:15-17,84-106` |
| 3 | C.6b "11-20 count / 1-10 do NOT substitute" | **PASS (and is the Top-5 safety gate)** | — | `sailing_half_fills.py:103`; `unscheduled_source.py:115,122,152` |
| 4 | A.6 runs before A.5 → prevents A.5 first-fit scoop | **PASS (load-bearing)** | — | `pipeline.py:217-237`; `top5_and_swaps.py:744-746` |
| 5 | `_enforce_sailing_slot_exclusivity` capacity (1/2/1) + Thursday | **PASS** | — | `pipeline.py:46-76` |
| 6 | Duplicate `_schedule_delta_sailing_pairs` (one shadowed/dead) | **FLAG** | S3 | `preference_and_limited.py:2201` (active) vs `phase_a_foundation.py:325` (dead) |
| 7 | Docstrings claim "Delta takes 2 slots" (SKULL = 1) | **FLAG** | S3 | `phase_a_foundation.py:329`; `SKULL.json:394-395,1063-1067` |
| 8 | A.6 uses raw `add_entry`, skips staff-cache/`_mark_schedule_changed` | **FLAG (bounded)** | S3 | `top5_and_swaps.py:879` vs `placement_and_state.py:65-102` |
| 9 | A.6 Thursday pick can break Delta/Sailing pairing | **FLAG** | S2 | `top5_and_swaps.py:885-903`; cf. dropped guard `:1007` |
| 10 | "9-slot matrix" name vs 8 sessions actually attempted | **FLAG** | S3 | `top5_and_swaps.py:907-944` |

Severity: **S0** breaks Top-5/hard contract · **S1** wrong score/contract mismatch · **S2** missed optimization · **S3** quality/dead code.

## Detailed findings

### F-1 (PASS) — 90-min / 2-slot model is consistent end-to-end
Sailing has `duration = 1.5` (`SKULL.json:194-195`), and `slots_needed = int(1.5 + 0.5) = 2`. Every layer treats
a Sailing session as occupying the start slot **and** the next slot, with slot-2 the only legal shared slot:

- **Model / search:** `Schedule.add_entry` writes 2 entries for `effective_slots >= 1.5` (`models.py:259-264`) and the
  continuation guard allows the slot-2 overlap (`models.py:244-254`: `allowed = 2 if next_slot.day != THURSDAY and next_slot.slot_number == 2 else 1`).
  `is_activity_available` repeats the same rule for same-name Sailing entries (`models.py:322-339`: continuation-only, then `count("Sailing") < 2`).
- **Sailing gate:** `_can_schedule_sailing` enforces start∈{1,2}, ≤2 sessions/non-Thursday day, Thursday start=slot-1 only (`sequencing_and_constraints.py:1769-1817`), and is dispatched from `_can_schedule` (`sequencing_and_constraints.py:1303-1304`).
- **A.6:** `try_schedule` adds 2 slots via `add_entry` and rejects starts whose `start+1` exceeds `2 if THURSDAY else 3` (`top5_and_swaps.py:870-883`).
- **A.7 (active):** lays Sailing(1-2)+Delta(3) or Delta(1)+Sailing(2-3) (`preference_and_limited.py:2270-2296`) — both fit a 3-slot day cleanly because Delta is 1 slot (see F-7).
- **Final normalizer:** `occupied = [start, start+1]` and `allowed = 2 iff non-Thursday slot 2 else 1` (`pipeline.py:38-50`) → slot1 max 1, slot2 max 2, slot3 max 1, exactly BRAIN §4 line 109.
- **Half-fill sidecar:** the fill always lands in slot 2 with the half complementary to the Sailing block — `fill_half = "bottom" if start_slot == 1 else "top"` (`sailing_half_fills.py:134-135`). A slot-1 start occupies slot1 + top-of-slot2 (fill = bottom-of-slot2, i.e. *after* Sailing); a slot-2 start occupies bottom-of-slot2 + slot3 (fill = top-of-slot2, i.e. *before* Sailing). Both satisfy BRAIN C.6b "may sit before or after Sailing," and `half_fill_occupancy` is keyed by `(day, slot, activity, half)` so two troops never collide in the same half (`sailing_half_fills.py:99,139`). Thursday is correctly skipped as a continuous 2-hour block (`sailing_half_fills.py:123-128`).

No layer treats Sailing as 1 or 3 slots, and the slot-2-max-2 rule is identical in all four enforcement points. **Consistent.**

### F-2 / F-3 (PASS) — C.6b candidate order, rank-override, and the 11-20/1-10 rule are exact
`HALF_FILL_CANDIDATES = ["Gaga Ball", "9 Square", "Trading Post"]`, `DEFAULT_HALF_FILL_PRIORITY` = that order,
fallback `"Campsite Free Time"` (`sailing_half_fills.py:15-17`) — matches BRAIN C.6b line 194 verbatim.
`choose_fill_activity` sorts requested candidates first, ascending by request rank, then by default order
(`sailing_half_fills.py:85-92`), so "the highest-requested candidate is preferred" is implemented; unavailable/duplicate
candidates are skipped via `troop_activity_names`, `blocked_full_slots`, and `half_fill_occupancy` (`:94-100`), with
`Campsite Free Time` as terminal fallback (`:106`).

The rank rule is `counts_as_request = priority is not None and 10 <= priority < 20` (`sailing_half_fills.py:103`), where
`priority` is the 0-indexed rank. So index 10-19 = displayed ranks **11-20 → counts**, and index 0-9 = displayed ranks
**1-10 → does NOT count**. This is exactly BRAIN C.6b. Crucially this is **also the Top-5 safety gate**:
`build_unscheduled_data` folds only credited (`counts_as_request`) fills into `scheduled_activity_names`
(`unscheduled_source.py:115` via `get_request_credit_fill_activities`, `sailing_half_fills.py:34`), and only iterates
`preferences[:5]` / `preferences[5:10]` for misses (`unscheduled_source.py:122,152`). Because credited fills are
rank 11-20 by construction, they can never match a Top-5 (rank 1-5) or Top-10 (rank 6-10) name → a half-fill can
never falsely satisfy the hard contract that `_count_non_exempt_top5_misses` enforces (`placement_and_state.py:2714-2732`).
A rank-1-10 candidate may still be *displayed* as the fill (preferred order), but with `counts_as_request = False` the
troop's full-hour obligation remains unscheduled — i.e. it "does not substitute." **Faithful and safe.**

### F-4 (PASS) — A.6 before A.5 is genuinely load-bearing
A.5 `_schedule_two_hour_activities_priority` selects *any* Top-10 preference with `effective_slots >= 1.5`
(`top5_and_swaps.py:744`) and places it with the generic first-fit `_try_schedule_activity`. Sailing (1.5) **matches that
predicate** and is not excluded by name, so if A.5 ran first it would scoop Sailing into arbitrary slots, defeating the
9-slot packer. The pipeline runs A.6 (`pipeline.py:222`) → A.7 (`:229`) → A.5 (`:236`), and A.5 guards with
`if self._troop_has_activity(troop, activity): continue` (`top5_and_swaps.py:746`). Therefore every troop A.6 has already
seated is skipped by A.5, and the specialized packer owns the placements — the reordering claim in BRAIN §5 A.6 (line 167)
holds. (Troops A.6 fails to seat can still be picked up by A.5 first-fit, which is the intended fallback.)

### F-5 (PASS) — final normalizer capacity & ordering
`_enforce_sailing_slot_exclusivity` (`pipeline.py:13-76`) correctly identifies session *starts* (no same-troop Sailing in
the prior slot, `:26-35`), buckets `[start, start+1]` occupancy per slot, applies `allowed = 2` only for non-Thursday
slot 2 else 1 (`:50`), keeps the best-ranked sessions, and relocates/removes the excess (`:54-76`). It is called inside
`_final_comprehensive_validation` (`placement_and_state.py:1879`) which runs at `pipeline.py:476` — *before* the C.6b
sidecar at `pipeline.py:570`, so half-fills are computed against the already-normalized final board. A staggered pair
(start-1 + start-2) is preserved (slot2 = 2 ≤ allowed 2). Excess removals create gaps that the following
`_guarantee_no_gaps()` (`placement_and_state.py:1883`) refills. **Correct.**

### F-6 (S3) — duplicate `_schedule_delta_sailing_pairs`; one is dead
Two definitions exist: `preference_and_limited.py:2201` and `phase_a_foundation.py:325`. Per the MRO in
`constrained_scheduler.py:43-60`, `PreferenceAndLimitedMixin` (4th base) precedes `PhaseAFoundationMixin` (14th), so the
**`preference_and_limited.py` version is the one A.7 actually calls** and the `phase_a_foundation.py` copy is shadowed
dead code. The dead copy diverges (single layout Delta-slot1 + Sailing-slot2, sourced from `COMMISSIONER_DELTA_DAYS`
rather than the family-day policy). It never runs but is a maintenance trap — an edit there has zero effect, and a future
MRO change would silently swap behavior.

### F-7 (S3) — docstrings claim "Delta takes 2 slots"; SKULL says 1
Both pair docstrings state "Delta takes 2 slots" (`phase_a_foundation.py:329`; same mental model implied at
`preference_and_limited.py:2202-2207`), but `SKULL.json:394-395` sets Delta `duration = 1` and the `multi_slot` list
(`SKULL.json:1063-1067`) excludes Delta; `_can_schedule_on_day` also treats Delta as once-per-week single placement
(`sequencing_and_constraints.py:1866`). The active geometry is still correct because Delta consumes one slot
(Sailing(1-2)+Delta(3) and Delta(1)+Sailing(2-3) both fit 3 slots). Risk is purely documentation: anyone "fixing" the
code to honor the comment (Delta as 2 slots overlapping Sailing at slot 2) would create a same-troop double-book that
`is_troop_free` rejects (`models.py:391-393`), breaking the pairing.

### F-8 (S3, bounded) — A.6 mutates via raw `add_entry`, skipping wrappers
`_schedule_sailing_optimize_all.try_schedule` calls `self.schedule.add_entry(...)` directly (`top5_and_swaps.py:879`)
instead of `_add_to_schedule` (`placement_and_state.py:65-102`). Consequence: `total_staff_by_slot` /
`staff_load_by_slot` and `_mark_schedule_changed()` are **not** updated for A.6 Sailing placements, so soft staff-balance
scoring under-counts Sailing's beach staff until the next `_rebuild_staff_tracking()` (which Phase D calls repeatedly).
Bounded because the **hard** beach-staff/saturation caps are recomputed from `entries` in `is_activity_available`
(`models.py:371-385`), not from the caches. No contract impact; soft-optimization noise only.

### F-9 (S2) — A.6 Thursday pick can forfeit the Delta/Sailing pairing
`_schedule_sailing_optimize_all` awards Thursday's single Sailing session to the largest **Top-5** troop with no check
for whether that troop also wants Delta (`top5_and_swaps.py:885-903`). Thursday has only 2 slots and Sailing consumes
both, so Delta cannot be paired there; A.7 then places Delta on another day, incurring the BRAIN §6 "missed Delta/Sailing
pairing" soft penalty (line 234). The legacy dedicated method explicitly skipped Delta-wanters for Thursday
(`top5_and_swaps.py:1007` `if "Delta" in troop.preferences: continue`); that guard was dropped when Sailing logic was
consolidated into A.6. Soft/optimization regression only — not a Top-5 break.

### F-10 (S3) — "9-slot capacity matrix" vs 8 sessions attempted
BRAIN §5 A.6 (line 167) and the method docstring call it the "9-slot" matrix, but the loop only attempts
Mon/Tue/Wed × 2 + Thursday × 1 + Friday × 1 = **8 sessions** (Friday is tried as a single slot-1 last resort,
`top5_and_swaps.py:941-944`), even though `_can_schedule_sailing` would permit 2 Friday sessions. Minor capacity
under-utilization plus a naming mismatch; harmless to the contract.

### Cross-reference (out of WP9 scope, noted)
`sailing_balls_fills` feeds `_count_non_exempt_top5_misses` (`placement_and_state.py:2724`) yet is computed only once at
the very end (`pipeline.py:570`, after the acceptance gate at `:555`) and is omitted from snapshot/restore. Safe today
for two independent reasons — credited fills are rank 11-20 (cannot touch Top-5/Top-10, F-3) and the counter sees empty
fills during every rollback-prone phase — but it would become a latent contract-accounting bug if C.6b were moved earlier.
Already tracked by WP8 (`review/WP8_state.md` F-WP8-3); flagged here only for traceability.

## Executive summary
The Sailing subsystem holds up under audit. The 90-minute / 2-slot capacity model (occupy `[start, start+1]`, slot-1
max 1, slot-2 max 2, slot-3 max 1) is implemented identically across the search-time gate, `Schedule.add_entry`,
`_can_schedule_sailing`, the A.6 packer, the active A.7 pairer, the final `_enforce_sailing_slot_exclusivity` normalizer,
and the C.6b half-fill sidecar — no divergence found. C.6b reproduces BRAIN's candidate order (Gaga Ball → 9 Square →
Trading Post → Campsite Free Time) and the rank-override rule precisely, and the `10 <= priority < 20` gate is the very
mechanism that keeps half-fills from ever falsely crediting a Top-5/Top-10 preference, so the hard contract is protected.
A.6-before-A.5 is load-bearing: A.5's first-fit explicitly grabs any `slots >= 1.5` activity (Sailing included) and is
prevented from scooping only because A.6 places Sailing first and A.5 skips already-placed troops. No S0/S1 issues. The
defects are quality-grade: a shadowed duplicate `_schedule_delta_sailing_pairs` (S3), docstrings that mislabel Delta as
2 slots while SKULL says 1 (S3), A.6 bypassing the staff-cache wrapper (S3, self-healing), an "9-slot" name that only
attempts 8 sessions (S3), and one genuine soft-optimization miss — A.6 can hand Thursday Sailing to a Delta-wanting troop
and forfeit the Delta/Sailing pairing penalty (S2). Recommended fixes (later WP): restore the Thursday Delta-skip guard
in A.6, delete or reconcile the dead pair method, and correct the Delta-slot docstrings.
