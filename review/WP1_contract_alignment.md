# WP1 — BRAIN / SKULL / Code Contract Alignment (read-only)

## Summary table
| ID | Sev | Finding | Primary code |
| --- | --- | --- | --- |
| F01 | S1 | `tower_extended_size` (15) in SKULL never read; Tower 2-slot uses hardcoded `scouts > 15` | `core/models.py:207-209` |
| F02 | S2 | `sailing_extended_size` (12) fully orphan — no consumer | `config_loader.py:133-141` |
| F03 | S2 | `non_consecutive` loaded into constants, never enforced | `constants.py:51`, `constrained_scheduler.py:100` |
| F04 | S2 | `slot_rules` (beach 1/3, Thu 1/2, sailing slot 2) not consumed; enforcement hardcoded | `sequencing_and_constraints.py:1123-1140` |
| F05 | S2 | Optimization toggles orphan (`avoid_friday`, `archery_target_days`, `enable_*`, `consecutive_activities`) | SKULL only |
| F06 | **S1** | Gaga Ball / 9 Square same-day is **hard** in code; BRAIN §4 lists as **soft**; pair absent from `soft_prohibited_pairs` | `sequencing_and_constraints.py:1896-1902` |
| F07 | S2 | `prohibited_pairs: []` — hard same-day path dead; rules duplicated/hardcoded | `constants.py:54`, `sequencing_and_constraints.py:1502-1509` |
| F08 | S2 | Staff caps hardcoded 16/20/24 vs SKULL `max_staff_global`/`target_staff_global` | `sequencing_and_constraints.py:812-819`, `gap_fill_and_stats.py:908` |
| F09 | S3 | Consistency checker skips `target_staff_global` (14) and extended sizes | `check_brain_skull_consistency.py:58-85` |
| F10 | S3 | `unscheduled_source.py` hardcodes HC/DG set instead of `tuesday_only_activities` | `unscheduled_source.py:12` |
| F11 | S3 | Sailing half-fill candidates hardcoded; not in SKULL | `sailing_half_fills.py:15-17` |
| F12 | **S1** | Voyageur `Commissioner% = 0.0` is a **regression-metric bug** (0 checks, "no data" misreported as 0%), NOT disabled grouping | `regression_checker.py:450-472` vs `state.py:56-59` |
| F13 | S2 | Large-troop threshold inconsistent: Tower `scouts > 15`; Shotgun `scouts+adults > 15` | `models.py:208`, `sequencing_and_constraints.py:1019` |
| F14 | S3 | `web/gui_web.py` duplicates commissioner day maps (not SKULL-driven) | `gui_web.py:1511+` |

**Aligned & verified wired:** `mandatory_anchors`, `tuesday_only_activities`, `request_only_activities`, `concurrent_activities`, `concurrent_exclusivity_exceptions`, `rotation_schedule`; numeric limits canoe 26, beach staff 12, beach saturation 4→5, global max 16, target 14 (scoring only — placement diverges per F08).

## Key detail — F12 Voyageur metric bug
Troop JSON uses `"commissioner": "Voyageur A"`; scheduler aliases `Commissioner X`→`Voyageur X` at `state.py:56-59`, so **grouping IS active**. But `regression_checker.py:450-472` only maps `Commissioner A/B/C`, so `expected_map.get("Voyageur A")` is None → `commissioner_checks == 0` → `100.0 * 0 / max(1,0) = 0.0`. Fix: mirror the alias in the checker or report `N/A` when checks==0.

## F06 detail (hard vs soft mismatch)
`sequencing_and_constraints.py:1896-1902` hard-blocks Gaga Ball + 9 Square same day, but BRAIN §4.1 lists Balls (Nine Square/Gaga) as a SOFT pair, and the pair is missing from SKULL `soft_prohibited_pairs`. Either add to soft pairs + soften enforcement, or update BRAIN.

## Orphan SKULL keys (no consumer)
`optimization.consecutive_activities`, `avoid_friday`, `archery_target_days`, `enable_smart_balls_scheduling`, `enable_area_day_filling`, `sailing_extended_size`, all of `slot_rules.*` (loader only), `get_capacity_limits()`, `get_commissioner_for_troop()`. `prohibited_pairs` read-but-empty.

## Hardcoded lists that should source from SKULL
`STAFF_CLUSTERING_ACTIVITIES` (`sequencing_and_constraints.py:804-808`), Gaga/9Square + Trading-Post-Monday rules (`:1892-1902`), `HALF_FILL_CANDIDATES` (`sailing_half_fills.py:15`), `HC_DG_ACTIVITIES` (`unscheduled_source.py:12`), GUI commissioner dicts.

## Recommended first fixes
F12 (Voyageur alias in checker), F01 (wire tower_extended_size), F06 (Gaga/9Square soft), F04 (consume slot_rules).
