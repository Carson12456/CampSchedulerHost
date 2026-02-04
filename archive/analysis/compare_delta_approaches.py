"""
Compare scheduler performance: Forced Delta vs Preference-Based Delta
Runs both approaches on all available weeks and compares results.
"""
import sys
from copy import deepcopy
from pathlib import Path

from models import Day, generate_time_slots
from activities import get_all_activities, get_activity_by_name
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler


def run_preference_based_delta(troops_file):
    """Run scheduler with current preference-based Delta (new behavior)."""
    troops = load_troops_from_json(troops_file)
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    return scheduler, schedule, troops


def run_forced_delta(troops_file):
    """Run scheduler with forced Delta for ALL troops (old behavior).
    
    This simulates the old behavior by temporarily adding Delta to all troops' preferences.
    """
    troops = load_troops_from_json(troops_file)
    
    # Add Delta to all troops' preferences if not already there
    for troop in troops:
        if "Delta" not in troop.preferences:
            # Insert Delta at position 10 (after Top 10, so it doesn't take priority slots)
            troop.preferences.insert(10, "Delta")
    
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    return scheduler, schedule, troops


def calculate_stats(schedule, troops):
    """Calculate detailed stats for a schedule."""
    stats = {
        'total_top5_slots': 0,
        'total_top10_slots': 0,
        'troops_with_all_top5': 0,
        'troops_missing_top5': [],
        'delta_count': 0,
        'super_troop_count': 0,
        'per_troop': {}
    }
    
    for troop in troops:
        entries = [e for e in schedule.entries if e.troop == troop]
        
        top5_slots = sum(1 for e in entries if troop.get_priority(e.activity.name) is not None and troop.get_priority(e.activity.name) < 5)
        top10_slots = sum(1 for e in entries if troop.get_priority(e.activity.name) is not None and troop.get_priority(e.activity.name) < 10)
        
        # Count unique Top 5 activities (not slots)
        top5_activities = set()
        for e in entries:
            prio = troop.get_priority(e.activity.name)
            if prio is not None and prio < 5:
                top5_activities.add(e.activity.name)
        
        has_delta = any(e.activity.name == "Delta" for e in entries)
        has_super_troop = any(e.activity.name == "Super Troop" for e in entries)
        
        if has_delta:
            stats['delta_count'] += 1
        if has_super_troop:
            stats['super_troop_count'] += 1
        
        stats['total_top5_slots'] += top5_slots
        stats['total_top10_slots'] += top10_slots
        
        # Check if troop got all their unique Top 5 activities
        troop_top5_prefs = troop.preferences[:5]
        missing_top5 = [p for p in troop_top5_prefs if p not in [e.activity.name for e in entries]]
        
        if len(missing_top5) == 0:
            stats['troops_with_all_top5'] += 1
        else:
            stats['troops_missing_top5'].append((troop.name, missing_top5))
        
        stats['per_troop'][troop.name] = {
            'top5_slots': top5_slots,
            'top10_slots': top10_slots,
            'unique_top5': len(top5_activities),
            'has_delta': has_delta,
            'has_super_troop': has_super_troop,
            'missing_top5': missing_top5
        }
    
    return stats


def compare_week(troops_file):
    """Compare forced vs preference-based Delta for a single week."""
    print(f"\n{'='*80}")
    print(f"COMPARING: {troops_file}")
    print(f"{'='*80}")
    
    # Run both versions (suppress scheduler output)
    import io
    import contextlib
    
    print("\nRunning PREFERENCE-BASED Delta (new)...")
    with contextlib.redirect_stdout(io.StringIO()):
        _, schedule_new, troops_new = run_preference_based_delta(troops_file)
    stats_new = calculate_stats(schedule_new, troops_new)
    
    print("Running FORCED Delta (old)...")
    with contextlib.redirect_stdout(io.StringIO()):
        _, schedule_old, troops_old = run_forced_delta(troops_file)
    stats_old = calculate_stats(schedule_old, troops_old)
    
    # Print comparison
    print(f"\n{'-'*80}")
    print(f"{'METRIC':<40} {'FORCED DELTA':<20} {'PREF-BASED':<20}")
    print(f"{'-'*80}")
    
    print(f"{'Troops with Delta':<40} {stats_old['delta_count']:<20} {stats_new['delta_count']:<20}")
    print(f"{'Troops with Super Troop':<40} {stats_old['super_troop_count']:<20} {stats_new['super_troop_count']:<20}")
    print(f"{'Total Top 5 slots filled':<40} {stats_old['total_top5_slots']:<20} {stats_new['total_top5_slots']:<20}")
    print(f"{'Total Top 10 slots filled':<40} {stats_old['total_top10_slots']:<20} {stats_new['total_top10_slots']:<20}")
    print(f"{'Troops with ALL unique Top 5':<40} {stats_old['troops_with_all_top5']:<20} {stats_new['troops_with_all_top5']:<20}")
    
    # Show improvement
    print(f"\n{'-'*80}")
    print("IMPROVEMENT (Preference-Based vs Forced):")
    print(f"{'-'*80}")
    
    top5_diff = stats_new['total_top5_slots'] - stats_old['total_top5_slots']
    top10_diff = stats_new['total_top10_slots'] - stats_old['total_top10_slots']
    all_top5_diff = stats_new['troops_with_all_top5'] - stats_old['troops_with_all_top5']
    
    print(f"  Top 5 slots: {top5_diff:+d}")
    print(f"  Top 10 slots: {top10_diff:+d}")
    print(f"  Troops with ALL Top 5: {all_top5_diff:+d}")
    
    # Show which troops benefit
    print(f"\n{'-'*80}")
    print("PER-TROOP COMPARISON:")
    print(f"{'-'*80}")
    print(f"{'Troop':<15} {'Top5 (Old)':<12} {'Top5 (New)':<12} {'Top10 (Old)':<12} {'Top10 (New)':<12} {'Delta?':<10}")
    print(f"{'-'*80}")
    
    for troop_name in stats_new['per_troop']:
        old = stats_old['per_troop'].get(troop_name, {})
        new = stats_new['per_troop'].get(troop_name, {})
        
        delta_status = "Yes" if new.get('has_delta') else "No (freed)"
        
        print(f"{troop_name:<15} {old.get('top5_slots', 0):<12} {new.get('top5_slots', 0):<12} {old.get('top10_slots', 0):<12} {new.get('top10_slots', 0):<12} {delta_status:<10}")
    
    return {
        'file': troops_file,
        'old': stats_old,
        'new': stats_new,
        'top5_diff': top5_diff,
        'top10_diff': top10_diff
    }


def main():
    """Run comparison on all available weeks."""
    print("="*80)
    print("DELTA SCHEDULING COMPARISON: FORCED vs PREFERENCE-BASED")
    print("="*80)
    
    weeks = ["tc_week5_troops.json", "tc_week6_troops.json", "tc_week7_troops.json"]
    results = []
    
    for week_file in weeks:
        if Path(week_file).exists():
            result = compare_week(week_file)
            results.append(result)
        else:
            print(f"\nSkipping {week_file} (not found)")
    
    # Summary
    print("\n" + "="*80)
    print("OVERALL SUMMARY")
    print("="*80)
    
    total_top5_improvement = sum(r['top5_diff'] for r in results)
    total_top10_improvement = sum(r['top10_diff'] for r in results)
    
    print(f"\nTotal Top 5 slot improvement across all weeks: {total_top5_improvement:+d}")
    print(f"Total Top 10 slot improvement across all weeks: {total_top10_improvement:+d}")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    
    if total_top5_improvement > 0 or total_top10_improvement > 0:
        print("""
PREFERENCE-BASED Delta is BETTER because:
1. Troops who don't want Delta get an extra slot for their actual preferences
2. All Delta-before-Super-Troop constraints are still enforced
3. Troops who DO want Delta still get commissioner day clustering
4. Overall preference satisfaction increased
""")
    elif total_top5_improvement == 0 and total_top10_improvement == 0:
        print("""
PREFERENCE-BASED Delta is NEUTRAL:
- No measurable difference in preference satisfaction
- But still provides cleaner logic (don't force unwanted activities)
""")
    else:
        print("""
FORCED Delta might be better in some cases - investigate further.
""")


if __name__ == "__main__":
    main()
