# 🧠 BRAIN: Central Source of Truth

**Version:** 2.2.0 | **Last Updated:** 2026-02-21 | **Status:** BLUEPRINT

This document is the **System Blueprint** for the Summer Camp Scheduler. It defines the "Laws of Physics" for the scheduling engine: constraints, rotation logic, scoring, and phase behavior.

---

## 🎯 Executive Summary

### Core Principles
> [!IMPORTANT]
> **Satisfaction First:** User preferences (Top 5) take precedence over administrative ease.
> **Hard Contract:** Scheduler must produce **100% non-exempt Top 5 success**.

1. **Prevention Over Cure:** Validate constraints before placement.
2. **Rocks, Pebbles, Sand:** Place large/rigid items first, then core requests, then fills.
3. **Fail-Fast:** Hard-constraint violation invalidates schedule.
4. **No Empty Slots:** Every troop has an activity in every available slot.
5. **Zero Non-Exempt Top 5 Misses:** Non-exempt Top 5 misses are never acceptable.

---

## ✅ Top 5 Success Contract (Authoritative)

### Definitions
1. **Top 5 Requested Activity**
   - A troop preference with rank 1-5.
2. **Missed Activity**
   - A Top 5 requested activity not present in that troop's final schedule.
3. **Exempt Miss**
   - A missed activity that meets a formal exemption rule:
   - **3-hour duplication rule:** Troop requested multiple 3-hour activities and already received one.
   - **Tuesday HC/DG saturation rule:** Only the highest three requested of both DG and HC can get one of teh three avalable slots.
   - **Canoe-family duplication rule:** If a troop already has one canoe-family activity, another missed canoe-family request may be exempt.
4. **Non-Exempt Miss**
   - Any missed Top 5 request that does not meet an exemption rule.

### Required Outcome
- `non_exempt_top5_misses == 0`
- Equivalent to `100%` non-exempt Top 5 success.
- Any non-zero value is a failed run and must trigger repair logic.

### Single Source of Truth Protocol (Mandatory)
- All Top-5/Top-10 miss reporting MUST be read from `schedule_json.unscheduled`.
- Authoritative path format:
  - `unscheduled.<troop_name>.top5[]`
  - `unscheduled.<troop_name>.top10[]`
- Every miss item MUST include `name`, `rank`, and `is_exempt`.
- Reconstructing misses directly from `troop.preferences` for reporting is forbidden.
- If `unscheduled` is missing, analysis must fail fast instead of using fallback calculations.

---

## 💃 The Waltz: Commissioner Rotation

The camp is geographically divided into three commissioner areas for balanced coverage.

### 1. Commissioner Areas
| Group | Commissioner | Campsites (Geographic Cluster) |
| :--- | :--- | :--- |
| **North** | **Comm A** | Massasoit, Tecumseh, Samoset, Black Hawk, Taskalusa |
| **Central** | **Comm B** | Powhatan, Red Cloud, Cochise, Joseph, Tamanend |
| **South** | **Comm C** | Pontiac, Skenandoa, Sequoyah, Roman Nose |

### 2. Rotation Schedule
| Activity Group | **Comm A** (North) | **Comm B** (Central) | **Comm C** (South) |
| :--- | :--- | :--- | :--- |
| **Delta / Sailing** | Monday | Tuesday | Wednesday |
| **Tower / ODS** | Thursday | Monday | Tuesday |
| **Rifle / Super Troop** | Monday* | Tuesday* | Wednesday* |
| **Archery / Boats** | Wednesday | Friday | Monday |

Pairing integrity is more important than strict day ownership if both cannot be satisfied simultaneously.

## ⏳ Fill Priority Algorithm

When a troop has open slots and no remaining preferred requests, fills come from `SKULL.json` (`constraints.fill_priority`).

**Objective:** Fill with high-value activities first; use passive fillers only as last resort.

## 📚 Constraint Dictionary

### 🔴 HARD Constraints (Invalidates Schedule)
1. **Exclusive Double-Booking:** Only one troop per slot in configured exclusive activities.
2. **Completeness:** Every troop must have all weekly slots filled.
3. **Mandatory Anchors:**
   - `Reflection` on Friday.
   - `Super Troop` once weekly.
   - `History Center` and `Disc Golf` constrained to Tuesday.
4. **Capacity Safety:**
   - Canoes max 26 people.
   - Global staff max 16 per slot.
   - Beach staff max 12 per slot.
   - Beach saturation max 4 staffed beach activities per slot.
5. **Top 5 Acceptance Gate:** Non-exempt Top 5 misses must be zero.

### 🟡 Soft Constraints (Score Deductions)
Violations reduce score but do not directly invalidate schedule.

#### 1. Prohibited Same-Day Pairs
- Accuracy: `Troop Rifle` / `Troop Shotgun` / `Archery`
- Boats: paired canoe-family activities
- Water Games: `Aqua Trampoline` / `Water Polo` / `Greased Watermelon`
- Free Time: `Trading Post` / `Shower House` / `Campsite Free Time`
- Balls: 'Nine Square' / 'Gaga Ball'

#### 2. Wet/Dry Patterns
- Avoid wet-dry-wet sandwiches.
- Avoid direct Wet <-> Tower/ODS transitions.
- Beach slot preference is 1 or 3 (Thursday has slot-2 exception).

#### 3. Activity Consecutiveness
*   `Tie Dye`, `Rifle`, `Shotgun` escecially and specifically should seek to run back-to-back in the area schedules to reduce setup/teardown.
History Center and Disc Golf must have a Balls activity either before or after it.

---

## 📊 Scoring & Metrics (Target: 1000)

| Category | Points | Logic |
| :--- | :--- | :--- |
| **1. Preferences** | **450** | Base score. Deductions for misses, bonuses for deep hits. Top 5 miss penalties apply to **non-exempt** misses. |
| **2. Efficiency** | **250** | Clustering and logistics quality (`excess days`, `cluster gaps`). |
| **3. Soft Compliance** | **150** | Penalties for soft-constraint violations. |
| **4. Staff Balance** | **100** | Variance and underuse/excessive load penalties. |
| **5. Bonuses** | **50** | AT sharing, early-week bias, sailing pairing bonuses. |

> Preference scoring exists for optimization, but Top 5 non-exempt success is a hard acceptance contract.

---

## 🏗️ System Architecture & Phase Gates

The `ConstrainedScheduler` runs A -> D. Each phase has Top 5 anti-miss safeguards.

### Phase A: Foundation (The Skeleton)
1. Place rigid anchors (`Reflection`, `Super Troop`, Tuesday-only mechanics).
2. Reserve rigid multi-slot structures (3-hour, Sailing, Delta/Sailing shape).
3. Front-load high-risk Top 5 resources (especially constrained beach windows).
4. **Exit Gate A:** Emit Top 5-at-risk list (missing candidates + blocking reason).

### Phase B: Core Requests (The Meat)
1. Force Top 1.
2. Place Top 2-5.
3. Run mandatory recovery in passes:
   - strict placement
   - relaxed placement
   - displacement/cross-slot recovery
4. Never displace an existing Top 5 to place Top 6+.
5. **Exit Gate B:** Non-exempt Top 5 misses must be zero.

### Phase C: Optimization (The Polish)
1. Optimize staff/load/cluster quality.
2. Fill remaining gaps.
3. Preserve Top 5 integrity during all moves.
4. **Continuous Gate C:** After each major optimizer, re-check non-exempt Top 5 misses; rollback/repair if miss count rises.

### Phase D: Final Polish & Verification (The Shield)
1. Apply final constraint sanitization and cleanup.
2. Run targeted Top 5 recovery if any post-optimization drift occurred.
3. **Final Acceptance Gate:** all must pass:
   - no hard violations
   - no empty troop slots
   - `non_exempt_top5_misses == 0`
4. If any gate fails, re-enter repair loop before schedule acceptance.

---

## 🧩 Special Logic & Exceptions

### Voyageur Mode
*   **Definition:** Specialized schedule for older scout troops.
*   **Overrides:**
    *   Commissioner assignments may differ (North/South split).
    *   **HC/DG Pairing:** Must be paired with `Gaga Ball` or `9 Square` for transition buffers.

### Smart Reflection
- If exactly one Friday slot remains, lock in `Reflection` immediately.

### Activity Nuances
- `Sailing` consumes 1.5 slots (scheduled as 2).
- `Water Polo` and `Aqua Trampoline` can support small-troop sharing.

### Clustering Metric Clarification
*   **Excess Day Formula:** For each cluster area, `required_days = ceil(activity_count / 3)`. If an area uses more than `required_days`, each extra day counts as an excess day.
*   **Example (Excess Day):** 7 activities -> `ceil(7/3) = 3` required days. If scheduled across 4 days, that is **1 excess day**.
*   **Cluster Gap Definition:** A cluster gap is specifically `Slot 1 = area activity`, `Slot 2 = empty`, `Slot 3 = same area activity` for a troop/day.  
*   **Intent:** Either fill Slot 2 appropriately or move one of the outer activities toward Slot 2 to avoid fragmented same-day clustering.

### Scoring Exemptions
*   **Activity Duplication:** If a troop requests multiple 3-hour activities (e.g., Tamarac & Itasca), successfully scheduling ONE exempts the others from "Missed Preference" penalties.
*   **Canoe-Family Duplication:** If a troop already receives one of `Troop Canoe`, `Troop Kayak`, `Canoe Snorkel`, `Nature Canoe`, or `Float for Floats`, a second missed canoe-family request is exempt.
*   **Multi-Slot Consumption:** Scores are not penalized for missing lower-ranked activities (e.g. Rank 14) if higher-ranked multi-slot activities (Sailing, 3-hour blocks) physically consumed the available slots.
*   **HC/DG Saturation:** If all Tuesday slots are filled with HC and DG, missing one of them is exempt.

---

> [!NOTE]
> **Data Sources:**
> * **Activities:** `core/activities.py`
> * **Configuration:** `config/SKULL.json`
> * **Scoring Weights:** `utils/regression_checker.py`