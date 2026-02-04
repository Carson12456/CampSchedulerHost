"""
Unit tests for Activity Rules
"""
import pytest

from core.rules.activity_rules import ActivityRules


class TestActivityRules:
    """Test cases for Activity Rules"""
    
    def test_get_exclusive_areas(self):
        """Test getting exclusive areas mapping"""
        rules = ActivityRules()
        exclusive = rules.get_exclusive_areas()
        assert isinstance(exclusive, dict)
        assert "Tower" in exclusive
        assert "Climbing Tower" in exclusive["Tower"]
    
    def test_is_activity_exclusive(self):
        """Test checking if activity is exclusive"""
        rules = ActivityRules()
        assert rules.is_activity_exclusive("Climbing Tower") == True
        assert rules.is_activity_exclusive("Archery") == True
        assert rules.is_activity_exclusive("Reflection") == False
    
    def test_get_exclusive_area_for_activity(self):
        """Test getting exclusive area for an activity"""
        rules = ActivityRules()
        assert rules.get_exclusive_area_for_activity("Climbing Tower") == "Tower"
        assert rules.get_exclusive_area_for_activity("Archery") == "Archery"
        assert rules.get_exclusive_area_for_activity("Reflection") is None
    
    def test_get_activities_in_area(self):
        """Test getting all activities in an exclusive area"""
        rules = ActivityRules()
        tower_activities = rules.get_activities_in_area("Tower")
        assert "Climbing Tower" in tower_activities
        assert len(tower_activities) == 1
        
        outdoor_activities = rules.get_activities_in_area("Outdoor Skills")
        assert "Knots and Lashings" in outdoor_activities
        assert "Orienteering" in outdoor_activities
    
    def test_are_activities_same_exclusive_area(self):
        """Test checking if two activities are in same exclusive area"""
        rules = ActivityRules()
        assert rules.are_activities_same_exclusive_area("Climbing Tower", "Climbing Tower") == True
        assert rules.are_activities_same_exclusive_area("Knots and Lashings", "Orienteering") == True
        assert rules.are_activities_same_exclusive_area("Climbing Tower", "Archery") == False
    
    def test_get_wet_activities(self):
        """Test getting list of wet activities"""
        rules = ActivityRules()
        wet = rules.get_wet_activities()
        assert "Aqua Trampoline" in wet
        assert "Water Polo" in wet
        assert "Troop Swim" in wet
        assert "Archery" not in wet
    
    def test_is_wet_activity(self):
        """Test checking if activity is wet"""
        rules = ActivityRules()
        assert rules.is_wet_activity("Aqua Trampoline") == True
        assert rules.is_wet_activity("Water Polo") == True
        assert rules.is_wet_activity("Archery") == False
        assert rules.is_wet_activity("Climbing Tower") == False
    
    def test_get_tower_ods_activities(self):
        """Test getting tower and ODS activities"""
        rules = ActivityRules()
        tower_ods = rules.get_tower_ods_activities()
        assert "Climbing Tower" in tower_ods
        assert "Knots and Lashings" in tower_ods
        assert "Orienteering" in tower_ods
        assert "Aqua Trampoline" not in tower_ods
    
    def test_is_tower_ods_activity(self):
        """Test checking if activity is tower/ODS"""
        rules = ActivityRules()
        assert rules.is_tower_ods_activity("Climbing Tower") == True
        assert rules.is_tower_ods_activity("Knots and Lashings") == True
        assert rules.is_tower_ods_activity("Aqua Trampoline") == False
    
    def test_get_accuracy_activities(self):
        """Test getting accuracy activities"""
        rules = ActivityRules()
        accuracy = rules.get_accuracy_activities()
        assert "Troop Rifle" in accuracy
        assert "Troop Shotgun" in accuracy
        assert "Archery" in accuracy
        assert "Water Polo" not in accuracy
    
    def test_is_accuracy_activity(self):
        """Test checking if activity is accuracy activity"""
        rules = ActivityRules()
        assert rules.is_accuracy_activity("Troop Rifle") == True
        assert rules.is_accuracy_activity("Archery") == True
        assert rules.is_accuracy_activity("Water Polo") == False
    
    def test_get_three_hour_activities(self):
        """Test getting 3-hour activities"""
        rules = ActivityRules()
        three_hour = rules.get_three_hour_activities()
        assert "Tamarac Wildlife Refuge" in three_hour
        assert "Itasca State Park" in three_hour
        assert "Back of the Moon" in three_hour
        assert "Archery" not in three_hour
    
    def test_is_three_hour_activity(self):
        """Test checking if activity is 3-hour"""
        rules = ActivityRules()
        assert rules.is_three_hour_activity("Itasca State Park") == True
        assert rules.is_three_hour_activity("Archery") == False
    
    def test_get_non_consecutive_activities(self):
        """Test getting activities that don't need consecutive slot optimization"""
        rules = ActivityRules()
        non_consecutive = rules.get_non_consecutive_activities()
        assert "Trading Post" in non_consecutive
        assert "Campsite Free Time" in non_consecutive
        assert "Itasca State Park" in non_consecutive
        assert "Archery" not in non_consecutive
    
    def test_is_non_consecutive_activity(self):
        """Test checking if activity needs consecutive optimization"""
        rules = ActivityRules()
        assert rules.is_non_consecutive_activity("Trading Post") == True
        assert rules.is_non_consecutive_activity("Archery") == False
    
    def test_get_beach_activities(self):
        """Test getting beach activities"""
        rules = ActivityRules()
        beach = rules.get_beach_activities()
        assert "Water Polo" in beach
        assert "Aqua Trampoline" in beach
        assert "Greased Watermelon" in beach
        assert "Archery" not in beach
    
    def test_is_beach_activity(self):
        """Test checking if activity is beach activity"""
        rules = ActivityRules()
        assert rules.is_beach_activity("Water Polo") == True
        assert rules.is_beach_activity("Aqua Trampoline") == True
        assert rules.is_beach_activity("Archery") == False
    
    def test_get_beach_prohibited_pairs(self):
        """Test getting beach activity prohibited pairs"""
        rules = ActivityRules()
        prohibited = rules.get_beach_prohibited_pairs()
        assert "Aqua Trampoline" in prohibited
        assert "Water Polo" in prohibited
        assert "Greased Watermelon" in prohibited
    
    def test_are_beach_activities_prohibited_pair(self):
        """Test checking if two beach activities are prohibited pair"""
        rules = ActivityRules()
        assert rules.are_beach_activities_prohibited_pair("Aqua Trampoline", "Water Polo") == True
        assert rules.are_beach_activities_prohibited_pair("Aqua Trampoline", "Greased Watermelon") == True
        assert rules.are_beach_activities_prohibited_pair("Water Polo", "Greased Watermelon") == True
        assert rules.are_beach_activities_prohibited_pair("Aqua Trampoline", "Archery") == False
    
    def test_get_same_day_conflicts(self):
        """Test getting same day conflict pairs"""
        rules = ActivityRules()
        conflicts = rules.get_same_day_conflicts()
        assert ("Trading Post", "Campsite Free Time") in conflicts
        assert ("Aqua Trampoline", "Water Polo") in conflicts
        assert len(conflicts) > 0
    
    def test_have_same_day_conflict(self):
        """Test checking if two activities have same day conflict"""
        rules = ActivityRules()
        assert rules.have_same_day_conflict("Trading Post", "Campsite Free Time") == True
        assert rules.have_same_day_conflict("Aqua Trampoline", "Water Polo") == True
        assert rules.have_same_day_conflict("Archery", "Climbing Tower") == False
    
    def test_get_soft_same_day_conflicts(self):
        """Test getting soft same day conflict pairs"""
        rules = ActivityRules()
        conflicts = rules.get_soft_same_day_conflicts()
        assert ("Fishing", "Trading Post") in conflicts
        assert len(conflicts) > 0
    
    def test_have_soft_same_day_conflict(self):
        """Test checking if two activities have soft same day conflict"""
        rules = ActivityRules()
        assert rules.have_soft_same_day_conflict("Fishing", "Trading Post") == True
        assert rules.have_soft_same_day_conflict("Archery", "Climbing Tower") == False
