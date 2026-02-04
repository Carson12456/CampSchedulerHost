#!/usr/bin/env python3
"""
Constraint Analysis Script
Analyzes schedules for weeks 1, 3 (Voy), and 7 to verify constraint compliance.
"""
import json
from pathlib import Path
from collections import defaultdict

def analyze_schedule(week_name, schedule_path, is_voyageur=False):
    """Analyze a single week's schedule for constraint violations."""
    print(f"\n{'='*60}")
    print(f"ANALYZING {week_name}")
    print(f"{'='*60}")
    
    with open(schedule_path) as f:
        data = json.load(f)
    
    troops = {t['name']: t for t in data['troops']}
    entries = data['entries']
    
    # Track violations
    violations = []
    stats = {
        'total_activities': len(entries),
        'top1_grey_needed': 0,
        'showerhouse_monday': 0,
        'shotgun_large_troops': 0,
        'reflection_splits': defaultdict(set),
        'rifle_days': defaultdict(list),
        'shotgun_days': defaultdict(list)
    }
    
    # Analyze each entry
    for entry in entries:
        troop_name = entry['troop_name']
        activity = entry['activity_name']
        day = entry['day']
        slot = entry['slot']
        
        troop = troops[troop_name]
        
        # Check #1: Showerhouse on Monday
        if activity == "Reserve Shower House" and day == "MONDAY":
            violations.append(f"[X] {troop_name}: Showerhouse on Monday")
            stats['showerhouse_monday'] += 1
        
        # Check #2: Shotgun for large troops
        if activity == "Troop Shotgun":
            troop_size = troop['scouts'] + troop['adults']
            if troop_size > 15:
                violations.append(f"[X] {troop_name}: Shotgun with {troop_size} people (>15)")
                stats['shotgun_large_troops'] += 1
        
        # Check #3: Top 1 activities (for UI grey verification)
        if activity in troop['preferences'][:1]:  # Top 1
            stats['top1_grey_needed'] += 1
        
        # Check #4: Reflection for split troops
        if activity == "Reflection":
            base_name = troop_name
            if troop_name.endswith('-A') or troop_name.endswith('-B'):
                base_name = troop_name[:-2]
            stats['reflection_splits'][base_name].add((day, slot))
        
        # Check #5: Range clustering
        if activity == "Troop Rifle":
            stats['rifle_days'][day].append((troop_name, slot))
        if activity == "Troop Shotgun":
            stats['shotgun_days'][day].append((troop_name, slot))
    
    # Check for split troop reflection violations
    for base_name, slots in stats['reflection_splits'].items():
        if len(slots) > 1:
            violations.append(f"[X] Split troop {base_name}: Reflection in multiple slots {slots}")
    
    # Print results
    print(f"\n[STATISTICS]")
    print(f"  Total Activities: {stats['total_activities']}")
    print(f"  Top 1 Activities (need grey UI): {stats['top1_grey_needed']}")
    
    print(f"\n[CONSTRAINT CHECKS]")
    print(f"  OK Showerhouse Monday violations: {stats['showerhouse_monday']}")
    print(f"  OK Shotgun large troop violations: {stats['shotgun_large_troops']}")
    
    if stats['reflection_splits']:
        print(f"  OK Split troop Reflection sync: {len([s for s in stats['reflection_splits'].values() if len(s) == 1])}/{len(stats['reflection_splits'])} correct")
    
    # Range clustering analysis
    print(f"\n[RANGE CLUSTERING]")
    all_range_days = set(list(stats['rifle_days'].keys()) + list(stats['shotgun_days'].keys()))
    for day in sorted(all_range_days):
        rifles = stats['rifle_days'].get(day, [])
        shotguns = stats['shotgun_days'].get(day, [])
        print(f"  {day}: {len(rifles)} Rifles, {len(shotguns)} Shotguns")
        
        # Check if they're consecutive (all rifles before shotguns)
        if rifles and shotguns:
            rifle_slots = sorted([s for _, s in rifles])
            shotgun_slots = sorted([s for _, s in shotguns])
            if rifle_slots and shotgun_slots:
                if max(rifle_slots) < min(shotgun_slots):
                    print(f"     OK Rifles then Shotguns (consecutive)")
                else:
                    print(f"     INFO Mixed Rifle/Shotgun scheduling")
    
    if violations:
        print(f"\n[!] VIOLATIONS FOUND ({len(violations)})")
        for v in violations[:10]:  # Limit to first 10
            print(f"  {v}")
    else:
        print(f"\n[OK] NO VIOLATIONS FOUND!")
    
    return len(violations)

def main():
    """Analyze all key weeks."""
    weeks = [
        ("TC Week 1", "schedules/tc_week1_troops_schedule.json", False),
        ("Voyageur Week 3", "schedules/voyageur_week3_troops_schedule.json", True),
        ("TC Week 7", "schedules/tc_week7_troops_schedule.json", False)
    ]
    
    total_violations = 0
    for week_name, path, is_voy in weeks:
        schedule_path = Path(path)
        if schedule_path.exists():
            violations = analyze_schedule(week_name, schedule_path, is_voy)
            total_violations += violations
        else:
            print(f"\n[!] {week_name}: Schedule file not found at {path}")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {total_violations} total violations across all weeks")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
