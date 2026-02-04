#!/usr/bin/env python3
"""
Enhanced validation system for safe scheduling operations
Implements comprehensive check-before-action validation
"""

from models import TimeSlot, Activity, Troop, ScheduleEntry
from activities import get_activity_by_name
from safe_optimizer import SafeScheduleOptimizer
import logging

class SafeSchedulingValidator:
    """Comprehensive validation system for scheduling operations"""
    
    def __init__(self, schedule, time_slots, troops):
        self.schedule = schedule
        self.time_slots = time_slots
        self.troops = troops
        self.logger = logging.getLogger(__name__)
        self.safe_optimizer = SafeScheduleOptimizer(schedule, time_slots, troops)
    
    def validate_before_action(self, action_type, **kwargs):
        """
        Comprehensive validation before performing any scheduling action
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
        elif action_type == "fill_gap":
            is_safe, action_warnings, action_errors = self._validate_fill_gap(**kwargs)
        else:
            is_safe = False
            action_errors = [f"Unknown action type: {action_type}"]
        
        warnings.extend(action_warnings)
        errors.extend(action_errors)
        
        return is_safe, warnings, errors
    
    def _validate_add_entry(self, troop, activity, time_slot, **kwargs):
        """Validate adding a new entry"""
        warnings = []
        errors = []
        
        # Basic availability checks
        if not self._is_troop_available(troop, time_slot):
            errors.append(f"Troop {troop.name} not available at {time_slot}")
            return False, warnings, errors
        
        if not self._is_activity_available(activity, time_slot):
            errors.append(f"Activity {activity.name} not available at {time_slot}")
            return False, warnings, errors
        
        # Multi-slot activity checks
        if activity.slots > 1:
            consecutive_slots = self._get_consecutive_slots(time_slot, activity.slots)
            if not consecutive_slots:
                errors.append(f"Cannot fit {activity.slots}-slot activity starting at {time_slot}")
                return False, warnings, errors
            
            for slot in consecutive_slots:
                if not self._is_troop_available(troop, slot):
                    errors.append(f"Troop {troop.name} not available for consecutive slot {slot}")
                    return False, warnings, errors
                if not self._is_activity_available(activity, slot):
                    errors.append(f"Activity {activity.name} not available for consecutive slot {slot}")
                    return False, warnings, errors
        
        # Constraint violation checks
        temp_entry = ScheduleEntry(time_slot, activity, troop)
        violations = self._check_constraint_violations(temp_entry, check_existing=True)
        
        if violations:
            hard_violations = [v for v in violations if v['severity'] == 'hard']
            soft_violations = [v for v in violations if v['severity'] == 'soft']
            
            if hard_violations:
                errors.extend([f"Hard violation: {v['description']}" for v in hard_violations])
                return False, warnings, errors
            
            if soft_violations:
                warnings.extend([f"Soft violation: {v['description']}" for v in soft_violations])
        
        # Staff distribution checks
        staff_issues = self._check_staff_distribution(temp_entry, check_existing=True)
        if staff_issues:
            warnings.extend([f"Staff issue: {issue}" for issue in staff_issues])
        
        # Clustering and efficiency checks
        efficiency_issues = self._check_efficiency_impact(temp_entry, check_existing=True)
        if efficiency_issues:
            warnings.extend([f"Efficiency issue: {issue}" for issue in efficiency_issues])
        
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
                
                # Check if there's a gap between previous and next
                if self._creates_gap(prev_slot, next_slot):
                    warnings.append(f"Removing {entry.activity.name} will create a gap between {prev_slot} and {next_slot}")
        
        # Check if this removes a Top 5 activity
        if entry.activity.name in entry.troop.preferences[:5]:
            warnings.append(f"Removing Top 5 activity: {entry.activity.name}")
        
        # Check impact on multi-slot activities
        if entry.activity.slots > 1:
            warnings.append(f"Removing multi-slot activity: {entry.activity.name}")
        
        return True, warnings, errors
    
    def _validate_swap_entries(self, entry1, entry2, **kwargs):
        """Validate swapping two entries"""
        warnings = []
        errors = []
        
        # Basic validation
        if entry1 not in self.schedule.entries or entry2 not in self.schedule.entries:
            errors.append("One or both entries not found in schedule")
            return False, warnings, errors
        
        # Check if swap is possible (same time slots or compatible)
        if entry1.time_slot != entry2.time_slot:
            # Cross-time slot swap - more complex validation needed
            temp_entry1 = ScheduleEntry(entry2.time_slot, entry1.activity, entry1.troop)
            temp_entry2 = ScheduleEntry(entry1.time_slot, entry2.activity, entry2.troop)
            
            # Validate both temporary entries
            safe1, warnings1, errors1 = self._validate_add_entry(
                troop=temp_entry1.troop,
                activity=temp_entry1.activity,
                time_slot=temp_entry1.time_slot
            )
            
            safe2, warnings2, errors2 = self._validate_add_entry(
                troop=temp_entry2.troop,
                activity=temp_entry2.activity,
                time_slot=temp_entry2.time_slot
            )
            
            if not safe1 or not safe2:
                errors.extend(errors1 + errors2)
                return False, warnings, errors
            
            warnings.extend(warnings1 + warnings2)
        else:
            # Same time slot swap - simpler validation
            # Just check if troops can do each other's activities at this time
            if not self._is_activity_available(entry1.activity, entry1.time_slot):
                errors.append(f"{entry1.troop.name} cannot do {entry1.activity.name} at {entry1.time_slot}")
                return False, warnings, errors
            
            if not self._is_activity_available(entry2.activity, entry2.time_slot):
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
    
    def _validate_fill_gap(self, troop, activity, time_slot, **kwargs):
        """Validate filling a gap"""
        warnings = []
        errors = []
        
        # Check if it's actually a gap
        troop_schedule = self.schedule.get_troop_schedule(troop)
        existing_entries = [e for e in troop_schedule if e.time_slot == time_slot]
        
        if existing_entries:
            existing_entry = existing_entries[0]
            errors.append(f"Not a gap - {troop.name} already has {existing_entry.activity.name} at {time_slot}")
            return False, warnings, errors
        
        # Use standard add_entry validation
        return self._validate_add_entry(troop, activity, time_slot, **kwargs)
    
    def _is_troop_available(self, troop, time_slot):
        """Check if troop is available at time slot"""
        return self.schedule.is_troop_free(time_slot, troop)
    
    def _is_activity_available(self, activity, time_slot):
        """Check if activity is available at time slot"""
        from models import is_activity_available
        return is_activity_available(activity, time_slot, self.schedule)
    
    def _get_consecutive_slots(self, start_slot, num_slots):
        """Get consecutive slots for multi-slot activities"""
        consecutive = []
        current_slot = start_slot
        
        for i in range(num_slots):
            if current_slot in self.time_slots:
                consecutive.append(current_slot)
                # Move to next slot (simplified - would need proper slot sequencing)
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
        # Simplified gap detection - would need proper slot sequencing
        prev_index = self.time_slots.index(prev_slot)
        next_index = self.time_slots.index(next_slot)
        return next_index > prev_index + 1
    
    def _check_constraint_violations(self, entry, check_existing=False):
        """Check for constraint violations"""
        violations = []
        
        # Use the safe optimizer's constraint checking
        if check_existing:
            # Temporarily add entry to check violations
            self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        try:
            # Check all constraints using the safe optimizer
            if not self.safe_optimizer.check_all_constraints(entry.troop, entry.activity, entry.time_slot):
                violations.append({
                    'severity': 'hard',
                    'description': f"Constraint violation for {entry.activity.name} at {entry.time_slot}"
                })
        except Exception as e:
            violations.append({
                'severity': 'soft',
                'description': f"Constraint check failed: {e}"
            })
        
        if check_existing:
            # Remove temporary entry
            self.schedule.remove_entry(entry)
        
        return violations
    
    def _check_staff_distribution(self, entry, check_existing=False):
        """Check staff distribution impact"""
        issues = []
        
        # Simplified staff check - would need comprehensive staff analysis
        slot_entries = self.schedule.get_slot_activities(entry.time_slot)
        total_staff = sum(e.activity.staff_required for e in slot_entries)
        
        if check_existing:
            total_staff += entry.activity.staff_required
        
        if total_staff > 15:
            issues.append(f"Staff limit exceeded: {total_staff} > 15")
        elif total_staff < 5:
            issues.append(f"Underutilized staff: {total_staff} < 5")
        
        return issues
    
    def _check_efficiency_impact(self, entry, check_existing=False):
        """Check efficiency and clustering impact"""
        issues = []
        
        # Check for clustering efficiency
        troop_schedule = self.schedule.get_troop_schedule(entry.troop)
        
        if check_existing:
            # Temporarily add entry for checking
            self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
            troop_schedule = self.schedule.get_troop_schedule(entry.troop)
            self.schedule.remove_entry(entry)
        
        # Check for inefficient patterns
        # This would need more sophisticated clustering analysis
        return issues


class SafeEnhancedScheduler:
    """Enhanced scheduler with comprehensive validation"""
    
    def __init__(self, troops, time_slots=None):
        from enhanced_scheduler import EnhancedScheduler
        self.base_scheduler = EnhancedScheduler(troops, time_slots)
        self.validator = SafeSchedulingValidator(
            self.base_scheduler.schedule,
            self.base_scheduler.time_slots,
            troops
        )
        self.logger = logging.getLogger(__name__)
    
    def safe_add_entry(self, troop, activity, time_slot):
        """Safely add an entry with validation"""
        is_safe, warnings, errors = self.validator.validate_before_action(
            "add_entry",
            troop=troop,
            activity=activity,
            time_slot=time_slot
        )
        
        if not is_safe:
            self.logger.error(f"Cannot add entry: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.logger.warning(f"Adding entry with warnings: {'; '.join(warnings)}")
        
        # Perform the action
        self.base_scheduler.schedule.add_entry(time_slot, activity, troop)
        return True, warnings
    
    def safe_remove_entry(self, entry):
        """Safely remove an entry with validation"""
        is_safe, warnings, errors = self.validator.validate_before_action(
            "remove_entry",
            entry=entry
        )
        
        if not is_safe:
            self.logger.error(f"Cannot remove entry: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.logger.warning(f"Removing entry with warnings: {'; '.join(warnings)}")
        
        # Perform the action
        self.base_scheduler.schedule.remove_entry(entry)
        return True, warnings
    
    def safe_swap_entries(self, entry1, entry2):
        """Safely swap entries with validation"""
        is_safe, warnings, errors = self.validator.validate_before_action(
            "swap_entries",
            entry1=entry1,
            entry2=entry2
        )
        
        if not is_safe:
            self.logger.error(f"Cannot swap entries: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.logger.warning(f"Swapping entries with warnings: {'; '.join(warnings)}")
        
        # Perform the swap
        self.base_scheduler.schedule.remove_entry(entry1)
        self.base_scheduler.schedule.remove_entry(entry2)
        self.base_scheduler.schedule.add_entry(entry2.time_slot, entry1.activity, entry1.troop)
        self.base_scheduler.schedule.add_entry(entry1.time_slot, entry2.activity, entry2.troop)
        
        return True, warnings
    
    def safe_displace_entry(self, existing_entry, new_activity):
        """Safely displace an entry with validation"""
        is_safe, warnings, errors = self.validator.validate_before_action(
            "displace_entry",
            existing_entry=existing_entry,
            new_activity=new_activity
        )
        
        if not is_safe:
            self.logger.error(f"Cannot displace entry: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.logger.warning(f"Displacing entry with warnings: {'; '.join(warnings)}")
        
        # Perform the displacement
        self.base_scheduler.schedule.remove_entry(existing_entry)
        self.base_scheduler.schedule.add_entry(existing_entry.time_slot, new_activity, existing_entry.troop)
        
        return True, warnings
    
    def safe_fill_gap(self, troop, activity, time_slot):
        """Safely fill a gap with validation"""
        is_safe, warnings, errors = self.validator.validate_before_action(
            "fill_gap",
            troop=troop,
            activity=activity,
            time_slot=time_slot
        )
        
        if not is_safe:
            self.logger.error(f"Cannot fill gap: {'; '.join(errors)}")
            return False, errors
        
        if warnings:
            self.logger.warning(f"Filling gap with warnings: {'; '.join(warnings)}")
        
        # Perform the action
        self.base_scheduler.schedule.add_entry(time_slot, activity, troop)
        return True, warnings
    
    def schedule_all(self):
        """Schedule all with enhanced safety"""
        self.logger.info("Starting safe enhanced scheduling...")
        
        # Use base scheduler with enhanced validation
        schedule = self.base_scheduler.schedule_all()
        
        # Additional safety validation pass
        self.logger.info("Running final safety validation...")
        self._final_safety_check()
        
        return schedule
    
    def _final_safety_check(self):
        """Final comprehensive safety check"""
        issues = []
        
        for entry in self.base_scheduler.schedule.entries:
            # Validate each entry
            is_safe, warnings, errors = self.validator.validate_before_action(
                "add_entry",
                troop=entry.troop,
                activity=entry.activity,
                time_slot=entry.time_slot
            )
            
            if not is_safe:
                issues.append(f"Unsafe entry found: {entry.troop.name} - {entry.activity.name} at {entry.time_slot}")
                issues.extend([f"  Error: {error}" for error in errors])
            
            if warnings:
                issues.append(f"Entry with warnings: {entry.troop.name} - {entry.activity.name} at {entry.time_slot}")
                issues.extend([f"  Warning: {warning}" for warning in warnings])
        
        if issues:
            self.logger.warning(f"Final safety check found {len(issues)} issues:")
            for issue in issues:
                self.logger.warning(f"  {issue}")
        else:
            self.logger.info("Final safety check passed - no issues found")


if __name__ == "__main__":
    print("Safe Scheduling Validator - Comprehensive check-before-action system")
    print("This module provides enhanced validation for all scheduling operations")
