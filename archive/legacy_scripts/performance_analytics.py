"""
Comprehensive Performance Analytics Dashboard
Provides detailed analytics, visualization data, and performance insights
for the Summer Camp Scheduler system.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, Counter
import statistics
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import math


@dataclass
class PerformanceMetrics:
    """Performance metrics for scheduling operations."""
    total_scheduling_time: float
    constraint_checks_performed: int
    violations_detected: int
    violations_fixed: int
    preference_satisfaction_rate: float
    staff_efficiency_score: float
    clustering_quality: float
    schedule_completeness: float


@dataclass
class AnalyticsData:
    """Comprehensive analytics data structure."""
    timestamp: str
    schedule_summary: Dict
    performance_metrics: PerformanceMetrics
    constraint_violations: Dict
    preference_analysis: Dict
    staff_analysis: Dict
    clustering_analysis: Dict
    quality_trends: List[Dict]
    recommendations: List[str]


class PerformanceAnalytics:
    """
    Comprehensive performance analytics system for the Summer Camp Scheduler.
    Provides detailed insights, trend analysis, and actionable recommendations.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Performance tracking
        self.start_time = None
        self.end_time = None
        self.constraint_checks = 0
        self.violations_detected = 0
        self.violations_fixed = 0
        
        # Historical data
        self.analytics_history = []
        self.performance_trends = defaultdict(list)
        
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
    
    def start_timing(self):
        """Start performance timing."""
        self.start_time = time.time()
    
    def end_timing(self):
        """End performance timing."""
        if self.start_time:
            self.end_time = time.time()
    
    def increment_constraint_checks(self, count: int = 1):
        """Increment constraint check counter."""
        self.constraint_checks += count
    
    def increment_violations_detected(self, count: int = 1):
        """Increment violations detected counter."""
        self.violations_detected += count
    
    def increment_violations_fixed(self, count: int = 1):
        """Increment violations fixed counter."""
        self.violations_fixed += count
    
    def generate_comprehensive_analytics(self) -> AnalyticsData:
        """
        Generate comprehensive analytics data for the current schedule.
        """
        print("=== PERFORMANCE ANALYTICS DASHBOARD ===")
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics()
        
        # Generate schedule summary
        schedule_summary = self._generate_schedule_summary()
        
        # Analyze constraint violations
        constraint_violations = self._analyze_constraint_violations()
        
        # Analyze preferences
        preference_analysis = self._analyze_preferences()
        
        # Analyze staff performance
        staff_analysis = self._analyze_staff_performance()
        
        # Analyze clustering
        clustering_analysis = self._analyze_clustering()
        
        # Generate quality trends
        quality_trends = self._generate_quality_trends()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            performance_metrics, constraint_violations, 
            preference_analysis, staff_analysis, clustering_analysis
        )
        
        # Create analytics data
        analytics_data = AnalyticsData(
            timestamp=datetime.now().isoformat(),
            schedule_summary=schedule_summary,
            performance_metrics=performance_metrics,
            constraint_violations=constraint_violations,
            preference_analysis=preference_analysis,
            staff_analysis=staff_analysis,
            clustering_analysis=clustering_analysis,
            quality_trends=quality_trends,
            recommendations=recommendations
        )
        
        # Store in history
        self.analytics_history.append(analytics_data)
        
        # Update trends
        self._update_performance_trends(analytics_data)
        
        return analytics_data
    
    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        scheduling_time = (self.end_time or time.time()) - (self.start_time or 0)
        
        # Calculate various performance scores
        preference_satisfaction = self._calculate_preference_satisfaction_rate()
        staff_efficiency = self._calculate_staff_efficiency_score()
        clustering_quality = self._calculate_clustering_quality()
        schedule_completeness = self._calculate_schedule_completeness()
        
        return PerformanceMetrics(
            total_scheduling_time=scheduling_time,
            constraint_checks_performed=self.constraint_checks,
            violations_detected=self.violations_detected,
            violations_fixed=self.violations_fixed,
            preference_satisfaction_rate=preference_satisfaction,
            staff_efficiency_score=staff_efficiency,
            clustering_quality=clustering_quality,
            schedule_completeness=schedule_completeness
        )
    
    def _generate_schedule_summary(self) -> Dict:
        """Generate comprehensive schedule summary."""
        summary = {
            'total_troops': len(self.troops),
            'total_activities_scheduled': len(self.schedule.entries),
            'total_available_activities': len(self.activities),
            'unique_activities_scheduled': len(set(e.activity.name for e in self.schedule.entries)),
            'average_activities_per_troop': len(self.schedule.entries) / max(1, len(self.troops)),
            'schedule_density': self._calculate_schedule_density(),
            'zone_distribution': self._calculate_zone_distribution(),
            'day_distribution': self._calculate_day_distribution(),
            'slot_utilization': self._calculate_slot_utilization()
        }
        
        return summary
    
    def _analyze_constraint_violations(self) -> Dict:
        """Analyze constraint violations in detail."""
        violations = {
            'total_violations': 0,
            'violation_types': defaultdict(int),
            'violations_by_troop': defaultdict(int),
            'violations_by_day': defaultdict(int),
            'critical_violations': [],
            'fix_rate': self.violations_fixed / max(1, self.violations_detected)
        }
        
        # Analyze each type of violation
        beach_violations = self._analyze_beach_slot_violations()
        wet_dry_violations = self._analyze_wet_dry_violations()
        reflection_violations = self._analyze_friday_reflection_violations()
        exclusive_violations = self._analyze_exclusive_area_violations()
        
        # Aggregate violations
        violations['violation_types']['beach_slot'] = beach_violations['count']
        violations['violation_types']['wet_dry'] = wet_dry_violations['count']
        violations['violation_types']['friday_reflection'] = reflection_violations['count']
        violations['violation_types']['exclusive_area'] = exclusive_violations['count']
        
        violations['total_violations'] = sum(violations['violation_types'].values())
        
        # Detailed violation data
        violations['details'] = {
            'beach_slot': beach_violations,
            'wet_dry': wet_dry_violations,
            'friday_reflection': reflection_violations,
            'exclusive_area': exclusive_violations
        }
        
        return violations
    
    def _analyze_preferences(self) -> Dict:
        """Analyze preference satisfaction in detail."""
        analysis = {
            'overall_satisfaction_rate': 0.0,
            'top5_satisfaction': 0.0,
            'top10_satisfaction': 0.0,
            'top15_satisfaction': 0.0,
            'top20_satisfaction': 0.0,
            'satisfaction_by_troop': {},
            'most_popular_activities': [],
            'least_satisfied_troops': [],
            'preference_distribution': self._analyze_preference_distribution()
        }
        
        # Calculate satisfaction rates
        total_preferences = 0
        satisfied_preferences = 0
        top5_satisfied = 0
        top10_satisfied = 0
        top15_satisfied = 0
        top20_satisfied = 0
        
        troop_satisfaction = {}
        
        # Group scheduled activities by troop
        troop_activities = defaultdict(set)
        for entry in self.schedule.entries:
            troop_activities[entry.troop.name].add(entry.activity.name)  # Use troop name instead of troop object
        
        for troop in self.troops:
            scheduled_activities = troop_activities[troop.name]  # Use troop name as key
            troop_top5 = 0
            troop_top10 = 0
            troop_top15 = 0
            troop_top20 = 0
            troop_satisfied = 0
            
            for rank, activity_name in enumerate(troop.preferences):
                total_preferences += 1
                if activity_name in scheduled_activities:
                    satisfied_preferences += 1
                    troop_satisfied += 1
                    
                    if rank < 5:
                        top5_satisfied += 1
                        troop_top5 += 1
                    elif rank < 10:
                        top10_satisfied += 1
                        troop_top10 += 1
                    elif rank < 15:
                        top15_satisfied += 1
                        troop_top15 += 1
                    elif rank < 20:
                        top20_satisfied += 1
                        troop_top20 += 1
            
            # Calculate troop satisfaction rate
            troop_total_prefs = len(troop.preferences)
            troop_satisfaction_rate = troop_satisfied / max(1, troop_total_prefs)
            troop_satisfaction[troop.name] = {
                'satisfaction_rate': troop_satisfaction_rate,
                'top5_satisfied': troop_top5,
                'top10_satisfied': troop_top10,
                'total_preferences': troop_total_prefs
            }
        
        # Calculate overall rates
        analysis['overall_satisfaction_rate'] = satisfied_preferences / max(1, total_preferences)
        analysis['top5_satisfaction'] = top5_satisfied / max(1, len(self.troops) * 5)
        analysis['top10_satisfaction'] = top10_satisfied / max(1, len(self.troops) * 10)
        analysis['top15_satisfaction'] = top15_satisfied / max(1, len(self.troops) * 15)
        analysis['top20_satisfaction'] = top20_satisfied / max(1, len(self.troops) * 20)
        analysis['satisfaction_by_troop'] = troop_satisfaction
        
        # Find most popular activities
        activity_counts = Counter()
        for troop in self.troops:
            activity_counts.update(troop.preferences)
        
        analysis['most_popular_activities'] = activity_counts.most_common(10)
        
        # Find least satisfied troops
        least_satisfied = sorted(
            [(name, data['satisfaction_rate']) for name, data in troop_satisfaction.items()],
            key=lambda x: x[1]
        )[:5]
        analysis['least_satisfied_troops'] = least_satisfied
        
        return analysis
    
    def _analyze_staff_performance(self) -> Dict:
        """Analyze staff performance and workload distribution."""
        analysis = {
            'total_staff_requiring_activities': 0,
            'staff_loads_by_slot': {},
            'staff_load_variance': 0.0,
            'overloaded_slots': [],
            'underloaded_slots': [],
            'staff_efficiency_score': 0.0,
            'zone_staff_distribution': defaultdict(int)
        }
        
        # Calculate staff loads
        staff_loads = defaultdict(int)
        slot_entries = defaultdict(list)
        
        for entry in self.schedule.entries:
            if self._requires_staff(entry.activity.name):
                analysis['total_staff_requiring_activities'] += 1
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                staff_loads[slot_key] += 1
                slot_entries[slot_key].append(entry)
                
                # Track zone distribution
                analysis['zone_staff_distribution'][entry.activity.zone] += 1
        
        analysis['staff_loads_by_slot'] = dict(staff_loads)
        
        # Calculate variance
        if staff_loads:
            loads = list(staff_loads.values())
            analysis['staff_load_variance'] = statistics.variance(loads) if len(loads) > 1 else 0.0
            
            # Find overloaded/underloaded slots
            avg_load = statistics.mean(loads)
            for slot, load in staff_loads.items():
                if load > avg_load * 1.3:
                    analysis['overloaded_slots'].append({'slot': slot, 'load': load})
                elif load < avg_load * 0.7:
                    analysis['underloaded_slots'].append({'slot': slot, 'load': load})
        
        # Calculate efficiency score
        max_acceptable_variance = 2.0
        analysis['staff_efficiency_score'] = max(0, (max_acceptable_variance - analysis['staff_load_variance']) / max_acceptable_variance)
        
        return analysis
    
    def _analyze_clustering(self) -> Dict:
        """Analyze activity clustering efficiency."""
        analysis = {
            'zone_clustering_efficiency': {},
            'overall_clustering_score': 0.0,
            'clustering_opportunities': [],
            'well_clustered_zones': [],
            'poorly_clustered_zones': []
        }
        
        # Group activities by zone
        zone_activities = defaultdict(list)
        for entry in self.schedule.entries:
            zone = entry.activity.zone
            zone_activities[zone].append(entry)
        
        total_efficiency = 0.0
        zone_count = 0
        
        for zone, entries in zone_activities.items():
            if len(entries) < 2:
                continue
            
            zone_count += 1
            days_used = set(e.time_slot.day for e in entries)
            max_possible_days = len(Day)
            
            # Calculate clustering efficiency
            efficiency = 1.0 - (len(days_used) - 1) / max_possible_days
            total_efficiency += efficiency
            
            zone_analysis = {
                'activities_count': len(entries),
                'days_used': len(days_used),
                'efficiency': efficiency,
                'days_distribution': Counter(e.time_slot.day for e in entries)
            }
            
            analysis['zone_clustering_efficiency'][zone.value] = zone_analysis
            
            # Identify well/poorly clustered zones
            if efficiency >= 0.8:
                analysis['well_clustered_zones'].append(zone.value)
            elif efficiency < 0.5:
                analysis['poorly_clustered_zones'].append(zone.value)
        
        # Calculate overall clustering score
        analysis['overall_clustering_score'] = total_efficiency / max(1, zone_count)
        
        # Identify clustering opportunities
        for zone, entries in zone_activities.items():
            if len(entries) >= 2:
                days = set(e.time_slot.day for e in entries)
                if len(days) > len(entries) / 2:  # Many days used for few activities
                    analysis['clustering_opportunities'].append({
                        'zone': zone.value,
                        'activities': len(entries),
                        'days_used': len(days),
                        'potential_improvement': (len(days) - math.ceil(len(entries) / 2)) / len(days)
                    })
        
        return analysis
    
    def _generate_quality_trends(self) -> List[Dict]:
        """Generate quality trend analysis."""
        if len(self.analytics_history) < 2:
            return []
        
        trends = []
        
        # Get recent history
        recent_history = self.analytics_history[-10:]  # Last 10 analyses
        
        for i in range(1, len(recent_history)):
            current = recent_history[i]
            previous = recent_history[i - 1]
            
            trend = {
                'timestamp': current.timestamp,
                'preference_satisfaction_change': (
                    current.preference_analysis['overall_satisfaction_rate'] - 
                    previous.preference_analysis['overall_satisfaction_rate']
                ),
                'staff_efficiency_change': (
                    current.staff_analysis['staff_efficiency_score'] - 
                    previous.staff_analysis['staff_efficiency_score']
                ),
                'clustering_quality_change': (
                    current.clustering_analysis['overall_clustering_score'] - 
                    previous.clustering_analysis['overall_clustering_score']
                ),
                'violations_change': (
                    current.constraint_violations['total_violations'] - 
                    previous.constraint_violations['total_violations']
                )
            }
            
            trends.append(trend)
        
        return trends
    
    def _generate_recommendations(self, performance_metrics: PerformanceMetrics,
                                 constraint_violations: Dict,
                                 preference_analysis: Dict,
                                 staff_analysis: Dict,
                                 clustering_analysis: Dict) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Performance recommendations
        if performance_metrics.total_scheduling_time > 30.0:
            recommendations.append("Consider optimizing scheduling algorithm for better performance")
        
        if performance_metrics.violations_detected > 0:
            fix_rate = performance_metrics.violations_fixed / max(1, performance_metrics.violations_detected)
            if fix_rate < 0.8:
                recommendations.append("Improve constraint violation detection and fixing mechanisms")
        
        # Preference recommendations
        if preference_analysis['overall_satisfaction_rate'] < 0.8:
            recommendations.append("Focus on improving troop preference satisfaction")
        
        if preference_analysis['top5_satisfaction'] < 0.9:
            recommendations.append("Prioritize Top 5 preferences in scheduling algorithm")
        
        # Staff recommendations
        if staff_analysis['staff_load_variance'] > 2.0:
            recommendations.append("Implement better staff workload balancing")
        
        if len(staff_analysis['overloaded_slots']) > 3:
            recommendations.append("Redistribute activities to reduce staff overload")
        
        # Clustering recommendations
        if clustering_analysis['overall_clustering_score'] < 0.7:
            recommendations.append("Improve activity zone clustering for better efficiency")
        
        if len(clustering_analysis['clustering_opportunities']) > 2:
            recommendations.append("Exploit identified clustering opportunities for better organization")
        
        # Constraint-specific recommendations
        if constraint_violations['violation_types']['beach_slot'] > 0:
            recommendations.append("Fix beach slot constraint violations")
        
        if constraint_violations['violation_types']['friday_reflection'] > 0:
            recommendations.append("Ensure all troops have Friday Reflection scheduled")
        
        if constraint_violations['violation_types']['wet_dry'] > 0:
            recommendations.append("Address wet/dry pattern violations")
        
        return recommendations
    
    def _update_performance_trends(self, analytics_data: AnalyticsData):
        """Update performance trend data."""
        self.performance_trends['preference_satisfaction'].append(
            analytics_data.preference_analysis['overall_satisfaction_rate']
        )
        self.performance_trends['staff_efficiency'].append(
            analytics_data.staff_analysis['staff_efficiency_score']
        )
        self.performance_trends['clustering_quality'].append(
            analytics_data.clustering_analysis['overall_clustering_score']
        )
        self.performance_trends['total_violations'].append(
            analytics_data.constraint_violations['total_violations']
        )
    
    # Helper methods for calculations
    def _calculate_preference_satisfaction_rate(self) -> float:
        """Calculate preference satisfaction rate."""
        total_preferences = 0
        satisfied_preferences = 0
        
        troop_activities = defaultdict(set)
        for entry in self.schedule.entries:
            troop_activities[entry.troop.name].add(entry.activity.name)  # Use troop name instead of troop object
        
        for troop in self.troops:
            scheduled_activities = troop_activities[troop.name]  # Use troop name as key
            for activity_name in troop.preferences:
                total_preferences += 1
                if activity_name in scheduled_activities:
                    satisfied_preferences += 1
        
        return satisfied_preferences / max(1, total_preferences)
    
    def _calculate_staff_efficiency_score(self) -> float:
        """Calculate staff efficiency score."""
        staff_loads = defaultdict(int)
        
        for entry in self.schedule.entries:
            if self._requires_staff(entry.activity.name):
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                staff_loads[slot_key] += 1
        
        if not staff_loads:
            return 1.0
        
        loads = list(staff_loads.values())
        variance = statistics.variance(loads) if len(loads) > 1 else 0.0
        max_acceptable_variance = 2.0
        
        return max(0, (max_acceptable_variance - variance) / max_acceptable_variance)
    
    def _calculate_clustering_quality(self) -> float:
        """Calculate clustering quality score."""
        zone_activities = defaultdict(list)
        for entry in self.schedule.entries:
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
            
            efficiency = 1.0 - (len(days_used) - 1) / max_possible_days
            total_efficiency += efficiency
        
        return total_efficiency / max(1, zone_count)
    
    def _calculate_schedule_completeness(self) -> float:
        """Calculate schedule completeness."""
        total_slots = 0
        for day in Day:
            max_slot = 2 if day == Day.THURSDAY else 3
            total_slots += max_slot
        
        total_possible_slots = len(self.troops) * total_slots
        scheduled_activities = len(self.schedule.entries)
        
        return scheduled_activities / max(1, total_possible_slots)
    
    def _calculate_schedule_density(self) -> float:
        """Calculate schedule density."""
        return self._calculate_schedule_completeness()
    
    def _calculate_zone_distribution(self) -> Dict:
        """Calculate zone distribution."""
        zone_counts = Counter()
        for entry in self.schedule.entries:
            zone_counts[entry.activity.zone.value] += 1
        return dict(zone_counts)
    
    def _calculate_day_distribution(self) -> Dict:
        """Calculate day distribution."""
        day_counts = Counter()
        for entry in self.schedule.entries:
            day_counts[entry.time_slot.day.value] += 1
        return dict(day_counts)
    
    def _calculate_slot_utilization(self) -> Dict:
        """Calculate slot utilization."""
        slot_counts = Counter()
        for entry in self.schedule.entries:
            slot_key = f"{entry.time_slot.day.value}-{entry.time_slot.slot_number}"
            slot_counts[slot_key] += 1
        return dict(slot_counts)
    
    def _analyze_preference_distribution(self) -> Dict:
        """Analyze preference distribution patterns."""
        all_preferences = []
        for troop in self.troops:
            all_preferences.extend(troop.preferences)
        
        preference_counts = Counter(all_preferences)
        
        return {
            'total_unique_preferences': len(preference_counts),
            'most_common': preference_counts.most_common(10),
            'least_common': preference_counts.most_common()[-10:],
            'average_preference_frequency': statistics.mean(preference_counts.values()) if preference_counts else 0
        }
    
    # Detailed violation analysis methods
    def _analyze_beach_slot_violations(self) -> Dict:
        """Analyze beach slot violations."""
        violations = []
        
        for entry in self.schedule.entries:
            if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.slot_number == 2 and 
                entry.time_slot.day != Day.THURSDAY):
                violations.append({
                    'troop': entry.troop.name,
                    'activity': entry.activity.name,
                    'day': entry.time_slot.day.value,
                    'slot': entry.time_slot.slot_number
                })
        
        return {'count': len(violations), 'violations': violations}
    
    def _analyze_wet_dry_violations(self) -> Dict:
        """Analyze wet/dry violations."""
        violations = []
        
        for troop in self.troops:
            troop_entries = sorted(
                [e for e in self.schedule.entries if e.troop == troop],
                key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
            )
            
            by_day = defaultdict(list)
            for entry in troop_entries:
                by_day[entry.time_slot.day].append(entry)
            
            for day, day_entries in by_day.items():
                day_entries.sort(key=lambda e: e.time_slot.slot_number)
                
                for i in range(len(day_entries) - 1):
                    curr = day_entries[i]
                    next_e = day_entries[i + 1]
                    
                    if (curr.activity.name in self.WET_ACTIVITIES and 
                        next_e.activity.name in self.TOWER_ODS_ACTIVITIES):
                        violations.append({
                            'troop': troop.name,
                            'day': day.value,
                            'wet_activity': curr.activity.name,
                            'tower_ods_activity': next_e.activity.name,
                            'wet_slot': curr.time_slot.slot_number,
                            'tower_ods_slot': next_e.time_slot.slot_number
                        })
        
        return {'count': len(violations), 'violations': violations}
    
    def _analyze_friday_reflection_violations(self) -> Dict:
        """Analyze Friday Reflection violations."""
        violations = []
        
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries if e.troop == troop
            )
            
            if not has_reflection:
                violations.append({'troop': troop.name})
        
        return {'count': len(violations), 'violations': violations}
    
    def _analyze_exclusive_area_violations(self) -> Dict:
        """Analyze exclusive area violations."""
        violations = []
        exclusive_activities = {
            "Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery",
            "Aqua Trampoline", "Sailing"
        }
        
        # Group by slot and activity
        slot_activity_troops = defaultdict(set)
        for entry in self.schedule.entries:
            if entry.activity.name in exclusive_activities:
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number, entry.activity.name)
                slot_activity_troops[slot_key].add(entry.troop.name)  # Use troop name instead of troop object
        
        for slot_key, troops in slot_activity_troops.items():
            if len(troops) > 1:
                day, slot_num, activity = slot_key
                violations.append({
                    'activity': activity,
                    'day': day.value,
                    'slot': slot_num,
                    'troop_count': len(troops),
                    'troops': list(troops)  # troops are already names
                })
        
        return {'count': len(violations), 'violations': violations}
    
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
    
    def export_analytics(self, filepath: str):
        """Export analytics data to JSON file."""
        if not self.analytics_history:
            print("  [Analytics] No analytics data to export")
            return
        
        latest_analytics = self.analytics_history[-1]
        
        # Convert to serializable format
        export_data = asdict(latest_analytics)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"  [Analytics] Analytics exported to {filepath}")
    
    def print_summary_report(self):
        """Print a summary analytics report."""
        if not self.analytics_history:
            print("  [Analytics] No analytics data available")
            return
        
        latest = self.analytics_history[-1]
        
        print("\n=== PERFORMANCE ANALYTICS SUMMARY ===")
        print(f"Schedule Quality Score: {latest.performance_metrics.preference_satisfaction_rate:.1%}")
        print(f"Staff Efficiency: {latest.performance_metrics.staff_efficiency_score:.1%}")
        print(f"Clustering Quality: {latest.performance_metrics.clustering_quality:.1%}")
        print(f"Total Violations: {latest.constraint_violations['total_violations']}")
        print(f"Violations Fixed: {latest.performance_metrics.violations_fixed}")
        
        print("\nTop Recommendations:")
        for i, rec in enumerate(latest.recommendations[:5], 1):
            print(f"  {i}. {rec}")
        
        print(f"\nAnalytics generated at: {latest.timestamp}")


def create_performance_analytics(schedule, troops, activities):
    """
    Create and configure a performance analytics system.
    """
    analytics = PerformanceAnalytics(schedule, troops, activities)
    return analytics
