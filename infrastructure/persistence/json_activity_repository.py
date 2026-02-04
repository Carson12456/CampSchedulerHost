"""
JSON implementation of Activity Repository
Concrete implementation following Clean Architecture
"""
import json
from pathlib import Path
from typing import List, Optional

from interfaces.repositories.activity_repository import ActivityRepository
from core.entities.activity import Activity
from core.entities.activity import Zone


class JsonActivityRepository(ActivityRepository):
    """JSON file-based implementation of ActivityRepository."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._activities = []
        self._load_activities()
    
    def _load_activities(self) -> None:
        """Load activities from JSON file."""
        if not self.file_path.exists():
            self._activities = []
            return
        
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            self._activities = []
            for activity_data in data.get('activities', []):
                activity = Activity(
                    name=activity_data['name'],
                    slots=activity_data['slots'],
                    zone=Zone(activity_data['zone']),
                    staff=activity_data.get('staff'),
                    conflicts_with=activity_data.get('conflicts_with', [])
                )
                self._activities.append(activity)
        except (json.JSONDecodeError, FileNotFoundError):
            self._activities = []
    
    def get_all(self) -> List[Activity]:
        """Get all activities."""
        return self._activities.copy()
    
    def get_by_name(self, name: str) -> Optional[Activity]:
        """Get an activity by name."""
        for activity in self._activities:
            if activity.name == name:
                return activity
        return None
    
    def save(self, activity: Activity) -> None:
        """Save an activity."""
        # Remove existing activity with same name
        self._activities = [a for a in self._activities if a.name != activity.name]
        # Add the new activity
        self._activities.append(activity)
    
    def delete(self, activity: Activity) -> bool:
        """Delete an activity."""
        original_length = len(self._activities)
        self._activities = [a for a in self._activities if a.name != activity.name]
        return len(self._activities) < original_length
    
    def exists(self, name: str) -> bool:
        """Check if an activity exists."""
        return self.get_by_name(name) is not None
