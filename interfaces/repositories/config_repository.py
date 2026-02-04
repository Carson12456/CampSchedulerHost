"""
Config Repository Interface
Abstract definition for configuration data access following Clean Architecture
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ConfigRepository(ABC):
    """
    Abstract repository for configuration data access.
    
    This interface defines the contract for configuration data persistence
    without specifying the implementation details (JSON, YAML, database, etc.).
    """
    
    @abstractmethod
    def get_config(self, key: str) -> Optional[Any]:
        """Get configuration value by key."""
        pass
    
    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        pass
    
    @abstractmethod
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration values."""
        pass
    
    @abstractmethod
    def load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        pass
    
    @abstractmethod
    def save_config_file(self, file_path: str, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        pass
