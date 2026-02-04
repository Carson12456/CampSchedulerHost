# Summer Camp Scheduler

A comprehensive scheduling system for summer camp activities with constraint validation, preference optimization, and staff workload balancing.

## Features

- ✅ **Smart Scheduling**: Constraint-based scheduling respecting camp rules
- ✅ **Preference Optimization**: Maximizes troop satisfaction for top preferences
- ✅ **Staff Clustering**: Optimizes staff workload and activity clustering
- ✅ **Web GUI**: Interactive schedule viewing and commissioner dashboards
- ✅ **Multiple Exports**: CSV, Excel, and PDF schedule exports
- ✅ **Quality Reports**: Automated schedule analysis and metrics
- ✅ **Automated Testing**: Constraint validation and capacity testing

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Troop Data
Use `TC_WEEK_TEMPLATE.md` as a guide to create week files:
- `tc_week1_troops.json` ✓ (included)
- `tc_week4_troops.json` ✓ (included)
- `tc_week7_troops.json` ✓ (included)

### 3. Validate Data
```bash
python validate_troop_data.py
```

### 4. Generate Schedule
```bash
python generate_schedule.py tc_week1_troops.json
```

### 5. View in Web GUI
```bash
python gui_web.py
```
Open browser to: http://localhost:5000

## Project Structure

```
summer-camp-scheduler/
├── Core Modules
│   ├── models.py                  # Data models (Troop, Activity, Schedule)
│   ├── activities.py              # Activity definitions  
│   ├── constrained_scheduler.py  # Main scheduling logic
│   └── io_handler.py              # File I/O utilities
│
├── Web Interface
│   ├── gui_web.py                 # Flask web application
│   └── templates/
│       └── index.html             # Schedule viewer
│
├── Utilities
│   ├── generate_schedule.py       # CLI schedule generator
│   ├── export_schedule.py         # Export to CSV/Excel/PDF
│   ├── generate_quality_report.py # Quality analysis
│   ├── validate_troop_data.py     # Data validation
│   └── migrate_activity_names.py  # Data migration tool
│
├── Testing
│   ├── tests/
│   │   ├── test_constraints.py    # Constraint validation tests
│   │   ├── test_capacity.py       # Capacity limit tests
│   │   ├── test_preferences.py    # Preference & staff tests
│       └── run_all_tests.py       # Master test runner
│
├── Data
│   ├── tc_week*.json              # Troop preference files
│   ├── voyageur_week*.json        # Voyageur week files
│   └── schedules/                 # Generated schedules (JSON)
│
├── Output
│   ├── exports/                   # Exported schedules
│   └── reports/                   # Quality reports
│
└── Archive
    ├── debug/                     # Debug scripts
    └── analysis/                  # Analysis scripts
```

## Usage

### Generate a Schedule
```bash
python generate_schedule.py tc_week7_troops.json
```

### Export Schedules
```bash
# Export to all formats (CSV, Excel, PDF)
python export_schedule.py

# Export specific formats
python export_schedule.py csv excel
```

### Run Tests
```bash
cd tests
python run_all_tests.py
```

### Generate Quality Report
```bash
python generate_quality_report.py
```

## Scheduling Constraints

The scheduler enforces these rules:

1. **Beach Activities**: Slots 1 or 3 (slot 2 allowed on Thursday only)
2. **Accuracy Limit**: Max 1 accuracy activity (Rifle/Shotgun/Archery) per day
3. **Friday Reflection**: Required for all troops
4. **Wet → Tower/ODS**: Tower/ODS cannot immediately follow wet activities
5. **Delta → Super Troop**: Delta must precede Super Troop for each troop
6. **Canoe Capacity**: Max 26 people per slot (13 canoes)
7. **Beach Staff**: Max 12 staff per slot
8. **Exclusive Areas**: Tower, Rifle, ODS, Sailing, Delta, Super Troop

## Web GUI Features

- 📋 **Troop Schedules**: Individual troop daily schedules
- 🏖️ **Area Boards**: Beach, Boats, Handicrafts, etc.
- 👥 **Commissioner Schedules**: Activity assignments by commissioner
- 📊 **Staff Requirements**: Workload tracking per time slot
- 🔄 **Week Selector**: Switch between different camp weeks

## Documentation

- `ITERATION_3_PLANNING.md` - Feature planning and requirements
- `SCHEDULING_PROCESS.md` - How the scheduler works
- `TC_WEEK_TEMPLATE.md` - Template for creating new week data
- `archive/README.md` - Archived files documentation

## Contributing

When adding new features:
1. Update tests in `tests/`
2. Run `python tests/run_all_tests.py`
3. Update this README
4. Generate quality report to verify improvements

## License

Internal use for Camp Ten Chiefs scheduling.
