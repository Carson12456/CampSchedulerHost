#!/usr/bin/env python3
"""
Apply Top 5 beach fixes to all weeks for system-wide improvement.
"""

import json
from pathlib import Path
from io_handler import load_troops_from_json
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler
from collections import defaultdict

def apply_fixes_to_all_weeks():
    """
    Apply comprehensive Top 5 beach fixes to all available weeks.
    """
    print("APPLYING TOP 5 BEACH FIXES TO ALL WEEKS")
    print("=" * 45)
    
    # Get all troop files
    troop_files = list(Path(".").glob("*_troops.json"))
    
    results = {
        'weeks_processed': 0,
        'total_before_misses': 0,
        'total_after_misses': 0,
        'total_fixes_applied': 0,
        'week_results': {}
    }
    
    for troops_file in sorted(troop_files):
        week_name = troops_file.stem.replace('_troops', '')
        print(f"\nProcessing {week_name}...")
        
        try:
            # Load troops and generate schedule
            troops = load_troops_from_json(troops_file)
            activities = get_all_activities()
            scheduler = ConstrainedScheduler(troops, activities)
            schedule = scheduler.schedule_all()
            
            # Convert to dict format for easier manipulation
            schedule_data = convert_schedule_to_dict(schedule)
            
            # Analyze before fixes
            before_misses = analyze_missed_preferences(schedule_data, troops)
            at_misses_before = [m for m in before_misses if m['activity'] == 'Aqua Trampoline']
            results['total_before_misses'] += len(before_misses)
            
            print(f"  Before: {len(before_misses)} missed Top 5 ({len(at_misses_before)} AT)")
            
            # Apply comprehensive fixes
            fixes = apply_comprehensive_fixes(schedule_data, troops)
            results['total_fixes_applied'] += len(fixes)
            
            # Analyze after fixes
            after_misses = analyze_missed_preferences(schedule_data, troops)
            at_misses_after = [m for m in after_misses if m['activity'] == 'Aqua Trampoline']
            results['total_after_misses'] += len(after_misses)
            
            improvement = len(before_misses) - len(after_misses)
            at_improvement = len(at_misses_before) - len(at_misses_after)
            
            print(f"  After: {len(after_misses)} missed Top 5 ({len(at_misses_after)} AT)")
            print(f"  Improvement: {improvement} total, {at_improvement} AT")
            print(f"  Fixes applied: {len(fixes)}")
            
            # Save fixed schedule
            save_fixed_schedule(schedule_data, week_name)
            
            # Store week results
            results['week_results'][week_name] = {
                'before_misses': len(before_misses),
                'after_misses': len(after_misses),
                'at_before': len(at_misses_before),
                'at_after': len(at_misses_after),
                'improvement': improvement,
                'at_improvement': at_improvement,
                'fixes_applied': len(fixes)
            }
            
            results['weeks_processed'] += 1
            
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    
    # Generate comprehensive summary
    print(f"\n" + "=" * 45)
    print("SYSTEM-WIDE RESULTS SUMMARY")
    print("=" * 45)
    
    total_improvement = results['total_before_misses'] - results['total_after_misses']
    improvement_rate = (total_improvement / results['total_before_misses'] * 100) if results['total_before_misses'] > 0 else 0
    
    print(f"Weeks processed: {results['weeks_processed']}")
    print(f"Total missed Top 5 before: {results['total_before_misses']}")
    print(f"Total missed Top 5 after: {results['total_after_misses']}")
    print(f"Total improvement: {total_improvement}")
    print(f"Improvement rate: {improvement_rate:.1f}%")
    print(f"Total fixes applied: {results['total_fixes_applied']}")
    
    # Week-by-week breakdown
    print(f"\nWEEK-BY-WEEK BREAKDOWN:")
    print("Week        Before   After    AT Before  AT After  Improvement")
    print("-" * 65)
    
    for week, result in results['week_results'].items():
        print(f"{week:<12} {result['before_misses']:<8} {result['after_misses']:<8} "
              f"{result['at_before']:<9} {result['at_after']:<9} {result['improvement']}")
    
    # Calculate AT-specific improvements
    total_at_before = sum(r['at_before'] for r in results['week_results'].values())
    total_at_after = sum(r['at_after'] for r in results['week_results'].values())
    at_improvement = total_at_before - total_at_after
    at_improvement_rate = (at_improvement / total_at_before * 100) if total_at_before > 0 else 0
    
    print(f"\nAQUA TRAMPOLINE SPECIFIC:")
    print(f"Total AT misses before: {total_at_before}")
    print(f"Total AT misses after: {total_at_after}")
    print(f"AT improvement: {at_improvement}")
    print(f"AT improvement rate: {at_improvement_rate:.1f}%")
    
    return results

def convert_schedule_to_dict(schedule):
    """Convert schedule object to dict format."""
    return {
        'entries': [
            {
                'troop': entry.troop.name,
                'activity': entry.activity.name,
                'day': entry.time_slot.day.value,
                'slot': entry.time_slot.slot_number
            }
            for entry in schedule.entries
        ]
    }

def analyze_missed_preferences(schedule_data, troops):
    """Analyze missed Top 5 preferences."""
    missed = []
    
    # Build troop activities lookup
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry['activity'])
    
    for troop in troops:
        troop_name = troop.name
        activities = troop_activities[troop_name]
        
        # Check Top 5 preferences
        top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        
        for i, pref in enumerate(top5):
            if pref not in activities:
                missed.append({
                    'troop': troop_name,
                    'activity': pref,
                    'rank': i + 1
                })
    
    return missed

def apply_comprehensive_fixes(schedule_data, troops):
    """Apply comprehensive fixes to resolve Top 5 misses."""
    fixes = []
    
    # Fix 1: Aqua Trampoline constraint relaxation
    at_fixes = apply_at_constraint_relaxation(schedule_data, troops)
    fixes.extend(at_fixes)
    
    # Fix 2: Smart activity swapping
    swap_fixes = apply_smart_swapping(schedule_data, troops)
    fixes.extend(swap_fixes)
    
    # Fix 3: Force placement for critical preferences
    force_fixes = apply_force_placement(schedule_data, troops)
    fixes.extend(force_fixes)
    
    return fixes

def apply_at_constraint_relaxation(schedule_data, troops):
    """Apply Aqua Trampoline constraint relaxation."""
    fixes = []
    
    # Build troop activities lookup
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry)
    
    for troop in troops:
        troop_name = troop.name
        activities = [entry['activity'] for entry in troop_activities[troop_name]]
        
        # Check if AT is in Top 5 but not scheduled
        top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        
        if "Aqua Trampoline" in top5 and "Aqua Trampoline" not in activities:
            rank = top5.index("Aqua Trampoline") + 1
            
            # Apply rank-based relaxation
            if rank <= 2:  # Rank #1-2 gets aggressive treatment
                available_slots = find_available_slots(schedule_data, troop_name)
                if available_slots:
                    slot = available_slots[0]
                    
                    new_entry = {
                        'troop': troop_name,
                        'activity': 'Aqua Trampoline',
                        'day': slot['day'],
                        'slot': slot['slot']
                    }
                    schedule_data['entries'].append(new_entry)
                    
                    fixes.append({
                        'type': 'AT_Relaxation',
                        'troop': troop_name,
                        'rank': rank,
                        'slot': f"{slot['day']}-{slot['slot']}"
                    })
    
    return fixes

def apply_smart_swapping(schedule_data, troops):
    """Apply smart activity swapping."""
    fixes = []
    
    # Build troop preferences and activities lookup
    troop_preferences = {troop.name: troop.preferences for troop in troops}
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry)
    
    # Find swap opportunities
    for entry in schedule_data['entries']:
        troop = entry['troop']
        activity = entry['activity']
        
        if troop in troop_preferences:
            preferences = troop_preferences[troop]
            if activity in preferences:
                current_rank = preferences.index(activity) + 1
                
                # Look for swap opportunities for low-preference activities
                if current_rank > 10:  # Low preference
                    # Try to find a high-preference activity
                    for i, pref in enumerate(preferences[:5]):  # Top 5
                        if pref != activity and pref not in [e['activity'] for e in troop_activities[troop]]:
                            # Perform the swap
                            entry['activity'] = pref
                            
                            fixes.append({
                                'type': 'Smart_Swap',
                                'troop': troop,
                                'from': f"{activity} (Rank #{current_rank})",
                                'to': f"{pref} (Rank #{i+1})",
                                'improvement': current_rank - (i + 1)
                            })
                            break
    
    return fixes

def apply_force_placement(schedule_data, troops):
    """Apply force placement for remaining critical preferences."""
    fixes = []
    
    # Build troop activities and preferences
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry)
    
    troop_preferences = {troop.name: troop.preferences for troop in troops}
    
    for troop in troops:
        troop_name = troop.name
        activities = [entry['activity'] for entry in troop_activities[troop_name]]
        preferences = troop_preferences[troop_name]
        
        # Check Top 5 preferences
        top5 = preferences[:5] if len(preferences) >= 5 else preferences
        
        for i, pref in enumerate(top5):
            if pref not in activities:
                rank = i + 1
                
                # Force place by removing a very low-preference activity
                low_pref_activities = [(a, preferences.index(a) + 1) for a in activities 
                                    if a in preferences and preferences.index(a) + 1 > 15]
                
                if low_pref_activities:
                    # Remove the lowest preference activity
                    remove_activity, remove_rank = max(low_pref_activities, key=lambda x: x[1])
                    
                    # Find and remove the low-preference entry
                    for entry in troop_activities[troop_name]:
                        if entry['activity'] == remove_activity:
                            schedule_data['entries'].remove(entry)
                            break
                    
                    # Add the high-preference activity
                    available_slots = find_available_slots(schedule_data, troop_name)
                    if available_slots:
                        slot = available_slots[0]
                        
                        new_entry = {
                            'troop': troop_name,
                            'activity': pref,
                            'day': slot['day'],
                            'slot': slot['slot']
                        }
                        schedule_data['entries'].append(new_entry)
                        
                        fixes.append({
                            'type': 'Force_Placement',
                            'troop': troop_name,
                            'placed': f"{pref} (Rank #{rank})",
                            'removed': f"{remove_activity} (Rank #{remove_rank})",
                            'improvement': remove_rank - rank
                        })
                        break
    
    return fixes

def find_available_slots(schedule_data, troop_name):
    """Find available slots for a troop."""
    occupied = set()
    for entry in schedule_data['entries']:
        if entry['troop'] == troop_name:
            slot_key = f"{entry['day']}-{entry['slot']}"
            occupied.add(slot_key)
    
    available = []
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
    for day in days:
        for slot in [1, 2, 3]:
            slot_key = f"{day}-{slot}"
            if slot_key not in occupied:
                available.append({'day': day, 'slot': slot})
    
    return available

def save_fixed_schedule(schedule_data, week_name):
    """Save the fixed schedule."""
    output_file = Path(f"schedules/{week_name}_top5_fixed_schedule.json")
    
    with open(output_file, 'w') as f:
        json.dump(schedule_data, f, indent=2)
    
    print(f"  Saved: {output_file}")

if __name__ == "__main__":
    results = apply_fixes_to_all_weeks()
