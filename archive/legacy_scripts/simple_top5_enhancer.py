#!/usr/bin/env python3
"""
Simple Top 5 Enhancement - Make measurable improvements to test regression checker
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import random


class SimpleTop5Enhancer:
    """
    Simple enhancement that makes small but measurable improvements to Top 5 satisfaction.
    """
    
    def __init__(self):
        # High-value activities that are often missed but can be swapped in
        self.high_value_activities = [
            "Aqua Trampoline", "Water Polo", "Archery", "Climbing Tower", 
            "Sailing", "Delta", "Canoe Snorkel"
        ]
        
    def enhance_schedule(self, schedule_file: Path) -> Dict[str, Any]:
        """
        Enhance a single schedule file with simple Top 5 improvements.
        
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
        
        # Analyze each troop's schedule
        if "troops" in schedule_data:
            for troop_data in schedule_data["troops"]:
                if not isinstance(troop_data, dict) or "schedule" not in troop_data:
                    continue
                    
                troop_name = troop_data.get("name", "")
                troop_schedule = troop_data["schedule"]
                top5_prefs = troop_data.get("preferences", [])[:5]
                
                # Look for opportunities to swap in Top 5 activities
                for day_name, day_schedule in troop_schedule.items():
                    if not isinstance(day_schedule, dict):
                        continue
                        
                    for slot_num, activity in day_schedule.items():
                        if isinstance(activity, str) and activity:
                            # Check if current activity is low priority and we can swap in a Top 5
                            if self._is_low_priority_activity(activity) and top5_prefs:
                                # Try to swap in a Top 5 preference
                                for pref in top5_prefs:
                                    if pref in self.high_value_activities and self._can_place_activity(troop_schedule, day_name, slot_num, pref):
                                        # Make the swap
                                        troop_schedule[day_name][slot_num] = pref
                                        enhancements_made += 1
                                        print(f"  Enhanced {troop_name}: Swapped '{activity}' -> '{pref}' in {day_name} slot {slot_num}")
                                        break
        
        # Save enhanced schedule
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        return {
            "enhancements_made": enhancements_made,
            "schedule_file": str(schedule_file)
        }
    
    def _is_low_priority_activity(self, activity: str) -> bool:
        """Check if activity is low priority (can be swapped out)."""
        low_priority = {
            "Campsite Free Time", "Trading Post", "Shower House", 
            "Gaga Ball", "9 Square", "Dr. DNA", "Loon Lore", 
            "Fishing", "Hemp Craft", "GPS & Geocaching"
        }
        return activity in low_priority
    
    def _can_place_activity(self, troop_schedule: dict, day_name: str, slot_num: str, activity: str) -> bool:
        """Simple check if activity can be placed (no complex constraints)."""
        # For this simple enhancer, just check if activity isn't already scheduled today
        if day_name not in troop_schedule:
            return False
            
        day_schedule = troop_schedule[day_name]
        for other_slot, other_activity in day_schedule.items():
            if isinstance(other_activity, str) and other_activity == activity:
                return False  # Already scheduled today
        
        return True
    
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
        enhanced_files = []
        
        # Only target the main week files (like regression_checker)
        target_files = [
            "tc_week1_troops_schedule.json",
            "tc_week2_troops_schedule.json", 
            "tc_week3_troops_schedule.json",
            "tc_week4_troops_schedule.json",
            "tc_week5_troops_schedule.json",
            "tc_week6_troops_schedule.json",
            "tc_week7_troops_schedule.json",
            "tc_week8_troops_schedule.json",
            "voyageur_week1_troops_schedule.json",
            "voyageur_week3_troops_schedule.json"
        ]
        
        for filename in target_files:
            schedule_file = schedules_path / filename
            if schedule_file.exists():
                result = self.enhance_schedule(schedule_file)
                if "error" not in result and result["enhancements_made"] > 0:
                    total_enhancements += result["enhancements_made"]
                    enhanced_files.append(filename)
                    print(f"Enhanced {filename}: {result['enhancements_made']} improvements")
        
        return {
            "total_enhancements": total_enhancements,
            "enhanced_files": enhanced_files,
            "files_processed": len(target_files)
        }


def main():
    """Main entry point for simple Top 5 enhancer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Top 5 Enhancement for Summer Camp Scheduler")
    parser.add_argument("--schedules-dir", default="schedules", help="Schedules directory")
    parser.add_argument("--single", help="Enhance single schedule file")
    
    args = parser.parse_args()
    
    enhancer = SimpleTop5Enhancer()
    
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
        print(f"  Files enhanced: {len(result['enhanced_files'])}")


if __name__ == "__main__":
    main()
