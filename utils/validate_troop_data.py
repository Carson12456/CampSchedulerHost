"""
Troop Data Validation Utility (Item 7 - partial)
Validates troop JSON files before scheduling.
"""
import json
from pathlib import Path

def validate_troop_file(filepath):
    """Validate a troop JSON file for common errors."""
    errors = []
    warnings = []
    
    # Check file exists
    if not Path(filepath).exists():
        errors.append(f"File not found: {filepath}")
        return errors, warnings
    
    # Load JSON
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return errors, warnings
    
    # Check structure
    if 'troops' not in data:
        errors.append("Missing 'troops' key in JSON")
        return errors, warnings
    
    if not isinstance(data['troops'], list):
        errors.append("'troops' must be a list")
        return errors, warnings
    
    # Valid activity names (from activities.py)
    VALID_ACTIVITIES = {
        "9 Square", "Gaga Ball", "Fishing", "Sauna", "Shower House", "Trading Post",
        "Aqua Trampoline", "Troop Canoe", "Troop Kayak", "Canoe Snorkel", "Float for Floats",
        "Greased Watermelon", "Underwater Obstacle Course", "Troop Swim", "Water Polo",
        "Nature Canoe", "Sailing", "Dr. DNA", "Loon Lore", "Hemp Craft", "Monkey's Fist",
        "Tie Dye", "Woggle Neckerchief Slide", "Archery", "Troop Rifle", "Troop Shotgun",
        "Climbing Tower", "Chopped!", "GPS & Geocaching", "Knots and Lashings",
        "Orienteering", "Ultimate Survivor", "What's Cooking", "Delta", "Super Troop",
        "Back of the Moon", "Disc Golf", "Itasca State Park", "Tamarac Wildlife Refuge",
        "Campsite Free Time", "Reflection", "History Center", "Ecosystem in a Jar",
        "Nature Salad", "Nature Bingo"
    }
    
    VALID_COMMISSIONERS = {
        "Commissioner A", "Commissioner B", "Commissioner C",
        "Voyageur A", "Voyageur B", "Voyageur C"
    }
    
    VALID_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    
    # Validate each troop
    for idx, troop in enumerate(data['troops']):
        troop_num = idx + 1
        
        # Required fields
        if 'name' not in troop:
            errors.append(f"Troop {troop_num}: Missing 'name'")
            continue
        
        troop_name = troop['name']
        
        if 'campsite' not in troop:
            errors.append(f"{troop_name}: Missing 'campsite'")
        
        if 'preferences' not in troop:
            errors.append(f"{troop_name}: Missing 'preferences'")
        elif not isinstance(troop['preferences'], list):
            errors.append(f"{troop_name}: 'preferences' must be a list")
        else:
            # Check for invalid activity names
            for pref in troop['preferences']:
                if pref not in VALID_ACTIVITIES:
                    errors.append(f"{troop_name}: Invalid activity '{pref}'")
            
            # Check for duplicates
            if len(troop['preferences']) != len(set(troop['preferences'])):
                warnings.append(f"{troop_name}: Duplicate preferences found")
        
        # Optional fields with validation
        if 'scouts' in troop:
            if not isinstance(troop['scouts'], int) or troop['scouts'] < 1 or troop['scouts'] > 50:
                errors.append(f"{troop_name}: scouts must be 1-50, got {troop['scouts']}")
        
        if 'adults' in troop:
            if not isinstance(troop['adults'], int) or troop['adults'] < 0 or troop['adults'] > 25:
                errors.append(f"{troop_name}: adults must be 0-25, got {troop['adults']}")
        
        if 'commissioner' in troop:
            if troop['commissioner'] and troop['commissioner'] not in VALID_COMMISSIONERS:
                warnings.append(f"{troop_name}: Unknown commissioner '{troop['commissioner']}'")
        
        if 'day_requests' in troop:
            if not isinstance(troop['day_requests'], dict):
                errors.append(f"{troop_name}: 'day_requests' must be a dict")
            else:
                for day, activities in troop['day_requests'].items():
                    if day not in VALID_DAYS:
                        errors.append(f"{troop_name}: Invalid day '{day}' in day_requests")
                    if not isinstance(activities, list):
                        errors.append(f"{troop_name}: day_requests['{day}'] must be a list")
                    else:
                        for act in activities:
                            if act not in VALID_ACTIVITIES:
                                errors.append(f"{troop_name}: Invalid activity '{act}' in day_requests")
    
    return errors, warnings

def validate_all_weeks():
    """Validate all week files."""
    import glob
    
    import glob
    import os
    
    data_dir = Path(__file__).parent.parent / "data/troops"
    week_files = list(data_dir.glob("tc_week*.json")) + list(data_dir.glob("voyageur_week*.json"))
    
    print("="*70)
    print("TROOP DATA VALIDATION")
    print("="*70)
    
    all_valid = True
    
    for week_file in sorted(week_files):
        print(f"\nValidating {week_file}...")
        errors, warnings = validate_troop_file(week_file)
        
        if errors:
            print(f"  [FAIL] {len(errors)} errors:")
            for err in errors[:5]:  # Show first 5
                print(f"    - {err}")
            if len(errors) > 5:
                print(f"    ... and {len(errors)-5} more")
            all_valid = False
        else:
            print("  [OK] No errors")
        
        if warnings:
            print(f"  [WARN] {len(warnings)} warnings:")
            for warn in warnings[:3]:
                print(f"    - {warn}")
            if len(warnings) > 3:
                print(f"    ... and {len(warnings)-3} more")
    
    print("\n" + "="*70)
    if all_valid:
        print("[OK] ALL FILES VALID")
    else:
        print("[FAIL] VALIDATION FAILED - Fix errors before scheduling")
    print("="*70)
    
    return all_valid

if __name__ == "__main__":
    validate_all_weeks()
