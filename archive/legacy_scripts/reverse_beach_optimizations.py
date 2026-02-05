#!/usr/bin/env python3
"""
Reverse Beach Optimizations - Test regression checker by removing improvements

This script reverses the smart beach optimizer improvements to test
if the enhanced regression checker detects the quality degradation.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class ReverseBeachOptimizations:
    """
    Reverses beach activity optimizations to test regression detection.
    """
    
    def __init__(self):
        # The specific optimizations made by smart_beach_optimizer.py
        self.reversed_optimizations = [
            # tc_week1_troops_schedule.json
            {
                "file": "tc_week1_troops_schedule.json",
                "changes": [
                    {"troop": "Massasoit", "day": "FRIDAY", "slot": 1, "from": "Aqua Trampoline", "to": "Reflection"},
                    {"troop": "Tamanend", "day": "THURSDAY", "slot": 1, "from": "Aqua Trampoline", "to": "Archery"},
                ]
            },
            # tc_week4_troops_schedule.json
            {
                "file": "tc_week4_troops_schedule.json", 
                "changes": [
                    {"troop": "Tamanend", "day": "TUESDAY", "slot": 1, "from": "Canoe Snorkel", "to": "Archery"},
                    {"troop": "Tamanend", "day": "THURSDAY", "slot": 1, "from": "Water Polo", "to": "Archery"},
                    {"troop": "Tecumseh", "day": "MONDAY", "slot": 1, "from": "Canoe Snorkel", "to": "Archery"},
                    {"troop": "Massasoit", "day": "THURSDAY", "slot": 1, "from": "Aqua Trampoline", "to": "Archery"},
                    {"troop": "Pontiac", "day": "THURSDAY", "slot": 1, "from": "Aqua Trampoline", "to": "Archery"},
                    {"troop": "Tecumseh", "day": "FRIDAY", "slot": 3, "from": "Float for Floats", "to": "Archery"},
                ]
            },
            # Add other files as needed...
        ]
    
    def reverse_optimizations(self, schedules_dir: str = "schedules") -> Dict[str, Any]:
        """
        Reverse the beach optimizer improvements.
        
        Args:
            schedules_dir: Directory containing schedule files
            
        Returns:
            Results of reversal operation
        """
        schedules_path = Path(schedules_dir)
        total_reversed = 0
        reversed_files = []
        
        for optimization in self.reversed_optimizations:
            schedule_file = schedules_path / optimization["file"]
            if not schedule_file.exists():
                print(f"Warning: Schedule file not found: {schedule_file}")
                continue
            
            # Load schedule
            with open(schedule_file, 'r') as f:
                schedule_data = json.load(f)
            
            file_reversed = 0
            
            # Apply reversals
            if "entries" in schedule_data:
                for change in optimization["changes"]:
                    for entry in schedule_data["entries"]:
                        if (entry.get("troop_name") == change["troop"] and
                            entry.get("day") == change["day"] and
                            str(entry.get("slot")) == str(change["slot"]) and
                            entry.get("activity_name") == change["from"]):
                            
                            # Reverse the optimization
                            entry["activity_name"] = change["to"]
                            file_reversed += 1
                            total_reversed += 1
                            
                            print(f"  Reversed {change['troop']}: {change['from']} -> {change['to']} ({change['day']} slot {change['slot']})")
            
            if file_reversed > 0:
                # Save reversed schedule
                with open(schedule_file, 'w') as f:
                    json.dump(schedule_data, f, indent=2)
                reversed_files.append(optimization["file"])
                print(f"Reversed {file_reversed} optimizations in {optimization['file']}")
        
        return {
            "total_reversed": total_reversed,
            "reversed_files": reversed_files
        }


def main():
    """Main entry point for reversing beach optimizations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reverse Beach Optimizations for Regression Testing")
    parser.add_argument("--schedules-dir", default="schedules", help="Schedules directory")
    
    args = parser.parse_args()
    
    reverser = ReverseBeachOptimizations()
    
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    import os
    os.chdir(script_dir)
    
    # Reverse optimizations
    result = reverser.reverse_optimizations(args.schedules_dir)
    print(f"\nReversal results:")
    print(f"  Total optimizations reversed: {result['total_reversed']}")
    print(f"  Files modified: {len(result['reversed_files'])}")


if __name__ == "__main__":
    main()
