"""
Scheduling rules for Summer Camp Scheduler
Business rules for scheduling constraints and patterns
"""
from typing import List


class SchedulingRules:
    """
    Business rules for scheduling patterns and constraints.
    
    This class contains rules related to scheduling patterns,
    time constraints, and activity sequencing.
    """
    
    # Default priority order for filling remaining slots when troop doesn't have enough preferences
    # Note: Gaga Ball and 9 Square are at the END because they're flexible (middle of camp, short duration)
    # Note: Delta is NOT in this list - it's only scheduled for troops who request it in preferences
    DEFAULT_FILL_PRIORITY = [
        "Super Troop",
        "Aqua Trampoline",
        # "Climbing Tower", # Removed to prevent accidental stacking as fill
        "Archery",
        "Water Polo",
        "Troop Rifle",
        "Gaga Ball",  # Balls last - flexible, middle of camp
        "9 Square",   # Balls last - flexible, middle of camp
        "Troop Swim",
        "Sailing",
        "Trading Post",  # Trading Post / Showerhouse
        "GPS & Geocaching",  # ODS Activity
        # "Disc Golf", # Removed to prevent orphan entries (needs pair)
        "Hemp Craft",  # Handicrafts (Tie Dye removed - only schedule if requested)
        "Dr. DNA",  # Nature Activity
        "Loon Lore",  # Nature Activity
        "Fishing",
        "Campsite Free Time",  # In site time
    ]
    
    # Activities that can have multiple troops at once
    CONCURRENT_ACTIVITIES = ["Reflection", "Campsite Free Time"]
    
    def get_default_fill_priority(self) -> List[str]:
        """Get default activity priority for filling slots."""
        return self.DEFAULT_FILL_PRIORITY.copy()
    
    def get_concurrent_activities(self) -> List[str]:
        """Get activities that can have multiple troops at once."""
        return self.CONCURRENT_ACTIVITIES.copy()
    
    def is_concurrent_activity(self, activity_name: str) -> bool:
        """Check if activity can have multiple troops at once."""
        return activity_name in self.CONCURRENT_ACTIVITIES
    
    def get_fill_priority_for_troop(self, troop_preferences: List[str]) -> List[str]:
        """
        Get fill priority customized for a specific troop.
        
        Args:
            troop_preferences: List of troop's preferred activities
            
        Returns:
            Customized fill priority list
        """
        # Start with troop preferences, then add default priorities
        priority = troop_preferences.copy()
        
        # Add default priorities that aren't already in troop preferences
        for activity in self.DEFAULT_FILL_PRIORITY:
            if activity not in priority:
                priority.append(activity)
        
        return priority
