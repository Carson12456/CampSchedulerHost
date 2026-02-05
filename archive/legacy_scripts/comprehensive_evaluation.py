#!/usr/bin/env python3
"""
Comprehensive evaluation of all generated schedules.
Analyzes performance metrics and identifies weaknesses.
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
from models import Day

def evaluate_single_schedule(troops_file):
    """Evaluate a single schedule and return comprehensive metrics."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {troops_file.name}")
    print(f"{'='*60}")
    
    # Load troops and generate schedule
    troops = load_troops_from_json(troops_file)
    activities = get_all_activities()
    scheduler = ConstrainedScheduler(troops, activities)
    schedule = scheduler.schedule_all()
    
    # Ensure 0 gaps
    scheduler._force_zero_gaps_absolute()
    
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
        'issues': []
    }
    
    # 1. Gap Analysis
    days_list = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
    slots_per_day = {
        Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
        Day.THURSDAY: 2, Day.FRIDAY: 3
    }
    
    total_gaps = 0
    for troop in troops:
        troop_gaps = 0
        for day in days_list:
            for slot_num in range(1, slots_per_day[day] + 1):
                slot = next((s for s in scheduler.time_slots 
                            if s.day == day and s.slot_number == slot_num), None)
                if slot and schedule.is_troop_free(slot, troop):
                    troop_gaps += 1
        total_gaps += troop_gaps
        metrics['troop_gaps'][troop.name] = troop_gaps
        
        if troop_gaps > 0:
            metrics['issues'].append(f"{troop.name} has {troop_gaps} gaps")
    
    metrics['gaps'] = total_gaps
    
    # 2. Preference Satisfaction Analysis
    total_prefs = 0
    satisfied_prefs = 0
    top5_satisfied = 0
    top5_total = 0
    
    for troop in troops:
        troop_entries = schedule.get_troop_schedule(troop)
        scheduled_activities = {e.activity.name for e in troop_entries}
        
        # Count all preferences
        for i, pref in enumerate(troop.preferences):
            total_prefs += 1
            if pref in scheduled_activities:
                satisfied_prefs += 1
                if i < 5:
                    top5_satisfied += 1
            if i < 5:
                top5_total += 1
        
        # Check Top 5 satisfaction
        troop_top5 = troop.preferences[:5]
        troop_satisfied = sum(1 for pref in troop_top5 if pref in scheduled_activities)
        metrics['top5_satisfaction'][troop.name] = {
            'satisfied': troop_satisfied,
            'total': len(troop_top5),
            'percentage': (troop_satisfied / len(troop_top5)) * 100 if troop_top5 else 0
        }
        
        if troop_satisfied < 5:
            missing = [pref for pref in troop_top5 if pref not in scheduled_activities]
            metrics['issues'].append(f"{troop.name} missing Top 5: {missing}")
    
    metrics['preference_stats'] = {
        'total_preferences': total_prefs,
        'satisfied_preferences': satisfied_prefs,
        'satisfaction_rate': (satisfied_prefs / total_prefs) * 100 if total_prefs > 0 else 0,
        'top5_satisfaction_rate': (top5_satisfied / top5_total) * 100 if top5_total > 0 else 0
    }
    
    # 3. Staff Balance Analysis
    staff_loads = scheduler._calculate_staff_load_by_slot()
    if staff_loads:
        loads = list(staff_loads.values())
        metrics['staff_stats'] = {
            'avg_staff': statistics.mean(loads),
            'min_staff': min(loads),
            'max_staff': max(loads),
            'variance': statistics.variance(loads) if len(loads) > 1 else 0,
            'high_load_slots': sum(1 for load in loads if load > 14),
            'underused_slots': sum(1 for load in loads if load < 5)
        }
        
        # Check for staff issues
        if metrics['staff_stats']['max_staff'] > 16:
            metrics['issues'].append(f"Overloaded slot: {metrics['staff_stats']['max_staff']} staff")
        if metrics['staff_stats']['underused_slots'] > 2:
            metrics['issues'].append(f"Too many underused slots: {metrics['staff_stats']['underused_slots']}")
        if metrics['staff_stats']['variance'] > 4:
            metrics['issues'].append(f"High staff variance: {metrics['staff_stats']['variance']:.2f}")
    
    # 4. Clustering Analysis
    from models import EXCLUSIVE_AREAS
    area_days = defaultdict(set)
    for entry in schedule.entries:
        for area, activities in EXCLUSIVE_AREAS.items():
            if entry.activity.name in activities:
                area_days[area].add(entry.time_slot.day)
    
    clustering_issues = 0
    for area, days in area_days.items():
        if len(days) > 3:  # Most activities should be clustered in 2-3 days
            clustering_issues += 1
            metrics['issues'].append(f"{area} spread across {len(days)} days (poor clustering)")
    
    metrics['clustering_stats'] = {
        'areas_with_poor_clustering': clustering_issues,
        'total_areas': len(area_days)
    }
    
    # 5. Constraint Violations (simplified check)
    violations = []
    
    # Check for basic constraint issues
    for entry in schedule.entries:
        # Check for duplicate entries for same troop/slot
        duplicates = [e for e in schedule.entries 
                     if e.troop == entry.troop and e.time_slot == entry.time_slot and e != entry]
        if duplicates:
            violations.append({
                'type': 'Duplicate Entry',
                'message': f"{entry.troop.name} has duplicate entries at {entry.time_slot}"
            })
    
    if violations:
        metrics['constraint_violations'] = {
            'count': len(violations),
            'types': list(set(v['type'] for v in violations))
        }
        metrics['issues'].extend([f"{v['type']}: {v['message']}" for v in violations])
    
    return metrics

def generate_comprehensive_report():
    """Generate and evaluate all schedules."""
    print("COMPREHENSIVE SCHEDULE EVALUATION")
    print("=" * 80)
    
    # Find all troop files
    script_dir = Path(__file__).parent
    troop_files = sorted(script_dir.glob("*troops.json"))
    
    if not troop_files:
        print("No troop files found!")
        return
    
    all_metrics = []
    
    for troops_file in troop_files:
        try:
            metrics = evaluate_single_schedule(troops_file)
            all_metrics.append(metrics)
        except Exception as e:
            print(f"ERROR evaluating {troops_file.name}: {e}")
            continue
    
    # Generate summary report
    print(f"\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}")
    
    if not all_metrics:
        print("No schedules were successfully evaluated!")
        return
    
    # Overall statistics
    total_troops = sum(m['troop_count'] for m in all_metrics)
    avg_satisfaction = statistics.mean([m['preference_stats']['satisfaction_rate'] for m in all_metrics])
    avg_top5 = statistics.mean([m['preference_stats']['top5_satisfaction_rate'] for m in all_metrics])
    total_issues = sum(len(m['issues']) for m in all_metrics)
    
    print(f"\nOVERALL METRICS:")
    print(f"  Total schedules evaluated: {len(all_metrics)}")
    print(f"  Total troops: {total_troops}")
    print(f"  Average preference satisfaction: {avg_satisfaction:.1f}%")
    print(f"  Average Top 5 satisfaction: {avg_top5:.1f}%")
    print(f"  Total issues found: {total_issues}")
    
    # Identify worst performers
    worst_satisfaction = min(all_metrics, key=lambda m: m['preference_stats']['satisfaction_rate'])
    worst_top5 = min(all_metrics, key=lambda m: m['preference_stats']['top5_satisfaction_rate'])
    most_issues = max(all_metrics, key=lambda m: len(m['issues']))
    
    print(f"\nWORST PERFORMERS:")
    print(f"  Lowest satisfaction: {worst_satisfaction['week_name']} ({worst_satisfaction['preference_stats']['satisfaction_rate']:.1f}%)")
    print(f"  Lowest Top 5: {worst_top5['week_name']} ({worst_top5['preference_stats']['top5_satisfaction_rate']:.1f}%)")
    print(f"  Most issues: {most_issues['week_name']} ({len(most_issues['issues'])} issues)")
    
    # Common issues
    all_issue_types = defaultdict(int)
    for metrics in all_metrics:
        for issue in metrics['issues']:
            # Categorize issues
            if "missing Top 5" in issue:
                all_issue_types["Missing Top 5 preferences"] += 1
            elif "gaps" in issue:
                all_issue_types["Gap issues"] += 1
            elif "Overloaded" in issue:
                all_issue_types["Staff overload"] += 1
            elif "underused" in issue:
                all_issue_types["Staff underuse"] += 1
            elif "variance" in issue:
                all_issue_types["Staff imbalance"] += 1
            elif "clustering" in issue:
                all_issue_types["Poor clustering"] += 1
            else:
                all_issue_types["Other"] += 1
    
    print(f"\nCOMMON ISSUE TYPES:")
    for issue_type, count in sorted(all_issue_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {issue_type}: {count} occurrences")
    
    # Detailed breakdown for worst schedules
    print(f"\nDETAILED ANALYSIS OF PROBLEMATIC SCHEDULES:")
    
    for metrics in sorted(all_metrics, key=lambda m: len(m['issues']), reverse=True)[:3]:
        print(f"\n{metrics['week_name'].upper()}:")
        print(f"  Issues ({len(metrics['issues'])}):")
        for issue in metrics['issues'][:5]:  # Show first 5 issues
            print(f"    - {issue}")
        if len(metrics['issues']) > 5:
            print(f"    ... and {len(metrics['issues']) - 5} more")
        print(f"  Satisfaction: {metrics['preference_stats']['satisfaction_rate']:.1f}%")
        print(f"  Top 5: {metrics['preference_stats']['top5_satisfaction_rate']:.1f}%")
        print(f"  Staff variance: {metrics['staff_stats'].get('variance', 0):.2f}")
    
    # Save detailed results
    results_file = script_dir / "comprehensive_evaluation_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_metrics, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    return all_metrics

if __name__ == "__main__":
    generate_comprehensive_report()
