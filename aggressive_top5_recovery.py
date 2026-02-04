#!/usr/bin/env python3
"""
Aggressive Top 5 Recovery System
Implements aggressive recovery of Top 5 preferences as outlined in the Spine Final Edition
"""

from typing import List, Dict, Set, Tuple, Optional
from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone
from activities import get_activity_by_name, get_all_activities
from prevention_aware_validator import PreventionValidator
import logging


class AggressiveTop5Recovery:
    """
    Aggressive Top 5 preference recovery system.
    Implements three-phase approach: Intelligent swaps → Force placement → Emergency placement.
    """
    
    def __init__(self, schedule: Schedule):
        self.schedule = schedule
        self.logger = logging.getLogger(__name__)
        self.validator = PreventionValidator(schedule)
        
        # Top 5 recovery metrics
        self.top5_recovered = 0
        self.force_placements = 0
        self.emergency_placements = 0
        self.violations_created = 0
        
        # Recovery strategy tracking
        self.strategy_usage = {
            'intelligent_swap': 0,
            'force_placement': 0,
            'emergency_placement': 0
        }
        
        # Detailed tracking
        self.recovery_details = []
        self.missed_preferences = []
    
    def recover_all_top5(self) -> Dict:
        """
        Main Top 5 recovery method using aggressive strategies.
        Returns comprehensive recovery results.
        """
        self.logger.info("Starting aggressive Top 5 recovery...")
        
        # Identify all missing Top 5 preferences
        missing_top5 = self._identify_missing_top5()
        self.logger.info(f"Found {len(missing_top5)} missing Top 5 preferences")
        
        # Phase 1: Intelligent swaps
        intelligent_results = self._intelligent_swap_phase(missing_top5)
        self.strategy_usage['intelligent_swap'] = intelligent_results['recovered']
        self.top5_recovered += intelligent_results['recovered']
        
        # Update remaining missing preferences
        remaining_missing = [pref for pref in missing_top5 if not pref.get('recovered', False)]
        
        # Phase 2: Force placement
        force_results = self._force_placement_phase(remaining_missing)
        self.strategy_usage['force_placement'] = force_results['recovered']
        self.top5_recovered += force_results['recovered']
        self.force_placements += force_results['recovered']
        self.violations_created += force_results['violations_created']
        
        # Update remaining missing preferences
        still_missing = [pref for pref in remaining_missing if not pref.get('recovered', False)]
        
        # Phase 3: Emergency placement
        emergency_results = self._emergency_placement_phase(still_missing)
        self.strategy_usage['emergency_placement'] = emergency_results['recovered']
        self.top5_recovered += emergency_results['recovered']
        self.emergency_placements += emergency_results['recovered']
        self.violations_created += emergency_results['violations_created']
        
        # Final analysis
        final_missing = [pref for pref in still_missing if not pref.get('recovered', False)]
        self.missed_preferences = final_missing
        
        results = {
            'initial_missing': len(missing_top5),
            'final_missing': len(final_missing),
            'total_recovered': self.top5_recovered,
            'recovery_rate': self.top5_recovered / max(1, len(missing_top5)),
            'strategy_usage': self.strategy_usage,
            'violations_created': self.violations_created,
            'force_placements': self.force_placements,
            'emergency_placements': self.emergency_placements,
            'recovery_details': self.recovery_details,
            'missed_preferences': self.missed_preferences
        }
        
        self.logger.info(f"Top 5 recovery complete: {results['total_recovered']}/{results['initial_missing']} recovered")
        return results
    
    def _identify_missing_top5(self) -> List[Dict]:
        """Identify all missing Top 5 preferences for all troops."""
        missing_top5 = []
        
        for troop in self.schedule.troops:
            top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            troop_activities = self.schedule.get_troop_activities(troop)
            troop_activity_names = [act.name for act in troop_activities]
            
            for i, pref in enumerate(top5_prefs):
                if pref.name not in troop_activity_names:
                    # Check if activity is available in the schedule
                    activity = get_activity_by_name(pref.name)
                    if activity:
                        missing_top5.append({
                            'troop': troop,
                            'activity': activity,
                            'preference_rank': i + 1,
                            'recovered': False,
                            'recovery_method': None,
                            'violations': []
                        })
        
        return missing_top5
    
    def _intelligent_swap_phase(self, missing_top5: List[Dict]) -> Dict:
        """Phase 1: Intelligent swapping to make room for Top 5 preferences."""
        results = {'recovered': 0, 'details': []}
        
        for pref_info in missing_top5:
            if pref_info.get('recovered', False):
                continue
            
            troop = pref_info['troop']
            activity = pref_info['activity']
            
            # Find potential swap candidates
            swap_candidates = self._find_top5_swap_candidates(troop, activity)
            
            for candidate in swap_candidates:
                if self._perform_intelligent_swap(troop, activity, candidate):
                    pref_info['recovered'] = True
                    pref_info['recovery_method'] = 'intelligent_swap'
                    results['recovered'] += 1
                    results['details'].append({
                        'troop': troop.name,
                        'activity': activity.name,
                        'method': 'intelligent_swap',
                        'displaced_activity': candidate.activity.name
                    })
                    self.recovery_details.append(results['details'][-1])
                    break
        
        self.logger.info(f"Intelligent swap phase recovered {results['recovered']} Top 5 preferences")
        return results
    
    def _force_placement_phase(self, missing_top5: List[Dict]) -> Dict:
        """Phase 2: Force placement of Top 5 preferences with constraint awareness."""
        results = {'recovered': 0, 'violations_created': 0, 'details': []}
        
        for pref_info in missing_top5:
            if pref_info.get('recovered', False):
                continue
            
            troop = pref_info['troop']
            activity = pref_info['activity']
            
            # Find best slot for force placement
            best_slot = self._find_best_force_placement_slot(troop, activity)
            
            if best_slot:
                # Remove lower-priority activity if necessary
                displaced_entry = self._remove_lower_priority_activity(troop, best_slot)
                
                # Place the Top 5 activity
                entry = ScheduleEntry(troop, activity, best_slot)
                self.schedule.add_entry(entry)
                
                # Check for violations
                validation = self.validator.comprehensive_prevention_check(troop, activity, best_slot)
                violations = validation['issues'] if not validation['valid'] else []
                
                pref_info['recovered'] = True
                pref_info['recovery_method'] = 'force_placement'
                pref_info['violations'] = violations
                results['recovered'] += 1
                results['violations_created'] += len(violations)
                results['details'].append({
                    'troop': troop.name,
                    'activity': activity.name,
                    'method': 'force_placement',
                    'slot': str(best_slot),
                    'displaced_activity': displaced_entry.activity.name if displaced_entry else None,
                    'violations': violations
                })
                self.recovery_details.append(results['details'][-1])
        
        self.logger.info(f"Force placement phase recovered {results['recovered']} Top 5 preferences with {results['violations_created']} violations")
        return results
    
    def _emergency_placement_phase(self, missing_top5: List[Dict]) -> Dict:
        """Phase 3: Emergency placement as last resort."""
        results = {'recovered': 0, 'violations_created': 0, 'details': []}
        
        for pref_info in missing_top5:
            if pref_info.get('recovered', False):
                continue
            
            troop = pref_info['troop']
            activity = pref_info['activity']
            
            # Find any available slot, even with major violations
            emergency_slot = self._find_emergency_placement_slot(troop, activity)
            
            if emergency_slot:
                # Force place regardless of violations
                entry = ScheduleEntry(troop, activity, emergency_slot)
                self.schedule.add_entry(entry)
                
                # Check for violations
                validation = self.validator.comprehensive_prevention_check(troop, activity, emergency_slot)
                violations = validation['issues'] if not validation['valid'] else []
                
                pref_info['recovered'] = True
                pref_info['recovery_method'] = 'emergency_placement'
                pref_info['violations'] = violations
                results['recovered'] += 1
                results['violations_created'] += len(violations)
                results['details'].append({
                    'troop': troop.name,
                    'activity': activity.name,
                    'method': 'emergency_placement',
                    'slot': str(emergency_slot),
                    'violations': violations
                })
                self.recovery_details.append(results['details'][-1])
        
        self.logger.info(f"Emergency placement phase recovered {results['recovered']} Top 5 preferences with {results['violations_created']} violations")
        return results
    
    def _find_top5_swap_candidates(self, troop: Troop, target_activity: Activity) -> List[ScheduleEntry]:
        """Find potential swap candidates for Top 5 placement."""
        candidates = []
        troop_entries = self.schedule.get_troop_entries(troop)
        
        for entry in troop_entries:
            if self._can_swap_for_top5(entry, target_activity):
                candidates.append(entry)
        
        # Sort by swap priority (lower priority activities first)
        candidates.sort(key=lambda e: self._get_swap_priority(e, target_activity))
        return candidates
    
    def _can_swap_for_top5(self, entry: ScheduleEntry, target_activity: Activity) -> bool:
        """Check if an entry can be swapped for a Top 5 activity."""
        # Don't swap other Top 5 activities
        troop_prefs = entry.troop.preferences[:5]
        if entry.activity.name in [pref.name for pref in troop_prefs]:
            return False
        
        # Don't swap if target activity is already placed
        troop_activities = self.schedule.get_troop_activities(entry.troop)
        if target_activity in troop_activities:
            return False
        
        return True
    
    def _get_swap_priority(self, entry: ScheduleEntry, target_activity: Activity) -> int:
        """Get swap priority (lower number = better swap candidate)."""
        # Basic activities are easiest to swap
        basic_activities = ["Campsite Free Time", "Gaga Ball", "9 Square", "Troop Swim", "Fishing"]
        if entry.activity.name in basic_activities:
            return 1
        
        # Standard activities
        standard_activities = ["Archery", "Sailing", "Water Polo", "Trading Post", "Shower House"]
        if entry.activity.name in standard_activities:
            return 2
        
        # High-value activities
        high_value_activities = ["Super Troop", "Delta", "Climbing Tower", "Aqua Trampoline"]
        if entry.activity.name in high_value_activities:
            return 3
        
        return 4
    
    def _perform_intelligent_swap(self, troop: Troop, target_activity: Activity, candidate: ScheduleEntry) -> bool:
        """Perform an intelligent swap to place Top 5 activity."""
        # Try to move the candidate activity to a different slot
        alternative_slots = self._find_alternative_slots_for_activity(candidate)
        
        for slot in alternative_slots:
            validation = self.validator.comprehensive_prevention_check(troop, candidate.activity, slot)
            if validation['valid']:
                # Move the candidate activity
                self.schedule.remove_entry(candidate)
                new_candidate_entry = ScheduleEntry(troop, candidate.activity, slot)
                self.schedule.add_entry(new_candidate_entry)
                
                # Place the Top 5 activity in the freed slot
                top5_entry = ScheduleEntry(troop, target_activity, candidate.time_slot)
                self.schedule.add_entry(top5_entry)
                
                return True
        
        return False
    
    def _find_best_force_placement_slot(self, troop: Troop, activity: Activity) -> Optional[TimeSlot]:
        """Find the best slot for force placement."""
        available_slots = self.schedule.get_remaining_slots_for_troop(troop)
        
        if not available_slots:
            # No available slots, need to displace something
            return self._find_best_displacement_slot(troop, activity)
        
        # Find the slot with minimum violations
        best_slot = None
        min_violations = float('inf')
        
        for slot in available_slots:
            validation = self.validator.comprehensive_prevention_check(troop, activity, slot)
            violation_count = len(validation['issues'])
            
            if violation_count < min_violations:
                min_violations = violation_count
                best_slot = slot
        
        return best_slot
    
    def _find_emergency_placement_slot(self, troop: Troop, activity: Activity) -> Optional[TimeSlot]:
        """Find any slot for emergency placement."""
        all_slots = self.schedule.get_all_time_slots()
        
        for slot in all_slots:
            existing_entry = self.schedule.get_entry(troop, slot)
            if not existing_entry:
                return slot
        
        # If no empty slots, find the least harmful slot to displace
        return self._find_emergency_displacement_slot(troop, activity)
    
    def _find_alternative_slots_for_activity(self, entry: ScheduleEntry) -> List[TimeSlot]:
        """Find alternative slots for an activity."""
        alternative_slots = []
        available_slots = self.schedule.get_remaining_slots_for_troop(entry.troop)
        
        for slot in available_slots:
            validation = self.validator.comprehensive_prevention_check(entry.troop, entry.activity, slot)
            if validation['valid']:
                alternative_slots.append(slot)
        
        return alternative_slots
    
    def _find_best_displacement_slot(self, troop: Troop, activity: Activity) -> Optional[TimeSlot]:
        """Find the best slot to displace for force placement."""
        troop_entries = self.schedule.get_troop_entries(troop)
        
        best_entry = None
        min_priority = float('inf')
        
        for entry in troop_entries:
            priority = self._get_displacement_priority(entry, activity)
            if priority < min_priority:
                min_priority = priority
                best_entry = entry
        
        return best_entry.time_slot if best_entry else None
    
    def _find_emergency_displacement_slot(self, troop: Troop, activity: Activity) -> Optional[TimeSlot]:
        """Find any slot to displace for emergency placement."""
        troop_entries = self.schedule.get_troop_entries(troop)
        return troop_entries[0].time_slot if troop_entries else None
    
    def _get_displacement_priority(self, entry: ScheduleEntry, target_activity: Activity) -> int:
        """Get displacement priority for an entry."""
        # Don't displace other Top 5 activities
        troop_prefs = entry.troop.preferences[:5]
        if entry.activity.name in [pref.name for pref in troop_prefs]:
            return 100  # Very high priority (don't displace)
        
        # Basic activities are easiest to displace
        basic_activities = ["Campsite Free Time", "Gaga Ball", "9 Square", "Troop Swim", "Fishing"]
        if entry.activity.name in basic_activities:
            return 1
        
        # Standard activities
        standard_activities = ["Archery", "Sailing", "Water Polo", "Trading Post", "Shower House"]
        if entry.activity.name in standard_activities:
            return 2
        
        # High-value activities
        high_value_activities = ["Super Troop", "Delta", "Climbing Tower", "Aqua Trampoline"]
        if entry.activity.name in high_value_activities:
            return 3
        
        return 4
    
    def _remove_lower_priority_activity(self, troop: Troop, time_slot: TimeSlot) -> Optional[ScheduleEntry]:
        """Remove a lower priority activity from a slot."""
        existing_entry = self.schedule.get_entry(troop, time_slot)
        if existing_entry:
            self.schedule.remove_entry(existing_entry)
        return existing_entry
    
    def get_top5_recovery_metrics(self) -> Dict:
        """Get comprehensive Top 5 recovery metrics."""
        return {
            'top5_recovered': self.top5_recovered,
            'force_placements': self.force_placements,
            'emergency_placements': self.emergency_placements,
            'violations_created': self.violations_created,
            'strategy_usage': self.strategy_usage,
            'recovery_details': self.recovery_details,
            'missed_preferences': self.missed_preferences,
            'recovery_effectiveness': self._calculate_recovery_effectiveness()
        }
    
    def _calculate_recovery_effectiveness(self) -> Dict:
        """Calculate effectiveness of each recovery strategy."""
        total = max(1, sum(self.strategy_usage.values()))
        return {
            strategy: count / total 
            for strategy, count in self.strategy_usage.items()
        }
