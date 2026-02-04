import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

print("Testing imports...")
try:
    import models
    print("✓ models")
    import activities
    print("✓ activities")
    import constrained_scheduler
    print("✓ constrained_scheduler")
    import gui_web
    print("✓ gui_web")
    print("\nSystem integrity verified.")
except Exception as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    sys.exit(1)
