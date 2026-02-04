"""
Greedy scheduler algorithm for camp scheduling.
"""
from models import Activity, Troop, Schedule, TimeSlot, generate_time_slots
from activities import get_all_activities, get_activity_by_name


class GreedyScheduler:
    """
    Greedy scheduling algorithm that assigns activities by preference rank.
    
    Algorithm:
    1. For each troop, iterate through their preferences in order
    2. For each preferred activity, find an available time slot
    3. Assign the activity to that slot
    4. Continue until all slots are filled or preferences exhausted
    """
    
    def __init__(self, troops: list[Troop], activities: list[Activity] = None):
        self.troops = troops
        self.activities = activities or get_all_activities()
        self.schedule = Schedule()
        self.time_slots = generate_time_slots()
    
    def schedule_all(self) -> Schedule:
        """Run the greedy scheduling algorithm."""
        # Phase 1: Assign top 5 preferences (must get)
        self._assign_preferences(self.troops, range(0, 5), "Top 5")
        
        # Phase 2: Assign preferences 6-10 (should get)
        self._assign_preferences(self.troops, range(5, 10), "Top 6-10")
        
        # Phase 3: Assign preferences 11-20 (best effort)
        self._assign_preferences(self.troops, range(10, 20), "Top 11-20")
        
        # Phase 4: Fill remaining slots with any available activity
        self._fill_remaining_slots()
        
        return self.schedule
    
    def _assign_preferences(self, troops: list[Troop], pref_range: range, phase_name: str):
        """Assign activities from a preference range to troops."""
        print(f"\n--- Scheduling {phase_name} ---")
        
        for pref_index in pref_range:
            for troop in troops:
                if pref_index >= len(troop.preferences):
                    continue
                
                activity_name = troop.preferences[pref_index]
                activity = get_activity_by_name(activity_name)
                
                if not activity:
                    print(f"  Warning: Activity '{activity_name}' not found for {troop.name}")
                    continue
                
                # Check if troop already has this activity
                if self._troop_has_activity(troop, activity):
                    continue
                
                # Find an available slot
                slot = self._find_available_slot(troop, activity)
                
                if slot:
                    self.schedule.add_entry(slot, activity, troop)
                    print(f"  {troop.name}: {activity_name} -> {slot}")
                else:
                    print(f"  {troop.name}: Could not schedule {activity_name}")
    
    def _troop_has_activity(self, troop: Troop, activity: Activity) -> bool:
        """Check if a troop already has an activity scheduled."""
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.activity.name == activity.name:
                return True
        return False
    
    def _find_available_slot(self, troop: Troop, activity: Activity) -> TimeSlot | None:
        """Find an available time slot for a troop and activity."""
        slots_needed = int(activity.slots) if activity.slots == int(activity.slots) else 2
        
        # Cache troop's current schedule for performance
        troop_schedule = self.schedule.get_troop_schedule(troop)
        occupied_slots = {(e.time_slot.day, e.time_slot.slot_number) for e in troop_schedule}
        
        for i, slot in enumerate(self.time_slots):
            slot_key = (slot.day, slot.slot_number)
            
            # Quick check: if troop already occupied, skip
            if slot_key in occupied_slots:
                continue
            
            # Check if activity is available (not booked, no conflicts)
            if not self.schedule.is_activity_available(slot, activity, troop):
                continue
            
            # For multi-slot activities, check consecutive slots
            if slots_needed > 1:
                if not self._check_consecutive_slots(troop, activity, i, slots_needed):
                    continue
            
            # All checks passed
            return slot
        
        return None
    
    def _check_consecutive_slots(self, troop: Troop, activity: Activity, 
                                  start_index: int, slots_needed: int) -> bool:
        """Check if consecutive slots are available for multi-hour activities."""
        if start_index + slots_needed > len(self.time_slots):
            return False
        
        # Verify slots are on the same day
        start_slot = self.time_slots[start_index]
        for offset in range(1, slots_needed):
            next_slot = self.time_slots[start_index + offset]
            if next_slot.day != start_slot.day:
                return False
            if not self.schedule.is_troop_free(next_slot, troop):
                return False
            if not self.schedule.is_activity_available(next_slot, activity):
                return False
        
        return True
    
    def _fill_remaining_slots(self):
        """Fill any remaining empty slots with available activities."""
        print("\n--- Filling remaining slots ---")
        
        for troop in self.troops:
            for slot in self.time_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    continue
                
                # Find any available activity
                for activity in self.activities:
                    if activity.slots > 1:  # Skip multi-hour for fill
                        continue
                    
                    if self._troop_has_activity(troop, activity):
                        continue
                    
                    if self.schedule.is_activity_available(slot, activity):
                        self.schedule.add_entry(slot, activity, troop)
                        print(f"  {troop.name}: {activity.name} -> {slot} (fill)")
                        break
    
    def get_stats(self) -> dict:
        """Get scheduling statistics."""
        stats = {
            'total_entries': len(self.schedule.entries),
            'troops': {}
        }
        
        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)
            top5_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 5)
            top10_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 10)
            
            stats['troops'][troop.name] = {
                'total_scheduled': len(entries),
                'top5_achieved': top5_count,
                'top10_achieved': top10_count
            }
        
        return stats
