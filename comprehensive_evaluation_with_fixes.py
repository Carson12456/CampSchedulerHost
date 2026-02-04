#!/usr/bin/env python3
"""
Comprehensive evaluation with Top 5 beach activity fixes applied.
Tests the impact of our Aqua Trampoline and beach activity optimizations.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import statistics

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from io_handler import load_troops_from_json
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler
from integrated_top5_beach_fix import apply_integrated_top5_beach_fix
from models import Day

def evaluate_single_schedule_with_fixes(troops_file):
    """Evaluate a single schedule with our Top 5 beach fixes applied."""
    print(f"\n{'='*60}")
    print(f"Evaluating with Fixes: {troops_file.name}")
    print(f"{'='*60}")
    
    # Load troops and generate schedule
    troops = load_troops_from_json(troops_file)
    activities = get_all_activities()
    scheduler = ConstrainedScheduler(troops, activities)
    schedule = scheduler.schedule_all()
    
    # Ensure 0 gaps
    scheduler._force_zero_gaps_absolute()
    
    # Apply our Top 5 beach fixes
    print("Applying Top 5 beach activity fixes...")
    fix_results = apply_integrated_top5_beach_fix(schedule)
    
    metrics = {
        'week_name': troops_file.stem,
        'troop_count': len(troops),
        'total_entries': len(schedule.entries),
        'gaps': 0,
        'troop_gaps': {},
        'preference_stats': {},
        'staff_stats': {},
        'clustering_stats': {},
        'constraint_violations': {},
        'top5_satisfaction': {},
        'fix_results': fix_results,
        'issues': []
    }
    
    # 1. Gap Analysis
    gaps_by_troop = defaultdict(int)
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        expected_slots = len(scheduler.time_slots)
        actual_slots = len(troop_entries)
        gaps = expected_slots - actual_slots
        if gaps > 0:
            gaps_by_troop[troop.name] = gaps
            metrics['issues'].append(f"{troop.name} has {gaps} gaps")
    
    metrics['gaps'] = sum(gaps_by_troop.values())
    metrics['troop_gaps'] = dict(gaps_by_troop)
    
    # 2. Preference Analysis
    total_satisfaction = 0
    top5_satisfaction = 0
    for troop in troops:
        troop_activities = [e.activity.name for e in schedule.entries if e.troop == troop]
        satisfied = sum(1 for pref in troop.preferences if pref in troop_activities)
        total_satisfaction += satisfied / len(troop.preferences) if troop.preferences else 0
        
        # Top 5 satisfaction
        top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        top5_satisfied = sum(1 for pref in top5_prefs if pref in troop_activities)
        top5_satisfaction += top5_satisfied / len(top5_prefs) if top5_prefs else 0
    
    metrics['preference_stats'] = {
        'average_satisfaction': total_satisfaction / len(troops) if troops else 0,
        'top5_satisfaction': top5_satisfaction / len(troops) if troops else 0
    }
    
    # 3. Staff Analysis
    staff_by_slot = defaultdict(int)
    for entry in schedule.entries:
        if hasattr(entry.activity, 'staff_required') and entry.activity.staff_required:
            staff_by_slot[entry.time_slot] += 1
    
    if staff_by_slot:
        staff_variance = statistics.variance(staff_by_slot.values())
        metrics['staff_stats'] = {
            'variance': staff_variance,
            'total_staffed_slots': len(staff_by_slot)
        }
    
    # 4. Clustering Analysis
    zone_by_day = defaultdict(lambda: defaultdict(set))
    for entry in schedule.entries:
        zone_by_day[entry.time_slot.day][entry.activity.zone].add(entry.troop.name)
    
    clustering_score = 0
    total_days = 0
    for day, zones in zone_by_day.items():
        if len(zones) > 1:
            zone_sizes = [len(troops) for troops in zones.values()]
            clustering_score += max(zone_sizes) / sum(zone_sizes)
            total_days += 1
    
    metrics['clustering_stats'] = {
        'clustering_score': clustering_score / total_days if total_days > 0 else 0
    }
    
    # 5. Constraint Violations
    violations = []
    
    # Beach slot violations
    beach_activities = {"Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
                      "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
                      "Nature Canoe", "Float for Floats"}
    
    for entry in schedule.entries:
        if (entry.activity.name in beach_activities and 
            entry.time_slot.slot_number == 2 and 
            entry.time_slot.day != Day.THURSDAY):
            violations.append(f"Beach activity {entry.activity.name} in invalid slot 2")
    
    metrics['constraint_violations'] = {
        'total': len(violations),
        'beach_slot': len([v for v in violations if 'Beach activity' in v]),
        'details': violations
    }
    
    # 6. Top 5 Detailed Analysis
    top5_details = {}
    for troop in troops:
        troop_activities = [e.activity.name for e in schedule.entries if e.troop == troop]
        top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        missing_top5 = [pref for pref in top5_prefs if pref not in troop_activities]
        
        if missing_top5:
            top5_details[troop.name] = {
                'missing': missing_top5,
                'satisfied': len(top5_prefs) - len(missing_top5),
                'total': len(top5_prefs)
            }
    
    metrics['top5_satisfaction'] = {
        'details': top5_details,
        'total_missing': sum(len(details['missing']) for details in top5_details.values())
    }
    
    return metrics, schedule

def run_comprehensive_evaluation_with_fixes():
    """Run comprehensive evaluation with our Top 5 beach fixes."""
    print("COMPREHENSIVE EVALUATION WITH TOP 5 BEACH FIXES")
    print("=" * 60)
    
    # Get all troop files
    troops_dir = Path("troops")
    troop_files = list(troops_dir.glob("*_troops.json"))
    
    all_results = []
    all_schedules = []
    
    for troops_file in sorted(troop_files):
        try:
            metrics, schedule = evaluate_single_schedule_with_fixes(troops_file)
            all_results.append(metrics)
            all_schedules.append(schedule)
            
            # Print summary
            print(f"  Week: {metrics['week_name']}")
            print(f"    Troops: {metrics['troop_count']}")
            print(f"    Top 5 Satisfaction: {metrics['preference_stats']['top5_satisfaction']:.1%}")
            print(f"    Fixes Applied: {metrics['fix_results']['overall_impact']['total_fixes_applied']}")
            print(f"    Troops Helped: {metrics['fix_results']['overall_impact']['unique_troops_helped']}")
            print(f"    Effectiveness Score: {metrics['fix_results']['overall_impact']['effectiveness_score']}/10")
            
        except Exception as e:
            print(f"  ERROR evaluating {troops_file.name}: {e}")
            continue
    
    # Generate summary
    print(f"\n{'='*60}")
    print("OVERALL SUMMARY WITH FIXES")
    print("=" * 60)
    
    if all_results:
        avg_top5 = statistics.mean([r['preference_stats']['top5_satisfaction'] for r in all_results])
        avg_satisfaction = statistics.mean([r['preference_stats']['average_satisfaction'] for r in all_results])
        total_fixes = sum([r['fix_results']['overall_impact']['total_fixes_applied'] for r in all_results])
        total_troops_helped = len(set().union(*[r['fix_results']['top5_beach_fixes']['troops_helped'] for r in all_results]))
        avg_effectiveness = statistics.mean([r['fix_results']['overall_impact']['effectiveness_score'] for r in all_results])
        
        print(f"Weeks evaluated: {len(all_results)}")
        print(f"Average Top 5 satisfaction: {avg_top5:.1%}")
        print(f"Average overall satisfaction: {avg_satisfaction:.1%}")
        print(f"Total fixes applied: {total_fixes}")
        print(f"Unique troops helped: {total_troops_helped}")
        print(f"Average effectiveness score: {avg_effectiveness:.1f}/10")
        
        # Compare with before
        print(f"\nCOMPARISON WITH BEFORE FIXES:")
        print(f"  Before: Aqua Trampoline 12 misses, Top 5 satisfaction ~90%")
        print(f"  After: {total_fixes} fixes applied, Top 5 satisfaction {avg_top5:.1%}")
        
        if avg_top5 > 0.90:
            print(f"  IMPROVEMENT: Top 5 satisfaction improved!")
        if total_fixes > 10:
            print(f"  SUCCESS: Significant fix impact detected!")
    
    # Save results
    results_file = Path("comprehensive_evaluation_with_fixes_results.json")
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {results_file}")
    return all_results, all_schedules

if __name__ == "__main__":
    run_comprehensive_evaluation_with_fixes()
