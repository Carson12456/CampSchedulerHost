"""
Troop Repository Interface
Abstract definition for troop data access following Clean Architecture
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from core.entities.troop import Troop


class TroopRepository(ABC):
    """
    Abstract repository for troop data access.
    
    This interface defines the contract for troop data persistence
    without specifying the implementation details (JSON, database, etc.).
    Following Clean Architecture principles, this interface depends only
    on core entities and has no external dependencies.
    """
    
    @abstractmethod
    def get_all(self) -> List[Troop]:
        """
        Retrieve all troops from the data store.
        
        Returns:
            List of all troops in the system
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Troop]:
        """
        Retrieve a troop by name.
        
        Args:
            name: The name of the troop to retrieve
            
        Returns:
            The troop if found, None otherwise
        """
        pass
    
    @abstractmethod
    def save(self, troop: Troop) -> None:
        """
        Save a troop to the data store.
        
        Args:
            troop: The troop to save
        """
        pass
    
    @abstractmethod
    def delete(self, troop: Troop) -> bool:
        """
        Delete a troop from the data store.
        
        Args:
            troop: The troop to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        pass
    
    @abstractmethod
    def exists(self, name: str) -> bool:
        """
        Check if a troop exists in the data store.
        
        Args:
            name: The name of the troop to check
            
        Returns:
            True if troop exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_by_campsite(self, campsite: str) -> List[Troop]:
        """
        Retrieve all troops assigned to a specific campsite.
        
        Args:
            campsite: The campsite name
            
        Returns:
            List of troops at the specified campsite
        """
        pass
    
    @abstractmethod
    def get_by_commissioner(self, commissioner: str) -> List[Troop]:
        """
        Retrieve all troops assigned to a specific commissioner.
        
        Args:
            commissioner: The commissioner name
            
        Returns:
            List of troops assigned to the specified commissioner
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get the total number of troops in the data store.
        
        Returns:
            Total count of troops
        """
        pass
