
# PATCH: Improve Friday Reflection Scheduling
# Add to constrained_scheduler.py in _schedule_friday_reflection method

def _schedule_friday_reflection(self):
    """Ensure ALL troops get Reflection on Friday with enhanced error handling."""
    print("\n--- Scheduling Friday Reflection for ALL troops (ENHANCED) ---")
    reflection = get_activity_by_name("Reflection")
    if not reflection:
        print("  ERROR: Reflection activity not found!")
        return False
    
    friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
    if not friday_slots:
        print("  ERROR: No Friday slots found!")
        return False
    
    success_count = 0
    force_count = 0
    
    for troop in self.troops:
        scheduled = False
        
        # Try each Friday slot in order
        for slot in friday_slots:
            if self.schedule.is_troop_free(slot, troop):
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot}")
                success_count += 1
                scheduled = True
                break
        
        # Force schedule if all slots are busy
        if not scheduled:
            force_slot = friday_slots[-1]  # Use last slot
            self.schedule.add_entry(force_slot, reflection, troop)
            print(f"  [FORCE] {troop.name}: Reflection -> {force_slot} (Overbooked)")
            force_count += 1
    
    print(f"Reflection scheduling complete: {success_count} normal, {force_count} forced")
    return True
