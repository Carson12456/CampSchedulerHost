#!/usr/bin/env python3
"""
Activity Placement Analyzer
Tracks scheduling decisions and identifies logical errors in activity placement.
"""

import json
from pathlib import Path
from collections import defaultdict
from models import Day, TimeSlot, generate_time_slots, ScheduleEntry, Troop, Schedule
from activities import get_all_activities
from io_handler import load_troops_from_json, load_schedule_from_json
from constrained_scheduler import ConstrainedScheduler

class ActivityPlacementAnalyzer:
    def __init__(self):
        self.activities = get_all_activities()
        self.time_slots = generate_time_slots()
        self.placement_decisions = []
        self.scheduling_issues = []
        
    def analyze_week(self, week_file):
        """Analyze a specific week for placement issues."""
        print(f"\n=== ANALYZING {week_file} ===")
        
        # Load schedule
        troops = load_troops_from_json(week_file)
        week_basename = Path(week_file).stem
        schedule_file = f"schedules/{week_basename}_schedule.json"
        
        with open(schedule_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct schedule
        schedule = Schedule()
        troop_map = {t['name']: Troop(t['name'], t['scouts'], t['adults'], 
                          t.get('campsite', t['name']), t.get('commissioner'),
                          t.get('preferences', []), t.get('day_requests', {})) 
                     for t in data['troops']}
        
        # Create activity map with fallback
        activity_map = {}
        for act in self.activities:
            activity_map[act.name] = act
        
        # Add missing activities as generic ones if needed
        for entry_data in data['entries']:
            activity_name = entry_data['activity_name']
            if activity_name not in activity_map:
                # Create a generic activity for missing ones
                from models import Activity
                activity_map[activity_name] = Activity(activity_name, 1.0, "Unknown", 1, False)
        
        # Create slot map
        slot_map = {}
        for ts in self.time_slots:
            slot_map[(ts.day.name, ts.slot_number)] = ts
        
        for entry_data in data['entries']:
            troop = troop_map[entry_data['troop_name']]
            activity = activity_map[entry_data['activity_name']]
            time_slot = slot_map[(entry_data['day'], entry_data['slot'])]
            if troop and activity and time_slot:
                schedule.entries.append(ScheduleEntry(time_slot, activity, troop))
        
        # Analyze placements
        self._analyze_placement_patterns(troops, schedule, week_basename)
        
    def _analyze_placement_patterns(self, troops, schedule, week_name):
        """Analyze placement patterns for logical issues."""
        print(f"\n--- PLACEMENT ANALYSIS FOR {week_name} ---")
        
        # Track each troop's schedule
        for troop in troops:
            troop_entries = [e for e in schedule.entries if e.troop == troop]
            troop_schedule = {}
            
            # Build schedule matrix
            for entry in troop_entries:
                day = entry.time_slot.day
                slot = entry.time_slot.slot_number
                if day not in troop_schedule:
                    troop_schedule[day] = {}
                troop_schedule[day][slot] = {
                    'activity': entry.activity.name,
                    'priority': troop.get_priority(entry.activity.name),
                    'zone': entry.activity.zone.name if entry.activity.zone else None,
                    'slots': entry.activity.slots
                }
            
            # Check for placement issues
            self._check_troop_placement(troop, troop_schedule)
    
    def _check_troop_placement(self, troop, schedule):
        """Check a single troop's schedule for placement issues."""
        issues = []
        
        # Check high/medium priority activities in suboptimal slots
        for day, day_slots in schedule.items():
            for slot, activity_info in day_slots.items():
                priority = activity_info['priority']
                
                if priority is not None and priority < 10:  # Top 10 activities
                    # Check if this looks like a suboptimal placement
                    issue = self._analyze_suboptimal_placement(troop, day, slot, activity_info, schedule)
                    if issue:
                        issues.append(issue)
        
        # Check multi-slot activity continuity
        self._check_multislot_continuity(troop, schedule, issues)
        
        # Report issues
        if issues:
            print(f"\n[ISSUES] {troop.name} Placement Issues:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print(f"[OK] {troop.name}: No obvious placement issues")
    
    def _analyze_suboptimal_placement(self, troop, day, slot, activity_info, schedule):
        """Analyze if a high-priority activity is in a suboptimal slot."""
        activity = activity_info['activity']
        priority = activity_info['priority']
        
        # Check for obvious issues
        issues = []
        
        # Issue 1: High priority activities on Friday (usually suboptimal)
        if day == Day.FRIDAY and priority < 5:
            # Check if there were better slots available earlier in the week
            better_slots = self._find_better_alternative_slots(troop, activity, schedule, exclude_day=Day.FRIDAY)
            if better_slots:
                issues.append(f"Top {priority+1} '{activity}' on FRIDAY-{slot} (better slots available: {better_slots})")
        
        # Issue 2: Activities that should be clustered but aren't
        if activity in ['Tie Dye', 'Troop Rifle', 'Troop Shotgun'] and self._should_be_clustered(activity, schedule):
            if not self._is_properly_clustered(troop, activity, schedule):
                issues.append(f"'{activity}' not properly clustered with same activity")
        
        # Issue 3: Activities in slots that conflict with their zone preferences
        zone = activity_info['zone']
        if zone and self._has_zone_conflict(activity, day, slot, zone):
            issues.append(f"'{activity}' in {zone} zone with potential conflicts")
        
        return issues[0] if issues else None
    
    def _check_multislot_continuity(self, troop, schedule, issues):
        """Check if multi-slot activities have proper continuity."""
        for day, day_slots in schedule.items():
            # Check for 1.5-slot activities like Sailing
            for slot in [1, 2]:  # Only check slots 1 and 2 for potential 1.5-slot activities
                if slot in day_slots:
                    activity_info = day_slots[slot]
                    activity = activity_info['activity']
                    slots = activity_info['slots']
                    
                    if slots >= 1.5:  # 1.5-slot activity
                        # Should have continuation in next slot
                        next_slot = slot + 1
                        if next_slot in day_slots:
                            next_activity = day_slots[next_slot]['activity']
                            if next_activity != activity:
                                issues.append(f"Multi-slot '{activity}' ({slots} slots) missing continuation in {day.name}-{next_slot}")
                        else:
                            issues.append(f"Multi-slot '{activity}' ({slots} slots) missing continuation slot {day.name}-{next_slot}")
    
    def _find_better_alternative_slots(self, troop, activity, schedule, exclude_day=None):
        """Find better slots that were available for this activity."""
        better_slots = []
        
        for day, day_slots in schedule.items():
            if exclude_day and day == exclude_day:
                continue
                
            for slot in [1, 2, 3]:
                if day == Day.THURSDAY and slot == 3:
                    continue  # Thursday only has 2 slots
                    
                if slot not in day_slots:  # Empty slot
                    # Check if this slot would have been better
                    if self._is_better_slot(day, slot, exclude_day):
                        better_slots.append(f"{day.name[:3]}-{slot}")
        
        return better_slots[:3]  # Return top 3 alternatives
    
    def _is_better_slot(self, day, slot, exclude_day):
        """Determine if a slot is better than the excluded day."""
        if exclude_day == Day.FRIDAY:
            # Any slot Monday-Thursday is better than Friday
            return day != Day.FRIDAY
        return True
    
    def _should_be_clustered(self, activity, schedule):
        """Check if activity should be clustered with same activity."""
        # Count instances of this activity
        count = sum(1 for day_slots in schedule.values() 
                   for slot_info in day_slots.values() 
                   if slot_info['activity'] == activity)
        return count > 1
    
    def _is_properly_clustered(self, troop, activity, schedule):
        """Check if activity is properly clustered."""
        activity_slots = []
        for day, day_slots in schedule.items():
            for slot, slot_info in day_slots.items():
                if slot_info['activity'] == activity:
                    activity_slots.append((day, slot))
        
        if len(activity_slots) <= 1:
            return True  # No clustering needed
        
        # Check if slots are on same day or consecutive days
        days = [day for day, _ in activity_slots]
        days_sorted = sorted(days, key=lambda d: d.value)
        
        # Check if days are consecutive (good clustering)
        for i in range(len(days_sorted) - 1):
            if days_sorted[i + 1].value - days_sorted[i].value > 1:
                return False  # Gap in days
        
        return True
    
    def _has_zone_conflict(self, activity, day, slot, zone):
        """Check if activity has zone conflicts in this slot."""
        # This is a simplified check - could be more sophisticated
        conflicting_zones = {
            'Beach': ['Tower', 'Rifle Range'],  # Wet activities near dry equipment
            'Tower': ['Beach'],  # Tower near beach (logistics)
            'Rifle Range': ['Beach'],  # Range near beach (safety)
        }
        
        return zone in conflicting_zones and any(conflict in conflicting_zones[zone] 
                                           for conflict in conflicting_zones[zone])

def main():
    """Run placement analysis on all weeks."""
    analyzer = ActivityPlacementAnalyzer()
    
    # Find all troop files in current directory
    import glob
    troop_files = glob.glob("*troops.json")
    
    for troop_file in sorted(troop_files):
        try:
            analyzer.analyze_week(troop_file)
        except Exception as e:
            print(f"Error analyzing {troop_file}: {e}")
    
    print(f"\n=== ANALYSIS COMPLETE ===")

if __name__ == "__main__":
    main()
