#!/usr/bin/env python3
"""
Aggressive Test Enhancer - Makes measurable changes to test regression checker effectiveness
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import random


class AggressiveTestEnhancer:
    """
    Aggressive enhancer that makes small but measurable improvements to test regression checker.
    This will intentionally make some changes to see if regression_checker detects them.
    """
    
    def __init__(self):
        # Activities we'll prioritize
        self.priority_activities = [
            "Aqua Trampoline", "Water Polo", "Archery", "Climbing Tower", 
            "Sailing", "Delta", "Canoe Snorkel", "Greased Watermelon"
        ]
        
    def enhance_schedule(self, schedule_file: Path) -> Dict[str, Any]:
        """
        Enhance a single schedule file with aggressive improvements.
        
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
                
                # Make targeted improvements
                enhancements_made += self._improve_top5_placement(troop_name, troop_schedule, top5_prefs)
                enhancements_made += self._add_priority_activities(troop_name, troop_schedule)
        
        # Save enhanced schedule
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        return {
            "enhancements_made": enhancements_made,
            "schedule_file": str(schedule_file)
        }
    
    def _improve_top5_placement(self, troop_name: str, troop_schedule: dict, top5_prefs: list) -> int:
        """Improve placement of Top 5 preferences."""
        improvements = 0
        
        for day_name, day_schedule in troop_schedule.items():
            if not isinstance(day_schedule, dict):
                continue
                
            # Look for empty slots or low-value activities
            for slot_num, activity in day_schedule.items():
                if not isinstance(activity, str):
                    continue
                    
                # If empty slot, try to fill with Top 5
                if not activity and top5_prefs:
                    pref_to_place = top5_prefs[0]  # Place highest priority
                    troop_schedule[day_name][slot_num] = pref_to_place
                    improvements += 1
                    print(f"  Filled empty slot: {troop_name} in {day_name} slot {slot_num} -> {pref_to_place}")
                    break
                
                # If low-value activity, consider swapping
                elif activity in ["Campsite Free Time", "Trading Post", "Shower House"] and top5_prefs:
                    # Find a Top 5 preference not already scheduled
                    for pref in top5_prefs:
                        if pref not in self._get_scheduled_activities(troop_schedule, day_name):
                            troop_schedule[day_name][slot_num] = pref
                            improvements += 1
                            print(f"  Swapped: {troop_name} in {day_name} slot {slot_num} '{activity}' -> '{pref}'")
                            break
        
        return improvements
    
    def _add_priority_activities(self, troop_name: str, troop_schedule: dict) -> int:
        """Add priority activities to empty slots."""
        improvements = 0
        
        for day_name, day_schedule in troop_schedule.items():
            if not isinstance(day_schedule, dict):
                continue
                
            for slot_num, activity in day_schedule.items():
                if isinstance(activity, str) and not activity:
                    # Fill empty slot with priority activity
                    priority_activity = random.choice(self.priority_activities)
                    troop_schedule[day_name][slot_num] = priority_activity
                    improvements += 1
                    print(f"  Added priority: {troop_name} in {day_name} slot {slot_num} -> {priority_activity}")
        
        return improvements
    
    def _get_scheduled_activities(self, troop_schedule: dict, day_name: str) -> set:
        """Get all activities scheduled for a specific day."""
        if day_name not in troop_schedule:
            return set()
        
        scheduled = set()
        day_schedule = troop_schedule[day_name]
        if isinstance(day_schedule, dict):
            for activity in day_schedule.values():
                if isinstance(activity, str) and activity:
                    scheduled.add(activity)
        
        return scheduled
    
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
        
        # Target the main week files
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
                if "error" not in result:
                    total_enhancements += result["enhancements_made"]
                    if result["enhancements_made"] > 0:
                        enhanced_files.append(filename)
                    print(f"Enhanced {filename}: {result['enhancements_made']} improvements")
        
        return {
            "total_enhancements": total_enhancements,
            "enhanced_files": enhanced_files,
            "files_processed": len(target_files)
        }


def main():
    """Main entry point for aggressive test enhancer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggressive Test Enhancement for Summer Camp Scheduler")
    parser.add_argument("--schedules-dir", default="schedules", help="Schedules directory")
    
    args = parser.parse_args()
    
    enhancer = AggressiveTestEnhancer()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    import os
    os.chdir(script_dir)
    
    # Enhance all files
    result = enhancer.enhance_all_schedules(args.schedules_dir)
    print(f"\nOverall enhancement results:")
    print(f"  Files processed: {result['files_processed']}")
    print(f"  Total enhancements: {result['total_enhancements']}")
    print(f"  Files enhanced: {len(result['enhanced_files'])}")


if __name__ == "__main__":
    main()
