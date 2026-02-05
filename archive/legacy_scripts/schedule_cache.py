"""
Schedule Caching System (Item 12)
Automatically detects changes and regenerates schedules as needed.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime

def get_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def get_cache_info_path(week_file):
    """Get path to cache info file."""
    week_name = Path(week_file).stem
    return Path("schedules") / f"{week_name}_cache_info.json"

def get_schedule_path(week_file):
    """Get path to cached schedule file."""
    week_name = Path(week_file).stem
    return Path("schedules") / f"{week_name}_schedule.json"

def is_cache_valid(week_file):
    """Check if cached schedule is still valid."""
    cache_info_path = get_cache_info_path(week_file)
    schedule_path = get_schedule_path(week_file)
    
    # Check if cache files exist
    if not cache_info_path.exists() or not schedule_path.exists():
        return False
    
    # Load cache info
    try:
        with open(cache_info_path, 'r') as f:
            cache_info = json.load(f)
    except:
        return False
    
    # Check if source file hash matches
    current_hash = get_file_hash(week_file)
    if cache_info.get('source_hash') != current_hash:
        return False
    
    # Check if source file was modified
    source_mtime = Path(week_file).stat().st_mtime
    if cache_info.get('source_mtime') != source_mtime:
        return False
    
    return True

def save_cache_info(week_file):
    """Save cache information for a week file."""
    cache_info = {
        'source_file': str(week_file),
        'source_hash': get_file_hash(week_file),
        'source_mtime': Path(week_file).stat().st_mtime,
        'generated_at': datetime.now().isoformat(),
        'cache_version': '1.0'
    }
    
    cache_info_path = get_cache_info_path(week_file)
    cache_info_path.parent.mkdir(exist_ok=True)
    
    with open(cache_info_path, 'w') as f:
        json.dump(cache_info, f, indent=2)

def invalidate_cache(week_file):
    """Invalidate cache for a week file."""
    cache_info_path = get_cache_info_path(week_file)
    if cache_info_path.exists():
        cache_info_path.unlink()

def get_or_generate_schedule(week_file, force_regenerate=False):
    """Get cached schedule or generate new one if needed."""
    from io_handler import load_troops_from_json
    from constrained_scheduler import ConstrainedScheduler
    from activities import get_all_activities
    
    schedule_path = get_schedule_path(week_file)
    
    # Check cache validity
    if not force_regenerate and is_cache_valid(week_file):
        print(f"✓ Using cached schedule for {week_file}")
        with open(schedule_path, 'r') as f:
            return json.load(f)
    
    # Generate new schedule
    print(f"⟳ Generating schedule for {week_file}...")
    troops = load_troops_from_json(week_file)
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    
    # Save schedule
    schedule_data = {
        'week_file': str(week_file),
        'troops': [{'name': t.name, 'scouts': t.scouts, 'adults': t.adults} for t in troops],
        'entries': [
            {
                'troop': e.troop.name,
                'activity': e.activity.name,
                'day': e.time_slot.day.value,
                'slot': e.time_slot.slot_number
            }
            for e in schedule.entries
        ],
        'generated_at': datetime.now().isoformat()
    }
    
    schedule_path.parent.mkdir(exist_ok=True)
    with open(schedule_path, 'w') as f:
        json.dump(schedule_data, f, indent=2)
    
    # Save cache info
    save_cache_info(week_file)
    
    print(f"✓ Schedule cached to {schedule_path}")
    return schedule_data

if __name__ == "__main__":
    import glob
    import sys
    
    week_files = glob.glob("tc_week*.json") + glob.glob("voyageur_week*.json")
    
    force = "--force" in sys.argv
    
    print("Schedule Cache Management")
    print("=" * 60)
    
    for week_file in sorted(week_files):
        get_or_generate_schedule(week_file, force_regenerate=force)
    
    print("\n✓ All schedules cached")
