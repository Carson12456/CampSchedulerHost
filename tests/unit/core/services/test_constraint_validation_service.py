"""
Unit tests for Constraint Validation Service
"""
import pytest
from unittest.mock import Mock

from core.services.constraint_validation_service import ConstraintValidationService
from core.entities import Activity, Troop, TimeSlot, Day, Zone
from core.rules import ActivityRules, CapacityRules, SchedulingRules
from interfaces.repositories import TroopRepository, ScheduleRepository


class TestConstraintValidationService:
    """Test cases for Constraint Validation Service"""
    
    def test_service_initialization(self):
        """Test service can be initialized with repositories and rules"""
        troop_repo = Mock(spec=TroopRepository)
        schedule_repo = Mock(spec=ScheduleRepository)
        activity_rules = ActivityRules()
        capacity_rules = CapacityRules()
        scheduling_rules = SchedulingRules()
        
        service = ConstraintValidationService(
            troop_repo, schedule_repo, activity_rules, capacity_rules, scheduling_rules
        )
        
        assert service is not None
        assert service.troop_repository == troop_repo
        assert service.schedule_repository == schedule_repo
    
    def test_validate_activity_availability_basic(self):
        """Test basic activity availability validation"""
        service = self._create_service()
        time_slot = TimeSlot(Day.MONDAY, 1)
        activity = Activity("Archery", 1.0, Zone.TOWER)
        troop = Troop("Test Troop", "Site A", [])
        
        result = service.validate_activity_availability(time_slot, activity, troop)
        
        assert isinstance(result, bool)
    
    def test_validate_exclusive_area_conflict(self):
        """Test exclusive area conflict detection"""
        service = self._create_service()
        time_slot = TimeSlot(Day.MONDAY, 1)
        activity1 = Activity("Climbing Tower", 1.0, Zone.TOWER)
        activity2 = Activity("Knots and Lashings", 1.0, Zone.OUTDOOR_SKILLS)
        troop = Troop("Test Troop", "Site A", [])
        
        # These should not conflict (different exclusive areas)
        result = service.validate_exclusive_area_conflict(time_slot, activity1)
        assert result == True
    
    def test_validate_same_day_conflict(self):
        """Test same day conflict detection"""
        service = self._create_service()
        troop = Troop("Test Troop", "Site A", [])
        
        # This method only takes troop and activity
        result = service.validate_same_day_conflict(troop, Activity("Trading Post", 1.0, Zone.OUTDOOR_SKILLS))
        assert result == True  # Should be valid (no conflicts in empty schedule)
    
    def test_validate_beach_staff_capacity(self):
        """Test beach staff capacity validation"""
        service = self._create_service()
        time_slot = TimeSlot(Day.MONDAY, 1)
        
        # This method only takes time_slot and activity
        result = service.validate_beach_staff_capacity(time_slot, Activity("Sailing", 1.0, Zone.BEACH))
        assert result == True  # Should be allowed (empty schedule)
    
    def test_validate_accuracy_activity_limit(self):
        """Test accuracy activity per day limit"""
        service = self._create_service()
        troop = Troop("Test Troop", "Site A", [])
        
        # This method only takes troop, activity, and time_slot
        result = service.validate_accuracy_activity_limit(troop, Activity("Troop Shotgun", 1.0, Zone.TOWER), TimeSlot(Day.WEDNESDAY, 1))
        assert result == True  # Should be allowed (no existing accuracy activities)
    
    def test_validate_wet_dry_pattern(self):
        """Test wet/dry activity pattern validation"""
        service = self._create_service()
        troop = Troop("Test Troop", "Site A", [])
        
        # This method only takes troop, activity, and time_slot
        result = service.validate_wet_dry_pattern(troop, Activity("Aqua Trampoline", 1.0, Zone.BEACH), TimeSlot(Day.MONDAY, 2))
        assert result == True  # Should be valid (no previous activity)
    
    def test_validate_troop_availability(self):
        """Test troop availability in time slot"""
        service = self._create_service()
        time_slot = TimeSlot(Day.MONDAY, 1)
        troop = Troop("Test Troop", "Site A", [])
        
        # Mock empty schedule
        result = service.validate_troop_availability(time_slot, troop)
        assert result == True  # Should be available
    
    def test_validate_multi_slot_activity_continuity(self):
        """Test multi-slot activity continuity validation"""
        service = self._create_service()
        troop = Troop("Test Troop", "Site A", [])
        
        # This method only takes troop, activity, and time_slot
        result = service.validate_multi_slot_continuity(troop, Activity("Sailing", 1.5, Zone.BEACH), TimeSlot(Day.MONDAY, 1))
        assert result == True  # Should be valid (mocked empty schedule)
    
    def test_comprehensive_validation(self):
        """Test comprehensive validation with all constraints"""
        service = self._create_service()
        time_slot = TimeSlot(Day.MONDAY, 1)
        activity = Activity("Archery", 1.0, Zone.TOWER)
        troop = Troop("Test Troop", "Site A", [])
        
        result = service.validate_placement(time_slot, activity, troop)
        
        assert isinstance(result, dict)
        assert 'is_valid' in result
        assert 'violations' in result
        assert 'warnings' in result
    
    def _create_service(self):
        """Helper method to create service instance with mocked dependencies"""
        troop_repo = Mock(spec=TroopRepository)
        schedule_repo = Mock(spec=ScheduleRepository)
        activity_rules = ActivityRules()
        capacity_rules = CapacityRules()
        scheduling_rules = SchedulingRules()
        
        # Configure mocks to return empty lists by default
        schedule_repo.get_entries_for_time_slot.return_value = []
        schedule_repo.get_entries_for_troop.return_value = []
        schedule_repo.get_all_entries.return_value = []
        
        return ConstraintValidationService(
            troop_repo, schedule_repo, activity_rules, capacity_rules, scheduling_rules
        )
