# WP11 — Unit Test Adequacy vs BRAIN Hard Contract (read-only)

**Verdict:** Unit tests mostly exercise primitives + a 3-troop `schedule_all()` smoke path. They do **not** enforce most BRAIN hard-contract clauses. Real enforcement lives in `utils/regression_checker.py` (integration), outside `pytest -q tests/unit`.

## Coverage table
| # | BRAIN clause | Covered? | Ref / MISSING | Risk |
| --- | --- | --- | --- | --- |
| 1 | Top-5 zero non-exempt misses | Partial | `test_scheduling_algorithm.py:70-75` (3 synthetic troops; no negative/gate-fail case) | High |
| 2 | Four Top-5 exemption rules | **No** | MISSING — `unscheduled_source.py:27-45` untested | **Critical** |
| 3 | Anchors (Reflection Fri, Super Troop, HC/DG Tue) | Partial | Reflection+SuperTroop `:50-67`; HC/DG Tue-only MISSING | High |
| 4 | Delta ↔ Tower/ODS adjacency | **No** | MISSING | High |
| 5 | Sailing 90-min caps + slot-2 overlap | Partial | post-hoc caps `:180-197`; placement-time overlap MISSING | Medium |
| 6 | No empty slots (completeness) | **No** | MISSING (only single-gap fill tested) | High |
| 7 | MUST-HONOR ladder T0–T6 + Thu opt-out | **No** | MISSING | **Critical** |
| 8 | Cluster-gap (1,-,3) + excess-day ceil(n/3) | **No** | MISSING (`regression_checker.py:330-403`) | Medium |
| 9 | Scoring buckets 450/250/200/100 + miss-sourcing | Partial | pref cap `test_scoring_contract.py:150-155`; other buckets + unscheduled cross-check MISSING | Medium |
| 10 | Shower House hard rules | **No** | MISSING | Medium |

## Notable weakness
`test_constraint_system.py:160-162, 176-177, 200-201` assert permissive `Schedule.add_entry` behavior with comments "scheduler should prevent" — so scheduler regressions would NOT fail these tests.

## Highest-value missing tests (priority)
1. `unscheduled_source` exemption matrix (parametrized, incl. negative `is_exempt=False` cases).
2. Top-5 acceptance gate: synthetic non-exempt miss must fail; repair drives misses→0.
3. Day-request MUST-HONOR ladder (T1–T6, anchor non-displacement, Thu opt-out trio preservation).
4. Delta↔Tower/ODS adjacency rejection both directions via `_can_schedule`.
5. Completeness after `schedule_all()` (every troop, every slot; Thu 2-slot vs Fri 3-slot).
6. HC/DG Tuesday-only rejection off-Tuesday.
7. Cluster metrics: ceil(n/3) + 1,-,3 detection on constructed schedules.
8. Scoring bucket caps sum ≤ 1000; `evaluate_week` raises on pref-vs-unscheduled mismatch.
9. Sailing placement-time slot-2 overlap (2 troops during search; final caps hold).
10. Shower House Monday block + same-day ordering vs wet/Super Troop.
