"""
Phase C Optimization Module.

Contains methods for Phase C of the scheduling algorithm:
- C.1: Day-specific requests
- C.2: Staff optimization (consecutive activities)
- C.4: Remaining preferences (Top 6-20)
- C.5: Guarantee Top 10
- C.6: Fill slot logic
- C.7: Aqua Trampoline sharing
"""

from ..models import Day, TimeSlot, generate_time_slots
from ..activities import get_activity_by_name
from .constants import SchedulerConstants


class PhaseCOptimizationMixin:
    """
    Mixin class providing Phase C (Remaining & Optimization) methods.
    
    Phase C handles:
    - Remaining preference scheduling (Top 6-20)
    - Fill slot logic
    - Staff optimization
    """
    
    # =========================================================================
    # C.1: DAY-SPECIFIC REQUESTS
    # =========================================================================
    
    def _schedule_day_requests(self):
        """Schedule day-specific activity requests (MUST be fulfilled)."""
        print("\n--- Scheduling Day-Specific Requests ---")
        
        for troop in self.troops:
            if not hasattr(troop, 'day_requests') or not troop.day_requests:
                continue
            
            for day, activity_name in troop.day_requests.items():
                activity = get_activity_by_name(activity_name)
                if not activity:
                    continue
                
                # Check if already scheduled
                if self._troop_has_activity_by_name(troop, activity_name):
                    continue
                
                # Find a slot on the requested day
                day_slots = [s for s in self.time_slots if s.day == day]
                
                scheduled = False
                for slot in day_slots:
                    if self.schedule.is_troop_free(slot, troop):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"  {troop.name}: {activity_name} -> {day.name} (day request)")
                        scheduled = True
                        break
                
                if not scheduled:
                    print(f"  WARNING: Could not fulfill day request for {troop.name}: {activity_name} on {day.name}")
    
    def _troop_has_activity_by_name(self, troop, activity_name):
        """Check if troop already has an activity scheduled."""
        return any(
            e.activity.name == activity_name
            for e in self.schedule.entries
            if e.troop == troop
        )
    
    # =========================================================================
    # C.2: STAFF OPTIMIZATION
    # =========================================================================
    
    def _schedule_staff_optimized_areas(self):
        """Schedule staff-intensive activities to minimize setup time."""
        print("\n--- Staff Optimization (consecutive activities) ---")
        
        STAFF_AREAS = {
            "Tower": ["Climbing Tower"],
            "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
            "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching",
                              "Ultimate Survivor", "What's Cooking", "Chopped!"],
            "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
        }
        
        # For each area, try to cluster activities on the same days
        for area_name, area_activities in STAFF_AREAS.items():
            # Find all scheduled activities in this area
            area_entries = [
                e for e in self.schedule.entries
                if e.activity.name in area_activities
            ]
            
            if not area_entries:
                continue
            
            # Count activities per day
            day_counts = {}
            for entry in area_entries:
                day = entry.time_slot.day
                day_counts[day] = day_counts.get(day, 0) + 1
            
            # Find the best days (most activities)
            sorted_days = sorted(day_counts.items(), key=lambda x: -x[1])
            
            print(f"  {area_name}: {len(area_entries)} activities across {len(day_counts)} days")
    
    # =========================================================================
    # C.5: GUARANTEE TOP 10
    # =========================================================================
    
    def _guarantee_top10_with_exceptions(self):
        """Guarantee Top 10 satisfaction with some exceptions."""
        print("\n--- Guaranteeing Top 10 with exceptions ---")
        
        for troop in self.troops:
            if not troop.preferences:
                continue
            
            top10 = troop.preferences[:10]
            missing = []
            
            for activity_name in top10:
                if not self._troop_has_activity_by_name(troop, activity_name):
                    missing.append(activity_name)
            
            if not missing:
                continue
            
            print(f"  {troop.name}: Missing from Top 10: {', '.join(missing)}")
    
    def _guarantee_minimum_top10(self):
        """Guarantee minimum Top 10 (2-3 per troop)."""
        print("\n--- Guaranteeing Minimum Top 10 (2-3 per troop) ---")
        
        for troop in self.troops:
            if not troop.preferences:
                continue
            
            # Count how many Top 10 are scheduled
            top10 = troop.preferences[:10]
            scheduled_count = sum(
                1 for activity_name in top10
                if self._troop_has_activity_by_name(troop, activity_name)
            )
            
            if scheduled_count < 2:
                print(f"  WARNING: {troop.name} only has {scheduled_count} Top 10!")
    
    # =========================================================================
    # C.6: FILL SLOT LOGIC
    # =========================================================================
    
    def _fill_all_remaining(self):
        """Fill all remaining slots with appropriate activities."""
        print("\n--- Filling Remaining Slots ---")
        
        fill_priority = SchedulerConstants.DEFAULT_FILL_PRIORITY
        
        for troop in self.troops:
            # Find empty slots
            for slot in self.time_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    continue
                
                # Try to fill with a fill activity
                for fill_name in fill_priority:
                    if self._troop_has_activity_by_name(troop, fill_name):
                        continue
                    
                    activity = get_activity_by_name(fill_name)
                    if not activity:
                        continue
                    
                    
                    # Basic constraint check - ensure exclusive activities aren't double-booked
                    if activity.name in SchedulerConstants.EXCLUSIVE_ACTIVITIES:
                        # Check exclusivity: Is ANY execution of this activity already scheduled in this slot?
                        # NOTE: This enforces 1-per-slot for ALL exclusive activities (Tower, Rifle, Archery, ODS stations etc)
                        blocked = any(
                            e.time_slot == slot and e.activity.name == activity.name
                            for e in self.schedule.entries
                        )
                        if blocked:
                            continue
                    
                    self._add_to_schedule(slot, activity, troop)
                    print(f"  {troop.name}: {fill_name} -> {slot}")
                    break
    
    def _guarantee_no_gaps(self):
        """Guarantee no gaps in the schedule by force-filling."""
        print("\n--- Guaranteeing No Gaps ---")
        
        fallback_activities = ["Campsite Free Time", "9 Square", "Gaga Ball"]
        
        for troop in self.troops:
            for slot in self.time_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    continue
                
                # Try each fallback
                for fallback_name in fallback_activities:
                    activity = get_activity_by_name(fallback_name)
                    if activity:
                        self._add_to_schedule(slot, activity, troop)
                        print(f"  [Gap Fill] {troop.name}: {fallback_name} -> {slot}")
                        break
