"""
Capacity rules for Summer Camp Scheduler
Business rules for capacity and staffing constraints
"""
from typing import Set


class CapacityRules:
    """
    Business rules for capacity constraints and staffing limitations.
    
    This class contains rules related to beach staff capacity,
    activity limits, and resource constraints.
    """
    
    # Beach staff activities - limited to 4 per slot to prevent overcrowding
    # These require beach staff supervision (not including unstaffed beach activities)
    BEACH_STAFF_ACTIVITIES = {
        "Aqua Trampoline", "Troop Canoe", "Troop Kayak", "Canoe Snorkel", 
        "Float for Floats", "Greased Watermelon", "Underwater Obstacle Course",
        "Troop Swim", "Water Polo", "Nature Canoe", "Sailing"
    }
    
    MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT = 4
    
    def get_beach_staff_activities(self) -> Set[str]:
        """Get set of activities that require beach staff."""
        return self.BEACH_STAFF_ACTIVITIES.copy()
    
    def is_beach_staff_activity(self, activity_name: str) -> bool:
        """Check if activity requires beach staff."""
        return activity_name in self.BEACH_STAFF_ACTIVITIES
    
    def get_max_beach_staff_activities_per_slot(self) -> int:
        """Get maximum number of beach staff activities per slot."""
        return self.MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT
    
    def can_add_beach_staff_activity(self, current_count: int) -> bool:
        """Check if another beach staff activity can be added to a slot."""
        return current_count < self.MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT
