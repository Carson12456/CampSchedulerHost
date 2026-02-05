#!/usr/bin/env python3
"""
Smart validation system for safe scheduling operations
Focuses on preventing NEW problems while allowing existing schedules
"""

from models import TimeSlot, Activity, Troop, ScheduleEntry
from activities import get_activity_by_name
import logging

class SmartSchedulingValidator:
    """Smart validator that prevents creating new problems"""
    
    def __init__(self, schedule, time_slots, troops):
        self.schedule = schedule
        self.time_slots = time_slots
        self.troops = troops
        self.logger = logging.getLogger(__name__)
    
    def validate_action(self, action_type, **kwargs):
        """
        Validate an action to ensure it doesn't create new problems
        Returns (is_safe, warnings, errors)
        """
        warnings = []
        errors = []
        
        if action_type == "add_entry":
            is_safe, action_warnings, action_errors = self._validate_add_entry(**kwargs)
        elif action_type == "remove_entry":
            is_safe, action_warnings, action_errors = self._validate_remove_entry(**kwargs)
        elif action_type == "swap_entries":
            is_safe, action_warnings, action_errors = self._validate_swap_entries(**kwargs)
        elif action_type == "displace_entry":
            is_safe, action_warnings, action_errors = self._validate_displace_entry(**kwargs)
        else:
            is_safe = False
            action_errors = [f"Unknown action type: {action_type}"]
        
        warnings.extend(action_warnings)
        errors.extend(action_errors)
        
        return is_safe, warnings, errors
    
    def _validate_add_entry(self, troop, activity, time_slot, **kwargs):
        """Validate adding a new entry - focus on NEW problems"""
        warnings = []
        errors = []
        
        # Basic availability checks
        if not self.schedule.is_troop_free(time_slot, troop):
            errors.append(f"Troop {troop.name} not available at {time_slot}")
            return False, warnings, errors
        
        if not self.schedule.is_activity_available(activity, time_slot, troop):
            errors.append(f"Activity {activity.name} not available at {time_slot}")
            return False, warnings, errors
        
        # Multi-slot activity checks
        if activity.slots > 1:
            consecutive_slots = self._get_consecutive_slots(time_slot, activity.slots)
            if not consecutive_slots:
                errors.append(f"Cannot fit {activity.slots}-slot activity starting at {time_slot}")
                return False, warnings, errors
            
            for slot in consecutive_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    errors.append(f"Troop {troop.name} not available for consecutive slot {slot}")
                    return False, warnings, errors
                if not self.schedule.is_activity_available(activity, slot, troop):
                    errors.append(f"Activity {activity.name} not available for consecutive slot {slot}")
                    return False, warnings, errors
        
        # Check for CRITICAL constraint violations only (hard violations)
        critical_violations = self._check_critical_violations(troop, activity, time_slot)
        if critical_violations:
            errors.extend([f"Critical violation: {v}" for v in critical_violations])
            return False, warnings, errors
        
        # Check for soft violations (warnings only)
        soft_violations = self._check_soft_violations(troop, activity, time_slot)
        if soft_violations:
            warnings.extend([f"Soft violation: {v}" for v in soft_violations])
        
        # Staff distribution checks
        staff_issues = self._check_staff_impact(troop, activity, time_slot)
        if staff_issues:
            warnings.extend([f"Staff issue: {issue}" for issue in staff_issues])
        
        return True, warnings, errors
    
    def _validate_remove_entry(self, entry, **kwargs):
        """Validate removing an entry"""
        warnings = []
        errors = []
        
        # Check if entry exists
        if entry not in self.schedule.entries:
            errors.append("Entry not found in schedule")
            return False, warnings, errors
        
        # Check if removal creates gaps
        troop_schedule = self.schedule.get_troop_schedule(entry.troop)
        troop_entries = sorted(troop_schedule, key=lambda e: e.time_slot)
        
        entry_index = troop_entries.index(entry)
        
        # Check if this creates isolated gaps
        if len(troop_entries) > 1:
            if entry_index > 0 and entry_index < len(troop_entries) - 1:
                prev_slot = troop_entries[entry_index - 1].time_slot
                next_slot = troop_entries[entry_index + 1].time_slot
                
                if self._creates_gap(prev_slot, next_slot):
                    warnings.append(f"Removing {entry.activity.name} will create a gap between {prev_slot} and {next_slot}")
        
        # Check if this removes a Top 5 activity
        if entry.activity.name in entry.troop.preferences[:5]:
            warnings.append(f"Removing Top 5 activity: {entry.activity.name}")
        
        return True, warnings, errors
    
    def _validate_swap_entries(self, entry1, entry2, **kwargs):
        """Validate swapping two entries"""
        warnings = []
        errors = []
        
        # Basic validation
        if entry1 not in self.schedule.entries or entry2 not in self.schedule.entries:
            errors.append("One or both entries not found in schedule")
            return False, warnings, errors
        
        # Check if swap is possible
        if entry1.time_slot != entry2.time_slot:
            # Cross-time slot swap
            # Validate both temporary entries
            safe1, warnings1, errors1 = self._validate_add_entry(
                troop=entry1.troop,
                activity=entry1.activity,
                time_slot=entry2.time_slot
            )
            
            safe2, warnings2, errors2 = self._validate_add_entry(
                troop=entry2.troop,
                activity=entry2.activity,
                time_slot=entry1.time_slot
            )
            
            if not safe1 or not safe2:
                errors.extend(errors1 + errors2)
                return False, warnings, errors
            
            warnings.extend(warnings1 + warnings2)
        else:
            # Same time slot swap - simpler validation
            if not self.schedule.is_activity_available(entry1.activity, entry1.time_slot, entry1.troop):
                errors.append(f"{entry1.troop.name} cannot do {entry1.activity.name} at {entry1.time_slot}")
                return False, warnings, errors
            
            if not self.schedule.is_activity_available(entry2.activity, entry2.time_slot, entry2.troop):
                errors.append(f"{entry2.troop.name} cannot do {entry2.activity.name} at {entry2.time_slot}")
                return False, warnings, errors
        
        # Check Top 5 impact
        for entry in [entry1, entry2]:
            if entry.activity.name in entry.troop.preferences[:5]:
                warnings.append(f"Swap affects Top 5 activity: {entry.activity.name} for {entry.troop.name}")
        
        return True, warnings, errors
    
    def _validate_displace_entry(self, existing_entry, new_activity, **kwargs):
        """Validate displacing an existing entry with a new activity"""
        warnings = []
        errors = []
        
        # First validate removing the existing entry
        safe_remove, remove_warnings, remove_errors = self._validate_remove_entry(existing_entry)
        if not safe_remove:
            errors.extend(remove_errors)
            return False, warnings, errors
        
        warnings.extend(remove_warnings)
        
        # Then validate adding the new activity
        safe_add, add_warnings, add_errors = self._validate_add_entry(
            troop=existing_entry.troop,
            activity=new_activity,
            time_slot=existing_entry.time_slot
        )
        
        if not safe_add:
            errors.extend(add_errors)
            return False, warnings, errors
        
        warnings.extend(add_warnings)
        
        # Additional displacement-specific checks
        if existing_entry.activity.name in existing_entry.troop.preferences[:5]:
            if new_activity.name not in existing_entry.troop.preferences[:5]:
                warnings.append(f"Displacing Top 5 activity {existing_entry.activity.name} with lower priority {new_activity.name}")
        
        return True, warnings, errors
    
    def _get_consecutive_slots(self, start_slot, num_slots):
        """Get consecutive slots for multi-slot activities"""
        consecutive = []
        current_slot = start_slot
        
        for i in range(num_slots):
            if current_slot in self.time_slots:
                consecutive.append(current_slot)
                # Move to next slot
                current_index = self.time_slots.index(current_slot)
                if current_index + 1 < len(self.time_slots):
                    current_slot = self.time_slots[current_index + 1]
                else:
                    return None
            else:
                return None
        
        return consecutive
    
    def _creates_gap(self, prev_slot, next_slot):
        """Check if removing an entry creates a gap"""
        prev_index = self.time_slots.index(prev_slot)
        next_index = self.time_slots.index(next_slot)
        return next_index > prev_index + 1
    
    def _check_critical_violations(self, troop, activity, time_slot):
        """Check for critical (hard) constraint violations"""
        violations = []
        
        # Check exclusive area conflicts
        from models import EXCLUSIVE_AREAS
        activity_area = None
        for area, activities in EXCLUSIVE_AREAS.items():
            if activity.name in activities:
                activity_area = area
                break
        
        if activity_area:
            slot_entries = self.schedule.get_slot_activities(time_slot)
            for entry in slot_entries:
                for area, activities in EXCLUSIVE_AREAS.items():
                    if area == activity_area and entry.activity.name in activities:
                        violations.append(f"Exclusive area conflict: {activity.name} and {entry.activity.name} in {area}")
        
        # Check explicit conflicts
        slot_entries = self.schedule.get_slot_activities(time_slot)
        for entry in slot_entries:
            if activity.name in entry.activity.conflicts_with:
                violations.append(f"Explicit conflict: {activity.name} conflicts with {entry.activity.name}")
            if entry.activity.name in activity.conflicts_with:
                violations.append(f"Explicit conflict: {entry.activity.name} conflicts with {activity.name}")
        
        return violations
    
    def _check_soft_violations(self, troop, activity, time_slot):
        """Check for soft violations (warnings only)"""
        violations = []
        
        # Check beach slot violations
        from models import BEACH_STAFF_ACTIVITIES
        if activity.name in BEACH_STAFF_ACTIVITIES:
            if time_slot.slot_number == 2:  # Beach slot 2 is problematic
                violations.append(f"Beach activity {activity.name} in slot 2")
        
        # Check accuracy activity conflicts
        accuracy_activities = ["Archery", "Rifle", "Shotgun"]
        if activity.name in accuracy_activities:
            slot_entries = self.schedule.get_slot_activities(time_slot)
            for entry in slot_entries:
                if entry.activity.name in accuracy_activities and entry.activity.name != activity.name:
                    violations.append(f"Multiple accuracy activities: {activity.name} and {entry.activity.name}")
        
        return violations
    
    def _check_staff_impact(self, troop, activity, time_slot):
        """Check staff distribution impact"""
        issues = []
        
        slot_entries = self.schedule.get_slot_activities(time_slot)
        total_staff = sum(e.activity.staff_required for e in slot_entries) + activity.staff_required
        
        if total_staff > 15:
            issues.append(f"Staff limit exceeded: {total_staff} > 15")
        elif total_staff < 5:
            issues.append(f"Underutilized staff: {total_staff} < 5")
        
        return issues


class SmartSafeScheduler:
    """Scheduler with smart validation that prevents new problems"""
    
    def __init__(self, troops, time_slots=None):
        from enhanced_scheduler import EnhancedScheduler
        self.base_scheduler = EnhancedScheduler(troops, time_slots)
        self.validator = SmartSchedulingValidator(
            self.base_scheduler.schedule,
            self.base_scheduler.time_slots,
            troops
        )
        self.logger = logging.getLogger(__name__)
        self.operations_safe = 0
        self.operations_blocked = 0
        self.operations_warned = 0
    
    def safe_add_entry(self, troop, activity, time_slot):
        """Safely add an entry with validation"""
        is_safe, warnings, errors = self.validator.validate_action(
            "add_entry",
            troop=troop,
            activity=activity,
            time_slot=time_slot
        )
        
        if not is_safe:
            self.operations_blocked += 1
            self.logger.debug(f"Add entry blocked: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.operations_warned += 1
            self.logger.debug(f"Add entry warned: {'; '.join(warnings)}")
        
        # Perform the action
        self.base_scheduler.schedule.add_entry(time_slot, activity, troop)
        self.operations_safe += 1
        return True, warnings
    
    def safe_remove_entry(self, entry):
        """Safely remove an entry with validation"""
        is_safe, warnings, errors = self.validator.validate_action(
            "remove_entry",
            entry=entry
        )
        
        if not is_safe:
            self.operations_blocked += 1
            self.logger.debug(f"Remove entry blocked: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.operations_warned += 1
            self.logger.debug(f"Remove entry warned: {'; '.join(warnings)}")
        
        # Perform the action
        self.base_scheduler.schedule.remove_entry(entry)
        self.operations_safe += 1
        return True, warnings
    
    def safe_swap_entries(self, entry1, entry2):
        """Safely swap entries with validation"""
        is_safe, warnings, errors = self.validator.validate_action(
            "swap_entries",
            entry1=entry1,
            entry2=entry2
        )
        
        if not is_safe:
            self.operations_blocked += 1
            self.logger.debug(f"Swap entries blocked: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.operations_warned += 1
            self.logger.debug(f"Swap entries warned: {'; '.join(warnings)}")
        
        # Perform the swap
        self.base_scheduler.schedule.remove_entry(entry1)
        self.base_scheduler.schedule.remove_entry(entry2)
        self.base_scheduler.schedule.add_entry(entry2.time_slot, entry1.activity, entry1.troop)
        self.base_scheduler.schedule.add_entry(entry1.time_slot, entry2.activity, entry2.troop)
        self.operations_safe += 1
        return True, warnings
    
    def safe_displace_entry(self, existing_entry, new_activity):
        """Safely displace an entry with validation"""
        is_safe, warnings, errors = self.validator.validate_action(
            "displace_entry",
            existing_entry=existing_entry,
            new_activity=new_activity
        )
        
        if not is_safe:
            self.operations_blocked += 1
            self.logger.debug(f"Displace entry blocked: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.operations_warned += 1
            self.logger.debug(f"Displace entry warned: {'; '.join(warnings)}")
        
        # Perform the displacement
        self.base_scheduler.schedule.remove_entry(existing_entry)
        self.base_scheduler.schedule.add_entry(existing_entry.time_slot, new_activity, existing_entry.troop)
        self.operations_safe += 1
        return True, warnings
    
    def schedule_all(self):
        """Schedule all with smart safety"""
        self.logger.info("Starting smart safe scheduling...")
        
        # Use base scheduler
        schedule = self.base_scheduler.schedule_all()
        
        # Log statistics
        self.logger.info(f"Smart safe scheduling complete:")
        self.logger.info(f"  Safe operations: {self.operations_safe}")
        self.logger.info(f"  Blocked operations: {self.operations_blocked}")
        self.logger.info(f"  Warned operations: {self.operations_warned}")
        
        return schedule


if __name__ == "__main__":
    print("Smart Scheduling Validator - Prevents new problems while allowing existing schedules")
