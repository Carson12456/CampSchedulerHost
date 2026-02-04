"""
Advanced Staff Workload Balancer
Addresses staff load variance issues identified in scheduling analysis
"""

from models import Day, Activity, TimeSlot
from collections import defaultdict
import math


class StaffBalanceOptimizer:
    """
    Advanced staff workload optimization system.
    Reduces variance in staff distribution across time slots.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        self.time_slots = self._generate_time_slots()
        
        # Staff zone mapping
        self.STAFF_ZONE_MAP = {
            'Climbing Tower': 'Tower',
            'Troop Rifle': 'Rifle',
            'Troop Shotgun': 'Rifle',
            'Archery': 'Archery',
            'Knots and Lashings': 'ODS',
            'Orienteering': 'ODS',
            'GPS & Geocaching': 'ODS',
            'Ultimate Survivor': 'ODS',
            "What's Cooking": 'ODS',
            'Chopped!': 'ODS',
            'Tie Dye': 'Handicrafts',
            'Hemp Craft': 'Handicrafts',
            'Woggle Neckerchief Slide': 'Handicrafts',
            "Monkey's Fist": 'Handicrafts',
            'Aqua Trampoline': 'Beach',
            'Troop Canoe': 'Beach',
            'Troop Kayak': 'Beach',
            'Canoe Snorkel': 'Beach',
            'Float for Floats': 'Beach',
            'Greased Watermelon': 'Beach',
            'Underwater Obstacle Course': 'Beach',
            'Troop Swim': 'Beach',
            'Water Polo': 'Beach',
            'Nature Canoe': 'Beach',
            'Sailing': 'Beach',
        }
        
        # Safe swap activities (low impact on preferences)
        self.SAFE_SWAP_ACTIVITIES = {
            'Gaga Ball', '9 Square', 'Fishing', 'Trading Post', 
            'Campsite Free Time', 'Dr. DNA', 'Loon Lore'
        }
    
    def _generate_time_slots(self):
        """Generate all time slots for the week."""
        slots = []
        for day in Day:
            max_slot = 2 if day == Day.THURSDAY else 3
            for slot_num in range(1, max_slot + 1):
                slots.append((day, slot_num))
        return slots
    
    def optimize_staff_balance(self, target_variance=1.0):
        """
        Optimize staff workload balance to achieve target variance.
        Uses intelligent activity swapping to reduce load variance.
        """
        print("=== ADVANCED STAFF BALANCE OPTIMIZER ===")
        
        # Calculate current staff distribution
        current_distribution = self._calculate_staff_distribution()
        current_variance = self._calculate_variance(current_distribution)
        
        print(f"Current variance: {current_variance:.2f}")
        print(f"Target variance: {target_variance:.2f}")
        
        if current_variance <= target_variance:
            print("Staff balance already optimal!")
            return 0
        
        optimization_cycles = 0
        max_cycles = 10
        
        while current_variance > target_variance and optimization_cycles < max_cycles:
            print(f"\nOptimization cycle {optimization_cycles + 1}/{max_cycles}")
            
            # Find overloaded and underloaded slots
            overloaded_slots = []
            underloaded_slots = []
            
            avg_load = sum(current_distribution.values()) / len(current_distribution)
            
            for slot, load in current_distribution.items():
                if load > avg_load * 1.3:  # 30% above average
                    overloaded_slots.append((slot, load))
                elif load < avg_load * 0.7:  # 30% below average
                    underloaded_slots.append((slot, load))
            
            print(f"  Overloaded slots: {len(overloaded_slots)}")
            print(f"  Underloaded slots: {len(underloaded_slots)}")
            
            if not overloaded_slots or not underloaded_slots:
                print("  No more optimization opportunities")
                break
            
            # Try to move activities from overloaded to underloaded slots
            moves_made = self._optimize_slot_pairs(overloaded_slots, underloaded_slots)
            
            if moves_made == 0:
                print("  No moves possible in this cycle")
                break
            
            # Recalculate distribution
            current_distribution = self._calculate_staff_distribution()
            current_variance = self._calculate_variance(current_distribution)
            
            print(f"  Moves made: {moves_made}")
            print(f"  New variance: {current_variance:.2f}")
            
            optimization_cycles += 1
        
        variance_reduction = current_variance - current_variance
        print(f"\n=== OPTIMIZATION COMPLETE ===")
        print(f"Variance reduced by: {variance_reduction:.2f}")
        print(f"Final variance: {current_variance:.2f}")
        print(f"Optimization cycles: {optimization_cycles}")
        
        return variance_reduction
    
    def _calculate_staff_distribution(self):
        """Calculate staff workload distribution across all slots."""
        distribution = defaultdict(int)
        
        for entry in self.schedule.entries:
            activity_name = entry.activity.name
            if activity_name in self.STAFF_ZONE_MAP:
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                distribution[slot_key] += 1
        
        return distribution
    
    def _calculate_variance(self, distribution):
        """Calculate variance of staff distribution."""
        if not distribution:
            return 0.0
        
        loads = list(distribution.values())
        avg_load = sum(loads) / len(loads)
        
        variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)
        return variance
    
    def _optimize_slot_pairs(self, overloaded_slots, underloaded_slots):
        """
        Optimize by swapping activities between overloaded and underloaded slots.
        Prioritizes low-impact swaps to preserve preference satisfaction.
        """
        moves_made = 0
        
        for (overloaded_slot, overloaded_load) in overloaded_slots:
            for (underloaded_slot, underloaded_load) in underloaded_slots:
                # Try to find swappable activities
                move_result = self._find_optimal_move(overloaded_slot, underloaded_slot)
                
                if move_result:
                    activity_to_move, troop = move_result
                    
                    # Perform the move
                    self._move_activity(activity_to_move, troop, overloaded_slot, underloaded_slot)
                    moves_made += 1
                    
                    print(f"    Moved {activity_to_move} from {overloaded_slot[0].value[:3]}-{overloaded_slot[1]} to {underloaded_slot[0].value[:3]}-{underloaded_slot[1]}")
                    
                    # Update loads
                    overloaded_load -= 1
                    underloaded_load += 1
                    
                    if overloaded_load <= underloaded_load:
                        break  # This slot is balanced enough
        
        return moves_made
    
    def _find_optimal_move(self, from_slot, to_slot):
        """
        Find the best activity to move from overloaded to underloaded slot.
        Prioritizes activities that:
        1. Are safe swap activities (low preference impact)
        2. Don't create constraint violations
        3. Can actually be moved (troop is free, activity available)
        """
        # Get activities in the overloaded slot
        from_entries = [
            e for e in self.schedule.entries 
            if (e.time_slot.day == from_slot[0] and 
                e.time_slot.slot_number == from_slot[1] and
                e.activity.name in self.STAFF_ZONE_MAP)
        ]
        
        # Sort by priority: safe swap activities first
        from_entries.sort(key=lambda e: 0 if e.activity.name in self.SAFE_SWAP_ACTIVITIES else 1)
        
        for entry in from_entries:
            # Check if this activity can be moved to the target slot
            if self._can_move_activity(entry, to_slot):
                return (entry.activity.name, entry.troop)
        
        return None
    
    def _can_move_activity(self, entry, target_slot):
        """
        Check if an activity can be moved to a target slot without violating constraints.
        """
        troop = entry.troop
        activity = entry.activity
        target_time_slot = TimeSlot(target_slot[0], target_slot[1])
        
        # Check if troop is free in target slot
        if not self.schedule.is_troop_free(target_time_slot, troop):
            return False
        
        # Check if activity is available in target slot
        if not self.schedule.is_activity_available(target_time_slot, activity, troop):
            return False
        
        # Additional constraint checks
        # 1. Beach slot constraint
        if (activity.name in {'Water Polo', 'Greased Watermelon', 'Aqua Trampoline', 'Troop Swim',
                             'Underwater Obstacle Course', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                             'Nature Canoe', 'Float for Floats'} and
            target_slot[1] == 2 and target_slot[0] != Day.THURSDAY):
            return False
        
        # 2. Wet/Dry pattern check
        if self._would_create_wet_dry_violation(entry, target_slot):
            return False
        
        return True
    
    def _would_create_wet_dry_violation(self, entry, target_slot):
        """Check if moving an activity would create wet/dry pattern violations."""
        WET_ACTIVITIES = {
            "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats", "Sailing", "Sauna"
        }
        
        TOWER_ODS_ACTIVITIES = {
            "Climbing Tower", "Knots and Lashings", "Orienteering", "GPS & Geocaching",
            "Ultimate Survivor", "What's Cooking", "Chopped!"
        }
        
        # Get troop's activities in the target day
        day_entries = [
            e for e in self.schedule.entries 
            if e.troop == entry.troop and e.time_slot.day == target_slot[0]
        ]
        
        # Add the entry we're considering moving
        day_entries.append(entry)
        
        # Sort by slot number
        day_entries.sort(key=lambda e: e.time_slot.slot_number)
        
        # Check for violations
        for i in range(len(day_entries) - 1):
            curr = day_entries[i]
            next_e = day_entries[i + 1]
            
            # Wet -> Tower/ODS violation
            if (curr.activity.name in WET_ACTIVITIES and 
                next_e.activity.name in TOWER_ODS_ACTIVITIES):
                return True
            
            # Tower/ODS -> Wet violation
            if (curr.activity.name in TOWER_ODS_ACTIVITIES and 
                next_e.activity.name in WET_ACTIVITIES):
                return True
        
        return False
    
    def _move_activity(self, activity_name, troop, from_slot, to_slot):
        """
        Move an activity from one slot to another.
        """
        # Find the entry to move
        entry_to_move = None
        for entry in self.schedule.entries:
            if (entry.troop == troop and 
                entry.activity.name == activity_name and
                entry.time_slot.day == from_slot[0] and
                entry.time_slot.slot_number == from_slot[1]):
                entry_to_move = entry
                break
        
        if not entry_to_move:
            return False
        
        # Remove from old slot
        self.schedule.remove_entry(entry_to_move)
        
        # Add to new slot
        new_time_slot = TimeSlot(to_slot[0], to_slot[1])
        self.schedule.add_entry(new_time_slot, entry_to_move.activity, troop)
        
        return True


def optimize_staff_workload(schedule, troops, activities, target_variance=1.0):
    """
    Optimize staff workload balance for a schedule.
    """
    optimizer = StaffBalanceOptimizer(schedule, troops, activities)
    return optimizer.optimize_staff_balance(target_variance)
