#!/usr/bin/env python3
"""
Test Top 5 beach fixes on a single week to verify functionality.
"""

import json
from pathlib import Path
from io_handler import load_troops_from_json
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler
from integrated_top5_beach_fix import apply_integrated_top5_beach_fix
from analyze_top5_misses import analyze_week

def test_single_week():
    """Test fixes on a single week."""
    print("Testing Top 5 Beach Fixes on Single Week")
    print("=" * 50)
    
    # Use tc_week4 (has most Aqua Trampoline issues)
    troops_file = Path("tc_week4_troops.json")
    schedule_file = Path("schedules/tc_week4_troops_schedule.json")
    
    if not troops_file.exists():
        print(f"Troops file not found: {troops_file}")
        return
    
    print(f"Testing week: {troops_file.name}")
    
    # Load troops
    troops = load_troops_from_json(troops_file)
    print(f"Loaded {len(troops)} troops")
    
    # Generate schedule
    activities = get_all_activities()
    scheduler = ConstrainedScheduler(troops, activities)
    schedule = scheduler.schedule_all()
    
    # Analyze before fixes (simple count)
    print("\nBEFORE FIXES:")
    troop_activities = {}
    for troop in troops:
        troop_activities[troop.name] = [e.activity.name for e in schedule.entries if e.troop == troop]
    
    before_misses = []
    for troop in troops:
        top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        for i, pref in enumerate(top5_prefs):
            if pref not in troop_activities[troop.name]:
                before_misses.append({
                    'troop': troop.name,
                    'activity': pref,
                    'rank': i + 1
                })
    
    print(f"  Missed Top 5: {len(before_misses)}")
    
    # Show specific AT misses
    at_misses = [m for m in before_misses if m['activity'] == 'Aqua Trampoline']
    print(f"  Aqua Trampoline misses: {len(at_misses)}")
    for miss in at_misses:
        print(f"    {miss['troop']} rank #{miss['rank']}")
    
    # Apply our fixes
    print("\nAPPLYING FIXES:")
    
    # Manually add troops to schedule for our fix system
    schedule.troops = troops
    
    fix_results = apply_integrated_top5_beach_fix(schedule)
    
    print(f"  Total fixes applied: {fix_results['overall_impact']['total_fixes_applied']}")
    print(f"  Troops helped: {fix_results['overall_impact']['unique_troops_helped']}")
    print(f"  Effectiveness score: {fix_results['overall_impact']['effectiveness_score']}/10")
    print(f"  Constraint violations: {fix_results['overall_impact']['total_violations_created']}")
    
    # Show fix details
    if fix_results['top5_beach_fixes']['details']:
        print("\nFIX DETAILS:")
        for detail in fix_results['top5_beach_fixes']['details']:
            print(f"  {detail['troop']}: {detail['activity']} (Rank #{detail['rank']}) at {detail['slot']}")
            print(f"    Violations: {detail['violations']}, Constraint relaxed: {detail['constraint_relaxed']}")
    
    # Show recommendations
    if fix_results['recommendations']:
        print("\nRECOMMENDATIONS:")
        for rec in fix_results['recommendations']:
            print(f"  {rec}")
    
    print(f"\nFIX SUMMARY:")
    print(f"  Top 5 beach fixes: {fix_results['top5_beach_fixes']['fixes_applied']}")
    print(f"  Beach optimizations: {fix_results['beach_optimizations']['capacity_optimizations'] + fix_results['beach_optimizations']['constraint_relaxations'] + fix_results['beach_optimizations']['scheduling_improvements']}")
    
    return fix_results

if __name__ == "__main__":
    test_single_week()
