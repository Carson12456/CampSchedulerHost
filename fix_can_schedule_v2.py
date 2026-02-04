#!/usr/bin/env python3
"""Fix _can_schedule method to support both signatures"""

# Read the current file
with open('constrained_scheduler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the current _can_schedule method definition
import re

# Pattern to match the _can_schedule method definition
pattern = r'def _can_schedule\(self, troop: Troop, activity: Activity, slot: TimeSlot, day: Day, relax_constraints: bool = False, ignore_day_requests: bool = False, allow_top1_beach_slot2: bool = False\) -> bool:'

# New method definition that supports both signatures
new_def = '''def _can_schedule(self, *args, **kwargs):
        """
        Check if activity can be scheduled in this slot.
        Supports both signatures:
        - _can_schedule(troop, activity, slot, day, ...)
        - _can_schedule(timeslot, activity, troop, day=None, ...)
        """
        # Handle the test signature: _can_schedule(timeslot, activity, troop, day=None)
        if len(args) == 3 and 'troop' not in kwargs and 'activity' not in kwargs and 'slot' not in kwargs and 'day' not in kwargs:
            # Test signature detected
            timeslot, activity, troop = args
            day = kwargs.get('day', timeslot.day)
            slot = timeslot
            relax_constraints = kwargs.get('relax_constraints', False)
            ignore_day_requests = kwargs.get('ignore_day_requests', False)
            allow_top1_beach_slot2 = kwargs.get('allow_top1_beach_slot2', False)
        else:
            # Original signature
            if len(args) >= 4:
                troop, activity, slot, day = args[:4]
                relax_constraints = kwargs.get('relax_constraints', False)
                ignore_day_requests = kwargs.get('ignore_day_requests', False)
                allow_top1_beach_slot2 = kwargs.get('allow_top1_beach_slot2', False)
            else:
                raise ValueError("Insufficient arguments for _can_schedule")
        
        # Original method body starts here
        if not self.schedule.is_troop_free(slot, troop):
            return False'''

# Replace the method definition
new_content = re.sub(pattern, new_def, content)

if new_content != content:
    # Write back to file
    with open('constrained_scheduler.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Method signature fixed successfully")
else:
    print("Pattern not found - method signature might be different")
