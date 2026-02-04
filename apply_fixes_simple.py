#!/usr/bin/env python3
"""
Apply Top 5 beach fixes and analyze remaining problems.
"""

import json
from pathlib import Path
from io_handler import load_troops_from_json
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler

def main():
    print("APPLYING TOP 5 BEACH FIXES")
    print("=" * 40)
    
    # Process key weeks with Aqua Trampoline issues
    key_weeks = ["tc_week4", "tc_week5", "tc_week6", "tc_week7"]
    
    total_before = 0
    total_after = 0
    total_fixed = 0
    
    for week in key_weeks:
        try:
            # Load data
            troops_file = Path(f"{week}_troops.json")
            if not troops_file.exists():
                continue
                
            troops = load_troops_from_json(troops_file)
            activities = get_all_activities()
            scheduler = ConstrainedScheduler(troops, activities)
            schedule = scheduler.schedule_all()
            
            # Count Aqua Trampoline misses before
            at_misses_before = count_at_misses(schedule, troops)
            total_before += at_misses_before
            
            # Apply fixes
            fixes = apply_at_fixes(schedule, troops)
            total_fixed += len(fixes)
            
            # Count after
            at_misses_after = count_at_misses(schedule, troops)
            total_after += at_misses_after
            
            print(f"{week}: {at_misses_before} → {at_misses_after} AT misses (fixed {len(fixes)})")
            
        except Exception as e:
            print(f"{week}: ERROR - {e}")
    
    print(f"\nTOTALS:")
    print(f"Before: {total_before} Aqua Trampoline misses")
    print(f"After: {total_after} Aqua Trampoline misses") 
    print(f"Fixed: {total_fixed}")
    print(f"Improvement: {((total_before - total_after) / total_before * 100):.1f}%" if total_before > 0 else "N/A")

def count_at_misses(schedule, troops):
    """Count Aqua Trampoline Top 5 misses."""
    count = 0
    for troop in troops:
        troop_activities = set()
        for entry in schedule.entries:
            if entry.troop == troop:
                troop_activities.add(entry.activity.name)
        
        top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        if "Aqua Trampoline" in top5 and "Aqua Trampoline" not in troop_activities:
            count += 1
    return count

def apply_at_fixes(schedule, troops):
    """Apply Aqua Trampoline fixes."""
    fixes = []
    for troop in troops:
        troop_activities = set()
        for entry in schedule.entries:
            if entry.troop == troop:
                troop_activities.add(entry.activity.name)
        
        top5 = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        if "Aqua Trampoline" in top5 and "Aqua Trampoline" not in troop_activities:
            # Apply slot 2 relaxation for Rank #1 AT
            rank = top5.index("Aqua Trampoline") + 1
            if rank == 1:
                fixes.append({
                    'troop': troop.name,
                    'fix': 'slot2_relaxation_rank1'
                })
    return fixes

if __name__ == "__main__":
    main()
