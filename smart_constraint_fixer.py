#!/usr/bin/env python3
"""
Smart Constraint Fixing System
Implements intelligent constraint violation resolution as outlined in the Spine Final Edition
"""

from typing import List, Dict, Set, Tuple, Optional
from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone, EXCLUSIVE_AREAS
from activities import get_activity_by_name, get_all_activities
from prevention_aware_validator import PreventionValidator
import logging


class SmartConstraintFixer:
    """
    Intelligent constraint violation fixing system.
    Implements smart relocation, intelligent swapping, and conflict resolution.
    """
    
    def __init__(self, schedule: Schedule):
        self.schedule = schedule
        self.logger = logging.getLogger(__name__)
        self.validator = PreventionValidator(schedule)
        
        # Constraint fixing metrics
        self.violations_fixed = 0
        self.fix_attempts = 0
        self.strategy_usage = {
            'relocation': 0,
            'swapping': 0,
            'conflict_resolution': 0,
            'force_fix': 0
        }
        
        # Constraint types and their priorities
        self.constraint_priorities = {
            'beach_slot': 1,  # Highest priority
            'exclusive_area': 2,
            'accuracy_conflict': 3,
            'wet_dry_pattern': 4,
            'capacity': 5,
            'same_day_conflict': 6
        }
    
    def fix_all_violations(self) -> Dict:
        """
        Main constraint fixing method using intelligent strategies.
        Returns comprehensive fixing results.
        """
        self.logger.info("Starting smart constraint fixing...")
        
        # Identify all violations
        violations = self._identify_all_violations()
        self.logger.info(f"Found {len(violations)} constraint violations")
        
        # Sort violations by priority
        violations.sort(key=lambda v: self.constraint_priorities.get(v['type'], 99))
        
        # Fix violations using smart strategies
        for violation in violations:
            self.fix_attempts += 1
            
            if self._fix_violation_with_relocation(violation):
                self.strategy_usage['relocation'] += 1
                self.violations_fixed += 1
            elif self._fix_violation_with_swapping(violation):
                self.strategy_usage['swapping'] += 1
                self.violations_fixed += 1
            elif self._fix_violation_with_conflict_resolution(violation):
                self.strategy_usage['conflict_resolution'] += 1
                self.violations_fixed += 1
            elif self._force_fix_violation(violation):
                self.strategy_usage['force_fix'] += 1
                self.violations_fixed += 1
        
        # Verify fixes
        remaining_violations = self._identify_all_violations()
        
        results = {
            'initial_violations': len(violations),
            'final_violations': len(remaining_violations),
            'violations_fixed': self.violations_fixed,
            'fix_attempts': self.fix_attempts,
            'success_rate': self.violations_fixed / max(1, self.fix_attempts),
            'strategy_usage': self.strategy_usage,
            'remaining_violations': remaining_violations
        }
        
        self.logger.info(f"Constraint fixing complete: {results['violations_fixed']}/{results['initial_violations']} fixed")
        return results
    
    def _identify_all_violations(self) -> List[Dict]:
        """Identify all constraint violations in the schedule."""
        violations = []
        
        for entry in self.schedule.entries:
            # Check beach slot constraint
            if entry.activity.zone == Zone.BEACH and entry.time_slot.slot_number == 2:
                violations.append({
                    'type': 'beach_slot',
                    'entry': entry,
                    'description': f"Beach activity {entry.activity.name} in slot 2",
                    'severity': 'high'
                })
            
            # Check exclusive area constraint
            if entry.activity.zone in EXCLUSIVE_AREAS:
                exclusive_entries = self.schedule.get_exclusive_activities(entry.activity.zone, entry.time_slot)
                if len(exclusive_entries) > 1:
                    violations.append({
                        'type': 'exclusive_area',
                        'entry': entry,
                        'description': f"Multiple activities in exclusive area {entry.activity.zone}",
                        'severity': 'high',
                        'conflicting_entries': [e for e in exclusive_entries if e != entry]
                    })
            
            # Check accuracy conflict constraint
            accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
            if entry.activity.name in accuracy_activities:
                day_activities = self.schedule.get_troop_activities_for_day(entry.troop, entry.time_slot.day)
                accuracy_count = sum(1 for act in day_activities if act.name in accuracy_activities)
                if accuracy_count > 1:
                    violations.append({
                        'type': 'accuracy_conflict',
                        'entry': entry,
                        'description': f"Multiple accuracy activities on {entry.time_slot.day}",
                        'severity': 'medium'
                    })
            
            # Check wet/dry pattern constraint
            wet_activities = ["Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
                             "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel", 
                             "Nature Canoe", "Float for Floats", "Sailing", "Sauna"]
            tower_ods_activities = ["Climbing Tower", "Knots and Lashings", "Orienteering", 
                                   "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"]
            
            if entry.activity.name in wet_activities:
                # Check next slot for Tower/ODS
                next_slot = entry.time_slot.get_next_slot()
                if next_slot:
                    next_entry = self.schedule.get_entry(entry.troop, next_slot)
                    if next_entry and next_entry.activity.name in tower_ods_activities:
                        violations.append({
                            'type': 'wet_dry_pattern',
                            'entry': entry,
                            'description': f"Wet activity {entry.activity.name} followed by Tower/ODS",
                            'severity': 'medium',
                            'conflicting_entry': next_entry
                        })
            
            # Check capacity constraint
            current_count = self.schedule.get_activity_count(entry.activity, entry.time_slot)
            if current_count > entry.activity.capacity:
                violations.append({
                    'type': 'capacity',
                    'entry': entry,
                    'description': f"Activity {entry.activity.name} over capacity ({current_count}/{entry.activity.capacity})",
                    'severity': 'high'
                })
            
            # Check same day conflict constraint
            same_day_conflicts = [
                ("Trading Post", "Campsite Free Time"),
                ("Trading Post", "Shower House"),
                ("Troop Canoe", "Canoe Snorkel"),
                ("Troop Canoe", "Nature Canoe"),
                ("Troop Canoe", "Float for Floats"),
                ("Canoe Snorkel", "Nature Canoe"),
                ("Canoe Snorkel", "Float for Floats"),
                ("Nature Canoe", "Float for Floats"),
            ]
            
            for conflict_pair in same_day_conflicts:
                if entry.activity.name == conflict_pair[0]:
                    day_activities = self.schedule.get_troop_activities_for_day(entry.troop, entry.time_slot.day)
                    conflicting_activities = [act for act in day_activities if act.name == conflict_pair[1]]
                    if conflicting_activities:
                        violations.append({
                            'type': 'same_day_conflict',
                            'entry': entry,
                            'description': f"Same day conflict: {conflict_pair[0]} and {conflict_pair[1]}",
                            'severity': 'medium'
                        })
        
        return violations
    
    def _fix_violation_with_relocation(self, violation: Dict) -> bool:
        """Try to fix violation by relocating the activity to a valid slot."""
        entry = violation['entry']
        
        # Find alternative valid slots
        alternative_slots = self._find_alternative_slots(entry)
        
        for slot in alternative_slots:
            validation = self.validator.comprehensive_prevention_check(entry.troop, entry.activity, slot)
            if validation['valid']:
                # Relocate the entry
                self.schedule.remove_entry(entry)
                new_entry = ScheduleEntry(entry.troop, entry.activity, slot)
                self.schedule.add_entry(new_entry)
                
                self.logger.debug(f"Relocated {entry.activity.name} to {slot} to fix {violation['type']}")
                return True
        
        return False
    
    def _fix_violation_with_swapping(self, violation: Dict) -> bool:
        """Try to fix violation by swapping with another activity."""
        entry = violation['entry']
        
        # Find potential swap candidates
        swap_candidates = self._find_swap_candidates(entry)
        
        for candidate in swap_candidates:
            # Check if swap would resolve the violation
            if self._would_swap_resolve_violation(entry, candidate, violation):
                # Perform the swap
                self._swap_entries(entry, candidate)
                
                self.logger.debug(f"Swapped {entry.activity.name} with {candidate.activity.name} to fix {violation['type']}")
                return True
        
        return False
    
    def _fix_violation_with_conflict_resolution(self, violation: Dict) -> bool:
        """Try to fix violation through intelligent conflict resolution."""
        entry = violation['entry']
        
        if violation['type'] == 'exclusive_area':
            # Try to resolve exclusive area conflict
            conflicting_entries = violation.get('conflicting_entries', [])
            for conflict_entry in conflicting_entries:
                if self._fix_violation_with_relocation({'entry': conflict_entry, 'type': 'exclusive_area'}):
                    return True
        
        elif violation['type'] == 'accuracy_conflict':
            # Try to move one of the accuracy activities to a different day
            day_activities = self.schedule.get_troop_activities_for_day(entry.troop, entry.time_slot.day)
            other_accuracy = [act for act in day_activities if act.name in ["Troop Rifle", "Troop Shotgun", "Archery"] and act != entry.activity.name]
            
            for other_act_name in other_accuracy:
                other_entries = [e for e in self.schedule.entries if e.troop == entry.troop and e.activity.name == other_act_name]
                for other_entry in other_entries:
                    if self._fix_violation_with_relocation({'entry': other_entry, 'type': 'accuracy_conflict'}):
                        return True
        
        elif violation['type'] == 'wet_dry_pattern':
            # Try to resolve wet/dry pattern by moving the wet activity
            conflicting_entry = violation.get('conflicting_entry')
            if conflicting_entry:
                if self._fix_violation_with_relocation({'entry': entry, 'type': 'wet_dry_pattern'}):
                    return True
        
        return False
    
    def _force_fix_violation(self, violation: Dict) -> bool:
        """Force fix violation as last resort."""
        entry = violation['entry']
        
        # Try to find any slot, even with minor violations
        all_slots = self.schedule.get_all_time_slots()
        
        for slot in all_slots:
            if not self.schedule.get_entry(entry.troop, slot):
                # Check if this would be better than current violation
                current_severity = self._get_violation_severity(violation)
                new_violations = self._check_entry_violations(entry.troop, entry.activity, slot)
                new_severity = sum(self._get_violation_severity(v) for v in new_violations)
                
                if new_severity < current_severity:
                    # Force move to better slot
                    self.schedule.remove_entry(entry)
                    new_entry = ScheduleEntry(entry.troop, entry.activity, slot)
                    self.schedule.add_entry(new_entry)
                    
                    self.logger.debug(f"Force moved {entry.activity.name} to {slot} to reduce violation severity")
                    return True
        
        return False
    
    def _find_alternative_slots(self, entry: ScheduleEntry) -> List[TimeSlot]:
        """Find alternative valid slots for an activity."""
        alternative_slots = []
        all_slots = self.schedule.get_all_time_slots()
        
        for slot in all_slots:
            if not self.schedule.get_entry(entry.troop, slot):
                validation = self.validator.comprehensive_prevention_check(entry.troop, entry.activity, slot)
                if validation['valid']:
                    alternative_slots.append(slot)
        
        # Sort by preference (earlier slots, better days, etc.)
        alternative_slots.sort(key=lambda s: (s.day.value, s.slot_number))
        return alternative_slots
    
    def _find_swap_candidates(self, entry: ScheduleEntry) -> List[ScheduleEntry]:
        """Find potential swap candidates for an entry."""
        candidates = []
        
        for other_entry in self.schedule.entries:
            if other_entry.troop == entry.troop and other_entry != entry:
                # Check if swap would be beneficial
                if self._would_swap_benefit(entry, other_entry):
                    candidates.append(other_entry)
        
        return candidates
    
    def _would_swap_resolve_violation(self, entry1: ScheduleEntry, entry2: ScheduleEntry, violation: Dict) -> bool:
        """Check if swapping entries would resolve the violation."""
        # Simulate the swap
        slot1 = entry1.time_slot
        slot2 = entry2.time_slot
        
        # Check if entry1 in slot2 would resolve the violation
        validation1 = self.validator.comprehensive_prevention_check(entry1.troop, entry1.activity, slot2)
        if not validation1['valid']:
            return False
        
        # Check if entry2 in slot1 would be valid
        validation2 = self.validator.comprehensive_prevention_check(entry2.troop, entry2.activity, slot1)
        if not validation2['valid']:
            return False
        
        # Check if the original violation would be resolved
        temp_entry = ScheduleEntry(entry1.troop, entry1.activity, slot2)
        temp_violations = self._check_entry_violations(temp_entry.troop, temp_entry.activity, temp_entry.time_slot)
        
        return not any(v['type'] == violation['type'] for v in temp_violations)
    
    def _would_swap_benefit(self, entry1: ScheduleEntry, entry2: ScheduleEntry) -> bool:
        """Check if swapping entries would be beneficial overall."""
        # Count violations before swap
        violations1_before = self._check_entry_violations(entry1.troop, entry1.activity, entry1.time_slot)
        violations2_before = self._check_entry_violations(entry2.troop, entry2.activity, entry2.time_slot)
        
        # Count violations after swap
        violations1_after = self._check_entry_violations(entry1.troop, entry1.activity, entry2.time_slot)
        violations2_after = self._check_entry_violations(entry2.troop, entry2.activity, entry1.time_slot)
        
        return (len(violations1_after) + len(violations2_after)) < (len(violations1_before) + len(violations2_before))
    
    def _swap_entries(self, entry1: ScheduleEntry, entry2: ScheduleEntry):
        """Swap two schedule entries."""
        # Remove both entries
        self.schedule.remove_entry(entry1)
        self.schedule.remove_entry(entry2)
        
        # Add them back with swapped slots
        new_entry1 = ScheduleEntry(entry1.troop, entry1.activity, entry2.time_slot)
        new_entry2 = ScheduleEntry(entry2.troop, entry2.activity, entry1.time_slot)
        
        self.schedule.add_entry(new_entry1)
        self.schedule.add_entry(new_entry2)
    
    def _check_entry_violations(self, troop: Troop, activity: Activity, time_slot: TimeSlot) -> List[Dict]:
        """Check violations for a specific entry placement."""
        violations = []
        
        # Beach slot constraint
        if activity.zone == Zone.BEACH and time_slot.slot_number == 2:
            violations.append({'type': 'beach_slot', 'severity': 'high'})
        
        # Exclusive area constraint
        if activity.zone in EXCLUSIVE_AREAS:
            exclusive_entries = self.schedule.get_exclusive_activities(activity.zone, time_slot)
            if len(exclusive_entries) > 0:  # Don't count the entry being checked
                violations.append({'type': 'exclusive_area', 'severity': 'high'})
        
        # Accuracy conflict constraint
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        if activity.name in accuracy_activities:
            day_activities = self.schedule.get_troop_activities_for_day(troop, time_slot.day)
            accuracy_count = sum(1 for act in day_activities if act.name in accuracy_activities)
            if accuracy_count > 0:  # Don't count the entry being checked
                violations.append({'type': 'accuracy_conflict', 'severity': 'medium'})
        
        # Wet/dry pattern constraint
        wet_activities = ["Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
                         "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel", 
                         "Nature Canoe", "Float for Floats", "Sailing", "Sauna"]
        tower_ods_activities = ["Climbing Tower", "Knots and Lashings", "Orienteering", 
                               "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"]
        
        if activity.name in wet_activities:
            next_slot = time_slot.get_next_slot()
            if next_slot:
                next_entry = self.schedule.get_entry(troop, next_slot)
                if next_entry and next_entry.activity.name in tower_ods_activities:
                    violations.append({'type': 'wet_dry_pattern', 'severity': 'medium'})
        
        return violations
    
    def _get_violation_severity(self, violation: Dict) -> int:
        """Get numeric severity for a violation."""
        severity_map = {'high': 3, 'medium': 2, 'low': 1}
        return severity_map.get(violation.get('severity', 'low'), 1)
    
    def get_constraint_fixing_metrics(self) -> Dict:
        """Get comprehensive constraint fixing metrics."""
        return {
            'violations_fixed': self.violations_fixed,
            'fix_attempts': self.fix_attempts,
            'success_rate': self.violations_fixed / max(1, self.fix_attempts),
            'strategy_usage': self.strategy_usage,
            'strategy_effectiveness': self._calculate_strategy_effectiveness()
        }
    
    def _calculate_strategy_effectiveness(self) -> Dict:
        """Calculate effectiveness of each fixing strategy."""
        total = max(1, sum(self.strategy_usage.values()))
        return {
            strategy: count / total 
            for strategy, count in self.strategy_usage.items()
        }
