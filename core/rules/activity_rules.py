"""
Activity rules for Summer Camp Scheduler
Business rules and constraints for activities
"""
from typing import Dict, List, Set, Tuple, Optional


class ActivityRules:
    """
    Business rules for activity scheduling and constraints.
    
    This class contains all business logic related to activity constraints,
    exclusive areas, and scheduling rules that were previously embedded
    in the models.py file.
    """
    
    # Activity exclusive areas - only one troop can have activities from each area per slot
    EXCLUSIVE_AREAS = {
        "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", "Ultimate Survivor", 
                          "What's Cooking", "Chopped!"],
        "Tower": ["Climbing Tower"],
        "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
        "Archery": ["Archery"],
        "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
        "Nature Center": ["Dr. DNA", "Loon Lore"],
        # Commissioner-led activities - EXCLUSIVE (one troop at a time per commissioner)
        "Delta": ["Delta"],
        "Super Troop": ["Super Troop"],
        "Sailing": ["Sailing"],  # Sailing IS exclusive - only 1 troop per slot
        # Note: Reflection can have multiple troops (all troops do Reflection on Friday)
        # Note: 3-hour off-camp activities can have multiple troops
        # Beach activities - each exclusive (only one troop per activity per slot)
        "Aqua Trampoline": ["Aqua Trampoline"],
        "Water Polo": ["Water Polo"],
        "Greased Watermelon": ["Greased Watermelon"],
        "Troop Swim": ["Troop Swim"],
        "Float for Floats": ["Float for Floats"],
        "Canoe Snorkel": ["Canoe Snorkel"],
        "Troop Canoe": ["Troop Canoe"],
        "Nature Canoe": ["Nature Canoe"],
        "Fishing": ["Fishing"],
        # Other activities
        "History Center": ["History Center"],
        "Trading Post": ["Trading Post"],
        "Sauna": ["Sauna"],
        "Shower House": ["Shower House"],
        "Disc Golf": ["Disc Golf"],
    }
    
    # Beach activities that should ideally be on different days (soft constraint)
    BEACH_ACTIVITIES = ["Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim", 
                       "Underwater Obstacle Course", "Float for Floats", "Canoe Snorkel"]
    
    # WET activities - cannot have Tower/ODS immediately before or after
    WET_ACTIVITIES = [
        "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", "Underwater Obstacle Course",
        "Troop Canoe", "Troop Kayak", "Canoe Snorkel", "Nature Canoe", "Float for Floats", "Sailing", "Sauna"
    ]
    
    # Tower and ODS activities - cannot be scheduled after wet activities
    TOWER_ODS_ACTIVITIES = [
        "Climbing Tower", "Knots and Lashings", "Orienteering", "GPS & Geocaching",
        "Ultimate Survivor", "What's Cooking", "Chopped!"
    ]
    
    # Accuracy activities (max 1 per day per troop)
    ACCURACY_ACTIVITIES = ["Troop Rifle", "Troop Shotgun", "Archery"]
    
    # 3-hour activities
    THREE_HOUR_ACTIVITIES = ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"]
    
    # Activities that don't need consecutive slot optimization
    NON_CONSECUTIVE_ACTIVITIES = [
        "Trading Post", "Campsite Free Time",
        "Itasca State Park", "Tamarac Wildlife Refuge", "Back of the Moon", 
        "Disc Golf", "History Center"
    ]
    
    # Beach activities prohibited pairs - no pair on same day
    BEACH_PROHIBITED_PAIR = {"Aqua Trampoline", "Water Polo", "Greased Watermelon"}
    
    # Activities that cannot be on the same day for a troop (HARD constraints)
    SAME_DAY_CONFLICTS = [
        ("Trading Post", "Campsite Free Time"),
        ("Trading Post", "Shower House"),  # Re-enabled per .cursorrules
        # Beach prohibited pairs
        ("Aqua Trampoline", "Water Polo"),
        ("Aqua Trampoline", "Greased Watermelon"),
        ("Water Polo", "Greased Watermelon"),
        # Canoe activities - no two canoeing activities on same day
        ("Troop Canoe", "Canoe Snorkel"),
        ("Troop Canoe", "Nature Canoe"),
        ("Troop Canoe", "Float for Floats"),
        ("Canoe Snorkel", "Nature Canoe"),
        ("Canoe Snorkel", "Float for Floats"),
        ("Nature Canoe", "Float for Floats"),
    ]
    
    # Activities to AVOID on same day (SOFT constraints - try to avoid)
    SOFT_SAME_DAY_CONFLICTS = [
        ("Fishing", "Trading Post"),
        ("Fishing", "Shower House"),
        ("Disc Golf", "Trading Post"),
        ("Disc Golf", "Shower House"),
    ]
    
    def get_exclusive_areas(self) -> Dict[str, List[str]]:
        """Get the exclusive areas mapping."""
        return self.EXCLUSIVE_AREAS.copy()
    
    def is_activity_exclusive(self, activity_name: str) -> bool:
        """
        Check if an activity is exclusive (only one troop per slot).
        
        Args:
            activity_name: Name of the activity to check
            
        Returns:
            True if activity is exclusive, False otherwise
        """
        for area, activities in self.EXCLUSIVE_AREAS.items():
            if activity_name in activities:
                return True
        return False
    
    def get_exclusive_area_for_activity(self, activity_name: str) -> Optional[str]:
        """
        Get the exclusive area for an activity.
        
        Args:
            activity_name: Name of the activity
            
        Returns:
            Area name if activity is exclusive, None otherwise
        """
        for area, activities in self.EXCLUSIVE_AREAS.items():
            if activity_name in activities:
                return area
        return None
    
    def get_activities_in_area(self, area: str) -> List[str]:
        """
        Get all activities in an exclusive area.
        
        Args:
            area: Name of the exclusive area
            
        Returns:
            List of activity names in the area
        """
        return self.EXCLUSIVE_AREAS.get(area, []).copy()
    
    def are_activities_same_exclusive_area(self, activity1: str, activity2: str) -> bool:
        """
        Check if two activities are in the same exclusive area.
        
        Args:
            activity1: First activity name
            activity2: Second activity name
            
        Returns:
            True if both activities are in the same exclusive area
        """
        area1 = self.get_exclusive_area_for_activity(activity1)
        area2 = self.get_exclusive_area_for_activity(activity2)
        return area1 is not None and area1 == area2
    
    def get_wet_activities(self) -> List[str]:
        """Get list of wet activities."""
        return self.WET_ACTIVITIES.copy()
    
    def is_wet_activity(self, activity_name: str) -> bool:
        """Check if activity is a wet activity."""
        return activity_name in self.WET_ACTIVITIES
    
    def get_tower_ods_activities(self) -> List[str]:
        """Get list of tower and ODS activities."""
        return self.TOWER_ODS_ACTIVITIES.copy()
    
    def is_tower_ods_activity(self, activity_name: str) -> bool:
        """Check if activity is a tower/ODS activity."""
        return activity_name in self.TOWER_ODS_ACTIVITIES
    
    def get_accuracy_activities(self) -> List[str]:
        """Get list of accuracy activities."""
        return self.ACCURACY_ACTIVITIES.copy()
    
    def is_accuracy_activity(self, activity_name: str) -> bool:
        """Check if activity is an accuracy activity."""
        return activity_name in self.ACCURACY_ACTIVITIES
    
    def get_three_hour_activities(self) -> List[str]:
        """Get list of 3-hour activities."""
        return self.THREE_HOUR_ACTIVITIES.copy()
    
    def is_three_hour_activity(self, activity_name: str) -> bool:
        """Check if activity is a 3-hour activity."""
        return activity_name in self.THREE_HOUR_ACTIVITIES
    
    def get_non_consecutive_activities(self) -> List[str]:
        """Get activities that don't need consecutive slot optimization."""
        return self.NON_CONSECUTIVE_ACTIVITIES.copy()
    
    def is_non_consecutive_activity(self, activity_name: str) -> bool:
        """Check if activity needs consecutive slot optimization."""
        return activity_name in self.NON_CONSECUTIVE_ACTIVITIES
    
    def get_beach_activities(self) -> List[str]:
        """Get list of beach activities."""
        return self.BEACH_ACTIVITIES.copy()
    
    def is_beach_activity(self, activity_name: str) -> bool:
        """Check if activity is a beach activity."""
        return activity_name in self.BEACH_ACTIVITIES
    
    def get_beach_prohibited_pairs(self) -> Set[str]:
        """Get beach activities that cannot be paired on same day."""
        return self.BEACH_PROHIBITED_PAIR.copy()
    
    def are_beach_activities_prohibited_pair(self, activity1: str, activity2: str) -> bool:
        """
        Check if two beach activities are a prohibited pair.
        
        Args:
            activity1: First beach activity name
            activity2: Second beach activity name
            
        Returns:
            True if activities cannot be on same day
        """
        return (activity1 in self.BEACH_PROHIBITED_PAIR and 
                activity2 in self.BEACH_PROHIBITED_PAIR and
                activity1 != activity2)
    
    def get_same_day_conflicts(self) -> List[Tuple[str, str]]:
        """Get hard same day conflict pairs."""
        return self.SAME_DAY_CONFLICTS.copy()
    
    def have_same_day_conflict(self, activity1: str, activity2: str) -> bool:
        """
        Check if two activities have a hard same day conflict.
        
        Args:
            activity1: First activity name
            activity2: Second activity name
            
        Returns:
            True if activities cannot be on same day
        """
        return (activity1, activity2) in self.SAME_DAY_CONFLICTS or \
               (activity2, activity1) in self.SAME_DAY_CONFLICTS
    
    def get_soft_same_day_conflicts(self) -> List[Tuple[str, str]]:
        """Get soft same day conflict pairs."""
        return self.SOFT_SAME_DAY_CONFLICTS.copy()
    
    def have_soft_same_day_conflict(self, activity1: str, activity2: str) -> bool:
        """
        Check if two activities have a soft same day conflict.
        
        Args:
            activity1: First activity name
            activity2: Second activity name
            
        Returns:
            True if activities should avoid being on same day
        """
        return (activity1, activity2) in self.SOFT_SAME_DAY_CONFLICTS or \
               (activity2, activity1) in self.SOFT_SAME_DAY_CONFLICTS
