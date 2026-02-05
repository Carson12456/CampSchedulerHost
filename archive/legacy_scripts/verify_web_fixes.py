#!/usr/bin/env python3
"""
Verify that the web interface schedules now have the Top 5 fixes applied.
"""

import json
from pathlib import Path
from collections import defaultdict

def verify_web_fixes():
    """
    Verify the Top 5 satisfaction in the updated web interface schedules.
    """
    print("VERIFYING TOP 5 FIXES IN WEB INTERFACE")
    print("=" * 45)
    
    # Get all troop files
    troop_files = list(Path(".").glob("*_troops.json"))
    
    total_top5_prefs = 0
    satisfied_top5_prefs = 0
    total_at_prefs = 0
    satisfied_at_prefs = 0
    
    week_results = {}
    
    for troops_file in sorted(troop_files):
        week_name = troops_file.stem.replace('_troops', '')
        schedule_file = Path(f"schedules/{week_name}_troops_schedule.json")
        
        if not schedule_file.exists():
            print(f"{week_name}: Schedule file not found")
            continue
        
        try:
            # Load troop data
            with open(troops_file) as f:
                troops_data = json.load(f)['troops']
            
            # Load schedule
            with open(schedule_file) as f:
                schedule_data = json.load(f)
            
            # Build troop activities lookup
            troop_activities = defaultdict(list)
            for entry in schedule_data.get('entries', []):
                troop_activities[entry['troop']].append(entry['activity'])
            
            # Analyze Top 5 satisfaction for this week
            week_top5 = 0
            week_satisfied = 0
            week_at = 0
            week_at_satisfied = 0
            missed_details = []
            
            for troop in troops_data:
                troop_name = troop['name']
                activities = troop_activities.get(troop_name, [])
                
                # Check Top 5 preferences
                top5 = troop['preferences'][:5] if len(troop['preferences']) >= 5 else troop['preferences']
                
                for pref in top5:
                    week_top5 += 1
                    total_top5_prefs += 1
                    
                    if pref == "Aqua Trampoline":
                        week_at += 1
                        total_at_prefs += 1
                    
                    if pref in activities:
                        week_satisfied += 1
                        satisfied_top5_prefs += 1
                        
                        if pref == "Aqua Trampoline":
                            week_at_satisfied += 1
                            satisfied_at_prefs += 1
                    else:
                        missed_details.append(f"{troop_name}: {pref}")
            
            # Calculate satisfaction rates
            top5_rate = (week_satisfied / week_top5 * 100) if week_top5 > 0 else 100
            at_rate = (week_at_satisfied / week_at * 100) if week_at > 0 else 100
            
            week_results[week_name] = {
                'top5_total': week_top5,
                'top5_satisfied': week_satisfied,
                'top5_rate': top5_rate,
                'at_total': week_at,
                'at_satisfied': week_at_satisfied,
                'at_rate': at_rate,
                'missed': missed_details
            }
            
            print(f"{week_name}:")
            print(f"  Top 5: {week_satisfied}/{week_top5} ({top5_rate:.1f}%)")
            print(f"  Aqua Trampoline: {week_at_satisfied}/{week_at} ({at_rate:.1f}%)")
            
            if missed_details:
                print(f"  Missed: {len(missed_details)} preferences")
                for miss in missed_details[:3]:  # Show first 3
                    print(f"    {miss}")
                if len(missed_details) > 3:
                    print(f"    ... and {len(missed_details) - 3} more")
            print()
            
        except Exception as e:
            print(f"{week_name}: ERROR - {e}")
    
    # Overall summary
    overall_top5_rate = (satisfied_top5_prefs / total_top5_prefs * 100) if total_top5_prefs > 0 else 100
    overall_at_rate = (satisfied_at_prefs / total_at_prefs * 100) if total_at_prefs > 0 else 100
    
    print("=" * 45)
    print("OVERALL RESULTS")
    print("=" * 45)
    print(f"Total Top 5 preferences: {total_top5_prefs}")
    print(f"Satisfied Top 5 preferences: {satisfied_top5_prefs}")
    print(f"Overall Top 5 satisfaction: {overall_top5_rate:.1f}%")
    print()
    print(f"Total Aqua Trampoline preferences: {total_at_prefs}")
    print(f"Satisfied Aqua Trampoline preferences: {satisfied_at_prefs}")
    print(f"Aqua Trampoline satisfaction: {overall_at_rate:.1f}%")
    
    # Success assessment
    print()
    if overall_top5_rate >= 95:
        print("SUCCESS: Excellent Top 5 satisfaction!")
    elif overall_top5_rate >= 90:
        print("GOOD: High Top 5 satisfaction")
    elif overall_top5_rate >= 80:
        print("ACCEPTABLE: Moderate Top 5 satisfaction")
    else:
        print("NEEDS IMPROVEMENT: Low Top 5 satisfaction")
    
    if overall_at_rate >= 95:
        print("SUCCESS: Aqua Trampoline crisis resolved!")
    elif overall_at_rate >= 80:
        print("GOOD: Aqua Trampoline significantly improved")
    else:
        print("NEEDS WORK: Aqua Trampoline still has issues")
    
    return week_results, overall_top5_rate, overall_at_rate

if __name__ == "__main__":
    verify_web_fixes()
