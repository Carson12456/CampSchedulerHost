"""
JSON implementation of Schedule Repository
Concrete implementation following Clean Architecture
"""
import json
from pathlib import Path
from typing import List, Optional

from interfaces.repositories.schedule_repository import ScheduleRepository
from core.entities.schedule_entry import ScheduleEntry
from core.entities.troop import Troop
from core.entities.time_slot import TimeSlot


class JsonScheduleRepository(ScheduleRepository):
    """JSON file-based implementation of ScheduleRepository."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._entries = []
        self._load_entries()
    
    def _load_entries(self) -> None:
        """Load schedule entries from JSON file."""
        if not self.file_path.exists():
            self._entries = []
            return
        
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # This is a simplified version - in practice, you'd need to reconstruct
            # the actual Troop and Activity objects from the stored data
            self._entries = []  # Placeholder
        except (json.JSONDecodeError, FileNotFoundError):
            self._entries = []
    
    def get_all_entries(self) -> List[ScheduleEntry]:
        """Get all schedule entries."""
        return self._entries.copy()
    
    def get_entries_for_troop(self, troop: Troop) -> List[ScheduleEntry]:
        """Get all entries for a specific troop."""
        return [entry for entry in self._entries if entry.troop.name == troop.name]
    
    def get_entries_for_time_slot(self, time_slot: TimeSlot) -> List[ScheduleEntry]:
        """Get all entries for a specific time slot."""
        return [entry for entry in self._entries if entry.time_slot == time_slot]
    
    def save_entry(self, entry: ScheduleEntry) -> None:
        """Save a schedule entry."""
        self._entries.append(entry)
    
    def delete_entry(self, entry: ScheduleEntry) -> bool:
        """Delete a schedule entry."""
        try:
            self._entries.remove(entry)
            return True
        except ValueError:
            return False
    
    def clear_all(self) -> None:
        """Clear all schedule entries."""
        self._entries.clear()
