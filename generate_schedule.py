"""
Generate and cache schedules for summer camp weeks.
This script generates schedules from troop JSON files and saves them as JSON for fast loading.
"""
import json
import sys
from pathlib import Path
from models import generate_time_slots, Day
from activities import get_all_activities
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler

SCRIPT_DIR = Path(__file__).parent.resolve()
SCHEDULES_DIR = SCRIPT_DIR / "schedules"

def serialize_schedule(schedule):
    """Convert Schedule object to JSON-serializable format."""
    entries_data = []
    for entry in schedule.entries:
        # Safety check for entry structure
        if (hasattr(entry, 'troop') and hasattr(entry.troop, 'name') and
            hasattr(entry, 'activity') and hasattr(entry.activity, 'name') and
            hasattr(entry, 'time_slot') and hasattr(entry.time_slot, 'day') and 
            hasattr(entry.time_slot, 'slot_number')):
            entries_data.append({
                'troop_name': entry.troop.name,
                'activity_name': entry.activity.name,
                'day': entry.time_slot.day.name,
                'slot': entry.time_slot.slot_number
            })
        else:
            # Skip malformed entries
            continue
    return entries_data

def generate_and_save_schedule(troops_file):
    """Generate schedule for a troop file and save as JSON."""
    troops_path = Path(troops_file)
    if not troops_path.exists():
        print(f"Error: {troops_file} not found")
        return False
    
    # Extract week identifier from filename (e.g., "tc_week5", "voyageur_week1")
    week_id = troops_path.stem  # removes .json extension
    
    print(f"Generating schedule for {week_id}...")
    
    # Load troops and generate schedule
    troops = load_troops_from_json(troops_path)
    activities = get_all_activities()
    import inspect
    print(f"DEBUG: Scheduler loaded from {inspect.getfile(ConstrainedScheduler)}")
    # print(inspect.getsource(ConstrainedScheduler._optimize_friday_reflections))
    scheduler = ConstrainedScheduler(troops, activities)
    schedule = scheduler.schedule_all()
    
    # Calculate unscheduled activities
    unscheduled_data = {}
    # HC/DG exemption: if all 3 Tuesday slots are HC or DG, troops who missed HC/DG get exempt
    tuesday_hc_dg_slots = set()
    for e in schedule.entries:
        # Safety check for entry structure
        if (hasattr(e, 'time_slot') and 
            hasattr(e.time_slot, 'day') and 
            hasattr(e.time_slot, 'slot_number') and
            hasattr(e, 'activity') and
            hasattr(e.activity, 'name')):
            if e.time_slot.day == Day.TUESDAY and e.activity.name in ("History Center", "Disc Golf"):
                tuesday_hc_dg_slots.add(e.time_slot.slot_number)
    hc_dg_tuesday_full = tuesday_hc_dg_slots >= {1, 2, 3}

    for troop in scheduler.troops:
        troop_schedule = schedule.get_troop_schedule(troop)
        scheduled_activity_names = {e.activity.name for e in troop_schedule}
        
        # Check if troop has ANY 3-hour activity scheduled
        has_3hr_scheduled = any(name in ConstrainedScheduler.THREE_HOUR_ACTIVITIES for name in scheduled_activity_names)
        
        missing_top5 = []
        for i, pref in enumerate(troop.preferences[:5]):
            if pref not in scheduled_activity_names:
                is_exempt = False
                if pref in ConstrainedScheduler.THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
                    is_exempt = True
                elif pref in ("History Center", "Disc Golf") and hc_dg_tuesday_full:
                    is_exempt = True  # All 3 Tuesday slots given to troops who wanted it more
                missing_top5.append({'name': pref, 'rank': i+1, 'is_exempt': is_exempt})
                
        missing_top10 = []
        for i, pref in enumerate(troop.preferences[5:10]):
            if pref not in scheduled_activity_names:
                is_exempt = False
                if pref in ConstrainedScheduler.THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
                    is_exempt = True
                elif pref in ("History Center", "Disc Golf") and hc_dg_tuesday_full:
                    is_exempt = True
                missing_top10.append({'name': pref, 'rank': i+6, 'is_exempt': is_exempt})
                
        if missing_top5 or missing_top10:
            unscheduled_data[troop.name] = {
                'top5': missing_top5,
                'top10': missing_top10
            }

    # Serialize schedule and troops data
    schedule_data = {
        'week_id': week_id,
        'troops': [{
            'name': t.name,
            'scouts': t.scouts,
            'adults': t.adults,
            'commissioner': t.commissioner,
            'preferences': t.preferences
        } for t in troops],
        'entries': serialize_schedule(schedule),
        'unscheduled': unscheduled_data
    }
    
    # Save to JSON
    SCHEDULES_DIR.mkdir(exist_ok=True)
    output_file = SCHEDULES_DIR / f"{week_id}_schedule.json"
    
    with open(output_file, 'w') as f:
        json.dump(schedule_data, f, indent=2)
    
    print(f"Saved schedule to {output_file}")
    return True

def generate_all():
    """Generate schedules for all troop files."""
    troop_files = sorted(SCRIPT_DIR.glob("*troops.json"))
    
    if not troop_files:
        print("No troop files found (*troops.json)")
        return
    
    print(f"Found {len(troop_files)} troop file(s)")
    print("=" * 60)
    
    success_count = 0
    for troop_file in troop_files:
        if generate_and_save_schedule(troop_file):
            success_count += 1
        print()
    
    print("=" * 60)
    print(f"Generated {success_count}/{len(troop_files)} schedules successfully")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Generate specific file
        troop_file = sys.argv[1]
        generate_and_save_schedule(troop_file)
    else:
        # Generate all
        generate_all()
