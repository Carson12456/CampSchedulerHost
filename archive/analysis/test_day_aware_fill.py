"""
Test day-aware fill optimization by monkey-patching the method
"""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from activities import get_activity_by_name

# Save original method
original_fill = ConstrainedScheduler._fill_all_remaining

def day_aware_fill(self):
    """Fill any empty slots with remaining preferences, using day-aware sorting."""
    for troop in self.troops:
        # Get free slots  
        free_slots = [s for s in self.time_slots if self.schedule.is_troop_free(s, troop)]
        
        # DAY-AWARE: Sort by activity count on each day (prefer busier days)
        free_slots.sort(
            key=lambda slot: sum(1 for e in self.schedule.entries 
                                if e.troop == troop and e.time_slot.day == slot.day),
            reverse=True
        )
        
        for slot in free_slots:
            if not self.schedule.is_troop_free(slot, troop):
                continue
            
            # Try troop preferences
            scheduled = False
            for pref_name in troop.preferences:
                activity = get_activity_by_name(pref_name)
                if not activity or self._troop_has_activity(troop, activity):
                    continue
                
                if self._can_schedule(troop, activity, slot, slot.day):
                    self.schedule.add_entry(slot, activity, troop)
                    self._update_progress(troop, activity.name)
                    scheduled = True
                    break
            
            # Default fill
            if not scheduled:
                for fill_name in self.DEFAULT_FILL_PRIORITY:
                    activity = get_activity_by_name(fill_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue
                    
                    if self._can_schedule(troop, activity, slot, slot.day, relax_constraints=True):
                        self.schedule.add_entry(slot, activity, troop)
                        print(f"  [DAY-AWARE Fill] {troop.name}: {fill_name} -> {slot}")
                        scheduled = True
                        break

# Monkey-patch the method
ConstrainedScheduler._fill_all_remaining = day_aware_fill

print("="*70)
print("DAY-AWARE FILL OPTIMIZATION TEST")
print("="*70)

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# Analyze days used per troop
print("\n" + "="*70)
print("DAYS USED PER TROOP ANALYSIS")
print("="*70)

from collections import defaultdict
for troop in troops:
    days_used = defaultdict(int)
    for entry in schedule.entries:
        if entry.troop.name == troop.name:
            days_used[entry.time_slot.day] += 1
    
    print(f"\n{troop.name}: {len(days_used)} days used")
    for day in sorted(days_used.keys(), key=lambda d: d.value):
        print(f"  {day.name}: {days_used[day]} activities")

# Calculate metrics
top5 = 0
top10 = 0
for troop in troops:
    entries = [e for e in schedule.entries if e.troop.name == troop.name]
    scheduled_names = {e.activity.name for e in entries}
    
    for pref in troop.preferences[:5]:
        if pref in scheduled_names:
            top5 += 1
    
    for pref in troop.preferences[:10]:
        if pref in scheduled_names:
            top10 += 1
    
total_troops = len(troops)
reflection_count = sum(1 for e in schedule.entries if e.activity.name == "Reflection")

print("\n" + "="*70)
print("METRICS")
print("="*70)
print(f"Reflections: {reflection_count}/{total_troops}")
print(f"Top 5: {top5}/{total_troops*5} ({top5/(total_troops*5)*100:.1f}%)")
print(f"Top 10: {top10}/{total_troops*10} ({top10/(total_troops*10)*100:.1f}%)")
