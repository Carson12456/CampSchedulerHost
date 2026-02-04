"""
Activity Repository Interface
Abstract definition for activity data access following Clean Architecture
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from core.entities.activity import Activity


class ActivityRepository(ABC):
    """
    Abstract repository for activity data access.
    
    This interface defines the contract for activity data persistence
    without specifying the implementation details (JSON, database, etc.).
    """
    
    @abstractmethod
    def get_all(self) -> List[Activity]:
        """Get all activities."""
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Activity]:
        """Get an activity by name."""
        pass
    
    @abstractmethod
    def save(self, activity: Activity) -> None:
        """Save an activity."""
        pass
    
    @abstractmethod
    def delete(self, activity: Activity) -> bool:
        """Delete an activity."""
        pass
    
    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if an activity exists."""
        pass
