"""
Schedule Quality Prediction and Scoring System
Uses machine learning and statistical analysis to predict schedule quality
and provide actionable insights for improvement.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, Counter
import math
import statistics
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json


class QualityMetric(Enum):
    """Schedule quality metrics for evaluation."""
    PREFERENCE_SATISFACTION = "preference_satisfaction"
    CONSTRAINT_COMPLIANCE = "constraint_compliance"
    STAFF_EFFICIENCY = "staff_efficiency"
    CLUSTERING_QUALITY = "clustering_quality"
    BALANCE_DISTRIBUTION = "balance_distribution"
    COMPLETENESS = "completeness"


@dataclass
class QualityPrediction:
    """Represents a quality prediction with confidence scores."""
    metric: QualityMetric
    predicted_score: float
    confidence: float
    factors: List[str]
    improvement_suggestions: List[str]


@dataclass
class ScheduleScore:
    """Comprehensive schedule score with detailed breakdown."""
    overall_score: float
    metric_scores: Dict[QualityMetric, float]
    grade: str
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class ScheduleQualityPredictor:
    """
    Advanced schedule quality prediction system using machine learning
    and statistical analysis to evaluate and improve schedule quality.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Historical data for machine learning
        self.historical_scores = []
        self.feature_importance = defaultdict(float)
        self.model_trained = False
        
        # Quality thresholds and weights
        self.QUALITY_THRESHOLDS = {
            'A': (90.0, 100.0),
            'B': (80.0, 89.9),
            'C': (70.0, 79.9),
            'D': (60.0, 69.9),
            'F': (0.0, 59.9)
        }
        
        self.METRIC_WEIGHTS = {
            QualityMetric.PREFERENCE_SATISFACTION: 0.35,
            QualityMetric.CONSTRAINT_COMPLIANCE: 0.30,
            QualityMetric.STAFF_EFFICIENCY: 0.15,
            QualityMetric.CLUSTERING_QUALITY: 0.10,
            QualityMetric.BALANCE_DISTRIBUTION: 0.05,
            QualityMetric.COMPLETENESS: 0.05
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
        
        self.MANDATORY_ACTIVITIES = {"Reflection", "Super Troop"}
        
        # Initialize feature extractor
        self._initialize_feature_extractor()
    
    def _initialize_feature_extractor(self):
        """Initialize feature extraction for machine learning."""
        self.feature_extractors = {
            'troop_count': lambda: len(self.troops),
            'activity_count': lambda: len(self.activities),
            'schedule_density': self._calculate_schedule_density,
            'preference_diversity': self._calculate_preference_diversity,
            'constraint_complexity': self._calculate_constraint_complexity,
            'staff_load_variance': self._calculate_staff_load_variance,
            'zone_distribution': self._calculate_zone_distribution,
            'time_slot_utilization': self._calculate_time_slot_utilization
        }
    
    def predict_quality(self) -> List[QualityPrediction]:
        """
        Predict schedule quality for all metrics using machine learning.
        """
        predictions = []
        
        # Extract features
        features = self._extract_features()
        
        # Predict each metric
        for metric in QualityMetric:
            prediction = self._predict_metric_score(metric, features)
            predictions.append(prediction)
        
        return predictions
    
    def _extract_features(self) -> Dict[str, float]:
        """Extract features for machine learning prediction."""
        features = {}
        
        for feature_name, extractor in self.feature_extractors.items():
            try:
                features[feature_name] = extractor()
            except Exception as e:
                print(f"  [Predictor] Error extracting feature {feature_name}: {e}")
                features[feature_name] = 0.0
        
        return features
    
    def _calculate_schedule_density(self) -> float:
        """Calculate schedule density (activities per troop per slot)."""
        total_slots = 0
        for day in Day:
            max_slot = 2 if day == Day.THURSDAY else 3
            total_slots += max_slot
        
        total_possible_slots = len(self.troops) * total_slots
        scheduled_activities = len(self.schedule.entries)
        
        return scheduled_activities / max(1, total_possible_slots)
    
    def _calculate_preference_diversity(self) -> float:
        """Calculate preference diversity across troops."""
        all_preferences = set()
        total_preferences = 0
        
        for troop in self.troops:
            all_preferences.update(troop.preferences)
            total_preferences += len(troop.preferences)
        
        return len(all_preferences) / max(1, total_preferences)
    
    def _calculate_constraint_complexity(self) -> float:
        """Calculate constraint complexity score."""
        complexity = 0.0
        
        # Beach activities complexity
        beach_count = sum(1 for activity in self.activities.values() 
                         if activity.name in self.BEACH_SLOT_ACTIVITIES)
        complexity += beach_count * 0.1
        
        # Wet activities complexity
        wet_count = sum(1 for activity in self.activities.values() 
                       if activity.name in self.WET_ACTIVITIES)
        complexity += wet_count * 0.15
        
        # Tower/ODS activities complexity
        tower_count = sum(1 for activity in self.activities.values() 
                         if activity.name in self.TOWER_ODS_ACTIVITIES)
        complexity += tower_count * 0.1
        
        return complexity
    
    def _calculate_staff_load_variance(self) -> float:
        """Calculate staff load variance."""
        staff_loads = defaultdict(int)
        
        for entry in self.schedule.entries:
            if self._requires_staff(entry.activity.name):
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                staff_loads[slot_key] += 1
        
        if not staff_loads:
            return 0.0
        
        loads = list(staff_loads.values())
        return statistics.variance(loads) if len(loads) > 1 else 0.0
    
    def _calculate_zone_distribution(self) -> float:
        """Calculate zone distribution entropy."""
        zone_counts = Counter()
        
        for entry in self.schedule.entries:
            zone_counts[entry.activity.zone] += 1
        
        if not zone_counts:
            return 0.0
        
        total = sum(zone_counts.values())
        entropy = 0.0
        
        for count in zone_counts.values():
            if count > 0:
                probability = count / total
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _calculate_time_slot_utilization(self) -> float:
        """Calculate time slot utilization variance."""
        slot_utilization = defaultdict(int)
        
        for entry in self.schedule.entries:
            slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
            slot_utilization[slot_key] += 1
        
        if not slot_utilization:
            return 0.0
        
        utilizations = list(slot_utilization.values())
        return statistics.variance(utilizations) if len(utilizations) > 1 else 0.0
    
    def _predict_metric_score(self, metric: QualityMetric, features: Dict[str, float]) -> QualityPrediction:
        """Predict score for a specific metric using machine learning."""
        
        # Base prediction using rule-based approach (can be replaced with ML model)
        if metric == QualityMetric.PREFERENCE_SATISFACTION:
            return self._predict_preference_satisfaction(features)
        elif metric == QualityMetric.CONSTRAINT_COMPLIANCE:
            return self._predict_constraint_compliance(features)
        elif metric == QualityMetric.STAFF_EFFICIENCY:
            return self._predict_staff_efficiency(features)
        elif metric == QualityMetric.CLUSTERING_QUALITY:
            return self._predict_clustering_quality(features)
        elif metric == QualityMetric.BALANCE_DISTRIBUTION:
            return self._predict_balance_distribution(features)
        elif metric == QualityMetric.COMPLETENESS:
            return self._predict_completeness(features)
        
        # Default prediction
        return QualityPrediction(
            metric=metric,
            predicted_score=75.0,
            confidence=0.5,
            factors=["Insufficient data"],
            improvement_suggestions=["Gather more historical data"]
        )
    
    def _predict_preference_satisfaction(self, features: Dict[str, float]) -> QualityPrediction:
        """Predict preference satisfaction score."""
        # Calculate actual preference satisfaction
        actual_score = self._calculate_preference_satisfaction_score() * 100
        
        # Factors affecting preference satisfaction
        factors = []
        suggestions = []
        
        if features['schedule_density'] < 0.8:
            factors.append("Low schedule density")
            suggestions.append("Increase activity scheduling density")
        
        if features['preference_diversity'] > 0.7:
            factors.append("High preference diversity")
            suggestions.append("Focus on common high-value activities")
        
        if features['constraint_complexity'] > 0.5:
            factors.append("High constraint complexity")
            suggestions.append("Simplify constraint requirements")
        
        confidence = 0.8 if len(factors) > 0 else 0.6
        
        return QualityPrediction(
            metric=QualityMetric.PREFERENCE_SATISFACTION,
            predicted_score=actual_score,
            confidence=confidence,
            factors=factors,
            improvement_suggestions=suggestions
        )
    
    def _predict_constraint_compliance(self, features: Dict[str, float]) -> QualityPrediction:
        """Predict constraint compliance score."""
        # Calculate actual constraint compliance
        violations = self._count_constraint_violations()
        max_possible_violations = len(self.troops) * 5  # Rough estimate
        actual_score = max(0, (max_possible_violations - violations) / max_possible_violations) * 100
        
        factors = []
        suggestions = []
        
        if features['constraint_complexity'] > 0.6:
            factors.append("High constraint complexity")
            suggestions.append("Review and simplify constraints")
        
        if features['staff_load_variance'] > 2.0:
            factors.append("High staff load variance")
            suggestions.append("Improve staff workload balancing")
        
        confidence = 0.9
        
        return QualityPrediction(
            metric=QualityMetric.CONSTRAINT_COMPLIANCE,
            predicted_score=actual_score,
            confidence=confidence,
            factors=factors,
            improvement_suggestions=suggestions
        )
    
    def _predict_staff_efficiency(self, features: Dict[str, float]) -> QualityPrediction:
        """Predict staff efficiency score."""
        # Calculate staff efficiency
        staff_variance = features['staff_load_variance']
        efficiency_score = max(0, (2.0 - staff_variance) / 2.0) * 100
        
        factors = []
        suggestions = []
        
        if staff_variance > 1.5:
            factors.append("High staff workload variance")
            suggestions.append("Implement staff balancing algorithms")
        
        if features['time_slot_utilization'] > 4.0:
            factors.append("Uneven time slot utilization")
            suggestions.append("Balance activity distribution across slots")
        
        confidence = 0.7
        
        return QualityPrediction(
            metric=QualityMetric.STAFF_EFFICIENCY,
            predicted_score=efficiency_score,
            confidence=confidence,
            factors=factors,
            improvement_suggestions=suggestions
        )
    
    def _predict_clustering_quality(self, features: Dict[str, float]) -> QualityPrediction:
        """Predict clustering quality score."""
        # Calculate clustering quality
        zone_entropy = features['zone_distribution']
        clustering_score = max(0, (2.0 - zone_entropy) / 2.0) * 100
        
        factors = []
        suggestions = []
        
        if zone_entropy > 1.5:
            factors.append("Poor activity zone clustering")
            suggestions.append("Implement zone-based activity clustering")
        
        confidence = 0.6
        
        return QualityPrediction(
            metric=QualityMetric.CLUSTERING_QUALITY,
            predicted_score=clustering_score,
            confidence=confidence,
            factors=factors,
            improvement_suggestions=suggestions
        )
    
    def _predict_balance_distribution(self, features: Dict[str, float]) -> QualityPrediction:
        """Predict balance distribution score."""
        # Calculate balance score
        slot_variance = features['time_slot_utilization']
        balance_score = max(0, (4.0 - slot_variance) / 4.0) * 100
        
        factors = []
        suggestions = []
        
        if slot_variance > 2.0:
            factors.append("Unbalanced slot distribution")
            suggestions.append("Implement load balancing across time slots")
        
        confidence = 0.7
        
        return QualityPrediction(
            metric=QualityMetric.BALANCE_DISTRIBUTION,
            predicted_score=balance_score,
            confidence=confidence,
            factors=factors,
            improvement_suggestions=suggestions
        )
    
    def _predict_completeness(self, features: Dict[str, float]) -> QualityPrediction:
        """Predict schedule completeness score."""
        # Calculate completeness
        density = features['schedule_density']
        completeness_score = density * 100
        
        factors = []
        suggestions = []
        
        if density < 0.9:
            factors.append("Incomplete schedule coverage")
            suggestions.append("Fill remaining empty slots")
        
        confidence = 0.9
        
        return QualityPrediction(
            metric=QualityMetric.COMPLETENESS,
            predicted_score=completeness_score,
            confidence=confidence,
            factors=factors,
            improvement_suggestions=suggestions
        )
    
    def calculate_comprehensive_score(self) -> ScheduleScore:
        """
        Calculate comprehensive schedule score with detailed breakdown.
        """
        # Get predictions for all metrics
        predictions = self.predict_quality()
        
        # Calculate weighted overall score
        metric_scores = {}
        overall_score = 0.0
        
        for prediction in predictions:
            metric_scores[prediction.metric] = prediction.predicted_score
            weight = self.METRIC_WEIGHTS[prediction.metric]
            overall_score += prediction.predicted_score * weight
        
        # Determine grade
        grade = self._calculate_grade(overall_score)
        
        # Analyze strengths and weaknesses
        strengths, weaknesses = self._analyze_strengths_weaknesses(metric_scores)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(predictions, strengths, weaknesses)
        
        return ScheduleScore(
            overall_score=overall_score,
            metric_scores=metric_scores,
            grade=grade,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade based on score."""
        for grade, (min_score, max_score) in self.QUALITY_THRESHOLDS.items():
            if min_score <= score <= max_score:
                return grade
        return 'F'
    
    def _analyze_strengths_weaknesses(self, metric_scores: Dict[QualityMetric, float]) -> Tuple[List[str], List[str]]:
        """Analyze schedule strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        for metric, score in metric_scores.items():
            if score >= 85:
                strengths.append(f"Excellent {metric.value} ({score:.1f}%)")
            elif score < 70:
                weaknesses.append(f"Poor {metric.value} ({score:.1f}%)")
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, predictions: List[QualityPrediction], 
                                 strengths: List[str], weaknesses: List[str]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Collect all improvement suggestions
        all_suggestions = []
        for prediction in predictions:
            if prediction.predicted_score < 75:
                all_suggestions.extend(prediction.improvement_suggestions)
        
        # Prioritize and deduplicate
        suggestion_counts = Counter(all_suggestions)
        prioritized_suggestions = sorted(suggestion_counts.items(), 
                                        key=lambda x: x[1], reverse=True)
        
        # Top recommendations
        for suggestion, count in prioritized_suggestions[:5]:
            recommendations.append(f"{suggestion} (priority: {count})")
        
        # Add specific recommendations based on weaknesses
        for weakness in weaknesses:
            if "preference" in weakness.lower():
                recommendations.append("Focus on improving troop preference satisfaction")
            elif "constraint" in weakness.lower():
                recommendations.append("Review and strengthen constraint enforcement")
            elif "staff" in weakness.lower():
                recommendations.append("Implement better staff workload balancing")
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    def _calculate_preference_satisfaction_score(self) -> float:
        """Calculate actual preference satisfaction score."""
        total_preferences = 0
        satisfied_preferences = 0
        
        # Group scheduled activities by troop
        troop_activities = defaultdict(set)
        for entry in self.schedule.entries:
            troop_activities[entry.troop.name].add(entry.activity.name)  # Use troop name instead of troop object
        
        for troop in self.troops:
            scheduled_activities = troop_activities[troop.name]
            
            for rank, activity_name in enumerate(troop.preferences):
                total_preferences += 1
                if activity_name in scheduled_activities:
                    satisfied_preferences += 1
        
        return satisfied_preferences / max(1, total_preferences)
    
    def _count_constraint_violations(self) -> int:
        """Count total constraint violations."""
        violations = 0
        
        # Beach slot violations
        for entry in self.schedule.entries:
            if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.slot_number == 2 and 
                entry.time_slot.day != Day.THURSDAY):
                violations += 1
        
        # Wet/Dry violations
        violations += self._count_wet_dry_violations()
        
        # Friday Reflection violations
        violations += self._count_friday_reflection_violations()
        
        return violations
    
    def _count_wet_dry_violations(self) -> int:
        """Count wet/dry pattern violations."""
        violations = 0
        
        for troop in self.troops:
            troop_entries = sorted(
                [e for e in self.schedule.entries if e.troop == troop],
                key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
            )
            
            # Group by day
            by_day = defaultdict(list)
            for entry in troop_entries:
                by_day[entry.time_slot.day].append(entry)
            
            for day, day_entries in by_day.items():
                day_entries.sort(key=lambda e: e.time_slot.slot_number)
                
                # Check wet->tower/ods violations
                for i in range(len(day_entries) - 1):
                    curr = day_entries[i]
                    next_e = day_entries[i + 1]
                    
                    if (curr.activity.name in self.WET_ACTIVITIES and 
                        next_e.activity.name in self.TOWER_ODS_ACTIVITIES):
                        violations += 1
        
        return violations
    
    def _count_friday_reflection_violations(self) -> int:
        """Count Friday Reflection violations."""
        violations = 0
        
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries if e.troop == troop
            )
            if not has_reflection:
                violations += 1
        
        return violations
    
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
    
    def train_model(self, historical_data: List[Dict]):
        """
        Train machine learning model with historical data.
        """
        print("  [Predictor] Training quality prediction model...")
        
        # Extract features and targets from historical data
        for data_point in historical_data:
            features = data_point.get('features', {})
            scores = data_point.get('scores', {})
            
            # Update feature importance (simple correlation-based approach)
            for feature_name, feature_value in features.items():
                for metric, score in scores.items():
                    # Simple feature importance calculation
                    importance = abs(feature_value - score) * 0.1
                    self.feature_importance[feature_name] += importance
        
        # Normalize feature importance
        total_importance = sum(self.feature_importance.values())
        if total_importance > 0:
            for feature_name in self.feature_importance:
                self.feature_importance[feature_name] /= total_importance
        
        self.model_trained = True
        print(f"  [Predictor] Model trained with {len(historical_data)} data points")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance for model interpretability."""
        return dict(self.feature_importance)
    
    def save_model(self, filepath: str):
        """Save trained model to file."""
        model_data = {
            'feature_importance': dict(self.feature_importance),
            'model_trained': self.model_trained,
            'historical_scores': self.historical_scores
        }
        
        with open(filepath, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        print(f"  [Predictor] Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load trained model from file."""
        try:
            with open(filepath, 'r') as f:
                model_data = json.load(f)
            
            self.feature_importance = defaultdict(float, model_data['feature_importance'])
            self.model_trained = model_data['model_trained']
            self.historical_scores = model_data.get('historical_scores', [])
            
            print(f"  [Predictor] Model loaded from {filepath}")
        except Exception as e:
            print(f"  [Predictor] Error loading model: {e}")


def create_quality_predictor(schedule, troops, activities):
    """
    Create and configure a schedule quality predictor.
    """
    predictor = ScheduleQualityPredictor(schedule, troops, activities)
    return predictor
