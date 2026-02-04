#!/usr/bin/env python3
"""
Analyze Current Scheduler State

Inspects all schedule files to determine actual Top 5 satisfaction rates
and identify gaps in the unscheduled JSON data.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from core.services.unscheduled_analyzer import UnscheduledAnalyzer


def analyze_week_from_entries(schedule_path: str) -> dict:
    """Analyze a week by cross-referencing scheduled entries with troop preferences."""
    with open(schedule_path, 'r') as f:
        data = json.load(f)
    
    troops = data.get('troops', [])
    entries = data.get('entries', [])
    unscheduled = data.get('unscheduled', {})
    
    # Build scheduled activities lookup
    scheduled = defaultdict(set)
    for entry in entries:
        troop = entry.get('troop_name', '')
        activity = entry.get('activity_name', '')
        if troop and activity:
            scheduled[troop].add(activity)
    
    # Analyze Top 5 satisfaction
    total_top5 = 0
    satisfied_top5 = 0
    missed_top5 = []
    troop_analysis = []
    
    for troop in troops:
        troop_name = troop.get('name', '')
        preferences = troop.get('preferences', [])[:5]  # Top 5
        total_top5 += len(preferences)
        
        troop_scheduled = scheduled.get(troop_name, set())
        troop_satisfied = 0
        troop_missed = []
        
        for i, pref in enumerate(preferences):
            if pref in troop_scheduled:
                troop_satisfied += 1
                satisfied_top5 += 1
            else:
                troop_missed.append(f'{pref} (#{i+1})')
        
        troop_analysis.append({
            'troop': troop_name,
            'satisfied': troop_satisfied,
            'total': len(preferences),
            'missed': troop_missed
        })
        
        if troop_missed:
            missed_top5.extend([(troop_name, miss) for miss in troop_missed])
    
    success_rate = 100.0 * satisfied_top5 / max(1, total_top5)
    
    return {
        'week_name': Path(schedule_path).stem.replace('_schedule', ''),
        'total_troops': len(troops),
        'total_entries': len(entries),
        'total_top5_slots': total_top5,
        'satisfied_top5': satisfied_top5,
        'missed_top5': len(missed_top5),
        'success_rate': success_rate,
        'unscheduled_empty': len(unscheduled) == 0,
        'troop_analysis': troop_analysis,
        'missed_details': missed_top5
    }


def main():
    """Main analysis function."""
    print("CURRENT SCHEDULER ANALYSIS")
    print("=" * 60)
    
    schedules_dir = Path("schedules")
    if not schedules_dir.exists():
        print("No schedules directory found!")
        return
    
    schedule_files = list(schedules_dir.glob("*_schedule.json"))
    
    # Focus on a representative sample
    sample_files = []
    for pattern in ["tc_week1", "tc_week2", "tc_week3", "tc_week4", "tc_week5"]:
        matches = [f for f in schedule_files if pattern in f.name]
        if matches:
            # Pick the most "standard" looking one (avoid enhanced/special variants)
            standard = [f for f in matches if any(x in f.name for x in ["direct_fixed", "troops", "ultra"])]
            if standard:
                sample_files.append(standard[0])
            else:
                sample_files.append(matches[0])
    
    print(f"Analyzing {len(sample_files)} representative schedule files...")
    print()
    
    all_weeks_analysis = []
    season_totals = {
        'total_top5_slots': 0,
        'satisfied_top5': 0,
        'missed_top5': 0,
        'weeks_with_empty_unscheduled': 0
    }
    
    for schedule_file in sample_files:
        analysis = analyze_week_from_entries(schedule_file)
        all_weeks_analysis.append(analysis)
        
        # Update season totals
        season_totals['total_top5_slots'] += analysis['total_top5_slots']
        season_totals['satisfied_top5'] += analysis['satisfied_top5']
        season_totals['missed_top5'] += analysis['missed_top5']
        if analysis['unscheduled_empty']:
            season_totals['weeks_with_empty_unscheduled'] += 1
        
        # Print week analysis
        print(f"--- {analysis['week_name']} ---")
        print(f"Troops: {analysis['total_troops']}, Entries: {analysis['total_entries']}")
        print(f"Top 5: {analysis['satisfied_top5']}/{analysis['total_top5_slots']} satisfied")
        print(f"Success Rate: {analysis['success_rate']:.1f}%")
        print(f"Unscheduled Empty: {'Yes' if analysis['unscheduled_empty'] else 'No'}")
        
        if analysis['missed_details']:
            print("Missed Top 5:")
            for troop, miss in analysis['missed_details'][:10]:  # Limit output
                print(f"  - {troop}: {miss}")
            if len(analysis['missed_details']) > 10:
                print(f"  ... and {len(analysis['missed_details']) - 10} more")
        else:
            print("All Top 5 preferences satisfied!")
        print()
    
    # Season summary
    season_success_rate = 100.0 * season_totals['satisfied_top5'] / max(1, season_totals['total_top5_slots'])
    
    print("=" * 60)
    print("SEASON SUMMARY")
    print("=" * 60)
    print(f"Weeks Analyzed: {len(all_weeks_analysis)}")
    print(f"Total Top 5 Slots: {season_totals['total_top5_slots']}")
    print(f"Satisfied: {season_totals['satisfied_top5']}")
    print(f"Missed: {season_totals['missed_top5']}")
    print(f"Season Success Rate: {season_success_rate:.1f}%")
    print(f"Weeks with Empty Unscheduled: {season_totals['weeks_with_empty_unscheduled']}/{len(all_weeks_analysis)}")
    print()
    
    # Key findings
    print("KEY FINDINGS:")
    print("=" * 60)
    
    if season_totals['weeks_with_empty_unscheduled'] == len(all_weeks_analysis):
        print("ALL weeks have empty unscheduled sections")
        print("   This indicates either:")
        print("   a) Perfect Top 5 satisfaction (unlikely)")
        print("   b) Unscheduled data not being populated by scheduler")
        print()
    
    if season_success_rate > 95:
        print("EXCELLENT: Near-perfect Top 5 satisfaction")
    elif season_success_rate > 85:
        print("GOOD: Strong Top 5 satisfaction")
    elif season_success_rate > 75:
        print("FAIR: Moderate Top 5 satisfaction")
    else:
        print("POOR: Low Top 5 satisfaction")
    
    print()
    
    # Recommendations
    print("RECOMMENDATIONS:")
    print("=" * 60)
    
    if season_totals['weeks_with_empty_unscheduled'] == len(all_weeks_analysis):
        print("1. Investigate why unscheduled JSON sections are empty")
        print("2. Check if scheduler is properly calculating missed activities")
        print("3. Verify unscheduled data population in scheduler output")
        print()
    
    if season_success_rate < 90:
        print("4. Focus on improving Top 5 satisfaction rates")
        print("5. Analyze missed activities for common patterns")
        print("6. Consider constraint relaxation for high-priority preferences")
    
    print("7. Use the new unscheduled_analyzer.py for future regression checks")
    print("8. Implement automated testing to catch Top 5 regressions")


if __name__ == "__main__":
    # Change to script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    main()
