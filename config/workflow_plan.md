# Workflow Plan for GPT 5.3: CampScheduler Polish

Based on the analysis of [BRAIN.md](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/BRAIN.md), [SKULL.json](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/SKULL.json), [regression_checker.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/utils/regression_checker.py), and [constrained_scheduler.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/core/constrained_scheduler.py), here is a refined workflow plan.

## 🧐 Analysis of Your Plan
**Your assumption:** *Brain -> Regression Checker -> SKULL Update -> SKULL Primary -> Analyze -> Improve.*

**My Verdict:** This is a **highly effective** and logical sequence. Use of [SKULL.json](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/SKULL.json) as the "single source of truth" is the most critical step because currently, [constrained_scheduler.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/core/constrained_scheduler.py) contains **significantly duplicate hardcoded logic** (e.g., `COMMISSIONER_DELTA_DAYS`, `AREA_PAIRS`, `WET_ACTIVITIES` are defined in the Python class despite existing in concepts).

If you skip the "SKULL Primary" step, any "Improvement" you make to the config will be ignored by the hardcoded Python lists, checking will fail, and the model will get confused. **Strict enforcement of Configuration-Driven Development is the key to success here.**

---

## 🚀 The Protocol (Numbered List)

### Phase 1: Preparation & Standardization
1.  **AI-Friendly Optimization & Cleanup**:
    *   **Action:** Remove "trash files" (temp scripts, unused data) to reduce noise.
    *   **Action:** Update `.cursorrules` or documentation to make the codebase more "AI friendly" (explicit types, clear boundaries).
2.  **Deep Scan & BRAIN Update**:
    *   **Action:** Scan the entire codebase (especially [constrained_scheduler.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/core/constrained_scheduler.py) and [activities.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/core/activities.py)) for *any* logic, constraints, or preference rules not currently in [BRAIN.md](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/BRAIN.md).
    *   *Goal:* Ensure [BRAIN.md](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/BRAIN.md) is the absolute, undisputed encyclopedia of the project before we align the config.
3.  **Sync BRAIN & SKULL**:
    *   Compare [BRAIN.md](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/BRAIN.md) (text spec) with [SKULL.json](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/SKULL.json) (config) to ensure they match perfectly.
    *   *Action:* Resolve any discrepancies (e.g., is "Sailing" definitely 1.5 slots in both? Are all "Prohibited Pairs" in both?).
4.  **Audit Regression Checker**:
    *   Verify [regression_checker.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/utils/regression_checker.py) provides a 100% test coverage of the "Laws of Physics" in [BRAIN.md](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/BRAIN.md).
    *   *critical check:* Does it catch *every* hard constraint? (e.g., "History Center & Disc Golf on Tuesday"). If not, add the check.
    *   *Refactor:* Stop the checker from re-defining lists like `WET_ACTIVITIES`. Make it import them from a shared model/config so it shares the same definition as the Scheduler.
5.  **SKULL Expansion (The Great Migration)**:
    *   Identify all hardcoded lists in [constrained_scheduler.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/core/constrained_scheduler.py) (lines 44-196) such as `DEFAULT_FILL_PRIORITY`, `BEACH_ACTIVITIES`, `AREA_PAIRS`, `COMMISSIONER_*_DAYS`.
    *   Move these definitions into [SKULL.json](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/SKULL.json) if they aren't there already.
6.  **Refactor & Break Down Constrained Scheduler**:
    *   **Action:** Deconstruct the massive [constrained_scheduler.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/core/constrained_scheduler.py) into smaller, logical components or distinct phases if possible.
    *   **Action:** Delete hardcoded defaults and strictly load them from [SKULL.json](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/SKULL.json).
    *   *Goal:* Changing a value in [SKULL.json](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/config/SKULL.json) must immediately change the Scheduler's behavior without touching Python code.

### Phase 2: Diagnosis
7.  **Run Season Baseline**:
    *   Run the (now correct) [regression_checker.py](file:///c:/Users/Carson/OneDrive%20-%20Minnesota%20State/Desktop/Projects/CampScheduler/summer-camp-scheduler/utils/regression_checker.py) on all 10 weeks of data (`tc_week1`... `voyageur_week3`).
    *   Generate a "Season Health Report".
8.  **Identify Weak Points**:
    *   Analyze the report for "Struggling Goals".
    *   *Look for:* Specific troops with low satisfaction, weeks with high "Cluster Gaps", or persistent "Soft Constraint" violations.

### Phase 3: Progressive Optimization
9.  **Optimize Commissioner Rotation**:
    *   Analyze: Area specific rotation (North=Monday, etc.).
    *   *Action:* Tune the "Foundation" phase to adhere to these days strictly, but verify it doesn't kill Top 5 scores.
10. **Enhance Activity Pairing**:
    *   Implementation: Improve `Phase A` and `Phase B` to aggressively pair `Delta + Sailing` and `Rifle + Super Troop`.
    *   *Metric:* Tracking "Promoted Pairs" count in the regression checker.
11. **Solver "Gap" Filling**:
    *   Address the "Efficiency" score. Improve the logic that fills empty slots (Sand/Pebbles) to prefer "Cluster-aligned" activities rather than random fills.
    *   *Example:* If a troop is at Tower for a slot, fill their empty slot with something nearby or neutral, not something that forces a walk across camp (like Beach).
12. **Final Polish**:
    *   Run specific checks for "Commissioner Balance" (are staff overworked on Mondays vs Fridays?).
    *   Code cleanup and documentation.

---

## 💡 Additional Thoughts
*   **Voyageur Mode**: You have a `voyageur_mode` flag in the code. Ensure the "SKULL Supremacy" step allows for "Voyageur Overrides" in the JSON (e.g., `commissioner_days_voyageur` vs `commissioner_days_standard`). Code currently seems to have some manual overrides.
*   **Test Data**: Ensure `data/schedules` contains the "current best" json files before starting the "Analyze" step, so you are comparing against the real current state.
