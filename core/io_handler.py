import json
from pathlib import Path
from .models import Troop

def load_troops_from_json(file_path):
    """Load troops from a JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    troops = []
    for t_data in data['troops']:
        # Handle optional fields
        campsite = t_data.get('campsite', t_data['name'])
        commissioner = t_data.get('commissioner', "")
        day_requests = t_data.get('day_requests', {})
        
        troop = Troop(
            name=t_data['name'],
            scouts=t_data.get('scouts', 10),
            adults=t_data.get('adults', 2),
            campsite=campsite,
            commissioner=commissioner,
            preferences=t_data.get('preferences', []),
            day_requests=day_requests
        )
        troops.append(troop)
        
    return troops

def save_schedule_to_json(schedule, troops, output_file, unscheduled_data=None):
    """Save schedule and troops to a JSON file (cache format)."""
    
    # Serialize troops
    troops_data = []
    for t in troops:
        t_dict = {
            'name': t.name,
            'scouts': t.scouts,
            'adults': t.adults,
            'campsite': t.campsite,
            'commissioner': t.commissioner,
            'preferences': t.preferences,
            'day_requests': t.day_requests
        }
        troops_data.append(t_dict)
        
    # Serialize entries
    entries_data = []
    for entry in schedule.entries:
        entry_dict = {
            'troop_name': entry.troop.name,
            'activity_name': entry.activity.name,
            'day': entry.time_slot.day.name,
            'slot': entry.time_slot.slot_number
        }
        entries_data.append(entry_dict)
        
    output_data = {
        'troops': troops_data,
        'entries': entries_data,
        'unscheduled': unscheduled_data if unscheduled_data else {}
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Schedule saved to {output_file}")
def load_schedule_from_json(file_path, troops, all_activities):
    """
    Load a schedule from a JSON file.
    Requires fully populated troops and activities lists to reconstruct objects.
    """
    from .models import Schedule, ScheduleEntry, TimeSlot, Day
    
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    schedule = Schedule()
    
    # Map names to objects
    troop_map = {t.name: t for t in troops}
    activity_map = {a.name: a for a in all_activities}
    
    for entry_data in data['entries']:
        troop_name = entry_data['troop_name']
        activity_name = entry_data['activity_name']
        day_name = entry_data['day']
        slot_num = entry_data['slot']
        
        troop = troop_map.get(troop_name)
        activity = activity_map.get(activity_name)
        
        # Look up Day enum safely
        try:
            day = Day[day_name.upper()]
        except KeyError:
            print(f"Warning: Invalid day {day_name}")
            continue
            
        if troop and activity:
            slot = TimeSlot(day, slot_num)
            entry = ScheduleEntry(slot, activity, troop)
            schedule.entries.append(entry)
            
    return schedule
