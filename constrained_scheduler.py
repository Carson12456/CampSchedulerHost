"""
Backward-compatible scheduler module.

Legacy tests and scripts import ``ConstrainedScheduler`` from the repository root.
The implementation now lives under ``core/``.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Some legacy tests mutate sys.path toward a sibling folder that also has a
# `core/` tree. Only clear already-loaded `core` modules if they resolved to
# the wrong location.
_core_mod = sys.modules.get("core")
if _core_mod is not None:
    loaded_paths = [str(p).lower() for p in getattr(_core_mod, "__path__", [])]
    expected_path = str(_PROJECT_ROOT / "core").lower()
    if not any(p.startswith(expected_path) for p in loaded_paths):
        for module_name in list(sys.modules):
            if module_name == "core" or module_name.startswith("core."):
                del sys.modules[module_name]

from core.constrained_scheduler import ConstrainedScheduler

__all__ = ["ConstrainedScheduler"]
