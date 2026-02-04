"""
Adaptive Constraint Weighting System
Dynamically adjusts constraint priorities and weights based on scheduling difficulty
and historical performance to optimize schedule quality.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, deque
import math
import statistics
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ConstraintType(Enum):
    BEACH_SLOT = "beach_slot"
    WET_DRY = "wet_dry"
    FRIDAY_REFLECTION = "friday_reflection"
    EXCLUSIVE_AREA = "exclusive_area"
    STAFF_BALANCE = "staff_balance"
    ACTIVITY_CONFLICT = "activity_conflict"
    PREFERENCE_SATISFACTION = "preference_satisfaction"
    CLUSTERING_EFFICIENCY = "clustering_efficiency"


@dataclass
class ConstraintWeight:
    """Represents a constraint weight with adaptive properties."""
    constraint_type: ConstraintType
    base_weight: float
    current_weight: float
    min_weight: float
    max_weight: float
    adaptation_rate: float
    success_rate: float = 0.0
    violation_count: int = 0
    last_adjustment: int = 0


class AdaptiveConstraintSystem:
    """
    Adaptive constraint weighting system that dynamically adjusts
    constraint priorities based on scheduling difficulty and performance.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Initialize constraint weights
        self.constraint_weights = self._initialize_constraint_weights()
        
        # Performance tracking
        self.scheduling_history = deque(maxlen=100)  # Last 100 scheduling attempts
        self.violation_history = defaultdict(deque)  # Violation history per constraint
        self.performance_metrics = defaultdict(list)
        
        # Adaptation settings
        self.adaptation_enabled = True
        self.learning_rate = 0.1
        self.performance_window = 10  # Number of recent schedules to consider
        
        # Constraint definitions for validation
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
    
    def _initialize_constraint_weights(self) -> Dict[ConstraintType, ConstraintWeight]:
        """Initialize constraint weights with base values."""
        weights = {
            ConstraintType.BEACH_SLOT: ConstraintWeight(
                constraint_type=ConstraintType.BEACH_SLOT,
                base_weight=10.0,
                current_weight=10.0,
                min_weight=5.0,
                max_weight=20.0,
                adaptation_rate=0.15
            ),
            ConstraintType.WET_DRY: ConstraintWeight(
                constraint_type=ConstraintType.WET_DRY,
                base_weight=8.0,
                current_weight=8.0,
                min_weight=4.0,
                max_weight=16.0,
                adaptation_rate=0.1
            ),
            ConstraintType.FRIDAY_REFLECTION: ConstraintWeight(
                constraint_type=ConstraintType.FRIDAY_REFLECTION,
                base_weight=15.0,
                current_weight=15.0,
                min_weight=10.0,
                max_weight=25.0,
                adaptation_rate=0.2
            ),
            ConstraintType.EXCLUSIVE_AREA: ConstraintWeight(
                constraint_type=ConstraintType.EXCLUSIVE_AREA,
                base_weight=20.0,
                current_weight=20.0,
                min_weight=15.0,
                max_weight=30.0,
                adaptation_rate=0.25
            ),
            ConstraintType.STAFF_BALANCE: ConstraintWeight(
                constraint_type=ConstraintType.STAFF_BALANCE,
                base_weight=6.0,
                current_weight=6.0,
                min_weight=2.0,
                max_weight=12.0,
                adaptation_rate=0.08
            ),
            ConstraintType.PREFERENCE_SATISFACTION: ConstraintWeight(
                constraint_type=ConstraintType.PREFERENCE_SATISFACTION,
                base_weight=12.0,
                current_weight=12.0,
                min_weight=8.0,
                max_weight=20.0,
                adaptation_rate=0.12
            ),
            ConstraintType.CLUSTERING_EFFICIENCY: ConstraintWeight(
                constraint_type=ConstraintType.CLUSTERING_EFFICIENCY,
                base_weight=4.0,
                current_weight=4.0,
                min_weight=1.0,
                max_weight=8.0,
                adaptation_rate=0.05
            )
        }
        
        return weights
    
    def get_constraint_weight(self, constraint_type: ConstraintType) -> float:
        """Get current weight for a constraint type."""
        return self.constraint_weights[constraint_type].current_weight
    
    def calculate_schedule_score(self, schedule_entries: List[ScheduleEntry] = None) -> float:
        """
        Calculate comprehensive schedule score using adaptive weights.
        """
        if schedule_entries is None:
            schedule_entries = self.schedule.entries
        
        total_score = 0.0
        
        # Calculate scores for each constraint type
        for constraint_type, weight_info in self.constraint_weights.items():
            constraint_score = self._calculate_constraint_score(constraint_type, schedule_entries)
            weighted_score = constraint_score * weight_info.current_weight
            total_score += weighted_score
        
        return total_score
    
    def _calculate_constraint_score(self, constraint_type: ConstraintType, 
                                   schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate score for a specific constraint type."""
        if constraint_type == ConstraintType.BEACH_SLOT:
            return self._calculate_beach_slot_score(schedule_entries)
        elif constraint_type == ConstraintType.WET_DRY:
            return self._calculate_wet_dry_score(schedule_entries)
        elif constraint_type == ConstraintType.FRIDAY_REFLECTION:
            return self._calculate_friday_reflection_score(schedule_entries)
        elif constraint_type == ConstraintType.EXCLUSIVE_AREA:
            return self._calculate_exclusive_area_score(schedule_entries)
        elif constraint_type == ConstraintType.STAFF_BALANCE:
            return self._calculate_staff_balance_score(schedule_entries)
        elif constraint_type == ConstraintType.PREFERENCE_SATISFACTION:
            return self._calculate_preference_satisfaction_score(schedule_entries)
        elif constraint_type == ConstraintType.CLUSTERING_EFFICIENCY:
            return self._calculate_clustering_efficiency_score(schedule_entries)
        
        return 0.0
    
    def _calculate_beach_slot_score(self, schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate beach slot constraint score (higher = better)."""
        violations = 0
        total_beach_activities = 0
        
        for entry in schedule_entries:
            if entry.activity.name in self.BEACH_SLOT_ACTIVITIES:
                total_beach_activities += 1
                if (entry.time_slot.slot_number == 2 and 
                    entry.time_slot.day != Day.THURSDAY):
                    violations += 1
        
        if total_beach_activities == 0:
            return 1.0  # Perfect score if no beach activities
        
        return (total_beach_activities - violations) / total_beach_activities
    
    def _calculate_wet_dry_score(self, schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate wet/dry constraint score."""
        violations = 0
        total_adjacent_pairs = 0
        
        # Group by troop and day
        troop_day_entries = defaultdict(list)
        for entry in schedule_entries:
            key = (entry.troop.name, entry.time_slot.day)  # Use troop name instead of troop object
            troop_day_entries[key].append(entry)
        
        for (troop, day), entries in troop_day_entries.items():
            entries.sort(key=lambda e: e.time_slot.slot_number)
            
            for i in range(len(entries) - 1):
                total_adjacent_pairs += 1
                curr_activity = entries[i].activity.name
                next_activity = entries[i + 1].activity.name
                
                if self._is_wet_dry_conflict(curr_activity, next_activity):
                    violations += 1
        
        if total_adjacent_pairs == 0:
            return 1.0
        
        return (total_adjacent_pairs - violations) / total_adjacent_pairs
    
    def _calculate_friday_reflection_score(self, schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate Friday Reflection compliance score."""
        troops_with_reflection = set()
        
        for entry in schedule_entries:
            if (entry.activity.name == "Reflection" and 
                entry.time_slot.day == Day.FRIDAY):
                troops_with_reflection.add(entry.troop.name)  # Use troop name instead of troop object
        
        if len(self.troops) == 0:
            return 1.0
        
        return len(troops_with_reflection) / len(self.troops)
    
    def _calculate_exclusive_area_score(self, schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate exclusive area constraint score."""
        exclusive_activities = {
            "Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery",
            "Aqua Trampoline", "Sailing"
        }
        
        violations = 0
        total_exclusive_scheduled = 0
        
        # Group by slot and activity
        slot_activity_troops = defaultdict(set)
        for entry in schedule_entries:
            if entry.activity.name in exclusive_activities:
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number, entry.activity.name)
                slot_activity_troops[slot_key].add(entry.troop.name)  # Use troop name instead of troop object
                total_exclusive_scheduled += 1
        
        for slot_key, troops in slot_activity_troops.items():
            if len(troops) > 1:
                violations += len(troops) - 1
        
        if total_exclusive_scheduled == 0:
            return 1.0
        
        return (total_exclusive_scheduled - violations) / total_exclusive_scheduled
    
    def _calculate_staff_balance_score(self, schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate staff workload balance score."""
        staff_loads = defaultdict(int)
        
        for entry in schedule_entries:
            if self._requires_staff(entry.activity.name):
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                staff_loads[slot_key] += 1
        
        if not staff_loads:
            return 1.0
        
        loads = list(staff_loads.values())
        avg_load = sum(loads) / len(loads)
        
        # Calculate variance (lower variance = higher score)
        variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)
        
        # Normalize variance to score (variance of 0 = score 1, high variance = score 0)
        max_acceptable_variance = 4.0  # Adjust based on requirements
        normalized_variance = min(variance / max_acceptable_variance, 1.0)
        
        return 1.0 - normalized_variance
    
    def _calculate_preference_satisfaction_score(self, schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate preference satisfaction score."""
        total_preferences = 0
        satisfied_preferences = 0
        
        # Group scheduled activities by troop
        troop_activities = defaultdict(set)
        for entry in schedule_entries:
            troop_activities[entry.troop.name].add(entry.activity.name)  # Use troop name instead of troop object
        
        for troop in self.troops:
            scheduled_activities = troop_activities[troop.name]  # Use troop name as key
            
            for rank, activity_name in enumerate(troop.preferences):
                total_preferences += 1
                if activity_name in scheduled_activities:
                    satisfied_preferences += 1
        
        if total_preferences == 0:
            return 1.0
        
        return satisfied_preferences / total_preferences
    
    def _calculate_clustering_efficiency_score(self, schedule_entries: List[ScheduleEntry]) -> float:
        """Calculate activity clustering efficiency score."""
        zone_activities = defaultdict(list)
        for entry in schedule_entries:
            zone = entry.activity.zone
            zone_activities[zone].append(entry)
        
        if not zone_activities:
            return 1.0
        
        total_efficiency = 0.0
        zone_count = 0
        
        for zone, entries in zone_activities.items():
            if len(entries) < 2:
                continue
            
            zone_count += 1
            days_used = set(e.time_slot.day for e in entries)
            max_possible_days = len(Day)
            
            # Higher efficiency for fewer days used
            efficiency = 1.0 - (len(days_used) - 1) / max_possible_days
            total_efficiency += efficiency
        
        return total_efficiency / zone_count if zone_count > 0 else 1.0
    
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
    
    def record_scheduling_result(self, schedule_score: float, violations: Dict[ConstraintType, int]):
        """
        Record scheduling result for adaptive learning.
        """
        # Store in history
        result = {
            'score': schedule_score,
            'violations': violations.copy(),
            'timestamp': len(self.scheduling_history)
        }
        self.scheduling_history.append(result)
        
        # Update violation history
        for constraint_type, count in violations.items():
            self.violation_history[constraint_type].append(count)
            self.constraint_weights[constraint_type].violation_count += count
        
        # Adapt weights if enabled
        if self.adaptation_enabled:
            self._adapt_constraint_weights()
    
    def _adapt_constraint_weights(self):
        """
        Adapt constraint weights based on recent performance.
        """
        if len(self.scheduling_history) < self.performance_window:
            return  # Not enough data for adaptation
        
        # Get recent performance data
        recent_results = list(self.scheduling_history)[-self.performance_window:]
        
        # Calculate performance metrics for each constraint
        for constraint_type, weight_info in self.constraint_weights.items():
            # Calculate recent violation rate
            recent_violations = []
            for result in recent_results:
                violation_count = result['violations'].get(constraint_type, 0)
                recent_violations.append(violation_count)
            
            if not recent_violations:
                continue
            
            avg_violations = statistics.mean(recent_violations)
            violation_trend = self._calculate_trend(recent_violations)
            
            # Calculate success rate (lower violations = higher success)
            max_possible_violations = len(self.troops)  # Rough estimate
            success_rate = max(0.0, 1.0 - (avg_violations / max(1, max_possible_violations)))
            weight_info.success_rate = success_rate
            
            # Adapt weight based on performance
            current_weight = weight_info.current_weight
            
            # If violations are increasing, increase weight
            if violation_trend > 0.1:  # Increasing violations
                adjustment = weight_info.adaptation_rate * (1.0 - success_rate)
                new_weight = current_weight + adjustment
            # If violations are decreasing, can decrease weight slightly
            elif violation_trend < -0.1 and success_rate > 0.8:  # Decreasing violations and good success
                adjustment = weight_info.adaptation_rate * 0.5 * (success_rate - 0.8)
                new_weight = current_weight - adjustment
            else:
                new_weight = current_weight
            
            # Clamp to min/max bounds
            new_weight = max(weight_info.min_weight, min(weight_info.max_weight, new_weight))
            weight_info.current_weight = new_weight
            weight_info.last_adjustment = len(self.scheduling_history)
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (positive = increasing, negative = decreasing)."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def get_adaptation_report(self) -> Dict:
        """Get comprehensive adaptation report."""
        report = {
            'adaptation_enabled': self.adaptation_enabled,
            'total_scheduling_attempts': len(self.scheduling_history),
            'constraint_weights': {},
            'performance_summary': {},
            'recommendations': []
        }
        
        # Constraint weight details
        for constraint_type, weight_info in self.constraint_weights.items():
            report['constraint_weights'][constraint_type.value] = {
                'base_weight': weight_info.base_weight,
                'current_weight': weight_info.current_weight,
                'min_weight': weight_info.min_weight,
                'max_weight': weight_info.max_weight,
                'success_rate': weight_info.success_rate,
                'total_violations': weight_info.violation_count,
                'weight_change': weight_info.current_weight - weight_info.base_weight,
                'last_adjustment': weight_info.last_adjustment
            }
        
        # Performance summary
        if self.scheduling_history:
            recent_scores = [r['score'] for r in list(self.scheduling_history)[-10:]]
            report['performance_summary'] = {
                'recent_avg_score': statistics.mean(recent_scores),
                'recent_score_trend': self._calculate_trend(recent_scores),
                'best_score': max(r['score'] for r in self.scheduling_history),
                'worst_score': min(r['score'] for r in self.scheduling_history)
            }
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations()
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on current performance."""
        recommendations = []
        
        for constraint_type, weight_info in self.constraint_weights.items():
            if weight_info.success_rate < 0.5:
                recommendations.append(
                    f"Consider increasing {constraint_type.value} constraint weight "
                    f"(current success rate: {weight_info.success_rate:.1%})"
                )
            elif weight_info.success_rate > 0.9 and weight_info.current_weight > weight_info.base_weight * 1.2:
                recommendations.append(
                    f"Consider decreasing {constraint_type.value} constraint weight "
                    f"(high success rate: {weight_info.success_rate:.1%})"
                )
        
        # Check for adaptation opportunities
        if len(self.scheduling_history) >= self.performance_window:
            recent_scores = [r['score'] for r in list(self.scheduling_history)[-5:]]
            if self._calculate_trend(recent_scores) < -0.1:
                recommendations.append("Recent schedule quality is declining - consider reviewing constraint priorities")
        
        return recommendations
    
    def reset_adaptation(self):
        """Reset all constraint weights to base values."""
        for weight_info in self.constraint_weights.values():
            weight_info.current_weight = weight_info.base_weight
            weight_info.success_rate = 0.0
            weight_info.violation_count = 0
            weight_info.last_adjustment = 0
        
        # Clear history
        self.scheduling_history.clear()
        self.violation_history.clear()
        self.performance_metrics.clear()
        
        print("  [Adaptive] Constraint weights reset to base values")
    
    def enable_adaptation(self):
        """Enable adaptive weight adjustment."""
        self.adaptation_enabled = True
        print("  [Adaptive] Constraint weight adaptation enabled")
    
    def disable_adaptation(self):
        """Disable adaptive weight adjustment."""
        self.adaptation_enabled = False
        print("  [Adaptive] Constraint weight adaptation disabled")


def create_adaptive_constraint_system(schedule, troops, activities):
    """
    Create and configure an adaptive constraint system.
    """
    system = AdaptiveConstraintSystem(schedule, troops, activities)
    return system
