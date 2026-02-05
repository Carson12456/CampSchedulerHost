"""
Configuration Loader (Item 6)
Loads YAML configuration files for camp settings and constraints.
"""
import yaml
from pathlib import Path
from typing import Dict, Any

class CampConfig:
    """Camp configuration loader and accessor."""
    
    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)
        self.camp_config = None
        self.constraint_config = None
        self._load_configs()
    
    def _load_configs(self):
        """Load all configuration files."""
        try:
            # Load camp config
            camp_file = self.config_dir / "camp_config.yaml"
            if camp_file.exists():
                with open(camp_file, 'r') as f:
                    self.camp_config = yaml.safe_load(f)
            
            # Load constraint config
            constraint_file = self.config_dir / "activity_constraints.yaml"
            if constraint_file.exists():
                with open(constraint_file, 'r') as f:
                    self.constraint_config = yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Error loading config files: {e}")
            print("Using default hardcoded values")
    
    def get_camp_setting(self, key: str, default=None):
        """Get a camp setting by dot notation (e.g., 'camp.name')."""
        if not self.camp_config:
            return default
        
        keys = key.split('.')
        value = self.camp_config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_constraint(self, key: str, default=None):
        """Get a constraint setting by key."""
        if not self.constraint_config:
            return default
        return self.constraint_config.get(key, default)
    
    def get_commissioners(self):
        """Get commissioner configuration."""
        return self.get_camp_setting('commissioners', [])
    
    def get_exclusive_areas(self):
        """Get exclusive area definitions."""
        return self.get_constraint('exclusive_areas', {})
    
    def get_wet_activities(self):
        """Get wet activity list."""
        return self.get_constraint('wet_activities', [])
    
    def get_tower_ods_activities(self):
        """Get Tower/ODS activity list."""
        return self.get_constraint('tower_ods_activities', [])
    
    def get_accuracy_activities(self):
        """Get accuracy activity list."""
        constraint = self.get_constraint('accuracy_limit', {})
        return constraint.get('activities', [])
    
    def get_beach_activities(self):
        """Get beach activity list."""
        constraint = self.get_constraint('beach_slot_constraint', {})
        return constraint.get('activities', [])
    
    def get_default_fill_priority(self):
        """Get default fill priority list."""
        return self.get_camp_setting('default_fill_priority', [])
    
    def get_capacity_setting(self, key: str, default=None):
        """Get capacity setting."""
        capacities = self.get_camp_setting('capacity', {})
        return capacities.get(key, default)

# Global config instance
_config = None

def get_config():
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CampConfig()
    return _config

def reload_config():
    """Reload configuration from files."""
    global _config
    _config = CampConfig()
    return _config

# Example usage
if __name__ == "__main__":
    config = get_config()
    
    print("Camp Configuration")
    print("=" * 50)
    print(f"Camp Name: {config.get_camp_setting('camp.name')}")
    print(f"Total Weeks: {config.get_camp_setting('camp.total_weeks')}")
    print(f"Slots Per Day: {config.get_camp_setting('camp.slots_per_day')}")
    print(f"\nMax Beach Staff: {config.get_capacity_setting('max_beach_staff_per_slot')}")
    print(f"Max Canoe Capacity: {config.get_capacity_setting('max_canoe_capacity')}")
    
    print(f"\nCommissioners: {len(config.get_commissioners())}")
    for comm in config.get_commissioners():
        print(f"  - {comm['name']}: {len(comm['troops'])} troops")
    
    print(f"\nExclusive Areas: {len(config.get_exclusive_areas())}")
    for area in config.get_exclusive_areas():
        print(f"  - {area}")
    
    print(f"\nWet Activities: {len(config.get_wet_activities())}")
    print(f"Accuracy Activities: {len(config.get_accuracy_activities())}")
