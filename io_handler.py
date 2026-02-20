"""
Backward-compatible I/O module.

Legacy tests and scripts import I/O helpers from the repository root.
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

from core.io_handler import load_schedule_from_json, load_troops_from_json, save_schedule_to_json

__all__ = ["load_troops_from_json", "save_schedule_to_json", "load_schedule_from_json"]
