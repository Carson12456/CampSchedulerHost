"""
Unit tests for TimeSlot entity
"""
import pytest

from core.entities.time_slot import TimeSlot, Day


class TestTimeSlot:
    """Test cases for TimeSlot entity"""
    
    def test_time_slot_creation(self):
        """Test creating a basic time slot"""
        time_slot = TimeSlot(day=Day.MONDAY, slot_number=1)
        assert time_slot.day == Day.MONDAY
        assert time_slot.slot_number == 1
    
    def test_time_slot_different_days(self):
        """Test time slots for different days"""
        monday_slot = TimeSlot(day=Day.MONDAY, slot_number=1)
        tuesday_slot = TimeSlot(day=Day.TUESDAY, slot_number=1)
        assert monday_slot.day != tuesday_slot.day
        assert monday_slot.slot_number == tuesday_slot.slot_number
    
    def test_time_slot_different_slots(self):
        """Test time slots for different slot numbers"""
        slot1 = TimeSlot(day=Day.MONDAY, slot_number=1)
        slot2 = TimeSlot(day=Day.MONDAY, slot_number=2)
        assert slot1.day == slot2.day
        assert slot1.slot_number != slot2.slot_number
    
    def test_time_slot_equality(self):
        """Test time slot equality"""
        slot1 = TimeSlot(day=Day.MONDAY, slot_number=1)
        slot2 = TimeSlot(day=Day.MONDAY, slot_number=1)
        slot3 = TimeSlot(day=Day.MONDAY, slot_number=2)
        slot4 = TimeSlot(day=Day.TUESDAY, slot_number=1)
        
        assert slot1 == slot2  # Same day and slot
        assert slot1 != slot3  # Different slot
        assert slot1 != slot4  # Different day
    
    def test_time_slot_hash(self):
        """Test time slot is hashable for use in sets/dicts"""
        slot1 = TimeSlot(day=Day.MONDAY, slot_number=1)
        slot2 = TimeSlot(day=Day.MONDAY, slot_number=1)
        slot3 = TimeSlot(day=Day.MONDAY, slot_number=2)
        
        slot_set = {slot1, slot2, slot3}
        assert len(slot_set) == 2  # slot1 and slot2 are the same
        
        # Test use as dictionary key
        slot_dict = {slot1: "Monday 1", slot3: "Monday 2"}
        assert slot_dict[slot1] == "Monday 1"
        assert slot_dict[slot3] == "Monday 2"
    
    def test_time_slot_repr(self):
        """Test string representation of time slot"""
        slot = TimeSlot(day=Day.MONDAY, slot_number=1)
        repr_str = repr(slot)
        assert "Mon-1" in repr_str
    
    def test_time_slot_str(self):
        """Test string conversion of time slot"""
        slot = TimeSlot(day=Day.WEDNESDAY, slot_number=2)
        str_repr = str(slot)
        assert "Wed-2" in str_repr


class TestDay:
    """Test cases for Day enum"""
    
    def test_day_enum_values(self):
        """Test day enum has correct values"""
        assert Day.MONDAY.value == "Monday"
        assert Day.TUESDAY.value == "Tuesday"
        assert Day.WEDNESDAY.value == "Wednesday"
        assert Day.THURSDAY.value == "Thursday"
        assert Day.FRIDAY.value == "Friday"
    
    def test_day_enum_iteration(self):
        """Test we can iterate over all days"""
        days = list(Day)
        assert len(days) == 5
        assert Day.MONDAY in days
        assert Day.FRIDAY in days
    
    def test_day_order(self):
        """Test days are in expected order"""
        days = list(Day)
        assert days[0] == Day.MONDAY
        assert days[1] == Day.TUESDAY
        assert days[2] == Day.WEDNESDAY
        assert days[3] == Day.THURSDAY
        assert days[4] == Day.FRIDAY
