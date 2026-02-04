"""
Core Entity Tests

Tests for fundamental data models and entities to ensure they maintain
their expected behavior and immutability properties.
"""
import pytest
import sys
from pathlib import Path
from dataclasses import FrozenInstanceError

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone


class TestActivity:
    """Test Activity entity behavior"""
    
    def test_activity_creation(self):
        """Test: Activity can be created with valid parameters"""
        activity = Activity("Test Activity", 1.0, Zone.BEACH, "Test Staff")
        
        assert activity.name == "Test Activity"
        assert activity.slots == 1.0
        assert activity.zone == Zone.BEACH
        assert activity.staff == "Test Staff"
        assert activity.conflicts_with == []
    
    def test_activity_with_conflicts(self):
        """Test: Activity can have conflict relationships"""
        conflicts = ["Activity A", "Activity B"]
        activity = Activity("Test Activity", 1.0, Zone.BEACH, "Test Staff", conflicts)
        
        assert activity.conflicts_with == conflicts
    
    def test_activity_hashable(self):
        """Test: Activity is hashable for use in sets and dict keys"""
        activity1 = Activity("Test Activity", 1.0, Zone.BEACH)
        activity2 = Activity("Test Activity", 1.0, Zone.BEACH)
        activity3 = Activity("Different Activity", 1.0, Zone.BEACH)
        
        # Same activities should have same hash
        assert hash(activity1) == hash(activity2)
        
        # Different activities should have different hashes
        assert hash(activity1) != hash(activity3)
        
        # Should be usable in sets
        activity_set = {activity1, activity2, activity3}
        assert len(activity_set) == 2  # activity1 and activity2 are the same
    
    def test_activity_equality(self):
        """Test: Activity equality is based on name"""
        activity1 = Activity("Test Activity", 1.0, Zone.BEACH)
        activity2 = Activity("Test Activity", 2.0, Zone.TOWER)  # Different properties
        activity3 = Activity("Different Activity", 1.0, Zone.BEACH)
        
        # Same name = equal
        assert activity1 == activity2
        
        # Different name = not equal
        assert activity1 != activity3
        
        # Not equal to non-Activity objects
        assert activity1 != "Test Activity"
        assert activity1 != None


class TestTimeSlot:
    """Test TimeSlot entity behavior"""
    
    def test_timeslot_creation(self):
        """Test: TimeSlot can be created with valid parameters"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        assert timeslot.day == Day.MONDAY
        assert timeslot.slot_number == 1
    
    def test_timeslot_hashable(self):
        """Test: TimeSlot is hashable"""
        timeslot1 = TimeSlot(Day.MONDAY, 1)
        timeslot2 = TimeSlot(Day.MONDAY, 1)
        timeslot3 = TimeSlot(Day.MONDAY, 2)
        
        # Same timeslots should have same hash
        assert hash(timeslot1) == hash(timeslot2)
        
        # Different timeslots should have different hashes
        assert hash(timeslot1) != hash(timeslot3)
        
        # Should be usable in sets
        timeslot_set = {timeslot1, timeslot2, timeslot3}
        assert len(timeslot_set) == 2
    
    def test_timeslot_equality(self):
        """Test: TimeSlot equality is based on day and slot"""
        timeslot1 = TimeSlot(Day.MONDAY, 1)
        timeslot2 = TimeSlot(Day.MONDAY, 1)
        timeslot3 = TimeSlot(Day.MONDAY, 2)
        timeslot4 = TimeSlot(Day.TUESDAY, 1)
        
        # Same day and slot = equal
        assert timeslot1 == timeslot2
        
        # Different slot = not equal
        assert timeslot1 != timeslot3
        
        # Different day = not equal
        assert timeslot1 != timeslot4
    
    def test_timeslot_repr(self):
        """Test: TimeSlot has readable string representation"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        repr_str = repr(timeslot)
        
        assert "Mon-1" in repr_str


class TestTroop:
    """Test Troop entity behavior"""
    
    def test_troop_creation(self):
        """Test: Troop can be created with valid parameters"""
        troop = Troop("Test Troop", "Site A", ["Activity 1", "Activity 2"], 12, 2)
        
        assert troop.name == "Test Troop"
        assert troop.campsite == "Site A"
        assert troop.preferences == ["Activity 1", "Activity 2"]
        assert troop.scouts == 12
        assert troop.adults == 2
        assert troop.commissioner == ""
    
    def test_troop_size_property(self):
        """Test: Troop size property calculates correctly"""
        troop = Troop("Test Troop", "Site A", [], 12, 2)
        
        assert troop.size == 14  # 12 scouts + 2 adults
    
    def test_troop_size_categories(self):
        """Test: Troop size categorization works correctly"""
        # Extra Small
        troop_xs = Troop("XS Troop", "Site A", [], 3, 2)
        assert troop_xs.size_category == "Extra Small"
        
        # Small
        troop_s = Troop("S Troop", "Site A", [], 8, 2)
        assert troop_s.size_category == "Small"
        
        # Medium
        troop_m = Troop("M Troop", "Site A", [], 13, 2)
        assert troop_m.size_category == "Medium"
        
        # Large
        troop_l = Troop("L Troop", "Site A", [], 18, 2)
        assert troop_l.size_category == "Large"
        
        # Split
        troop_split = Troop("Split Troop", "Site A", [], 25, 2)
        assert troop_split.size_category == "Split"
    
    def test_troop_needs_split(self):
        """Test: Troop split detection works correctly"""
        troop_small = Troop("Small Troop", "Site A", [], 12, 2)
        assert not troop_small.needs_split()
        
        troop_large = Troop("Large Troop", "Site A", [], 25, 2)
        assert troop_large.needs_split()
    
    def test_troop_get_priority(self):
        """Test: Troop priority calculation works correctly"""
        preferences = ["Activity 1", "Activity 2", "Activity 3"]
        troop = Troop("Test Troop", "Site A", preferences, 12, 2)
        
        # Existing preferences should return index
        assert troop.get_priority("Activity 1") == 0
        assert troop.get_priority("Activity 2") == 1
        assert troop.get_priority("Activity 3") == 2
        
        # Non-existent preference should return 999
        assert troop.get_priority("Non-existent") == 999


class TestScheduleEntry:
    """Test ScheduleEntry entity behavior"""
    
    def test_schedule_entry_creation(self):
        """Test: ScheduleEntry can be created with valid parameters"""
        troop = Troop("Test Troop", "Site A", [], 12, 2)
        activity = Activity("Test Activity", 1.0, Zone.BEACH)
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        entry = ScheduleEntry(timeslot, activity, troop)
        
        assert entry.time_slot == timeslot
        assert entry.activity == activity
        assert entry.troop == troop
    
    def test_schedule_entry_argument_reordering(self):
        """Test: ScheduleEntry handles mis-ordered constructor arguments"""
        troop = Troop("Test Troop", "Site A", [], 12, 2)
        activity = Activity("Test Activity", 1.0, Zone.BEACH)
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Test with wrong order (troop, activity, slot)
        entry_wrong_order = ScheduleEntry(troop, activity, timeslot)
        
        assert entry_wrong_order.time_slot == timeslot
        assert entry_wrong_order.activity == activity
        assert entry_wrong_order.troop == troop
    
    def test_schedule_entry_hashable(self):
        """Test: ScheduleEntry is hashable"""
        troop = Troop("Test Troop", "Site A", [], 12, 2)
        activity = Activity("Test Activity", 1.0, Zone.BEACH)
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        entry1 = ScheduleEntry(timeslot, activity, troop)
        entry2 = ScheduleEntry(timeslot, activity, troop)
        entry3 = ScheduleEntry(TimeSlot(Day.MONDAY, 2), activity, troop)
        
        # Same entries should have same hash
        assert hash(entry1) == hash(entry2)
        
        # Different entries should have different hashes
        assert hash(entry1) != hash(entry3)
        
        # Should be usable in sets
        entry_set = {entry1, entry2, entry3}
        assert len(entry_set) == 2
    
    def test_schedule_entry_equality(self):
        """Test: ScheduleEntry equality is based on all three components"""
        troop = Troop("Test Troop", "Site A", [], 12, 2)
        activity = Activity("Test Activity", 1.0, Zone.BEACH)
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        entry1 = ScheduleEntry(timeslot, activity, troop)
        entry2 = ScheduleEntry(timeslot, activity, troop)
        entry3 = ScheduleEntry(TimeSlot(Day.MONDAY, 2), activity, troop)
        
        # Same components = equal
        assert entry1 == entry2
        
        # Different timeslot = not equal
        assert entry1 != entry3
        
        # Not equal to non-ScheduleEntry objects
        assert entry1 != "string"
        assert entry1 != None


class TestSchedule:
    """Test Schedule entity behavior"""
    
    @pytest.fixture
    def sample_troop(self):
        """Create a sample troop for testing"""
        return Troop("Test Troop", "Site A", ["Activity 1", "Activity 2"], 12, 2)
    
    @pytest.fixture
    def sample_activity(self):
        """Create a sample activity for testing"""
        return Activity("Test Activity", 1.0, Zone.BEACH)
    
    @pytest.fixture
    def sample_schedule(self):
        """Create a sample schedule for testing"""
        return Schedule()
    
    def test_schedule_creation(self, sample_schedule):
        """Test: Schedule can be created empty"""
        assert len(sample_schedule.entries) == 0
        assert isinstance(sample_schedule.entries, list)
    
    def test_add_entry_success(self, sample_schedule, sample_troop, sample_activity):
        """Test: Can add entry to schedule successfully"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        result = sample_schedule.add_entry(timeslot, sample_activity, sample_troop)
        
        assert result == True
        assert len(sample_schedule.entries) == 1
        
        entry = sample_schedule.entries[0]
        assert entry.time_slot == timeslot
        assert entry.activity == sample_activity
        assert entry.troop == sample_troop
    
    def test_add_duplicate_entry_fails(self, sample_schedule, sample_troop, sample_activity):
        """Test: Cannot add duplicate entry to schedule"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Add first entry
        result1 = sample_schedule.add_entry(timeslot, sample_activity, sample_troop)
        assert result1 == True
        
        # Try to add duplicate
        result2 = sample_schedule.add_entry(timeslot, sample_activity, sample_troop)
        assert result2 == False  # Should fail
        assert len(sample_schedule.entries) == 1  # Still only one entry
    
    def test_add_entry_troop_not_free_fails(self, sample_schedule, sample_troop, sample_activity):
        """Test: Cannot add entry if troop is not free"""
        timeslot1 = TimeSlot(Day.MONDAY, 1)
        timeslot2 = TimeSlot(Day.MONDAY, 1)
        activity2 = Activity("Activity 2", 1.0, Zone.BEACH)
        
        # Add first entry
        result1 = sample_schedule.add_entry(timeslot1, sample_activity, sample_troop)
        assert result1 == True
        
        # Try to add another entry for same troop at same time
        result2 = sample_schedule.add_entry(timeslot2, activity2, sample_troop)
        assert result2 == False  # Should fail
        assert len(sample_schedule.entries) == 1  # Still only one entry
    
    def test_get_troop_schedule(self, sample_schedule, sample_troop, sample_activity):
        """Test: Can get troop's schedule"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        sample_schedule.add_entry(timeslot, sample_activity, sample_troop)
        
        troop_schedule = sample_schedule.get_troop_schedule(sample_troop)
        
        assert len(troop_schedule) == 1
        assert troop_schedule[0].troop == sample_troop
        assert troop_schedule[0].activity == sample_activity
    
    def test_get_slot_activities(self, sample_schedule, sample_troop, sample_activity):
        """Test: Can get activities for a time slot"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        sample_schedule.add_entry(timeslot, sample_activity, sample_troop)
        
        slot_activities = sample_schedule.get_slot_activities(timeslot)
        
        assert len(slot_activities) == 1
        assert slot_activities[0].activity == sample_activity
        assert slot_activities[0].troop == sample_troop
    
    def test_remove_entry_success(self, sample_schedule, sample_troop, sample_activity):
        """Test: Can remove entry from schedule"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        sample_schedule.add_entry(timeslot, sample_activity, sample_troop)
        
        entry = sample_schedule.entries[0]
        result = sample_schedule.remove_entry(entry)
        
        assert result == True
        assert len(sample_schedule.entries) == 0
    
    def test_remove_nonexistent_entry_fails(self, sample_schedule):
        """Test: Cannot remove non-existent entry"""
        troop = Troop("Test Troop", "Site A", [], 12, 2)
        activity = Activity("Test Activity", 1.0, Zone.BEACH)
        timeslot = TimeSlot(Day.MONDAY, 1)
        entry = ScheduleEntry(timeslot, activity, troop)
        
        result = sample_schedule.remove_entry(entry)
        
        assert result == False
        assert len(sample_schedule.entries) == 0
    
    def test_is_troop_free(self, sample_schedule, sample_troop, sample_activity):
        """Test: Can check if troop is free at a time slot"""
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        # Troop should be free initially
        assert sample_schedule.is_troop_free(timeslot, sample_troop) == True
        
        # Add entry
        sample_schedule.add_entry(timeslot, sample_activity, sample_troop)
        
        # Troop should not be free anymore
        assert sample_schedule.is_troop_free(timeslot, sample_troop) == False
        
        # Should be free at different time
        different_timeslot = TimeSlot(Day.MONDAY, 2)
        assert sample_schedule.is_troop_free(different_timeslot, sample_troop) == True
    
    def test_multislot_activity_handling(self, sample_schedule, sample_troop):
        """Test: Multi-slot activities are handled correctly"""
        # Create 1.5 slot activity
        multislot_activity = Activity("Multi-Slot Activity", 1.5, Zone.BEACH)
        timeslot = TimeSlot(Day.MONDAY, 1)
        
        result = sample_schedule.add_entry(timeslot, multislot_activity, sample_troop)
        
        assert result == True
        assert len(sample_schedule.entries) == 2  # Should add continuation entry
        
        # Check that both entries are for the same activity and troop
        for entry in sample_schedule.entries:
            assert entry.activity == multislot_activity
            assert entry.troop == sample_troop
        
        # Check that troop is not free in either slot
        assert sample_schedule.is_troop_free(timeslot, sample_troop) == False
        continuation_slot = TimeSlot(Day.MONDAY, 2)
        assert sample_schedule.is_troop_free(continuation_slot, sample_troop) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
