"""
Backward-compatible models module.

Legacy tests and scripts import model types and constants from the repository root.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

_core_mod = sys.modules.get("core")
if _core_mod is not None:
    loaded_paths = [str(p).lower() for p in getattr(_core_mod, "__path__", [])]
    expected_path = str(_PROJECT_ROOT / "core").lower()
    if not any(p.startswith(expected_path) for p in loaded_paths):
        for module_name in list(sys.modules):
            if module_name == "core" or module_name.startswith("core."):
                del sys.modules[module_name]

from core.models import (
    Activity,
    Day,
    Schedule,
    ScheduleEntry,
    TimeSlot,
    Troop,
    Zone,
    generate_time_slots,
)
from core.scheduler import config_loader

# Compatibility constants used by older tests/helpers.
EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()
BEACH_STAFF_ACTIVITIES = {
    name
    for name in config_loader.get_beach_staff_activities()
}

__all__ = [
    "Activity",
    "Troop",
    "Schedule",
    "ScheduleEntry",
    "TimeSlot",
    "Day",
    "Zone",
    "generate_time_slots",
    "EXCLUSIVE_AREAS",
    "BEACH_STAFF_ACTIVITIES",
]
