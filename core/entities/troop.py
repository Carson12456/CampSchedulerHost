"""
Troop entity for Summer Camp Scheduler
Pure domain entity with no external dependencies
"""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Troop:
    """
    Represents a scout troop with their preferences and requirements.
    
    This is a pure domain entity that contains troop information
    and preference-related logic, with no external dependencies.
    """
    name: str
    campsite: str
    preferences: List[str]  # Ranked list of activity names (index 0 = top choice)
    scouts: int = 10  # Number of scouts in troop
    adults: int = 2   # Number of adult leaders
    commissioner: str = ""  # Assigned commissioner (e.g., "Commissioner A")
    day_requests: Dict[str, List[str]] = field(default_factory=dict)  # {"Monday": ["Tie Dye"], "Thursday": ["Itasca"]}
    
    @property
    def size(self) -> int:
        """Total troop size (scouts + adults)."""
        return self.scouts + self.adults
    
    @property
    def size_category(self) -> str:
        """
        Size category based on scout count:
        - Extra Small: 2-5 scouts
        - Small: 6-10 scouts
        - Medium: 11-15 scouts
        - Large: 16-24 scouts
        - Split: 25+ scouts (needs separate schedules)
        """
        if self.scouts <= 5:
            return "Extra Small"
        elif self.scouts <= 10:
            return "Small"
        elif self.scouts <= 15:
            return "Medium"
        elif self.scouts <= 24:
            return "Large"
        else:
            return "Split"
    
    def needs_split(self) -> bool:
        """Troops with 25+ scouts need completely separate schedules."""
        return self.scouts >= 25
    
    def get_priority(self, activity_name: str) -> int:
        """
        Returns priority (lower is better) for an activity.
        Returns 999 if not in preferences.
        
        Args:
            activity_name: Name of the activity to check
            
        Returns:
            Priority ranking (0 = highest priority, 999 = not in preferences)
        """
        try:
            return self.preferences.index(activity_name)
        except ValueError:
            return 999
    
    def is_in_preferences(self, activity_name: str) -> bool:
        """Check if an activity is in the troop's preferences."""
        return activity_name in self.preferences
    
    def get_top_preferences(self, count: int = 5) -> List[str]:
        """
        Get the top N preferences from the troop's preference list.
        
        Args:
            count: Number of top preferences to return
            
        Returns:
            List of activity names (up to count items)
        """
        return self.preferences[:count]
    
    def has_day_request(self, day: str) -> bool:
        """Check if troop has specific requests for a given day."""
        return day in self.day_requests
    
    def get_day_requests(self, day: str) -> List[str]:
        """Get specific activity requests for a given day."""
        return self.day_requests.get(day, [])
    
    def __repr__(self):
        """String representation for debugging"""
        return f"Troop(name='{self.name}', scouts={self.scouts}, campsite='{self.campsite}')"
