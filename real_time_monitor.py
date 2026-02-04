"""
Real-Time Constraint Violation Monitoring System
Provides continuous monitoring and immediate resolution of scheduling violations
during the scheduling process.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, deque
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ViolationSeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ConstraintViolation:
    """Represents a constraint violation with detailed information."""
    violation_type: str
    severity: ViolationSeverity
    troop: Troop
    activity: Activity
    time_slot: TimeSlot
    description: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False


class RealTimeMonitor:
    """
    Real-time monitoring system for constraint violations during scheduling.
    Provides immediate feedback and automatic resolution capabilities.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Violation tracking
        self.active_violations = []
        self.violation_history = deque(maxlen=1000)  # Keep last 1000 violations
        self.violation_counts = defaultdict(int)
        
        # Constraint definitions
        self.BEACH_SLOT_ACTIVITIES = {
            "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats"
        }
        
        self.WET_ACTIVITIES = {
            "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats", "Sailing", "Sauna"
        }
        
        self.TOWER_ODS_ACTIVITIES = {
            "Climbing Tower", "Knots and Lashings", "Orienteering", "GPS & Geocaching",
            "Ultimate Survivor", "What's Cooking", "Chopped!"
        }
        
        self.MANDATORY_ACTIVITIES = {"Reflection", "Super Troop"}
        
        # Monitoring settings
        self.auto_fix_enabled = True
        self.monitoring_active = False
        self.violation_callbacks = []
        
        # Performance tracking
        self.check_count = 0
        self.total_check_time = 0.0
        self.violations_fixed = 0
    
    def start_monitoring(self):
        """Start real-time monitoring."""
        self.monitoring_active = True
        print("  [Monitor] Real-time constraint monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        self.monitoring_active = False
        print(f"  [Monitor] Monitoring stopped. Checked {self.check_count} entries in {self.total_check_time:.3f}s")
        print(f"  [Monitor] Fixed {self.violations_fixed} violations automatically")
    
    def add_violation_callback(self, callback):
        """Add callback function for violation notifications."""
        self.violation_callbacks.append(callback)
    
    def check_entry(self, entry: ScheduleEntry) -> List[ConstraintViolation]:
        """
        Check a single schedule entry for violations.
        Called in real-time during scheduling.
        """
        if not self.monitoring_active:
            return []
        
        start_time = time.time()
        violations = []
        
        # Check various constraint types
        violations.extend(self._check_beach_slot_violation(entry))
        violations.extend(self._check_wet_dry_violations(entry))
        violations.extend(self._check_mandatory_activity_violations(entry))
        violations.extend(self._check_exclusive_area_violations(entry))
        violations.extend(self._check_activity_conflicts(entry))
        
        # Process violations
        for violation in violations:
            self._process_violation(violation)
        
        # Update performance metrics
        self.check_count += 1
        self.total_check_time += time.time() - start_time
        
        return violations
    
    def check_schedule_comprehensive(self) -> List[ConstraintViolation]:
        """
        Perform comprehensive schedule check.
        Used for validation and reporting.
        """
        all_violations = []
        
        for entry in self.schedule.entries:
            violations = self.check_entry(entry)
            all_violations.extend(violations)
        
        # Additional cross-entry checks
        all_violations.extend(self._check_cross_entry_violations())
        
        return all_violations
    
    def _check_beach_slot_violation(self, entry: ScheduleEntry) -> List[ConstraintViolation]:
        """Check for beach slot constraint violations."""
        violations = []
        
        if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
            entry.time_slot.slot_number == 2 and 
            entry.time_slot.day != Day.THURSDAY):
            
            violation = ConstraintViolation(
                violation_type="beach_slot",
                severity=ViolationSeverity.HIGH,
                troop=entry.troop,
                activity=entry.activity,
                time_slot=entry.time_slot,
                description=f"Beach activity '{entry.activity.name}' scheduled in invalid slot 2",
                suggested_fix="Move to slot 1 or 3",
                auto_fixable=True
            )
            violations.append(violation)
        
        return violations
    
    def _check_wet_dry_violations(self, entry: ScheduleEntry) -> List[ConstraintViolation]:
        """Check for wet/dry pattern violations."""
        violations = []
        
        # Get troop's activities for the same day
        day_entries = [
            e for e in self.schedule.entries 
            if e.troop == entry.troop and e.time_slot.day == entry.time_slot.day
        ]
        
        day_entries.sort(key=lambda e: e.time_slot.slot_number)
        
        # Check adjacent activities
        entry_index = next((i for i, e in enumerate(day_entries) if e == entry), -1)
        
        if entry_index >= 0:
            # Check previous activity
            if entry_index > 0:
                prev_entry = day_entries[entry_index - 1]
                if self._is_wet_dry_conflict(prev_entry.activity.name, entry.activity.name):
                    violations.append(ConstraintViolation(
                        violation_type="wet_dry_pattern",
                        severity=ViolationSeverity.MEDIUM,
                        troop=entry.troop,
                        activity=entry.activity,
                        time_slot=entry.time_slot,
                        description=f"Wet activity '{prev_entry.activity.name}' followed by incompatible activity '{entry.activity.name}'",
                        suggested_fix=f"Move '{entry.activity.name}' to different slot or day",
                        auto_fixable=True
                    ))
            
            # Check next activity
            if entry_index < len(day_entries) - 1:
                next_entry = day_entries[entry_index + 1]
                if self._is_wet_dry_conflict(entry.activity.name, next_entry.activity.name):
                    violations.append(ConstraintViolation(
                        violation_type="wet_dry_pattern",
                        severity=ViolationSeverity.MEDIUM,
                        troop=entry.troop,
                        activity=entry.activity,
                        time_slot=entry.time_slot,
                        description=f"Wet activity '{entry.activity.name}' followed by incompatible activity '{next_entry.activity.name}'",
                        suggested_fix=f"Move '{entry.activity.name}' to different slot or day",
                        auto_fixable=True
                    ))
        
        return violations
    
    def _check_mandatory_activity_violations(self, entry: ScheduleEntry) -> List[ConstraintViolation]:
        """Check for mandatory activity violations."""
        violations = []
        
        # This is more of a completeness check - would need to be done comprehensively
        # For individual entry check, we just track mandatory activities
        
        return violations
    
    def _check_exclusive_area_violations(self, entry: ScheduleEntry) -> List[ConstraintViolation]:
        """Check for exclusive area violations."""
        violations = []
        
        # Define exclusive areas
        exclusive_areas = {
            "Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery",
            "Aqua Trampoline", "Sailing"
        }
        
        if entry.activity.name in exclusive_areas:
            # Check if another troop has the same activity in the same slot
            same_slot_entries = [
                e for e in self.schedule.entries 
                if (e.time_slot == entry.time_slot and 
                    e.activity.name == entry.activity.name and
                    e.troop != entry.troop)
            ]
            
            if same_slot_entries:
                violations.append(ConstraintViolation(
                    violation_type="exclusive_area",
                    severity=ViolationSeverity.CRITICAL,
                    troop=entry.troop,
                    activity=entry.activity,
                    time_slot=entry.time_slot,
                    description=f"Exclusive activity '{entry.activity.name}' scheduled for multiple troops in same slot",
                    suggested_fix="Move to different time slot",
                    auto_fixable=True
                ))
        
        return violations
    
    def _check_activity_conflicts(self, entry: ScheduleEntry) -> List[ConstraintViolation]:
        """Check for activity conflicts."""
        violations = []
        
        # Check if troop has conflicting activities
        troop_entries = [
            e for e in self.schedule.entries 
            if e.troop == entry.troop and e != entry
        ]
        
        for other_entry in troop_entries:
            if other_entry.time_slot == entry.time_slot:
                violations.append(ConstraintViolation(
                    violation_type="activity_conflict",
                    severity=ViolationSeverity.CRITICAL,
                    troop=entry.troop,
                    activity=entry.activity,
                    time_slot=entry.time_slot,
                    description=f"Troop scheduled for multiple activities in same slot",
                    suggested_fix="Remove one of the conflicting activities",
                    auto_fixable=True
                ))
        
        return violations
    
    def _check_cross_entry_violations(self) -> List[ConstraintViolation]:
        """Check violations that require cross-entry analysis."""
        violations = []
        
        # Check Friday Reflection completeness
        violations.extend(self._check_friday_reflection_completeness())
        
        # Check staff overload
        violations.extend(self._check_staff_overload())
        
        return violations
    
    def _check_friday_reflection_completeness(self) -> List[ConstraintViolation]:
        """Check if all troops have Friday Reflection."""
        violations = []
        
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries if e.troop == troop
            )
            
            if not has_reflection:
                violations.append(ConstraintViolation(
                    violation_type="missing_reflection",
                    severity=ViolationSeverity.HIGH,
                    troop=troop,
                    activity=None,
                    time_slot=None,
                    description=f"Troop '{troop.name}' missing mandatory Friday Reflection",
                    suggested_fix="Schedule Reflection on Friday",
                    auto_fixable=True
                ))
        
        return violations
    
    def _check_staff_overload(self) -> List[ConstraintViolation]:
        """Check for staff overload in time slots."""
        violations = []
        
        # Count staff-requiring activities per slot
        slot_counts = defaultdict(int)
        slot_entries = defaultdict(list)
        
        for entry in self.schedule.entries:
            activity_name = entry.activity.name
            if self._requires_staff(activity_name):
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                slot_counts[slot_key] += 1
                slot_entries[slot_key].append(entry)
        
        # Check for overloaded slots (more than 15 staff)
        for slot_key, count in slot_counts.items():
            if count > 15:
                day, slot_num = slot_key
                violations.append(ConstraintViolation(
                    violation_type="staff_overload",
                    severity=ViolationSeverity.MEDIUM,
                    troop=None,
                    activity=None,
                    time_slot=TimeSlot(day, slot_num),
                    description=f"Staff overload: {count} activities in slot (limit: 15)",
                    suggested_fix="Move some activities to different slots",
                    auto_fixable=False  # Requires complex optimization
                ))
        
        return violations
    
    def _is_wet_dry_conflict(self, activity1: str, activity2: str) -> bool:
        """Check if two activities have wet/dry conflict."""
        wet1 = activity1 in self.WET_ACTIVITIES
        wet2 = activity2 in self.WET_ACTIVITIES
        tower_ods1 = activity1 in self.TOWER_ODS_ACTIVITIES
        tower_ods2 = activity2 in self.TOWER_ODS_ACTIVITIES
        
        return (wet1 and tower_ods2) or (tower_ods1 and wet2)
    
    def _requires_staff(self, activity_name: str) -> bool:
        """Check if activity requires staff."""
        staff_activities = {
            'Climbing Tower', 'Troop Rifle', 'Troop Shotgun', 'Archery',
            'Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
            'Ultimate Survivor', "What's Cooking", 'Chopped!',
            'Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide',
            "Monkey's Fist", 'Aqua Trampoline', 'Troop Canoe', 'Troop Kayak',
            'Canoe Snorkel', 'Float for Floats', 'Greased Watermelon',
            'Underwater Obstacle Course', 'Troop Swim', 'Water Polo',
            'Nature Canoe', 'Sailing'
        }
        return activity_name in staff_activities
    
    def _process_violation(self, violation: ConstraintViolation):
        """Process a detected violation."""
        # Add to tracking
        self.active_violations.append(violation)
        self.violation_history.append(violation)
        self.violation_counts[violation.violation_type] += 1
        
        # Notify callbacks
        for callback in self.violation_callbacks:
            try:
                callback(violation)
            except Exception as e:
                print(f"  [Monitor] Callback error: {e}")
        
        # Auto-fix if enabled and possible
        if self.auto_fix_enabled and violation.auto_fixable:
            if self._auto_fix_violation(violation):
                self.violations_fixed += 1
                print(f"  [Monitor] Auto-fixed: {violation.description}")
    
    def _auto_fix_violation(self, violation: ConstraintViolation) -> bool:
        """Attempt to automatically fix a violation."""
        try:
            if violation.violation_type == "beach_slot":
                return self._fix_beach_slot_violation(violation)
            elif violation.violation_type == "wet_dry_pattern":
                return self._fix_wet_dry_violation(violation)
            elif violation.violation_type == "missing_reflection":
                return self._fix_missing_reflection(violation)
            elif violation.violation_type == "exclusive_area":
                return self._fix_exclusive_area_violation(violation)
            elif violation.violation_type == "activity_conflict":
                return self._fix_activity_conflict(violation)
        except Exception as e:
            print(f"  [Monitor] Auto-fix failed: {e}")
        
        return False
    
    def _fix_beach_slot_violation(self, violation: ConstraintViolation) -> bool:
        """Fix beach slot violation by moving to valid slot."""
        if not violation.activity or not violation.time_slot:
            return False
        
        # Try to move to slot 1 or 3
        for target_slot in [1, 3]:
            if target_slot > 2 and violation.time_slot.day == Day.THURSDAY:
                continue
            
            new_time_slot = TimeSlot(violation.time_slot.day, target_slot)
            
            if (self.schedule.is_troop_free(new_time_slot, violation.troop) and
                self.schedule.is_activity_available(new_time_slot, violation.activity, violation.troop)):
                
                # Find and remove old entry
                old_entry = None
                for entry in self.schedule.entries:
                    if (entry.troop == violation.troop and 
                        entry.activity == violation.activity and
                        entry.time_slot == violation.time_slot):
                        old_entry = entry
                        break
                
                if old_entry:
                    self.schedule.remove_entry(old_entry)
                    self.schedule.add_entry(new_time_slot, violation.activity, violation.troop)
                    return True
        
        return False
    
    def _fix_wet_dry_violation(self, violation: ConstraintViolation) -> bool:
        """Fix wet/dry violation by moving activity."""
        # This is complex - for now, just report
        return False
    
    def _fix_missing_reflection(self, violation: ConstraintViolation) -> bool:
        """Fix missing Friday Reflection."""
        reflection = self.activities.get("Reflection")
        if not reflection:
            return False
        
        # Find available Friday slot
        for slot_num in [1, 2, 3]:
            friday_slot = TimeSlot(Day.FRIDAY, slot_num)
            
            if (self.schedule.is_troop_free(friday_slot, violation.troop) and
                self.schedule.is_activity_available(friday_slot, reflection, violation.troop)):
                
                self.schedule.add_entry(friday_slot, reflection, violation.troop)
                return True
        
        return False
    
    def _fix_exclusive_area_violation(self, violation: ConstraintViolation) -> bool:
        """Fix exclusive area violation."""
        # Find alternative slot for one of the conflicting entries
        conflicting_entries = [
            e for e in self.schedule.entries 
            if (e.time_slot == violation.time_slot and 
                e.activity.name == violation.activity.name)
        ]
        
        if len(conflicting_entries) >= 2:
            # Try to move the second entry
            entry_to_move = conflicting_entries[1]
            
            for slot in self._generate_all_slots():
                if (slot != violation.time_slot and
                    self.schedule.is_troop_free(slot, entry_to_move.troop) and
                    self.schedule.is_activity_available(slot, entry_to_move.activity, entry_to_move.troop)):
                    
                    self.schedule.remove_entry(entry_to_move)
                    self.schedule.add_entry(slot, entry_to_move.activity, entry_to_move.troop)
                    return True
        
        return False
    
    def _fix_activity_conflict(self, violation: ConstraintViolation) -> bool:
        """Fix activity conflict by removing one entry."""
        # Find conflicting entries
        conflicting_entries = [
            e for e in self.schedule.entries 
            if (e.troop == violation.troop and 
                e.time_slot == violation.time_slot)
        ]
        
        if len(conflicting_entries) >= 2:
            # Remove the lower priority entry
            conflicting_entries.sort(key=lambda e: self._get_activity_priority(e.activity.name))
            self.schedule.remove_entry(conflicting_entries[0])
            return True
        
        return False
    
    def _get_activity_priority(self, activity_name: str) -> int:
        """Get activity priority for conflict resolution."""
        # Lower number = higher priority
        priority_map = {
            "Reflection": 1,
            "Super Troop": 2,
            "Climbing Tower": 3,
            "Sailing": 4,
            "Aqua Trampoline": 5,
        }
        return priority_map.get(activity_name, 999)
    
    def _generate_all_slots(self):
        """Generate all possible time slots."""
        slots = []
        for day in Day:
            max_slot = 2 if day == Day.THURSDAY else 3
            for slot_num in range(1, max_slot + 1):
                slots.append(TimeSlot(day, slot_num))
        return slots
    
    def get_violation_summary(self) -> Dict:
        """Get summary of current violations."""
        return {
            'total_violations': len(self.active_violations),
            'violations_by_type': dict(self.violation_counts),
            'auto_fix_enabled': self.auto_fix_enabled,
            'violations_fixed': self.violations_fixed,
            'monitoring_active': self.monitoring_active,
            'performance': {
                'checks_performed': self.check_count,
                'total_check_time': self.total_check_time,
                'avg_check_time': self.total_check_time / max(1, self.check_count)
            }
        }
    
    def clear_violations(self):
        """Clear all active violations."""
        self.active_violations.clear()
        print("  [Monitor] Violations cleared")


def create_real_time_monitor(schedule, troops, activities):
    """
    Create and configure a real-time monitoring system.
    """
    monitor = RealTimeMonitor(schedule, troops, activities)
    
    # Add default violation callback
    def default_callback(violation):
        severity_symbol = {
            ViolationSeverity.LOW: "YELLOW",
            ViolationSeverity.MEDIUM: "ORANGE", 
            ViolationSeverity.HIGH: "RED",
            ViolationSeverity.CRITICAL: "CRITICAL"
        }
        
        symbol = severity_symbol.get(violation.severity, "UNKNOWN")
        print(f"  [{symbol}] {violation.description}")
    
    monitor.add_violation_callback(default_callback)
    
    return monitor
