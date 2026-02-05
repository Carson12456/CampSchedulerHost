#!/usr/bin/env python3
"""
Beach Activity Enhancement - Simple improvement to test regression checker
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class BeachActivityEnhancer:
    """
    Simple enhancement to improve beach activity placement in existing schedules.
    Focuses on better placement of Top 5 beach activities.
    """
    
    def __init__(self):
        self.beach_activities = {
            "Aqua Trampoline", "Water Polo", "Greased Watermelon", 
            "Troop Swim", "Underwater Obstacle Course", "Float for Floats", 
            "Canoe Snorkel"
        }
        self.beach_slots = {"1", "3"}  # Preferred beach slots (not slot 2)
        
    def enhance_schedule(self, schedule_file: Path) -> Dict[str, Any]:
        """
        Enhance a single schedule file with better beach activity placement.
        
        Args:
            schedule_file: Path to schedule JSON file
            
        Returns:
            Enhancement results
        """
        if not schedule_file.exists():
            return {"error": f"Schedule file not found: {schedule_file}"}
        
        # Load schedule
        with open(schedule_file, 'r') as f:
            schedule_data = json.load(f)
        
        enhancements_made = 0
        top5_enhancements = 0
        
        # Analyze each troop's schedule
        if "troops" in schedule_data:
            for troop_data in schedule_data["troops"]:
                if not isinstance(troop_data, dict) or "schedule" not in troop_data:
                    continue
                    
                troop_name = troop_data.get("name", "")
                troop_schedule = troop_data["schedule"]
                
                # Get troop preferences to identify Top 5
                top5_prefs = set(troop_data.get("preferences", [])[:5])
                
                # Look for beach activities in suboptimal slots
                for day_name, day_schedule in troop_schedule.items():
                    if not isinstance(day_schedule, dict):
                        continue
                        
                    for slot_num, activity in day_schedule.items():
                        if isinstance(activity, str) and activity in self.beach_activities:
                            # Check if this is a Top 5 preference in wrong slot
                            if activity in top5_prefs and slot_num == "2":
                                # Try to find a better slot
                                better_slot = self._find_better_beach_slot(troop_schedule, day_name)
                                if better_slot:
                                    # Make the swap
                                    troop_schedule[day_name][better_slot] = activity
                                    troop_schedule[day_name][slot_num] = troop_schedule[day_name].get(better_slot, "")
                                    enhancements_made += 1
                                    top5_enhancements += 1
        
        # Save enhanced schedule
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        return {
            "enhancements_made": enhancements_made,
            "top5_enhancements": top5_enhancements,
            "schedule_file": str(schedule_file)
        }
    
    def _get_top5_preferences(self, prefs_file: Path) -> set:
        """Get Top 5 preferences from troop file."""
        if not prefs_file.exists():
            return set()
        
        try:
            with open(prefs_file, 'r') as f:
                prefs_data = json.load(f)
            return set(prefs_data.get("preferences", [])[:5])
        except:
            return set()
    
    def _find_better_beach_slot(self, troop_schedule: dict, day_name: str) -> str:
        """Find a better beach slot for the given day."""
        if day_name not in troop_schedule:
            return ""
        
        day_schedule = troop_schedule[day_name]
        
        # Prefer slot 1, then slot 3
        for preferred_slot in ["1", "3"]:
            if preferred_slot in day_schedule:
                current_activity = day_schedule[preferred_slot]
                # Can swap if current slot is empty or has a non-beach activity
                if not current_activity or current_activity not in self.beach_activities:
                    return preferred_slot
        
        return ""
    
    def enhance_all_schedules(self, schedules_dir: str = "schedules") -> Dict[str, Any]:
        """
        Enhance all schedule files in the schedules directory.
        
        Args:
            schedules_dir: Directory containing schedule files
            
        Returns:
            Overall enhancement results
        """
        schedules_path = Path(schedules_dir)
        if not schedules_path.exists():
            return {"error": f"Schedules directory not found: {schedules_dir}"}
        
        total_enhancements = 0
        total_top5_enhancements = 0
        enhanced_files = []
        
        # Find all schedule files
        schedule_files = list(schedules_path.glob("*_schedule.json"))
        
        for schedule_file in schedule_files:
            result = self.enhance_schedule(schedule_file)
            if "error" not in result:
                total_enhancements += result["enhancements_made"]
                total_top5_enhancements += result["top5_enhancements"]
                enhanced_files.append(str(schedule_file))
                print(f"Enhanced {schedule_file.name}: {result['enhancements_made']} improvements")
        
        return {
            "total_enhancements": total_enhancements,
            "total_top5_enhancements": total_top5_enhancements,
            "enhanced_files": enhanced_files,
            "files_processed": len(schedule_files)
        }


def main():
    """Main entry point for beach activity enhancer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Beach Activity Enhancement for Summer Camp Scheduler")
    parser.add_argument("--schedules-dir", default="schedules", help="Schedules directory")
    parser.add_argument("--single", help="Enhance single schedule file")
    
    args = parser.parse_args()
    
    enhancer = BeachActivityEnhancer()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    import os
    os.chdir(script_dir)
    
    if args.single:
        # Enhance single file
        schedule_file = Path(args.single)
        result = enhancer.enhance_schedule(schedule_file)
        print(f"Single file enhancement result: {result}")
    else:
        # Enhance all files
        result = enhancer.enhance_all_schedules(args.schedules_dir)
        print(f"\nOverall enhancement results:")
        print(f"  Files processed: {result['files_processed']}")
        print(f"  Total enhancements: {result['total_enhancements']}")
        print(f"  Top 5 enhancements: {result['total_top5_enhancements']}")
        print(f"  Files enhanced: {len(result['enhanced_files'])}")


if __name__ == "__main__":
    main()
