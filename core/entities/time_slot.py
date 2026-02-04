"""
TimeSlot entity for Summer Camp Scheduler
Pure domain entity with no external dependencies
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Day(Enum):
    """Represents days of the week for camp scheduling"""
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"


@dataclass
class TimeSlot:
    """
    Represents a time slot in the schedule.
    
    This is a pure domain entity that represents a specific time
    during the week when activities can be scheduled.
    """
    day: Day
    slot_number: int  # 1, 2, or 3 (Tuesday only has 1, 2)
    
    def __hash__(self):
        """Make TimeSlot hashable for use in sets and as dictionary keys"""
        return hash((self.day, self.slot_number))
    
    def __eq__(self, other):
        """TimeSlots are equal if they have the same day and slot number"""
        if isinstance(other, TimeSlot):
            return self.day == other.day and self.slot_number == other.slot_number
        return False
    
    def __repr__(self):
        """String representation for debugging"""
        return f"{self.day.value[:3]}-{self.slot_number}"
    
    def __str__(self):
        """Human-readable string representation"""
        return f"{self.day.value[:3]}-{self.slot_number}"
    
    def is_thursday(self) -> bool:
        """Check if this time slot is on Thursday"""
        return self.day == Day.THURSDAY
    
    def is_friday(self) -> bool:
        """Check if this time slot is on Friday"""
        return self.day == Day.FRIDAY
    
    def is_morning(self) -> bool:
        """Check if this is a morning slot (slot 1)"""
        return self.slot_number == 1
    
    def is_afternoon(self) -> bool:
        """Check if this is an afternoon slot (slot 2 or 3)"""
        return self.slot_number in [2, 3]
    
    def get_next_slot(self) -> Optional['TimeSlot']:
        """
        Get the next time slot in sequence.
        Returns None if this is the last slot of the day.
        """
        max_slot = 2 if self.day == Day.THURSDAY else 3
        if self.slot_number >= max_slot:
            return None
        
        return TimeSlot(self.day, self.slot_number + 1)
    
    def get_previous_slot(self) -> Optional['TimeSlot']:
        """
        Get the previous time slot in sequence.
        Returns None if this is the first slot of the day.
        """
        if self.slot_number <= 1:
            return None
        
        return TimeSlot(self.day, self.slot_number - 1)
