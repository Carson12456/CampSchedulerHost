"""
Generate and cache schedules for summer camp weeks.
This script generates schedules from troop JSON files and saves them as JSON for fast loading.
"""
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.activities import get_all_activities
from core.io_handler import load_troops_from_json
from core.constrained_scheduler import ConstrainedScheduler
from core.services.unscheduled_source import build_unscheduled_data

SCRIPT_DIR = Path(__file__).parent.resolve()
SCHEDULES_DIR = Path(__file__).parent.parent / "data/schedules"

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
    
    # Authoritative unscheduled payload for all Top-5/Top-10 miss reporting.
    unscheduled_data = build_unscheduled_data(scheduler.troops, schedule)

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
    # Look in data/troops/ directory
    troops_dir = SCRIPT_DIR.parent / "data" / "troops"
    troop_files = sorted(troops_dir.glob("*troops.json"))
    
    if not troop_files:
        print(f"No troop files found in {troops_dir} (*troops.json)")
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
