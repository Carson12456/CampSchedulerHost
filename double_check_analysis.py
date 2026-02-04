#!/usr/bin/env python3
"""
Double-check everything implemented to catch mistakes from skewed numbers
"""

import json
from pathlib import Path
from collections import defaultdict

def check_actual_schedule_files():
    """Check what schedule files actually exist for the 10 weeks."""
    week_patterns = [
        'tc_week1', 'tc_week2', 'tc_week3', 'tc_week4', 'tc_week5', 
        'tc_week6', 'tc_week7', 'tc_week8', 'voyageur_week1', 'voyageur_week3'
    ]
    
    print('CHECKING ACTUAL SCHEDULE FILES FOR 10 WEEKS:')
    print('=' * 60)
    
    for week_pattern in week_patterns:
        schedule_files = list(Path('schedules').glob(f'{week_pattern}*_schedule.json'))
        print(f'{week_pattern}: {len(schedule_files)} variants found')
        for sf in schedule_files[:3]:  # Show first 3
            print(f'  - {sf.name}')
        if len(schedule_files) > 3:
            print(f'  ... and {len(schedule_files) - 3} more')
        print()

def analyze_week_correctly(week_pattern):
    """Analyze one week correctly using the right schedule file."""
    print(f'ANALYZING {week_pattern} CORRECTLY:')
    print('=' * 60)
    
    # Find the best schedule file for this week
    schedule_files = list(Path('schedules').glob(f'{week_pattern}*_schedule.json'))
    if not schedule_files:
        print(f'ERROR: No schedule files found for {week_pattern}')
        return None
    
    # Priority: troops variant > direct_fixed > first available
    selected_file = None
    for sf in schedule_files:
        if 'troops' in sf.name:
            selected_file = sf
            break
    if not selected_file:
        for sf in schedule_files:
            if 'direct_fixed' in sf.name:
                selected_file = sf
                break
    if not selected_file:
        selected_file = schedule_files[0]
    
    print(f'Using: {selected_file.name}')
    
    with open(selected_file, 'r') as f:
        data = json.load(f)
    
    troops = data.get('troops', [])
    entries = data.get('entries', [])
    unscheduled = data.get('unscheduled', {})
    
    print(f'Troops in file: {len(troops)}')
    print(f'Entries in file: {len(entries)}')
    print(f'Unscheduled sections: {len(unscheduled)}')
    
    # Build scheduled activities
    scheduled = defaultdict(set)
    for entry in entries:
        troop = entry.get('troop_name', '')
        activity = entry.get('activity_name', '')
        if troop and activity:
            scheduled[troop].add(activity)
    
    # Check each troop
    missing_reflection = 0
    top5_satisfied = 0
    top5_total = 0
    
    for troop in troops:
        troop_name = troop.get('name', '')
        preferences = troop.get('preferences', [])[:5]
        
        # Check Reflection
        if 'Reflection' not in scheduled.get(troop_name, set()):
            missing_reflection += 1
        
        # Check Top 5
        troop_scheduled = scheduled.get(troop_name, set())
        top5_total += len(preferences)
        
        for pref in preferences:
            if pref in troop_scheduled:
                top5_satisfied += 1
    
    # Check unscheduled data consistency
    unscheduled_top5_misses = 0
    for troop_name, troop_data in unscheduled.items():
        unscheduled_top5_misses += len(troop_data.get('top5', []))
    
    print(f'Reflection missing: {missing_reflection}/{len(troops)}')
    print(f'Top 5 satisfied: {top5_satisfied}/{top5_total} ({100.0*top5_satisfied/max(1,top5_total):.1f}%)')
    print(f'Unscheduled Top5 misses: {unscheduled_top5_misses}')
    
    # Check consistency
    calculated_misses = top5_total - top5_satisfied
    if calculated_misses != unscheduled_top5_misses:
        print(f'WARNING: Data inconsistency!')
        print(f'  Calculated misses: {calculated_misses}')
        print(f'  Unscheduled misses: {unscheduled_top5_misses}')
    else:
        print(f'Data consistency: GOOD')
    
    return {
        'week': week_pattern,
        'file': selected_file.name,
        'troops': len(troops),
        'entries': len(entries),
        'missing_reflection': missing_reflection,
        'top5_satisfied': top5_satisfied,
        'top5_total': top5_total,
        'unscheduled_misses': unscheduled_top5_misses
    }

def main():
    """Main double-check function."""
    print('DOUBLE-CHECKING EVERYTHING IMPLEMENTED')
    print('=' * 60)
    
    # Check what files exist
    check_actual_schedule_files()
    
    # Analyze each week correctly
    week_patterns = [
        'tc_week1', 'tc_week2', 'tc_week3', 'tc_week4', 'tc_week5', 
        'tc_week6', 'tc_week7', 'tc_week8', 'voyageur_week1', 'voyageur_week3'
    ]
    
    all_results = []
    for week_pattern in week_patterns:
        result = analyze_week_correctly(week_pattern)
        if result:
            all_results.append(result)
        print()
    
    # Summary
    print('CORRECTED SUMMARY FOR 10 WEEKS:')
    print('=' * 60)
    
    total_troops = sum(r['troops'] for r in all_results)
    total_entries = sum(r['entries'] for r in all_results)
    total_missing_reflection = sum(r['missing_reflection'] for r in all_results)
    total_top5_satisfied = sum(r['top5_satisfied'] for r in all_results)
    total_top5_total = sum(r['top5_total'] for r in all_results)
    total_unscheduled_misses = sum(r['unscheduled_misses'] for r in all_results)
    
    print(f'Total Weeks: {len(all_results)}')
    print(f'Total Troops: {total_troops}')
    print(f'Total Entries: {total_entries}')
    print(f'Reflection Missing: {total_missing_reflection}/{total_troops} ({100.0*total_missing_reflection/max(1,total_troops):.1f}%)')
    print(f'Top 5 Success: {total_top5_satisfied}/{total_top5_total} ({100.0*total_top5_satisfied/max(1,total_top5_total):.1f}%)')
    print(f'Unscheduled Top5 Misses: {total_unscheduled_misses}')
    
    # Check for mistakes in my implementation
    print()
    print('MISTAKE ANALYSIS:')
    print('=' * 60)
    
    if total_top5_satisfied != total_top5_total - total_unscheduled_misses:
        print('ERROR: Top 5 calculation inconsistency detected!')
        print(f'  Satisfied + Misses = {total_top5_satisfied + total_unscheduled_misses}')
        print(f'  Total Top 5 slots = {total_top5_total}')
    
    if total_missing_reflection > total_troops * 0.5:
        print('WARNING: Very high Reflection missing rate detected!')
        print('  This suggests a systematic issue with Reflection scheduling')
    
    # Compare with my previous (wrong) numbers
    print()
    print('COMPARISON WITH PREVIOUS ANALYSIS:')
    print('=' * 60)
    print('PREVIOUS (WRONG):')
    print('  - Analyzed 160 files (all variants)')
    print('  - 1,207 troops (wrong count)')
    print('  - 88.6% Top 5 success (wrong)')
    print('  - 528 missing Reflection (wrong)')
    print()
    print('CORRECT:')
    print(f'  - Analyzed {len(all_results)} files (actual weeks)')
    print(f'  - {total_troops} troops (correct count)')
    print(f'  - {100.0*total_top5_satisfied/max(1,total_top5_total):.1f}% Top 5 success (correct)')
    print(f'  - {total_missing_reflection} missing Reflection (correct)')

if __name__ == "__main__":
    main()
