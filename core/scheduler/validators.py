"""
Scheduler Validators Module.

Contains methods for validating schedule constraints:
- Critical constraint validation (Reflection, exclusivity, etc.)
- Violation counting and reporting
- Staff variance calculations
- Constraint checking before scheduling
"""

import math
from collections import defaultdict
from ..models import Day
from .constants import SchedulerConstants
from . import config_loader


CLUSTER_AREAS = {
    "Tower": ["Climbing Tower"],
    "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
    "Outdoor Skills": [
        "Knots and Lashings",
        "Orienteering",
        "GPS & Geocaching",
        "Ultimate Survivor",
        "What's Cooking",
        "Chopped!",
    ],
    "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
}


def would_create_excess_day_for_entries(entries, activity_name: str, day: Day) -> bool:
    """Single source-of-truth excess-day rule aligned with BRAIN/regression checker."""
    activity_area = None
    for area_name, activities in CLUSTER_AREAS.items():
        if activity_name in activities:
            activity_area = area_name
            break

    if not activity_area:
        return False

    area_activities = CLUSTER_AREAS[activity_area]
    area_entries = [e for e in entries if e.activity.name in area_activities]
    if not area_entries:
        return False

    current_days = set(e.time_slot.day for e in area_entries)
    if day in current_days:
        return False

    total_activities = len(area_entries)
    new_total = total_activities + 1
    required_days = math.ceil(new_total / 3.0)
    new_days_count = len(current_days) + 1
    return new_days_count > required_days


class ValidatorMixin:
    """
    Mixin class providing validation methods for the scheduler.
    
    These methods check schedule validity and report violations.
    """
    
    # =========================================================================
    # CRITICAL CONSTRAINT VALIDATION
    # =========================================================================
    
    def _final_comprehensive_validation(self):
        """Perform final comprehensive validation of the schedule."""
        print("  [Final Validation] Checking schedule integrity...")
        
        # ALWAYS run gap guarantee - ensures 100% slot completeness (Spine: No Empty Slots)
        gaps = self._comprehensive_gap_check("Final Validation")
        if gaps > 0:
            print(f"    Found {gaps} gaps - fixing...")
        self._guarantee_no_gaps()  # Unconditional: fill any gaps before return
        
        # Check critical constraints
        self._validate_critical_constraints()
        
        print("  [Final Validation] Complete")
    
    def _validate_critical_constraints(self):
        """Validate critical constraints are satisfied."""
        # Check Friday Reflection
        missing_reflection = 0
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries
                if e.troop == troop
            )
            if not has_reflection:
                missing_reflection += 1
                print(f"    WARNING: {troop.name} missing Friday Reflection!")
        
        if missing_reflection > 0:
            print(f"  [CRITICAL] {missing_reflection} troops missing Friday Reflection!")
        else:
            print("  Friday Reflection: All troops OK")
        
        # Check exclusive area violations
        exclusive_violations = self._count_exclusive_area_violations()
        if exclusive_violations > 0:
            print(f"  [CRITICAL] {exclusive_violations} exclusive area violations!")
        else:
            print("  Exclusive areas: No violations")
        
        # Check Super Troop
        missing_super_troop = sum(1 for t in self.troops if not self.troop_has_super_troop.get(t.name, False))
        if missing_super_troop > 0:
            print(f"  [WARNING] {missing_super_troop} troops may be missing Super Troop")
    
    # =========================================================================
    # VIOLATION COUNTING
    # =========================================================================
    
    def _count_violations_by_type(self):
        """Count violations by type for adaptive system."""
        violations = {
            'friday_reflection': self._count_missing_friday_reflection_violations(),
            'exclusive_area': self._count_exclusive_area_violations(),
            'staff_variance': self._calculate_staff_variance(),
            'gaps': 0,  # Will be calculated separately
        }
        
        # Count gaps
        for troop in self.troops:
            for day in Day:
                slots_per_day = 3 if day != Day.THURSDAY else 2
                for slot_num in range(1, slots_per_day + 1):
                    slot = next(
                        (s for s in self.time_slots 
                         if s.day == day and s.slot_number == slot_num),
                        None
                    )
                    if slot and self.schedule.is_troop_free(slot, troop):
                        violations['gaps'] += 1
        
        return violations
    
    def _count_missing_friday_reflection_violations(self):
        """Count Friday Reflection violations."""
        missing = 0
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries
                if e.troop == troop
            )
            if not has_reflection:
                missing += 1
        return missing
    
    def _count_exclusive_area_violations(self):
        """Count exclusive area violations."""
        violations = 0
        
        for slot in self.time_slots:
            # Get all activities in this slot
            slot_entries = [e for e in self.schedule.entries if e.time_slot == slot]
            
            for area_name, area_activities in config_loader.get_exclusive_areas().items():
                # Count how many activities from this area are in the slot
                area_count = sum(
                    1 for e in slot_entries 
                    if e.activity.name in area_activities
                )
                
                # More than 1 = violation (exclusive area allows only 1)
                if area_count > 1:
                    violations += area_count - 1
        
        return violations
    
    def _calculate_staff_variance(self):
        """Calculate staff workload variance."""
        from statistics import variance
        
        # Get staff load per slot
        loads = []
        for slot in self.time_slots:
            loads.append(self.total_staff_by_slot.get(slot, 0))
        
        if len(loads) < 2:
            return 0.0
        
        return variance(loads)
    
    # =========================================================================
    # COMPREHENSIVE GAP CHECK
    # =========================================================================
    
    def _count_troop_empty_slots(self) -> int:
        """
        Count troop-level empty slots (gaps). Used by pipeline for immediate gap fix.
        PlacementAndState/Top5AndSwaps override _comprehensive_gap_check with cluster-gap
        semantics; this method is never overridden and detects actual empty troop slots.
        """
        slots_per_day = {
            Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
            Day.THURSDAY: 2, Day.FRIDAY: 3
        }
        total = 0
        for troop in self.troops:
            for day in Day:
                for slot_num in range(1, slots_per_day[day] + 1):
                    slot = next((s for s in self.time_slots
                                if s.day == day and s.slot_number == slot_num), None)
                    if slot and self.schedule.is_troop_free(slot, troop):
                        total += 1
        return total

    def _comprehensive_gap_check(self, phase_name: str) -> int:
        """Comprehensive gap check to detect gaps early and prevent accumulation.
        
        Returns number of gaps found. If > 0, logs details for debugging.
        """
        slots_per_day = {
            Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
            Day.THURSDAY: 2, Day.FRIDAY: 3
        }
        
        total_gaps = 0
        gap_details = []
        
        for troop in self.troops:
            troop_gaps = []
            
            # Check each day and slot using the actual is_troop_free method
            for day in Day:
                max_slot = slots_per_day[day]
                for slot_num in range(1, max_slot + 1):
                    # Find the TimeSlot object
                    slot = next((s for s in self.time_slots 
                                if s.day == day and s.slot_number == slot_num), None)
                    if slot and self.schedule.is_troop_free(slot, troop):
                        # Troop is free = this is a gap
                        troop_gaps.append(f"{day.name[:3]}-{slot_num}")
                        total_gaps += 1
            
            if troop_gaps:
                gap_details.append(f"{troop.name}: {', '.join(troop_gaps)}")
        
        if total_gaps > 0:
            print(f"  [GAP CHECK] {phase_name}: {total_gaps} gaps detected!")
            for detail in gap_details[:5]:  # Show first 5 troops to avoid spam
                print(f"    {detail}")
            if len(gap_details) > 5:
                print(f"    ... and {len(gap_details) - 5} more troops")
        else:
            print(f"  [GAP CHECK] {phase_name}: No gaps detected [OK]")
        
        return total_gaps
    
    def _immediate_gap_fix_if_needed(self, phase_name: str) -> None:
        """Immediately fix gaps if any are detected after a phase."""
        gaps = self._comprehensive_gap_check(phase_name)
        if gaps > 0:
            print(f"  [IMMEDIATE FIX] Running emergency gap fill after {phase_name}")
            self._guarantee_no_gaps()  # Quick emergency fix
    
    # =========================================================================
    # ACTIVITY SCORING
    # =========================================================================
    
    def _get_activity_score(self, troop, activity, slot, day):
        """
        Calculate score for an activity placement.
        Higher scores = better placement.
        """
        score = 0
        
        # Preference bonus (higher for top preferences)
        priority = troop.get_priority(activity.name)
        if priority < 5:
            score += (5 - priority) * 20  # Top 5: 20-80 bonus
        elif priority < 10:
            score += (10 - priority) * 5  # Top 10: 5-25 bonus
        elif priority < 20:
            score += (20 - priority) * 1  # Top 20: 1-10 bonus
        
        # Clustering bonus (if troop has activities on this day)
        day_counts = self._get_troop_day_activity_counts(troop)
        score += day_counts.get(day, 0) * 5
        
        # Staff balance penalty
        staff_load = self._get_slot_staff_score(slot, activity.name)
        score -= staff_load
        
        return score
    
    # =========================================================================
    # EXCESS DAY CHECK
    # =========================================================================
    
    def _would_create_excess_day(self, activity_name: str, day: Day) -> bool:
        return would_create_excess_day_for_entries(self.schedule.entries, activity_name, day)
