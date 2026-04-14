"""
Phase B Core Module.

Contains methods for Phase B of the scheduling algorithm:
- B.1/B.1b/B.1c: Top 1-5 Preferences (Top 5 Guarantee)
- B.2: Guaranteeing 100% Top 5 satisfaction
- B.3: Mandatory Top 5 enforcement
- B.4: Delta scheduling (requested only)
- B.5: Commissioner Busy Map (diagnostic)
- B.6: Enforce Delta + Sailing same-day pairing
- B.7: Aqua Trampoline sharing (consolidated single pass)
"""

from ..models import Day, TimeSlot, generate_time_slots
from ..activities import get_activity_by_name
from .constants import SchedulerConstants


class PhaseBCoreMixin:
    """
    Mixin class providing Phase B (Core Requests) methods.
    
    Phase B handles preference-based scheduling:
    - Top 5 preferences (guaranteed)
    - Top 6-10 preferences
    - Delta and Sailing coordination
    - Activity pairing optimization
    """
    
    # =========================================================================
    # B.1: PREFERENCE SCHEDULING
    # =========================================================================
    
    def _schedule_preferences_range(self, start_rank, end_rank):
        """
        Unified per-preference scheduling: iterate through preference ranks start_rank to end_rank.
        """
        print(f"\n--- Scheduling Preferences {start_rank+1} to {end_rank} ---")
        
        for troop in self.troops:
            if not troop.preferences:
                continue
            
            for rank in range(start_rank, min(end_rank, len(troop.preferences))):
                activity_name = troop.preferences[rank]
                
                # Skip if already scheduled
                if self._troop_has_activity_by_name(troop, activity_name):
                    continue
                
                activity = get_activity_by_name(activity_name)
                if not activity:
                    continue
                
                # Find a valid slot
                scheduled = False
                for slot in self.time_slots:
                    if not self.schedule.is_troop_free(slot, troop):
                        continue
                    
                    # Basic constraint check
                    if self._can_schedule_basic(slot, activity, troop):
                        self._add_to_schedule(slot, activity, troop)
                        
                        # Update tracking
                        if rank < 5:
                            self.troop_top5_scheduled[troop.name] = self.troop_top5_scheduled.get(troop.name, 0) + 1
                        elif rank < 10:
                            self.troop_top10_scheduled[troop.name] = self.troop_top10_scheduled.get(troop.name, 0) + 1
                        
                        print(f"  {troop.name}: {activity_name} (rank {rank+1}) -> {slot}")
                        scheduled = True
                        break
                
                if not scheduled and rank < 5:
                    print(f"  {troop.name}: Could not schedule Top 5 activity: {activity_name}")
    
    def _troop_has_activity_by_name(self, troop, activity_name):
        """Check if troop already has an activity scheduled."""
        return any(
            e.activity.name == activity_name
            for e in self.schedule.entries
            if e.troop == troop
        )
    
    def _can_schedule_basic(self, slot, activity, troop):
        """Basic constraint check for scheduling."""
        # Check exclusive area violations
        if activity.name in ["Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery"]:
            # Check if another troop has this activity at this time
            for entry in self.schedule.entries:
                if entry.time_slot == slot and entry.activity.name == activity.name:
                    return False
        
        # Check beach slot rules (slots 1 or 3 only, except Thursday)
        if activity.name in SchedulerConstants.BEACH_SLOT_ACTIVITIES:
            if slot.day != Day.THURSDAY and slot.slot_number == 2:
                # Slot 2 allowed for Top 5 beach activities
                priority = troop.get_priority(activity.name)
                if priority is None or priority >= 5:
                    return False
        
        return True
    
    # =========================================================================
    # B.2: GUARANTEE TOP 5
    # =========================================================================
    
    def _guarantee_all_top5(self):
        """Guarantee 100% Top 5 satisfaction for all troops."""
        print("\n--- Guaranteeing 100% Top 5 ---")
        
        for troop in self.troops:
            if not troop.preferences:
                continue
            
            top5 = troop.preferences[:5]
            missing = []
            
            for activity_name in top5:
                if not self._troop_has_activity_by_name(troop, activity_name):
                    missing.append(activity_name)
            
            if not missing:
                continue
            
            print(f"  {troop.name}: Missing Top 5: {missing}")
            
            for activity_name in missing:
                activity = get_activity_by_name(activity_name)
                if not activity:
                    continue
                
                # Try to force-place
                for slot in self.time_slots:
                    if self.schedule.is_troop_free(slot, troop):
                        self._add_to_schedule(slot, activity, troop)
                        print(f"    -> {activity_name} forced to {slot}")
                        break
    
    # =========================================================================
    # B.3: MANDATORY ENFORCEMENT
    # =========================================================================
    
    def _enforce_mandatory_top5(self):
        """Enforce mandatory Top 5 activities by displacing lower-priority items."""
        print("\n--- Enforcing Mandatory Top 5 ---")
        
        for troop in self.troops:
            if not troop.preferences:
                continue
            
            top5 = troop.preferences[:5]
            
            for activity_name in top5:
                if self._troop_has_activity_by_name(troop, activity_name):
                    continue
                
                activity = get_activity_by_name(activity_name)
                if not activity:
                    continue
                
                # Find a low-priority activity to displace
                displaced = self._displace_for_activity(troop, activity)
                if displaced:
                    print(f"  {troop.name}: Displaced {displaced} for {activity_name}")
    
    def _displace_for_activity(self, troop, activity):
        """Try to displace a low-priority activity to make room for a higher-priority one."""
        # Find fill activities that can be displaced
        fill_activities = SchedulerConstants.FILL_ACTIVITIES
        
        for entry in list(self.schedule.entries):
            if entry.troop != troop:
                continue
            
            if entry.activity.name in fill_activities:
                # Skip if it's a top preference
                priority = troop.get_priority(entry.activity.name)
                if priority is not None and priority < 10:
                    continue
                
                # Displace this activity
                slot = entry.time_slot
                displaced_name = entry.activity.name
                
                self._remove_from_schedule(entry)
                self._add_to_schedule(slot, activity, troop)
                
                return displaced_name
        
        return None
    
    # =========================================================================
    # B.4: DELTA SCHEDULING
    # =========================================================================
    
    def _schedule_delta_early(self):
        """Schedule Delta for troops that request it (not forced by commissioner)."""
        print("\n--- Scheduling Delta (requested only) ---")
        
        delta = get_activity_by_name("Delta")
        if not delta:
            print("  Warning: Delta not found!")
            return
        
        for troop in self.troops:
            # Check if troop wants Delta
            priority = troop.get_priority("Delta")
            if priority is None or priority >= 20:
                continue
            
            # Check if already scheduled
            if self.troop_has_delta.get(troop.name, False):
                continue
            
            # Get commissioner's Delta day
            commissioner = self.troop_commissioner.get(troop.name, "")
            delta_day = self.COMMISSIONER_DELTA_DAYS.get(commissioner)
            
            if not delta_day:
                continue
            
            # Find slots on that day
            day_slots = sorted(
                [s for s in self.time_slots if s.day == delta_day],
                key=lambda s: s.slot_number
            )
            
            # Delta needs 2 consecutive slots - prefer slots 1-2
            for i in range(len(day_slots) - 1):
                slot1 = day_slots[i]
                slot2 = day_slots[i + 1]
                
                if (self.schedule.is_troop_free(slot1, troop) and
                    self.schedule.is_troop_free(slot2, troop)):
                    self._add_to_schedule(slot1, delta, troop)
                    self.troop_has_delta[troop.name] = True
                    print(f"  {troop.name}: Delta -> {slot1} (2 slots)")
                    break
    
    # =========================================================================
    # B.7: AQUA TRAMPOLINE SHARING (CONSOLIDATED)
    # =========================================================================
    
    def _aggressive_aqua_trampoline_sharing(self):
        """
        Pair troops for Aqua Trampoline sharing when possible.
        
        Two troops can share an AT slot if their combined size is <= 16.
        """
        print("\n--- Aggressive Aqua Trampoline Sharing ---")
        
        at = get_activity_by_name("Aqua Trampoline")
        if not at:
            return
        
        # Find troops that want AT but don't have it
        at_wants = []
        for troop in self.troops:
            if self._troop_has_activity_by_name(troop, "Aqua Trampoline"):
                continue
            
            priority = troop.get_priority("Aqua Trampoline")
            if priority is not None and priority < 10:
                at_wants.append((priority, troop))
        
        at_wants.sort(key=lambda x: x[0])
        
        # Find slots that already have AT scheduled
        at_slots = []
        for entry in self.schedule.entries:
            if entry.activity.name == "Aqua Trampoline":
                at_slots.append((entry.time_slot, entry.troop))
        
        # Try to pair troops
        for priority, troop in at_wants:
            troop_size = troop.scouts + troop.adults
            
            for slot, existing_troop in at_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    continue
                
                existing_size = existing_troop.scouts + existing_troop.adults
                
                if troop_size + existing_size <= 16:
                    self._add_to_schedule(slot, at, troop)
                    print(f"  {troop.name}: AT shared with {existing_troop.name} in {slot}")
                    break
