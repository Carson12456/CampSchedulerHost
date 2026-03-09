# 🧠 BRAIN: Central Source of Truth
**The Summer Camp Scheduler System Blueprint**

| Metadata | Details |
| :--- | :--- |
| **Version** | 2.4.1 |
| **Last Updated** | 2026-03-04 |

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
1. **Hard Constraints First:** Never accept hard-constraint violations.
2. **Top 5 Contract Second:** Prefer a soft-constraint violation over creating a non-exempt Top 5 miss.
3. **Soft Constraints Third:** Optimize soft compliance only after Hard + Top 5 are protected.

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
    * A troop cannot have Delta, and then have a Tower or ODS actviity afterwards, and vice versa.
* **Capacity Safety Limits:**
    * Canoes: Max 26 people.
    * Global Staff: Base max 16 per slot; clustering-targeted scheduling can use controlled elevated limits for specific staff-clustering activities.
    * Beach Staff: Max 12 per slot.
    * Beach Saturation: Max 4 staffed beach activities per slot, with a narrowly-scoped Top-5 Aqua Trampoline overload path up to 5.
* **The Acceptance Gate:** `non_exempt_top5_misses == 0` is strictly enforced.
* **Day Requests:** Day-specific requests are enforced as hard constraints in normal placement (override only in explicit recovery paths).
* **Shower House Hard Rules:**
    * No Shower House on Monday.
    * Do not place Shower House before a later Super Troop or wet activity on the same day (strict mode).

### 🟡 SOFT Constraints (Score Deductions)
Violating these will lower the schedule's quality score, but will not break the build.

#### 1. Prohibited Same-Day Pairs
* *Accuracy:* Troop Rifle / Troop Shotgun / Archery
* *Boats:* Paired boating activities
* *Water Games:* Aqua Trampoline / Water Polo / Greased Watermelon
* *Free Time:* Trading Post / Shower House / Campsite Free Time
* *Balls:* Nine Square / Gaga Ball

#### 2. Wet/Dry Flow & Transitions
* Avoid "Wet-Dry-Wet" sandwiches.
* Avoid direct transitions between Wet activities and Tower/ODS.
* Beach activities should preferably land in Slot 1 or Slot 3 (Slot 2 is acceptable on Thursdays only).

#### 3. Activity Consecutiveness
* `Tie Dye`, `Rifle`, and `Shotgun` should actively seek to run back-to-back within area schedules to minimize setup/teardown time.
* `History Center` and `Disc Golf` should have compatible adjacency (Balls/reserve-adjacent behavior). Current implementation allows a broader compatibility set than strict "Balls-only".

---

## 🏗️ 5. System Architecture & Phase Gates

The `ConstrainedScheduler` executes from Phase A to Phase D. Every phase includes Top 5 anti-miss safeguards.

### Phase A: Foundation (The Skeleton)
1.  **Place Anchors:** Lock in rigid requirements (`Reflection`, `Super Troop`, Tuesday mechanics).
2.  **Reserve Large Blocks:** Map out multi-slot structures (3-hour blocks, Sailing, Delta/Sailing shapes).
3.  **Secure High-Risk Assets:** Front-load highly contested Top 5 resources (especially constrained beach windows).
* **Exit Gate A (Operational):** Run immediate gap detection/repair and preserve Top-5 safety context for subsequent recovery passes. 

### Phase B: Core Requests (The Meat)
2.  **Place Top 1–5:** Schedule the remaining primary requests.
3.  **Mandatory Recovery Loops:** Run placement passes (Strict -> Relaxed -> Displacement/Cross-slot recovery).
4.  **The Golden Rule:** Never displace an existing Top 5 request just to accommodate a Top 6+ request.
* **Exit Gate B (Operational):** Top-5 recovery loops are required in Phase B; strict zero non-exempt Top-5 misses is hard-enforced at final acceptance gate.

### Phase C: Optimization (The Polish)
1.  **Optimize:** Balance staff loads and improve cluster quality.
2.  **Fill Gaps:** Utilize the **Fill Priority Algorithm** (sourced from `SKULL.json` under `constraints.fill_priority`). Always use high-value activities first, falling back on passive fillers only as a last resort.
3.  **Preserve Top 5:** Maintain Top 5 integrity through all reshuffling.
* **Continuous Gate C (Operational):** Optimization and swap paths use localized Top-5 safety checks/rollback patterns; final global zero-miss enforcement happens in Phase D acceptance.

### Phase D: Final Verification (The Shield)
1.  **Sanitize:** Apply final constraint cleanup.
2.  **Targeted Recovery:** Fix any post-optimization drift.
3.  **Final Acceptance Gate:** The schedule is only accepted if there are:
    * No accepted hard constraint violations after final sanitization/repair passes.
    * No empty troop slots.
    * `non_exempt_top5_misses == 0`.
    *(If any condition fails, re-enter the repair loop before acceptance.)*
4.  **Last Scheduling Action (D.10):** The final optimization pass may replace a lower-ranked **staffed** activity with a higher-ranked missing **unstaffed** preference for the same troop when:
    * hard constraints remain satisfied,
    * non-exempt Top 5 misses do not increase,
    * and penalty-oriented quality signals do not regress (soft-pattern violations, excess cluster days, area-level cluster gaps, and composite quality trend).
    The swap is slot-conservative to avoid unnecessary schedule churn.
5. **Additional Implemented Verification Passes:**
    * Multi-slot integrity normalization.
    * Beach saturation cleanup.
    * Final Sailing exclusivity normalization pass.

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

| Category | Points | Logic |
| :--- | :--- | :--- |
| **1. Preferences** | **450** | Base score. Deductions for non-exempt misses, bonuses for deep hits. |
| **2. Efficiency** | **250** | Quality of clustering and logistics (penalties for each `excess day` or `cluster gap`). |
| **3. Soft Compliance** | **150** | Penalties applied for violating Soft Constraints. |
| **4. Staff Balance** | **100** | Penalties for variance, underuse, or excessive staff load. |
| **5. Bonuses** | **50** | Points awarded for AT sharing, early-week bias, and sailing pairings. |

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

### Scoring Exemptions (Deep Dive)
* **Multi-Slot Consumption:** No penalty is applied for missing lower-ranked activities (e.g., Rank 14) if higher-ranked multi-slot activities (like Sailing) physically consumed all available time.

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