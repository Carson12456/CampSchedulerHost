"""
Unit tests for Capacity Rules
"""
import pytest

from core.rules.capacity_rules import CapacityRules


class TestCapacityRules:
    """Test cases for Capacity Rules"""
    
    def test_get_beach_staff_activities(self):
        """Test getting beach staff activities set"""
        rules = CapacityRules()
        beach_staff = rules.get_beach_staff_activities()
        assert isinstance(beach_staff, set)
        assert "Aqua Trampoline" in beach_staff
        assert "Water Polo" in beach_staff
        assert "Troop Swim" in beach_staff
        assert "Archery" not in beach_staff
        assert "Climbing Tower" not in beach_staff
    
    def test_is_beach_staff_activity(self):
        """Test checking if activity requires beach staff"""
        rules = CapacityRules()
        assert rules.is_beach_staff_activity("Aqua Trampoline") == True
        assert rules.is_beach_staff_activity("Water Polo") == True
        assert rules.is_beach_staff_activity("Troop Swim") == True
        assert rules.is_beach_staff_activity("Sailing") == True
        assert rules.is_beach_staff_activity("Archery") == False
        assert rules.is_beach_staff_activity("Climbing Tower") == False
        assert rules.is_beach_staff_activity("Reflection") == False
    
    def test_get_max_beach_staff_activities_per_slot(self):
        """Test getting maximum beach staff activities per slot"""
        rules = CapacityRules()
        max_count = rules.get_max_beach_staff_activities_per_slot()
        assert max_count == 4
        assert isinstance(max_count, int)
    
    def test_can_add_beach_staff_activity(self):
        """Test checking if beach staff activity can be added"""
        rules = CapacityRules()
        
        # Should be able to add when under limit
        assert rules.can_add_beach_staff_activity(0) == True
        assert rules.can_add_beach_staff_activity(1) == True
        assert rules.can_add_beach_staff_activity(2) == True
        assert rules.can_add_beach_staff_activity(3) == True
        
        # Should not be able to add when at or over limit
        assert rules.can_add_beach_staff_activity(4) == False
        assert rules.can_add_beach_staff_activity(5) == False
    
    def test_beach_staff_activities_completeness(self):
        """Test that all expected beach staff activities are included"""
        rules = CapacityRules()
        beach_staff = rules.get_beach_staff_activities()
        
        expected_activities = [
            "Aqua Trampoline", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Float for Floats", "Greased Watermelon", "Underwater Obstacle Course",
            "Troop Swim", "Water Polo", "Nature Canoe", "Sailing"
        ]
        
        for activity in expected_activities:
            assert activity in beach_staff, f"Missing expected beach staff activity: {activity}"
        
        # Verify count matches expected
        assert len(beach_staff) == len(expected_activities)
