"""
Scheduler Utilities Module.

Contains helper methods for common scheduling operations:
- Adding/removing schedule entries
- Staff load tracking
- Slot finding and validation
- Swap helpers
"""

from ..models import Activity, Troop, TimeSlot, Day, generate_time_slots
from ..activities import get_activity_by_name
from .constants import SchedulerConstants


class UtilityMixin:
    """
    Mixin class providing utility methods for the scheduler.
    
    These are low-level helper methods used by all phases of the scheduling algorithm.
    """
    
    # =========================================================================
    # SCHEDULE MODIFICATION
    # =========================================================================
    
    def _add_to_schedule(self, slot: TimeSlot, activity: Activity, troop: Troop):
        """
        Wrapper to add an entry to the schedule and update staff load tracking.
        Relies on Schedule.add_entry() for atomic multi-slot scheduling and validation.
        """
        # 1. Try to add via Schedule model (handles multi-slot logic and atomic check)
        if not self.schedule.add_entry(slot, activity, troop):
            return
        
        # 2. Update staff load for ALL slots occupied
        # Calculate derived slots strictly matching add_entry logic
        effective_slots = self.schedule._get_effective_slots(activity, troop)
        slots_needed = int(effective_slots + 0.5)
        
        all_slots = generate_time_slots()
        try:
            start_idx = all_slots.index(slot)
            for offset in range(slots_needed):
                if start_idx + offset >= len(all_slots):
                    break
                
                next_slot = all_slots[start_idx + offset]
                
                # add_entry logic stops at day boundary
                if next_slot.day != slot.day:
                    break
                
                # Update staff load
                self._update_staff_load(next_slot, activity.name, delta=1)
                
                # Update total staff tracking
                if activity.name in SchedulerConstants.ACTIVITY_STAFF_COUNT:
                    self.total_staff_by_slot[next_slot] += SchedulerConstants.ACTIVITY_STAFF_COUNT[activity.name]
        except ValueError:
            pass
    
    def _remove_from_schedule(self, entry):
        """
        Remove an entry from the schedule and update staff tracking.
        
        Args:
            entry: The ScheduleEntry to remove
        """
        if entry not in self.schedule.entries:
            return
        
        # Update staff load before removal
        activity_name = entry.activity.name
        slot = entry.time_slot
        
        # Calculate slots this entry occupied
        effective_slots = self.schedule._get_effective_slots(entry.activity, entry.troop)
        slots_needed = int(effective_slots + 0.5)
        
        all_slots = generate_time_slots()
        try:
            start_idx = all_slots.index(slot)
            for offset in range(slots_needed):
                if start_idx + offset >= len(all_slots):
                    break
                
                next_slot = all_slots[start_idx + offset]
                if next_slot.day != slot.day:
                    break
                
                # Update staff load
                self._update_staff_load(next_slot, activity_name, delta=-1)
                
                # Update total staff tracking
                if activity_name in SchedulerConstants.ACTIVITY_STAFF_COUNT:
                    self.total_staff_by_slot[next_slot] -= SchedulerConstants.ACTIVITY_STAFF_COUNT[activity_name]
        except ValueError:
            pass
        
        # Remove the entry
        self.schedule.entries.remove(entry)
    
    # =========================================================================
    # STAFF LOAD TRACKING
    # =========================================================================
    
    def _update_staff_load(self, slot: TimeSlot, activity_name: str, delta: int = 1):
        """
        Update staff load tracking for a slot.
        
        Args:
            slot: The time slot
            activity_name: Name of the activity
            delta: +1 for adding, -1 for removing
        """
        zone = SchedulerConstants.STAFF_ZONE_MAP.get(activity_name)
        if zone:
            self.staff_load_by_slot[slot][zone] += delta
    
    def _get_staff_load_for_slot(self, slot: TimeSlot) -> int:
        """Get total staff count for a slot across all zones."""
        return self.total_staff_by_slot.get(slot, 0)
    
    # =========================================================================
    # CONSTRAINT CHECKING
    # =========================================================================
    
    def _can_schedule(self, slot: TimeSlot, activity, troop) -> bool:
        """
        Check if an activity can be scheduled for a troop in a given slot.
        
        This is the central constraint checking method that validates:
        - Beach slot rules (slots 1/3 only, except Thursday)
        - Exclusive area conflicts
        - Multi-slot availability
        - Wet/dry activity sequencing
        
        Args:
            slot: The time slot to check
            activity: The activity to schedule
            troop: The troop to schedule for
            
        Returns:
            True if the activity can be scheduled, False otherwise
        """
        activity_name = activity.name
        
        # 1. Beach slot check - beach activities only in slots 1 or 3 (except Thursday)
        if activity_name in SchedulerConstants.BEACH_SLOT_ACTIVITIES:
            if slot.day != Day.THURSDAY and slot.slot_number == 2:
                # Allow slot 2 for Top 5 beach preferences
                priority = troop.get_priority(activity_name)
                if priority is None or priority >= 5:
                    return False
        
        # 2. Exclusive area check - only 1 troop per exclusive activity per slot
        if activity_name in SchedulerConstants.EXCLUSIVE_ACTIVITIES:
            for entry in self.schedule.entries:
                if (entry.time_slot == slot and 
                    entry.activity.name == activity_name and 
                    entry.troop != troop):
                    return False
        
        # 3. Multi-slot availability check
        if hasattr(activity, 'duration') and activity.duration > 1:
            all_slots = generate_time_slots()
            try:
                start_idx = all_slots.index(slot)
                slots_needed = int(activity.duration + 0.5)
                
                for offset in range(slots_needed):
                    if start_idx + offset >= len(all_slots):
                        return False
                    
                    next_slot = all_slots[start_idx + offset]
                    if next_slot.day != slot.day:
                        return False  # Can't span days
                    
                    if not self.schedule.is_troop_free(next_slot, troop):
                        return False
            except ValueError:
                return False
        
        # 4. Same-activity-per-day check (prevent double-scheduling)
        day_activities = self._get_troop_activities_on_day(troop, slot.day)
        if activity_name in day_activities:
            return False
        
        # 5. Staff capacity check (optional - can be overridden)
        if hasattr(self, 'staff_load_by_slot'):
            zone = SchedulerConstants.STAFF_ZONE_MAP.get(activity_name)
            if zone:
                current_load = self.staff_load_by_slot.get(slot, {}).get(zone, 0)
                max_load = SchedulerConstants.MAX_STAFF_PER_ZONE.get(zone, 5)
                if current_load >= max_load:
                    return False
        
        return True
    
    # =========================================================================
    # SLOT FINDING
    # =========================================================================
    
    def _find_valid_slots_for_activity(self, activity: Activity, troop: Troop, 
                                        exclude_days: list = None) -> list:
        """
        Find all valid slots where an activity can be scheduled for a troop.
        
        Args:
            activity: The activity to schedule
            troop: The troop to schedule for
            exclude_days: Days to exclude from consideration
            
        Returns:
            List of valid TimeSlot objects
        """
        exclude_days = exclude_days or []
        valid_slots = []
        
        for slot in self.time_slots:
            if slot.day in exclude_days:
                continue
            
            # Check if troop is free
            if not self.schedule.is_troop_free(slot, troop):
                continue
            
            # Check if we can schedule here
            if self._can_schedule(slot, activity, troop):
                valid_slots.append(slot)
        
        return valid_slots
    
    def _get_troop_activity_slot(self, troop: Troop, activity_name: str) -> TimeSlot:
        """
        Get the slot where a troop has a specific activity scheduled.
        
        Returns:
            The TimeSlot, or None if not found
        """
        for entry in self.schedule.entries:
            if entry.troop == troop and entry.activity.name == activity_name:
                return entry.time_slot
        return None
    
    def _get_troop_activities_on_day(self, troop: Troop, day: Day) -> list:
        """
        Get all activities scheduled for a troop on a specific day.
        
        Returns:
            List of activity names
        """
        activities = []
        for entry in self.schedule.entries:
            if entry.troop == troop and entry.time_slot.day == day:
                activities.append(entry.activity.name)
        return activities
    
    # =========================================================================
    # REFLECTION HELPERS
    # =========================================================================
    
    def _check_and_schedule_reflection(self, troop):
        """
        SMART REFLECTION: Check if troop has only 1 Friday slot remaining.
        If so, immediately schedule Reflection in that slot.
        
        Call this after ANY Friday slot is filled for a troop.
        Returns True if Reflection was scheduled, False otherwise.
        """
        # Check if troop already has Reflection
        has_reflection = any(
            e.activity.name == "Reflection"
            for e in self.schedule.entries
            if e.troop == troop
        )
        
        if has_reflection:
            return False  # Already have Reflection
        
        # Get Friday slots
        if self._friday_slots is None:
            self._friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
        
        # Count free Friday slots
        free_friday = [s for s in self._friday_slots if self.schedule.is_troop_free(s, troop)]
        
        if len(free_friday) == 1:
            # Only 1 slot left - schedule Reflection NOW
            reflection = get_activity_by_name("Reflection")
            if reflection:
                slot = free_friday[0]
                self._add_to_schedule(slot, reflection, troop)
                print(f"  [Smart Reflection] {troop.name}: Reflection -> {slot} (triggered: 1 slot left)")
                return True
        
        return False
    
    # =========================================================================
    # CONTINUATION HELPERS (for multi-slot activities)
    # =========================================================================
    
    def _remove_continuations_helper(self, entry):
        """
        Helper method to remove continuation entries for multi-slot activities.
        Returns a list of removed continuation entries.
        """
        removed = []
        activity = entry.activity
        troop = entry.troop
        start_slot = entry.time_slot
        
        # Find all continuation entries for this activity+troop
        # They will be in consecutive slots on the same day
        all_slots = generate_time_slots()
        try:
            start_idx = all_slots.index(start_slot)
        except ValueError:
            return removed
        
        # Look for continuation entries
        for offset in range(1, 4):  # Max 3 continuation slots
            if start_idx + offset >= len(all_slots):
                break
            
            next_slot = all_slots[start_idx + offset]
            if next_slot.day != start_slot.day:
                break
            
            # Find and remove continuation entry
            for e in list(self.schedule.entries):
                if (e.troop == troop and 
                    e.activity.name == activity.name and 
                    e.time_slot == next_slot):
                    self.schedule.entries.remove(e)
                    removed.append(e)
                    break
        
        return removed
    
    # =========================================================================
    # TROOP TRACKING HELPERS
    # =========================================================================
    
    def _get_troop_day_activity_counts(self, troop) -> dict:
        """
        Count how many activities a troop has scheduled per day.
        
        Returns:
            Dict mapping Day -> count of activities
        """
        counts = {}
        for entry in self.schedule.entries:
            if entry.troop == troop:
                day = entry.time_slot.day
                counts[day] = counts.get(day, 0) + 1
        return counts
    
    def _troop_has_activity(self, troop, activity_name: str) -> bool:
        """Check if a troop already has a specific activity scheduled."""
        return any(
            e.activity.name == activity_name
            for e in self.schedule.entries
            if e.troop == troop
        )
    
    def _get_troop_scheduled_preferences(self, troop, max_rank: int = 20) -> list:
        """
        Get list of preference activities that are already scheduled for a troop.
        
        Args:
            troop: The troop to check
            max_rank: Maximum preference rank to check (default 20)
            
        Returns:
            List of (rank, activity_name) tuples for scheduled preferences
        """
        scheduled = []
        if not troop.preferences:
            return scheduled
        
        for rank, activity_name in enumerate(troop.preferences[:max_rank]):
            if self._troop_has_activity(troop, activity_name):
                scheduled.append((rank, activity_name))
        
        return scheduled
    
    def _get_troop_missing_preferences(self, troop, max_rank: int = 5) -> list:
        """
        Get list of preference activities NOT yet scheduled for a troop.
        
        Args:
            troop: The troop to check
            max_rank: Maximum preference rank to check (default 5 for Top 5)
            
        Returns:
            List of (rank, activity_name) tuples for missing preferences
        """
        missing = []
        if not troop.preferences:
            return missing
        
        for rank, activity_name in enumerate(troop.preferences[:max_rank]):
            if not self._troop_has_activity(troop, activity_name):
                missing.append((rank, activity_name))
        
        return missing
    
    # =========================================================================
    # SCORING HELPERS
    # =========================================================================
    
    def _get_slot_staff_score(self, slot: TimeSlot, activity_name: str) -> int:
        """
        Calculate staff load score for a slot.
        Lower is better (less staff competition).
        """
        zone = SchedulerConstants.STAFF_ZONE_MAP.get(activity_name)
        if not zone:
            return 0
        
        if hasattr(self, 'staff_load_by_slot'):
            return self.staff_load_by_slot.get(slot, {}).get(zone, 0)
        return 0
    
    def _get_clustering_score(self, troop, day: Day) -> int:
        """
        Calculate how many activities a troop has on a specific day.
        Higher score = better clustering.
        """
        return sum(
            1 for e in self.schedule.entries
            if e.troop == troop and e.time_slot.day == day
        )
