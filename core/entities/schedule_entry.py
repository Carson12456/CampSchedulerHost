"""
ScheduleEntry entity for Summer Camp Scheduler
Pure domain entity with no external dependencies
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .time_slot import TimeSlot
    from .activity import Activity
    from .troop import Troop


@dataclass
class ScheduleEntry:
    """
    A single entry in the schedule.
    
    This is a pure domain entity that represents the relationship
    between a troop, activity, and time slot.
    """
    time_slot: 'TimeSlot'
    activity: 'Activity'
    troop: 'Troop'
    
    def __post_init__(self):
        """
        Normalize argument order if constructed with wrong parameter order.
        This provides flexibility for different calling patterns while ensuring
        the internal structure is always correct.
        """
        # Accept mis-ordered construction and reorder by type
        ts = None
        act = None
        tr = None
        for value in (self.time_slot, self.activity, self.troop):
            if hasattr(value, 'day') and hasattr(value, 'slot_number'):
                ts = value
            elif hasattr(value, 'name') and hasattr(value, 'slots'):
                act = value
            elif hasattr(value, 'name') and hasattr(value, 'scouts'):
                tr = value
        
        if ts and act and tr:
            self.time_slot = ts
            self.activity = act
            self.troop = tr
    
    def __hash__(self):
        """Make ScheduleEntry hashable for use in sets and as dictionary keys"""
        return hash((self.time_slot, self.activity.name, self.troop.name))
    
    def __eq__(self, other):
        """ScheduleEntries are equal if they have the same time_slot, activity.name, and troop.name"""
        if isinstance(other, ScheduleEntry):
            return (self.time_slot == other.time_slot and 
                   self.activity.name == other.activity.name and
                   self.troop.name == other.troop.name)
        return False
    
    def __repr__(self):
        """String representation for debugging"""
        return f"ScheduleEntry({self.troop.name} -> {self.activity.name} @ {self.time_slot})"
    
    def is_multi_slot(self) -> bool:
        """Check if this entry represents a multi-slot activity"""
        return self.activity.is_multi_slot()
    
    def is_on_day(self, day) -> bool:
        """Check if this entry is on a specific day"""
        return self.time_slot.day == day
    
    def is_in_slot(self, slot_number: int) -> bool:
        """Check if this entry is in a specific slot number"""
        return self.time_slot.slot_number == slot_number
