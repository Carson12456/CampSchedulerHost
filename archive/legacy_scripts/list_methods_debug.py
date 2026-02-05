
import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'summer-camp-scheduler'))

try:
    from constrained_scheduler import ConstrainedScheduler
    print("Class found.")
    methods = [func for func in dir(ConstrainedScheduler) if callable(getattr(ConstrainedScheduler, func))]
    print("Methods:")
    for m in sorted(methods):
        print(f" - {m}")
        
    if '_can_schedule' in methods:
        print("\n_can_schedule FOUND")
    else:
        print("\n_can_schedule NOT FOUND")

except Exception as e:
    print(f"Error: {e}")
