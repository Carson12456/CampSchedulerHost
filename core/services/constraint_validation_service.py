"""
Constraint Validation Service for Summer Camp Scheduler
Business logic service for validating scheduling constraints
"""
from typing import List, Dict, Any, Optional, Tuple

from core.entities.activity import Activity
from core.entities.troop import Troop
from core.entities.time_slot import TimeSlot, Day
from core.entities.schedule_entry import ScheduleEntry

from core.rules.activity_rules import ActivityRules
from core.rules.capacity_rules import CapacityRules
from core.rules.scheduling_rules import SchedulingRules

from interfaces.repositories.troop_repository import TroopRepository
from interfaces.repositories.schedule_repository import ScheduleRepository


class ConstraintValidationService:
    """
    Service for validating scheduling constraints and business rules.
    
    This service encapsulates all constraint validation logic and uses
    repository interfaces to access data, following Clean Architecture principles.
    It depends on abstract interfaces rather than concrete implementations.
    """
    
    def __init__(
        self,
        troop_repository: TroopRepository,
        schedule_repository: ScheduleRepository,
        activity_rules: ActivityRules,
        capacity_rules: CapacityRules,
        scheduling_rules: SchedulingRules
    ):
        """
        Initialize the constraint validation service.
        
        Args:
            troop_repository: Repository for troop data access
            schedule_repository: Repository for schedule data access
            activity_rules: Business rules for activities
            capacity_rules: Business rules for capacity constraints
            scheduling_rules: Business rules for scheduling patterns
        """
        self.troop_repository = troop_repository
        self.schedule_repository = schedule_repository
        self.activity_rules = activity_rules
        self.capacity_rules = capacity_rules
        self.scheduling_rules = scheduling_rules
    
    def validate_placement(
        self, 
        time_slot: TimeSlot, 
        activity: Activity, 
        troop: Troop
    ) -> Dict[str, Any]:
        """
        Perform comprehensive validation for a potential placement.
        
        Args:
            time_slot: The time slot for the activity
            activity: The activity to be scheduled
            troop: The troop to be scheduled
            
        Returns:
            Dictionary with validation results:
            - is_valid: bool indicating if placement is valid
            - violations: List of constraint violations
            - warnings: List of potential issues
        """
        violations = []
        warnings = []
        
        # Check troop availability
        if not self.validate_troop_availability(time_slot, troop):
            violations.append("Troop not available in time slot")
        
        # Check activity availability
        if not self.validate_activity_availability(time_slot, activity, troop):
            violations.append("Activity not available in time slot")
        
        # Check exclusive area conflicts
        if not self.validate_exclusive_area_conflict(time_slot, activity):
            violations.append("Exclusive area conflict detected")
        
        # Check beach staff capacity
        if not self.validate_beach_staff_capacity(time_slot, activity):
            violations.append("Beach staff capacity exceeded")
        
        # Check same day conflicts
        if not self.validate_same_day_conflict(troop, activity):
            violations.append("Same day conflict detected")
        
        # Check accuracy activity limits
        if not self.validate_accuracy_activity_limit(troop, activity, time_slot):
            violations.append("Accuracy activity limit exceeded")
        
        # Check wet/dry patterns
        if not self.validate_wet_dry_pattern(troop, activity, time_slot):
            violations.append("Invalid wet/dry activity pattern")
        
        # Check multi-slot continuity
        if not self.validate_multi_slot_continuity(troop, activity, time_slot):
            violations.append("Multi-slot activity continuity issue")
        
        return {
            'is_valid': len(violations) == 0,
            'violations': violations,
            'warnings': warnings
        }
    
    def validate_activity_availability(
        self, 
        time_slot: TimeSlot, 
        activity: Activity, 
        requesting_troop: Troop
    ) -> bool:
        """
        Validate if an activity is available in a time slot.
        
        Args:
            time_slot: The time slot to check
            activity: The activity to check
            requesting_troop: The troop requesting the activity
            
        Returns:
            True if activity is available, False otherwise
        """
        # Get existing entries for the time slot
        existing_entries = self.schedule_repository.get_entries_for_time_slot(time_slot)
        
        for entry in existing_entries:
            # Check if same activity is already booked (non-shareable)
            if entry.activity.name == activity.name:
                # Special cases for shareable activities
                if activity.name == "Water Polo":
                    # Allow up to 2 troops for Water Polo
                    polo_count = sum(1 for e in existing_entries if e.activity.name == "Water Polo")
                    if polo_count < 2:
                        continue
                
                return False
            
            # Check exclusive area conflicts
            if self.activity_rules.are_activities_same_exclusive_area(
                activity.name, entry.activity.name
            ):
                return False
            
            # Check explicit conflicts
            if (activity.name in entry.activity.conflicts_with or
                entry.activity.name in activity.conflicts_with):
                return False
        
        # Check beach staff capacity
        if self.capacity_rules.is_beach_staff_activity(activity.name):
            beach_count = sum(1 for e in existing_entries 
                           if self.capacity_rules.is_beach_staff_activity(e.activity.name))
            if not self.capacity_rules.can_add_beach_staff_activity(beach_count):
                return False
        
        return True
    
    def validate_exclusive_area_conflict(
        self, 
        time_slot: TimeSlot, 
        activity: Activity
    ) -> bool:
        """
        Validate if activity conflicts with exclusive area usage.
        
        Args:
            time_slot: The time slot to check
            activity: The activity to validate
            
        Returns:
            True if no conflict, False if conflict exists
        """
        if not self.activity_rules.is_activity_exclusive(activity.name):
            return True
        
        existing_entries = self.schedule_repository.get_entries_for_time_slot(time_slot)
        activity_area = self.activity_rules.get_exclusive_area_for_activity(activity.name)
        
        for entry in existing_entries:
            entry_area = self.activity_rules.get_exclusive_area_for_activity(entry.activity.name)
            if entry_area == activity_area:
                return False
        
        return True
    
    def validate_same_day_conflict(self, troop: Troop, activity: Activity) -> bool:
        """
        Validate if activity conflicts with troop's same-day activities.
        
        Args:
            troop: The troop to check
            activity: The activity to validate
            
        Returns:
            True if no conflict, False if conflict exists
        """
        troop_entries = self.schedule_repository.get_entries_for_troop(troop)
        
        for entry in troop_entries:
            if self.activity_rules.have_same_day_conflict(activity.name, entry.activity.name):
                return False
        
        return True
    
    def validate_beach_staff_capacity(
        self, 
        time_slot: TimeSlot, 
        activity: Activity
    ) -> bool:
        """
        Validate if beach staff activity can be added to time slot.
        
        Args:
            time_slot: The time slot to check
            activity: The activity to validate
            
        Returns:
            True if capacity allows, False if exceeded
        """
        if not self.capacity_rules.is_beach_staff_activity(activity.name):
            return True
        
        existing_entries = self.schedule_repository.get_entries_for_time_slot(time_slot)
        beach_count = sum(1 for e in existing_entries 
                       if self.capacity_rules.is_beach_staff_activity(e.activity.name))
        
        return self.capacity_rules.can_add_beach_staff_activity(beach_count)
    
    def validate_accuracy_activity_limit(
        self, 
        troop: Troop, 
        activity: Activity, 
        time_slot: TimeSlot
    ) -> bool:
        """
        Validate if accuracy activity exceeds daily limit.
        
        Args:
            troop: The troop to check
            activity: The activity to validate
            time_slot: The time slot for the activity
            
        Returns:
            True if within limit, False if exceeded
        """
        if not self.activity_rules.is_accuracy_activity(activity.name):
            return True
        
        troop_entries = self.schedule_repository.get_entries_for_troop(troop)
        accuracy_count = sum(1 for e in troop_entries 
                           if e.time_slot.day == time_slot.day
                           and self.activity_rules.is_accuracy_activity(e.activity.name))
        
        return accuracy_count < 1  # Max 1 accuracy activity per day
    
    def validate_wet_dry_pattern(
        self, 
        troop: Troop, 
        activity: Activity, 
        time_slot: TimeSlot
    ) -> bool:
        """
        Validate wet/dry activity pattern constraints.
        
        Args:
            troop: The troop to check
            activity: The activity to validate
            time_slot: The time slot for the activity
            
        Returns:
            True if pattern is valid, False if invalid
        """
        if not self.activity_rules.is_wet_activity(activity.name):
            return True
        
        # Check previous slot for tower/ODS activities
        previous_slot = time_slot.get_previous_slot()
        if previous_slot:
            previous_entries = self.schedule_repository.get_entries_for_troop(troop)
            for entry in previous_entries:
                if (entry.time_slot == previous_slot and 
                    self.activity_rules.is_tower_ods_activity(entry.activity.name)):
                    return False
        
        return True
    
    def validate_multi_slot_continuity(
        self, 
        troop: Troop, 
        activity: Activity, 
        time_slot: TimeSlot
    ) -> bool:
        """
        Validate multi-slot activity continuity requirements.
        
        Args:
            troop: The troop to check
            activity: The activity to validate
            time_slot: The starting time slot
            
        Returns:
            True if continuity is valid, False if invalid
        """
        if not activity.is_multi_slot():
            return True
        
        # Check if required consecutive slots are available
        slots_needed = activity.get_duration_in_slots()
        all_slots = self.schedule_repository.get_all_entries()
        
        for offset in range(1, slots_needed):
            next_slot = time_slot.get_next_slot()
            if not next_slot:
                return False
            
            # Check if troop is available in next slot
            if not self.validate_troop_availability(next_slot, troop):
                return False
            
            # Check if next slot is on same day
            if next_slot.day != time_slot.day:
                return False
        
        return True
    
    def validate_troop_availability(self, time_slot: TimeSlot, troop: Troop) -> bool:
        """
        Validate if troop is available in the specified time slot.
        
        Args:
            time_slot: The time slot to check
            troop: The troop to validate
            
        Returns:
            True if available, False if already scheduled
        """
        troop_entries = self.schedule_repository.get_entries_for_troop(troop)
        
        for entry in troop_entries:
            if entry.time_slot == time_slot:
                return False
        
        return True
    
    def get_constraint_violations(self, troop: Troop) -> List[Dict[str, Any]]:
        """
        Get all constraint violations for a troop's schedule.
        
        Args:
            troop: The troop to analyze
            
        Returns:
            List of violation details
        """
        violations = []
        troop_entries = self.schedule_repository.get_entries_for_troop(troop)
        
        for entry in troop_entries:
            # Check each entry for various violations
            validation_result = self.validate_placement(
                entry.time_slot, entry.activity, troop
            )
            
            if not validation_result['is_valid']:
                violations.append({
                    'time_slot': entry.time_slot,
                    'activity': entry.activity.name,
                    'violations': validation_result['violations']
                })
        
        return violations
