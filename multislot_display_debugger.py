#!/usr/bin/env python3
"""
Multi-Slot Activity Display Debugger
Specifically tracks multi-slot activities and their display in the web interface.
"""

import json
from pathlib import Path
from collections import defaultdict
from models import Day, TimeSlot, generate_time_slots, ScheduleEntry, Troop, Schedule
from activities import get_all_activities
from io_handler import load_troops_from_json, load_schedule_from_json

class MultiSlotDisplayDebugger:
    def __init__(self):
        self.activities = get_all_activities()
        self.time_slots = generate_time_slots()
        
    def debug_multislot_display(self, week_file):
        """Debug multi-slot activity display issues."""
        print(f"\n=== DEBUGGING MULTI-SLOT DISPLAY FOR {week_file} ===")
        
        # Load schedule
        troops = load_troops_from_json(week_file)
        week_basename = Path(week_file).stem
        schedule_file = f"schedules/{week_basename}_schedule.json"
        
        with open(schedule_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct schedule
        schedule = Schedule()
        troop_map = {t['name']: Troop(t['name'], t['scouts'], t['adults'], 
                          t.get('campsite', t['name']), t.get('commissioner'),
                          t.get('preferences', []), t.get('day_requests', {})) 
                     for t in data['troops']}
        
        # Create activity map
        activity_map = {}
        for act in self.activities:
            activity_map[act.name] = act
        
        # Add missing activities as generic ones if needed
        for entry_data in data['entries']:
            activity_name = entry_data['activity_name']
            if activity_name not in activity_map:
                from models import Activity
                activity_map[activity_name] = Activity(activity_name, 1.0, "Unknown", 1, False)
        
        # Create slot map
        slot_map = {}
        for ts in self.time_slots:
            slot_map[(ts.day.name, ts.slot_number)] = ts
        
        for entry_data in data['entries']:
            troop = troop_map[entry_data['troop_name']]
            activity = activity_map[entry_data['activity_name']]
            time_slot = slot_map[(entry_data['day'], entry_data['slot'])]
            if troop and activity and time_slot:
                schedule.entries.append(ScheduleEntry(time_slot, activity, troop))
        
        # Debug each troop's multi-slot activities
        for troop in troops:
            self._debug_troop_multislot(troop, schedule)
    
    def _debug_troop_multislot(self, troop, schedule):
        """Debug multi-slot activities for a specific troop."""
        print(f"\n--- DEBUGGING {troop.name} MULTI-SLOT ACTIVITIES ---")
        
        # Get all entries for this troop
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        
        # Group by activity to find multi-slot ones
        activity_groups = defaultdict(list)
        for entry in troop_entries:
            activity_groups[entry.activity.name].append(entry)
        
        # Check each activity for multi-slot issues
        for activity_name, entries in activity_groups.items():
            activity = entries[0].activity
            
            if activity.slots > 1.0:  # Multi-slot activity
                print(f"\n[Multi-Slot] {activity_name} ({activity.slots} slots):")
                
                # Sort entries by time
                entries.sort(key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number))
                
                for entry in entries:
                    day = entry.time_slot.day.name
                    slot = entry.time_slot.slot_number
                    print(f"  {day}-{slot}: {activity_name}")
                    
                    # Check if this should be marked as continuation
                    is_continuation = self._is_continuation_entry(entry, entries)
                    print(f"    Should be continuation: {is_continuation}")
                    
                    # Check what the GUI would display
                    gui_data = self._simulate_gui_data(entry, entries)
                    print(f"    GUI would show: is_continuation={gui_data.get('is_continuation', False)}")
                    
                    # Check if continuation slots are properly filled
                    if activity.slots >= 1.5 and slot < 3:  # Could have continuation
                        next_slot = slot + (1 if activity.slots >= 1.5 else 1)
                        if next_slot <= 3:
                            has_continuation = any(
                                e.time_slot.day == entry.time_slot.day and 
                                e.time_slot.slot_number == next_slot and
                                e.activity.name == activity_name
                                for e in entries
                            )
                            print(f"    Has continuation in {day}-{next_slot}: {has_continuation}")
                            if not has_continuation:
                                print(f"    [ERROR] Missing continuation for {activity.name}!")
    
    def _is_continuation_entry(self, entry, all_entries):
        """Determine if this entry should be marked as a continuation."""
        # Check if there's an earlier entry for the same activity on the same day
        for other_entry in all_entries:
            if (other_entry.activity.name == entry.activity.name and 
                other_entry.time_slot.day == entry.time_slot.day and
                other_entry.time_slot.slot_number < entry.time_slot.slot_number):
                return True
        return False
    
    def _simulate_gui_data(self, entry, all_entries):
        """Simulate what the GUI would return for this entry."""
        # Simulate the GUI logic from gui_web.py
        is_continuation = False
        for other_entry in all_entries:
            if (other_entry.activity.name == entry.activity.name and 
                other_entry.time_slot.day == entry.time_slot.day and
                other_entry.time_slot.slot_number < entry.time_slot.slot_number):
                is_continuation = True
                break
        
        return {
            'activity': entry.activity.name,
            'is_continuation': is_continuation,
            'slots': entry.activity.slots
        }
    
    def debug_scheduling_decisions(self, week_file):
        """Debug scheduling decisions for high-priority activities."""
        print(f"\n=== DEBUGGING SCHEDULING DECISIONS FOR {week_file} ===")
        
        # Load troops and check their preferences
        troops = load_troops_from_json(week_file)
        
        for troop in troops:
            print(f"\n--- SCHEDULING DECISIONS FOR {troop.name} ---")
            
            # Show Top 10 preferences
            print(f"Top 10 preferences: {troop.preferences[:10]}")
            
            # Check actual schedule
            week_basename = Path(week_file).stem
            schedule_file = f"schedules/{week_basename}_schedule.json"
            
            with open(schedule_file, 'r') as f:
                data = json.load(f)
            
            # Find this troop's scheduled activities
            troop_scheduled = []
            for entry_data in data['entries']:
                if entry_data['troop_name'] == troop.name:
                    troop_scheduled.append(entry_data)
            
            # Sort by priority
            def get_priority(activity_name):
                try:
                    return troop.preferences.index(activity_name)
                except ValueError:
                    return 999
            
            troop_scheduled.sort(key=lambda x: get_priority(x['activity_name']))
            
            print("Scheduled activities (by priority):")
            for entry in troop_scheduled[:10]:  # Top 10
                priority = get_priority(entry['activity_name'])
                day = entry['day']
                slot = entry['slot']
                activity = entry['activity_name']
                priority_marker = f"#{priority+1}" if priority < 999 else "N/A"
                print(f"  {priority_marker:>3} {activity} ({day}-{slot})")
                
                # Check if this looks like a questionable placement
                if priority < 10:  # Top 10
                    self._analyze_placement_question(troop, activity, day, slot, priority)
    
    def _analyze_placement_question(self, troop, activity, day, slot, priority):
        """Analyze if this placement looks questionable."""
        # Check for obvious issues
        issues = []
        
        # Issue 1: High priority activities on Friday (usually suboptimal)
        if day == 'FRIDAY' and priority < 5:
            issues.append(f"Top {priority+1} '{activity}' on FRIDAY-{slot} (usually suboptimal)")
        
        # Issue 2: Activities that should be clustered but aren't
        if activity in ['Tie Dye', 'Troop Rifle', 'Troop Shotgun'] and priority < 10:
            issues.append(f"High priority '{activity}' should be clustered")
        
        # Issue 3: Check if this activity has specific slot preferences
        slot_preferences = {
            'Shower House': 3,  # Prefers slot 3
            'Trading Post': None,  # No strong preference
            'Reflection': None,  # Friday only
        }
        
        if activity in slot_preferences and slot_preferences[activity]:
            preferred_slot = slot_preferences[activity]
            if slot != preferred_slot:
                issues.append(f"'{activity}' in slot {slot} (prefers slot {preferred_slot})")
        
        if issues:
            print(f"    [QUESTIONABLE] {activity} ({day}-{slot}): {'; '.join(issues)}")
        else:
            print(f"    [OK] {activity} ({day}-{slot}): Placement looks reasonable")

def main():
    """Run multi-slot display debugging."""
    debugger = MultiSlotDisplayDebugger()
    
    # Find all troop files
    import glob
    troop_files = sorted(glob.glob("*troops.json"))
    
    # Debug a specific week that might have multi-slot issues
    test_files = [f for f in troop_files if 'voyageur_week3' in f or 'tc_week3' in f]
    
    if test_files:
        for troop_file in test_files:
            try:
                debugger.debug_multislot_display(troop_file)
                debugger.debug_scheduling_decisions(troop_file)
            except Exception as e:
                print(f"Error debugging {troop_file}: {e}")
    else:
        print("No test files found. Debugging all weeks...")
        for troop_file in troop_files:
            try:
                debugger.debug_multislot_display(troop_file)
            except Exception as e:
                print(f"Error debugging {troop_file}: {e}")
    
    print(f"\n=== DEBUGGING COMPLETE ===")

if __name__ == "__main__":
    main()
