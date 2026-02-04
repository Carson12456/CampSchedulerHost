"""
Unit tests for Activity entity
"""
import pytest
from dataclasses import FrozenInstanceError

from core.entities.activity import Activity, Zone


class TestActivity:
    """Test cases for Activity entity"""
    
    def test_activity_creation(self):
        """Test creating a basic activity"""
        activity = Activity(name="Archery", slots=1.0, zone=Zone.TOWER)
        assert activity.name == "Archery"
        assert activity.slots == 1.0
        assert activity.zone == Zone.TOWER
        assert activity.staff is None
        assert activity.conflicts_with == []
    
    def test_activity_with_staff(self):
        """Test creating activity with staff assignment"""
        activity = Activity(name="Dr. DNA", slots=1.0, zone=Zone.OUTDOOR_SKILLS, staff="Nature Director")
        assert activity.staff == "Nature Director"
    
    def test_activity_with_conflicts(self):
        """Test creating activity with conflicts"""
        activity = Activity(
            name="Troop Rifle", 
            slots=1.0, 
            zone=Zone.TOWER,
            conflicts_with=["Troop Shotgun", "Archery"]
        )
        assert len(activity.conflicts_with) == 2
        assert "Troop Shotgun" in activity.conflicts_with
    
    def test_activity_equality(self):
        """Test activity equality based on name"""
        activity1 = Activity(name="Archery", slots=1.0, zone=Zone.TOWER)
        activity2 = Activity(name="Archery", slots=1.5, zone=Zone.OUTDOOR_SKILLS)
        activity3 = Activity(name="Climbing Tower", slots=1.0, zone=Zone.TOWER)
        
        assert activity1 == activity2  # Same name
        assert activity1 != activity3  # Different name
        assert activity2 != activity3  # Different name
    
    def test_activity_hash(self):
        """Test activity is hashable for use in sets/dicts"""
        activity = Activity(name="Archery", slots=1.0, zone=Zone.TOWER)
        activity_set = {activity}
        assert len(activity_set) == 1
        
        # Same name should produce same hash
        activity2 = Activity(name="Archery", slots=1.5, zone=Zone.OUTDOOR_SKILLS)
        activity_set.add(activity2)
        assert len(activity_set) == 1  # Should be the same due to same name
    
    def test_activity_immutability(self):
        """Test that activity attributes can be modified (dataclass is not frozen)"""
        activity = Activity(name="Archery", slots=1.0, zone=Zone.TOWER)
        activity.staff = "Range Master"
        assert activity.staff == "Range Master"
    
    def test_activity_str_representation(self):
        """Test string representation of activity"""
        activity = Activity(name="Archery", slots=1.0, zone=Zone.TOWER)
        str_repr = str(activity)
        assert "Archery" in str_repr


class TestZone:
    """Test cases for Zone enum"""
    
    def test_zone_enum_values(self):
        """Test zone enum has correct values"""
        assert Zone.DELTA.value == "Delta"
        assert Zone.BEACH.value == "Beach"
        assert Zone.OUTDOOR_SKILLS.value == "Outdoor Skills"
        assert Zone.TOWER.value == "Tower"
        assert Zone.OFF_CAMP.value == "Off-camp"
        assert Zone.CAMPSITE.value == "Campsite"
    
    def test_zone_enum_iteration(self):
        """Test we can iterate over all zones"""
        zones = list(Zone)
        assert len(zones) == 6
        assert Zone.DELTA in zones
        assert Zone.BEACH in zones
