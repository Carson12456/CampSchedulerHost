"""
JSON implementation of Troop Repository
Concrete implementation following Clean Architecture
"""
import json
from pathlib import Path
from typing import List, Optional

from interfaces.repositories.troop_repository import TroopRepository
from core.entities.troop import Troop


class JsonTroopRepository(TroopRepository):
    """
    JSON file-based implementation of TroopRepository.
    
    This concrete implementation stores troop data in JSON files,
    following the repository pattern and Clean Architecture principles.
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the JSON troop repository.
        
        Args:
            file_path: Path to the JSON file containing troop data
        """
        self.file_path = Path(file_path)
        self._troops = []
        self._load_troops()
    
    def _load_troops(self) -> None:
        """Load troops from JSON file."""
        if not self.file_path.exists():
            self._troops = []
            return
        
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            self._troops = []
            for troop_data in data.get('troops', []):
                troop = Troop(
                    name=troop_data['name'],
                    campsite=troop_data.get('campsite', troop_data['name']),
                    preferences=troop_data.get('preferences', []),
                    scouts=troop_data.get('scouts', 10),
                    adults=troop_data.get('adults', 2),
                    commissioner=troop_data.get('commissioner', ""),
                    day_requests=troop_data.get('day_requests', {})
                )
                self._troops.append(troop)
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Error loading troops from {self.file_path}: {e}")
            self._troops = []
    
    def _save_troops(self) -> None:
        """Save troops to JSON file."""
        data = {
            'troops': [
                {
                    'name': troop.name,
                    'campsite': troop.campsite,
                    'preferences': troop.preferences,
                    'scouts': troop.scouts,
                    'adults': troop.adults,
                    'commissioner': troop.commissioner,
                    'day_requests': troop.day_requests
                }
                for troop in self._troops
            ]
        }
        
        # Create parent directory if it doesn't exist
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_all(self) -> List[Troop]:
        """Retrieve all troops from the data store."""
        return self._troops.copy()
    
    def get_by_name(self, name: str) -> Optional[Troop]:
        """Retrieve a troop by name."""
        for troop in self._troops:
            if troop.name == name:
                return troop
        return None
    
    def save(self, troop: Troop) -> None:
        """Save a troop to the data store."""
        # Remove existing troop with same name
        self._troops = [t for t in self._troops if t.name != troop.name]
        # Add the new troop
        self._troops.append(troop)
        # Save to file
        self._save_troops()
    
    def delete(self, troop: Troop) -> bool:
        """Delete a troop from the data store."""
        original_length = len(self._troops)
        self._troops = [t for t in self._troops if t.name != troop.name]
        
        if len(self._troops) < original_length:
            self._save_troops()
            return True
        return False
    
    def exists(self, name: str) -> bool:
        """Check if a troop exists in the data store."""
        return self.get_by_name(name) is not None
    
    def get_by_campsite(self, campsite: str) -> List[Troop]:
        """Retrieve all troops assigned to a specific campsite."""
        return [troop for troop in self._troops if troop.campsite == campsite]
    
    def get_by_commissioner(self, commissioner: str) -> List[Troop]:
        """Retrieve all troops assigned to a specific commissioner."""
        return [troop for troop in self._troops if troop.commissioner == commissioner]
    
    def count(self) -> int:
        """Get the total number of troops in the data store."""
        return len(self._troops)
