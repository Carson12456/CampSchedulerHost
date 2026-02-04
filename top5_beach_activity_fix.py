#!/usr/bin/env python3
"""
Top 5 Beach Activity Constraint Relaxation System
Addresses Aqua Trampoline crisis by relaxing beach slot constraints for high-priority Top 5 preferences.
"""

from typing import List, Dict, Set, Optional
from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day
from activities import get_activity_by_name
import logging


class Top5BeachActivityFix:
    """
    Relax beach activity constraints for Top 5 preferences to solve Aqua Trampoline crisis.
    """
    
    def __init__(self, schedule: Schedule):
        self.schedule = schedule
        self.logger = logging.getLogger(__name__)
        
        # High-priority beach activities that deserve slot flexibility for Top 5
        self.TOP5_BEACH_PRIORITY_ACTIVITIES = {
            "Aqua Trampoline",  # #1 missed activity (12/18 misses)
            "Water Polo",       # #2 missed beach activity
            "Sailing",          # High-demand exclusive activity
            "Troop Swim",       # Popular beach activity
        }
        
        # Beach activities with normal slot restrictions
        self.BEACH_SLOT_ACTIVITIES = {
            "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats"
        }
        
        # Track fixes applied
        self.fixes_applied = []
        self.constraint_violations_created = 0
    
    def apply_top5_beach_fixes(self) -> Dict:
        """
        Apply Top 5 beach activity constraint relaxation.
        """
        results = {
            'fixes_applied': 0,
            'constraint_violations': 0,
            'troops_helped': set(),
            'activities_placed': [],
            'details': []
        }
        
        # Find all troops missing high-priority beach activities in their Top 5
        missed_top5_beach = self._find_missed_top5_beach_activities()
        
        self.logger.info(f"Found {len(missed_top5_beach)} missed Top 5 beach activities")
        
        for miss_info in missed_top5_beach:
            troop = miss_info['troop']
            activity = miss_info['activity']
            rank = miss_info['rank']
            
            # Try to place with relaxed constraints
            placement_result = self._place_with_relaxed_constraints(troop, activity, rank)
            
            if placement_result['placed']:
                results['fixes_applied'] += 1
                results['constraint_violations'] += placement_result['violations']
                results['troops_helped'].add(troop.name)
                results['activities_placed'].append(activity.name)
                
                detail = {
                    'troop': troop.name,
                    'activity': activity.name,
                    'rank': rank,
                    'slot': str(placement_result['slot']),
                    'violations': placement_result['violations'],
                    'constraint_relaxed': placement_result['constraint_relaxed']
                }
                results['details'].append(detail)
                self.fixes_applied.append(detail)
                
                self.logger.info(f"Placed {activity.name} (Rank #{rank}) for {troop.name} at {placement_result['slot']}")
        
        results['troops_helped'] = list(results['troops_helped'])
        return results
    
    def _find_missed_top5_beach_activities(self) -> List[Dict]:
        """
        Find all troops missing high-priority beach activities in their Top 5.
        """
        missed = []
        
        for troop in self.schedule.troops:
            # Get troop's current activities
            troop_activities = set()
            for entry in self.schedule.entries:
                if entry.troop == troop:
                    troop_activities.add(entry.activity.name)
            
            # Check Top 5 preferences
            top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            
            for i, pref_name in enumerate(top5_prefs):
                if pref_name in self.TOP5_BEACH_PRIORITY_ACTIVITIES:
                    if pref_name not in troop_activities:
                        activity = get_activity_by_name(pref_name)
                        if activity:
                            missed.append({
                                'troop': troop,
                                'activity': activity,
                                'rank': i + 1
                            })
        
        return missed
    
    def _place_with_relaxed_constraints(self, troop: Troop, activity: Activity, rank: int) -> Dict:
        """
        Try to place activity with relaxed beach constraints for Top 5.
        """
        # Generate all possible time slots
        from models import generate_time_slots
        all_slots = generate_time_slots()
        
        # Rank-based constraint relaxation
        # Rank #1: Most aggressive relaxation (allow slot 2)
        # Rank #2-3: Moderate relaxation
        # Rank #4-5: Minimal relaxation
        
        for slot in all_slots:
            if not self.schedule.is_troop_free(slot, troop):
                continue
            
            # Check if placement is possible with relaxed constraints
            can_place, violation_info = self._check_relaxed_placement(activity, troop, slot, rank)
            
            if can_place:
                # Place the activity
                entry = ScheduleEntry(troop, activity, slot)
                self.schedule.add_entry(entry)
                
                # Track constraint violations
                violations = len(violation_info)
                if violations > 0:
                    self.constraint_violations_created += violations
                
                return {
                    'placed': True,
                    'slot': slot,
                    'violations': violations,
                    'constraint_relaxed': violation_info
                }
        
        return {'placed': False, 'slot': None, 'violations': 0, 'constraint_relaxed': []}
    
    def _check_relaxed_placement(self, activity: Activity, troop: Troop, slot: TimeSlot, rank: int) -> tuple[bool, List[str]]:
        """
        Check if placement is possible with relaxed beach constraints based on preference rank.
        """
        violations = []
        
        # Rank #1: Allow slot 2 beach placement (major relaxation)
        if rank == 1 and activity.name in self.TOP5_BEACH_PRIORITY_ACTIVITIES:
            if slot.slot_number == 2 and slot.day != Day.THURSDAY:
                violations.append("Rank #1 beach activity slot 2 relaxation")
                return True, violations
        
        # Rank #2-3: Allow slot 2 for Aqua Trampoline only (targeted relaxation)
        if rank <= 3 and activity.name == "Aqua Trampoline":
            if slot.slot_number == 2 and slot.day != Day.THURSDAY:
                violations.append("Aqua Trampoline Rank #2-3 slot 2 relaxation")
                return True, violations
        
        # Rank #4-5: Allow slot 2 on Thursday only (minimal relaxation)
        if rank <= 5 and activity.name in self.TOP5_BEACH_PRIORITY_ACTIVITIES:
            if slot.slot_number == 2 and slot.day == Day.THURSDAY:
                violations.append("Thursday slot 2 relaxation")
                return True, violations
        
        # Standard constraint checking
        # Check exclusive activity constraint
        for entry in self.schedule.entries:
            if (entry.activity.name == activity.name and 
                entry.time_slot.day == slot.day and 
                entry.time_slot.slot_number == slot.slot_number):
                violations.append("exclusive activity conflict")
                return False, violations
        
        # Check other basic constraints
        if activity.name in self.BEACH_SLOT_ACTIVITIES:
            if slot.slot_number == 2 and slot.day != Day.THURSDAY:
                violations.append("beach slot constraint")
                return False, violations
        
        return True, violations
    
    def get_fix_summary(self) -> Dict:
        """
        Get summary of applied fixes.
        """
        return {
            'total_fixes': len(self.fixes_applied),
            'constraint_violations': self.constraint_violations_created,
            'fixes_by_activity': self._count_fixes_by_activity(),
            'fixes_by_rank': self._count_fixes_by_rank(),
            'detailed_fixes': self.fixes_applied
        }
    
    def _count_fixes_by_activity(self) -> Dict[str, int]:
        """Count fixes by activity name."""
        counts = {}
        for fix in self.fixes_applied:
            activity = fix['activity']
            counts[activity] = counts.get(activity, 0) + 1
        return counts
    
    def _count_fixes_by_rank(self) -> Dict[int, int]:
        """Count fixes by preference rank."""
        counts = {}
        for fix in self.fixes_applied:
            rank = fix['rank']
            counts[rank] = counts.get(rank, 0) + 1
        return counts


def apply_top5_beach_fix(schedule: Schedule) -> Dict:
    """
    Apply Top 5 beach activity constraint relaxation to a schedule.
    """
    fixer = Top5BeachActivityFix(schedule)
    results = fixer.apply_top5_beach_fixes()
    results['summary'] = fixer.get_fix_summary()
    return results
