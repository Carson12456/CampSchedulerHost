#!/usr/bin/env python3
"""
Restore original schedules to fix web interface lag.
"""

import json
from pathlib import Path

def restore_original_schedules():
    """
    Restore original schedules from backups to fix performance issues.
    """
    print("RESTORING ORIGINAL SCHEDULES")
    print("=" * 35)
    
    schedules_dir = Path("schedules")
    restored_count = 0
    
    # List of backup files to restore
    backup_files = [
        'tc_week1_troops_schedule.json.backup',
        'tc_week2_troops_schedule.json.backup',
        'tc_week3_troops_schedule.json.backup',
        'tc_week4_troops_schedule.json.backup',
        'tc_week5_troops_schedule.json.backup',
        'tc_week6_troops_schedule.json.backup',
        'tc_week7_troops_schedule.json.backup',
        'tc_week8_troops_schedule.json.backup',
        'voyageur_week1_troops_schedule.json.backup',
        'voyageur_week3_troops_schedule.json.backup'
    ]
    
    for backup_file in backup_files:
        backup_path = schedules_dir / backup_file
        original_file = backup_path.with_suffix('')  # Remove .backup
        
        if backup_path.exists():
            print(f"Restoring {original_file.name}...")
            
            # Load backup
            with open(backup_path) as f:
                backup_data = json.load(f)
            
            # Restore original
            with open(original_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            print(f"  Restored {original_file.name}")
            restored_count += 1
        else:
            print(f"Backup not found: {backup_file}")
    
    print(f"\nRestored {restored_count} original schedules")
    print("Web interface should now use the original schedules")
    
    return restored_count

def check_web_performance():
    """
    Check if restoring originals fixes the performance.
    """
    print(f"\n" + "=" * 35)
    print("CHECKING WEB PERFORMANCE")
    print("=" * 35)
    
    # Check tc_week4 as example
    schedule_file = Path("schedules/tc_week4_troops_schedule.json")
    
    if schedule_file.exists():
        with open(schedule_file) as f:
            data = json.load(f)
        
        entries = data.get('entries', [])
        print(f"tc_week4 entries: {len(entries)}")
        print(f"File size: {schedule_file.stat().st_size} bytes")
        
        # Check for any obvious issues
        troop_count = len(set(entry['troop'] for entry in entries))
        print(f"Unique troops: {troop_count}")
        
        # Check if this looks like a normal schedule
        if len(entries) > 200:
            print("WARNING: Schedule has too many entries - may cause lag")
        elif len(entries) < 50:
            print("WARNING: Schedule has too few entries - may be incomplete")
        else:
            print("Schedule size looks normal")
    
    print("\nWeb interface performance tips:")
    print("1. Refresh the browser page (Ctrl+F5)")
    print("2. Clear browser cache")
    print("3. Check browser console for errors")
    print("4. Try a different browser")

if __name__ == "__main__":
    restored = restore_original_schedules()
    if restored > 0:
        check_web_performance()
