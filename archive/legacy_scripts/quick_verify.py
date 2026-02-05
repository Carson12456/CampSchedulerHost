#!/usr/bin/env python3
"""
Quick verification of Top 5 fixes in proper format.
"""

import json
from pathlib import Path

def quick_verify():
    """Quick verification of Top 5 fixes."""
    print("QUICK VERIFICATION")
    print("=" * 20)
    
    # Check tc_week4 as example
    schedule_file = Path("schedules/tc_week4_troops_schedule.json")
    troops_file = Path("tc_week4_troops.json")
    
    if not schedule_file.exists() or not troops_file.exists():
        print("Files not found")
        return
    
    # Load data
    with open(schedule_file) as f:
        schedule_data = json.load(f)
    
    with open(troops_file) as f:
        troops_data = json.load(f)['troops']
    
    # Build troop activities
    troop_activities = {}
    for entry in schedule_data['entries']:
        if entry['troop'] not in troop_activities:
            troop_activities[entry['troop']] = []
        troop_activities[entry['troop']].append(entry['activity'])
    
    # Check Top 5 satisfaction
    total_top5 = 0
    satisfied_top5 = 0
    total_at = 0
    satisfied_at = 0
    
    for troop in troops_data:
        troop_name = troop['name']
        activities = troop_activities.get(troop_name, [])
        
        top5 = troop['preferences'][:5]
        
        for pref in top5:
            total_top5 += 1
            if pref == "Aqua Trampoline":
                total_at += 1
            
            if pref in activities:
                satisfied_top5 += 1
                if pref == "Aqua Trampoline":
                    satisfied_at += 1
    
    top5_rate = (satisfied_top5 / total_top5 * 100) if total_top5 > 0 else 0
    at_rate = (satisfied_at / total_at * 100) if total_at > 0 else 0
    
    print(f"Top 5: {satisfied_top5}/{total_top5} ({top5_rate:.1f}%)")
    print(f"Aqua Trampoline: {satisfied_at}/{total_at} ({at_rate:.1f}%)")
    print(f"Format: {'troops' in schedule_data and 'entries' in schedule_data}")
    
    if top5_rate >= 95 and at_rate >= 95:
        print("SUCCESS: Excellent Top 5 satisfaction with proper format!")
    else:
        print("NEEDS WORK: Top 5 satisfaction needs improvement")

if __name__ == "__main__":
    quick_verify()
