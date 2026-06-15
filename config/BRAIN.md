# 🧠 BRAIN: Central Source of Truth
**The Summer Camp Scheduler System Blueprint**

| Metadata | Details |
| :--- | :--- |
| **Version** | 2.5.2 |
| **Last Updated** | 2026-04-20 |

This document defines the overarching "Laws of Physics" for the scheduling engine, dictating constraints, rotation logic, scoring systems, and phase behavior.

---

## 🎯 1. Executive Summary & Core Principles

At the heart of the scheduling engine is a single, unbreakable philosophy: **Satisfaction First.** User preferences (specifically their Top 5 choices) strictly take precedence over administrative ease. 

> [!IMPORTANT]
> **The Hard Contract**
> The scheduler *must* produce a schedule with **100% non-exempt Top 5 success**. Any non-zero value of missed non-exempt Top 5 activities is a failed run and must trigger repair logic.

To achieve this, the system operates on five foundational rules:
1. **Prevention Over Cure:** Validate constraints *before* placing an activity.
2. **Rocks, Pebbles, Sand:** Place large and rigid items first, followed by core requests, and finally the passive fills.
3. **Fail-Closed Acceptance:** Hard-constraint drift triggers repair/sanitization passes; only an accepted final schedule may pass hard gates.
4. **No Empty Slots:** Every troop must have an assigned activity in every available slot.
5. **Zero Non-Exempt Top 5 Misses:** Missing a non-exempt Top 5 request is never acceptable.

### Priority Ladder (Authoritative)
When trade-offs are unavoidable, apply this order:
1. **Day Requests (MUST-HONOR) First:** A troop's explicit day-specific request is
   the highest-priority authored input and **must be honored** even if doing so
   requires a soft-constraint violation or the displacement of a non-anchor
   Top 5 preference. See §10 for the solver contract and exemption rules.
2. **Hard Constraints Second:** Never accept physical hard-constraint violations
   (exclusivity, capacity, Delta-Tower/ODS adjacency, anchor days).
3. **Top 5 Contract Third:** Prefer a soft-constraint violation over creating a
   non-exempt Top 5 miss, subject to day-request supremacy above.
4. **Soft Constraints Fourth:** Optimize soft compliance only after Day
   Requests + Hard + Top 5 are protected.

---

## 🏆 2. The Top 5 Success Contract (Authoritative)

This section defines the strict parameters for fulfilling troop requests and reporting on successes and failures.

### Key Definitions
* **Top 5 Requested Activity:** Any troop preference ranked 1 through 5.
* **Missed Activity:** A Top 5 request that does not appear in the troop's final schedule.
* **Exempt Miss:** A missed activity that is forgiven because it meets one of the following formal rules:
    * *3-Hour Duplication:* The troop requested multiple 3-hour activities (e.g., Tamarac & Itasca) but already received one.
    * *Tuesday HC/DG Saturation:* Only the highest three requested of both Disc Golf (DG) and History Center (HC) can be granted one of the three available Tuesday slots.
    * *Two Hour Canoe Duplication:* If a troop is already scheduled for one two hour activity, a missed request for another two hour canoe activity is exempt.
    * *Day-Request Displacement (MUST-HONOR):* A missed Top 5 activity is exempt when
      (a) the missed activity is itself day-requested (physical impossibility
      accepted), or (b) the troop has at least one honored day-request that
      occupies a slot the Top 5 would have needed. Per the Priority Ladder
      (§1), day requests supersede Top 5; this exemption lets the hard
      acceptance gate correctly pass schedules that honored MUST-HONOR requests.
* **Non-Exempt Miss:** Any missed Top 5 request that does *not* qualify for an exemption.

### The Single Source of Truth Protocol (Mandatory)
You may not calculate misses on the fly. All reporting on missed Top 5 or general missed activities **MUST** follow these strict data paths:

* **Read Location:** `schedule_json.unscheduled`
* **Authoritative Paths:** * `unscheduled.<troop_name>.top5[]`
    * `unscheduled.<troop_name>.top10[]`
* **Required Data Attributes:** Every logged miss must include the `name`, `rank`, and `is_exempt` status.
* **Strict Prohibitions:** Reconstructing miss lists directly from `troop.preferences` is strictly forbidden. If the `unscheduled` object is missing, the analysis must fail-fast rather than using fallback calculations.

---

## 🗺️ 3. "The Waltz": Commissioner Rotation & Geography

To ensure balanced coverage, the camp is geographically divided into three distinct commissioner areas.

### Geographic Clusters
These are ideal groupings, 

| Group | Commissioner | Assigned Campsites |
| :--- | :--- | :--- |
| **North** | Comm A | Massasoit, Tecumseh, Samoset, Black Hawk, Taskalusa |
| **Central** | Comm B | Powhatan, Red Cloud, Cochise, Joseph, Tamanend |
| **South** | Comm C | Pontiac, Skenandoa, Sequoyah, Roman Nose |

### Activity Rotation Schedule
If a scheduling conflict arises, **pairing integrity** is prioritized over strict day ownership. 

| Activity Group | Comm A (North) | Comm B (Central) | Comm C (South) |
| :--- | :--- | :--- | :--- |
| **Delta / Sailing** | Monday | Tuesday | Wednesday |
| **Tower / ODS** | Tuesday | Wednesday | Thursday |
| **Rifle / Super Troop** | Wednesday | Thursday | Monday |
| **Archery / Boats** | Thursday | Monday | Tuesday |

> [!NOTE]
> Current baseline behavior keeps the durable family-day policy envelope only for `Delta/Sailing`. `Tower/ODS`, `Rifle`, and `Super Troop` still use their legacy / commissioner-first placement shape by default unless explicitly re-enabled for A/B testing.

---

## ⚖️ 4. Constraint Dictionary

Constraints dictate what is physically and logically possible within a schedule.

### 🔴 HARD Constraints (Invalidates Schedule)
Failing any of these will immediately scrap the schedule.
* **Exclusive Double-Booking:** Only one troop per slot is allowed in configured exclusive activities, with one formal exception:
    * **Sailing Slot-2 Overlap Exception (search-time):** `Sailing` is a 90-minute activity modeled as a 2-slot placement. During placement checks, Slot 2 may temporarily hold **1 or 2 Sailing troops** (30-minute overlap between a Slot-1 start and a Slot-2 start).
    * **Final Output Normalization:** The final pipeline enforces the same 90-minute Sailing capacity model in delivered schedules (Slot 1 max 1, Slot 2 max 2, Slot 3 max 1).
* **Completeness:** Every troop must have a fully booked week (zero empty slots).
* **Mandatory Anchors:**
    * `Reflection` must occur on Friday.
    * `Super Troop` must occur once weekly.
    * `History Center` and `Disc Golf` are strictly constrained to Tuesday.
* **Delta + Tower/ODS:**
    * A troop cannot have Delta, and then have a Tower or ODS actviity in the slot after, OR
    * A troop cannot have a Tower or ODS actviity, and then have Delta in the slot after.
* **Capacity Safety Limits:**
    * Canoes: Max 26 people.
    * Global Staff: Base max 16 per slot; clustering-targeted scheduling can use controlled elevated limits for specific staff-clustering activities.
    * Beach Staff: Max 12 per slot.
    * Beach Saturation: Max 4 staffed beach activities per slot, with a narrowly-scoped Top-5 Aqua Trampoline overload path up to 5.
* **The Acceptance Gate:** `non_exempt_top5_misses == 0` is strictly enforced.
* **Day Requests (MUST-HONOR):** Day-specific requests are **authoritative
  inputs** that must be honored in the final schedule. They may bypass soft
  constraints (duplicate prevention, beach slot rule, staff cap, back-to-back)
  and may displace non-anchor occupants — including Top-5 placements —
  during the Final Day-Request Enforcement pass. Protected anchors
  (`Reflection`, `Super Troop`, `History Center`, `Disc Golf`) are never
  displaced. See §10 for the full solver contract and Thursday 3-hour
  opt-out semantics.

### 🟡 SOFT Constraints (Score Deductions)
Violating these will lower the schedule's quality score, but will not break the build.

#### 1. Prohibited Same-Day Pairs
Each configured same-day pair (SKULL `soft_prohibited_pairs`) is a soft violation,
scored exactly once per troop per day. Groups below expand to all pairwise combinations.
* *Accuracy:* Troop Rifle / Troop Shotgun / Archery
* *Boats:* Paired boating activities
* *Water Games:* Aqua Trampoline / Water Polo / Greased Watermelon. Any same-day pair among these three is a soft violation.
* *Free Time:* Trading Post / Shower House / Campsite Free Time (and Fishing with Trading Post / Campsite Free Time)
* *Balls:* Nine Square / Gaga Ball (soft only — never a hard block)

#### 1a. Campsite Free Time Coverage (Universal)
`Campsite Free Time` is concurrent (no shared capacity), requires no staff, and is
universally placeable in any slot on any day. Because it can be added at no
scheduling cost, **every troop should receive at least one `Campsite Free Time`
block** where it fits cleanly.
* This is a soft *policy*, not a hard anchor. A guarded terminal pass gives each
  troop that lacks `Campsite Free Time` one, by replacing its worst non-anchor
  occupant. Replacement priority follows: an occupant that **causes a soft
  violation** → a cluster activity on an **excess day** → the **lowest-ranked
  filler**.
* The pass commits a replacement only when it is **score-neutral or better** and
  preserves the Top-5 / Top-10 contract. It never displaces a protected anchor
  (`Reflection`, `Super Troop`, `History Center`, `Disc Golf`), a multi-slot
  block, an honored MUST-HONOR day request, or a higher-value preference, and it
  never creates a Free Time same-day soft pair (§1).

#### 2. Wet/Dry Flow & Transitions
* Avoid "Wet-Dry-Wet" sandwiches.
* Avoid direct transitions between Wet activities and Tower/ODS.
* Beach activities should preferably land in Slot 1 or Slot 3 (Slot 2 is acceptable on Thursdays only).

#### 2a. Shower House Timing
* **Shower House on Monday** is a soft violation: the scheduler should avoid it,
  and it costs points, but it does not invalidate the build (it may still occur
  under a MUST-HONOR day request or as a last-resort fill).
* **Shower House must not precede a later Super Troop or wet activity on the same
  day** (a shower before getting sweaty/wet defeats its purpose). The scheduler
  never self-inflicts this: when Shower House is a fill activity (not explicitly
  requested), it is swapped for a different fill rather than placed before a later
  Super Troop / wet activity. This ordering may only occur to honor an explicit
  MUST-HONOR Shower House day request, in which case the resulting soft violation
  is contract-exempt. The judge scores it as a soft violation when present.

#### 3. Activity Consecutiveness
* `Tie Dye`, `Rifle`, and `Shotgun` should actively seek to run back-to-back within area schedules to minimize setup/teardown time.
* `History Center` and `Disc Golf` should have compatible adjacency (Balls/reserve-adjacent behavior). Current implementation allows a broader compatibility set than strict "Balls-only".

---

## 🏗️ 5. System Architecture & Phase Gates

The `ConstrainedScheduler` executes from Phase A to Phase D. Every phase includes Top 5 anti-miss safeguards. The order below represents the actual execution flow.

### Phase A: Foundation (The Skeleton)
**Goal:** Place mandatory anchors, then multi-slot structures (Rocks) before smaller items (Sand). Aggressively protect heavily-contested Top-5 resources before fragmentation occurs. All multi-slot constraints (3-hour, 2-hour, Sailing, Delta) are grouped here.

*   **A.1: Friday Reflection** — Reserves Friday slots first to guarantee this camp-wide mandatory end-of-week anchor fits.
*   **A.3: HC/DG Tuesday** — Locks in History Center and Disc Golf on their exclusive mandated day (Tuesday) before other activities claim those slots.
*   **A.4: 3-Hour Activities (Rocks)** — Places full-day blocks first. This is the biggest contiguous constraint and must be placed before single-slot activities fragment available day schedules.
*   **A.6: Sailing Optimization (relocated pre-A.5)** — Fills Sailing's 9-slot (90-min, 2-slot) capacity matrix. Must run **before** A.5, because A.5's generic first-fit pass scoops any activity with `slots >= 1.5` (including Sailing) and causes A.6 to skip troops whose Sailing is already placed sub-optimally. Running it here lets the specialized commissioner-day packer own Sailing placements.
*   **A.7: Delta + Sailing Pairing (relocated pre-A.5)** — Pairs Delta with Sailing on the same commissioner day immediately after Sailing lands. Together with A.6, this seeds a durable full-day `Delta/Sailing` envelope before any other single-slot or 2-hour activities compete for the same troop-day.
*   **A.5: Top-10 2-Hour Activities (Rocks)** — Places consecutive multi-slot requirements. Runs after Sailing/Delta so those structural blocks are locked in; A.5 only handles the remaining 2-hour Rocks.
*   **A.2: Super Troop (Relocated)** — Mandatory weekly placement for all troops. Moved *after* multi-slot rocks (A.4-A.7) so it doesn't artificially fragment 3hr/2hr/Sailing day blocks.
*   **A.12: Early Staff Area Clustering** — Pre-schedules Tower, ODS, and Rifle to improve setup efficiency via legacy day-shape behavior before core random requests scramble the board.
*   **Exit Gate A:** Immediate gap repair if a troop is missing placements for available slots, preventing structural cascades.

### Phase B: Core Requests (The Meat)
**Goal:** Guarantee the Top 1–5 preferences are satisfied (The Hard Contract) and lock in priority requested pairings.

*   **B.1: Top 1 First / B.1b: Force Top 1 / B.1c: Top 2-5** — Secures primary rank preferences hierarchically, ensuring the most important requests are seated when the board is still relatively clear.
*   **B.2: Guarantee 100% Top 5** — Runs dedicated recovery loops to ensure the Top 5 satisfaction contract is fulfilled for any holdouts.
*   **B.3: Mandatory Top 5 Enforcement** — Strict compliance check and forceful relocation to ensure zero non-exempt misses.
*   **B.5: Commissioner Busy Map** — Diagnostic/tracking generation for awareness in later clustering.
*   **B.6: Enforce Delta + Sailing Pairing** — Safety net check after preferences are placed, repairing any `Delta/Sailing` pairings that drifted during the aggressive Top 1-5 recoveries.
*   **Exit Gate B:** Immediate gap check and repair.
*   **B.7: Aqua Trampoline Sharing** — Consolidated single pass for Top 5 capacity sharing. Placed here so the core board is settled before attempting localized capacity overloads.

### Phase C: Remaining & Optimization
**Goal:** Accommodate lower-tier preferences (6-20), protect the Top-10 baseline, and achieve a 100% filled schedule.

*   **C.1: Day-Specific Requests (MUST-HONOR, non-aggressive)** — First pass of the MUST-HONOR solver (see §10). Placed here to fulfill "easy" day requests before later passes rely on the schedule shape. Non-destructive so it doesn't blow up Top-5 integrity.
*   **C.2: Staff Optimization** — Clusters consecutive activities to lower staff teardown footprint.
*   **C.3: Remaining Preferences (6-20)** — Honors general troop requests in descending order.
*   **C.4: Guarantee Minimum Top 10** — Assures each troop gets a baseline of 2-3 Top 10 requests (the "Floor").
*   **C.5: Guarantee Top 10 with Exceptions** — Reconciles lingering valuable requests to push the Top 10 count higher (the "Maximize" pass).
*   **C.6: Fill All Remaining Slots** — Fills available empty slots via Fill Priority Algorithm to achieve a completely full board.
*   **C.6b: Scheduling half-slot activities during Sailing** — Uses the 30-minute dead time during a 90-minute Sailing block to assign a half-slot sidecar activity. Candidate order is `Gaga Ball`, `9 Square`, `Trading Post`, unless one of those is requested higher by the troop, in which case the highest-requested candidate is preferred. If all three are unavailable, fallback is `Campsite Free Time`. A half-slot fill may sit before or after Sailing regardless of the adjacent full-hour activity because the 30-minute Sailing buffer absorbs travel time (including Tower / ODS adjacency). If the chosen half-slot activity is ranked `11-20`, it may count as fulfilling that request; if it is ranked `1-10`, it does **not** substitute for the troop still receiving the full-hour version elsewhere.
*   **Exit Gate C:** Safety checks for Top 5 integrity to ensure the schedule is 100% populated.

### Phase D: Final Polish (The Shield — Strict Swap Phase)
**Goal:** Execute localized swaps to resolve cluster gaps, reduce day variance, and optimize commissioner ownership. The schedule is 100% full entering Phase D — all optimization steps are wrapped in Top-5/Top-10 safety harnesses and will roll back if they degrade preference placements. No interleaved gap-fix calls.

*   **D.1: Friday Reflection Optimization** — Swaps Reflection slots to pack a commissioner's troops together for geographic efficiency.
*   **D.2: Comprehensive Clustering & Smart Swaps** — Cross-slot smart trades to consolidate activities onto fewer days (guarded).
*   **D.3: Forced Clustering Consolidation** — Pulls distant activities closer, with a bypass path for non-day-requested troops to push through soft constraints (guarded).
*   **D.4: Ultra-Aggressive Excess Day Reduction** — Slashes excess days at a high threshold to fix severe fragmentation (guarded).
*   **D.5: Friday Super Troop Optimization** — Swaps exclusive activities with fillers across all days to align Friday blocks and reduce total setup days.
*   **D.6: Flexible Reflection Optimization** — Maneuvers floating Reflections to spread commissioner visits (adversarial to D.1, balancing geographic packing vs. sequential visitation).
*   **D.8: Setup Efficiency & Activity Clustering** — Smooths wet/dry transitions and continues day-consolidation (guarded).
*   **D.9: Outlier Activity & Commissioner Day Ownership** — Tweaks rogue single-day placements and aligns day ownership (guarded), honoring protected `Delta/Sailing` envelopes.
*   **D.10: Post-Fill Cluster Gap Optimization** — Closes 1-0-1 area-level pattern gaps internally.
*   **D.11: Comprehensive Final Cleanup** — Single point for Phase D gap filling and multi-layer validation/dedup.
*   **FINAL VERIFICATION / Multi-Slot Integrity** — Ensures all multi-slot blocks (Sailing, etc.) survived the swaps intact.
*   **Diagnostic: Commissioner Load Balancing** — Prints load distribution (formerly D.7).
*   **FINAL Day-Request Enforcement (MUST-HONOR, aggressive)** — The authoritative day-request pass (see §10). Runs at the **very end** (inside final validation) using the full T1-T6 ladder. Ensures MUST-HONOR placements are locked in and not undone by any previous repair/gap-fill pass.
*   **Exit Gate D (Acceptance Gate):** Gate checks `non_exempt_top5_misses == 0` (with MUST-HONOR exemptions per §2).

---

## 📊 6. Scoring & Metrics (Target: 1000)

While optimization scoring is important, the **Top 5 non-exempt success rule remains a hard contract**.

### Formulas & Definitions
* **Excess Day Formula:** For a given cluster area, calculate the required days as `required_days = ceil(activity_count / 3)`. If the area uses more than this calculated number, each additional day counts as an excess day penalty. *(Example: 7 activities requires `ceil(7/3) = 3` days. If scheduled across 4 days, there is 1 excess day).*
* **Cluster Gap Definition (Authoritative):** A gap is an **area-level** pattern, not a troop-level empty slot. For a given `day + cluster area`, a gap exists when:
  * Slot 1 has at least one activity from that area, and
  * Slot 3 has at least one activity from that area, and
  * Slot 2 has no activity from that same area.
  This is the canonical `1,-,3` cluster fragmentation pattern used by quality evaluation.
* **Final Clustering Repair Contract:** In Phase D/final validation, every single-slot activity on an official excess area day, plus the slot-1 and slot-3 edge activities in an official `1,-,3` cluster gap, must be considered for a guarded move or same-troop swap. A candidate may commit only when it reduces `excess_cluster_days` or `cluster_gaps` and does not create hard violations, non-exempt Top-5 misses, or Top-10 loss.

| Category | Points | Logic |
| :--- | :--- | :--- |
| **1. Preferences** | **450** | Innocent-until-proven-guilty base score. Deductions for non-exempt misses; deep hits are diagnostic and cannot push the bucket above 450. |
| **2. Efficiency** | **250** | Quality of clustering and logistics (penalties for each `excess day`, `cluster gap`, and missed batching/sailing efficiency expectation). |
| **3. Soft + Expectations** | **200** | Penalties applied for Soft Constraints and expected-but-missed behavior such as avoidable late Delta, missed Delta/Sailing pairing, or missed Aqua Trampoline sharing. |
| **4. Staff Balance** | **100** | Penalties for actual staff-load variance, underuse, over-target slots, or excessive staff load. |

There is no additive bonus bucket. Former bonuses are now expectation checks:
the schedule starts from the available component budgets and loses points when
expected quality behaviors are not achieved.

---

## 🧩 7. Special Logic, Formulas, & Exceptions

### Mode & State Exceptions
* **Smart Reflection:** If a troop has exactly one Friday slot remaining, the system must immediately lock in `Reflection`.

### Activity Nuances
* **Water Polo & Aqua Trampoline:** Authorized for sharing with activity-specific capacity semantics.
* **Large Troop Shotgun Rule:** Troops larger than 15 may receive up to two Shotgun sessions only when Shotgun is Top 5, and sessions must be on different days.
* **Reflection Placement Detail:** Reflection scheduling uses Friday slot strategy plus smart-lock behavior when exactly one Friday slot remains.
* **Top-10 Stability Layers:** In addition to Top-5 hard contract, implementation includes minimum Top-10 and Top-10 recovery passes as optimization safeguards.
* **Delta Displacement Rule:** `Delta` is requested-but-not-mandatory and is treated as a regular displaceable preference in late optimization/recovery passes when hard constraints and Top-5 guarantees remain intact.
* **Adaptive Day-Strategy Scope:** The durable family-day policy framework is retained only for `Delta/Sailing` in the default baseline. Wider staffed-family experiments must re-earn inclusion via fresh A/B regression wins.

### Scoring Exemptions (Deep Dive)
* **Multi-Slot Consumption:** No penalty is applied for missing lower-ranked activities (e.g., Rank 14) if higher-ranked multi-slot activities (like Sailing) physically consumed all available time.
* **Delta Timing:** Delta is scored against the earliest capacity window needed
  for the week's Delta demand. If demand fits Monday, Tuesday is a light miss,
  Wednesday is larger, Thursday larger still, and Friday largest. If demand
  requires Monday+Tuesday, Tuesday is not penalized and Wednesday becomes the
  first light miss.

---
> [!NOTE]
> **System Data Sources:**
> * Activities: `core/activities.py`
> * Configuration: `config/SKULL.json`
> * Scoring Weights: `utils/regression_checker.py`

---

## 🧪 8. Regression Evaluation Protocol (Fresh-Run Standard)

All official evaluations must be run as a fresh cycle so old artifacts cannot contaminate results.

### Mandatory Sequence
1. **Delete stale evaluation artifacts** from previous runs (e.g., `analysis_results*.json`, `regen_analysis.txt`, `violation_details.txt`, `regen_log.txt`, `regen_output.txt`).
2. **Regenerate all schedules** using `utils/regenerate_all_schedules.py`.
3. During regeneration, rebuild the authoritative `schedule_json.unscheduled` payload via `core/services/unscheduled_source.py`.
4. **Run evaluation only after regeneration** (recommended command: `python utils/regression_checker.py --fresh-eval --detailed --show-violations`).

### Reporting Rule
All authoritative Top 5/Top 10/etc miss metrics in the final report must come from `schedule_json.unscheduled`.
Implementation note: scoring internals may compute provisional preference deltas, but Top-5/Top-10 reported values are cross-checked against and sourced from `unscheduled`.

---

## 📝 9. Attempted Family-Day Strategy Rollout

The scheduler recently tested a broader durable family-day policy framework that extended adaptive day selection beyond `Delta/Sailing` to additional staffed families.

### What Was Attempted
* Added persistent family-day policy state so early day-shape decisions could survive later optimization phases.
* Extended adaptive / family-policy logic to `Tower/ODS`, `Rifle`, and evaluation-time quality acceptance.
* Measured the rollout with fresh full-regression runs across the 10-week evaluation set.

### Result
* The broader rollout regressed the official score, especially on smaller and Voyageur-heavy weeks.
* Main failure modes observed:
  * increased excess cluster days and area gaps,
  * staff-family day stacking on constrained days,
  * late-phase optimization pressure drifting away from the legacy score shape.

### Current Guidance
* Keep the durable family-day policy framework only where it has the clearest value: `Delta/Sailing`.
* Default `Tower/ODS`, `Rifle`, and `Super Troop` back to legacy / effectively-off adaptive behavior unless a fresh A/B run proves a specific family change is net-positive.
* Treat broader staffed-family adaptive rollout as experimental, not baseline policy.

---

## 🗝️ 10. Day-Request (MUST-HONOR) Solver Contract

> [!IMPORTANT]
> **Policy:** Any day-specific request authored on a troop (i.e. a
> `troop.day_requests[Day] = [activity_name, ...]`) **must be honored** in the
> final delivered schedule, even at the cost of a soft-constraint violation or
> the displacement of an otherwise-mandatory Top 5 activity. Physical
> impossibility is the ONLY acceptable reason for non-fulfillment, and such
> cases must be logged as `UNFULFILLED`/`INFEASIBLE` with an explicit reason.

### 10.1 Two-Pass Architecture
The solver `_schedule_day_requests(aggressive: bool)` runs twice:

1. **C.1 — Non-aggressive pass** (`aggressive=False`). Early in Phase C.
   Uses tiers T1-T2 only. Non-destructive; does NOT force-bypass soft
   constraints and does NOT displace existing entries. Its purpose is to
   place "easy" day-requests as early as possible so later phases (Top-10
   recovery, clustering) see the correct shape.

2. **Final Day-Request Enforcement — aggressive pass** (`aggressive=True`).
   Runs at the **end** of `_final_comprehensive_validation` after all internal
   repairs (not only immediately after the pre-validation multi-slot check in
   `FINAL VERIFICATION`). Uses the full tiered ladder (T1-T6). This is the
   **authoritative** enforcement point for the returned schedule.

### 10.2 Tiered Placement Ladder (Final Pass)
For each `(troop, activity, requested_day)`:

* **T0 — Already placed:** activity is already on the requested day → skip.
* **T0.5 — Thursday 3-hour opt-out:** if day is Thursday and the activity is
  3-slot, take the dedicated opt-out path (§10.4) — consumes Thu 1+2+3,
  troop skips the camp-wide mandatory 3rd-slot event.
* **T1 — Strict:** try `_can_schedule(...)` with no relaxations.
* **T2 — Relaxed:** try with `relax_constraints=True`.
* **T3 — Forced:** try with `relax_constraints=True, force_day_request=True`.
  Bypasses duplicate prevention, staff limit, back-to-back rule, beach slot
  rule, and beach staff cap; still honors physical invariants (`is_troop_free`,
  multi-slot boundary, request-only). Primary path for multi-day
  same-activity requests (e.g., `Shower House` Thu + Fri — after the first
  placement, the second needs duplicate bypass).
* **T4 — Wrong-day relocation:** pull the troop's existing entries for this
  activity IFF they are on a day NOT in the troop's day-request set for this
  activity (so multi-day requests don't cannibalize each other), then retry T3.
* **T5 — Non-Top-5 displacement:** displace any non-anchor, non-Top-5
  occupant on the requested day; retry.
* **T6 — Top-5 displacement:** last resort; displace a non-anchor Top-5
  occupant; retry. Top-5 misses created this way are **exempt** under
  Exemption 4 / 5 (§2).

Protected anchors (never displaced): `Reflection`, `Super Troop`,
`History Center`, `Disc Golf`. A `Delta` entry whose troop has `Sailing`
scheduled is also protected (pair-integrity; see §11).

### 10.3 `force_day_request` Flag Semantics
A `force_day_request=True` kwarg on `_can_schedule` indicates the activity is
being placed under MUST-HONOR. In this mode, the following soft checks are
bypassed: back-to-back rule, activity staff limit, duplicate prevention
(non-`Troop Shotgun`), beach slot rule, beach staff cap. Invariants that
remain enforced: `is_troop_free(slot, troop)`, multi-slot day-boundary fit,
request-only activity gate, and physical exclusivity.

### 10.4 Thursday 3-Hour Opt-Out (§4 extension)
A 3-slot activity day-requested on Thursday IS allowed. Meaning: the troop
opts out of the mandatory 3rd-slot camp-wide event to consume their entire
Thursday (slots 1, 2, and 3) with the requested 3-hour activity.

* **Implementation:** the solver's opt-out path directly appends three
  `ScheduleEntry` rows (Thu-1, Thu-2, Thu-3). Thu-3 is constructed as a
  virtual `TimeSlot(day=THURSDAY, slot_number=3)` on the fly; it is
  intentionally NOT emitted by `generate_time_slots()` so gap fill and
  ordinary placement for non-opt-out troops remain unchanged.
* **Downstream awareness:** boundary-fix (`_remove_overlaps`) and
  multi-slot integrity (`_fix_multislot_integrity`) consult
  `_is_day_request_thursday_3slot(troop, activity)` and preserve the
  opt-out trio when it applies. All other cleanup passes operate
  unchanged on the opt-out entries.
* **Eligibility gate:** opt-out only applies when the troop's
  `day_requests[Thursday]` literally contains the 3-slot activity name.

### 10.5 Known Limitations
* **Downstream removal risk:** the Thursday opt-out is sensitive to
  cleanup passes that iterate `schedule.entries` and remove based on
  max-slot heuristics. The two critical removal sites are guarded, but
  rare interactions with future passes may still strip opt-out entries.
  A robust long-term fix requires teaching the data model that Thursday
  has an optional 3rd slot (guarded per-troop).
* **Anchor blockage:** a request that targets a day whose every slot is
  a protected anchor (e.g., a troop with `Super Troop` + `Reflection`
  both on the same day) cannot be placed and is logged `UNFULFILLED`.
  This is architecturally unavoidable given anchor semantics.

### 10.6 Observability
Every day-request pass prints:

```
--- <pass_label> (MUST-HONOR) ---
  <Troop>: <Activity> -> <DAY>-<slot>             # honored strict/relaxed
  <Troop>: <Activity> -> <DAY>-<slot> [FORCED]    # T3 force
  <Troop>: <Activity> -> <DAY>-<slot> [FORCED-RELOCATED]  # T4
  <Troop>: <Activity> -> Thursday 1-2-3 [THURSDAY-3HR-OPT-OUT]
  [UNFULFILLED] <Troop>: <Activity> on <Day>      # T5/T6 failed
  [INFEASIBLE] <Troop>: <Activity> on <Day> (reason)
  Summary: honored=N, relocated=N, forced=N[, infeasible=N]
```

---

## 🔗 11. Delta / Sailing Pair Protection

### Problem
Historically, Top 1-5 recovery and enforcement passes treated `Sailing`
as protected (it is a Rock — 2-slot 90-minute multi-day structure) but
treated `Delta` as a freely displaceable preference. When a later pass
reclaimed a Delta entry for a Top-5 recovery, the Delta/Sailing pairing
drifted off the same day, and `B.6` had to repair it — sometimes
successfully, sometimes leaving durable clustering damage.

### Policy
A Delta entry whose troop has `Sailing` scheduled is treated as
**pair-protected** and is NOT eligible for displacement in ANY recovery,
enforcement, or swap pass, across Phases B-D. Implemented via the helper
`_is_pair_protected_delta(entry)` (true iff `entry.activity == "Delta"`,
the troop's preferences include `"Sailing"`, and a `Sailing` entry
exists for that troop). This check is inserted alongside the existing
`PROTECTED` membership checks at every displacement site.

### Effect on `B.6`
`B.6 — Enforce Delta + Sailing same-day pairing` remains enabled as a
safety net. In the improved policy, most pairings are preserved in-place
by pair protection, so B.6 typically reports little-to-no work. If
future A/B runs show B.6 has become a no-op, it can be retired.

### Status
* **Implemented:** pair protection in all Top 1-5 recovery and
  enforcement displacement loops (`_force_top1_preferences`,
  `_guarantee_all_top5`, `_enforce_mandatory_top5`,
  `_schedule_preferences_range`).
* **Pending:** similar pair protection in late-phase D clustering and
  swap passes; measure whether B.6 can safely be retired after broader
  coverage. (Baseline measurements with partial coverage already show
  improvement: +10.6 average week score, −0.40 average excess cluster
  days versus the MUST-HONOR-only baseline.)