# WP10 — Breadth / Dead Code Audit (read-only)

## Cut / unreachable pipeline steps (confirmed, zero call sites)
| Step | Method | Location |
| :--- | :--- | :--- |
| A.8 | `_schedule_early_sailing_top10` | `top5_and_swaps.py:1302-1430` |
| A.9 | `_consolidate_sailing_same_day` | `top5_and_swaps.py:1609-1762` |
| A.10 | `_schedule_early_aqua_trampoline_top5` | `top5_and_swaps.py:1031-1088` |
| A.11 | `_guarantee_top1_beach` | `top5_and_swaps.py:1090-1201` |
| A.14 | `_schedule_sailing_pairs` | `preference_and_limited.py:2308-2394` |
| B.4 | `_schedule_delta_early` | `preference_and_limited.py:2094-2198` |
| — | `_schedule_thursday_sailing_largest_troop` | `top5_and_swaps.py:954`, `phase_a_foundation.py:273` (dead) |

## Findings by severity

### S1 — wrong behavior / crash risk
- **MRO shadowing (`constrained_scheduler.py:43-59`)**: `Top5AndSwapsMixin`/`PreferenceAndLimitedMixin` precede `PhaseAFoundationMixin`/`PhaseBCoreMixin`. All phase-file impls (`_schedule_friday_reflection`, `_schedule_super_troop`, `_guarantee_all_top5`, etc.) are **never executed**; legacy_parts versions win (~700 lines dead). → Remove phase stub modules from MRO or delete stub bodies. **Verify which copy is authoritative before deleting.**
- **`psutil.py:1-22`**: local stub shadows PyPI `psutil` when repo root on `sys.path` (Flask adds parent at `gui_web.py:12`). No imports today; future `import psutil` gets fake `rss=0`. → Rename/move out of root.
- **`core/io_handler.py:7-8,85`**: `load_troops_from_json` / `load_schedule_from_json` raise `KeyError` on malformed JSON (no validation). → validate schema.
- **Flask grid routes** `/api/area`, `/api/commissioner`, `/api/beach_board`, `/api/balls`, `/api/reflection`, `/api/staff`, `/api/staff-requirements` (`gui_web.py:1321-1802`): `data['schedule']` with no null guard; `get_week_data` can return `None` (`:295`). → shared `_require_week_data` guard.
- **`/api/regenerate/<week_id>` (`gui_web.py:1117-1156`)**: no try/except around `generate_schedule`. → wrap.
- **Snapshot loaders (`gui_web.py:217-228, 291-295`)**: unguarded `json.load`, bad IDs → `None` → downstream `TypeError`. → guard.

### S2 — missed optimization / drift
- **Duplicate `_ultra_aggressive_top5_recovery`** in `top5_and_swaps.py:3123` and `:3256` — second shadows first (~130 lines dead). → delete first; add test.
- **Hardcoded SKULL duplicates in GUI** (`gui_web.py:1332-1350` area/staff maps; `:1503-1519` commissioner day maps ×3) — drift risk vs `config/SKULL.json`. → load from config_loader.
- **Two divergent schedule loaders** (`gui_web.py:65-145` vs `core/io_handler.py:69`) — Thu-3 virtual slot + unscheduled rebuild differ. → unify.
- **`compatibility_bridges.py:118`** bare `except:` in `_get_priority_level`. → narrow.

### S3 — quality / dead code
- `compatibility_bridges.py:23-168` entire `LegacyPart08Mixin` + analytics methods — zero callers.
- Root shims duplicate `sys.path` purge logic 4× → extract helper.
- `gui_web.py:5` unused `send_from_directory` import; `:1159-1161` dead commented stub.
- `phase_a_foundation.py:12-17` / `phase_b_core.py:198-240` misleading docs/stubs.

## Backward-compat shims: OK
Root `constrained_scheduler.py`, `models.py`, `activities.py`, `io_handler.py` all re-export correctly.

## Cross-link to WP4
The MRO-shadowing finding (phase_a/phase_b stubs never run) overlaps WP4's "cut steps not silently half-wired" check — reconcile there.
