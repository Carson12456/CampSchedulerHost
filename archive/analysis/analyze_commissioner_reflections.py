"""
Analyze Reflection slot distribution by commissioner
to see if commissioners can attend all their troops' Reflections
"""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler

# Test Week 7
troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

print("="*70)
print("REFLECTION SLOT DISTRIBUTION BY COMMISSIONER")
print("="*70)

# Group Reflection entries by commissioner
from collections import defaultdict
commissioner_reflections = defaultdict(list)

for entry in schedule.entries:
    if entry.activity.name == "Reflection":
        troop_name = entry.troop.name
        commissioner = scheduler.troop_commissioner.get(troop_name, "Unknown")
        slot_num = entry.time_slot.slot_number
        commissioner_reflections[commissioner].append((troop_name, slot_num))

# Analyze each commissioner
for commissioner in sorted(commissioner_reflections.keys()):
    reflections = commissioner_reflections[commissioner]
    slots_used = set(slot for _, slot in reflections)
    
    print(f"\n{commissioner}:")
    print(f"  Troops: {len(reflections)}")
    print(f"  Slots used: {sorted(slots_used)}")
    
    # Group by slot
    by_slot = defaultdict(list)
    for troop, slot in reflections:
        by_slot[slot].append(troop)
    
    for slot in sorted(by_slot.keys()):
        troops_in_slot = by_slot[slot]
        print(f"    Slot {slot}: {', '.join(troops_in_slot)}")
    
    # Can commissioner attend all Reflections?
    if len(slots_used) == 1:
        print(f"  OK: All in same slot - commissioner can attend all")
    else:
        print(f"  WARNING: Spread across {len(slots_used)} slots - commissioner CANNOT attend all")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

commissioners_can_attend_all = sum(1 for c, refs in commissioner_reflections.items() 
                                   if len(set(slot for _, slot in refs)) == 1)
total_commissioners = len(commissioner_reflections)

print(f"Commissioners who can attend ALL Reflections: {commissioners_can_attend_all}/{total_commissioners}")
print(f"\nThis is a PROBLEM if commissioners need to attend all their troops' Reflections!")
