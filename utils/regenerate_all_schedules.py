
import sys
import os
import io
from pathlib import Path

# Fix encoding for Windows when output is redirected (prevents UnicodeEncodeError)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.io_handler import load_troops_from_json, save_schedule_to_json
from core.activities import get_all_activities
from core.constrained_scheduler import ConstrainedScheduler
from core.services.unscheduled_source import build_unscheduled_data

def regenerate_all():
    print("Regenerating all schedules...")
    
    troops_dir = Path("data/troops")
    schedules_dir = Path("data/schedules")
    schedules_dir.mkdir(parents=True, exist_ok=True)
    
    troop_files = list(troops_dir.glob("*.json"))
    all_activities = get_all_activities()
    
    print(f"Found {len(troop_files)} troop files.")
    
    success_count = 0
    for troop_file in troop_files:
        week_name = troop_file.stem
        print(f"\nProcessing {week_name}...")
        
        try:
            # Load troops
            troops = load_troops_from_json(str(troop_file))
            voyageur_mode = "voyageur" in week_name.lower()
            
            # Generate schedule
            scheduler = ConstrainedScheduler(troops, all_activities, voyageur_mode=voyageur_mode)
            schedule = scheduler.schedule_all()
            sailing_half_fills = getattr(scheduler, 'sailing_balls_fills', {}) or {}
            day_request_displacements = getattr(scheduler, 'day_request_displacements', None)
            
            # Authoritative unscheduled payload for all Top-5/Top-10 miss reporting.
            unscheduled_data = build_unscheduled_data(
                scheduler.troops, schedule, sailing_half_fills, day_request_displacements
            )
            
            # Save
            output_file = schedules_dir / f"{week_name}_schedule.json"
            save_schedule_to_json(
                schedule,
                scheduler.troops,
                str(output_file),
                unscheduled_data,
                sailing_half_fills,
                day_request_displacements,
            )
            
            print(f"  Saved to {output_file}")
            success_count += 1
            
        except Exception as e:
            print(f"  FAILED {week_name}: {e}")
            import traceback
            traceback.print_exc(file=sys.stdout)
            
    print(f"\nSuccessfully regenerated {success_count}/{len(troop_files)} schedules.")
    if success_count != len(troop_files):
        raise RuntimeError(
            f"Regeneration incomplete: {success_count}/{len(troop_files)} schedules succeeded"
        )

if __name__ == "__main__":
    regenerate_all()
