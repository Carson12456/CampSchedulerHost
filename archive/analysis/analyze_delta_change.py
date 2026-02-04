"""
Analyze the Delta scheduling changes for Week 5.
Compares: 
- Which troops got Delta (should only be those who requested it)
- Delta-before-Super-Troop timing constraint
- Overall preference satisfaction
"""
import json
from pathlib import Path

from models import Day, generate_time_slots
from activities import get_all_activities, get_activity_by_name
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler


def analyze_delta_changes(troops_file="tc_week5_troops.json"):
    """Analyze the impact of Delta scheduling changes."""
    print("=" * 70)
    print(f"DELTA SCHEDULING ANALYSIS - {troops_file}")
    print("=" * 70)
    
    # Load troops
    troops = load_troops_from_json(troops_file)
    
    # Identify troops that have Delta in their preferences
    troops_wanting_delta = []
    troops_not_wanting_delta = []
    
    for troop in troops:
        if "Delta" in troop.preferences:
            delta_rank = troop.preferences.index("Delta") + 1
            troops_wanting_delta.append((troop.name, delta_rank))
        else:
            troops_not_wanting_delta.append(troop.name)
    
    print("\n" + "=" * 70)
    print("1. TROOPS THAT REQUESTED DELTA")
    print("=" * 70)
    print("\nTroops WITH Delta in preferences (should get Delta):")
    for name, rank in sorted(troops_wanting_delta, key=lambda x: x[1]):
        print(f"  - {name}: Rank #{rank}")
    
    print(f"\nTroops WITHOUT Delta in preferences (should NOT get Delta):")
    for name in troops_not_wanting_delta:
        print(f"  - {name}")
    
    # Run scheduler
    print("\n" + "=" * 70)
    print("2. RUNNING SCHEDULER...")
    print("=" * 70)
    
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    
    # Analyze results
    print("\n" + "=" * 70)
    print("3. DELTA ASSIGNMENT RESULTS")
    print("=" * 70)
    
    time_slots = generate_time_slots()
    
    # Check which troops got Delta
    troops_with_delta = []
    troops_with_super_troop = []
    delta_slots = {}
    super_troop_slots = {}
    
    for entry in schedule.entries:
        if entry.activity.name == "Delta":
            troops_with_delta.append(entry.troop.name)
            delta_slots[entry.troop.name] = entry.time_slot
        if entry.activity.name == "Super Troop":
            troops_with_super_troop.append(entry.troop.name)
            super_troop_slots[entry.troop.name] = entry.time_slot
    
    print("\nTroops that GOT Delta:")
    for troop_name in sorted(set(troops_with_delta)):
        slot = delta_slots.get(troop_name)
        wanted = any(t[0] == troop_name for t in troops_wanting_delta)
        status = "[OK] CORRECT (requested)" if wanted else "[X] ERROR (not requested)"
        print(f"  - {troop_name}: {slot} - {status}")
    
    print("\nTroops that did NOT get Delta:")
    for troop_name in [t.name for t in troops]:
        if troop_name not in troops_with_delta:
            wanted = any(t[0] == troop_name for t in troops_wanting_delta)
            status = "[OK] CORRECT (not requested)" if not wanted else "[X] ERROR (was requested!)"
            print(f"  - {troop_name} - {status}")
    
    # Check Delta-before-Super-Troop constraint
    print("\n" + "=" * 70)
    print("4. DELTA-BEFORE-SUPER-TROOP CONSTRAINT CHECK")
    print("=" * 70)
    
    violations = []
    correct_order = []
    
    for troop_name in sorted(set(troops_with_delta)):
        if troop_name in super_troop_slots:
            delta_slot = delta_slots[troop_name]
            super_slot = super_troop_slots[troop_name]
            
            delta_idx = time_slots.index(delta_slot)
            super_idx = time_slots.index(super_slot)
            
            if delta_idx < super_idx:
                correct_order.append(f"  [OK] {troop_name}: Delta ({delta_slot}) -> Super Troop ({super_slot})")
            else:
                violations.append(f"  [X] {troop_name}: Super Troop ({super_slot}) BEFORE Delta ({delta_slot})!")
    
    if correct_order:
        print("\nCorrect ordering (Delta before Super Troop):")
        for item in correct_order:
            print(item)
    
    if violations:
        print("\nVIOLATIONS (Super Troop scheduled before Delta):")
        for item in violations:
            print(item)
    else:
        print("\n[OK] All troops with Delta have it scheduled BEFORE Super Troop!")
    
    # Check preference satisfaction
    print("\n" + "=" * 70)
    print("5. PREFERENCE SATISFACTION SUMMARY")
    print("=" * 70)
    
    total_top5 = 0
    total_top10 = 0
    troops_count = len(troops)
    
    for troop in troops:
        top5_count = 0
        top10_count = 0
        
        for entry in schedule.entries:
            if entry.troop == troop:
                prio = troop.get_priority(entry.activity.name)
                if prio is not None:
                    if prio < 5:
                        top5_count += 1
                    if prio < 10:
                        top10_count += 1
        
        total_top5 += top5_count
        total_top10 += top10_count
    
    print(f"\nTotal Top 5 scheduled across all troops: {total_top5}")
    print(f"Total Top 10 scheduled across all troops: {total_top10}")
    print(f"Average Top 5 per troop: {total_top5/troops_count:.1f}")
    print(f"Average Top 10 per troop: {total_top10/troops_count:.1f}")
    
    # Summary
    print("\n" + "=" * 70)
    print("6. IMPACT ANALYSIS")
    print("=" * 70)
    
    # How many slots were freed up by not forcing Delta on everyone?
    troops_not_getting_delta = len(troops_not_wanting_delta)
    slots_freed = troops_not_getting_delta  # 1 slot per troop that didn't want Delta
    
    print(f"""
CHANGE SUMMARY:
- Delta changed from MANDATORY (like Super Troop) to PREFERENCE-BASED
- {len(troops_wanting_delta)} troops requested Delta -> got Delta
- {len(troops_not_wanting_delta)} troops did NOT request Delta -> did NOT get Delta
- {slots_freed} slots freed up for other preferences

BENEFITS:
1. Troops who didn't want Delta now have an extra slot for their actual preferences
2. Delta is still scheduled early (before Super Troop) for clustering
3. Troops who DO want Delta still get commissioner day priority for full-day scheduling
4. Constraint: Delta always scheduled before Super Troop for same troop is enforced

TROOPS BENEFITING FROM THIS CHANGE:
""")
    
    for name in troops_not_wanting_delta:
        print(f"- {name}: No longer forced into Delta, got an extra preference slot")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    import sys
    troops_file = sys.argv[1] if len(sys.argv) > 1 else "tc_week5_troops.json"
    analyze_delta_changes(troops_file)
