#!/usr/bin/env python3
"""
Advanced Top 5 fixes to resolve remaining problems.
Implements the highest-impact solutions from the analysis.
"""

import json
from pathlib import Path
from collections import defaultdict

def apply_advanced_top5_fixes():
    """
    Apply advanced fixes to resolve remaining Top 5 problems.
    """
    print("ADVANCED TOP 5 FIXES - RESOLVING REMAINING PROBLEMS")
    print("=" * 50)
    
    # Load the partially fixed schedule
    schedule_file = Path("schedules/tc_week4_beach_fixed_schedule.json")
    if not schedule_file.exists():
        print("Run targeted_beach_fix.py first!")
        return
    
    with open(schedule_file) as f:
        schedule_data = json.load(f)
    
    # Load troop data
    troops_file = Path("tc_week4_troops.json")
    with open(troops_file) as f:
        troops_data = json.load(f)['troops']
    
    fixes_applied = []
    
    # Fix 1: Resolve remaining Aqua Trampoline misses (Highest Priority)
    print("\n1. RESOLVING REMAINING AQUA TRAMPOLINE MISSES")
    at_fixes = resolve_remaining_at_misses(schedule_data, troops_data)
    fixes_applied.extend(at_fixes)
    print(f"   Applied {len(at_fixes)} AT fixes")
    
    # Fix 2: Smart Activity Swapping (High Impact)
    print("\n2. SMART ACTIVITY SWAPPING")
    swap_fixes = apply_smart_activity_swapping(schedule_data, troops_data)
    fixes_applied.extend(swap_fixes)
    print(f"   Applied {len(swap_fixes)} activity swaps")
    
    # Fix 3: Enhanced Force Placement (High Impact)
    print("\n3. ENHANCED FORCE PLACEMENT")
    force_fixes = apply_enhanced_force_placement(schedule_data, troops_data)
    fixes_applied.extend(force_fixes)
    print(f"   Applied {len(force_fixes)} force placements")
    
    # Fix 4: Constraint Violation Resolution (Medium Impact)
    print("\n4. CONSTRAINT VIOLATION RESOLUTION")
    constraint_fixes = resolve_constraint_violations(schedule_data)
    fixes_applied.extend(constraint_fixes)
    print(f"   Fixed {len(constraint_fixes)} constraint violations")
    
    # Save the fully fixed schedule
    output_file = Path("schedules/tc_week4_fully_fixed_schedule.json")
    with open(output_file, 'w') as f:
        json.dump(schedule_data, f, indent=2)
    
    print(f"\nFULLY FIXED SCHEDULE SAVED TO: {output_file}")
    
    # Final analysis
    print(f"\n" + "=" * 50)
    print("FINAL ANALYSIS")
    print("=" * 50)
    
    final_analysis = analyze_final_results(schedule_data, troops_data)
    print(f"Total fixes applied: {len(fixes_applied)}")
    print(f"Remaining AT misses: {final_analysis['remaining_at_misses']}")
    print(f"Top 5 satisfaction: {final_analysis['top5_satisfaction']:.1%}")
    print(f"Constraint violations: {final_analysis['violations']}")
    
    return fixes_applied, final_analysis

def resolve_remaining_at_misses(schedule_data, troops_data):
    """Resolve remaining Aqua Trampoline misses with aggressive fixes."""
    fixes = []
    
    # Find remaining AT misses
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry)
    
    for troop in troops_data:
        troop_name = troop['name']
        activities = [entry['activity'] for entry in troop_activities[troop_name]]
        
        # Check if AT is in Top 5 but not scheduled
        top5 = troop['preferences'][:5] if len(troop['preferences']) >= 5 else troop['preferences']
        
        if "Aqua Trampoline" in top5 and "Aqua Trampoline" not in activities:
            rank = top5.index("Aqua Trampoline") + 1
            
            # Aggressive fix: Find any available slot and place AT
            available_slots = find_available_slots_for_troop(troop_activities[troop_name])
            
            if available_slots:
                # Priority: Use any available slot for Rank #1 AT
                slot = available_slots[0]
                
                new_entry = {
                    'troop': troop_name,
                    'activity': 'Aqua Trampoline',
                    'day': slot['day'],
                    'slot': slot['slot']
                }
                schedule_data['entries'].append(new_entry)
                
                fixes.append({
                    'type': 'AT_Placement',
                    'troop': troop_name,
                    'action': f"Placed AT in {slot['day']}-{slot['slot']} (aggressive fix)",
                    'rank': rank
                })
    
    return fixes

def apply_smart_activity_swapping(schedule_data, troops_data):
    """Apply smart activity swapping to improve preference satisfaction."""
    fixes = []
    
    # Find low-preference activities that can be swapped
    troop_preferences = {troop['name']: troop['preferences'] for troop in troops_data}
    
    # Create activity lookup
    activity_lookup = defaultdict(list)
    for entry in schedule_data['entries']:
        activity_lookup[entry['activity']].append(entry)
    
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
                    # Try to find a high-preference activity that's not scheduled
                    for i, pref in enumerate(preferences[:5]):  # Top 5
                        if pref != activity and pref not in [e['activity'] for e in activity_lookup.get(troop, [])]:
                            # Check if this preference activity is available somewhere else
                            if pref in activity_lookup and len(activity_lookup[pref]) > 0:
                                # Found swap opportunity
                                swap_entry = activity_lookup[pref][0]
                                
                                # Perform the swap
                                entry['activity'] = pref
                                swap_entry['activity'] = activity
                                
                                fixes.append({
                                    'type': 'Smart_Swap',
                                    'troop': troop,
                                    'action': f"Swapped {activity} (Rank #{current_rank}) for {pref} (Rank #{i+1})",
                                    'improvement': current_rank - (i + 1)
                                })
                                break
    
    return fixes

def apply_enhanced_force_placement(schedule_data, troops_data):
    """Apply enhanced force placement for remaining critical preferences."""
    fixes = []
    
    troop_preferences = {troop['name']: troop['preferences'] for troop in troops_data}
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry)
    
    for troop in troops_data:
        troop_name = troop['name']
        activities = [entry['activity'] for entry in troop_activities[troop_name]]
        preferences = troop_preferences[troop_name]
        
        # Check Top 5 preferences
        top5 = preferences[:5] if len(preferences) >= 5 else preferences
        
        for i, pref in enumerate(top5):
            if pref not in activities:
                rank = i + 1
                
                # Force place by removing a low-preference activity
                low_pref_activities = [(a, preferences.index(a) + 1) for a in activities if a in preferences and preferences.index(a) + 1 > 15]
                
                if low_pref_activities:
                    # Remove the lowest preference activity
                    remove_activity, remove_rank = max(low_pref_activities, key=lambda x: x[1])
                    
                    # Find and remove the low-preference entry
                    for entry in troop_activities[troop_name]:
                        if entry['activity'] == remove_activity:
                            schedule_data['entries'].remove(entry)
                            break
                    
                    # Add the high-preference activity
                    available_slots = find_available_slots_for_troop(troop_activities[troop_name])
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
                            'action': f"Force placed {pref} (Rank #{rank}), removed {remove_activity} (Rank #{remove_rank})",
                            'improvement': remove_rank - rank
                        })
                        break
    
    return fixes

def resolve_constraint_violations(schedule_data):
    """Resolve constraint violations in the schedule."""
    fixes = []
    
    # Fix beach slot violations by moving activities to valid slots
    beach_activities = {"Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
                       "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
                       "Nature Canoe", "Float for Floats"}
    
    # Find beach slot violations
    violations = []
    for entry in schedule_data['entries']:
        if (entry['activity'] in beach_activities and 
            entry['slot'] == 2 and 
            entry['day'] != 'THURSDAY'):
            violations.append(entry)
    
    # Try to fix violations by moving to slot 1 or 3
    for violation in violations:
        # Try slot 1 first
        new_slot = 1
        if not is_slot_occupied(schedule_data, violation['troop'], violation['day'], new_slot):
            violation['slot'] = new_slot
            fixes.append({
                'type': 'Constraint_Fix',
                'troop': violation['troop'],
                'action': f"Moved {violation['activity']} from slot 2 to slot {new_slot} on {violation['day']}"
            })
        else:
            # Try slot 3
            new_slot = 3
            if not is_slot_occupied(schedule_data, violation['troop'], violation['day'], new_slot):
                violation['slot'] = new_slot
                fixes.append({
                    'type': 'Constraint_Fix',
                    'troop': violation['troop'],
                    'action': f"Moved {violation['activity']} from slot 2 to slot {new_slot} on {violation['day']}"
                })
    
    return fixes

def find_available_slots_for_troop(troop_entries):
    """Find available slots for a specific troop."""
    occupied = set()
    for entry in troop_entries:
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

def is_slot_occupied(schedule_data, troop, day, slot):
    """Check if a slot is occupied by a specific troop."""
    for entry in schedule_data['entries']:
        if entry['troop'] == troop and entry['day'] == day and entry['slot'] == slot:
            return True
    return False

def analyze_final_results(schedule_data, troops_data):
    """Analyze the final results after all fixes."""
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry['activity'])
    
    # Count remaining AT misses
    remaining_at_misses = 0
    total_top5 = 0
    satisfied_top5 = 0
    
    for troop in troops_data:
        troop_name = troop['name']
        activities = troop_activities[troop_name]
        top5 = troop['preferences'][:5] if len(troop['preferences']) >= 5 else troop['preferences']
        
        for pref in top5:
            total_top5 += 1
            if pref in activities:
                satisfied_top5 += 1
            elif pref == "Aqua Trampoline":
                remaining_at_misses += 1
    
    # Count constraint violations
    violations = 0
    beach_activities = {"Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
                       "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
                       "Nature Canoe", "Float for Floats"}
    
    for entry in schedule_data['entries']:
        if (entry['activity'] in beach_activities and 
            entry['slot'] == 2 and 
            entry['day'] != 'THURSDAY'):
            violations += 1
    
    return {
        'remaining_at_misses': remaining_at_misses,
        'top5_satisfaction': satisfied_top5 / total_top5 if total_top5 > 0 else 0,
        'violations': violations
    }

if __name__ == "__main__":
    fixes, analysis = apply_advanced_top5_fixes()
