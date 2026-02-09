# 🧠 BRAIN: Central Source of Truth

**Version:** 2.0.0 | **Last Updated:** 2026-02-09 | **Status:** BLUEPRINT

This document is the **System Blueprint** for the Summer Camp Scheduler. It defines the "Laws of Physics" for the scheduling engine—every constraint, rotation logic, scoring metric, and algorithmic phase is documented here.

---

## 🎯 Executive Summary

### Core Principles
> [!IMPORTANT]
> **Satisfaction First:** User preferences (Top 5) take precedence over administrative ease.

1.  **Prevention Over Cure:** Constraints are validated *before* placement.
2.  **Rocks, Pebbles, Sand:** Schedule large items (3-hour blocks, Sailing) first, then core requests, then fill.
3.  **Fail-Fast:** Hard constraints trigger immediate rejection (-1000 score).
4.  **No Empty Slots:** Every troop must have an activity in every available slot (14 slots/week).

---

## 💃 The Waltz: Commissioner Rotation

The camp is geographically divided into three Commissioner Areas to ensure even coverage. Activities rotate through these areas on specific days.

### 1. Commissioner Areas (The "Dancers")
| Group | Commissioner | Campsites (Geographic Cluster) |
| :--- | :--- | :--- |
| **North** | **Comm A** | Massasoit, Tecumseh, Samoset, Black Hawk, Taskalusa |
| **Central** | **Comm B** | Powhatan, Red Cloud, Cochise, Joseph, Tamanend |
| **South** | **Comm C** | Pontiac, Skenandoa, Sequoyah, Roman Nose |

### 2. The Rotation Schedule (The "Steps")
Commissioners manage specific high-demand areas on specific days.

| Activity Group | **Comm A** (North) | **Comm B** (Central) | **Comm C** (South) |
| :--- | :--- | :--- | :--- |
| **Delta / Sailing** | Monday | Tuesday | Wednesday |
| **Tower / ODS** | Thursday | Monday | Tuesday |
| **Rifle / Super Troop** | Monday* | Tuesday* | Wednesday* |
| **Archery / Boats** | Wednesday | Friday | Monday |

Note: If the activities are not scheduled on their commissioner day, it is then most convienient to proritize pairing the activities than keeping both on their suggested day.

---

## 📚 Constraint Dictionary

### 🔴 HARD Constraints (Invalidates Schedule)
Violating any of these results in a **-1000 point penalty** and an invalid schedule.

1.  **Exclusive Double-Booking:** Only **ONE** troop per slot in these areas:
    *   `Tower`, `Rifle`, `Shotgun`, `Archery`, `Delta`, `Super Troop`, `Sailing`, `Gaga Ball`, `9 Square`.
    *   *Note: Water Polo & AT have special exceptions for small troops.*
2.  **Completeness:** Every troop must have exactly **14 slots** filled (Mon-Wed 3/day, Thu 2/day, Fri 3/day).
3.  **Mandatory Anchors:**
    *   **Friday Reflection:** Must be scheduled on Friday.
    *   **Super Troop:** Must occur once per week.
    *   **History Center** & **Disc Golf** on **Tuesday** (Exclusive Day).
4.  **Capacity Safety:**
    *   **Canoes:** Max **26** people (Scouts + Adults) per slot.
    *   **Global Staff:** Max **16** staff used per slot.

### 🟡 SOFT Constraints (Score Deductions)
Violating these reduces the schedule score but does not invalidate it.

#### 1. Prohibited Pairs (Avoidance)
Troops should NOT do these pairs on the **same day**:
*   **Accuracy:** `Troop Rifle` OR `Troop Shotgun` or `Troop Archery`
*   **Boats:** Any pair of `Canoe`, `Snorkel`, `Nature Canoe`, `Floats for Floats`
*   **Water Games:** `Aqua Trampoline` OR `Water Polo` OR `Greased Watermelon`
*   **Infrastructure:** `Trading Post` OR `Shower House` OR `Campsite Free Time`

#### 2. Wet/Dry Patterns
*   **Pattern:** Avoid **Wet → Dry → Wet** sandwiches.
*   **Transition:** Avoid **Wet → Tower/ODS** (or vice versa) immediately back-to-back.
*   **Slot Preference:** Beach activities prefer **Slot 1 or 3**.
    *   *Exception:* Thursday allows Slot 2 for Beach.
    *   *Exception:* Sailing is always 1.5 slots (meaning it runs slot 1 and 2, then the second activity runs slot 2 and 3. This is because they only actually run for 1.5 hours but appear and are scheduled as 2 slots).

#### 3. Activity Consecutiveness
*   `Tie Dye`, `Rifle`, `Shotgun` should run back-to-back in the area schedules to reduce setup/teardown.    

---

## 📊 Scoring & Metrics (Target: 1000 pts)

The scheduler aims for a perfect score of **1000**.

| Category | Points | Logic |
| :--- | :--- | :--- |
| **1. Preferences** | **450** | **Base Score.** Deductions for misses, bonuses for deep hits.<br>• **Top 5 Miss:** -5.4 to -2.7 per miss (Weighted by rank).<br>• **Rank 6-14 Miss:** -2.6 to -1.2 per miss.<br>• **Rank 15-20 Hit:** +1.0 to +0.2 Bonus. |
| **2. Efficiency** | **250** | **Base Score.** Measures clustering and logistics.<br>• **Excess Day:** -25 pts (Spread too thin).<br>• **Cluster Gap:** -15 pts (1-x-3 pattern). |
| **3. Soft Compl.** | **150** | **Base Score.** Adherence to Soft Constraints.<br>• **Violation:** -10 pts per prohibited pair/pattern.<br>• **Beach Slot 2:** -3 pts per non-Thursday use. |
| **4. Staff Balance** | **100** | **Base Score.** Even distribution of staff load.<br>• **Variance:** -5 pts per variance unit.<br>• **Severe Underuse:** -3 pts per dead slot. |
| **5. Bonuses** | **50** | **Add-ons.**<br>• **AT Sharing:** +50 pts (2 small troops share AT).<br>• **Early Week:** +10 pts (Front-loading Mon/Tue).<br>• **Sailing Pairs:** +10 pts (Same-day sailing). |

---

## 🏗️ System Architecture & Phasing

The `ConstrainedScheduler` executes in specific phases to ensure priorities are met.

### Phase A: Foundation (The Skeleton)
1.  **Anchors:** Place `Reflection` (Friday) and `Super Troop` (Weekly).
2.  **Spines:** Place `History Center` & `Disc Golf` on **Tuesday** (Exclusive Day).
3.  **Rocks:** Place **3-Hour Activities** (`Tamarac`, `Itasca`, `Back of the Moon`).
4.  **Sailing:** Place `Sailing` (High priority, 1.5 slot duration).
    *   *Optimization:* Pair with `Delta` on the same day if possible.

### Phase B: Core Requests (The Meat)
1.  **Top 1:** Forced placement of #1 choice.
2.  **Top 5 Guarantee:**Iteratively place Ranks 2-5.
    *   *Note:* Creates "Islands" around these fixed points.

### Phase C: Optimization (The Polish)
1.  **Staff Smoothing:** Move flexible items to balance staff counts across slots.
2.  **Gap Filling:** Fill empty slots with `Gaga Ball`, `9 Square`, `Nature`, `Free Time`.
3.  **Cleanup:**
    *   Resolve Exclusive Conflicts.
    *   Fix Beach Slot 2 violations.
    *   Ensure HC/DG have transition pairings.

---

## 🧩 Special Logic & Exceptions

### Voyageur Mode
*   **Definition:** Specialized schedule for older scout troops.
*   **Overrides:**
    *   Commissioner assignments may differ (North/South split).
    *   **HC/DG Pairing:** Must be paired with `Gaga Ball` or `9 Square` for transition buffers.

### Smart Reflection
*   **Trigger:** If a troop has only **1 Friday slot left** open.
*   **Action:** Immediately schedules `Reflection` in that slot to prevent a lockout.

### Activity Nuances
*   **Sailing:** Counts as **1.5 slots**. On Thursday, it consumes the whole morning (2 slots).
*   **Water Polo:** Can accommodate **2 small troops** (<8 people) simultaneously.
*   **Aqua Trampoline:** Can accommodate **2 small troops** (<16 people) simultaneously (Bonus +50 pts).

---

> [!NOTE]
> **Data Sources:**
> *   **Activities:** `core/activities.py`
> *   **Configuration:** `config/SKULL.json`
> *   **Scoring Weights:** `utils/regression_checker.py`