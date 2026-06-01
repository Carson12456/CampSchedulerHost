# WP6 — Scoring Authority Audit (read-only)

**Judge:** `utils/regression_checker.py` | **Spec:** BRAIN §4/§6/§7 | **Config:** SKULL `soft_prohibited_pairs`

## Summary table
| # | Topic | Verdict | Sev | Lines |
| --- | --- | --- | --- | --- |
| 1 | Bucket weights 450+250+200+100=1000 | PASS | — | `regression_checker.py:111-132`, `182-184`, `997-1000`, `1284` |
| 2 | Excess-day ceil(count/3) per area | PASS | — | `:330-360` |
| 3 | Cluster gap 1,-,3 area-level (Thu excluded) | PASS | — | `:384-403` |
| 4 | SKULL soft pairs scored once each | **PARTIAL** | S1–S2 | `:44-106`, `665-709`, `789-800` |
| 4b | Wet/Dry flow §4.2 scored | PASS (beach slot-2 double-penalized) | S1 | `:711-750`, `601-631`, `1234-1238` |
| 5 | Delta timing demand-aware | PASS | — | `:173-230`, `1210-1214` |
| 6 | AT sharing miss penalty | PASS | — | `:233-249`, `1219-1220` |
| 7 | Top-5/10 from `unscheduled` + fail-fast | PASS (file must exist) | S1 edge | `:252-268`, `1006-1020` |
| 8 | Shower House before wet/Super Troop | **SOFT in judge, HARD in scheduler/BRAIN** | S1 | judge `:769-787`; sched `sequencing_and_constraints.py:963-974` |

## Key findings (detail)

### F-WP6-A (S1) — Balls pair unscored
Gaga Ball / 9 Square: **not in SKULL `soft_prohibited_pairs`**, **not scored by judge**, but **hard-blocked** in scheduler (`sequencing_and_constraints.py:1896-1902`). Judge never sees a violation. Matches WP1 F06. The judge has NO generic loop over `soft_prohibited_pairs` — only category-specific paths (`:44-55`), so any pair outside those filters is silently unscored.

### F-WP6-B (S2) — Canoe triples under-counted
Boats soft conflict scored once per troop-day if `len(acts)>=2` (`:697-709`); when 3+ canoe activities present, scores 1 violation vs up to 3 SKULL pairs.

### F-WP6-C (S2) — Fishing pairs orphan
`Fishing+Trading Post`, `Fishing+Campsite Free Time` in SKULL but not in BRAIN §4.1 and not scored anywhere.

### F-WP6-D (S1) — Beach slot-2 double penalty
Non-Top5 beach slot-2 use increments BOTH `soft_violations` (10pts) AND `beach_slot_2_uses` (3pts) = up to 13pts/occurrence (`:601-631`, `:1234-1238`). Decide single channel.

### F-WP6-E (S1) — Shower House hard/soft mismatch
BRAIN §4 HARD (`BRAIN.md:132-134`); scheduler HARD (`sequencing_and_constraints.py:963-974`); judge SOFT (`:769-787`). Also Monday Shower House not scored in judge if it slips through relax/day-request. Promote judge to hard OR downgrade BRAIN+scheduler consistently. **Cross-ref WP2.**

### F-WP6-F (S1 edge) — In-memory scoring fails
Fresh schedule without persisted `{week}_schedule.json` → `FileNotFoundError` at `:1006`. Official `--fresh-eval` regenerates files first so this only bites ad-hoc scoring.

### F-WP6-G (S3) — Dead knob
`top5_miss_penalty` (`:158`) never referenced in score math; legacy bonus knobs zeroed (`:136-142`).

## Strategic gaps (optimal-score analysis)

### (a) Scheduler optimizes; judge does NOT reward
- Commissioner day ownership (D.9) — advisory only, not in score buckets (`:420-473`).
- Early-week Delta/Super Troop bias — `early_week_points: 0`.
- Super Troop + Rifle pairing hits — only Delta+Sailing *misses* scored.
- Reflection clustering (D.1) vs spread (D.6) — no score component.
- HC/DG Balls adjacency — not scored (BRAIN §4.3).

### (b) Judge penalizes; no phase actively targets
- **Staff variance / underuse / over-target / excessive** (Staff 100): `_optimize_staff_variance` exists but **never called**; C.2 is consecutive clustering, not variance. ← biggest opportunity (week7 StVar 7.68 in WP0).
- **Sailing full-day miss** + **same-day pairing miss** (Cluster 250): `_consolidate_sailing_same_day` orphaned (WP10 A.9).
- Activity batching miss (Tie Dye/Rifle/Shotgun): D.8 partially aligns.
- Delta timing late-day: A.7 places early, no post-hoc timing repair.

**Implication:** a schedule can pass Top-5 and still bleed points on staff-variance, sailing-efficiency, and commissioner-day drift because those penalties have weak/zero scheduler feedback loops. This is the core "optimal strategy" gap.

## Recommended fixes (priority)
1. S1: generic SKULL-pair scorer + add Balls to soft pairs + soften scheduler (ties WP1 F06).
2. S1: unify Shower House severity across BRAIN/scheduler/judge (ties WP2).
3. S1: dedupe beach slot-2 penalty channel.
4. S2: wire `_optimize_staff_variance` and sailing-efficiency consolidation to the scored metrics, or drop the unused penalties.
