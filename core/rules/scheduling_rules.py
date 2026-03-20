"""
Scheduling rules sourced from SKULL-backed configuration.
"""

from typing import List

from core.scheduler import config_loader


class SchedulingRules:
    """
    Business rules for scheduling patterns and generic fill behavior.
    """

    DEFAULT_FILL_PRIORITY = config_loader.get_fill_priority()
    CONCURRENT_ACTIVITIES = config_loader.get_concurrent_activities()

    def get_default_fill_priority(self) -> List[str]:
        """Get default activity priority for filling slots."""
        return self.DEFAULT_FILL_PRIORITY.copy()

    def get_concurrent_activities(self) -> List[str]:
        """Get activities that can have multiple troops at once."""
        return self.CONCURRENT_ACTIVITIES.copy()

    def is_concurrent_activity(self, activity_name: str) -> bool:
        """Check if an activity can have multiple troops at once."""
        return activity_name in self.CONCURRENT_ACTIVITIES

    def get_fill_priority_for_troop(self, troop_preferences: List[str]) -> List[str]:
        """
        Get fill priority customized for a specific troop.
        """
        priority = troop_preferences.copy()
        for activity in self.DEFAULT_FILL_PRIORITY:
            if activity not in priority:
                priority.append(activity)
        return priority
