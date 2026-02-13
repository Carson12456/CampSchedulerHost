
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.constrained_scheduler import ConstrainedScheduler
from core.activities import get_all_activities
from core.io_handler import load_troops_from_json, save_schedule_to_json

def regenerate_all():
    root_dir = Path(__file__).parent.parent
    troops_dir = root_dir / "data" / "troops"
    schedules_dir = root_dir / "data" / "schedules"
    
    schedules_dir.mkdir(parents=True, exist_ok=True)
    
    all_activities = get_all_activities()
    
    # Process all JSON files in troops directory
    for troop_file in troops_dir.glob("*.json"):
        print(f"Processing {troop_file.name}...")
        
        try:
            troops = load_troops_from_json(str(troop_file))
            scheduler = ConstrainedScheduler(troops, all_activities)
            schedule = scheduler.schedule_all()
            
            # Construct output filename: {basename}_schedule.json
            output_file = schedules_dir / f"{troop_file.stem}_schedule.json"
            
            # Save
            save_schedule_to_json(schedule, troops, str(output_file))
            print(f"  -> Generated {output_file.name}")
            
        except Exception as e:
            print(f"  ERROR processing {troop_file.name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    regenerate_all()
