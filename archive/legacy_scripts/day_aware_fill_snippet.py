"""
Test smart day-aware fill by creating a modified version
"""
# New _fill_all_remaining with day-aware sorting

def _fill_all_remaining_DAY_AWARE(self):
    """Fill any empty slots with remaining preferences, then default activities.
    
    Uses day-aware fill: prefers days where troop already has activities (better clustering).
    """
    for troop in self.troops:
        # Get all free slots for this troop
        free_slots = [s for s in self.time_slots if self.schedule.is_troop_free(s, troop)]
        
        if not free_slots:
            continue
        
        # DAY-AWARE FILL: Sort slots by day activity count (prefer busier days)
        def get_day_score(slot):
            # Count activities already on this day for this troop
            return sum(1 for e in self.schedule.entries 
                      if e.troop == troop and e.time_slot.day == slot.day)
        
        # Sort: prefer days with MORE activities (higher score first)
        free_slots.sort(key=get_day_score, reverse=True)
        
        for slot in free_slots:
            if not self.schedule.is_troop_free(slot, troop):
                continue
            
            # First try troop preferences
            scheduled = False
            for pref_name in troop.preferences:
                activity = get_activity_by_name(pref_name)
                if not activity or self._troop_has_activity(troop, activity):
                    continue
                
                if self._can_schedule(troop, activity, slot, slot.day):
                    self.schedule.add_entry(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    scheduled = True
                    break
            
            # If still empty, use default fill priority with relaxed constraints
            if not scheduled:
                for fill_name in self.DEFAULT_FILL_PRIORITY:
                    activity = get_activity_by_name(fill_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue
                    
                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                        self.schedule.add_entry(slot, activity, troop)
                        print(f"  [Day-Aware Fill] {troop.name}: {fill_name} -> {slot}")
                        scheduled = True
                        break
