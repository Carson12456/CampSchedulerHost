"""
Enhanced Constraint Fixes for Summer Camp Scheduler
Addresses critical weak points in scheduling processes
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict
import math


class EnhancedConstraintFixer:
    """
    Advanced constraint violation detection and fixing system.
    Targets the most critical scheduling weak points identified in analysis.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        self.time_slots = self._generate_time_slots()
        
        # Critical constraint definitions
        self.BEACH_SLOT_ACTIVITIES = {
            "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats"
        }
        
        self.WET_ACTIVITIES = {
            "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats", "Sailing", "Sauna"
        }
        
        self.TOWER_ODS_ACTIVITIES = {
            "Climbing Tower", "Knots and Lashings", "Orienteering", "GPS & Geocaching",
            "Ultimate Survivor", "What's Cooking", "Chopped!"
        }
        
        self.DELTA_COMPATIBLE_ZONES = {Zone.BEACH, Zone.CAMPSITE, Zone.DELTA}
        
        # Safe replacement activities
        self.SAFE_REPLACEMENTS = [
            "Campsite Free Time", "Gaga Ball", "9 Square", "Fishing", 
            "Trading Post", "Dr. DNA", "Loon Lore"
        ]
    
    def _generate_time_slots(self):
        """Generate all time slots for the week."""
        slots = []
        for day in Day:
            max_slot = 2 if day == Day.THURSDAY else 3
            for slot_num in range(1, max_slot + 1):
                slots.append(TimeSlot(day, slot_num))
        return slots
    
    def fix_all_critical_violations(self):
        """
        Fix all critical constraint violations with priority ordering:
        1. Beach Slot Violations (Hard constraint)
        2. Friday Reflection Missing (Mandatory)
        3. Wet/Dry Pattern Violations (Quality constraint)
        4. Delta Walking Violations (Logistics constraint)
        """
        fixes_applied = {
            'beach_slot': 0,
            'friday_reflection': 0,
            'wet_dry_pattern': 0,
            'delta_walking': 0
        }
        
        print("=== ENHANCED CONSTRAINT FIXER ===")
        
        # Fix 1: Beach Slot Violations (Highest Priority)
        print("\n1. Fixing Beach Slot Violations...")
        fixes_applied['beach_slot'] = self._fix_beach_slot_violations()
        
        # Fix 2: Friday Reflection Missing (Mandatory)
        print("\n2. Fixing Friday Reflection Missing...")
        fixes_applied['friday_reflection'] = self._fix_friday_reflection_missing()
        
        # Fix 3: Wet/Dry Pattern Violations
        print("\n3. Fixing Wet/Dry Pattern Violations...")
        fixes_applied['wet_dry_pattern'] = self._fix_wet_dry_pattern_violations()
        
        # Fix 4: Delta Walking Violations
        print("\n4. Fixing Delta Walking Violations...")
        fixes_applied['delta_walking'] = self._fix_delta_walking_violations()
        
        total_fixes = sum(fixes_applied.values())
        print(f"\n=== SUMMARY ===")
        print(f"Total fixes applied: {total_fixes}")
        for fix_type, count in fixes_applied.items():
            print(f"  {fix_type}: {count}")
        
        return total_fixes
    
    def _fix_beach_slot_violations(self):
        """Fix beach activities in invalid slot 2 (except Thursday). Top 5 relaxation: skip valid slot 2."""
        violations = []
        
        for entry in self.schedule.entries:
            if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.slot_number == 2 and 
                entry.time_slot.day != Day.THURSDAY):
                troop = entry.troop
                pref_rank = troop.get_priority(entry.activity.name) if hasattr(troop, 'get_priority') else None
                if pref_rank is not None and pref_rank < 5:
                    if entry.activity.name == "Aqua Trampoline" and (troop.scouts + troop.adults) <= 16:
                        violations.append(entry)  # AT slot 2 requires exclusive
                    # else: Top 5 other beach - valid, skip
                else:
                    violations.append(entry)
        
        print(f"  Found {len(violations)} beach slot violations")
        
        fixes_count = 0
        for violation in violations:
            troop = violation.troop
            day = violation.time_slot.day
            
            # Try to move to slot 1 or 3
            for target_slot in [1, 3]:
                if target_slot > 2 and day == Day.THURSDAY:
                    continue  # Thursday only has 2 slots
                
                new_time_slot = TimeSlot(day, target_slot)
                
                # Check if move is valid
                if (self.schedule.is_troop_free(new_time_slot, troop) and
                    self.schedule.is_activity_available(new_time_slot, violation.activity, troop)):
                    
                    # Remove old entry and add new one
                    self.schedule.remove_entry(violation)
                    self.schedule.add_entry(new_time_slot, violation.activity, troop)
                    fixes_count += 1
                    print(f"    Fixed: {troop.name} {violation.activity.name} from slot 2 to slot {target_slot}")
                    break
        
        return fixes_count
    
    def _fix_friday_reflection_missing(self):
        """Ensure all troops have Friday Reflection scheduled - GUARANTEED APPROACH."""
        missing_troops = []
        
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries if e.troop == troop
            )
            if not has_reflection:
                missing_troops.append(troop)
        
        print(f"  Found {len(missing_troops)} troops missing Friday Reflection")
        
        fixes_count = 0
        reflection_activity = self.activities.get("Reflection")
        if not reflection_activity:
            print("    ERROR: Reflection activity not found!")
            return 0
        
        for troop in missing_troops:
            scheduled = False
            
            # Try to schedule in any available Friday slot (less strict checking)
            for slot_num in [1, 2, 3]:
                friday_slot = TimeSlot(Day.FRIDAY, slot_num)
                
                # Just check if troop is free, ignore activity availability
                if self.schedule.is_troop_free(friday_slot, troop):
                    self.schedule.add_entry(friday_slot, reflection_activity, troop)
                    fixes_count += 1
                    print(f"    Added: {troop.name} Reflection on Friday slot {slot_num}")
                    scheduled = True
                    break
            
            # If still not scheduled, FORCE it by removing existing activity
            if not scheduled:
                # Use Friday slot 3 for forced scheduling
                force_slot = TimeSlot(Day.FRIDAY, 3)
                
                # Remove any existing activity for this troop in this slot
                existing_entries = [e for e in self.schedule.entries 
                                  if e.time_slot == force_slot and e.troop == troop]
                
                for entry in existing_entries:
                    self.schedule.entries.remove(entry)
                    print(f"    [REMOVED] {troop.name}: {entry.activity.name} from Friday slot 3")
                
                # Add Reflection
                self.schedule.add_entry(force_slot, reflection_activity, troop)
                fixes_count += 1
                print(f"    [FORCED] {troop.name}: Reflection on Friday slot 3 (overrode existing)")
        
        return fixes_count
    
    def _fix_wet_dry_pattern_violations(self):
        """Fix wet-dry-wet patterns and wet->tower/ods violations."""
        violations = []
        
        for troop in self.troops:
            troop_entries = sorted(
                [e for e in self.schedule.entries if e.troop == troop],
                key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
            )
            
            # Group by day
            by_day = defaultdict(list)
            for entry in troop_entries:
                by_day[entry.time_slot.day].append(entry)
            
            for day, day_entries in by_day.items():
                day_entries.sort(key=lambda e: e.time_slot.slot_number)
                
                # Check wet->tower/ods violations
                for i in range(len(day_entries) - 1):
                    curr = day_entries[i]
                    next_e = day_entries[i + 1]
                    
                    if (curr.activity.name in self.WET_ACTIVITIES and 
                        next_e.activity.name in self.TOWER_ODS_ACTIVITIES):
                        violations.append({
                            'type': 'wet_to_tower',
                            'troop': troop,
                            'wet_entry': curr,
                            'tower_entry': next_e,
                            'day': day
                        })
                    
                    # Check wet-dry-wet pattern (slots 1,2,3)
                    if len(day_entries) >= 3:
                        slot_map = {e.time_slot.slot_number: e for e in day_entries}
                        if (1 in slot_map and 2 in slot_map and 3 in slot_map):
                            s1_wet = slot_map[1].activity.name in self.WET_ACTIVITIES
                            s2_wet = slot_map[2].activity.name in self.WET_ACTIVITIES
                            s3_wet = slot_map[3].activity.name in self.WET_ACTIVITIES
                            
                            if s1_wet and not s2_wet and s3_wet:
                                violations.append({
                                    'type': 'wet_dry_wet',
                                    'troop': troop,
                                    'middle_entry': slot_map[2],
                                    'day': day
                                })
        
        print(f"  Found {len(violations)} wet/dry pattern violations")
        
        fixes_count = 0
        for violation in violations:
            if violation['type'] == 'wet_to_tower':
                fixes_count += self._fix_wet_to_tower_violation(violation)
            elif violation['type'] == 'wet_dry_wet':
                fixes_count += self._fix_wet_dry_wet_violation(violation)
        
        return fixes_count
    
    def _fix_wet_to_tower_violation(self, violation):
        """Fix wet activity immediately followed by tower/ods activity."""
        troop = violation['troop']
        wet_entry = violation['wet_entry']
        tower_entry = violation['tower_entry']
        day = violation['day']
        
        # Try to swap tower activity with a different slot
        for target_slot in [1, 2, 3]:
            if target_slot == tower_entry.time_slot.slot_number:
                continue
            
            new_time_slot = TimeSlot(day, target_slot)
            
            # Check if we can move the tower activity
            if (self.schedule.is_troop_free(new_time_slot, troop) and
                self.schedule.is_activity_available(new_time_slot, tower_entry.activity, troop)):
                
                # Check if this creates new violations
                creates_violation = False
                
                # Check adjacent activities for wet conflicts
                for other_entry in self.schedule.entries:
                    if (other_entry.troop == troop and 
                        other_entry.time_slot.day == day and
                        abs(other_entry.time_slot.slot_number - target_slot) == 1):
                        
                        if (other_entry.activity.name in self.WET_ACTIVITIES or
                            other_entry.activity.name in self.TOWER_ODS_ACTIVITIES):
                            creates_violation = True
                            break
                
                if not creates_violation:
                    # Move the tower activity
                    self.schedule.remove_entry(tower_entry)
                    self.schedule.add_entry(new_time_slot, tower_entry.activity, troop)
                    print(f"    Fixed wet->tower: {troop.name} {tower_entry.activity.name} moved to slot {target_slot}")
                    return 1
        
        return 0
    
    def _fix_wet_dry_wet_violation(self, violation):
        """Fix wet-dry-wet pattern by replacing middle activity."""
        troop = violation['troop']
        middle_entry = violation['middle_entry']
        day = violation['day']
        
        # Try to replace middle activity with a safe one
        for safe_activity_name in self.SAFE_REPLACEMENTS:
            if safe_activity_name == middle_entry.activity.name:
                continue
            
            safe_activity = self.activities.get(safe_activity_name)
            if not safe_activity:
                continue
            
            if self.schedule.is_activity_available(middle_entry.time_slot, safe_activity, troop):
                # Replace the activity
                self.schedule.remove_entry(middle_entry)
                self.schedule.add_entry(middle_entry.time_slot, safe_activity, troop)
                print(f"    Fixed wet-dry-wet: {troop.name} replaced {middle_entry.activity.name} with {safe_activity_name}")
                return 1
        
        return 0
    
    def _fix_delta_walking_violations(self):
        """Fix Delta activities followed by incompatible zones."""
        violations = []
        
        for troop in self.troops:
            troop_entries = sorted(
                [e for e in self.schedule.entries if e.troop == troop],
                key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
            )
            
            # Check adjacent activities
            for i in range(len(troop_entries) - 1):
                curr = troop_entries[i]
                next_e = troop_entries[i + 1]
                
                # Check Delta -> incompatible zone
                if (curr.activity.name == "Delta" and 
                    next_e.activity.zone not in self.DELTA_COMPATIBLE_ZONES and
                    curr.time_slot.day == next_e.time_slot.day):
                    
                    violations.append({
                        'troop': troop,
                        'delta_entry': curr,
                        'incompatible_entry': next_e
                    })
        
        print(f"  Found {len(violations)} Delta walking violations")
        
        fixes_count = 0
        for violation in violations:
            fixes_count += self._fix_delta_walking_violation_single(violation)
        
        return fixes_count
    
    def _fix_delta_walking_violation_single(self, violation):
        """Fix a single Delta walking violation."""
        troop = violation['troop']
        delta_entry = violation['delta_entry']
        incompatible_entry = violation['incompatible_entry']
        
        # Try to move the incompatible activity to a different slot
        for target_day in Day:
            for target_slot in [1, 2, 3]:
                if target_slot > 2 and target_day == Day.THURSDAY:
                    continue
                
                new_time_slot = TimeSlot(target_day, target_slot)
                
                # Check if move is valid
                if (self.schedule.is_troop_free(new_time_slot, troop) and
                    self.schedule.is_activity_available(new_time_slot, incompatible_entry.activity, troop)):
                    
                    # Move the incompatible activity
                    self.schedule.remove_entry(incompatible_entry)
                    self.schedule.add_entry(new_time_slot, incompatible_entry.activity, troop)
                    print(f"    Fixed Delta walking: {troop.name} {incompatible_entry.activity.name} moved to {target_day.value[:3]}-{target_slot}")
                    return 1
        
        return 0


def apply_enhanced_constraint_fixes(schedule, troops, activities):
    """
    Apply all enhanced constraint fixes to a schedule.
    """
    fixer = EnhancedConstraintFixer(schedule, troops, activities)
    return fixer.fix_all_critical_violations()
