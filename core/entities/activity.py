"""
Activity entity for Summer Camp Scheduler
Pure domain entity with no external dependencies
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class Zone(Enum):
    """Represents different activity zones in the camp"""
    DELTA = "Delta"
    BEACH = "Beach"
    OUTDOOR_SKILLS = "Outdoor Skills"
    TOWER = "Tower"
    OFF_CAMP = "Off-camp"
    CAMPSITE = "Campsite"


@dataclass
class Activity:
    """
    Represents a camp activity.
    
    This is a pure domain entity that contains only the essential
    data and behavior for an activity, with no external dependencies.
    """
    name: str
    slots: float  # 1, 1.5, 2, or 3
    zone: Zone
    staff: Optional[str] = None  # None means unstaffed
    conflicts_with: List[str] = field(default_factory=list)  # Activity names that can't run simultaneously
    
    def __hash__(self):
        """Make Activity hashable for use in sets and as dictionary keys"""
        return hash(self.name)
    
    def __eq__(self, other):
        """Activities are equal if they have the same name"""
        if isinstance(other, Activity):
            return self.name == other.name
        return False
    
    def __repr__(self):
        """String representation for debugging"""
        return f"Activity(name='{self.name}', slots={self.slots}, zone={self.zone.value})"
    
    def is_multi_slot(self) -> bool:
        """Check if this activity spans multiple time slots"""
        return self.slots > 1.0
    
    def is_half_slot(self) -> bool:
        """Check if this activity has a half-slot duration"""
        return self.slots % 1.0 != 0
    
    def get_duration_in_slots(self) -> int:
        """Get the number of time slots this activity occupies (rounded up)"""
        return int(self.slots + 0.5)
