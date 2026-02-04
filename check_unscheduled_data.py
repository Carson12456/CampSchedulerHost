#!/usr/bin/env python3
"""
Check unscheduled data to understand what the regression checker should be detecting
"""

import json
from pathlib import Path

def check_unscheduled_data():
    """Check the unscheduled data in schedule files."""
    print("CHECKING UNSCHEDULED DATA")
    print("=" * 60)
    
    # Check a few schedule files
    schedule_files = [
        "schedules/tc_week1_troops_schedule.json",
        "schedules/tc_week2_troops_schedule.json", 
        "schedules/tc_week3_troops_schedule.json"
    ]
    
    total_stats = {
        'files': 0,
        'troops': 0,
        'top5_misses': 0,
        'top10_misses': 0,
        'reflection_compliance': 0
    }
    
    for schedule_file in schedule_files:
        if not Path(schedule_file).exists():
            print(f"File not found: {schedule_file}")
            continue
        
        print(f"\n--- {schedule_file} ---")
        
        with open(schedule_file, 'r') as f:
            data = json.load(f)
        
        unscheduled = data.get('unscheduled', {})
        troops = data.get('troops', [])
        
        print(f'Troops in file: {len(troops)}')
        print(f'Troops in unscheduled: {len(unscheduled)}')
        
        file_top5_misses = 0
        file_top10_misses = 0
        file_reflection_compliance = 0
        
        for troop_name, troop_data in unscheduled.items():
            top5_misses = len(troop_data.get('top5', []))
            top10_misses = len(troop_data.get('top10', []))
            has_reflection = troop_data.get('has_reflection', False)
            
            file_top5_misses += top5_misses
            file_top10_misses += top10_misses
            if has_reflection:
                file_reflection_compliance += 1
            
            if top5_misses > 0:
                print(f'  {troop_name}: {top5_misses} Top5 misses, Reflection: {has_reflection}')
        
        print(f'File summary: {file_top5_misses} Top5 misses, {file_reflection_compliance}/{len(unscheduled)} Reflection')
        
        total_stats['files'] += 1
        total_stats['troops'] += len(unscheduled)
        total_stats['top5_misses'] += file_top5_misses
        total_stats['top10_misses'] += file_top10_misses
        total_stats['reflection_compliance'] += file_reflection_compliance
    
    print(f"\n{'='*60}")
    print("TOTAL SUMMARY")
    print("=" * 60)
    print(f"Files checked: {total_stats['files']}")
    print(f"Total troops: {total_stats['troops']}")
    print(f"Total Top5 misses: {total_stats['top5_misses']}")
    print(f"Total Top10 misses: {total_stats['top10_misses']}")
    print(f"Reflection compliance: {total_stats['reflection_compliance']}/{total_stats['troops']} ({100.0*total_stats['reflection_compliance']/max(1,total_stats['troops']):.1f}%)")
    
    # Calculate success rate
    total_top5_slots = total_stats['troops'] * 5  # 5 Top 5 per troop
    satisfied_top5 = total_top5_slots - total_stats['top5_misses']
    success_rate = 100.0 * satisfied_top5 / max(1, total_top5_slots)
    
    print(f"Top 5 success rate: {satisfied_top5}/{total_top5_slots} ({success_rate:.1f}%)")

if __name__ == "__main__":
    check_unscheduled_data()
