"""
Phase A Foundation Module.

Contains methods for Phase A of the scheduling algorithm (Rocks, Pebbles, Sand):
- A.1: Friday Reflection (mandatory anchor)
- A.2: Super Troop (mandatory anchor)
- A.3: HC/DG Tuesday scheduling (mandatory anchor)
- A.4: 3-Hour Activities (Rocks)
- A.5: Top-10 2-Hour Activities (Rocks)
- A.6: Sailing Optimization (9-Slot)
- A.7: Delta + Sailing pairing
- A.8: Early Sailing for Top 10 troops (from Phase B)
- A.9: Consolidate Sailing same-day clustering (from Phase B)
- A.10: Early Aqua Trampoline for Top 5
- A.11: Guarantee Top 1 Beach
- A.12: Early staff area clustering
- A.13: Priority limited activities (Global Rank 0-4)
- A.14: Sailing pairs for same-day bonus
"""

from ..models import Day, TimeSlot, generate_time_slots
from ..activities import get_activity_by_name
from .constants import SchedulerConstants


class PhaseAFoundationMixin:
    """
    Mixin class providing Phase A (Foundation & Clustering) methods.
    
    Phase A establishes the schedule foundation by reserving slots for:
    - Mandatory activities (Reflection, Super Troop)
    - Multi-slot activities (3-hour, 2-hour, Sailing)
    - Commissioner-controlled activities (Delta)
    - Staff area clustering
    """
    
    # =========================================================================
    # A.1: FRIDAY REFLECTION
    # =========================================================================
    
    def _schedule_friday_reflection(self):
        """Ensure ALL troops get Reflection on Friday, distributed by campsite proximity.
        
        Nearby campsites (based on north-to-south order) share the same Reflection slot.
        Now decoupled from Commissioner availability (staff-led or troop-led).
        """
        print("\n--- Scheduling Friday Reflection for ALL troops (by campsite proximity) ---")
        reflection = get_activity_by_name("Reflection")
        if not reflection:
            print("  Warning: Reflection activity not found!")
            return
        
        print("DEBUG: Checking slots for Reflection...")
        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
        
        # Group troops by campsite proximity (divide into 3 zones: north, middle, south)
        troops_sorted = []
        for troop in self.troops:
            # Get campsite index from north-to-south order
            base_name = troop.name.replace("-A", "").replace("-B", "")
            if base_name in self.CAMPSITE_ORDER:
                idx = self.CAMPSITE_ORDER.index(base_name)
            else:
                idx = len(self.CAMPSITE_ORDER)  # Unknown campsites go last
            troops_sorted.append((idx, troop))
        
        troops_sorted.sort(key=lambda x: x[0])
        
        # Divide into 3 proximity groups (for 3 Friday slots)
        num_troops = len(troops_sorted)
        group_size = max(1, (num_troops + 2) // 3)  # Ceiling division
        
        troop_slot_map = {}  # Track assigned slots for base troop names
        
        for i, (_, troop) in enumerate(troops_sorted):
            base_name = troop.name.replace("-A", "").replace("-B", "")
            
            # Check if split troop already has assigned slot
            if base_name in troop_slot_map:
                slot_idx = troop_slot_map[base_name]
            else:
                slot_idx = min(i // group_size, len(friday_slots) - 1)
                troop_slot_map[base_name] = slot_idx
            
            slot = friday_slots[slot_idx]
            zone_name = "north" if slot_idx == 0 else ("middle" if slot_idx == 1 else "south")
            
            if self.schedule.is_troop_free(slot, troop):
                self.schedule.add_entry(slot, reflection, troop)
                print(f"  {troop.name}: Reflection -> {slot} ({zone_name} zone)")
            else:
                # Try next available slot
                scheduled = False
                for alt_slot in friday_slots:
                    if self.schedule.is_troop_free(alt_slot, troop):
                        self.schedule.add_entry(alt_slot, reflection, troop)
                        print(f"  {troop.name}: Reflection -> {alt_slot} (fallback)")
                        scheduled = True
                        break
                if not scheduled:
                    print(f"  WARNING: Could not schedule Reflection for {troop.name}")
                    # Force schedule in slot 3
                    force_slot = friday_slots[-1]
                    self.schedule.add_entry(force_slot, reflection, troop)
                    print(f"  [FORCE] {troop.name}: Reflection -> {force_slot}")
    
    # =========================================================================
    # A.2: SUPER TROOP
    # =========================================================================
    
    def _schedule_super_troop(self):
        """Schedule Super Troop for all troops on their commissioner's designated day.
        
        Super Troop is a mandatory activity that every troop must have.
        Each commissioner has a designated Super Troop day.
        """
        print("\n--- Scheduling Super Troop for ALL troops ---")
        super_troop = get_activity_by_name("Super Troop")
        if not super_troop:
            print("  Warning: Super Troop activity not found!")
            return
        
        for troop in self.troops:
            # Get commissioner's Super Troop day
            commissioner = self.troop_commissioner.get(troop.name, "")
            st_day = self.COMMISSIONER_SUPER_TROOP_DAYS.get(commissioner)
            
            if not st_day:
                print(f"  WARNING: No Super Troop day for {troop.name} (commissioner: {commissioner})")
                continue
            
            # Find a slot on that day
            day_slots = [s for s in self.time_slots if s.day == st_day]
            
            scheduled = False
            # Prefer slot 3 for Super Troop (after Delta in slots 1-2)
            preferred_order = [3, 2, 1]
            
            for slot_num in preferred_order:
                slot = next((s for s in day_slots if s.slot_number == slot_num), None)
                if slot and self.schedule.is_troop_free(slot, troop):
                    self._add_to_schedule(slot, super_troop, troop)
                    self.troop_has_super_troop[troop.name] = True
                    print(f"  {troop.name}: Super Troop -> {slot}")
                    scheduled = True
                    break
            
            if not scheduled:
                # Try any available slot on any day
                for slot in self.time_slots:
                    if self.schedule.is_troop_free(slot, troop):
                        self._add_to_schedule(slot, super_troop, troop)
                        self.troop_has_super_troop[troop.name] = True
                        print(f"  {troop.name}: Super Troop -> {slot} (fallback)")
                        scheduled = True
                        break
            
            if not scheduled:
                print(f"  WARNING: Could not schedule Super Troop for {troop.name}")
    
    # =========================================================================
    # A.4: 3-HOUR ACTIVITIES (ROCKS)
    # =========================================================================
    
    def _schedule_three_hour_activities(self):
        """Schedule 3-hour activities first - they need the most consecutive slots."""
        print("\n--- Scheduling 3-Hour Activities ---")
        
        three_hour_names = SchedulerConstants.THREE_HOUR_ACTIVITIES
        
        for troop in self.troops:
            for activity_name in three_hour_names:
                # Check if troop wants this activity
                priority = troop.get_priority(activity_name)
                if priority is None or priority >= 20:
                    continue  # Not in preferences
                
                activity = get_activity_by_name(activity_name)
                if not activity:
                    continue
                
                # Find a day with 3 consecutive free slots
                scheduled = False
                for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]:  # Skip Thu (2 slots) and Fri
                    day_slots = sorted(
                        [s for s in self.time_slots if s.day == day],
                        key=lambda s: s.slot_number
                    )
                    
                    # Check if all 3 slots are free
                    if len(day_slots) >= 3:
                        all_free = all(
                            self.schedule.is_troop_free(s, troop) 
                            for s in day_slots[:3]
                        )
                        
                        if all_free:
                            # Schedule in slot 1 (will occupy all 3)
                            self._add_to_schedule(day_slots[0], activity, troop)
                            print(f"  {troop.name}: {activity_name} -> {day.name} (3 slots)")
                            scheduled = True
                            break
                
                if not scheduled:
                    print(f"  {troop.name}: Could not schedule {activity_name}")
    
    # =========================================================================
    # A.3: HC/DG TUESDAY (MANDATORY ANCHOR)
    # =========================================================================
    
    def _schedule_hc_dg_tuesday(self):
        """
        Schedule History Center and Disc Golf for the top 3 troops that want them.
        
        NEW RULE: If a troop wants BOTH, they MUST be scheduled back-to-back.
        """
        print("\n--- Scheduling HC/DG Tuesday ---")
        
        hc = get_activity_by_name("History Center")
        dg = get_activity_by_name("Disc Golf")
        
        if not hc or not dg:
            print("  Warning: HC or DG not found!")
            return
        
        tuesday_slots = sorted(
            [s for s in self.time_slots if s.day == Day.TUESDAY],
            key=lambda s: s.slot_number
        )
        
        # Find troops that want HC and/or DG
        hc_wants = []
        dg_wants = []
        both_wants = []
        
        for troop in self.troops:
            hc_priority = troop.get_priority("History Center")
            dg_priority = troop.get_priority("Disc Golf")
            
            wants_hc = hc_priority is not None and hc_priority < 20
            wants_dg = dg_priority is not None and dg_priority < 20
            
            if wants_hc and wants_dg:
                # Sort by combined priority
                both_wants.append((hc_priority + dg_priority, troop))
            elif wants_hc:
                hc_wants.append((hc_priority, troop))
            elif wants_dg:
                dg_wants.append((dg_priority, troop))
        
        # Sort by priority
        both_wants.sort(key=lambda x: x[0])
        hc_wants.sort(key=lambda x: x[0])
        dg_wants.sort(key=lambda x: x[0])
        
        # Schedule troops that want BOTH first (back-to-back)
        for _, troop in both_wants[:2]:  # Max 2 troops for both
            # Find consecutive free slots
            for i in range(len(tuesday_slots) - 1):
                slot1 = tuesday_slots[i]
                slot2 = tuesday_slots[i + 1]
                
                if (self.schedule.is_troop_free(slot1, troop) and 
                    self.schedule.is_troop_free(slot2, troop)):
                    self._add_to_schedule(slot1, hc, troop)
                    self._add_to_schedule(slot2, dg, troop)
                    print(f"  {troop.name}: HC+DG -> {slot1}, {slot2} (back-to-back)")
                    break
    
    # =========================================================================
    # A.6: SAILING OPTIMIZATION (legacy Thursday Sailing helper)
    # =========================================================================
    
    def _schedule_thursday_sailing_largest_troop(self):
        """
        Schedule Thursday Sailing for the LARGEST troop that wants it.
        
        Thursday only has 2 slots total, so only 1 Sailing can fit (takes 1.5 slots).
        This must go to the troop with the most scouts to maximize attendance.
        """
        print("\n--- Scheduling Thursday Sailing (largest troop) ---")
        
        sailing = get_activity_by_name("Sailing")
        if not sailing:
            print("  Warning: Sailing not found!")
            return
        
        thursday_slots = sorted(
            [s for s in self.time_slots if s.day == Day.THURSDAY],
            key=lambda s: s.slot_number
        )
        
        if len(thursday_slots) < 2:
            print("  Warning: Not enough Thursday slots!")
            return
        
        # Find troops that want sailing, sorted by size
        sailing_wants = []
        for troop in self.troops:
            priority = troop.get_priority("Sailing")
            if priority is not None and priority < 20:
                sailing_wants.append((troop.scouts + troop.adults, priority, troop))
        
        # Sort by size (largest first), then priority
        sailing_wants.sort(key=lambda x: (-x[0], x[1]))
        
        if not sailing_wants:
            print("  No troops want Thursday Sailing")
            return
        
        # Schedule for the largest troop that fits
        for size, priority, troop in sailing_wants:
            slot = thursday_slots[0]  # Start in slot 1
            
            if self.schedule.is_troop_free(slot, troop):
                self._add_to_schedule(slot, sailing, troop)
                print(f"  {troop.name}: Sailing -> Thursday slot 1 (size: {size})")
                return
        
        print("  Could not schedule Thursday Sailing")
    
    # =========================================================================
    # A.7: DELTA + SAILING PAIRING
    # =========================================================================
    
    def _schedule_delta_sailing_pairs(self):
        """
        Schedule Delta + Sailing to occur on the same day when both are requested.
        
        Delta takes 2 slots, Sailing takes 1.5 slots.
        On a 3-slot day, Delta goes in slots 1-2, Sailing starts in slot 2.
        """
        print("\n--- Scheduling Delta + Sailing Pairs ---")
        
        delta = get_activity_by_name("Delta")
        sailing = get_activity_by_name("Sailing")
        
        if not delta or not sailing:
            print("  Warning: Delta or Sailing not found!")
            return
        
        for troop in self.troops:
            delta_priority = troop.get_priority("Delta")
            sailing_priority = troop.get_priority("Sailing")
            
            # Check if troop wants both
            wants_delta = delta_priority is not None and delta_priority < 20
            wants_sailing = sailing_priority is not None and sailing_priority < 20
            
            if not (wants_delta and wants_sailing):
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
            
            if len(day_slots) < 3:
                continue  # Need 3 slots for Delta + Sailing
            
            # Check if slots are free
            slot1, slot2, slot3 = day_slots[0], day_slots[1], day_slots[2]
            
            if (self.schedule.is_troop_free(slot1, troop) and
                self.schedule.is_troop_free(slot2, troop) and
                self.schedule.is_troop_free(slot3, troop)):
                
                # Schedule Delta in slot 1 (takes 2 slots)
                self._add_to_schedule(slot1, delta, troop)
                self.troop_has_delta[troop.name] = True
                
                # Schedule Sailing in slot 2 (overlaps with Delta, takes 1.5 slots)
                self._add_to_schedule(slot2, sailing, troop)
                
                print(f"  {troop.name}: Delta+Sailing -> {delta_day.name}")
