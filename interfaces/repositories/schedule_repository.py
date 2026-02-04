"""
Schedule Repository Interface
Abstract definition for schedule data access following Clean Architecture
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from core.entities.schedule_entry import ScheduleEntry
from core.entities.troop import Troop
from core.entities.time_slot import TimeSlot


class ScheduleRepository(ABC):
    """
    Abstract repository for schedule data access.
    
    This interface defines the contract for schedule data persistence
    without specifying the implementation details (JSON, database, etc.).
    """
    
    @abstractmethod
    def get_all_entries(self) -> List[ScheduleEntry]:
        """Get all schedule entries."""
        pass
    
    @abstractmethod
    def get_entries_for_troop(self, troop: Troop) -> List[ScheduleEntry]:
        """Get all entries for a specific troop."""
        pass
    
    @abstractmethod
    def get_entries_for_time_slot(self, time_slot: TimeSlot) -> List[ScheduleEntry]:
        """Get all entries for a specific time slot."""
        pass
    
    @abstractmethod
    def save_entry(self, entry: ScheduleEntry) -> None:
        """Save a schedule entry."""
        pass
    
    @abstractmethod
    def delete_entry(self, entry: ScheduleEntry) -> bool:
        """Delete a schedule entry."""
        pass
    
    @abstractmethod
    def clear_all(self) -> None:
        """Clear all schedule entries."""
        pass
