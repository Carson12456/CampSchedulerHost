"""
Activity rules sourced from SKULL-backed configuration.
"""

from typing import Dict, List, Optional, Set, Tuple

from core.scheduler import config_loader


class ActivityRules:
    """
    Business rules for activity scheduling and constraints.
    """

    EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()
    BEACH_ACTIVITIES = config_loader.get_activities_with_tag("beach")
    WET_ACTIVITIES = config_loader.get_activities_with_tag("wet")
    TOWER_ODS_ACTIVITIES = config_loader.get_activities_with_tag("tower_ods")
    ACCURACY_ACTIVITIES = config_loader.get_activities_with_tag("accuracy")
    THREE_HOUR_ACTIVITIES = config_loader.get_three_hour_activities()
    NON_CONSECUTIVE_ACTIVITIES = config_loader.get_non_consecutive_activities()
    BEACH_PROHIBITED_PAIR = set(config_loader.get_spine_beach_prohibited_pair())

    # The clean-architecture rules package still expects a single same-day
    # conflict list. Keep that compatibility behavior, but source the contents
    # from SKULL instead of hardcoding them here.
    SAME_DAY_CONFLICTS = config_loader.get_compatibility_same_day_conflicts()
    SOFT_SAME_DAY_CONFLICTS = [tuple(pair) for pair in config_loader.get_soft_prohibited_pairs()]

    def get_exclusive_areas(self) -> Dict[str, List[str]]:
        """Get the exclusive areas mapping."""
        return self.EXCLUSIVE_AREAS.copy()

    def is_activity_exclusive(self, activity_name: str) -> bool:
        """Check if an activity is exclusive."""
        return self.get_exclusive_area_for_activity(activity_name) is not None

    def get_exclusive_area_for_activity(self, activity_name: str) -> Optional[str]:
        """Get the exclusive area for an activity."""
        for area, activities in self.EXCLUSIVE_AREAS.items():
            if activity_name in activities:
                return area
        return None

    def get_activities_in_area(self, area: str) -> List[str]:
        """Get all activities in an exclusive area."""
        return self.EXCLUSIVE_AREAS.get(area, []).copy()

    def are_activities_same_exclusive_area(self, activity1: str, activity2: str) -> bool:
        """Check if two activities are in the same exclusive area."""
        area1 = self.get_exclusive_area_for_activity(activity1)
        area2 = self.get_exclusive_area_for_activity(activity2)
        return area1 is not None and area1 == area2

    def get_wet_activities(self) -> List[str]:
        """Get the configured wet activities."""
        return self.WET_ACTIVITIES.copy()

    def is_wet_activity(self, activity_name: str) -> bool:
        """Check if an activity is wet."""
        return activity_name in self.WET_ACTIVITIES

    def get_tower_ods_activities(self) -> List[str]:
        """Get tower and ODS activities."""
        return self.TOWER_ODS_ACTIVITIES.copy()

    def is_tower_ods_activity(self, activity_name: str) -> bool:
        """Check if an activity is tower/ODS."""
        return activity_name in self.TOWER_ODS_ACTIVITIES

    def get_accuracy_activities(self) -> List[str]:
        """Get configured accuracy activities."""
        return self.ACCURACY_ACTIVITIES.copy()

    def is_accuracy_activity(self, activity_name: str) -> bool:
        """Check if an activity is an accuracy activity."""
        return activity_name in self.ACCURACY_ACTIVITIES

    def get_three_hour_activities(self) -> List[str]:
        """Get configured 3-hour activities."""
        return self.THREE_HOUR_ACTIVITIES.copy()

    def is_three_hour_activity(self, activity_name: str) -> bool:
        """Check if an activity is a 3-hour activity."""
        return activity_name in self.THREE_HOUR_ACTIVITIES

    def get_non_consecutive_activities(self) -> List[str]:
        """Get activities that do not need consecutive-slot optimization."""
        return self.NON_CONSECUTIVE_ACTIVITIES.copy()

    def is_non_consecutive_activity(self, activity_name: str) -> bool:
        """Check if an activity does not need consecutive-slot optimization."""
        return activity_name in self.NON_CONSECUTIVE_ACTIVITIES

    def get_beach_activities(self) -> List[str]:
        """Get configured beach activities."""
        return self.BEACH_ACTIVITIES.copy()

    def is_beach_activity(self, activity_name: str) -> bool:
        """Check if an activity is a beach activity."""
        return activity_name in self.BEACH_ACTIVITIES

    def get_beach_prohibited_pairs(self) -> Set[str]:
        """Get the configured AT/WP/GM beach-pairing set."""
        return self.BEACH_PROHIBITED_PAIR.copy()

    def are_beach_activities_prohibited_pair(self, activity1: str, activity2: str) -> bool:
        """Check if two activities are in the configured beach-pairing conflict set."""
        return (
            activity1 in self.BEACH_PROHIBITED_PAIR
            and activity2 in self.BEACH_PROHIBITED_PAIR
            and activity1 != activity2
        )

    def get_same_day_conflicts(self) -> List[Tuple[str, str]]:
        """Get same-day conflict pairs used by the legacy rules layer."""
        return self.SAME_DAY_CONFLICTS.copy()

    def have_same_day_conflict(self, activity1: str, activity2: str) -> bool:
        """Check if two activities conflict in the legacy same-day rules layer."""
        return (activity1, activity2) in self.SAME_DAY_CONFLICTS or (activity2, activity1) in self.SAME_DAY_CONFLICTS

    def get_soft_same_day_conflicts(self) -> List[Tuple[str, str]]:
        """Get configured soft same-day conflict pairs."""
        return self.SOFT_SAME_DAY_CONFLICTS.copy()

    def have_soft_same_day_conflict(self, activity1: str, activity2: str) -> bool:
        """Check if two activities have a configured soft same-day conflict."""
        return (activity1, activity2) in self.SOFT_SAME_DAY_CONFLICTS or (
            activity2,
            activity1,
        ) in self.SOFT_SAME_DAY_CONFLICTS
