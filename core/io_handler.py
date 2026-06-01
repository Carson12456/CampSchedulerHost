import json
from pathlib import Path
from .models import Troop

def load_troops_from_json(file_path):
    """Load troops from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed troop JSON in {file_path}: {exc}") from exc

    if not isinstance(data, dict) or 'troops' not in data:
        raise ValueError(f"Troop JSON {file_path} is missing the required 'troops' key")

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

def save_schedule_to_json(schedule, troops, output_file, unscheduled_data=None, sailing_half_fills=None,
                          day_request_displacements=None):
    """Save schedule and troops to a JSON file (cache format).

    ``day_request_displacements`` is the scheduler's set of
    ``(troop_name, activity_name)`` preferences displaced by an honored
    MUST-HONOR day request. It is persisted so the regression checker and any
    JSON reader can reproduce the authoritative BRAIN §2 Exemption 4(b)
    decisions without rerunning the scheduler.
    """
    
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
        
    # Serialize day-request displacement provenance as a sorted list of
    # [troop_name, activity_name] pairs (JSON has no sets/tuples).
    displacements_data = sorted(
        [list(pair) for pair in day_request_displacements]
    ) if day_request_displacements else []

    output_data = {
        'troops': troops_data,
        'entries': entries_data,
        'unscheduled': unscheduled_data if unscheduled_data else {},
        'sailing_half_fills': sailing_half_fills if sailing_half_fills else {},
        'day_request_displacements': displacements_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Schedule saved to {output_file}")
def load_schedule_from_json(file_path, troops, all_activities):
    """
    Load a schedule from a JSON file.
    Requires fully populated troops and activities lists to reconstruct objects.
    """
    from .models import Schedule, ScheduleEntry, TimeSlot, Day

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed schedule JSON in {file_path}: {exc}") from exc

    if not isinstance(data, dict) or 'entries' not in data:
        raise ValueError(f"Schedule JSON {file_path} is missing the required 'entries' key")

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
        
        try:
            day = Day[day_name.upper()]
        except KeyError:
            raise ValueError(f"Invalid day {day_name!r} in schedule entry: {entry_data}")

        missing = []
        if troop is None:
            missing.append(f"troop {troop_name!r}")
        if activity is None:
            missing.append(f"activity {activity_name!r}")
        if missing:
            raise ValueError(f"Unknown {' and '.join(missing)} in schedule entry: {entry_data}")

        slot = TimeSlot(day=day, slot_number=slot_num)
        entry = ScheduleEntry(time_slot=slot, activity=activity, troop=troop)
        schedule.entries.append(entry)
            
    return schedule
