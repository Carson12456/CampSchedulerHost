#!/usr/bin/env python3
"""
Regression Test Enhancer - Makes measurable changes to test regression checker detection
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class RegressionTestEnhancer:
    """
    Makes intentional changes to test regression checker effectiveness.
    """
    
    def __init__(self):
        pass
    
    def make_intentional_improvement(self, schedule_file: Path) -> Dict[str, Any]:
        """
        Make an intentional improvement that should be detected by regression checker.
        
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
        
        improvements_made = 0
        
        # Analyze each troop's schedule
        if "troops" in schedule_data:
            for troop_data in schedule_data["troops"]:
                if not isinstance(troop_data, dict):
                    continue
                    
                troop_name = troop_data.get("name", "")
                preferences = troop_data.get("preferences", [])
                
                # Find missed Top 5 opportunities in entries
                if "entries" in schedule_data:
                    for entry in schedule_data["entries"]:
                        if entry.get("troop_name") == troop_name:
                            activity_name = entry.get("activity_name", "")
                            
                            # Check if this is a low-value activity that could be swapped
                            if activity_name in ["History Center", "Trading Post", "Campsite Free Time", "Shower House"]:
                                # Try to replace with a Top 5 preference
                                for pref in preferences[:5]:
                                    if pref not in ["History Center", "Trading Post", "Campsite Free Time", "Shower House"]:
                                        # Make the swap
                                        entry["activity_name"] = pref
                                        improvements_made += 1
                                        print(f"  Improved {troop_name}: Swapped '{activity_name}' -> '{pref}'")
                                        break
        
        # Save enhanced schedule
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        return {
            "improvements_made": improvements_made,
            "schedule_file": str(schedule_file)
        }
    
    def make_intentional_regression(self, schedule_file: Path) -> Dict[str, Any]:
        """
        Make an intentional regression that should be detected by regression checker.
        
        Args:
            schedule_file: Path to schedule JSON file
            
        Returns:
            Regression results
        """
        if not schedule_file.exists():
            return {"error": f"Schedule file not found: {schedule_file}"}
        
        # Load schedule
        with open(schedule_file, 'r') as f:
            schedule_data = json.load(f)
        
        regressions_made = 0
        
        # Analyze each troop's schedule
        if "troops" in schedule_data:
            for troop_data in schedule_data["troops"]:
                if not isinstance(troop_data, dict):
                    continue
                    
                troop_name = troop_data.get("name", "")
                preferences = troop_data.get("preferences", [])
                
                # Find Top 5 activities and replace them with low-value ones
                if "entries" in schedule_data:
                    for entry in schedule_data["entries"]:
                        if entry.get("troop_name") == troop_name:
                            activity_name = entry.get("activity_name", "")
                            
                            # Check if this is a Top 5 preference
                            if activity_name in preferences[:5]:
                                # Replace with a low-value activity
                                low_value_options = ["History Center", "Trading Post", "Campsite Free Time"]
                                for low_val in low_value_options:
                                    if low_val not in preferences[:5]:
                                        entry["activity_name"] = low_val
                                        regressions_made += 1
                                        print(f"  Regressed {troop_name}: Swapped '{activity_name}' -> '{low_val}'")
                                        break
        
        # Save regressed schedule
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        return {
            "regressions_made": regressions_made,
            "schedule_file": str(schedule_file)
        }


def main():
    """Main entry point for regression test enhancer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Regression Test Enhancement for Summer Camp Scheduler")
    parser.add_argument("--schedules-dir", default="schedules", help="Schedules directory")
    parser.add_argument("--improve", action="store_true", help="Make intentional improvements")
    parser.add_argument("--regress", action="store_true", help="Make intentional regressions")
    parser.add_argument("--file", help="Target specific file")
    
    args = parser.parse_args()
    
    enhancer = RegressionTestEnhancer()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    import os
    os.chdir(script_dir)
    
    if args.file:
        # Process single file
        schedule_file = Path(args.schedules_dir) / args.file
        if args.improve:
            result = enhancer.make_intentional_improvement(schedule_file)
        elif args.regress:
            result = enhancer.make_intentional_regression(schedule_file)
        else:
            result = {"error": "Must specify --improve or --regress"}
        
        print(f"Result: {result}")
    else:
        print("Must specify --file with target schedule file")


if __name__ == "__main__":
    main()
