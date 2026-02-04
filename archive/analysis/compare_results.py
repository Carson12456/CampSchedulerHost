"""
Compare scheduling results before/after process changes.
Measures: Top 5/10 satisfaction, clustering efficiency, constraint violations.
"""
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from pathlib import Path
from models import Day
from collections import defaultdict

def analyze_schedule(schedule, scheduler, troops):
    """Return metrics dict for a schedule."""
    metrics = {}
    
    # 1. Preference satisfaction
    top5_achieved = 0
    top10_achieved = 0
    
    for troop in troops:
        entries = [e for e in schedule.entries if e.troop.name == troop.name]
        scheduled_names = {e.activity.name for e in entries}
        
        for i, pref in enumerate(troop.preferences[:5]):
            if pref.name in scheduled_names:
                top5_achieved += 1
        
        for i, pref in enumerate(troop.preferences[:10]):
            if pref.name in scheduled_names:
                top10_achieved += 1
    
    metrics['top5_achieved'] = top5_achieved
    metrics['top5_total'] = len(troops) * 5
    metrics['top5_pct'] = round(100 * top5_achieved / (len(troops) * 5), 1)
    
    metrics['top10_achieved'] = top10_achieved
    metrics['top10_total'] = len(troops) * 10
    metrics['top10_pct'] = round(100 * top10_achieved / (len(troops) * 10), 1)
    
    # 2. Clustering efficiency
    STAFF_AREAS = {
        'Tower': ['Climbing Tower'],
        'ODS': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching', 'Ultimate Survivor', 
                'Leave No Trace', "What's Cooking", 'Chopped!', "Firem'n Chit/Totin' Chip"],
        'Rifle': ['Troop Rifle', 'Troop Shotgun'],
        'Archery': ['Archery/Tomahawks/Slingshots']
    }
    
    for area_name, activities in STAFF_AREAS.items():
        by_day = defaultdict(int)
        for entry in schedule.entries:
            if entry.activity.name in activities:
                by_day[entry.time_slot.day.name] += 1
        
        total = sum(by_day.values())
        days_used = len([d for d in by_day if by_day[d] > 0])
        efficiency = round(total / days_used, 1) if days_used > 0 else 0
        
        metrics[f'{area_name.lower()}_activities'] = total
        metrics[f'{area_name.lower()}_days'] = days_used
        metrics[f'{area_name.lower()}_efficiency'] = efficiency
    
    # 3. Schedule completeness
    all_complete = all(
        len([e for e in schedule.entries if e.troop.name == t.name]) == 14
        for t in troops
    )
    metrics['all_complete'] = all_complete
    metrics['total_entries'] = len(schedule.entries)
    
    return metrics

def print_comparison(baseline, experiment):
    """Print side-by-side comparison."""
    print("\n" + "="*70)
    print("COMPARISON: BASELINE vs EXPERIMENT")
    print("="*70)
    
    print(f"\n{'Metric':<30} {'Baseline':>15} {'Experiment':>15} {'Diff':>10}")
    print("-"*70)
    
    # Preference satisfaction
    print(f"{'Top 5 Achieved':<30} {baseline['top5_achieved']:>15} {experiment['top5_achieved']:>15} {experiment['top5_achieved'] - baseline['top5_achieved']:>+10}")
    print(f"{'Top 5 %':<30} {baseline['top5_pct']:>14}% {experiment['top5_pct']:>14}%")
    print(f"{'Top 10 Achieved':<30} {baseline['top10_achieved']:>15} {experiment['top10_achieved']:>15} {experiment['top10_achieved'] - baseline['top10_achieved']:>+10}")
    print(f"{'Top 10 %':<30} {baseline['top10_pct']:>14}% {experiment['top10_pct']:>14}%")
    
    print()
    
    # Clustering
    for area in ['tower', 'ods', 'rifle', 'archery']:
        b_days = baseline[f'{area}_days']
        e_days = experiment[f'{area}_days']
        diff = e_days - b_days
        better = "✅" if diff < 0 else ("⚠️" if diff > 0 else "")
        print(f"{area.upper() + ' days used':<30} {b_days:>15} {e_days:>15} {diff:>+10} {better}")
    
    print()
    print(f"{'Schedule Complete':<30} {str(baseline['all_complete']):>15} {str(experiment['all_complete']):>15}")
    print(f"{'Total Entries':<30} {baseline['total_entries']:>15} {experiment['total_entries']:>15}")

if __name__ == "__main__":
    troops = load_troops_from_json(Path('tc_week5_troops.json'))
    
    print("Running BASELINE schedule...")
    scheduler = ConstrainedScheduler(troops)
    schedule = scheduler.schedule_all()
    baseline = analyze_schedule(schedule, scheduler, troops)
    
    print("\n" + "="*70)
    print("BASELINE RESULTS")
    print("="*70)
    print(f"Top 5: {baseline['top5_achieved']}/{baseline['top5_total']} ({baseline['top5_pct']}%)")
    print(f"Top 10: {baseline['top10_achieved']}/{baseline['top10_total']} ({baseline['top10_pct']}%)")
    print(f"Tower: {baseline['tower_activities']} activities / {baseline['tower_days']} days")
    print(f"ODS: {baseline['ods_activities']} activities / {baseline['ods_days']} days")
    print(f"Rifle: {baseline['rifle_activities']} activities / {baseline['rifle_days']} days")
    print(f"Archery: {baseline['archery_activities']} activities / {baseline['archery_days']} days")
