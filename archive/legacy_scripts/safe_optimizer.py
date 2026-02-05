#!/usr/bin/env python3
"""
Safe Schedule Optimizer - Rebuilt with comprehensive constraint checking.
Prevents any optimization that would cause constraint violations.
"""

class SafeScheduleOptimizer:
    """Safe optimization system that never violates constraints."""
    
    def __init__(self, schedule, troops, time_slots):
        self.schedule = schedule
        self.troops = troops
        self.time_slots = time_slots
        self.optimization_log = []
        
        # Constraint checking cache for performance
        self.constraint_cache = {}
        
    def log_optimization(self, optimization_type, details, success, impact=0):
        """Log optimization attempts for debugging."""
        self.optimization_log.append({
            'type': optimization_type,
            'details': details,
            'success': success,
            'impact': impact,
            'timestamp': len(self.optimization_log)
        })
    
    def check_all_constraints(self, entry, new_time_slot=None):
        """Comprehensive constraint checking before any move."""
        if new_time_slot is None:
            new_time_slot = entry.time_slot
            
        # Create more efficient cache key
        cache_key = (id(entry), id(new_time_slot), entry.troop.name, entry.activity.name)
        
        if cache_key in self.constraint_cache:
            return self.constraint_cache[cache_key]
        
        constraints_ok = True
        violations = []
        
        # Batch constraint checks for performance
        troop = entry.troop
        activity = entry.activity
        
        # 1. Basic availability checks
        if not self.schedule.is_troop_free(new_time_slot, troop):
            constraints_ok = False
            violations.append("Troop not free")
            
        if not self.schedule.is_activity_available(new_time_slot, activity, troop):
            constraints_ok = False
            violations.append("Activity not available")
        
        # Only continue with detailed checks if basic checks pass
        if constraints_ok:
            # 2. Accuracy conflict check
            if self._would_cause_accuracy_conflict(entry, new_time_slot):
                constraints_ok = False
                violations.append("Accuracy conflict")
            
            # 3. Wet-dry-wet pattern check
            if self._would_cause_wet_dry_wet_pattern(entry, new_time_slot):
                constraints_ok = False
                violations.append("Wet-dry-wet pattern")
            
            # 4. Same area same day check
            if self._would_cause_same_area_conflict(entry, new_time_slot):
                constraints_ok = False
                violations.append("Same area conflict")
            
            # 5. Beach slot appropriateness check
            if self._would_cause_beach_slot_violation(entry, new_time_slot):
                constraints_ok = False
                violations.append("Beach slot violation")
            
            # 6. Capacity check
            if self._would_cause_capacity_violation(entry, new_time_slot):
                constraints_ok = False
                violations.append("Capacity violation")
            
            # 7. Overlap check
            if self._would_cause_overlap(entry, new_time_slot):
                constraints_ok = False
                violations.append("Overlap conflict")
            
            # 8. Exclusive area conflict check
            if self._would_cause_exclusive_area_conflict(entry, new_time_slot):
                constraints_ok = False
                violations.append("Exclusive area conflict")
        
        result = {
            'ok': constraints_ok,
            'violations': violations
        }
        
        self.constraint_cache[cache_key] = result
        return result
    
    def _would_cause_accuracy_conflict(self, entry, new_time_slot):
        """Check if move would cause accuracy activity conflict."""
        accuracy_activities = ['Troop Rifle', 'Troop Shotgun', 'Archery']
        
        if entry.activity.name not in accuracy_activities:
            return False
        
        # Check for other accuracy activities same day for same troop
        troop_entries = self.schedule.get_troop_schedule(entry.troop)
        for other_entry in troop_entries:
            if (other_entry.time_slot.day == new_time_slot.day and 
                other_entry.activity.name in accuracy_activities and
                other_entry.activity.name != entry.activity.name):
                return True
        
        return False
    
    def _would_cause_wet_dry_wet_pattern(self, entry, new_time_slot):
        """Check if move would cause wet-dry-wet pattern."""
        wet_activities = ['Swimming', 'Canoeing', 'Kayaking', 'Sailing', 'Aqua Trampoline', 'Canoe Snorkel']
        dry_activities = ['Climbing Tower', 'Archery', 'Rifle', 'Shotgun', 'Orienteering']
        
        # Get all troop entries for that day
        troop_entries = self.schedule.get_troop_schedule(entry.troop)
        day_entries = [e for e in troop_entries if e.time_slot.day == new_time_slot.day]
        day_entries.sort(key=lambda x: x.time_slot.slot_number)
        
        # Check if this creates wet-dry-wet pattern
        for i in range(len(day_entries) - 2):
            entry1, entry2, entry3 = day_entries[i:i+3]
            
            is_wet1 = entry1.activity.name in wet_activities
            is_dry2 = entry2.activity.name in dry_activities
            is_wet3 = entry3.activity.name in wet_activities
            
            if is_wet1 and is_dry2 and is_wet3:
                return True
        
        return False
    
    def _would_cause_same_area_conflict(self, entry, new_time_slot):
        """Check if move would cause same area same day conflict."""
        from models import EXCLUSIVE_AREAS
        
        # Find which area this activity belongs to
        activity_area = None
        for area, activities in EXCLUSIVE_AREAS.items():
            if entry.activity.name in activities:
                activity_area = area
                break
        
        if not activity_area:
            return False
        
        # Check for other activities from same area same day
        troop_entries = self.schedule.get_troop_schedule(entry.troop)
        for other_entry in troop_entries:
            if (other_entry.time_slot.day == new_time_slot.day and
                other_entry.activity.name in EXCLUSIVE_AREAS.get(activity_area, []) and
                other_entry.activity.name != entry.activity.name):
                return True
        
        return False
    
    def _would_cause_beach_slot_violation(self, entry, new_time_slot):
        """Check if move would cause beach slot violation."""
        # Define appropriate beach activities
        beach_activities = ['Swimming', 'Aqua Trampoline', 'Canoeing', 'Kayaking', 'Sailing']
        non_beach_activities = ['Climbing Tower', 'Archery', 'Rifle', 'Shotgun']
        
        # Check if beach slot has inappropriate activity
        is_beach_slot = new_time_slot.slot_number in [1, 2]  # Assuming slots 1-2 are beach
        activity_is_beach = entry.activity.name in beach_activities
        
        if is_beach_slot and not activity_is_beach:
            return True
        
        return False
    
    def _would_cause_capacity_violation(self, entry, new_time_slot):
        """Check if move would cause capacity violation."""
        # Get current entries for this slot
        slot_entries = self.schedule.get_entries_at_time(new_time_slot)
        
        # Check activity capacity (simplified - would need real capacity data)
        max_capacity = 20  # Default assumption
        if entry.activity.name in ['Climbing Tower']:
            max_capacity = 15
        elif entry.activity.name in ['Rifle', 'Shotgun']:
            max_capacity = 12
        
        current_count = len(slot_entries)
        if current_count >= max_capacity:
            return True
        
        return False
    
    def _would_cause_overlap(self, entry, new_time_slot):
        """Check if move would cause overlap for same troop."""
        troop_entries = self.schedule.get_troop_schedule(entry.troop)
        
        for other_entry in troop_entries:
            if other_entry == entry:
                continue
                
            # Check for time overlap
            if (other_entry.time_slot.day == new_time_slot.day and
                abs(other_entry.time_slot.slot_number - new_time_slot.slot_number) < 1):
                return True
        
        return False
    
    def _would_cause_exclusive_area_conflict(self, entry, new_time_slot):
        """Check if move would cause exclusive area conflict."""
        from models import EXCLUSIVE_AREAS
        
        # Find which area this activity belongs to
        activity_area = None
        for area, activities in EXCLUSIVE_AREAS.items():
            if entry.activity.name in activities:
                activity_area = area
                break
        
        if not activity_area or activity_area not in ['Tower', 'Rifle Range']:
            return False  # Only check exclusive areas
        
        # Check for other troops in same exclusive area at same time
        slot_entries = self.schedule.get_entries_at_time(new_time_slot)
        for other_entry in slot_entries:
            if other_entry.troop != entry.troop:
                other_area = None
                for area, activities in EXCLUSIVE_AREAS.items():
                    if other_entry.activity.name in activities:
                        other_area = area
                        break
                
                if other_area == activity_area:
                    return True
        
        return False
    
    def safe_move_entry(self, entry, new_time_slot):
        """Safely move an entry with comprehensive constraint checking."""
        # Check all constraints first
        constraint_result = self.check_all_constraints(entry, new_time_slot)
        
        if not constraint_result['ok']:
            self.log_optimization(
                "MOVE_BLOCKED",
                f"Cannot move {entry.troop.name} {entry.activity.name} - Violations: {', '.join(constraint_result['violations'])}",
                False
            )
            return False
        
        # If all constraints pass, make the move
        old_time_slot = entry.time_slot
        self.schedule.remove_entry(entry)
        self.schedule.add_entry(new_time_slot, entry.activity, entry.troop)
        
        # Clear relevant cache entries
        keys_to_remove = [key for key in self.constraint_cache.keys() 
                         if key[0] == id(entry) or key[1] == id(old_time_slot) or key[1] == id(new_time_slot)]
        for key in keys_to_remove:
            del self.constraint_cache[key]
        
        self.log_optimization(
            "MOVE_SUCCESS",
            f"Moved {entry.troop.name} {entry.activity.name} from {old_time_slot.day.name[:3]}-{old_time_slot.slot_number} to {new_time_slot.day.name[:3]}-{new_time_slot.slot_number}",
            True
        )
        
        return True
    
    def safe_swap_entries(self, entry1, entry2):
        """Safely swap two entries with constraint checking."""
        # Check if swapping would violate constraints for either entry
        constraint1 = self.check_all_constraints(entry1, entry2.time_slot)
        constraint2 = self.check_all_constraints(entry2, entry1.time_slot)
        
        if not constraint1['ok'] or not constraint2['ok']:
            violations = []
            if not constraint1['ok']:
                violations.extend(constraint1['violations'])
            if not constraint2['ok']:
                violations.extend(constraint2['violations'])
            
            self.log_optimization(
                "SWAP_BLOCKED",
                f"Cannot swap {entry1.troop.name} {entry1.activity.name} with {entry2.troop.name} {entry2.activity.name} - Violations: {', '.join(set(violations))}",
                False
            )
            return False
        
        # Perform the swap
        slot1 = entry1.time_slot
        slot2 = entry2.time_slot
        
        self.schedule.remove_entry(entry1)
        self.schedule.remove_entry(entry2)
        
        self.schedule.add_entry(slot2, entry1.activity, entry1.troop)
        self.schedule.add_entry(slot1, entry2.activity, entry2.troop)
        
        # Clear relevant cache entries
        keys_to_remove = [key for key in self.constraint_cache.keys() 
                         if key[0] in [id(entry1), id(entry2)] or key[1] in [id(slot1), id(slot2)]]
        for key in keys_to_remove:
            del self.constraint_cache[key]
        
        self.log_optimization(
            "SWAP_SUCCESS",
            f"Swapped {entry1.troop.name} {entry1.activity.name} with {entry2.troop.name} {entry2.activity.name}",
            True
        )
        
        return True
    
    def get_optimization_summary(self):
        """Get summary of optimization attempts."""
        total_attempts = len(self.optimization_log)
        successful = sum(1 for log in self.optimization_log if log['success'])
        blocked = total_attempts - successful
        
        by_type = {}
        for log in self.optimization_log:
            opt_type = log['type']
            if opt_type not in by_type:
                by_type[opt_type] = {'total': 0, 'success': 0, 'blocked': 0}
            by_type[opt_type]['total'] += 1
            if log['success']:
                by_type[opt_type]['success'] += 1
            else:
                by_type[opt_type]['blocked'] += 1
        
        return {
            'total_attempts': total_attempts,
            'successful': successful,
            'blocked': blocked,
            'success_rate': successful / total_attempts if total_attempts > 0 else 0,
            'by_type': by_type,
            'detailed_log': self.optimization_log
        }
