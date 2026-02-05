"""
Update troop JSON files to fix activity naming mismatches.
"""
import json
from pathlib import Path

# Activity name replacements
REPLACEMENTS = {
    "Archery/Tomahawks/Slingshots": "Archery",
    "Reserve Shower House": "Shower House",
    "Reserve Trading Post": "Trading Post",
    "Campsite Time/Free Time": "Campsite Free Time",
    "Leave No Trace": "Knots and Lashings",
    "Turk's Head": "Woggle Neckerchief Slide"
}

def update_troop_file(filename):
    """Update a single troop JSON file with corrected activity names."""
    filepath = Path(filename)
    
    if not filepath.exists():
        print(f"Skipping {filename} - file not found")
        return
    
    # Load JSON
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Track changes
    changes_made = 0
    
    # Update each troop's preferences
    for troop in data['troops']:
        preferences = troop.get('preferences', [])
        for i, pref in enumerate(preferences):
            if pref in REPLACEMENTS:
                old_name = pref
                new_name = REPLACEMENTS[pref]
                preferences[i] = new_name
                changes_made += 1
                print(f"  {troop['name']}: '{old_name}' -> '{new_name}'")
        
        # Also update day_requests
        day_requests = troop.get('day_requests', {})
        for day, activities in day_requests.items():
            for i, act in enumerate(activities):
                if act in REPLACEMENTS:
                    old_name = act
                    new_name = REPLACEMENTS[act]
                    activities[i] = new_name
                    changes_made += 1
                    print(f"  {troop['name']}: day_requests '{old_name}' -> '{new_name}'")
    
    if changes_made > 0:
        # Save updated JSON
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"\n[OK] Updated {filename} ({changes_made} changes)\n")
    else:
        print(f"\n  No changes needed for {filename}\n")

if __name__ == "__main__":
    import glob
    
    print("=" * 60)
    print("Activity Name Migration Script")
    print("=" * 60)
    print()
    
    week_files = glob.glob("tc_week*.json") + glob.glob("voyageur_week*.json")
    
    for filename in sorted(week_files):
        print(f"Processing {filename}...")
        update_troop_file(filename)
    
    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)
