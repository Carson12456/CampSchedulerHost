# BRAIN: Central Source of Truth

**Version:** 1.0.0
**Last Updated:** 2026-02-05

This document is the **Single Source of Truth** for all decision-making logic, constraints, and priorities for the Summer Camp Scheduler. All code logic (`core/`) and configuration (`config/`) must derive from the principles defined here.

---

## 🎯 Executive Summary

### Core Principles
1.  **Satisfaction First**: User preferences (Top 5) take precedence over administrative ease.
2.  **Prevention Over Cure**: Validate constraints *before* placing any activity.
3.  **Rocks, Pebbles, Sand**: Schedule large/constrained items (3-hour blocks, Sailing) first.
4.  **Fail-Fast**: Hard constraints must trigger immediate rejection.
5.  **No Empty Slots**: Every troop must have an activity in every available slot (14 slots/week).

---

## 🏗️ System Architecture

### The "Spine" (Core Schedule Structure)
The schedule is built around a "Spine" of mandatory and fixed-time activities that anchor the rest of the week.

1.  **Friday Reflection**: MANDATORY. Every troop has Reflection on Friday.
2.  **Super Troop**: MANDATORY. Once per week per troop. Exclusive area (one troop at a time).
3.  **Tuesday HC/DG**: History Center and Disc Golf are **Tuesday ONLY**.
4.  **Thursday Sailing**: Sailing duration increases to 2.0 slots on Thursday (vs 1.5 normally).

### Commissioner Structure
Troops are divided into 3 Commissioner Groups based on campsite geography to ensure even distribution.
-   **North (Comm A)**: Massasoit, Tecumseh, Samoset, Black Hawk, Taskalusa
-   **Central (Comm B)**: Powhatan, Red Cloud, Cochise, Joseph, Tamanend
-   **South (Comm C)**: Pontiac, Skenandoa, Sequoyah, Roman Nose

**Rotation Logic**:
-   Commissioners rotate responsibility for key areas (Super Troop, Delta, etc.) to prevent overlaps.
-   See `config/SKULL.json` for specific day-rotation maps.

---

## 📋 Constraints

### 🔴 HARD Constraints (Must Never Violate)

1.  **No Double Booking**: A troop cannot be in two places at once.
2.  **Activity Capacity**:
    -   **Exclusive Areas**: Max 1 troop per slot (Tower, Rifle, Archery, etc.).
    -   **Sailing**: Max 1 troop per slot (but allows 2 sessions/day due to staggered start).
    -   **Canoes**: Max 26 people (Scouts + Adults).
    -   **Beach Staff**: Max 4 staffed activities per slot.
3.  **Staff Safety Caps**:
    -   **Absolute Max**: 16 staff per slot globally.
    -   **Target**: ≤14 staff.
4.  **Time Slot Validations**:
    -   **Beach Activities**: Slot 1 or 3 ONLY. (Exception: Thursday allows Slot 2).
    -   **Multi-Slot Continuity**: 2-hour activities must have consecutive slots.
5.  **Prohibited Pairs (Same Day)**:
    -   Rifle + Shotgun
    -   Any 2 Canoe activities
    -   Any 2 "Spine" Beach activities (Aqua Trampoline, Water Polo, Greased Watermelon)
6.  **Dependency Chains**:
    -   **Delta → Super Troop**: Delta must generally precede Super Troop.

### 🟡 SOFT Constraints (Avoid if Possible)
1.  **Wet/Dry Patterns**: Avoid Wet → Dry → Wet patterns.
2.  **Activity Spacing**: Avoid strenuous activities (Tower, ODS) back-to-back with Wet activities.
3.  **Clustering**: Try to schedule activities in the same geographic zone on the same day to minimize walking.

---

## ⚡ Scheduling Priorities

1.  **Phase A (Foundation)**:
    -   Friday Reflection (Anchor)
    -   Super Troop (Anchor)
    -   Tuesday HC/DG (Day-locked)
    -   Thursday Sailing (Resource-locked)
    -   3-Hour Activities (Large blocks)

2.  **Phase B (Core Requests)**:
    -   **Top 5 Preferences**: Target 100% satisfaction.
    -   **Top 10 Preferences**: Target minimum 2-3 per troop.

3.  **Phase C (Optimization)**:
    -   Fill gaps with "Fill" activities (Gaga Ball, 9 Square, etc.).
    -   Optimize for AT (Aqua Trampoline) Sharing (+500 pts bonus).

4.  **Phase D (Cleanup)**:
    -   Resolve conflicts.
    -   Eliminate any remaining empty slots.

---

## 📊 Scoring & Metrics
-   **Avg Season Score Target**: >730
-   **Top 5 Satisfaction**: Target 100%
-   **Multi-Slot Success**: 100%
-   **Invalid Schedules**: 0


## 🏗️ Detailed Architecture & Placement Logic

### Top 5 Guarantee System
1.  **Phase 1**: Intelligent constraint-aware swaps
2.  **Phase 2**: Force placement with priority-based removal
3.  **Phase 3**: Emergency placement with conflict resolution

### Commissioner Logic
#### Even Distribution Rule
Troops are distributed 4-3-3 (or similar) across North/Central/South to ensure even workload.
- **North**: Massasoit, Tecumseh, Samoset, Black Hawk, Taskalusa
- **Central**: Powhatan, Red Cloud, Cochise, Joseph, Tamanend
- **South**: Pontiac, Skenandoa, Sequoyah, Roman Nose

#### Activity Day Rotation
| Activity | Comm A | Comm B | Comm C |
|----------|--------|--------|--------|
| **Rifle / Super Troop** | Tue | Wed | Thu |
| **Delta / Sailing** | Mon | Tue | Wed |
| **Archery / Boats** | Wed | Thu | Fri |
| **Tower / ODS** | Thu | Fri | Mon |

Note: **Early Week Bias** (Mon/Tue) explicitly overrides some rotations for priority.

---

## ⚡ Constraint Reference (Expanded)

### Exclusive Areas (Max 1 Troop/Slot)
- **Staffed**: Tower, Rifle, Archery, Handicrafts, Nature, Delta, Super Troop
- **Sailing**: 1.5 slots (2.0 on Thu). Max 1 troop per slot.
- **Exceptions**: Water Polo (2 troops if small), Aqua Trampoline (2 small or 1 large).

### Prohibited Pairs (Same Day)
- `Troop Rifle` + `Troop Shotgun`
- `Delta` + `Tower`/`ODS` (walking distance)
- `Trading Post` + `Free Time` or `Showers`
- Any 2 Boat activities (Canoe/Snorkel/Nature Canoe/Float)
- Any 2 "Spine" Beach activities (AT/WP/Greased Watermelon)

### Staff Safety Caps
- **Global Max**: 16 staff per slot (CRITICAL VIOLATION if exceeded).
- **Target**: ≤14 staff.
- **Beach Max**: 4 staffed activities per slot.

---

## 📊 Scoring & Metrics (The "Why")

### Points Budget (Total ~1000)
1.  **Preference Satisfaction** (~450 pts):
    - Top 1: +5.4 pts
    - Top 5: +2.7 pts
    - Missed Top 5: -3.2 pts
2.  **Bonuses**:
    - **AT Sharing**: +500 pts (Huge efficiency win)
    - **Mutual Excess Day Reduction**: +1000 pts
    - **Cluster Gap Filling**: +500 pts
3.  **Penalties**:
    - **Hard Constraint**: -999 pts (INVALID)
    - **Soft Constraint**: -25 pts
    - **Excess Cluster Day**: -2.0 pts

For specific configuration values (points, capacities, lists), refer to `config/SKULL.json`.
