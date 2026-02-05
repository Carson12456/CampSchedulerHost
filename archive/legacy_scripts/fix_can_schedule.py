#!/usr/bin/env python3
"""Fix _can_schedule method signature to match tests"""

# Read the current file
with open('constrained_scheduler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the end of the class and add the wrapper method
wrapper_code = '''
    
    # Wrapper method to match test signature for _can_schedule
    def _can_schedule_wrapper(self, timeslot, activity, troop, day=None):
        """Wrapper method to match test signature (timeslot, activity, troop)."""
        if day is None:
            day = timeslot.day
        # Store original method reference if not already done
        if not hasattr(self, '_original_can_schedule'):
            self._original_can_schedule = self._can_schedule
            # Rename the original method
            ConstrainedScheduler._can_schedule = self._can_schedule_wrapper
        # Call the actual method with correct parameter order
        return self._original_can_schedule(troop, activity, timeslot, day)
'''

# Add the wrapper method at the end of the class (before the last method)
# Find the position to insert (before the get_stats method)
insert_pos = content.find('    def get_stats(self) -> dict:')
if insert_pos != -1:
    # Insert the wrapper method before get_stats
    new_content = content[:insert_pos] + wrapper_code + content[insert_pos:]
    
    # Write back to file
    with open('constrained_scheduler.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Wrapper method added successfully")
else:
    print("Could not find insertion point")
