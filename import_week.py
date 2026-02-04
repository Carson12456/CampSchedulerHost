#!/usr/bin/env python3
"""
Bulletproof Week Import Script for Summer Camp Scheduler

This script provides a reliable process for importing new week data:
1. Parses raw troop preference input (tab-separated from spreadsheet)
2. Maps activity names to canonical system names
3. Validates all data
4. Generates clean JSON
5. Tests loading and schedule generation

Usage:
    python import_week.py --import-raw WEEK_NAME
    python import_week.py --validate tc_week4_troops.json
    python import_week.py --test-schedule tc_week4_troops.json
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Optional

# Activity name mapping: USER INPUT -> SYSTEM CANONICAL NAME
ACTIVITY_MAPPING = {
    # Beach Activities
    "aqua trampoline": "Aqua Trampoline",
    "greased watermelon": "Greased Watermelon",
    "water polo": "Water Polo",
    "troop swim": "Troop Swim",
    "fishing": "Fishing",
    "sauna": "Sauna",
    "float for floats": "Float for Floats",
    "canoe snorkel": "Canoe Snorkel",
    "snorkeling": "Canoe Snorkel",  # Alias
    "nature canoe": "Nature Canoe",
    "troop canoe": "Troop Canoe",
    "canoeing/kayaking/rowing": "Troop Canoe",  # Alias
    
    # Sailing
    "sailing": "Sailing",
    
    # Shooting Sports
    "shotgun": "Troop Shotgun",
    "troop shotgun": "Troop Shotgun", 
    "rifle": "Troop Rifle",
    "troop rifle": "Troop Rifle",
    ".22 rifle shoot": "Troop Rifle",  # Alias
    ".22 rifle": "Troop Rifle",  # Alias
    
    # Archery
    "archery": "Archery",
    "archery/tomahawks/slingshots": "Archery",
    
    # Tower
    "climbing tower": "Climbing Tower",
    "tower": "Climbing Tower",  # Alias
    
    # Outdoor Skills
    "chopped!": "Chopped!",
    "chopped": "Chopped!",  # Alias
    "gps & geocaching": "GPS & Geocaching",
    "gps and geocaching": "GPS & Geocaching",  # Alias
    "knots & lashings": "Knots and Lashings",
    "knots and lashings": "Knots and Lashings",
    "orienteering": "Orienteering",
    "ultimate survivor": "Ultimate Survivor",
    "what's cooking?": "What's Cooking",
    "what's cooking": "What's Cooking",
    "whats cooking": "What's Cooking",  # Alias
    
    # Delta/Commission Activities
    "delta": "Delta",
    "super troop": "Super Troop",
    "reflection": "Reflection",
    
    # Handicrafts
    "tie dye": "Tie Dye",
    "hemp craft": "Hemp Craft",
    "monkey's fist": "Monkey's Fist",
    "monkeys fist": "Monkey's Fist",  # Alias
    "woggle neckerchief slide": "Woggle Neckerchief Slide",
    
    # Nature
    "dr. dna": "Dr. DNA",
    "dr dna": "Dr. DNA",  # Alias
    "loon lore": "Loon Lore",
    
    # Balls (unstaffed beach activities)
    "gaga ball": "Gaga Ball",
    "9 square": "9 Square",
    "9-square": "9 Square",  # Alias
    
    # Camp Reservations
    "campsite free time": "Campsite Free Time",
    "campsite time/free time": "Campsite Free Time",
    "free time": "Campsite Free Time",  # Alias
    "reserve shower house": "Shower House",
    "showerhouse": "Shower House",  # Alias
    "shower house": "Shower House",  # Alias
    "reserve trading post": "Trading Post",
    "trading post": "Trading Post",  # Alias
    
    # Off-Camp
    "disc golf": "Disc Golf",
    "history center": "History Center",
    "history center/fire tower": "History Center",  # Alias
    "itasca state park": "Itasca State Park",
    "tamarac wildlife refuge": "Tamarac Wildlife Refuge",
    "back of the moon": "Back of the Moon",
    "back of the moon hike": "Back of the Moon",  # Alias
}

# Valid activity names from activities.py
VALID_ACTIVITIES = {
    "9 Square", "Gaga Ball", "Fishing", "Sauna", "Shower House", "Trading Post",
    "Aqua Trampoline", "Troop Canoe", "Troop Kayak", "Canoe Snorkel", "Float for Floats",
    "Greased Watermelon", "Underwater Obstacle Course", "Troop Swim", "Water Polo",
    "Nature Canoe", "Sailing", "Dr. DNA", "Loon Lore", "Hemp Craft", "Monkey's Fist",
    "Tie Dye", "Woggle Neckerchief Slide", "Archery", "Troop Rifle",
    "Troop Shotgun", "Climbing Tower", "Chopped!", "GPS & Geocaching", "Knots and Lashings",
    "Orienteering", "Ultimate Survivor", "What's Cooking", "Delta", "Super Troop",
    "Back of the Moon", "Disc Golf", "Itasca State Park", "Tamarac Wildlife Refuge",
    "Campsite Free Time", "Reflection", "History Center",
    "Ecosystem in a Jar", "Nature Salad", "Nature Bingo"
}

# Default commissioner assignments based on campsite (North to South geography)
CAMPSITE_COMMISSIONERS = {
    # Commissioner A (North Zone)
    "Massasoit": "Commissioner A",
    "Tecumseh": "Commissioner A",
    "Samoset": "Commissioner A",
    "Black Hawk": "Commissioner A",
    "Red Cloud": "Commissioner A",  # For other weeks
    
    # Commissioner B (Central Zone)
    "Taskalusa": "Commissioner B",
    "Powhatan": "Commissioner B",
    "Cochise": "Commissioner B",
    "Roman Nose": "Commissioner B",  # For other weeks
    
    # Commissioner C (South Zone)
    "Joseph": "Commissioner C",
    "Tamanend": "Commissioner C",
    "Pontiac": "Commissioner C",
    "Skenandoa": "Commissioner C",
}


def normalize_activity(raw_name: str) -> tuple[str, bool]:
    """
    Normalize an activity name to its canonical form.
    Returns (canonical_name, is_valid).
    """
    normalized = raw_name.strip().lower()
    
    # Try direct mapping
    if normalized in ACTIVITY_MAPPING:
        canonical = ACTIVITY_MAPPING[normalized]
        return canonical, canonical in VALID_ACTIVITIES
    
    # Try exact match (case-insensitive) against valid activities
    for valid in VALID_ACTIVITIES:
        if valid.lower() == normalized:
            return valid, True
    
    # Not found - return as-is (will be flagged as invalid)
    return raw_name.strip(), False


def parse_raw_input(lines: list[str]) -> list[dict]:
    """
    Parse raw tab-separated troop preference data.
    
    Expected format per line:
    TroopName\t\tPref1\tPref2\tPref3\t...\tOptionalNote
    
    Returns list of troop dicts with:
    - name
    - preferences (list, normalized)
    - notes (optional)
    - unmapped_activities (list of activities that couldn't be mapped)
    """
    troops = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        parts = line.split('\t')
        if len(parts) < 3:
            continue
        
        troop_name = parts[0].strip()
        if not troop_name:
            continue
        
        # Parse preferences (skip empty cells from double-tabs)
        raw_prefs = [p.strip() for p in parts[2:] if p.strip()]
        
        preferences = []
        unmapped = []
        notes = None
        
        for pref in raw_prefs:
            # Check if this looks like a note (contains sentence-like text)
            if len(pref) > 50 or "?" in pref or pref.lower().startswith("would") or pref.lower().startswith("thank"):
                notes = pref
                continue
            
            canonical, is_valid = normalize_activity(pref)
            
            # Avoid duplicates
            if canonical not in preferences:
                preferences.append(canonical)
                
            if not is_valid and canonical not in unmapped:
                unmapped.append(canonical)
        
        troop = {
            "name": troop_name,
            "campsite": troop_name,  # Usually same as name
            "commissioner": CAMPSITE_COMMISSIONERS.get(troop_name, "Commissioner A"),
            "preferences": preferences,
            "scouts": 10,  # Default, should be updated
            "adults": 2    # Default, should be updated
        }
        
        if notes:
            troop["notes"] = notes
        
        troops.append({
            **troop,
            "_unmapped": unmapped
        })
    
    return troops


def validate_json_file(filepath: Path) -> tuple[bool, list[str]]:
    """
    Validate an existing JSON troop file.
    Returns (is_valid, list of issues).
    """
    issues = []
    
    # Check file exists
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]
    
    # Try to parse JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    
    # Check structure
    if "troops" not in data:
        issues.append("Missing 'troops' key in JSON")
        return False, issues
    
    if not isinstance(data["troops"], list):
        issues.append("'troops' must be a list")
        return False, issues
    
    # Validate each troop
    for i, troop in enumerate(data["troops"]):
        troop_name = troop.get("name", f"Troop #{i}")
        
        # Required fields
        for field in ["name", "campsite", "preferences"]:
            if field not in troop:
                issues.append(f"{troop_name}: Missing required field '{field}'")
        
        # Validate preferences
        if "preferences" in troop:
            for pref in troop["preferences"]:
                canonical, is_valid = normalize_activity(pref)
                if not is_valid:
                    issues.append(f"{troop_name}: Unknown activity '{pref}'")
    
    # Try to load via io_handler
    try:
        from io_handler import load_troops_from_json
        troops = load_troops_from_json(filepath)
        print(f"[OK] Successfully loaded {len(troops)} troops via io_handler")
    except Exception as e:
        issues.append(f"io_handler failed to load: {e}")
    
    return len(issues) == 0, issues


def test_schedule_generation(filepath: Path) -> tuple[bool, Optional[str]]:
    """
    Test that a schedule can be generated for the week.
    Returns (success, error_message).
    """
    try:
        from io_handler import load_troops_from_json
        from activities import get_all_activities
        from constrained_scheduler import ConstrainedScheduler
        
        troops = load_troops_from_json(filepath)
        activities = get_all_activities()
        
        voyageur_mode = "voyageur" in filepath.name.lower()
        scheduler = ConstrainedScheduler(troops, activities, voyageur_mode=voyageur_mode)
        schedule = scheduler.schedule_all()
        
        # Basic verification
        if len(schedule.entries) == 0:
            return False, "Schedule is empty"
        
        print(f"[OK] Generated schedule with {len(schedule.entries)} entries")
        
        # Check each troop has activities
        for troop in scheduler.troops:
            troop_entries = schedule.get_troop_schedule(troop)
            if len(troop_entries) < 5:
                print(f"  [WARN] {troop.name} only has {len(troop_entries)} activities")
        
        return True, None
        
    except Exception as e:
        import traceback
        return False, f"{e}\n{traceback.format_exc()}"


def generate_json(troops: list[dict], output_file: Path) -> None:
    """Generate the JSON file from parsed troop data."""
    # Remove internal fields
    clean_troops = []
    for troop in troops:
        clean = {k: v for k, v in troop.items() if not k.startswith("_")}
        clean_troops.append(clean)
    
    data = {"troops": clean_troops}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    print(f"[OK] Generated {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Import/validate week troop data")
    parser.add_argument("--validate", type=str, help="Validate an existing JSON file")
    parser.add_argument("--test-schedule", type=str, help="Test schedule generation for a week")
    parser.add_argument("--import-raw", type=str, help="Import from raw input (reads from stdin)")
    parser.add_argument("--output", type=str, help="Output file for --import-raw")
    
    args = parser.parse_args()
    
    if args.validate:
        filepath = Path(args.validate)
        print(f"\n=== Validating {filepath} ===\n")
        
        is_valid, issues = validate_json_file(filepath)
        
        if issues:
            print("\n[WARN] Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        
        if is_valid:
            print("\n[OK] Validation passed!")
            return 0
        else:
            print("\n[FAIL] Validation failed!")
            return 1
    
    elif args.test_schedule:
        filepath = Path(args.test_schedule)
        print(f"\n=== Testing schedule generation for {filepath} ===\n")
        
        success, error = test_schedule_generation(filepath)
        
        if success:
            print("\n[OK] Schedule generation successful!")
            return 0
        else:
            print(f"\n[FAIL] Schedule generation failed: {error}")
            return 1
    
    elif args.import_raw:
        print(f"\n=== Importing raw data for {args.import_raw} ===")
        print("Paste troop data (tab-separated), then press Ctrl+D (Unix) or Ctrl+Z (Windows):\n")
        
        lines = sys.stdin.readlines()
        troops = parse_raw_input(lines)
        
        print(f"\nParsed {len(troops)} troops:")
        all_unmapped = []
        for troop in troops:
            unmapped = troop.get("_unmapped", [])
            print(f"  - {troop['name']}: {len(troop['preferences'])} preferences")
            if unmapped:
                print(f"    [WARN] Unmapped: {unmapped}")
                all_unmapped.extend(unmapped)
        
        if all_unmapped:
            print(f"\n[WARN] Total unmapped activities: {set(all_unmapped)}")
            print("  These activities will be kept but won't be scheduled.")
        
        output_file = Path(args.output or f"{args.import_raw}_troops.json")
        generate_json(troops, output_file)
        
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
