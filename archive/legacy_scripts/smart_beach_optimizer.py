#!/usr/bin/env python3
"""
Smart Beach Activity Optimizer - Real improvement for Summer Camp Scheduler

This optimizer makes intelligent improvements to beach activity placement
by analyzing constraints and preferences to optimize satisfaction.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict


class SmartBeachOptimizer:
    """
    Intelligent beach activity optimizer that improves Top 5 satisfaction
    while respecting beach slot constraints and troop preferences.
    """
    
    def __init__(self):
        # Beach activities that prefer slots 1 or 3 (not slot 2)
        self.beach_activities = {
            "Aqua Trampoline", "Water Polo", "Greased Watermelon", 
            "Troop Swim", "Underwater Obstacle Course", "Float for Floats", 
            "Canoe Snorkel"
        }
        
        # Preferred beach slots (slot 2 is only allowed on Thursday)
        self.preferred_beach_slots = {"1", "3"}
        self.thursday_beach_slots = {"1", "2", "3"}
        
    def optimize_schedule(self, schedule_file: Path) -> Dict[str, Any]:
        """
        Optimize beach activities in a schedule file.
        
        Args:
            schedule_file: Path to schedule JSON file
            
        Returns:
            Optimization results
        """
        if not schedule_file.exists():
            return {"error": f"Schedule file not found: {schedule_file}"}
        
        # Load schedule
        with open(schedule_file, 'r') as f:
            schedule_data = json.load(f)
        
        optimizations_made = 0
        top5_improvements = 0
        
        # Build troop preferences lookup
        troop_preferences = {}
        if "troops" in schedule_data:
            for troop in schedule_data["troops"]:
                troop_preferences[troop["name"]] = troop.get("preferences", [])
        
        # Analyze current entries for optimization opportunities
        if "entries" in schedule_data:
            optimizations_made, top5_improvements = self._optimize_beach_entries(
                schedule_data["entries"], troop_preferences
            )
        
        # Save optimized schedule
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        return {
            "optimizations_made": optimizations_made,
            "top5_improvements": top5_improvements,
            "schedule_file": str(schedule_file)
        }
    
    def _optimize_beach_entries(self, entries: List[Dict], troop_preferences: Dict[str, List[str]]) -> Tuple[int, int]:
        """
        Optimize beach activity entries for better placement.
        
        Args:
            entries: List of schedule entries
            troop_preferences: Troop preference lookup
            
        Returns:
            Tuple of (total optimizations, top5 improvements)
        """
        optimizations = 0
        top5_improvements = 0
        
        # Group entries by troop and day for analysis
        troop_day_entries = defaultdict(list)
        for entry in entries:
            key = (entry["troop_name"], entry["day"])
            troop_day_entries[key].append(entry)
        
        # Analyze each troop-day combination
        for (troop_name, day), day_entries in troop_day_entries.items():
            preferences = troop_preferences.get(troop_name, [])
            
            # Look for beach activities in suboptimal slots
            for entry in day_entries:
                activity = entry["activity_name"]
                current_slot = str(entry["slot"])
                
                if activity in self.beach_activities:
                    # Check if this is a Top 5 preference in wrong slot
                    is_top5 = activity in preferences[:5]
                    is_suboptimal = self._is_suboptimal_beach_placement(activity, current_slot, day)
                    
                    if is_top5 and is_suboptimal:
                        # Try to find a better slot
                        better_slot = self._find_better_beach_slot(
                            day_entries, activity, day
                        )
                        
                        if better_slot:
                            # Make the swap
                            old_activity = activity
                            entry["activity_name"] = better_slot["activity"]
                            better_slot["entry"]["activity_name"] = old_activity
                            
                            optimizations += 1
                            top5_improvements += 1
                            
                            print(f"  Optimized {troop_name}: Moved '{old_activity}' from {current_slot} to {better_slot['slot']} ({day})")
        
        return optimizations, top5_improvements
    
    def _is_suboptimal_beach_placement(self, activity: str, slot: str, day: str) -> bool:
        """
        Check if beach activity is in suboptimal slot.
        
        Args:
            activity: Beach activity name
            slot: Current slot number
            day: Day name
            
        Returns:
            True if placement is suboptimal
        """
        # Slot 2 is only allowed on Thursday for beach activities
        if slot == "2" and day != "THURSDAY":
            return True
        
        # All beach activities prefer slots 1 or 3
        if slot not in self.preferred_beach_slots:
            return True
        
        return False
    
    def _find_better_beach_slot(self, day_entries: List[Dict], beach_activity: str, day: str) -> Dict[str, Any]:
        """
        Find a better slot for a beach activity.
        
        Args:
            day_entries: All entries for this troop-day
            beach_activity: The beach activity to move
            day: Day name
            
        Returns:
            Dictionary with better slot info or empty dict
        """
        allowed_slots = self.thursday_beach_slots if day == "THURSDAY" else self.preferred_beach_slots
        
        for entry in day_entries:
            current_slot = str(entry["slot"])
            current_activity = entry["activity_name"]
            
            # Check if this is a preferred beach slot with a swappable activity
            if current_slot in allowed_slots and current_activity not in self.beach_activities:
                # Prefer to swap with non-Top 5 activities
                return {
                    "slot": current_slot,
                    "activity": current_activity,
                    "entry": entry
                }
        
        return {}
    
    def optimize_all_schedules(self, schedules_dir: str = "schedules") -> Dict[str, Any]:
        """
        Optimize all schedule files in the schedules directory.
        
        Args:
            schedules_dir: Directory containing schedule files
            
        Returns:
            Overall optimization results
        """
        schedules_path = Path(schedules_dir)
        if not schedules_path.exists():
            return {"error": f"Schedules directory not found: {schedules_dir}"}
        
        total_optimizations = 0
        total_top5_improvements = 0
        optimized_files = []
        
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
                result = self.optimize_schedule(schedule_file)
                if "error" not in result:
                    total_optimizations += result["optimizations_made"]
                    total_top5_improvements += result["top5_improvements"]
                    if result["optimizations_made"] > 0:
                        optimized_files.append(filename)
                    print(f"Optimized {filename}: {result['optimizations_made']} optimizations, {result['top5_improvements']} Top 5 improvements")
        
        return {
            "total_optimizations": total_optimizations,
            "total_top5_improvements": total_top5_improvements,
            "optimized_files": optimized_files,
            "files_processed": len(target_files)
        }


def main():
    """Main entry point for smart beach optimizer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Beach Activity Optimizer for Summer Camp Scheduler")
    parser.add_argument("--schedules-dir", default="schedules", help="Schedules directory")
    parser.add_argument("--single", help="Optimize single schedule file")
    
    args = parser.parse_args()
    
    optimizer = SmartBeachOptimizer()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    import os
    os.chdir(script_dir)
    
    if args.single:
        # Optimize single file
        schedule_file = Path(args.single)
        result = optimizer.optimize_schedule(schedule_file)
        print(f"Single file optimization result: {result}")
    else:
        # Optimize all files
        result = optimizer.optimize_all_schedules(args.schedules_dir)
        print(f"\nOverall optimization results:")
        print(f"  Files processed: {result['files_processed']}")
        print(f"  Total optimizations: {result['total_optimizations']}")
        print(f"  Top 5 improvements: {result['total_top5_improvements']}")
        print(f"  Files optimized: {len(result['optimized_files'])}")


if __name__ == "__main__":
    main()
