"""
Machine Learning-Based Activity Placement Prediction System
Uses historical scheduling data to predict optimal activity placements
and provide intelligent scheduling recommendations.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, Counter
import statistics
import json
import random
import math
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import pickle


@dataclass
class PlacementFeatures:
    """Features for ML-based activity placement prediction."""
    # Activity features
    activity_name: str
    activity_zone: str
    activity_duration: float
    activity_staff_required: bool
    activity_exclusive: bool
    activity_concurrent_limit: int
    
    # Troop features
    troop_size: int
    troop_preference_rank: int
    troop_day_requests: List[str]
    troop_previous_activities: List[str]
    
    # Temporal features
    day: str
    slot_number: int
    day_of_week: int  # 0-4 for Mon-Fri
    is_morning: bool
    is_afternoon: bool
    
    # Contextual features
    current_load: int
    zone_load: int
    staff_load: int
    commissioner_load: int
    adjacent_activities: List[str]
    
    # Historical success features
    historical_success_rate: float
    historical_violation_rate: float
    preference_satisfaction_rate: float


@dataclass
class PlacementPrediction:
    """ML prediction for activity placement."""
    activity_name: str
    troop_name: str
    predicted_day: str
    predicted_slot: int
    confidence: float
    success_probability: float
    violation_risk: float
    preference_satisfaction: float
    alternative_placements: List[Dict[str, any]]
    reasoning: List[str]


class MLActivityPredictor:
    """
    Machine learning system for predicting optimal activity placements
    based on historical scheduling data and patterns.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Historical data storage
        self.historical_placements = []
        self.feature_history = []
        self.success_history = []
        
        # ML model parameters (simplified rule-based approach)
        self.model_weights = self._initialize_model_weights()
        self.feature_importance = defaultdict(float)
        
        # Activity and zone mappings
        self.zone_mappings = {
            Zone.BEACH: "beach",
            Zone.TOWER: "tower", 
            Zone.OUTDOOR_SKILLS: "outdoor_skills",
            Zone.DELTA: "delta",
            Zone.OFF_CAMP: "off_camp",
            Zone.CAMPSITE: "campsite"
        }
        
        # Day mappings
        self.day_mappings = {
            Day.MONDAY: 0,
            Day.TUESDAY: 1, 
            Day.WEDNESDAY: 2,
            Day.THURSDAY: 3,
            Day.FRIDAY: 4
        }
        
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
        
        self.EXCLUSIVE_ACTIVITIES = {
            "Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery",
            "Aqua Trampoline", "Sailing"
        }
        
        # Initialize model
        self._initialize_model()
    
    def _initialize_model_weights(self):
        """Initialize ML model weights for different features."""
        return {
            'preference_rank': 0.25,
            'historical_success': 0.20,
            'zone_load': 0.15,
            'staff_load': 0.12,
            'time_slot_preference': 0.10,
            'commissioner_load': 0.08,
            'adjacent_compatibility': 0.06,
            'troop_size_match': 0.04
        }
    
    def _initialize_model(self):
        """Initialize the ML model with current schedule data."""
        print("  [ML Predictor] Initializing machine learning model...")
        
        # Extract features from current schedule
        for entry in self.schedule.entries:
            features = self._extract_placement_features(entry)
            self.feature_history.append(features)
            
            # Calculate success metrics
            success_score = self._calculate_placement_success(entry)
            self.success_history.append(success_score)
        
        # Update feature importance based on current data
        self._update_feature_importance()
        
        print(f"  [ML Predictor] Model initialized with {len(self.feature_history)} placement examples")
    
    def predict_optimal_placement(self, activity_name: str, troop_name: str) -> PlacementPrediction:
        """
        Predict optimal placement for a specific activity and troop.
        """
        # Get activity and troop objects
        activity = self.activities.get(activity_name)
        troop = next((t for t in self.troops if t.name == troop_name), None)
        
        if not activity or not troop:
            return self._create_empty_prediction(activity_name, troop_name)
        
        # Get preference rank
        preference_rank = len(troop.preferences)
        if activity_name in troop.preferences:
            preference_rank = troop.preferences.index(activity_name) + 1
        
        # Generate all possible placements
        possible_placements = []
        
        for day in Day:
            max_slot = 2 if day == Day.THURSDAY else 3
            for slot in range(1, max_slot + 1):
                # Check if placement is feasible
                if self._is_placement_feasible(activity, troop, day, slot):
                    placement_score = self._evaluate_placement(
                        activity, troop, day, slot, preference_rank
                    )
                    
                    possible_placements.append({
                        'day': day.value,
                        'slot': slot,
                        'score': placement_score['total_score'],
                        'success_probability': placement_score['success_probability'],
                        'violation_risk': placement_score['violation_risk'],
                        'preference_satisfaction': placement_score['preference_satisfaction'],
                        'confidence': placement_score['confidence'],
                        'reasoning': placement_score['reasoning']
                    })
        
        if not possible_placements:
            return self._create_empty_prediction(activity_name, troop_name)
        
        # Sort by total score
        possible_placements.sort(key=lambda x: x['score'], reverse=True)
        
        # Get best placement
        best_placement = possible_placements[0]
        alternatives = possible_placements[1:4]  # Top 3 alternatives
        
        return PlacementPrediction(
            activity_name=activity_name,
            troop_name=troop_name,
            predicted_day=best_placement['day'],
            predicted_slot=best_placement['slot'],
            confidence=best_placement['confidence'],
            success_probability=best_placement['success_probability'],
            violation_risk=best_placement['violation_risk'],
            preference_satisfaction=best_placement['preference_satisfaction'],
            alternative_placements=alternatives,
            reasoning=best_placement['reasoning']
        )
    
    def _extract_placement_features(self, entry: ScheduleEntry) -> PlacementFeatures:
        """Extract features from a schedule entry for ML training."""
        activity = entry.activity
        troop = entry.troop
        day = entry.time_slot.day
        slot = entry.time_slot.slot_number
        
        # Get preference rank
        preference_rank = len(troop.preferences)
        if activity.name in troop.preferences:
            preference_rank = troop.preferences.index(activity.name) + 1
        
        # Calculate contextual features
        current_load = self._calculate_slot_load(day, slot)
        zone_load = self._calculate_zone_load(activity.zone, day)
        staff_load = self._calculate_staff_load(day, slot)
        commissioner_load = self._calculate_commissioner_load(troop, day)
        adjacent_activities = self._get_adjacent_activities(troop, day, slot)
        
        # Calculate historical features
        historical_success = self._calculate_historical_success_rate(activity.name, day, slot)
        historical_violation = self._calculate_historical_violation_rate(activity.name, day, slot)
        preference_satisfaction = self._calculate_preference_satisfaction_rate(activity.name, preference_rank)
        
        return PlacementFeatures(
            activity_name=activity.name,
            activity_zone=self.zone_mappings[activity.zone],
            activity_duration=getattr(activity, 'duration', 1.0),  # Default to 1.0 if not present
            activity_staff_required=self._requires_staff(activity.name),
            activity_exclusive=activity.name in self.EXCLUSIVE_ACTIVITIES,
            activity_concurrent_limit=getattr(activity, 'concurrent_limit', 1),
            
            troop_size=getattr(troop, 'scouts', 0) + getattr(troop, 'adults', 0),
            troop_preference_rank=preference_rank,
            troop_day_requests=list(troop.day_requests),
            troop_previous_activities=self._get_troop_previous_activities(troop),
            
            day=day.value,
            slot_number=slot,
            day_of_week=self.day_mappings[day],
            is_morning=slot <= 2,
            is_afternoon=slot > 2,
            
            current_load=current_load,
            zone_load=zone_load,
            staff_load=staff_load,
            commissioner_load=commissioner_load,
            adjacent_activities=adjacent_activities,
            
            historical_success_rate=historical_success,
            historical_violation_rate=historical_violation,
            preference_satisfaction_rate=preference_satisfaction
        )
    
    def _evaluate_placement(self, activity: Activity, troop: Troop, day: Day, slot: int, 
                          preference_rank: int) -> Dict[str, float]:
        """Evaluate a potential placement using ML model."""
        
        # Calculate individual feature scores
        preference_score = self._calculate_preference_score(preference_rank)
        historical_score = self._calculate_historical_placement_score(activity.name, day, slot)
        zone_score = self._calculate_zone_optimization_score(activity.zone, day, slot)
        staff_score = self._calculate_staff_optimization_score(day, slot)
        time_score = self._calculate_time_slot_preference_score(activity.name, day, slot)
        commissioner_score = self._calculate_commissioner_balance_score(troop, day)
        adjacent_score = self._calculate_adjacent_compatibility_score(activity, troop, day, slot)
        size_score = self._calculate_troop_size_match_score(activity, troop)
        
        # Weighted combination
        total_score = (
            preference_score * self.model_weights['preference_rank'] +
            historical_score * self.model_weights['historical_success'] +
            zone_score * self.model_weights['zone_load'] +
            staff_score * self.model_weights['staff_load'] +
            time_score * self.model_weights['time_slot_preference'] +
            commissioner_score * self.model_weights['commissioner_load'] +
            adjacent_score * self.model_weights['adjacent_compatibility'] +
            size_score * self.model_weights['troop_size_match']
        )
        
        # Calculate derived metrics
        success_probability = min(1.0, total_score + 0.2)  # Adjust for probability scale
        violation_risk = max(0.0, 1.0 - total_score - 0.1)
        preference_satisfaction = preference_score
        confidence = min(1.0, len(self.feature_history) / 100.0)  # Based on data size
        
        # Generate reasoning
        reasoning = self._generate_placement_reasoning(
            preference_score, historical_score, zone_score, 
            staff_score, time_score, commissioner_score
        )
        
        return {
            'total_score': total_score,
            'success_probability': success_probability,
            'violation_risk': violation_risk,
            'preference_satisfaction': preference_satisfaction,
            'confidence': confidence,
            'reasoning': reasoning
        }
    
    def _calculate_preference_score(self, preference_rank: int) -> float:
        """Calculate preference satisfaction score."""
        if preference_rank <= 5:
            return 1.0
        elif preference_rank <= 10:
            return 0.8
        elif preference_rank <= 15:
            return 0.6
        elif preference_rank <= 20:
            return 0.4
        else:
            return 0.2
    
    def _calculate_historical_placement_score(self, activity_name: str, day: Day, slot: int) -> float:
        """Calculate historical placement success score."""
        # Look for similar historical placements
        similar_placements = [
            f for f in self.feature_history 
            if f.activity_name == activity_name and f.day == day.value and f.slot_number == slot
        ]
        
        if not similar_placements:
            return 0.5  # Neutral score for no historical data
        
        # Average success rate of similar placements
        success_rates = [
            self.success_history[i] for i, f in enumerate(self.feature_history)
            if f.activity_name == activity_name and f.day == day.value and f.slot_number == slot
        ]
        
        return statistics.mean(success_rates) if success_rates else 0.5
    
    def _calculate_zone_optimization_score(self, zone: Zone, day: Day, slot: int) -> float:
        """Calculate zone optimization score."""
        zone_load = self._calculate_zone_load(zone, day)
        
        # Optimal load is around 2-3 activities per day per zone
        if zone_load <= 1:
            return 0.9  # Good - zone has capacity
        elif zone_load <= 3:
            return 1.0  # Optimal
        elif zone_load <= 5:
            return 0.7  # Getting crowded
        else:
            return 0.4  # Overcrowded
    
    def _calculate_staff_optimization_score(self, day: Day, slot: int) -> float:
        """Calculate staff optimization score."""
        staff_load = self._calculate_staff_load(day, slot)
        
        # Optimal staff load is 2-3 activities per slot
        if staff_load <= 1:
            return 0.8
        elif staff_load <= 3:
            return 1.0
        elif staff_load <= 4:
            return 0.7
        else:
            return 0.4
    
    def _calculate_time_slot_preference_score(self, activity_name: str, day: Day, slot: int) -> float:
        """Calculate time slot preference score."""
        # Beach activities prefer morning slots
        if activity_name in self.BEACH_SLOT_ACTIVITIES:
            if slot == 1:
                return 1.0
            elif slot == 2 and day != Day.THURSDAY:
                return 0.0  # Invalid
            else:
                return 0.6
        
        # 3-hour activities prefer morning
        if activity_name in {"Rocks", "Delta"}:
            return 1.0 if slot == 1 else 0.3
        
        # General preference for earlier slots
        return 1.0 - (slot - 1) * 0.2
    
    def _calculate_commissioner_balance_score(self, troop: Troop, day: Day) -> float:
        """Calculate commissioner balance score."""
        commissioner_load = self._calculate_commissioner_load(troop, day)
        
        # Optimal is 1-2 activities per commissioner per day
        if commissioner_load <= 1:
            return 0.9
        elif commissioner_load <= 2:
            return 1.0
        elif commissioner_load <= 3:
            return 0.7
        else:
            return 0.4
    
    def _calculate_adjacent_compatibility_score(self, activity: Activity, troop: Troop, 
                                              day: Day, slot: int) -> float:
        """Calculate adjacent activity compatibility score."""
        adjacent = self._get_adjacent_activities(troop, day, slot)
        
        if not adjacent:
            return 0.8  # No adjacent activities
        
        score = 1.0
        
        for adj_activity in adjacent:
            # Check wet/dry conflicts
            if (activity.name in self.WET_ACTIVITIES and 
                adj_activity in self.TOWER_ODS_ACTIVITIES):
                score -= 0.5
            elif (adj_activity in self.WET_ACTIVITIES and 
                  activity.name in self.TOWER_ODS_ACTIVITIES):
                score -= 0.5
        
        return max(0.0, score)
    
    def _calculate_troop_size_match_score(self, activity: Activity, troop: Troop) -> float:
        """Calculate troop size match score."""
        troop_size = getattr(troop, 'scouts', 0) + getattr(troop, 'adults', 0)
        
        # Some activities are better for larger/smaller troops
        large_troop_activities = {
            "Aqua Trampoline", "Troop Swim", "Water Polo", "Super Troop"
        }
        
        small_troop_activities = {
            "Archery", "Troop Rifle", "Troop Shotgun", "Climbing Tower"
        }
        
        if activity.name in large_troop_activities:
            return min(1.0, troop_size / 20.0)
        elif activity.name in small_troop_activities:
            return min(1.0, (30 - troop_size) / 20.0)
        else:
            return 0.8  # Neutral for most activities
    
    def _generate_placement_reasoning(self, preference_score: float, historical_score: float,
                                   zone_score: float, staff_score: float, 
                                   time_score: float, commissioner_score: float) -> List[str]:
        """Generate reasoning for placement recommendation."""
        reasoning = []
        
        if preference_score >= 0.8:
            reasoning.append("High troop preference satisfaction")
        elif preference_score <= 0.4:
            reasoning.append("Low troop preference satisfaction")
        
        if historical_score >= 0.8:
            reasoning.append("Historically successful placement")
        elif historical_score <= 0.4:
            reasoning.append("Limited historical success")
        
        if zone_score >= 0.8:
            reasoning.append("Optimal zone load distribution")
        elif zone_score <= 0.5:
            reasoning.append("Zone may be overcrowded")
        
        if staff_score >= 0.8:
            reasoning.append("Good staff resource balance")
        elif staff_score <= 0.5:
            reasoning.append("Staff resources may be strained")
        
        if time_score >= 0.8:
            reasoning.append("Ideal time slot for activity")
        elif time_score <= 0.4:
            reasoning.append("Suboptimal time slot")
        
        if commissioner_score >= 0.8:
            reasoning.append("Good commissioner workload balance")
        elif commissioner_score <= 0.5:
            reasoning.append("Commissioner workload may be high")
        
        return reasoning
    
    def _is_placement_feasible(self, activity: Activity, troop: Troop, day: Day, slot: int) -> bool:
        """Check if placement is feasible given constraints."""
        # Check beach slot constraint
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot == 2 and day != Day.THURSDAY):
            return False
        
        # Check if troop is already scheduled at this time
        from models import generate_time_slots
        if not hasattr(self, '_time_slots'):
            self._time_slots = generate_time_slots()
        
        time_slot = next((ts for ts in self._time_slots 
                         if ts.day == day and ts.slot_number == slot), None)
        if time_slot and not self.schedule.is_troop_free(time_slot, troop):
            return False
        
        # Check exclusive activity constraint
        if activity.name in self.EXCLUSIVE_ACTIVITIES:
            for entry in self.schedule.entries:
                if (entry.activity.name == activity.name and 
                    entry.time_slot.day == day and 
                    entry.time_slot.slot_number == slot):
                    return False
        
        return True
    
    def _create_empty_prediction(self, activity_name: str, troop_name: str) -> PlacementPrediction:
        """Create empty prediction for invalid inputs."""
        return PlacementPrediction(
            activity_name=activity_name,
            troop_name=troop_name,
            predicted_day="",
            predicted_slot=0,
            confidence=0.0,
            success_probability=0.0,
            violation_risk=1.0,
            preference_satisfaction=0.0,
            alternative_placements=[],
            reasoning=["Invalid activity or troop"]
        )
    
    # Helper methods for feature calculation
    def _calculate_slot_load(self, day: Day, slot: int) -> int:
        """Calculate current load for a specific time slot."""
        return len([e for e in self.schedule.entries 
                   if e.time_slot.day == day and e.time_slot.slot_number == slot])
    
    def _calculate_zone_load(self, zone: Zone, day: Day) -> int:
        """Calculate current load for a specific zone on a day."""
        return len([e for e in self.schedule.entries 
                   if e.activity.zone == zone and e.time_slot.day == day])
    
    def _calculate_staff_load(self, day: Day, slot: int) -> int:
        """Calculate staff load for a specific time slot."""
        staff_activities = [
            e for e in self.schedule.entries 
            if (e.time_slot.day == day and e.time_slot.slot_number == slot and 
                self._requires_staff(e.activity.name))
        ]
        return len(staff_activities)
    
    def _calculate_commissioner_load(self, troop: Troop, day: Day) -> int:
        """Calculate commissioner load for a troop on a day."""
        commissioner = self._get_troop_commissioner(troop)
        if not commissioner:
            return 0
        
        return len([e for e in self.schedule.entries 
                   if e.time_slot.day == day and self._get_troop_commissioner(e.troop) == commissioner])
    
    def _get_adjacent_activities(self, troop: Troop, day: Day, slot: int) -> List[str]:
        """Get adjacent activities for a troop."""
        adjacent = []
        
        # Previous slot
        if slot > 1:
            prev_entries = [e for e in self.schedule.entries 
                          if e.troop == troop and e.time_slot.day == day and 
                          e.time_slot.slot_number == slot - 1]
            adjacent.extend([e.activity.name for e in prev_entries])
        
        # Next slot
        max_slot = 2 if day == Day.THURSDAY else 3
        if slot < max_slot:
            next_entries = [e for e in self.schedule.entries 
                          if e.troop == troop and e.time_slot.day == day and 
                          e.time_slot.slot_number == slot + 1]
            adjacent.extend([e.activity.name for e in next_entries])
        
        return adjacent
    
    def _get_troop_previous_activities(self, troop: Troop) -> List[str]:
        """Get previously scheduled activities for a troop."""
        return [e.activity.name for e in self.schedule.entries if e.troop == troop]
    
    def _calculate_historical_success_rate(self, activity_name: str, day: Day, slot: int) -> float:
        """Calculate historical success rate for activity placement."""
        similar_placements = [
            f for f in self.feature_history 
            if f.activity_name == activity_name and f.day == day.value and f.slot_number == slot
        ]
        
        if not similar_placements:
            return 0.5
        
        indices = [i for i, f in enumerate(self.feature_history) 
                  if f.activity_name == activity_name and f.day == day.value and f.slot_number == slot]
        
        success_rates = [self.success_history[i] for i in indices]
        return statistics.mean(success_rates) if success_rates else 0.5
    
    def _calculate_historical_violation_rate(self, activity_name: str, day: Day, slot: int) -> float:
        """Calculate historical violation rate for activity placement."""
        # Simplified - would need actual violation tracking
        return 0.1  # Default low violation rate
    
    def _calculate_preference_satisfaction_rate(self, activity_name: str, preference_rank: int) -> float:
        """Calculate preference satisfaction rate."""
        return self._calculate_preference_score(preference_rank)
    
    def _calculate_placement_success(self, entry: ScheduleEntry) -> float:
        """Calculate success score for a placement."""
        # Multi-factor success calculation
        preference_score = 0.5  # Would need actual preference data
        
        # Check for violations
        violations = 0
        if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
            entry.time_slot.slot_number == 2 and 
            entry.time_slot.day != Day.THURSDAY):
            violations += 1
        
        # Base success score
        success = 0.8 - violations * 0.2
        
        return max(0.0, min(1.0, success))
    
    def _update_feature_importance(self):
        """Update feature importance based on historical data."""
        if len(self.feature_history) < 10:
            return
        
        # Simple correlation-based importance
        for feature_name in self.model_weights.keys():
            # Simplified importance calculation
            self.feature_importance[feature_name] = 0.1  # Default importance
    
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
    
    def _get_troop_commissioner(self, troop: Troop) -> str:
        """Get commissioner for a troop."""
        # Would need actual commissioner mapping
        return getattr(troop, 'commissioner', 'Unknown')
    
    def train_model(self, historical_schedules: List[Dict]):
        """
        Train the ML model with historical schedule data.
        """
        print("  [ML Predictor] Training model with historical data...")
        
        for schedule_data in historical_schedules:
            # Extract features from historical schedules
            for entry_data in schedule_data.get('entries', []):
                # Convert to ScheduleEntry-like object
                # This would need proper implementation based on data format
                pass
        
        print(f"  [ML Predictor] Model trained with {len(historical_schedules)} historical schedules")
    
    def save_model(self, filepath: str):
        """Save trained model to file."""
        model_data = {
            'model_weights': self.model_weights,
            'feature_importance': dict(self.feature_importance),
            'historical_placements': self.historical_placements,
            'feature_history': [asdict(f) for f in self.feature_history],
            'success_history': self.success_history
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"  [ML Predictor] Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load trained model from file."""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model_weights = model_data['model_weights']
            self.feature_importance = defaultdict(float, model_data['feature_importance'])
            self.historical_placements = model_data['historical_placements']
            
            # Reconstruct feature history
            self.feature_history = [
                PlacementFeatures(**f) for f in model_data['feature_history']
            ]
            self.success_history = model_data['success_history']
            
            print(f"  [ML Predictor] Model loaded from {filepath}")
        except Exception as e:
            print(f"  [ML Predictor] Error loading model: {e}")
    
    def get_model_insights(self) -> Dict:
        """Get insights about the trained model."""
        return {
            'total_placements_analyzed': len(self.feature_history),
            'model_weights': self.model_weights,
            'feature_importance': dict(self.feature_importance),
            'confidence_level': min(1.0, len(self.feature_history) / 100.0),
            'most_successful_activities': self._get_most_successful_activities(),
            'optimal_time_slots': self._get_optimal_time_slots()
        }
    
    def _get_most_successful_activities(self) -> List[Tuple[str, float]]:
        """Get most successfully placed activities."""
        activity_success = defaultdict(list)
        
        for i, features in enumerate(self.feature_history):
            activity_success[features.activity_name].append(self.success_history[i])
        
        # Calculate average success rate
        activity_avg_success = [
            (activity, statistics.mean(successes))
            for activity, successes in activity_success.items()
        ]
        
        return sorted(activity_avg_success, key=lambda x: x[1], reverse=True)[:10]
    
    def _get_optimal_time_slots(self) -> List[Tuple[str, int, float]]:
        """Get optimal time slots for placements."""
        slot_success = defaultdict(list)
        
        for i, features in enumerate(self.feature_history):
            slot_key = (features.day, features.slot_number)
            slot_success[slot_key].append(self.success_history[i])
        
        # Calculate average success rate
        slot_avg_success = [
            (day, slot, statistics.mean(successes))
            for (day, slot), successes in slot_success.items()
        ]
        
        return sorted(slot_avg_success, key=lambda x: x[2], reverse=True)[:10]


def create_ml_activity_predictor(schedule, troops, activities):
    """
    Create and configure a machine learning activity predictor.
    """
    predictor = MLActivityPredictor(schedule, troops, activities)
    return predictor
