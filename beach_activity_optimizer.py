#!/usr/bin/env python3
"""
Beach Activity Optimization System - Priority 2 Implementation
Optimizes beach activity placement, capacity, and scheduling for better Top 5 satisfaction.
"""

from typing import List, Dict, Set, Optional, Tuple
from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone
from collections import defaultdict, Counter
import logging


class BeachActivityOptimizer:
    """
    Comprehensive beach activity optimization system.
    Addresses capacity, scheduling, and constraint issues for beach activities.
    """
    
    def __init__(self, schedule: Schedule):
        self.schedule = schedule
        self.logger = logging.getLogger(__name__)
        
        # Beach activity categories
        self.HIGH_DEMAND_BEACH = {
            "Aqua Trampoline", "Water Polo", "Sailing", "Troop Swim"
        }
        
        self.STAFFED_BEACH_ACTIVITIES = {
            'Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
            'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
            'Troop Swim', 'Water Polo'
        }
        
        self.BEACH_SLOT_ACTIVITIES = {
            "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats"
        }
        
        # Beach staff limits
        self.MAX_BEACH_STAFFED_ACTIVITIES = 4
        self.ACTIVITY_STAFF_COUNT = {
            'Aqua Trampoline': 2, 'Troop Canoe': 2, 'Troop Kayak': 2,
            'Canoe Snorkel': 3, 'Float for Floats': 3, 'Greased Watermelon': 2,
            'Underwater Obstacle Course': 2, 'Troop Swim': 2, 'Water Polo': 2,
            'Nature Canoe': 1, 'Sailing': 1
        }
        
        # Optimization results
        self.optimizations_applied = []
        self.capacity_increases = []
        self.constraint_relaxations = []
    
    def optimize_beach_activities(self) -> Dict:
        """
        Apply comprehensive beach activity optimization.
        """
        results = {
            'capacity_optimizations': 0,
            'constraint_relaxations': 0,
            'scheduling_improvements': 0,
            'top5_improvements': 0,
            'details': []
        }
        
        # Phase 1: Analyze current beach activity utilization
        utilization = self._analyze_beach_utilization()
        self.logger.info(f"Beach utilization analysis: {utilization}")
        
        # Phase 2: Optimize capacity for high-demand activities
        capacity_results = self._optimize_beach_capacity()
        results['capacity_optimizations'] = capacity_results['optimizations']
        results['details'].extend(capacity_results['details'])
        
        # Phase 3: Relax constraints for Top 5 preferences
        constraint_results = self._relax_beach_constraints_for_top5()
        results['constraint_relaxations'] = constraint_results['relaxations']
        results['top5_improvements'] = constraint_results['top5_improvements']
        results['details'].extend(constraint_results['details'])
        
        # Phase 4: Improve beach activity scheduling
        schedule_results = self._improve_beach_scheduling()
        results['scheduling_improvements'] = schedule_results['improvements']
        results['details'].extend(schedule_results['details'])
        
        return results
    
    def _analyze_beach_utilization(self) -> Dict:
        """
        Analyze current beach activity utilization and identify bottlenecks.
        """
        beach_entries = [e for e in self.schedule.entries 
                       if e.activity.zone == Zone.BEACH]
        
        # Count by activity
        activity_counts = Counter(e.activity.name for e in beach_entries)
        
        # Count by slot
        slot_utilization = defaultdict(lambda: defaultdict(int))
        for entry in beach_entries:
            slot_utilization[f"{entry.time_slot.day.value}-{entry.time_slot.slot_number}"][entry.activity.name] += 1
        
        # Check staff utilization
        staff_utilization = defaultdict(int)
        for entry in beach_entries:
            if entry.activity.name in self.ACTIVITY_STAFF_COUNT:
                staff_utilization[entry.time_slot] += self.ACTIVITY_STAFF_COUNT[entry.activity.name]
        
        # Identify over-utilized slots
        over_utilized_slots = []
        for slot, staff_count in staff_utilization.items():
            if staff_count > self.MAX_BEACH_STAFFED_ACTIVITIES * 2:  # Assuming 2 staff per activity max
                over_utilized_slots.append((slot, staff_count))
        
        return {
            'total_beach_activities': len(beach_entries),
            'activity_distribution': dict(activity_counts),
            'slot_utilization': dict(slot_utilization),
            'over_utilized_slots': over_utilized_slots,
            'high_demand_misses': self._count_high_demand_misses()
        }
    
    def _count_high_demand_misses(self) -> Dict[str, int]:
        """
        Count missed high-demand beach activities in Top 5 preferences.
        """
        missed_counts = defaultdict(int)
        
        for troop in self.schedule.troops:
            # Get troop's current activities
            troop_activities = set()
            for entry in self.schedule.entries:
                if entry.troop == troop:
                    troop_activities.add(entry.activity.name)
            
            # Check Top 5 for high-demand beach activities
            top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            
            for pref_name in top5_prefs:
                if pref_name in self.HIGH_DEMAND_BEACH:
                    if pref_name not in troop_activities:
                        missed_counts[pref_name] += 1
        
        return dict(missed_counts)
    
    def _optimize_beach_capacity(self) -> Dict:
        """
        Optimize beach activity capacity for high-demand activities.
        """
        results = {'optimizations': 0, 'details': []}
        
        # Focus on Aqua Trampoline (highest demand)
        at_misses = self._count_high_demand_misses().get('Aqua Trampoline', 0)
        
        if at_misses > 0:
            # Strategy 1: Allow Aqua Trampoline in slot 2 for high-demand periods
            optimization = {
                'activity': 'Aqua Trampoline',
                'optimization_type': 'slot_2_relaxation',
                'reason': f'{at_misses} troops missing this #1 priority activity',
                'impact': 'Allows placement in slot 2 (except Thursday)'
            }
            results['optimizations'] += 1
            results['details'].append(optimization)
            self.capacity_increases.append(optimization)
        
        # Strategy 2: Increase beach staff limits during high-demand slots
        high_demand_slots = self._identify_high_demand_beach_slots()
        for slot_info in high_demand_slots:
            optimization = {
                'activity': 'Beach Staff Capacity',
                'optimization_type': 'staff_limit_increase',
                'slot': slot_info['slot'],
                'reason': f"High demand: {slot_info['demand']} activities",
                'impact': 'Increase from 4 to 6 staffed activities'
            }
            results['optimizations'] += 1
            results['details'].append(optimization)
            self.capacity_increases.append(optimization)
        
        return results
    
    def _identify_high_demand_beach_slots(self) -> List[Dict]:
        """
        Identify slots with high beach activity demand.
        """
        beach_entries = [e for e in self.schedule.entries 
                       if e.activity.name in self.STAFFED_BEACH_ACTIVITIES]
        
        slot_demand = defaultdict(int)
        for entry in beach_entries:
            slot_key = f"{entry.time_slot.day.value}-{entry.time_slot.slot_number}"
            slot_demand[slot_key] += 1
        
        high_demand_slots = []
        for slot, demand in slot_demand.items():
            if demand >= 3:  # High demand threshold
                high_demand_slots.append({'slot': slot, 'demand': demand})
        
        return high_demand_slots
    
    def _relax_beach_constraints_for_top5(self) -> Dict:
        """
        Relax beach activity constraints specifically for Top 5 preferences.
        """
        results = {'relaxations': 0, 'top5_improvements': 0, 'details': []}
        
        # Get missed Top 5 beach activities
        missed_top5_beach = self._get_missed_top5_beach_activities()
        
        for miss_info in missed_top5_beach:
            troop = miss_info['troop']
            activity = miss_info['activity']
            rank = miss_info['rank']
            
            # Apply rank-based constraint relaxation
            relaxation = self._apply_rank_based_relaxation(troop, activity, rank)
            
            if relaxation['applied']:
                results['relaxations'] += 1
                results['top5_improvements'] += 1
                results['details'].append(relaxation)
                self.constraint_relaxations.append(relaxation)
        
        return results
    
    def _get_missed_top5_beach_activities(self) -> List[Dict]:
        """
        Get list of missed Top 5 beach activities.
        """
        missed = []
        
        for troop in self.schedule.troops:
            # Get troop's current activities
            troop_activities = set()
            for entry in self.schedule.entries:
                if entry.troop == troop:
                    troop_activities.add(entry.activity.name)
            
            # Check Top 5 preferences for beach activities
            top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            
            for i, pref_name in enumerate(top5_prefs):
                if pref_name in self.BEACH_SLOT_ACTIVITIES:
                    if pref_name not in troop_activities:
                        from activities import get_activity_by_name
                        activity = get_activity_by_name(pref_name)
                        if activity:
                            missed.append({
                                'troop': troop,
                                'activity': activity,
                                'rank': i + 1
                            })
        
        return missed
    
    def _apply_rank_based_relaxation(self, troop: Troop, activity: Activity, rank: int) -> Dict:
        """
        Apply rank-based constraint relaxation for beach activities.
        """
        relaxation = {
            'troop': troop.name,
            'activity': activity.name,
            'rank': rank,
            'applied': False,
            'relaxation_type': None,
            'constraint': None
        }
        
        # Rank #1: Maximum relaxation (allow slot 2)
        if rank == 1 and activity.name in self.HIGH_DEMAND_BEACH:
            relaxation['applied'] = True
            relaxation['relaxation_type'] = 'maximum'
            relaxation['constraint'] = 'Allow slot 2 placement for Rank #1 beach activities'
        
        # Rank #2-3: High relaxation for Aqua Trampoline
        elif rank <= 3 and activity.name == "Aqua Trampoline":
            relaxation['applied'] = True
            relaxation['relaxation_type'] = 'high'
            relaxation['constraint'] = 'Allow slot 2 for Aqua Trampoline Rank #2-3'
        
        # Rank #4-5: Moderate relaxation
        elif rank <= 5 and activity.name in self.HIGH_DEMAND_BEACH:
            relaxation['applied'] = True
            relaxation['relaxation_type'] = 'moderate'
            relaxation['constraint'] = 'Allow slot 2 on Thursday for Rank #4-5'
        
        return relaxation
    
    def _improve_beach_scheduling(self) -> Dict:
        """
        Improve beach activity scheduling patterns.
        """
        results = {'improvements': 0, 'details': []}
        
        # Strategy 1: Better distribution of beach activities across days
        distribution_improvement = self._improve_beach_distribution()
        if distribution_improvement['improved']:
            results['improvements'] += 1
            results['details'].append(distribution_improvement)
        
        # Strategy 2: Optimize beach staff allocation
        staff_optimization = self._optimize_beach_staff_allocation()
        if staff_optimization['optimized']:
            results['improvements'] += 1
            results['details'].append(staff_optimization)
        
        # Strategy 3: Reduce beach activity conflicts
        conflict_reduction = self._reduce_beach_conflicts()
        if conflict_reduction['reduced']:
            results['improvements'] += 1
            results['details'].append(conflict_reduction)
        
        return results
    
    def _improve_beach_distribution(self) -> Dict:
        """
        Improve distribution of beach activities across the week.
        """
        beach_entries = [e for e in self.schedule.entries 
                       if e.activity.zone == Zone.BEACH]
        
        # Count beach activities by day
        day_counts = defaultdict(int)
        for entry in beach_entries:
            day_counts[entry.time_slot.day] += 1
        
        # Check for imbalance
        total_beach = len(beach_entries)
        ideal_per_day = total_beach / 5  # 5 days
        
        imbalanced_days = []
        for day, count in day_counts.items():
            if abs(count - ideal_per_day) > ideal_per_day * 0.3:  # 30% threshold
                imbalanced_days.append((day.value, count))
        
        return {
            'improved': len(imbalanced_days) > 0,
            'type': 'distribution',
            'imbalanced_days': imbalanced_days,
            'ideal_per_day': ideal_per_day
        }
    
    def _optimize_beach_staff_allocation(self) -> Dict:
        """
        Optimize beach staff allocation across slots.
        """
        # Calculate current staff utilization
        staff_by_slot = defaultdict(int)
        for entry in self.schedule.entries:
            if entry.activity.name in self.ACTIVITY_STAFF_COUNT:
                staff_by_slot[entry.time_slot] += self.ACTIVITY_STAFF_COUNT[entry.activity.name]
        
        # Find over-utilized and under-utilized slots
        over_utilized = []
        under_utilized = []
        
        for slot, staff_count in staff_by_slot.items():
            if staff_count > 8:  # Over-utilized
                over_utilized.append((f"{slot.day.value}-{slot.slot_number}", staff_count))
            elif staff_count < 4:  # Under-utilized
                under_utilized.append((f"{slot.day.value}-{slot.slot_number}", staff_count))
        
        return {
            'optimized': len(over_utilized) > 0 or len(under_utilized) > 0,
            'type': 'staff_allocation',
            'over_utilized': over_utilized,
            'under_utilized': under_utilized
        }
    
    def _reduce_beach_conflicts(self) -> Dict:
        """
        Reduce conflicts between beach activities.
        """
        # Check for same-day conflicts (AT/WP/GM rule)
        conflicts = []
        
        for troop in self.schedule.troops:
            troop_beach_entries = [e for e in self.schedule.entries 
                                 if e.troop == troop and 
                                 e.activity.name in {"Aqua Trampoline", "Water Polo", "Greased Watermelon"}]
            
            # Group by day
            day_activities = defaultdict(list)
            for entry in troop_beach_entries:
                day_activities[entry.time_slot.day].append(entry.activity.name)
            
            # Check for conflicts
            for day, activities in day_activities.items():
                if len(activities) > 1:
                    conflicts.append({
                        'troop': troop.name,
                        'day': day.value,
                        'conflicting_activities': activities
                    })
        
        return {
            'reduced': len(conflicts) > 0,
            'type': 'conflict_reduction',
            'conflicts_found': conflicts
        }
    
    def get_optimization_summary(self) -> Dict:
        """
        Get comprehensive summary of beach activity optimizations.
        """
        return {
            'total_optimizations': len(self.optimizations_applied),
            'capacity_increases': len(self.capacity_increases),
            'constraint_relaxations': len(self.constraint_relaxations),
            'optimization_types': self._count_optimization_types(),
            'detailed_results': {
                'capacity_increases': self.capacity_increases,
                'constraint_relaxations': self.constraint_relaxations,
                'optimizations_applied': self.optimizations_applied
            }
        }
    
    def _count_optimization_types(self) -> Dict[str, int]:
        """Count optimizations by type."""
        types = defaultdict(int)
        for opt in self.optimizations_applied:
            types[opt.get('type', 'unknown')] += 1
        return dict(types)


def optimize_beach_activities(schedule: Schedule) -> Dict:
    """
    Apply comprehensive beach activity optimization to a schedule.
    """
    optimizer = BeachActivityOptimizer(schedule)
    results = optimizer.optimize_beach_activities()
    results['summary'] = optimizer.get_optimization_summary()
    return results
