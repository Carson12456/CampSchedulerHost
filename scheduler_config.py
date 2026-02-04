"""
Configuration system for Summer Camp Scheduler
Loads scheduling rules from YAML files for easy customization
"""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from models import Day


class SchedulerConfig:
    """Configuration manager for scheduler"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config = {}
        
    def load_all(self):
        """Load all configuration files"""
        self.load_scheduler_rules()
        self.load_commissioners()
        self.load_activity_rules()
        self.load_capacity_limits()
    
    def load_scheduler_rules(self) -> Dict[str, Any]:
        """Load main scheduling rules"""
        config_file = self.config_dir / "scheduler_rules.yaml"
        
        if not config_file.exists():
            # Return defaults if file doesn't exist
            return self._get_default_scheduler_rules()
        
        with open(config_file, 'r') as f:
            self.config['scheduler_rules'] = yaml.safe_load(f)
        
        return self.config['scheduler_rules']
    
    def load_commissioners(self, mode: str = "tc") -> Dict:
        """Load commissioner assignments"""
        config_file = self.config_dir / f"{mode}_commissioners.yaml"
        
        if not config_file.exists():
            return self._get_default_commissioners(mode)
        
        with open(config_file, 'r') as f:
            self.config['commissioners'] = yaml.safe_load(f)
        
        return self.config['commissioners']
    
    def load_activity_rules(self) -> Dict[str, Any]:
        """Load activity-specific rules"""
        config_file = self.config_dir / "activity_rules.yaml"
        
        if not config_file.exists():
            return self._get_default_activity_rules()
        
        with open(config_file, 'r') as f:
            self.config['activity_rules'] = yaml.safe_load(f)
        
        return self.config['activity_rules']
    
    def load_capacity_limits(self) -> Dict[str, Any]:
        """Load capacity and staff limits"""
        config_file = self.config_dir / "capacity_limits.yaml"
        
        if not config_file.exists():
            return self._get_default_capacity_limits()
        
        with open(config_file, 'r') as f:
            self.config['capacity'] = yaml.safe_load(f)
        
        return self.config['capacity']
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _get_default_scheduler_rules(self) -> Dict:
        """Default scheduler rules"""
        return {
            'constraints': {
                'beach_slot_rule': {
                    'allowed_slots': [1, 3],
                    'thursday_slot_2_allowed': True
                },
                'accuracy_limit': {
                    'max_per_day': 1,
                    'activities': ['Troop Rifle', 'Troop Shotgun', 'Archery']
                },
                'friday_reflection': {
                    'required': True,
                    'commissioner_clustering': True
                },
                'delta_before_super_troop': True,
                'max_accuracy_per_day': 1
            },
            'optimization': {
                'area_clustering_priority': [
                    'Tower',
                    'Rifle Range',
                    'Archery',
                    'Outdoor Skills'
                ],
                'consecutive_activities': ['Tie Dye', 'Archery'],
                'avoid_friday': ['Archery'],
                'archery_target_days': 2,
                'enable_smart_balls_scheduling': True,
                'enable_area_day_filling': True
            },
            'scheduling': {
                'default_fill_priority': [
                    'Super Troop',
                    'Aqua Trampoline',
                    'Climbing Tower',
                    'Archery',
                    'Water Polo',
                    'Troop Rifle',
                    'Gaga Ball',
                    '9 Square',
                    'Troop Swim',
                    'Sailing',
                    'Trading Post',
                    'GPS & Geocaching',
                    'Disc Golf',
                    'Hemp Craft',
                    'Dr. DNA',
                    'Loon Lore',
                    'Fishing',
                    'Campsite Free Time'
                ]
            }
        }
    
    def _get_default_commissioners(self, mode: str) -> Dict:
        """Default commissioner assignments"""
        if mode == "tc":
            return {
                'troops': {
                    'Commissioner A': ['Tecumseh', 'Red Cloud', 'Massasoit', 'Joseph', 'Skenandoa'],
                    'Commissioner B': ['Tamanend', 'Samoset', 'Black Hawk', 'Sequoyah'],
                    'Commissioner C': ['Taskalusa', 'Powhatan', 'Cochise', 'Pontiac']
                },
                'delta_days': {
                    'Commissioner A': 'Tuesday',
                    'Commissioner B': 'Wednesday',
                    'Commissioner C': 'Thursday'
                },
                'super_troop_days': {
                    'Commissioner A': 'Tuesday',
                    'Commissioner B': 'Wednesday',
                    'Commissioner C': 'Thursday'
                },
                'archery_days': {
                    'Commissioner A': 'Wednesday',
                    'Commissioner B': 'Friday',
                    'Commissioner C': 'Monday'
                },
                'tower_ods_days': {
                    'Commissioner A': 'Thursday',
                    'Commissioner B': 'Monday',
                    'Commissioner C': 'Tuesday'
                }
            }
        elif mode == "voyageur":
            return {
                'troops': {
                    'Voyageur A': [],
                    'Voyageur B': [],
                    'Voyageur C': []
                },
                'delta_days': {
                    'Voyageur A': 'Monday',
                    'Voyageur B': 'Wednesday',
                    'Voyageur C': 'Friday'
                },
                'super_troop_days': {
                    'Voyageur A': 'Monday',
                    'Voyageur B': 'Wednesday',
                    'Voyageur C': 'Friday'
                },
                'archery_days': {
                    'Voyageur A': 'Monday',
                    'Voyageur B': 'Wednesday',
                    'Voyageur C': 'Friday'
                },
                'tower_ods_days': {
                    'Voyageur A': 'Tuesday',
                    'Voyageur B': 'Thursday',
                    'Voyageur C': 'Monday'
                }
            }
        
        return {}
    
    def _get_default_activity_rules(self) -> Dict:
        """Default activity rules"""
        return {
            'exclusive_areas': {
                'Handicrafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
                'Delta': ['Delta'],
                'Super Troop': ['Super Troop'],
                'Tower': ['Climbing Tower'],
                'Rifle Range': ['Troop Rifle', 'Troop Shotgun'],
                'Archery': ['Archery'],
                'Sailing': ['Sailing'],
                'Outdoor Skills': [
                    'Knots and Lashings',
                    'Orienteering',
                    'GPS & Geocaching',
                    'Ultimate Survivor',
                    "What's Cooking",
                    'Chopped!'
                ],
                'Nature Center': ['Dr. DNA', 'Loon Lore', 'Nature Canoe']
            },
            'wet_activities': [
                'Aqua Trampoline',
                'Water Polo',
                'Greased Watermelon',
                'Troop Swim',
                'Underwater Obstacle Course',
                'Troop Canoe',
                'Troop Kayak',
                'Canoe Snorkel',
                'Nature Canoe',
                'Float for Floats',
                'Sailing',
                'Sauna',
                'Delta'
            ],
            'three_hour_activities': [
                'Tamarac Wildlife Refuge',
                'Itasca State Park',
                'Back of the Moon'
            ],
            'area_pairs': {
                'Tower': 'Outdoor Skills',
                'Outdoor Skills': 'Tower',
                'Rifle Range': 'Super Troop',
                'Super Troop': 'Rifle Range'
            },
            'same_day_conflicts': [
                ['Trading Post', 'Campsite Free Time'],
                ['Trading Post', 'Shower House'],
                ['Troop Canoe', 'Canoe Snorkel'],
                ['Troop Canoe', 'Nature Canoe'],
                ['Troop Canoe', 'Float for Floats'],
                ['Canoe Snorkel', 'Nature Canoe'],
                ['Canoe Snorkel', 'Float for Floats'],
                ['Nature Canoe', 'Float for Floats']
            ]
        }
    
    def _get_default_capacity_limits(self) -> Dict:
        """Default capacity limits"""
        return {
            'beach_staff_per_slot': 12,
            'canoe_capacity': 26,
            'tower_extended_size': 15,
            'sailing_extended_size': 12,
            'aqua_trampoline': {
                'max_small_troops': 2,
                'small_troop_size': 16
            }
        }


def create_default_config_files(config_dir: str = "config"):
    """Create default configuration files if they don't exist"""
    config_path = Path(config_dir)
    config_path.mkdir(exist_ok=True)
    
    config = SchedulerConfig(config_dir)
    
    # Create scheduler_rules.yaml
    rules_file = config_path / "scheduler_rules.yaml"
    if not rules_file.exists():
        rules = config._get_default_scheduler_rules()
        with open(rules_file, 'w') as f:
            yaml.dump(rules, f, default_flow_style=False, sort_keys=False)
        print(f"Created {rules_file}")
    
    # Create tc_commissioners.yaml
    tc_comm_file = config_path / "tc_commissioners.yaml"
    if not tc_comm_file.exists():
        tc_comm = config._get_default_commissioners("tc")
        with open(tc_comm_file, 'w') as f:
            yaml.dump(tc_comm, f, default_flow_style=False, sort_keys=False)
        print(f"Created {tc_comm_file}")
    
    # Create voyageur_commissioners.yaml
    voy_comm_file = config_path / "voyageur_commissioners.yaml"
    if not voy_comm_file.exists():
        voy_comm = config._get_default_commissioners("voyageur")
        with open(voy_comm_file, 'w') as f:
            yaml.dump(voy_comm, f, default_flow_style=False, sort_keys=False)
        print(f"Created {voy_comm_file}")
    
    # Create activity_rules.yaml
    activity_file = config_path / "activity_rules.yaml"
    if not activity_file.exists():
        activity_rules = config._get_default_activity_rules()
        with open(activity_file, 'w') as f:
            yaml.dump(activity_rules, f, default_flow_style=False, sort_keys=False)
        print(f"Created {activity_file}")
    
    # Create capacity_limits.yaml
    capacity_file = config_path / "capacity_limits.yaml"
    if not capacity_file.exists():
        capacity = config._get_default_capacity_limits()
        with open(capacity_file, 'w') as f:
            yaml.dump(capacity, f, default_flow_style=False, sort_keys=False)
        print(f"Created {capacity_file}")
    
    print(f"\nAll configuration files created in {config_path}/")
    print("You can now edit these YAML files to customize scheduling rules!")


if __name__ == "__main__":
    # Create default config files
    create_default_config_files()
    
    # Test loading
    print("\nTesting configuration loading:")
    config = SchedulerConfig()
    config.load_all()
    
    print(f"\nBeach staff limit: {config.get('capacity.beach_staff_per_slot')}")
    print(f"Archery target days: {config.get('scheduler_rules.optimization.archery_target_days')}")
    print(f"Friday reflection required: {config.get('scheduler_rules.constraints.friday_reflection.required')}")
