#!/usr/bin/env python3
"""
Prevention-Aware Validation System
Implements comprehensive prevention checks as outlined in the Spine Final Edition
"""

from typing import List, Dict, Set, Tuple, Optional
from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone, EXCLUSIVE_AREAS
from activities import get_activity_by_name
import logging


class PreventionValidator:
    """
    Comprehensive prevention system that validates scheduling decisions before they're made.
    Implements the prevention-first approach from the Spine.
    """
    
    def __init__(self, schedule: Schedule):
        self.schedule = schedule
        self.logger = logging.getLogger(__name__)
        
        # Prevention tracking metrics
        self.awareness_checks = 0
        self.issues_prevented = 0
        self.predictive_violations_prevented = 0
        self.proactive_gaps_filled = 0
        
        # Cache for performance
        self._validation_cache = {}
    
    def comprehensive_prevention_check(self, troop: Troop, activity: Activity, time_slot: TimeSlot) -> Dict:
        """
        Multi-layer validation system that prevents problems before they occur.
        Returns detailed validation result with reasoning.
        """
        self.awareness_checks += 1
        
        result = {
            'valid': True,
            'issues': [],
            'prevented_issues': [],
            'confidence': 1.0,
            'risk_level': 'low'
        }
        
        # Phase 1: Basic availability checks
        basic_result = self._basic_availability_check(troop, activity, time_slot)
        if not basic_result['valid']:
            result['valid'] = False
            result['issues'].extend(basic_result['issues'])
            result['risk_level'] = 'high'
            return result
        
        # Phase 2: Multi-slot compatibility verification
        multi_result = self._multi_slot_compatibility_check(troop, activity, time_slot)
        if not multi_result['valid']:
            result['valid'] = False
            result['issues'].extend(multi_result['issues'])
            result['risk_level'] = 'medium'
        
        # Phase 3: Predictive constraint violation detection
        predictive_result = self._predictive_constraint_check(troop, activity, time_slot)
        if not predictive_result['valid']:
            result['valid'] = False
            result['issues'].extend(predictive_result['issues'])
            result['prevented_issues'].extend(predictive_result['prevented_issues'])
            self.predictive_violations_prevented += len(predictive_result['prevented_issues'])
            result['risk_level'] = 'high'
        
        # Phase 4: Proactive gap creation prevention
        gap_result = self._proactive_gap_prevention_check(troop, activity, time_slot)
        if not gap_result['valid']:
            result['valid'] = False
            result['issues'].extend(gap_result['issues'])
            result['prevented_issues'].extend(gap_result['prevented_issues'])
            self.proactive_gaps_filled += len(gap_result['prevented_issues'])
            result['risk_level'] = 'medium'
        
        # Phase 5: Spine priority compliance verification
        priority_result = self._spine_priority_compliance_check(troop, activity, time_slot)
        if not priority_result['valid']:
            result['valid'] = False
            result['issues'].extend(priority_result['issues'])
            result['risk_level'] = 'medium'
        
        # Calculate overall confidence
        result['confidence'] = max(0.1, 1.0 - (len(result['issues']) * 0.2))
        
        # Track prevented issues
        self.issues_prevented += len(result['prevented_issues'])
        
        return result
    
    def _basic_availability_check(self, troop: Troop, activity: Activity, time_slot: TimeSlot) -> Dict:
        """Phase 1: Basic availability and capacity checks."""
        result = {'valid': True, 'issues': []}
        
        # Check if troop is already scheduled at this time
        existing_entry = self.schedule.get_entry(troop, time_slot)
        if existing_entry:
            result['valid'] = False
            result['issues'].append(f"Troop {troop.name} already scheduled at {time_slot}")
            return result
        
        # Check activity availability
        if not self.schedule.is_activity_available(time_slot, activity, troop):
            result['valid'] = False
            result['issues'].append(f"Activity {activity.name} not available at {time_slot}")
            return result
        
        return result
    
    def _multi_slot_compatibility_check(self, troop: Troop, activity: Activity, time_slot: TimeSlot) -> Dict:
        """Phase 2: Check multi-slot activity compatibility."""
        result = {'valid': True, 'issues': []}
        
        # Check for multi-slot activities
        if hasattr(activity, 'slots') and activity.slots > 1:
            # Verify all required slots are available
            all_slots = self.schedule.get_all_time_slots()
            start_idx = all_slots.index(time_slot)
            
            for offset in range(1, int(activity.slots)):
                if start_idx + offset >= len(all_slots):
                    result['valid'] = False
                    result['issues'].append(f"Multi-slot activity {activity.name} doesn't fit in remaining slots")
                    break
                
                next_slot = all_slots[start_idx + offset]
                if next_slot.day != time_slot.day:
                    result['valid'] = False
                    result['issues'].append(f"Multi-slot activity {activity.name} crosses day boundary")
                    break
                
                existing_entry = self.schedule.get_entry(troop, next_slot)
                if existing_entry:
                    result['valid'] = False
                    result['issues'].append(f"Multi-slot activity {activity.name} conflicts with existing activity at {next_slot}")
                    break
        
        return result
    
    def _predictive_constraint_check(self, troop: Troop, activity: Activity, time_slot: TimeSlot) -> Dict:
        """Phase 3: Predictive constraint violation detection."""
        result = {'valid': True, 'issues': [], 'prevented_issues': []}
        
        # Beach slot constraint prediction
        if hasattr(activity, 'zone') and activity.zone == Zone.BEACH and time_slot.slot_number == 2:
            result['valid'] = False
            result['issues'].append(f"Beach activity {activity.name} cannot be in slot 2")
            result['prevented_issues'].append("Beach slot violation prevented")
        
        # Exclusive area constraint prediction
        if hasattr(activity, 'name'):
            for area, activities in EXCLUSIVE_AREAS.items():
                if activity.name in activities:
                    existing_exclusive = self.schedule.get_exclusive_activities(area, time_slot)
                    if existing_exclusive and not any(act.name == activity.name for act in existing_exclusive):
                        result['valid'] = False
                        result['issues'].append(f"Exclusive area {area} already occupied")
                        result['prevented_issues'].append("Exclusive area conflict prevented")
                    break
        
        # Accuracy activity constraint prediction
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        if activity.name in accuracy_activities:
            day_activities = self.schedule.get_troop_activities_for_day(troop, time_slot.day)
            accuracy_count = sum(1 for act in day_activities if act.name in accuracy_activities)
            if accuracy_count >= 1:
                result['valid'] = False
                result['issues'].append(f"Too many accuracy activities on {time_slot.day}")
                result['prevented_issues'].append("Accuracy activity conflict prevented")
        
        # Wet/Dry pattern prediction
        wet_activities = ["Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
                         "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel", 
                         "Nature Canoe", "Float for Floats", "Sailing", "Sauna"]
        tower_ods_activities = ["Climbing Tower", "Knots and Lashings", "Orienteering", 
                               "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"]
        
        if activity.name in wet_activities:
            # Check next slot for Tower/ODS
            all_slots = self.schedule.get_all_time_slots()
            current_idx = all_slots.index(time_slot)
            if current_idx + 1 < len(all_slots):
                next_slot = all_slots[current_idx + 1]
                if next_slot.day == time_slot.day:
                    next_entry = self.schedule.get_entry(troop, next_slot)
                    if next_entry and next_entry.activity.name in tower_ods_activities:
                        result['valid'] = False
                        result['issues'].append(f"Wet activity {activity.name} cannot be followed by Tower/ODS activity")
                        result['prevented_issues'].append("Wet/Dry pattern violation prevented")
        
        return result
    
    def _proactive_gap_prevention_check(self, troop: Troop, activity: Activity, time_slot: TimeSlot) -> Dict:
        """Phase 4: Prevent gap creation through intelligent analysis."""
        result = {'valid': True, 'issues': [], 'prevented_issues': []}
        
        # Check if this placement would create unavoidable gaps
        remaining_slots = self.schedule.get_remaining_slots_for_troop(troop)
        
        # If this is a long activity and few slots remain, check for gap creation
        if hasattr(activity, 'slots') and activity.slots > 1:
            if len(remaining_slots) < activity.slots + 2:  # Leave buffer
                # Check if there are enough short activities to fill remaining slots
                short_activities_available = self._count_available_short_activities(troop, remaining_slots)
                if short_activities_available < len(remaining_slots) - activity.slots:
                    result['valid'] = False
                    result['issues'].append(f"Placing {activity.name} would create unavoidable gaps")
                    result['prevented_issues'].append("Gap creation prevented")
        
        return result
    
    def _spine_priority_compliance_check(self, troop: Troop, activity: Activity, time_slot: TimeSlot) -> Dict:
        """Phase 5: Ensure compliance with Spine priority hierarchy."""
        result = {'valid': True, 'issues': []}
        
        # Check if this placement violates priority hierarchy
        # CRITICAL: Gap elimination, constraint compliance
        # HIGH: Top 5 preferences, activity requirements
        # MEDIUM: Clustering efficiency, setup optimization
        # LOW: Preference optimization, minor adjustments
        
        # Get troop's top 5 preferences
        top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        
        # If this is not a top 5 preference and critical slots are available, check priority
        if activity.name not in [pref for pref in top5_prefs]:
            # Check if there are critical gaps that should be filled first
            critical_gaps = self._identify_critical_gaps(troop)
            if critical_gaps and time_slot in critical_gaps:
                result['valid'] = False
                result['issues'].append(f"Non-critical activity {activity.name} placed in critical slot")
        
        return result
    
    def _count_available_short_activities(self, troop: Troop, remaining_slots: List[TimeSlot]) -> int:
        """Count available short activities for gap filling."""
        from activities import get_all_activities
        short_activities = []
        for activity in get_all_activities():
            if hasattr(activity, 'slots') and activity.slots == 1:
                # Check if activity can be placed in any remaining slot
                for slot in remaining_slots:
                    if self.comprehensive_prevention_check(troop, activity, slot)['valid']:
                        short_activities.append(activity)
                        break
        return len(short_activities)
    
    def _identify_critical_gaps(self, troop: Troop) -> List[TimeSlot]:
        """Identify critical gaps that should be filled first."""
        critical_gaps = []
        remaining_slots = self.schedule.get_remaining_slots_for_troop(troop)
        
        for slot in remaining_slots:
            # Critical if it's the last available slot for a day
            day_slots = [s for s in remaining_slots if s.day == slot.day]
            if len(day_slots) == 1:
                critical_gaps.append(slot)
            
            # Critical if it's early in the week (higher priority)
            if slot.day.value <= 2:  # Monday/Tuesday
                critical_gaps.append(slot)
        
        return critical_gaps
    
    def get_prevention_metrics(self) -> Dict:
        """Get comprehensive prevention system metrics."""
        return {
            'awareness_checks': self.awareness_checks,
            'issues_prevented': self.issues_prevented,
            'predictive_violations_prevented': self.predictive_violations_prevented,
            'proactive_gaps_filled': self.proactive_gaps_filled,
            'prevention_effectiveness': self.issues_prevented / max(1, self.awareness_checks),
            'average_risk_level': self._calculate_average_risk_level()
        }
    
    def _calculate_average_risk_level(self) -> str:
        """Calculate average risk level across all validations."""
        # This would require tracking risk levels - simplified for now
        if self.issues_prevented > self.awareness_checks * 0.5:
            return 'high'
        elif self.issues_prevented > self.awareness_checks * 0.2:
            return 'medium'
        return 'low'
