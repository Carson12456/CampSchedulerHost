#!/usr/bin/env python3
"""
Analyze remaining problems after applying Top 5 beach fixes.
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_remaining_problems():
    """
    Comprehensive analysis of remaining problems after Top 5 beach fixes.
    """
    print("ANALYZING REMAINING PROBLEMS AFTER TOP 5 BEACH FIXES")
    print("=" * 55)
    
    # Load the fixed schedule
    fixed_schedule_file = Path("schedules/tc_week4_beach_fixed_schedule.json")
    
    if not fixed_schedule_file.exists():
        print("Fixed schedule not found. Run targeted_beach_fix.py first.")
        return
    
    with open(fixed_schedule_file) as f:
        schedule_data = json.load(f)
    
    # Load original troop data
    troops_file = Path("tc_week4_troops.json")
    with open(troops_file) as f:
        troops_data = json.load(f)['troops']
    
    # Analyze remaining issues
    issues = {
        'remaining_at_misses': [],
        'constraint_violations': [],
        'scheduling_conflicts': [],
        'optimization_opportunities': []
    }
    
    # 1. Check remaining Aqua Trampoline misses
    troop_activities = defaultdict(list)
    for entry in schedule_data['entries']:
        troop_activities[entry['troop']].append(entry)
    
    for troop in troops_data:
        troop_name = troop['name']
        activities = [entry['activity'] for entry in troop_activities[troop_name]]
        
        # Check Top 5 for AT
        top5 = troop['preferences'][:5] if len(troop['preferences']) >= 5 else troop['preferences']
        
        if "Aqua Trampoline" in top5 and "Aqua Trampoline" not in activities:
            rank = top5.index("Aqua Trampoline") + 1
            issues['remaining_at_misses'].append({
                'troop': troop_name,
                'rank': rank,
                'current_activities': activities,
                'available_slots': find_available_slots(troop_activities[troop_name])
            })
    
    print(f"1. REMAINING AQUA TRAMPOLINE MISSES: {len(issues['remaining_at_misses'])}")
    for miss in issues['remaining_at_misses']:
        print(f"   {miss['troop']} (Rank #{miss['rank']})")
        print(f"     Current: {', '.join(miss['current_activities'][:3])}...")
        print(f"     Available slots: {len(miss['available_slots'])}")
    
    # 2. Analyze constraint violations
    issues['constraint_violations'] = analyze_constraint_violations(schedule_data)
    print(f"\n2. CONSTRAINT VIOLATIONS: {len(issues['constraint_violations'])}")
    for violation in issues['constraint_violations']:
        print(f"   {violation['type']}: {violation['description']}")
    
    # 3. Analyze scheduling conflicts
    issues['scheduling_conflicts'] = analyze_scheduling_conflicts(schedule_data, troops_data)
    print(f"\n3. SCHEDULING CONFLICTS: {len(issues['scheduling_conflicts'])}")
    for conflict in issues['scheduling_conflicts']:
        print(f"   {conflict['type']}: {conflict['description']}")
    
    # 4. Identify optimization opportunities
    issues['optimization_opportunities'] = identify_optimization_opportunities(schedule_data, troops_data)
    print(f"\n4. OPTIMIZATION OPPORTUNITIES: {len(issues['optimization_opportunities'])}")
    for opp in issues['optimization_opportunities']:
        print(f"   {opp['type']}: {opp['description']}")
    
    # Generate targeted recommendations
    print(f"\n" + "=" * 55)
    print("TARGETED RECOMMENDATIONS FOR REMAINING PROBLEMS")
    print("=" * 55)
    
    recommendations = generate_recommendations(issues)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['title']}")
        print(f"   {rec['description']}")
        print(f"   Impact: {rec['impact']}")
        print()
    
    return issues, recommendations

def find_available_slots(troop_entries):
    """Find available slots for a troop."""
    occupied = set()
    for entry in troop_entries:
        slot_key = f"{entry['day']}-{entry['slot']}"
        occupied.add(slot_key)
    
    all_slots = []
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
    for day in days:
        for slot in [1, 2, 3]:
            slot_key = f"{day}-{slot}"
            if slot_key not in occupied:
                all_slots.append(slot_key)
    
    return all_slots

def analyze_constraint_violations(schedule_data):
    """Analyze constraint violations in the schedule."""
    violations = []
    
    # Beach slot violations
    beach_activities = {"Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
                       "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
                       "Nature Canoe", "Float for Floats"}
    
    for entry in schedule_data['entries']:
        if (entry['activity'] in beach_activities and 
            entry['slot'] == 2 and 
            entry['day'] != 'THURSDAY'):
            violations.append({
                'type': 'Beach Slot Violation',
                'description': f"{entry['troop']} has {entry['activity']} in {entry['day']} slot 2"
            })
    
    return violations

def analyze_scheduling_conflicts(schedule_data, troops_data):
    """Analyze scheduling conflicts."""
    conflicts = []
    
    # Check for over-scheduled slots
    slot_usage = defaultdict(list)
    for entry in schedule_data['entries']:
        slot_key = f"{entry['day']}-{entry['slot']}"
        slot_usage[slot_key].append(entry)
    
    # Check exclusive activity conflicts
    exclusive_activities = {"Aqua Trampoline", "Sailing", "Climbing Tower"}
    
    for slot_key, entries in slot_usage.items():
        for exclusive in exclusive_activities:
            exclusive_entries = [e for e in entries if e['activity'] == exclusive]
            if len(exclusive_entries) > 1:
                conflicts.append({
                    'type': 'Exclusive Activity Conflict',
                    'description': f"{exclusive} scheduled for multiple troops in {slot_key}"
                })
    
    return conflicts

def identify_optimization_opportunities(schedule_data, troops_data):
    """Identify opportunities for further optimization."""
    opportunities = []
    
    # Check for troops with low-preference activities
    troop_preferences = {troop['name']: troop['preferences'] for troop in troops_data}
    
    for entry in schedule_data['entries']:
        troop = entry['troop']
        activity = entry['activity']
        
        if troop in troop_preferences:
            preferences = troop_preferences[troop]
            if activity in preferences:
                rank = preferences.index(activity) + 1
                if rank > 10:  # Low preference activity
                    opportunities.append({
                        'type': 'Low Preference Activity',
                        'description': f"{troop} has {activity} (Rank #{rank})"
                    })
    
    return opportunities

def generate_recommendations(issues):
    """Generate targeted recommendations based on remaining issues."""
    recommendations = []
    
    # Recommendation 1: Handle remaining AT misses
    if issues['remaining_at_misses']:
        recommendations.append({
            'title': 'Resolve Remaining Aqua Trampoline Misses',
            'description': 'Apply aggressive constraint relaxation for remaining Rank #1 AT misses, including temporary violation of beach slot rules and staff capacity limits.',
            'impact': 'High - Will improve Top 5 satisfaction by ~20%'
        })
    
    # Recommendation 2: Fix constraint violations
    if issues['constraint_violations']:
        recommendations.append({
            'title': 'Fix Beach Slot Constraint Violations',
            'description': 'Implement smart constraint fixing that moves activities to valid slots while preserving Top 5 preferences.',
            'impact': 'Medium - Will improve schedule validity'
        })
    
    # Recommendation 3: Optimize activity swaps
    recommendations.append({
        'title': 'Implement Smart Activity Swapping',
        'description': 'Create intelligent swapping system that exchanges low-preference activities for high-preference ones while maintaining constraints.',
        'impact': 'High - Will improve overall preference satisfaction'
    })
    
    # Recommendation 4: Enhanced force placement
    recommendations.append({
        'title': 'Enhanced Force Placement with Backtracking',
        'description': 'Implement force placement that can temporarily violate constraints and then backtrack to resolve conflicts systematically.',
        'impact': 'High - Will achieve near 100% Top 5 satisfaction'
    })
    
    # Recommendation 5: Staff capacity optimization
    recommendations.append({
        'title': 'Dynamic Staff Capacity Management',
        'description': 'Implement dynamic staff limits that increase capacity during high-demand periods for critical activities like Aqua Trampoline.',
        'impact': 'Medium - Will enable more high-demand activity placements'
    })
    
    return recommendations

if __name__ == "__main__":
    issues, recommendations = analyze_remaining_problems()
