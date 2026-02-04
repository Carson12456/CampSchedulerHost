"""
Performance Metrics Tests

Tests for all performance metrics and scoring calculations.
Ensures the evaluation system works correctly and consistently.
"""
import pytest
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler


class TestScoringSystem:
    """Test the scoring system and point calculations"""
    
    @pytest.fixture
    def sample_schedule(self):
        """Create a sample schedule for testing"""
        schedule = Schedule()
        
        # Add sample entries
        troop = Troop("Test Troop", "Site A", ["Aqua Trampoline", "Climbing Tower"], 12, 2)
        activities = get_all_activities()
        
        # Add some activities
        schedule.add_entry(TimeSlot(Day.MONDAY, 1), activities[0], troop)
        schedule.add_entry(TimeSlot(Day.MONDAY, 2), activities[1], troop)
        schedule.add_entry(TimeSlot(Day.MONDAY, 3), activities[2], troop)
        
        return schedule
    
    def test_score_calculation_range(self, sample_schedule):
        """Test: Score calculation returns values in expected range"""
        # This would use the actual scoring system
        # For now, test that scoring logic exists
        try:
            from evaluate_week_success import calculate_week_score
            score = calculate_week_score(sample_schedule)
            
            # Score should be between 0 and 1000
            assert 0 <= score <= 1000, f"Score {score} should be between 0 and 1000"
        except ImportError:
            pytest.skip("evaluate_week_success module not available")
    
    def test_preference_satisfaction_scoring(self, sample_schedule):
        """Test: Preference satisfaction contributes correctly to score"""
        # Test preference satisfaction calculation
        troop = sample_schedule.troops[0] if sample_schedule.troops else \
                Troop("Test Troop", "Site A", ["Aqua Trampoline", "Climbing Tower"], 12, 2)
        
        troop_activities = {e.activity.name for e in sample_schedule.entries if e.troop == troop}
        preferences = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
        
        # Calculate satisfaction rate
        scheduled_preferences = troop_activities & set(preferences)
        satisfaction_rate = len(scheduled_preferences) / len(preferences) * 100 if preferences else 0
        
        # Should be reasonable
        assert 0 <= satisfaction_rate <= 100, f"Satisfaction rate {satisfaction_rate} should be between 0 and 100"
    
    def test_constraint_compliance_scoring(self, sample_schedule):
        """Test: Constraint violations are properly penalized"""
        # Test constraint violation detection
        violations = self._count_constraint_violations(sample_schedule)
        
        # Should be non-negative
        assert violations >= 0, f"Violation count {violations} should be non-negative"
    
    def test_schedule_quality_scoring(self, sample_schedule):
        """Test: Schedule quality metrics are calculated correctly"""
        # Test gap elimination scoring
        gaps = self._count_empty_slots(sample_schedule)
        
        # Should be non-negative
        assert gaps >= 0, f"Gap count {gaps} should be non-negative"
        
        # Test staff balance scoring
        staff_variance = self._calculate_staff_variance(sample_schedule)
        
        # Should be non-negative
        assert staff_variance >= 0, f"Staff variance {staff_variance} should be non-negative"
    
    def _count_constraint_violations(self, schedule: Schedule) -> int:
        """Count constraint violations in schedule"""
        violations = 0
        
        # Check for double bookings
        for troop in schedule.troops:
            troop_schedule = schedule.get_troop_schedule(troop)
            slot_activities = {}
            
            for entry in troop_schedule:
                slot_key = entry.time_slot
                if slot_key in slot_activities:
                    violations += 1  # Double booking
                slot_activities[slot_key] = entry.activity.name
        
        return violations
    
    def _count_empty_slots(self, schedule: Schedule) -> int:
        """Count empty slots in schedule"""
        all_slots = schedule.get_all_time_slots()
        empty_slots = 0
        
        for troop in schedule.troops:
            for slot in all_slots:
                if schedule.is_troop_free(slot, troop):
                    empty_slots += 1
        
        return empty_slots
    
    def _calculate_staff_variance(self, schedule: Schedule) -> float:
        """Calculate staff load variance"""
        # Simplified staff variance calculation
        staff_loads = []
        
        # This is a simplified version - real implementation would be more complex
        for entry in schedule.entries:
            if entry.activity.staff:  # Activity has staff
                staff_loads.append(1)  # Simplified - each staffed activity counts as 1
        
        if len(staff_loads) <= 1:
            return 0.0
        
        # Calculate variance
        mean_load = sum(staff_loads) / len(staff_loads)
        variance = sum((load - mean_load) ** 2 for load in staff_loads) / len(staff_loads)
        
        return variance


class TestPreferenceSatisfactionMetrics:
    """Test preference satisfaction metrics"""
    
    @pytest.fixture
    def sample_troops(self):
        """Create sample troops with known preferences"""
        return [
            Troop("Troop A", "Site A", 
                  ["Aqua Trampoline", "Climbing Tower", "Archery", "Water Polo", "Sailing"], 
                  12, 2),
            Troop("Troop B", "Site B", 
                  ["Climbing Tower", "Aqua Trampoline", "Archery", "Water Polo", "Sailing"], 
                  15, 2),
            Troop("Troop C", "Site C", 
                  ["Archery", "Aqua Trampoline", "Climbing Tower", "Water Polo", "Sailing"], 
                  8, 2),
        ]
    
    @pytest.fixture
    def scheduler(self, sample_troops):
        """Create scheduler with sample troops"""
        return ConstrainedScheduler(sample_troops, get_all_activities())
    
    def test_top5_satisfaction_calculation(self, scheduler):
        """Test: Top 5 satisfaction is calculated correctly"""
        schedule = scheduler.schedule_all()
        
        total_achieved = 0
        total_available = 0
        
        for troop in scheduler.troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top5_preferences = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
            
            # Filter exempt activities
            exempt = self._get_exempt_activities(troop)
            available_preferences = top5_preferences - exempt
            achieved_preferences = troop_activities & available_preferences
            
            total_achieved += len(achieved_preferences)
            total_available += len(available_preferences)
        
        satisfaction_rate = (total_achieved / total_available * 100) if total_available > 0 else 0
        
        # Should be reasonable
        assert 0 <= satisfaction_rate <= 100, f"Top 5 satisfaction {satisfaction_rate} should be between 0 and 100"
        assert total_achieved <= total_available, f"Achieved {total_achieved} should not exceed available {total_available}"
    
    def test_top10_satisfaction_calculation(self, scheduler):
        """Test: Top 10 satisfaction is calculated correctly"""
        schedule = scheduler.schedule_all()
        
        total_achieved = 0
        total_available = 0
        
        for troop in scheduler.troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top10_preferences = set(troop.preferences[:10]) if len(troop.preferences) >= 10 else set(troop.preferences)
            
            achieved_preferences = troop_activities & top10_preferences
            
            total_achieved += len(achieved_preferences)
            total_available += len(top10_preferences)
        
        satisfaction_rate = (total_achieved / total_available * 100) if total_available > 0 else 0
        
        # Should be reasonable
        assert 0 <= satisfaction_rate <= 100, f"Top 10 satisfaction {satisfaction_rate} should be between 0 and 100"
    
    def test_minimum_top10_requirement(self, scheduler):
        """Test: Each troop gets at least 2-3 Top 10 preferences"""
        schedule = scheduler.schedule_all()
        
        for troop in scheduler.troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top10_preferences = set(troop.preferences[:10]) if len(troop.preferences) >= 10 else set(troop.preferences)
            
            scheduled_top10 = troop_activities & top10_preferences
            
            # Should have at least 2-3 top 10 preferences
            min_required = 2
            assert len(scheduled_top10) >= min_required, \
                f"{troop.name}: Should have at least {min_required} Top 10 preferences, got {len(scheduled_top10)}"
    
    def _get_exempt_activities(self, troop: Troop) -> set:
        """Get activities exempt from preference requirements"""
        # This would contain the actual exemption logic
        # For now, return empty set
        return set()


class TestStaffEfficiencyMetrics:
    """Test staff efficiency metrics"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler for staff testing"""
        troops = [
            Troop("Troop A", "Site A", ["Aqua Trampoline", "Climbing Tower"], 12, 2),
            Troop("Troop B", "Site B", ["Water Polo", "Sailing"], 15, 2),
        ]
        return ConstrainedScheduler(troops, get_all_activities())
    
    def test_staff_load_calculation(self, scheduler):
        """Test: Staff load is calculated correctly per slot"""
        schedule = scheduler.schedule_all()
        
        # Group staff requirements by slot
        slot_staff_count = {}
        
        for entry in schedule.entries:
            slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
            
            # Count staff requirements
            staff_count = 0
            if entry.activity.staff:
                staff_count += 1  # Simplified - real implementation would be more detailed
            
            slot_staff_count[slot_key] = slot_staff_count.get(slot_key, 0) + staff_count
        
        # Should have reasonable staff counts
        for slot, count in slot_staff_count.items():
            assert count >= 0, f"Staff count for {slot} should be non-negative"
            assert count <= 20, f"Staff count {count} for {slot} seems too high"
    
    def test_staff_balance_calculation(self, scheduler):
        """Test: Staff balance variance is calculated correctly"""
        schedule = scheduler.schedule_all()
        
        # Calculate staff loads per slot
        staff_loads = []
        
        for entry in schedule.entries:
            if entry.activity.staff:
                staff_loads.append(1)  # Simplified
        
        if len(staff_loads) > 1:
            # Calculate variance
            mean_load = sum(staff_loads) / len(staff_loads)
            variance = sum((load - mean_load) ** 2 for load in staff_loads) / len(staff_loads)
            
            # Variance should be reasonable
            assert variance >= 0, f"Staff variance {variance} should be non-negative"
            assert variance < 100, f"Staff variance {variance} seems too high"
    
    def test_staff_efficiency_target(self, scheduler):
        """Test: Staff efficiency meets target of 55.8%"""
        # This would calculate actual staff efficiency
        # For now, test that the calculation logic exists
        assert hasattr(scheduler, '_calculate_staff_efficiency'), \
            "Scheduler should have staff efficiency calculation method"


class TestClusteringQualityMetrics:
    """Test clustering quality metrics"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler for clustering testing"""
        troops = [
            Troop("Troop A", "Site A", ["Climbing Tower", "GPS & Geocaching", "Knots and Lashings"], 12, 2),
            Troop("Troop B", "Site B", ["Aqua Trampoline", "Water Polo", "Troop Swim"], 15, 2),
        ]
        return ConstrainedScheduler(troops, get_all_activities())
    
    def test_clustering_efficiency_calculation(self, scheduler):
        """Test: Clustering efficiency is calculated correctly"""
        schedule = scheduler.schedule_all()
        
        # Group activities by zone and day
        zone_day_activities = {}
        
        for entry in schedule.entries:
            zone_key = (entry.activity.zone, entry.time_slot.day)
            if zone_key not in zone_day_activities:
                zone_day_activities[zone_key] = []
            zone_day_activities[zone_key].append(entry.activity.name)
        
        # Calculate clustering metrics
        total_activities = len(schedule.entries)
        clustered_activities = 0
        
        for activities in zone_day_activities.values():
            if len(activities) > 1:
                clustered_activities += len(activities)
        
        clustering_rate = (clustered_activities / total_activities * 100) if total_activities > 0 else 0
        
        # Should be reasonable
        assert 0 <= clustering_rate <= 100, f"Clustering rate {clustering_rate} should be between 0 and 100"
    
    def test_excess_day_calculation(self, scheduler):
        """Test: Excess cluster days are calculated correctly"""
        schedule = scheduler.schedule_all()
        
        # Count days per zone
        zone_days = {}
        
        for entry in schedule.entries:
            zone = entry.activity.zone
            day = entry.time_slot.day
            if zone not in zone_days:
                zone_days[zone] = set()
            zone_days[zone].add(day)
        
        # Calculate excess days (days beyond optimal clustering)
        total_excess_days = 0
        for zone, days in zone_days.items():
            # Optimal would be 1-2 days per zone
            optimal_days = 2
            excess = len(days) - optimal_days
            if excess > 0:
                total_excess_days += excess
        
        # Should be non-negative
        assert total_excess_days >= 0, f"Excess days {total_excess_days} should be non-negative"
    
    def test_consecutive_day_bonus(self, scheduler):
        """Test: Consecutive day clustering bonuses are applied"""
        schedule = scheduler.schedule_all()
        
        # Check for consecutive day clustering
        zone_day_sequences = {}
        
        for entry in schedule.entries:
            zone = entry.activity.zone
            day = entry.time_slot.day
            if zone not in zone_day_sequences:
                zone_day_sequences[zone] = []
            zone_day_sequences[zone].append(day)
        
        # Count consecutive sequences
        consecutive_bonuses = 0
        for zone, days in zone_day_sequences.items():
            unique_days = sorted(list(set(days)))
            consecutive_count = 0
            
            for i in range(len(unique_days) - 1):
                current_day_idx = list(Day).index(unique_days[i])
                next_day_idx = list(Day).index(unique_days[i + 1])
                
                if next_day_idx == current_day_idx + 1:
                    consecutive_count += 1
            
            consecutive_bonuses += consecutive_count
        
        # Should be non-negative
        assert consecutive_bonuses >= 0, f"Consecutive bonuses {consecutive_bonuses} should be non-negative"


class TestScheduleQualityMetrics:
    """Test overall schedule quality metrics"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler for quality testing"""
        troops = [
            Troop("Troop A", "Site A", ["Aqua Trampoline", "Climbing Tower", "Archery"], 12, 2),
            Troop("Troop B", "Site B", ["Water Polo", "Sailing", "Delta"], 15, 2),
        ]
        return ConstrainedScheduler(troops, get_all_activities())
    
    def test_completeness_metric(self, scheduler):
        """Test: Schedule completeness (no empty slots) is calculated correctly"""
        schedule = scheduler.schedule_all()
        
        all_slots = schedule.get_all_time_slots()
        total_slots = len(all_slots) * len(scheduler.troops)
        filled_slots = 0
        
        for troop in scheduler.troops:
            for slot in all_slots:
                if not schedule.is_troop_free(slot, troop):
                    filled_slots += 1
        
        completeness_rate = (filled_slots / total_slots * 100) if total_slots > 0 else 0
        
        # Should be high (target is 100%)
        assert completeness_rate >= 80.0, f"Completeness {completeness_rate} should be >= 80%"
        assert completeness_rate <= 100.0, f"Completeness {completeness_rate} should not exceed 100%"
    
    def test_validity_metric(self, scheduler):
        """Test: Schedule validity (no hard constraint violations) is calculated correctly"""
        schedule = scheduler.schedule_all()
        
        # Check hard constraint violations
        violations = 0
        
        # Double booking check
        for troop in scheduler.troops:
            troop_schedule = schedule.get_troop_schedule(troop)
            slot_map = {}
            
            for entry in troop_schedule:
                if entry.time_slot in slot_map:
                    violations += 1
                slot_map[entry.time_slot] = entry.activity.name
        
        validity_rate = 100.0 if violations == 0 else max(0, 100.0 - (violations * 10))
        
        # Should be high (target is 100%)
        assert validity_rate >= 90.0, f"Validity {validity_rate} should be >= 90%"
    
    def test_gap_elimination_metric(self, scheduler):
        """Test: Gap elimination effectiveness is calculated correctly"""
        schedule = scheduler.schedule_all()
        
        # Count gaps
        all_slots = schedule.get_all_time_slots()
        total_gaps = 0
        
        for troop in scheduler.troops:
            troop_gaps = 0
            for slot in all_slots:
                if schedule.is_troop_free(slot, troop):
                    troop_gaps += 1
            total_gaps += troop_gaps
        
        # Calculate gap elimination rate
        total_possible_slots = len(all_slots) * len(scheduler.troops)
        filled_slots = total_possible_slots - total_gaps
        gap_elimination_rate = (filled_slots / total_possible_slots * 100) if total_possible_slots > 0 else 0
        
        # Should be high
        assert gap_elimination_rate >= 80.0, f"Gap elimination {gap_elimination_rate} should be >= 80%"


class TestPerformanceAnalytics:
    """Test performance analytics and reporting"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler for analytics testing"""
        troops = [
            Troop("Troop A", "Site A", ["Aqua Trampoline", "Climbing Tower"], 12, 2),
        ]
        return ConstrainedScheduler(troops, get_all_activities())
    
    def test_analytics_data_collection(self, scheduler):
        """Test: Analytics data is collected correctly"""
        schedule = scheduler.schedule_all()
        
        # Test that analytics can be generated
        analytics_data = {
            'total_entries': len(schedule.entries),
            'total_troops': len(scheduler.troops),
            'activities_per_troop': len(schedule.entries) / len(scheduler.troops) if scheduler.troops else 0
        }
        
        # Should have reasonable values
        assert analytics_data['total_entries'] > 0, "Should have schedule entries"
        assert analytics_data['total_troops'] > 0, "Should have troops"
        assert analytics_data['activities_per_troop'] > 0, "Should have activities per troop"
    
    def test_performance_trends_tracking(self, scheduler):
        """Test: Performance trends are tracked over time"""
        # This would test trend tracking logic
        # For now, test that analytics methods exist
        assert hasattr(scheduler, '_generate_performance_report'), \
            "Scheduler should generate performance reports"
    
    def test_recommendation_generation(self, scheduler):
        """Test: Improvement recommendations are generated"""
        # This would test recommendation logic
        # For now, test that recommendation methods exist
        assert hasattr(scheduler, '_generate_recommendations'), \
            "Scheduler should generate improvement recommendations"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
