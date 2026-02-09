
import inspect
import sys
import os
sys.path.append(os.getcwd())

from core.constrained_scheduler import ConstrainedScheduler

method = getattr(ConstrainedScheduler, "_comprehensive_smart_swaps", None)
if method:
    lines = inspect.getsourcelines(method)
    print(f"Found _comprehensive_smart_swaps at line {lines[1]}")
else:
    print("Method _comprehensive_smart_swaps not found in ConstrainedScheduler")

method2 = getattr(ConstrainedScheduler, "_consolidate_staff_areas", None)
if method2:
    lines = inspect.getsourcelines(method2)
    print(f"Found _consolidate_staff_areas at line {lines[1]}")
else:
    print("Method _consolidate_staff_areas not found")
