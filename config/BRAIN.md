# 🧠 BRAIN: Central Source of Truth

**Version:** 1.2.0 | **Last Updated:** 2026-02-06 | **Status:** ACTIVE

This document serves as the **Single Source of Truth** for all decision-making logic, rules, and priorities for the Summer Camp Scheduler.

* **Logic:** Defined here in `BRAIN.md`.
* **Data:** Defined in `config/SKULL.json`.
* **Activities & Durations:** Defined in `core/activities.py`.

---

## 🎯 Executive Summary

### Core Principles
> [!IMPORTANT]
> **Satisfaction First:** User preferences (Top 5) take precedence over administrative ease.

* **Prevention Over Cure:** Constraints are validated *before* placement, not fixed after.
* **Rocks, Pebbles, Sand:** Schedule large/constrained items (3-hour blocks, Sailing) first.
* **Fail-Fast:** Hard constraints trigger immediate rejection.
* **No Empty Slots:** Every troop must have an activity in every available slot (**14 slots/week**).

---

## 📚 Constraint Dictionary

### 🔴 HARD Constraints (Non-Negotiable)

#### 1. Exclusiveness (Max 1 Troop per Slot)
Only one troop is allowed per slot in these specific locations:
* `Tower`, `Delta`, `Super Troop`, `Sailing`, `Rifle`, `Archery`, `Handicrafts`, `Nature Center`, 'Outdoor Skills'  
All slots of all troop's schedules must be complete, no empty slots allowed.

#### 2. Capacity & Safety Limits
* **Global Staff:** Maximum **16** staff utilized per slot (Target: <= 14).
* **Beach Staff:** Maximum **4** staffed activities per slot.
* **Canoes:** Maximum **26** people (Scouts + Adults) per slot.
* **Request Only:** `Tie Dye` and `Troop Shotgun` are **never** scheduled unless explicitly requested.

#### 3. Time & Logic Rules
* **Sailing:** Counts as **1.5 slots** (increases to **2.0** on Thursday).
* **Geographic Spacing:** `Delta` and `Tower`/`ODS` can be done on the same day if separated by another activity, but they **NEVER** occur back-to-back.

---

### 🟡 SOFT Constraints (Avoidance-Based)

#### 1. Prohibited "Same-Day" Pairs
Troops should not perform these pairs of activities within the same 24-hour window:
* **Weapons:** `Troop Rifle` + `Troop Shotgun`
* **Boats:** Any two boat activities (`Canoe`, `Snorkel`, `Nature Canoe`, `Float`)
* **Water Games:** Any two of `Aqua Trampoline`, `Water Polo`, `Greased Watermelon`
* **Reserves:** `Trading Post`, `Campsite Free Time`, or `Shower House`

#### 2. Wet/Dry Patterns
* **Beach Activities:** Should be Slot 1 or 3. (**Exception:** Thursday uses Slot 2).
* **No "Sandwiching":** Do not schedule **Wet → Dry → Wet**.
* **Wet Activities List:** `Aqua Trampoline`, `Water Polo`, `Greased Watermelon`, `Troop Swim`, `Obstacle Course`, `Canoe/Kayak`, `Snorkel`, `Nature Canoe`, `Float`, `Sailing`, `Sauna`.

#### 3. Area Clustering
* **Goal:** Schedule activities in the same geographic zone on the same day to minimize travel.
* **Avoid:** Strenuous activities (`Tower`, `ODS`) back-to-back with active `Wet` activities.

---

## 🏗️ System Architecture

### The "Spine"
These are the mandatory anchors that define the week's structure:
1. **Friday Reflection:** MANDATORY for all troops.
2. **Super Troop:** MANDATORY once per week.
3. **Tuesday HC/DG:** History Center and Disc Golf are Tuesday exclusives.
4. **Thursday Sailing:** Sailing extends to 2 full slots.

### Commissioner Rotation (The "Waltz")
Major areas rotate by Commissioner Group to ensure even distribution:

| Area | Comm A (North) | Comm B (Central) | Comm C (South) |
| :--- | :--- | :--- | :--- |
| **Delta / Sailing** | Monday | Tuesday | Wednesday |
| **Tower / ODS** | Thursday | Monday | Tuesday |
| **Rifle / Super Troop** | Tuesday | Wednesday | Thursday |
| **Archery / Boats** | Wednesday | Thursday | Friday |

*Note: Early-week bias (Mon/Tue) may override rotation for high-priority placement.*

---

## ⚡ Scheduling Priorities (Phases)

| Phase | Title | Focus |
| :--- | :--- | :--- |
| **Phase A** | **Foundation** | Anchors (Reflection, Super Troop), Tuesday Spines, 3-Hour Blocks. |
| **Phase B** | **Core Requests** | **Attributes** (Top 1) → **Top 5** (Targeting 100% success). |
| **Phase C** | **Optimization** | Fill gaps, optimize Staff Variance, consolidate Clusters. |
| **Phase D** | **Cleanup** | Resolve lingering conflicts or empty slots. |

---

## 📊 Scoring & Metrics (Target: 1000 = Perfect Schedule)

| Component | Points | Description |
| :--- | ---: | :--- |
| **Preferences** | **450** | +2.7 to +5.4 pts per top preference satisfied. |
| **Cluster Efficiency** | **250** | Same geographic zone on same day. |
| **Soft Constraints** | **150** | Wet patterns, same-day pairs, etc. |
| **Staff Balance** | **100** | Even staff distribution across slots. |
| **Bonuses** | **50** | Early week, batching, sailing, AT Sharing. |

### Invalidation Rules (Automatic -1000)
- 🔴 **Hard Constraint Violation** (e.g., exclusive double-book, missing Reflection)
- 🔴 **Empty Slot** (any gap in schedule)

> [!NOTE]
> For specific penalty values, refer to `config/SKULL.json` and `utils/regression_checker.py`.


> [!NOTE]
> For specific numerical values and configuration, refer to `config/SKULL.json`.