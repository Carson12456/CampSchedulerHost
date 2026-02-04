#!/usr/bin/env python3
"""
Aggressive optimizer that targets the highest-impact score improvements.
Focuses on constraint violations, excess cluster days, and missing Top 5.
"""

import sys
import os
sys.path.append('.')

from evaluate_week_success import evaluate_week
from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities, get_activity_by_name
from io_handler import load_troops_from_json, load_schedule_from_json, save_schedule_to_json
from models import Day, EXCLUSIVE_AREAS

def aggressive_optimize_schedule(week_file):
    """Apply aggressive optimizations to maximize score improvement."""
    print(f"\n{'='*60}")
    print(f"AGGRESSIVE OPTIMIZATION FOR {week_file}")
    print(f"{'='*60}")
    
    # Load baseline
    troops = load_troops_from_json(week_file)
    activities = get_all_activities()
    
    week_basename = os.path.splitext(os.path.basename(week_file))[0]
    schedule_file = os.path.join("schedules", f"{week_basename}_schedule.json")
    
    # Load existing schedule
    schedule = load_schedule_from_json(schedule_file, troops, activities)
    scheduler = ConstrainedScheduler(troops, activities)
    scheduler.schedule = schedule
    
    # Evaluate baseline
    baseline_metrics = evaluate_week(week_file)
    print(f"BASELINE: Score={baseline_metrics['final_score']}")
    
    # Calculate potential improvements
    constraint_potential = baseline_metrics['constraint_violations'] * 25
    cluster_potential = baseline_metrics['excess_cluster_days'] * 8
    top5_potential = baseline_metrics['missing_top5'] * 8
    variance_potential = baseline_metrics['staff_variance'] * 8
    
    print(f"POTENTIAL IMPROVEMENTS:")
    print(f"  Constraint fixes: +{constraint_potential} points")
    print(f"  Cluster reduction: +{cluster_potential} points") 
    print(f"  Top 5 recovery: +{top5_potential} points")
    print(f"  Variance reduction: +{variance_potential:.1f} points")
    print(f"  TOTAL POTENTIAL: +{constraint_potential + cluster_potential + top5_potential + variance_potential:.1f} points")
    
    improvements_made = 0
    
    # 1. AGGRESSIVE CONSTRAINT VIOLATION FIXES
    print(f"\n--- 1. AGGRESSIVE CONSTRAINT VIOLATION FIXES ---")
    constraint_fixes = fix_constraint_violations_aggressive(scheduler, troops)
    improvements_made += constraint_fixes
    print(f"  Constraint violations fixed: {constraint_fixes}")
    
    # 2. AGGRESSIVE CLUSTERING OPTIMIZATION
    print(f"\n--- 2. AGGRESSIVE CLUSTERING OPTIMIZATION ---")
    cluster_fixes = fix_clustering_aggressive(scheduler, troops)
    improvements_made += cluster_fixes
    print(f"  Clustering improvements: {cluster_fixes}")
    
    # 3. AGGRESSIVE TOP 5 RECOVERY
    print(f"\n--- 3. AGGRESSIVE TOP 5 RECOVERY ---")
    top5_fixes = fix_top5_aggressive(scheduler, troops)
    improvements_made += top5_fixes
    print(f"  Top 5 recoveries: {top5_fixes}")
    
    # 4. STAFF VARIANCE OPTIMIZATION
    print(f"\n--- 4. STAFF VARIANCE OPTIMIZATION ---")
    variance_fixes = fix_staff_variance_aggressive(scheduler, troops)
    improvements_made += variance_fixes
    print(f"  Staff variance optimizations: {variance_fixes}")
    
    # Save and evaluate
    optimized_schedule_file = os.path.join("schedules", f"{week_basename}_aggressive_optimized.json")
    save_schedule_to_json(schedule, troops, optimized_schedule_file)
    
    # Evaluate optimized version
    original_file = schedule_file
    backup_file = schedule_file + ".backup"
    
    if os.path.exists(original_file):
        os.rename(original_file, backup_file)
    os.rename(optimized_schedule_file, original_file)
    
    try:
        optimized_metrics = evaluate_week(week_file)
        score_improvement = optimized_metrics['final_score'] - baseline_metrics['final_score']
        
        print(f"\n--- RESULTS ---")
        print(f"OPTIMIZED: Score={optimized_metrics['final_score']}")
        print(f"IMPROVEMENT: +{score_improvement}")
        print(f"  Excess Days: {baseline_metrics['excess_cluster_days']} -> {optimized_metrics['excess_cluster_days']}")
        print(f"  Violations: {baseline_metrics['constraint_violations']} -> {optimized_metrics['constraint_violations']}")
        print(f"  Missing Top 5: {baseline_metrics['missing_top5']} -> {optimized_metrics['missing_top5']}")
        print(f"  Staff Variance: {baseline_metrics['staff_variance']:.2f} -> {optimized_metrics['staff_variance']:.2f}")
        
        return score_improvement
        
    finally:
        # Restore original
        if os.path.exists(original_file):
            os.remove(original_file)
        if os.path.exists(backup_file):
            os.rename(backup_file, original_file)

def fix_constraint_violations_aggressive(scheduler, troops):
    """Aggressively fix constraint violations by any means necessary."""
    violations_fixed = 0
    
    # 1. Fix accuracy conflicts with highest priority
    accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
    
    for troop in troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        day_accuracy = {}
        
        for entry in troop_entries:
            if entry.activity.name in accuracy_activities:
                day_accuracy.setdefault(entry.time_slot.day, []).append(entry)
        
        for day, entries in day_accuracy.items():
            if len(entries) > 1:
                # Keep highest priority, move others aggressively
                entries.sort(key=lambda e: troop.get_priority(e.activity.name))
                
                for entry in entries[1:]:
                    # Find ANY available slot on ANY day
                    for alt_day in Day:
                        if alt_day == day:
                            continue
                        
                        # Check if already has accuracy on this day
                        if any(e.time_slot.day == alt_day and e.activity.name in accuracy_activities 
                               for e in troop_entries):
                            continue
                        
                        # Find any slot
                        for slot in scheduler.time_slots:
                            if slot.day != alt_day:
                                continue
                            if not scheduler.schedule.is_troop_free(slot, troop):
                                continue
                            
                            # Force the move regardless of constraints
                            old_day = entry.time_slot.day
                            scheduler.schedule.entries.remove(entry)
                            scheduler.schedule.add_entry(slot, entry.activity, troop)
                            violations_fixed += 1
                            print(f"    [Forced] {troop.name}: {entry.activity.name} {old_day.name[:3]} -> {alt_day.name[:3]} (accuracy)")
                            break
                        break
    
    # 2. Fix wet-dry-wet patterns
    wet_activities = [
        "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
        "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", 
        "Canoe Snorkel", "Nature Canoe", "Float for Floats", "Sailing"
    ]
    
    for troop in troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        day_slots = {}
        
        for entry in troop_entries:
            day_slots.setdefault(entry.time_slot.day, {})[entry.time_slot.slot_number] = entry.activity.name
        
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            slots = day_slots.get(day, {})
            if 1 in slots and 2 in slots and 3 in slots:
                s1_wet = slots[1] in wet_activities
                s2_wet = slots[2] in wet_activities
                s3_wet = slots[3] in wet_activities
                
                if s1_wet and not s2_wet and s3_wet:
                    # Force move the slot 3 wet activity
                    wet_activity = slots[3]
                    
                    for entry in troop_entries:
                        if (entry.activity.name == wet_activity and 
                            entry.time_slot.day == day and 
                            entry.time_slot.slot_number == 3):
                            
                            # Find any alternative slot
                            for alt_day in Day:
                                if alt_day == day:
                                    continue
                                
                                for slot in scheduler.time_slots:
                                    if slot.day != alt_day:
                                        continue
                                    if not scheduler.schedule.is_troop_free(slot, troop):
                                        continue
                                    
                                    # Force move
                                    scheduler.schedule.entries.remove(entry)
                                    scheduler.schedule.add_entry(slot, entry.activity, troop)
                                    violations_fixed += 1
                                    print(f"    [Forced] {troop.name}: {wet_activity} {day.name[:3]}-3 -> {alt_day.name[:3]} (wet-dry-wet)")
                                    break
                                break
                            break
    
    return violations_fixed

def fix_clustering_aggressive(scheduler, troops):
    """Aggressively reduce excess cluster days."""
    cluster_moves = 0
    
    # Target cluster areas
    cluster_areas = ["Tower", "Rifle Range", "Outdoor Skills", "Handicrafts"]
    
    for area in cluster_areas:
        activities = EXCLUSIVE_AREAS.get(area, [])
        if not activities:
            continue
            
        area_entries = [e for e in scheduler.schedule.entries if e.activity.name in activities]
        if len(area_entries) < 4:
            continue
        
        # Count current distribution
        day_counts = {}
        for entry in area_entries:
            day_counts[entry.time_slot.day] = day_counts.get(entry.time_slot.day, 0) + 1
        
        # Calculate excess days
        import math
        num_activities = len(area_entries)
        min_days = math.ceil(num_activities / 3.0)
        current_days = len(day_counts)
        excess_days = max(0, current_days - min_days)
        
        if excess_days <= 0:
            continue
        
        # Find best days to keep
        best_days = sorted(day_counts.keys(), key=lambda d: day_counts[d], reverse=True)[:min_days]
        excess_day_list = [day for day in day_counts.keys() if day not in best_days]
        
        # Aggressively move all activities from excess days
        for entry in area_entries[:]:
            if entry.time_slot.day not in excess_day_list:
                continue
            
            # Try to move to any best day
            for best_day in best_days:
                for slot in scheduler.time_slots:
                    if slot.day != best_day:
                        continue
                    if not scheduler.schedule.is_troop_free(slot, entry.troop):
                        continue
                    
                    # Force the move
                    old_day = entry.time_slot.day
                    scheduler.schedule.entries.remove(entry)
                    scheduler.schedule.add_entry(slot, entry.activity, entry.troop)
                    cluster_moves += 1
                    print(f"    [Forced] {entry.troop.name}: {entry.activity.name} {old_day.name[:3]} -> {best_day.name[:3]} (cluster)")
                    break
                break
    
    return cluster_moves

def fix_top5_aggressive(scheduler, troops):
    """Aggressively recover missing Top 5 preferences."""
    top5_recoveries = 0
    
    for troop in troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        scheduled = {e.activity.name for e in troop_entries}
        
        top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        missing = [(i, pref) for i, pref in enumerate(top5) if pref not in scheduled]
        
        if not missing:
            continue
        
        for rank, missing_pref in missing:
            activity = get_activity_by_name(missing_pref)
            if not activity:
                continue
            
            # Find ANY displaceable entry (including Top 5 if necessary)
            displaceable = troop_entries
            
            def get_priority(entry):
                try:
                    return troop.preferences.index(entry.activity.name)
                except ValueError:
                    return 999
            
            displaceable.sort(key=get_priority, reverse=True)
            
            # Try to place in ANY available slot
            for entry in displaceable:
                for slot in scheduler.time_slots:
                    if not scheduler.schedule.is_troop_free(slot, troop):
                        continue
                    
                    # Remove the entry and try to place Top 5
                    scheduler.schedule.entries.remove(entry)
                    
                    if scheduler._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                        scheduler.schedule.add_entry(slot, activity, troop)
                        top5_recoveries += 1
                        print(f"    [Forced] {troop.name}: {missing_pref} (Top {rank+1}) <- {entry.activity.name}")
                        break
                    else:
                        # Restore and try next
                        scheduler.schedule.add_entry(entry.time_slot, entry.activity, troop)
                
                if top5_recoveries > 0:
                    break
    
    return top5_recoveries

def fix_staff_variance_aggressive(scheduler, troops):
    """Aggressively balance staff variance."""
    # Staff activity mapping
    STAFF_MAP = {
        'Beach Staff': ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                       'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                       'Troop Swim', 'Water Polo', 'Sailing'],
        'Tower Director': ['Climbing Tower'],
        'Rifle Director': ['Troop Rifle', 'Troop Shotgun'],
        'ODS Director': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                        'Ultimate Survivor', "What's Cooking", 'Chopped!'],
        'Handicrafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
        'Nature': ['Dr. DNA', 'Loon Lore', 'Nature Canoe'],
        'Archery': ['Archery']
    }
    
    all_staff_activities = set()
    for acts in STAFF_MAP.values():
        all_staff_activities.update(acts)
    
    # Count current staff load
    from collections import defaultdict
    slot_counts = defaultdict(int)
    staff_entries = []
    
    for entry in scheduler.schedule.entries:
        if entry.activity.name in all_staff_activities:
            slot_counts[(entry.time_slot.day, entry.time_slot.slot_number)] += 1
            staff_entries.append(entry)
    
    if not staff_entries:
        return 0
    
    # Calculate variance
    counts_list = list(slot_counts.values())
    avg_load = sum(counts_list) / len(counts_list)
    current_variance = sum((c - avg_load) ** 2 for c in counts_list) / len(counts_list)
    
    optimizations = 0
    
    # Aggressively balance by moving from overloaded to underloaded slots
    for entry in staff_entries[:]:
        current_slot = (entry.time_slot.day, entry.time_slot.slot_number)
        current_load = slot_counts[current_slot]
        
        # Find most underloaded slots
        underloaded = [(slot, load) for slot, load in slot_counts.items() 
                      if load < current_load - 1]
        underloaded.sort(key=lambda x: x[1])
        
        for (target_day, target_slot_num), target_load in underloaded:
            # Find slot object
            target_slot = None
            for slot in scheduler.time_slots:
                if slot.day == target_day and slot.slot_number == target_slot_num:
                    target_slot = slot
                    break
            
            if not target_slot:
                continue
            
            if not scheduler.schedule.is_troop_free(target_slot, entry.troop):
                continue
            
            # Force the move
            scheduler.schedule.entries.remove(entry)
            scheduler.schedule.add_entry(target_slot, entry.activity, entry.troop)
            
            slot_counts[current_slot] -= 1
            slot_counts[(target_day, target_slot_num)] += 1
            
            optimizations += 1
            print(f"    [Forced] {entry.troop.name}: {entry.activity.name} {entry.time_slot.day.name[:3]}-{entry.time_slot.slot_number} -> {target_day.name[:3]}-{target_slot_num}")
            break
    
    return optimizations

def main():
    """Run aggressive optimization on low-scoring weeks."""
    low_scoring_weeks = [
        'tc_week3_troops.json',
        'tc_week5_troops.json', 
        'tc_week6_troops.json'
    ]
    
    total_improvement = 0
    
    for week_file in low_scoring_weeks:
        try:
            improvement = aggressive_optimize_schedule(week_file)
            total_improvement += improvement
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"TOTAL AGGRESSIVE OPTIMIZATION IMPROVEMENT: +{total_improvement}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
