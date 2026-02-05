"""
Constraint Validation for Summer Camp Scheduler.

Provides centralized constraint checking and violation counting.
This module is step 1 of decomposing the God Object - focusing on
READ-ONLY validation logic that doesn't modify the schedule.
"""
from collections import defaultdict
from typing import Dict, List, Set, Any, TYPE_CHECKING

from core.scheduler.config_loader import (
    get_exclusive_areas,
    get_prohibited_pairs,
    are_activities_prohibited_together,
)

if TYPE_CHECKING:
    from core.models import Schedule, Troop, Day, TimeSlot


# === Activity Categories (to be migrated to SKULL.json in Phase 2.4) ===

BEACH_SLOT_ACTIVITIES = {
    "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
    "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
    "Nature Canoe", "Float for Floats"
}

WET_ACTIVITIES = {
    "Swimming", "Canoeing", "Kayaking", "Sailing", "Aqua Trampoline",
    "Canoe Snorkel", "Water Polo", "Troop Canoe", "Troop Swim",
    "Troop Kayak", "Nature Canoe", "Float for Floats", "Greased Watermelon",
    "Underwater Obstacle Course"
}

ACCURACY_ACTIVITIES = {"Archery", "Troop Rifle", "Troop Shotgun"}

TOWER_ODS_ACTIVITIES = {
    "Climbing Tower", "Knots and Lashings", "Orienteering", 
    "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"
}


class ConstraintValidator:
    """
    Validates schedule constraints without modifying the schedule.
    
    Use this for:
    - Counting violations by type
    - Checking if a placement is valid
    - Generating validation reports
    
    Does NOT modify the schedule. Fixing violations is handled by ConstrainedScheduler.
    """
    
    def __init__(self, schedule: 'Schedule', troops: List['Troop']):
        self.schedule = schedule
        self.troops = troops
    
    # === Violation Counting ===
    
    def count_beach_slot_violations(self) -> int:
        """Count beach activities in slot 2 (except Thursday) that aren't Top-5 protected."""
        from core.models import Day
        violations = 0
        
        for entry in self.schedule.entries:
            if not (hasattr(entry, 'time_slot') and hasattr(entry.time_slot, 'slot_number')):
                continue
            
            if (entry.activity.name in BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.slot_number == 2 and 
                entry.time_slot.day != Day.THURSDAY):
                
                troop = entry.troop
                pref_rank = troop.get_priority(entry.activity.name) if hasattr(troop, 'get_priority') else None
                
                # Top 5 exception (penalty still applies but not counted as violation)
                if pref_rank is not None and pref_rank < 5:
                    continue
                
                violations += 1
        
        return violations
    
    def count_friday_reflection_missing(self) -> int:
        """Count troops missing Friday Reflection."""
        from core.models import Day
        missing = 0
        
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries if e.troop == troop
            )
            if not has_reflection:
                missing += 1
        
        return missing
    
    def count_wet_dry_wet_violations(self) -> int:
        """Count wet-dry-wet pattern violations (3 slots: wet, then dry, then wet)."""
        from core.models import Day
        violations = 0
        
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            
            for day in Day:
                day_entries = sorted(
                    [e for e in troop_entries if e.time_slot.day == day],
                    key=lambda e: e.time_slot.slot_number
                )
                
                if len(day_entries) < 3:
                    continue
                
                # Build wet pattern: [True, False, True] = violation
                pattern = [e.activity.name in WET_ACTIVITIES for e in day_entries]
                
                for i in range(len(pattern) - 2):
                    if pattern[i] and not pattern[i+1] and pattern[i+2]:
                        violations += 1
        
        return violations
    
    def count_same_area_same_day_violations(self) -> int:
        """Count troops with multiple activities from same exclusive area on same day."""
        from core.models import Day
        violations = 0
        exclusive_areas = get_exclusive_areas()
        
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            
            for day in Day:
                day_entries = [e for e in troop_entries if e.time_slot.day == day]
                
                for area, activities in exclusive_areas.items():
                    area_count = sum(1 for e in day_entries if e.activity.name in activities)
                    if area_count >= 2:
                        violations += 1
        
        return violations
    
    def count_accuracy_conflicts(self) -> int:
        """Count troops with multiple accuracy activities (Archery/Rifle/Shotgun) same day."""
        from core.models import Day
        violations = 0
        
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            
            for day in Day:
                day_entries = [e for e in troop_entries if e.time_slot.day == day]
                accuracy_count = sum(1 for e in day_entries if e.activity.name in ACCURACY_ACTIVITIES)
                
                if accuracy_count >= 2:
                    violations += 1
        
        return violations
    
    def count_prohibited_pairs_violations(self) -> int:
        """Count same-day conflicts for prohibited activity pairs."""
        from core.models import Day
        violations = 0
        
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            
            for day in Day:
                day_activities = {e.activity.name for e in troop_entries if e.time_slot.day == day}
                
                for pair in get_prohibited_pairs():
                    if pair[0] in day_activities and pair[1] in day_activities:
                        violations += 1
        
        return violations
    
    # === Summary Report ===
    
    def get_violation_summary(self) -> Dict[str, int]:
        """Get a complete summary of all constraint violations."""
        return {
            "beach_slot_violations": self.count_beach_slot_violations(),
            "friday_reflection_missing": self.count_friday_reflection_missing(),
            "wet_dry_wet_patterns": self.count_wet_dry_wet_violations(),
            "same_area_same_day": self.count_same_area_same_day_violations(),
            "accuracy_conflicts": self.count_accuracy_conflicts(),
            "prohibited_pairs": self.count_prohibited_pairs_violations(),
        }
    
    def get_total_violations(self) -> int:
        """Get total count of all violations."""
        return sum(self.get_violation_summary().values())
    
    def print_validation_report(self) -> None:
        """Print a human-readable validation report."""
        summary = self.get_violation_summary()
        total = sum(summary.values())
        
        print("\n--- Constraint Validation Report ---")
        for constraint, count in summary.items():
            status = "[OK]" if count == 0 else f"[WARNING: {count}]"
            print(f"  {constraint}: {status}")
        print(f"  TOTAL VIOLATIONS: {total}")
        print("-----------------------------------\n")
