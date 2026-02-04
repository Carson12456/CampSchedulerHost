#!/usr/bin/env python3
"""
Quick evaluation of schedules to identify key issues.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import statistics

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def analyze_single_schedule(troops_file):
    """Quick analysis of one schedule."""
    print(f"\nAnalyzing: {troops_file.name}")
    print("-" * 50)
    
    try:
        from io_handler import load_troops_from_json
        from activities import get_all_activities
        from constrained_scheduler import ConstrainedScheduler
        from models import Day
        
        # Load and generate schedule
        troops = load_troops_from_json(troops_file)
        activities = get_all_activities()
        scheduler = ConstrainedScheduler(troops, activities)
        schedule = scheduler.schedule_all()
        
        # Ensure 0 gaps
        scheduler._force_zero_gaps_absolute()
        
        # Basic metrics
        metrics = {
            'week_name': troops_file.stem,
            'troop_count': len(troops),
            'total_entries': len(schedule.entries),
            'gaps': 0,
            'troop_gaps': {},
            'issues': []
        }
        
        # Gap analysis
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
        
        # Preference satisfaction
        total_prefs = 0
        satisfied_prefs = 0
        top5_satisfied = 0
        top5_total = 0
        
        for troop in troops:
            troop_entries = schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_entries}
            
            for i, pref in enumerate(troop.preferences):
                total_prefs += 1
                if pref in scheduled_activities:
                    satisfied_prefs += 1
                    if i < 5:
                        top5_satisfied += 1
                if i < 5:
                    top5_total += 1
        
        satisfaction_rate = (satisfied_prefs / total_prefs) * 100 if total_prefs > 0 else 0
        top5_rate = (top5_satisfied / top5_total) * 100 if top5_total > 0 else 0
        
        # Clustering analysis
        from models import EXCLUSIVE_AREAS
        area_days = defaultdict(set)
        for entry in schedule.entries:
            for area, activities in EXCLUSIVE_AREAS.items():
                if entry.activity.name in activities:
                    area_days[area].add(entry.time_slot.day)
        
        clustering_issues = 0
        for area, days in area_days.items():
            if len(days) > 3:
                clustering_issues += 1
                metrics['issues'].append(f"{area} spread across {len(days)} days")
        
        # Staff analysis
        staff_loads = scheduler._calculate_staff_load_by_slot()
        if staff_loads:
            loads = list(staff_loads.values())
            variance = statistics.variance(loads) if len(loads) > 1 else 0
            if variance > 4:
                metrics['issues'].append(f"High staff variance: {variance:.2f}")
        
        print(f"  Gaps: {total_gaps}")
        print(f"  Satisfaction: {satisfaction_rate:.1f}%")
        print(f"  Top 5: {top5_rate:.1f}%")
        print(f"  Clustering issues: {clustering_issues}")
        print(f"  Total issues: {len(metrics['issues'])}")
        
        if metrics['issues']:
            print("  Issues:")
            for issue in metrics['issues'][:5]:
                print(f"    - {issue}")
        
        return metrics
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

def main():
    """Run quick evaluation on all schedules."""
    print("QUICK SCHEDULE EVALUATION")
    print("=" * 60)
    
    # Find all troop files
    script_dir = Path(__file__).parent
    troop_files = sorted(script_dir.glob("*troops.json"))
    
    if not troop_files:
        print("No troop files found!")
        return
    
    all_metrics = []
    
    for troops_file in troop_files:
        metrics = analyze_single_schedule(troops_file)
        if metrics:
            all_metrics.append(metrics)
    
    if not all_metrics:
        print("No schedules successfully evaluated!")
        return
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    total_gaps = sum(m['gaps'] for m in all_metrics)
    avg_satisfaction = statistics.mean([m.get('satisfaction_rate', 0) for m in all_metrics])
    total_issues = sum(len(m['issues']) for m in all_metrics)
    
    print(f"\nTotal schedules: {len(all_metrics)}")
    print(f"Total gaps: {total_gaps}")
    print(f"Average satisfaction: {avg_satisfaction:.1f}%")
    print(f"Total issues: {total_issues}")
    
    # Worst performers
    if all_metrics:
        worst_issues = max(all_metrics, key=lambda m: len(m['issues']))
        print(f"\nMost issues: {worst_issues['week_name']} ({len(worst_issues['issues'])} issues)")
        
        print(f"\nTop issues across all schedules:")
        all_issue_types = defaultdict(int)
        for metrics in all_metrics:
            for issue in metrics['issues']:
                if "gaps" in issue:
                    all_issue_types["Gap issues"] += 1
                elif "spread across" in issue:
                    all_issue_types["Poor clustering"] += 1
                elif "variance" in issue:
                    all_issue_types["Staff imbalance"] += 1
                else:
                    all_issue_types["Other"] += 1
        
        for issue_type, count in sorted(all_issue_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {issue_type}: {count}")

if __name__ == "__main__":
    main()
