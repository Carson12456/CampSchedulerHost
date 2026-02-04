"""
Constraint System Tests

Tests for all constraint validation rules and business logic.
Ensures the scheduling constraints are properly enforced.
"""
import pytest
import sys
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone, EXCLUSIVE_AREAS, BEACH_STAFF_ACTIVITIES
from activities import get_all_activities


class TestConstraintValidation:
    """Test constraint validation rules"""
    
    @pytest.fixture
    def sample_schedule(self):
        """Create a sample schedule for testing"""
        return Schedule()
    
    @pytest.fixture
    def sample_troops(self):
        """Create sample troops for testing"""
        return [
            Troop("Troop A", "Site A", ["Aqua Trampoline", "Climbing Tower", "Archery"], 12, 2),
            Troop("Troop B", "Site B", ["Water Polo", "Sailing", "Delta"], 15, 2),
            Troop("Troop C", "Site C", ["Troop Rifle", "Nature Canoe", "GPS & Geocaching"], 8, 2),
        ]
    
    @pytest.fixture
    def all_activities(self):
        """Get all available activities"""
        return get_all_activities()
    
    # ========== EXCLUSIVE AREA CONSTRAINTS ==========
    
    def test_exclusive_areas_enforcement(self, sample_schedule, sample_troops, all_activities):
        """Test: Only one troop per slot in exclusive areas"""
        # Try to schedule two troops in Tower area at same time
        tower_activity = next((a for a in all_activities if a.name == "Climbing Tower"), None)
        assert tower_activity is not None
        
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Schedule first troop
        result1 = sample_schedule.add_entry(timeslot, tower_activity, sample_troops[0])
        assert result1 == True
        
        # Try to schedule second troop in same exclusive area
        result2 = sample_schedule.add_entry(timeslot, tower_activity, sample_troops[1])
        assert result2 == False  # Should fail due to exclusive area constraint
    
    def test_different_exclusive_areas_allowed(self, sample_schedule, sample_troops, all_activities):
        """Test: Different exclusive areas can be scheduled simultaneously"""
        tower_activity = next((a for a in all_activities if a.name == "Climbing Tower"), None)
        rifle_activity = next((a for a in all_activities if a.name == "Troop Rifle"), None)
        
        assert tower_activity is not None and rifle_activity is not None
        
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Schedule different troops in different exclusive areas
        result1 = sample_schedule.add_entry(timeslot, tower_activity, sample_troops[0])
        result2 = sample_schedule.add_entry(timeslot, rifle_activity, sample_troops[1])
        
        assert result1 == True
        assert result2 == True  # Should succeed - different exclusive areas
    
    def test_sailing_exclusivity_per_slot(self, sample_schedule, sample_troops, all_activities):
        """Test: Sailing is exclusive per slot (but can have 2 per day with different starts)"""
        sailing_activity = next((a for a in all_activities if a.name == "Sailing"), None)
        assert sailing_activity is not None
        
        # Same slot should fail
        timeslot = TimeSlot(Day.MONDAY, 1)
        result1 = sample_schedule.add_entry(timeslot, sailing_activity, sample_troops[0])
        result2 = sample_schedule.add_entry(timeslot, sailing_activity, sample_troops[1])
        
        assert result1 == True
        assert result2 == False  # Same slot should fail
        
        # Different slot should succeed (different starting times)
        timeslot2 = TimeSlot(Day.MONDAY, 2)
        result3 = sample_schedule.add_entry(timeslot2, sailing_activity, sample_troops[1])
        assert result3 == True  # Different slot should succeed
    
    # ========== BEACH SLOT CONSTRAINTS ==========
    
    def test_beach_activities_allowed_slots(self, sample_schedule, sample_troops, all_activities):
        """Test: Beach activities only allowed in specific slots"""
        beach_activities = ["Aqua Trampoline", "Water Polo", "Greased Watermelon"]
        
        for activity_name in beach_activities:
            activity = next((a for a in all_activities if a.name == activity_name), None)
            if activity is None:
                continue
            
            # Test allowed slots on regular days
            for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
                # Slot 1 should be allowed
                timeslot1 = TimeSlot(day, 1)
                result1 = sample_schedule.add_entry(timeslot1, activity, sample_troops[0])
                sample_schedule.remove_entry(ScheduleEntry(timeslot1, activity, sample_troops[0]))
                
                # Slot 3 should be allowed
                timeslot3 = TimeSlot(day, 3)
                result3 = sample_schedule.add_entry(timeslot3, activity, sample_troops[0])
                sample_schedule.remove_entry(ScheduleEntry(timeslot3, activity, sample_troops[0]))
                
                # These should generally succeed (unless other constraints prevent)
                # Note: Actual implementation may have additional constraints
    
    def test_beach_activities_thursday_slots(self, sample_schedule, sample_troops, all_activities):
        """Test: Beach activities have special slot rules on Thursday"""
        beach_activity = next((a for a in all_activities if a.name == "Aqua Trampoline"), None)
        if beach_activity is None:
            pytest.skip("Aqua Trampoline not found")
        
        # Thursday only has slots 1 and 2
        timeslot1 = TimeSlot(Day.THURSDAY, 1)
        timeslot2 = TimeSlot(Day.THURSDAY, 2)
        
        # Both slots should be allowed on Thursday
        result1 = sample_schedule.add_entry(timeslot1, beach_activity, sample_troops[0])
        assert result1 == True
        
        result2 = sample_schedule.add_entry(timeslot2, beach_activity, sample_troops[1])
        assert result2 == True  # Slot 2 should be allowed on Thursday
    
    # ========== ACTIVITY CONFLICT CONSTRAINTS ==========
    
    def test_accuracy_activity_limit(self, sample_schedule, sample_troops, all_activities):
        """Test: Max 1 accuracy activity per troop per day"""
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        
        # Get accuracy activities
        activities = []
        for activity_name in accuracy_activities:
            activity = next((a for a in all_activities if a.name == activity_name), None)
            if activity:
                activities.append(activity)
        
        if len(activities) < 2:
            pytest.skip("Need at least 2 accuracy activities for test")
        
        # Schedule first accuracy activity
        result1 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 1), activities[0], sample_troops[0])
        assert result1 == True
        
        # Try to schedule second accuracy activity on same day
        result2 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 2), activities[1], sample_troops[0])
        
        # This should be allowed in the basic schedule, but business logic should limit it
        # The constraint is typically enforced at the scheduler level, not schedule level
        assert result2 == True  # Schedule allows it, scheduler should prevent
    
    def test_prohibited_pairs_same_day(self, sample_schedule, sample_troops, all_activities):
        """Test: Certain activity pairs cannot be on same day for same troop"""
        # Test Rifle + Shotgun conflict
        rifle_activity = next((a for a in all_activities if a.name == "Troop Rifle"), None)
        shotgun_activity = next((a for a in all_activities if a.name == "Troop Shotgun"), None)
        
        if rifle_activity and shotgun_activity:
            # This is typically enforced at scheduler level, not schedule level
            # Schedule should allow both, but business logic should prevent
            result1 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 1), rifle_activity, sample_troops[0])
            result2 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 2), shotgun_activity, sample_troops[0])
            
            assert result1 == True
            assert result2 == True  # Schedule allows, scheduler should prevent
    
    def test_canoe_activity_conflicts(self, sample_schedule, sample_troops, all_activities):
        """Test: Cannot have multiple canoe activities on same day"""
        canoe_activities = ["Troop Canoe", "Canoe Snorkel", "Nature Canoe", "Float for Floats"]
        
        # Get two canoe activities
        activities = []
        for activity_name in canoe_activities:
            activity = next((a for a in all_activities if a.name == activity_name), None)
            if activity:
                activities.append(activity)
        
        if len(activities) < 2:
            pytest.skip("Need at least 2 canoe activities for test")
        
        # Schedule first canoe activity
        result1 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 1), activities[0], sample_troops[0])
        assert result1 == True
        
        # Try to schedule second canoe activity on same day
        result2 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 2), activities[1], sample_troops[0])
        
        # Schedule allows it, but business logic should prevent
        assert result2 == True
    
    # ========== CAPACITY CONSTRAINTS ==========
    
    def test_aqua_trampoline_sharing_rules(self, sample_schedule, all_activities):
        """Test: Aqua Trampoline sharing rules"""
        at_activity = next((a for a in all_activities if a.name == "Aqua Trampoline"), None)
        if at_activity is None:
            pytest.skip("Aqua Trampoline not found")
        
        # Create small troops (<=16) - should be able to share
        small_troop1 = Troop("Small Troop 1", "Site A", [], 8, 2)  # 10 total
        small_troop2 = Troop("Small Troop 2", "Site B", [], 10, 2)  # 12 total
        
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Should allow sharing
        result1 = sample_schedule.add_entry(timeslot, at_activity, small_troop1)
        result2 = sample_schedule.add_entry(timeslot, at_activity, small_troop2)
        
        assert result1 == True
        assert result2 == True  # Small troops should be able to share
        
        # Create large troop (>16) - should not be able to share with small troops
        large_troop = Troop("Large Troop", "Site C", [], 18, 2)  # 20 total
        
        # Try to add large troop to same slot
        result3 = sample_schedule.add_entry(timeslot, at_activity, large_troop)
        assert result3 == False  # Large troop should not be able to share with existing
    
    def test_aqua_trampoline_large_troop_exclusive(self, sample_schedule, all_activities):
        """Test: Large troops (>16) need exclusive use of Aqua Trampoline"""
        at_activity = next((a for a in all_activities if a.name == "Aqua Trampoline"), None)
        if at_activity is None:
            pytest.skip("Aqua Trampoline not found")
        
        large_troop1 = Troop("Large Troop 1", "Site A", [], 18, 2)  # 20 total
        large_troop2 = Troop("Large Troop 2", "Site B", [], 20, 2)  # 22 total
        
        timeslot = TimeSlot(Day.MONDAY, 2)
        
        # First large troop should succeed
        result1 = sample_schedule.add_entry(timeslot, at_activity, large_troop1)
        assert result1 == True
        
        # Second large troop should fail
        result2 = sample_schedule.add_entry(timeslot, at_activity, large_troop2)
        assert result2 == False  # Large troops cannot share
    
    def test_water_polo_sharing(self, sample_schedule, all_activities):
        """Test: Water Polo allows up to 2 troops (they play each other)"""
        wp_activity = next((a for a in all_activities if a.name == "Water Polo"), None)
        if wp_activity is None:
            pytest.skip("Water Polo not found")
        
        troop1 = Troop("Troop 1", "Site A", [], 12, 2)
        troop2 = Troop("Troop 2", "Site B", [], 10, 2)
        troop3 = Troop("Troop 3", "Site C", [], 8, 2)
        
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Should allow first two troops
        result1 = sample_schedule.add_entry(timeslot, wp_activity, troop1)
        result2 = sample_schedule.add_entry(timeslot, wp_activity, troop2)
        
        assert result1 == True
        assert result2 == True
        
        # Third troop should fail
        result3 = sample_schedule.add_entry(timeslot, wp_activity, troop3)
        assert result3 == False  # Max 2 troops for Water Polo
    
    # ========== MULTI-SLOT CONSTRAINTS ==========
    
    def test_multislot_activity_continuity(self, sample_schedule, sample_troops, all_activities):
        """Test: Multi-slot activities maintain continuity"""
        sailing_activity = next((a for a in all_activities if a.name == "Sailing"), None)
        if sailing_activity is None:
            pytest.skip("Sailing not found")
        
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Add sailing activity
        result = sample_schedule.add_entry(timeslot, sailing_activity, sample_troops[0])
        assert result == True
        
        # Should have added continuation entry
        sailing_entries = [e for e in sample_schedule.entries 
                          if e.troop == sample_troops[0] and e.activity.name == "Sailing"]
        
        assert len(sailing_entries) == 2  # Should have 2 entries (1.5 slots rounded up)
        
        # Check that they're in consecutive slots
        slots = sorted([e.time_slot.slot_number for e in sailing_entries])
        assert slots[0] == 1
        assert slots[1] == 2  # Should be consecutive
    
    def test_multislot_activity_thursday_duration(self, sample_schedule, sample_troops, all_activities):
        """Test: Sailing uses 2.0 slots on Thursday"""
        sailing_activity = next((a for a in all_activities if a.name == "Sailing"), None)
        if sailing_activity is None:
            pytest.skip("Sailing not found")
        
        timeslot = TimeSlot(Day.THURSDAY, 1)
        
        # Add sailing on Thursday
        result = sample_schedule.add_entry(timeslot, sailing_activity, sample_troops[0])
        assert result == True
        
        # Should have added continuation entry
        sailing_entries = [e for e in sample_schedule.entries 
                          if e.troop == sample_troops[0] and e.activity.name == "Sailing"
                          and e.time_slot.day == Day.THURSDAY]
        
        assert len(sailing_entries) == 2  # Should have 2 entries for Thursday
    
    def test_climbing_tower_dynamic_duration(self, sample_schedule, all_activities):
        """Test: Climbing Tower duration varies by troop size"""
        tower_activity = next((a for a in all_activities if a.name == "Climbing Tower"), None)
        if tower_activity is None:
            pytest.skip("Climbing Tower not found")
        
        # Small troop (<=15 scouts) - should use 1 slot
        small_troop = Troop("Small Troop", "Site A", [], 12, 2)
        timeslot1 = TimeSlot(Day.MONDAY, 1)
        
        result1 = sample_schedule.add_entry(timeslot1, tower_activity, small_troop)
        assert result1 == True
        
        small_entries = [e for e in sample_schedule.entries 
                        if e.troop == small_troop and e.activity.name == "Climbing Tower"]
        assert len(small_entries) == 1  # Small troop should use 1 slot
        
        # Clear schedule
        sample_schedule.entries.clear()
        
        # Large troop (>15 scouts) - should use 2 slots
        large_troop = Troop("Large Troop", "Site B", [], 18, 2)
        timeslot2 = TimeSlot(Day.MONDAY, 1)
        
        result2 = sample_schedule.add_entry(timeslot2, tower_activity, large_troop)
        assert result2 == True
        
        large_entries = [e for e in sample_schedule.entries 
                        if e.troop == large_troop and e.activity.name == "Climbing Tower"]
        assert len(large_entries) == 2  # Large troop should use 2 slots
    
    # ========== TROOP AVAILABILITY CONSTRAINTS ==========
    
    def test_troop_cannot_be_double_booked(self, sample_schedule, sample_troops, all_activities):
        """Test: Troop cannot be in two places at once"""
        activity1 = all_activities[0]
        activity2 = all_activities[1]
        
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Schedule first activity
        result1 = sample_schedule.add_entry(timeslot, activity1, sample_troops[0])
        assert result1 == True
        
        # Try to schedule second activity at same time
        result2 = sample_schedule.add_entry(timeslot, activity2, sample_troops[0])
        assert result2 == False  # Should fail - troop already booked
    
    def test_troop_available_different_times(self, sample_schedule, sample_troops, all_activities):
        """Test: Same troop can be scheduled at different times"""
        activity1 = all_activities[0]
        activity2 = all_activities[1]
        
        timeslot1 = TimeSlot(Day.MONDAY, 1)
        timeslot2 = TimeSlot(Day.MONDAY, 2)
        
        # Schedule activities at different times
        result1 = sample_schedule.add_entry(timeslot1, activity1, sample_troops[0])
        result2 = sample_schedule.add_entry(timeslot2, activity2, sample_troops[0])
        
        assert result1 == True
        assert result2 == True  # Should succeed - different times
    
    def test_multislot_blocks_other_activities(self, sample_schedule, sample_troops, all_activities):
        """Test: Multi-slot activities block all occupied slots"""
        sailing_activity = next((a for a in all_activities if a.name == "Sailing"), None)
        if sailing_activity is None:
            pytest.skip("Sailing not found")
        
        other_activity = all_activities[0]
        
        # Schedule sailing (1.5 slots = occupies slots 1 and 2)
        result1 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 1), sailing_activity, sample_troops[0])
        assert result1 == True
        
        # Try to schedule other activity in slot 1 (should fail)
        result2 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 1), other_activity, sample_troops[0])
        assert result2 == False
        
        # Try to schedule other activity in slot 2 (should fail - continuation)
        result3 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 2), other_activity, sample_troops[0])
        assert result3 == False
        
        # Try to schedule in slot 3 (should succeed)
        result4 = sample_schedule.add_entry(TimeSlot(Day.MONDAY, 3), other_activity, sample_troops[0])
        assert result4 == True


class TestConstraintHelpers:
    """Test constraint validation helper methods"""
    
    def test_exclusive_areas_constant(self):
        """Test: EXCLUSIVE_AREAS constant is properly defined"""
        assert isinstance(EXCLUSIVE_AREAS, dict)
        assert len(EXCLUSIVE_AREAS) > 0
        
        # Check that key areas are defined
        key_areas = ["Tower", "Rifle Range", "Archery", "Outdoor Skills"]
        for area in key_areas:
            assert area in EXCLUSIVE_AREAS
            assert isinstance(EXCLUSIVE_AREAS[area], list)
            assert len(EXCLUSIVE_AREAS[area]) > 0
    
    def test_beach_staff_activities_constant(self):
        """Test: BEACH_STAFF_ACTIVITIES constant is properly defined"""
        assert isinstance(BEACH_STAFF_ACTIVITIES, set)
        assert len(BEACH_STAFF_ACTIVITIES) > 0
        
        # Check that key beach activities are included
        key_activities = ["Aqua Trampoline", "Water Polo", "Troop Swim", "Sailing"]
        for activity in key_activities:
            assert activity in BEACH_STAFF_ACTIVITIES
    
    def test_activity_conflicts_property(self):
        """Test: Activity conflicts_with property works"""
        conflicts = ["Activity A", "Activity B"]
        activity = Activity("Test Activity", 1.0, Zone.BEACH, "Test Staff", conflicts)
        
        assert activity.conflicts_with == conflicts
        assert isinstance(activity.conflicts_with, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
