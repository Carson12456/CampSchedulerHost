"""
COMPREHENSIVE SCHEDULE VALIDATION TOOL

Run this to detect ANY scheduling issues:
  python validate_schedule.py

Checks for:
1. Overlapping activities (multiple non-concurrent activities in same slot)
2. Multi-slot activities extending beyond day boundaries
3. Duplicate entries (same troop, activity, slot)
4. Multi-slot activity extensions overlapping with other activities
5. Beach Slot Rule violations
6. Missing mandatory activities (Reflection, Super Troop)
"""

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
import sys
from io import StringIO
import os


def validate_week(week_file, verbose=True):
    """Validate a single week's schedule and return list of issues."""
    week_name = week_file.replace('tc_', '').replace('_troops.json', '')
    
    troops = load_troops_from_json(week_file)
    scheduler = ConstrainedScheduler(troops)
    
    # Suppress scheduler output
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    scheduler.schedule_all()
    sys.stdout = old_stdout
    
    issues = []
    
    # ========== CHECK 1: Overlapping Activities ==========
    slot_groups = {}
    for entry in scheduler.schedule.entries:
        key = (entry.troop.name, entry.time_slot.day.name, entry.time_slot.slot_number)
        if key not in slot_groups:
            slot_groups[key] = []
        slot_groups[key].append(entry)
    
    for key, entries in slot_groups.items():
        non_concurrent = [e for e in entries 
                        if e.activity.name not in scheduler.CONCURRENT_ACTIVITIES]
        if len(non_concurrent) > 1:
            activities = [e.activity.name for e in non_concurrent]
            issues.append({
                'type': 'OVERLAP',
                'severity': 'CRITICAL',
                'troop': key[0],
                'day': key[1],
                'slot': key[2],
                'details': f"Multiple activities: {', '.join(activities)}"
            })
    
    # ========== CHECK 2: Multi-slot boundary violations ==========
    # Only check STARTING entries, not continuations
    seen_activities_boundary = set()
    for entry in scheduler.schedule.entries:
        if entry.activity.slots > 1:
            start_slot = entry.time_slot.slot_number
            day = entry.time_slot.day.name
            activity_key = (entry.troop.name, entry.activity.name, day)
            
            # Skip continuation entries
            if activity_key in seen_activities_boundary:
                continue
            seen_activities_boundary.add(activity_key)
            
            slots_needed = int(entry.activity.slots + 0.5)
            max_slot = 2 if day == 'THURSDAY' else 3
            end_slot = start_slot + slots_needed - 1
            
            if end_slot > max_slot:
                issues.append({
                    'type': 'BOUNDARY',
                    'severity': 'ERROR',
                    'troop': entry.troop.name,
                    'day': day,
                    'slot': start_slot,
                    'details': f"{entry.activity.name} needs {slots_needed} slots, extends to slot {end_slot} but max is {max_slot}"
                })
    
    # ========== CHECK 3: Multi-slot extension overlaps ==========
    # Only check STARTING entries, not continuations
    seen_activities_extension = set()
    for entry in scheduler.schedule.entries:
        if entry.activity.slots > 1:
            troop = entry.troop
            start_day = entry.time_slot.day.name
            start_slot = entry.time_slot.slot_number
            activity_key = (troop.name, entry.activity.name, start_day)
            
            # Skip continuation entries
            if activity_key in seen_activities_extension:
                continue
            seen_activities_extension.add(activity_key)
            
            slots_needed = int(entry.activity.slots + 0.5)
            
            # Check each extended slot
            for offset in range(1, slots_needed):
                extended_slot = start_slot + offset
                # Find any other non-concurrent activity in this slot (NOT including our own continuations)
                for other in scheduler.schedule.entries:
                    if (other.troop == troop and 
                        other.time_slot.day.name == start_day and
                        other.time_slot.slot_number == extended_slot and
                        other.activity.name not in scheduler.CONCURRENT_ACTIVITIES and
                        other.activity.name != entry.activity.name):  # Don't flag our own continuations!
                        issues.append({
                            'type': 'EXTENSION_OVERLAP',
                            'severity': 'CRITICAL',
                            'troop': troop.name,
                            'day': start_day,
                            'slot': extended_slot,
                            'details': f"{entry.activity.name} (from slot {start_slot}) extends into slot {extended_slot} where {other.activity.name} is scheduled"
                        })
    
    # ========== CHECK 4: Beach Slot Rule ==========
    BEACH_ACTIVITIES = [
        "Aqua Trampoline", "Water Polo", "Troop Swim",
        "Float for Floats", "Greased Watermelon", "Canoe Snorkel",
        "Troop Canoe", "Nature Canoe", "Fishing"
    ]
    for entry in scheduler.schedule.entries:
        if entry.activity.name in BEACH_ACTIVITIES:
            # Slot 2 is only a violation if NOT on Thursday (user clarified Thursday only)
            if entry.time_slot.slot_number == 2 and entry.time_slot.day.name != 'THURSDAY':
                issues.append({
                    'type': 'BEACH_SLOT',
                    'severity': 'WARNING',
                    'troop': entry.troop.name,
                    'day': entry.time_slot.day.name,
                    'slot': 2,
                    'details': f"{entry.activity.name} in slot 2 (beach activities should be slot 1 or 3)"
                })
    
    # ========== CHECK 5: Missing Mandatory Activities ==========
    for troop in scheduler.troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        activity_names = {e.activity.name for e in troop_entries}
        
        if 'Reflection' not in activity_names:
            issues.append({
                'type': 'MISSING',
                'severity': 'ERROR',
                'troop': troop.name,
                'day': 'N/A',
                'slot': 'N/A',
                'details': 'Missing Reflection'
            })
        
        if 'Super Troop' not in activity_names:
            issues.append({
                'type': 'MISSING',
                'severity': 'ERROR',
                'troop': troop.name,
                'day': 'N/A',
                'slot': 'N/A',
                'details': 'Missing Super Troop'
            })
    
    # ========== CHECK 6: Schedule Gaps (Empty Slots) ==========
    # This is a CRITICAL check - every troop must have activities in all slots
    from models import Day as ModelDay
    import math
    
    days_list = [ModelDay.MONDAY, ModelDay.TUESDAY, ModelDay.WEDNESDAY, ModelDay.THURSDAY, ModelDay.FRIDAY]
    slots_per_day = {
        ModelDay.MONDAY: 3, ModelDay.TUESDAY: 3, ModelDay.WEDNESDAY: 3,
        ModelDay.THURSDAY: 2, ModelDay.FRIDAY: 3
    }
    
    total_gaps = 0
    for troop in scheduler.troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        
        # Build filled_slots accounting for multi-slot activities
        filled_slots = set()
        for e in troop_entries:
            filled_slots.add((e.time_slot.day, e.time_slot.slot_number))
            # Add continuation slots for multi-slot activities (Sailing = 2 slots, etc.)
            if e.activity.slots > 1:
                for extra in range(1, math.ceil(e.activity.slots)):
                    next_slot = e.time_slot.slot_number + extra
                    if next_slot <= slots_per_day.get(e.time_slot.day, 3):
                        filled_slots.add((e.time_slot.day, next_slot))
        
        # Check each slot
        for day in days_list:
            for slot_num in range(1, slots_per_day[day] + 1):
                if (day, slot_num) not in filled_slots:
                    total_gaps += 1
                    issues.append({
                        'type': 'GAP',
                        'severity': 'CRITICAL',
                        'troop': troop.name,
                        'day': day.name,
                        'slot': slot_num,
                        'details': f'Empty slot - no activity scheduled'
                    })
    
    # ========== CHECK 7: Entry Count ==========
    for troop in scheduler.troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        # Each troop should have exactly 14 slots (or less if multi-slot activities consume extra)
        # Thursday has 2 slots, other days have 3 = 4*3 + 2 = 14
        if len(troop_entries) < 10:  # Minimum reasonable entries
            issues.append({
                'type': 'INCOMPLETE',
                'severity': 'WARNING',
                'troop': troop.name,
                'day': 'N/A',
                'slot': 'N/A',
                'details': f'Only {len(troop_entries)} entries (expected ~14)'
            })

    
    # ========== CHECK 7: Activity Exclusivity ==========
    # Multiple troops should not have the same activity at the same time
    # Exceptions (CAN have multiple troops):
    # - Reflection (all troops do it on Friday)
    # - Campsite Free Time, Shower House (concurrent activities)
    # - 3-hour off-camp activities (Itasca, Tamarac, Back of the Moon)
    # Note: Gaga Ball, 9 Square, Float for Floats are EXCLUSIVE (one troop at a time)
    # Note: Delta and Super Troop ARE exclusive (one troop per commissioner)
    CONCURRENT = {
        'Reflection',
        'Campsite Free Time',
        'Shower House',
        'Itasca State Park', 'Tamarac Wildlife Refuge', 'Back of the Moon'
    }
    activity_slot_map = {}  # (day, slot, activity) -> list of troop names
    
    for entry in scheduler.schedule.entries:
        if entry.activity.name not in CONCURRENT:
            key = (entry.time_slot.day.name, entry.time_slot.slot_number, entry.activity.name)
            if key not in activity_slot_map:
                activity_slot_map[key] = []
            activity_slot_map[key].append(entry)
    
    # Canoe activities and capacity constant
    CANOE_ACTIVITIES = ['Nature Canoe', 'Canoe Snorkel', 'Float for Floats', 'Troop Canoe']
    MAX_CANOE_CAPACITY = 26
    
    for key, entries in activity_slot_map.items():
        if len(entries) > 1:
            day, slot, activity = key
            
            # Sailing is EXCLUSIVE: Only 1 troop per slot (per Spine rule)
            # No special handling - multiple troops is a violation
            
            # SPECIAL: Water Polo allows up to 2 troops
            if activity == "Water Polo" and len(entries) <= 2:
                continue
            
            # SPECIAL: Aqua Trampoline - 2 troops if both <=16 scouts
            if activity == "Aqua Trampoline":
                all_small = all(e.troop.scouts <= 16 for e in entries)
                if all_small and len(entries) <= 2:
                    continue
            
            # SPECIAL: Canoe activities - check total capacity
            if activity in CANOE_ACTIVITIES:
                total_people = sum(e.troop.scouts + e.troop.adults for e in entries)
                if total_people <= MAX_CANOE_CAPACITY:
                    continue
            
            troops = [e.troop.name for e in entries]
            issues.append({
                'type': 'ACTIVITY_CONFLICT',
                'severity': 'CRITICAL',
                'troop': ', '.join(troops),
                'day': day,
                'slot': slot,
                'details': f"Multiple troops ({', '.join(troops)}) have {activity} at the same time"
            })
    
    # ========== CHECK 7b: Exclusive AREA Conflicts ==========
    # Multiple troops should not have activities from the same exclusive area at the same time
    # This catches cases where e.g. one troop has Knots and Lashings and another has Orienteering
    # (both are Outdoor Skills area activities that require the same staff)
    from models import EXCLUSIVE_AREAS
    
    # Build activity->area map
    activity_to_area = {}
    for area, activities in EXCLUSIVE_AREAS.items():
        for activity_name in activities:
            activity_to_area[activity_name] = area
    
    # Group entries by (day, slot, AREA)
    area_slot_map = {}  # (day, slot, area) -> list of entries
    for entry in scheduler.schedule.entries:
        if entry.activity.name in CONCURRENT:
            continue
        area = activity_to_area.get(entry.activity.name)
        if area:
            key = (entry.time_slot.day.name, entry.time_slot.slot_number, area)
            if key not in area_slot_map:
                area_slot_map[key] = []
            area_slot_map[key].append(entry)
    
    for key, entries in area_slot_map.items():
        if len(entries) > 1:
            day, slot, area = key
            
            # Check if they're all the same activity (already caught above)
            activity_names = set(e.activity.name for e in entries)
            if len(activity_names) == 1:
                continue  # Same activity, already handled
            
            # SPECIAL: Water Polo allows up to 2 troops
            if area == "Water Polo" and len(entries) <= 2:
                continue
            
            # SPECIAL: Aqua Trampoline - 2 troops if both <=16 scouts
            if area == "Aqua Trampoline":
                all_small = all(e.troop.scouts <= 16 for e in entries)
                if all_small and len(entries) <= 2:
                    continue
            
            # SPECIAL: Canoe activities - check total capacity
            canoe_areas = {'Nature Canoe', 'Canoe Snorkel', 'Float for Floats', 'Troop Canoe'}
            if area in canoe_areas:
                total_people = sum(e.troop.scouts + e.troop.adults for e in entries)
                if total_people <= MAX_CANOE_CAPACITY:
                    continue
            
            troops_activities = [(e.troop.name, e.activity.name) for e in entries]
            issues.append({
                'type': 'AREA_CONFLICT',
                'severity': 'CRITICAL',
                'troop': ', '.join(e.troop.name for e in entries),
                'day': day,
                'slot': slot,
                'details': f"Multiple troops in '{area}' area: " + 
                           ', '.join(f"{t[0]}={t[1]}" for t in troops_activities)
            })
    
    # ========== CHECK 8: Rifle + Shotgun Same Day (CRITICAL) ==========
    for troop in scheduler.troops:
        from models import Day as ModelDay
        for day in [ModelDay.MONDAY, ModelDay.TUESDAY, ModelDay.WEDNESDAY, ModelDay.THURSDAY, ModelDay.FRIDAY]:
            day_entries = [e for e in scheduler.schedule.entries 
                          if e.troop == troop and e.time_slot.day == day]
            has_rifle = any(e.activity.name == "Troop Rifle" for e in day_entries)
            has_shotgun = any(e.activity.name == "Troop Shotgun" for e in day_entries)
            if has_rifle and has_shotgun:
                issues.append({
                    'type': 'RIFLE_SHOTGUN_SAME_DAY',
                    'severity': 'CRITICAL',
                    'troop': troop.name,
                    'day': day.name,
                    'slot': 'N/A',
                    'details': 'Troop Rifle and Troop Shotgun on same day (HARD CONSTRAINT)'
                })
    
    # ========== CHECK 9: Canoe Same-Day Conflicts (CRITICAL) ==========
    # Check if a troop has TWO DIFFERENT canoe activity TYPES on the same day
    # (same activity in multiple slots is OK - that's multi-slot handling)
    CANOE_ACTIVITIES = ["Troop Canoe", "Canoe Snorkel", "Nature Canoe", "Float for Floats"]
    for troop in scheduler.troops:
        from models import Day as ModelDay
        for day in [ModelDay.MONDAY, ModelDay.TUESDAY, ModelDay.WEDNESDAY, ModelDay.THURSDAY, ModelDay.FRIDAY]:
            day_entries = [e for e in scheduler.schedule.entries 
                          if e.troop == troop and e.time_slot.day == day]
            # Get UNIQUE canoe activity types (not counting duplicates from multi-slot)
            canoe_acts = set(e.activity.name for e in day_entries if e.activity.name in CANOE_ACTIVITIES)
            if len(canoe_acts) > 1:
                issues.append({
                    'type': 'CANOE_CONFLICT',
                    'severity': 'CRITICAL',
                    'troop': troop.name,
                    'day': day.name,
                    'slot': 'N/A',
                    'details': f'Multiple canoe activities on same day: {", ".join(canoe_acts)}'
                })
    
    # ========== CHECK 10: Trading Post Same-Day Conflicts (CRITICAL) ==========
    for troop in scheduler.troops:
        from models import Day as ModelDay
        for day in [ModelDay.MONDAY, ModelDay.TUESDAY, ModelDay.WEDNESDAY, ModelDay.THURSDAY, ModelDay.FRIDAY]:
            day_entries = [e for e in scheduler.schedule.entries 
                          if e.troop == troop and e.time_slot.day == day]
            activity_names = {e.activity.name for e in day_entries}
            
            if "Trading Post" in activity_names and "Campsite Free Time" in activity_names:
                issues.append({
                    'type': 'TRADING_POST_CONFLICT',
                    'severity': 'CRITICAL',
                    'troop': troop.name,
                    'day': day.name,
                    'slot': 'N/A',
                    'details': 'Trading Post and Campsite Free Time on same day'
                })
            
            if "Trading Post" in activity_names and "Shower House" in activity_names:
                issues.append({
                    'type': 'TRADING_POST_CONFLICT',
                    'severity': 'CRITICAL',
                    'troop': troop.name,
                    'day': day.name,
                    'slot': 'N/A',
                    'details': 'Trading Post and Shower House on same day'
                })
    
    # ========== CHECK 11: HC/DG Pairing Requirement (CRITICAL) ==========
    for troop in scheduler.troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        activity_names = {e.activity.name for e in troop_entries}
        
        if "History Center" in activity_names or "Disc Golf" in activity_names:
            has_balls = "Gaga Ball" in activity_names or "9 Square" in activity_names
            if not has_balls:
                hc_or_dg = "History Center" if "History Center" in activity_names else "Disc Golf"
                issues.append({
                    'type': 'HC_DG_PAIRING',
                    'severity': 'CRITICAL',
                    'troop': troop.name,
                    'day': 'N/A',
                    'slot': 'N/A',
                    'details': f'{hc_or_dg} scheduled without Gaga Ball or 9 Square pairing'
                })
    
    # ========== CHECK 12: Back of the Moon Top 3 Rule (WARNING) ==========
    for troop in scheduler.troops:
        troop_entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        if any(e.activity.name == "Back of the Moon" for e in troop_entries):
            rank = troop.preferences.index("Back of the Moon") + 1 if "Back of the Moon" in troop.preferences else 999
            if rank > 3:
                issues.append({
                    'type': 'BOTM_RANK',
                    'severity': 'WARNING',
                    'troop': troop.name,
                    'day': 'N/A',
                    'slot': 'N/A',
                    'details': f'Back of the Moon scheduled but ranked #{rank} (should be Top 3)'
                })
    
    return issues, week_name


def main():
    print("="*70)
    print("COMPREHENSIVE SCHEDULE VALIDATION")
    print("="*70)
    
    week_files = sorted([f for f in os.listdir('.') if f.startswith('tc_week') and f.endswith('_troops.json')])
    
    total_issues = 0
    critical_count = 0
    error_count = 0
    warning_count = 0
    
    for week_file in week_files:
        issues, week_name = validate_week(week_file)
        
        print(f"\n{week_name.upper()}:")
        print("-"*50)
        
        if not issues:
            print("  [PASS] No issues found")
        else:
            for issue in issues:
                severity = issue['severity']
                if severity == 'CRITICAL':
                    critical_count += 1
                    prefix = "[CRITICAL]"
                elif severity == 'ERROR':
                    error_count += 1
                    prefix = "[ERROR]"
                else:
                    warning_count += 1
                    prefix = "[WARNING]"
                
                print(f"  {prefix} {issue['type']}: {issue['troop']} @ {issue['day']} slot {issue['slot']}")
                print(f"           {issue['details']}")
                total_issues += 1
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total Issues: {total_issues}")
    print(f"  CRITICAL: {critical_count}")
    print(f"  ERROR: {error_count}")
    print(f"  WARNING: {warning_count}")
    
    if critical_count > 0:
        print("\n[FAIL] Schedule has CRITICAL issues that must be fixed!")
        return 1
    elif error_count > 0:
        print("\n[NEEDS ATTENTION] Schedule has errors that should be addressed")
        return 1
    elif warning_count > 0:
        print("\n[OK WITH WARNINGS] Schedule is functional but has minor issues")
        return 0
    else:
        print("\n[PASS] All schedules validated successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
