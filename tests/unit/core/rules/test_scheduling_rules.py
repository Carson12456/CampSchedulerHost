"""
Unit tests for Scheduling Rules
"""
import pytest

from core.rules.scheduling_rules import SchedulingRules


class TestSchedulingRules:
    """Test cases for Scheduling Rules"""
    
    def test_get_default_fill_priority(self):
        """Test getting default fill priority list"""
        rules = SchedulingRules()
        priority = rules.get_default_fill_priority()
        assert isinstance(priority, list)
        assert len(priority) > 0
        assert "Super Troop" in priority
        assert "Aqua Trampoline" in priority
        assert "Archery" in priority
        assert "Campsite Free Time" in priority
        
        # Check that certain activities are at the end (flexible ones)
        assert "Gaga Ball" == priority[5]  # 6th position
        assert "9 Square" == priority[6]   # 7th position
    
    def test_get_concurrent_activities(self):
        """Test getting concurrent activities list"""
        rules = SchedulingRules()
        concurrent = rules.get_concurrent_activities()
        assert isinstance(concurrent, list)
        assert "Reflection" in concurrent
        assert "Campsite Free Time" in concurrent
        assert len(concurrent) == 2
    
    def test_is_concurrent_activity(self):
        """Test checking if activity is concurrent"""
        rules = SchedulingRules()
        assert rules.is_concurrent_activity("Reflection") == True
        assert rules.is_concurrent_activity("Campsite Free Time") == True
        assert rules.is_concurrent_activity("Archery") == False
        assert rules.is_concurrent_activity("Climbing Tower") == False
    
    def test_get_fill_priority_for_troop(self):
        """Test getting customized fill priority for troop"""
        rules = SchedulingRules()
        
        # Test with empty preferences
        empty_prefs = []
        priority = rules.get_fill_priority_for_troop(empty_prefs)
        assert priority == rules.get_default_fill_priority()
        
        # Test with some preferences
        troop_prefs = ["Archery", "Climbing Tower", "Water Polo"]
        priority = rules.get_fill_priority_for_troop(troop_prefs)
        
        # Troop preferences should come first
        assert priority[0] == "Archery"
        assert priority[1] == "Climbing Tower"
        assert priority[2] == "Water Polo"
        
        # Should include default priorities that aren't in troop preferences
        assert "Super Troop" in priority
        assert "Aqua Trampoline" in priority
        assert "Campsite Free Time" in priority
        
        # Should not duplicate troop preferences
        assert priority.count("Archery") == 1
        assert priority.count("Climbing Tower") == 1
        assert priority.count("Water Polo") == 1
    
    def test_fill_priority_ordering(self):
        """Test that fill priority maintains correct ordering"""
        rules = SchedulingRules()
        priority = rules.get_default_fill_priority()
        
        # Check that high-priority activities are at the beginning
        assert priority[0] == "Super Troop"
        assert priority[1] == "Aqua Trampoline"
        
        # Check that flexible activities are positioned correctly
        # Gaga Ball and 9 Square are in middle positions (6th and 7th)
        # Campsite Free Time is at the end
        assert "Gaga Ball" == priority[5]  # 6th position  
        assert "9 Square" == priority[6]   # 7th position
        assert "Campsite Free Time" == priority[-1]  # Last position
    
    def test_fill_priority_no_duplicates(self):
        """Test that fill priority has no duplicate activities"""
        rules = SchedulingRules()
        priority = rules.get_default_fill_priority()
        
        # Check for duplicates
        assert len(priority) == len(set(priority)), "Fill priority should not have duplicates"
    
    def test_fill_priority_completeness(self):
        """Test that fill priority includes expected activities"""
        rules = SchedulingRules()
        priority = rules.get_default_fill_priority()
        
        expected_activities = [
            "Super Troop", "Aqua Trampoline", "Archery", "Water Polo", 
            "Troop Rifle", "Gaga Ball", "9 Square", "Troop Swim", "Sailing",
            "Trading Post", "GPS & Geocaching", "Hemp Craft", "Dr. DNA",
            "Loon Lore", "Fishing", "Campsite Free Time"
        ]
        
        for activity in expected_activities:
            assert activity in priority, f"Missing expected activity in fill priority: {activity}"
