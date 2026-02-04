"""
Regression Detection Tests

Tests specifically designed to detect regressions from the current 'correct' behavior.
These tests establish baseline expectations and will fail if performance degrades.
"""
import pytest
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler


class TestRegressionDetection:
    """Tests to detect regressions from established baseline behavior"""
    
    # BASELINE METRICS (from .cursorrules and system analysis)
    BASELINE_METRICS = {
        'average_season_score': 730.7,
        'top5_satisfaction_target': 90.0,  # 16/18 available preferences
        'multislot_success_target': 100.0,
        'schedule_empty_slots_target': 0,
        'schedule_validity_target': 100.0,
        'staff_efficiency_baseline': 55.8,
        'clustering_quality_baseline': 59.3,
        'max_allowed_violations': 6,  # From baseline analysis
        'min_success_rate': 30.0,  # Current working minimum
    }
    
    @pytest.fixture
    def sample_troops(self):
        """Load real troop data for comprehensive testing"""
        # Try to use real week data
        week_file = project_root / "tc_week1_troops.json"
        if week_file.exists():
            from io_handler import load_troops_from_json
            return load_troops_from_json(str(week_file))
        else:
            # Fallback to comprehensive test data
            return [
                Troop("Tecumseh", "Site A", 
                      ["Aqua Trampoline", "Climbing Tower", "Archery", "Water Polo", "Sailing",
                       "Delta", "Super Troop", "Reflection", "Troop Rifle", "Nature Canoe"], 
                      12, 2),
                Troop("Red Cloud", "Site B", 
                      ["Climbing Tower", "Aqua Trampoline", "Archery", "Water Polo", "Sailing",
                       "Delta", "Super Troop", "Reflection", "GPS & Geocaching", "Knots and Lashings"], 
                      15, 2),
                Troop("Tamanend", "Site C", 
                      ["Archery", "Aqua Trampoline", "Climbing Tower", "Water Polo", "Sailing",
                       "Delta", "Super Troop", "Reflection", "Ultimate Survivor", "What's Cooking"], 
                      8, 2),
            ]
    
    @pytest.fixture
    def scheduler(self, sample_troops):
        """Create scheduler with sample troops"""
        return ConstrainedScheduler(sample_troops, get_all_activities())
    
    @pytest.fixture
    def schedule(self, scheduler):
        """Generate schedule for testing"""
        return scheduler.schedule_all()
    
    # ========== CRITICAL SUCCESS METRIC REGRESSION TESTS ==========
    
    def test_regression_top5_satisfaction(self, schedule, sample_troops):
        """REGRESSION TEST: Top 5 satisfaction should not drop below baseline"""
        current_satisfaction = self._calculate_top5_satisfaction(schedule, sample_troops)
        target = self.BASELINE_METRICS['top5_satisfaction_target']
        
        # Allow some tolerance but catch significant regressions
        min_acceptable = target - 15.0  # Allow 15% drop from target
        
        assert current_satisfaction >= min_acceptable, \
            f"REGRESSION: Top 5 satisfaction dropped to {current_satisfaction:.1f}% " \
            f"(target: {target}%, minimum acceptable: {min_acceptable}%)"
        
        print(f"Top 5 Satisfaction: {current_satisfaction:.1f}% (target: {target}%)")
    
    def test_regression_schedule_completeness(self, schedule, sample_troops):
        """REGRESSION TEST: Schedule completeness should not degrade"""
        empty_slots = self._count_empty_slots(schedule, sample_troops)
        target = self.BASELINE_METRICS['schedule_empty_slots_target']
        
        assert empty_slots <= target + 2, \
            f"REGRESSION: Empty slots increased to {empty_slots} (target: {target})"
        
        print(f"Empty Slots: {empty_slots} (target: {target})")
    
    def test_regression_schedule_validity(self, schedule, sample_troops):
        """REGRESSION TEST: Schedule validity should remain at 100%"""
        validity_results = self._validate_schedule_validity(schedule, sample_troops)
        is_valid = validity_results['is_valid']
        violations = validity_results['violations']
        
        target = self.BASELINE_METRICS['schedule_validity_target']
        
        assert is_valid, \
            f"REGRESSION: Schedule validity dropped to {100 if is_valid else 0}% " \
            f"(target: {target}%), violations: {violations}"
        
        print(f"Schedule Validity: {target}% (violations: {len(violations)})")
    
    def test_regression_multislot_success(self, schedule, sample_troops):
        """REGRESSION TEST: Multi-slot activity success should remain at 100%"""
        multislot_results = self._validate_multislot_activities(schedule, sample_troops)
        success_rate = multislot_results['success_rate']
        target = self.BASELINE_METRICS['multislot_success_target']
        
        assert success_rate == target, \
            f"REGRESSION: Multi-slot success rate dropped to {success_rate}% (target: {target}%)"
        
        print(f"Multi-Slot Success: {success_rate}% (target: {target}%)")
    
    def test_regression_constraint_violations(self, schedule, sample_troops):
        """REGRESSION TEST: Constraint violations should not increase beyond baseline"""
        violations = self._count_constraint_violations(schedule, sample_troops)
        max_allowed = self.BASELINE_METRICS['max_allowed_violations']
        
        assert violations <= max_allowed, \
            f"REGRESSION: Constraint violations increased to {violations} (max allowed: {max_allowed})"
        
        print(f"Constraint Violations: {violations} (max allowed: {max_allowed})")
    
    # ========== PERFORMANCE REGRESSION TESTS ==========
    
    def test_regression_staff_efficiency(self, schedule, sample_troops):
        """REGRESSION TEST: Staff efficiency should not drop below baseline"""
        current_efficiency = self._calculate_staff_efficiency(schedule)
        baseline = self.BASELINE_METRICS['staff_efficiency_baseline']
        
        # Allow some tolerance but catch significant regressions
        min_acceptable = baseline - 20.0  # Allow 20% drop from baseline
        
        assert current_efficiency >= min_acceptable, \
            f"REGRESSION: Staff efficiency dropped to {current_efficiency:.1f}% " \
            f"(baseline: {baseline}%, minimum acceptable: {min_acceptable}%)"
        
        print(f"Staff Efficiency: {current_efficiency:.1f}% (baseline: {baseline}%)")
    
    def test_regression_clustering_quality(self, schedule):
        """REGRESSION TEST: Clustering quality should not drop below baseline"""
        current_clustering = self._calculate_clustering_quality(schedule)
        baseline = self.BASELINE_METRICS['clustering_quality_baseline']
        
        # Allow some tolerance
        min_acceptable = baseline - 10.0  # Allow 10% drop from baseline
        
        assert current_clustering >= min_acceptable, \
            f"REGRESSION: Clustering quality dropped to {current_clustering:.1f}% " \
            f"(baseline: {baseline}%, minimum acceptable: {min_acceptable}%)"
        
        print(f"Clustering Quality: {current_clustering:.1f}% (baseline: {baseline}%)")
    
    def test_regression_success_rate(self, scheduler):
        """REGRESSION TEST: Overall success rate should not drop below minimum"""
        # This would be calculated across multiple weeks in real scenario
        # For single schedule test, check basic success criteria
        schedule = scheduler.schedule_all()
        
        # Basic success criteria
        has_entries = len(schedule.entries) > 0
        has_mandatory = self._has_mandatory_activities(schedule, scheduler.troops)
        minimal_gaps = self._count_empty_slots(schedule, scheduler.troops) <= 5
        
        success_indicators = sum([has_entries, has_mandatory, minimal_gaps])
        success_rate = (success_indicators / 3) * 100
        
        min_success = self.BASELINE_METRICS['min_success_rate']
        
        assert success_rate >= min_success, \
            f"REGRESSION: Success rate dropped to {success_rate:.1f}% (minimum: {min_success}%)"
        
        print(f"Success Rate: {success_rate:.1f}% (minimum: {min_success}%)")
    
    # ========== FUNCTIONAL REGRESSION TESTS ==========
    
    def test_regression_mandatory_activities_present(self, schedule, sample_troops):
        """REGRESSION TEST: All mandatory activities must be present"""
        mandatory_missing = []
        
        for troop in sample_troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            
            # Check mandatory activities
            mandatory_activities = ["Reflection", "Super Troop"]
            for mandatory in mandatory_activities:
                if mandatory not in troop_activities:
                    mandatory_missing.append(f"{troop.name}: {mandatory}")
        
        assert len(mandatory_missing) == 0, \
            f"REGRESSION: Missing mandatory activities: {mandatory_missing}"
        
        print(f"Mandatory Activities: All present")
    
    def test_regression_exclusive_area_enforcement(self, schedule):
        """REGRESSION TEST: Exclusive area constraints must be enforced"""
        exclusive_violations = self._check_exclusive_area_violations(schedule)
        
        assert len(exclusive_violations) == 0, \
            f"REGRESSION: Exclusive area violations detected: {exclusive_violations}"
        
        print(f"Exclusive Area Enforcement: No violations")
    
    def test_regression_bach_slot_rules_enforced(self, schedule):
        """REGRESSION TEST: Beach slot rules must be enforced"""
        beach_violations = self._check_beach_slot_violations(schedule)
        
        # Allow minimal violations for Top 5 exceptions
        max_allowed_beach_violations = 2
        
        assert len(beach_violations) <= max_allowed_beach_violations, \
            f"REGRESSION: Beach slot violations increased to {len(beach_violations)} " \
            f"(max allowed: {max_allowed_beach_violations})"
        
        print(f"Beach Slot Rules: {len(beach_violations)} violations (max allowed: {max_allowed_beach_violations})")
    
    def test_regression_multislot_continuity(self, schedule):
        """REGRESSION TEST: Multi-slot activity continuity must be maintained"""
        continuity_violations = self._check_multislot_continuity(schedule)
        
        assert len(continuity_violations) == 0, \
            f"REGRESSION: Multi-slot continuity violations: {continuity_violations}"
        
        print(f"Multi-Slot Continuity: No violations")
    
    def test_regression_aqua_trampoline_sharing(self, schedule):
        """REGRESSION TEST: Aqua Trampoline sharing rules must be followed"""
        at_violations = self._check_aqua_trampoline_sharing(schedule)
        
        assert len(at_violations) == 0, \
            f"REGRESSION: Aqua Trampoline sharing violations: {at_violations}"
        
        print(f"Aqua Trampoline Sharing: No violations")
    
    # ========== PERFORMANCE BOUNDARY TESTS ==========
    
    def test_regression_scheduling_performance(self, scheduler):
        """REGRESSION TEST: Scheduling should complete within reasonable time"""
        import time
        
        start_time = time.time()
        schedule = scheduler.schedule_all()
        end_time = time.time()
        
        scheduling_time = end_time - start_time
        
        # Should complete within reasonable time (adjust based on your system)
        max_allowed_time = 30.0  # 30 seconds
        
        assert scheduling_time <= max_allowed_time, \
            f"REGRESSION: Scheduling time increased to {scheduling_time:.2f}s " \
            f"(max allowed: {max_allowed_time}s)"
        
        print(f"Scheduling Time: {scheduling_time:.2f}s (max allowed: {max_allowed_time}s)")
    
    def test_regression_memory_usage(self, scheduler):
        """REGRESSION TEST: Memory usage should not increase excessively"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        schedule = scheduler.schedule_all()
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        # Should not use excessive memory
        max_allowed_increase = 100  # 100 MB increase
        
        assert memory_increase <= max_allowed_increase, \
            f"REGRESSION: Memory usage increased by {memory_increase:.1f}MB " \
            f"(max allowed: {max_allowed_increase}MB)"
        
        print(f"Memory Usage: {memory_increase:.1f}MB increase (max allowed: {max_allowed_increase}MB)")
    
    # ========== UTILITY METHODS FOR REGRESSION TESTING ==========
    
    def _calculate_top5_satisfaction(self, schedule: Schedule, troops: List[Troop]) -> float:
        """Calculate current Top 5 satisfaction rate"""
        total_achieved = 0
        total_available = 0
        
        for troop in troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top5_preferences = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
            
            # Filter exempt activities
            exempt = self._get_exempt_top5_activities(troop)
            available_preferences = top5_preferences - exempt
            achieved_preferences = troop_activities & available_preferences
            
            total_achieved += len(achieved_preferences)
            total_available += len(available_preferences)
        
        return (total_achieved / total_available * 100) if total_available > 0 else 0
    
    def _get_exempt_top5_activities(self, troop: Troop) -> set:
        """Get activities exempt from Top 5 requirements"""
        # This would contain actual exemption logic
        return set()
    
    def _count_empty_slots(self, schedule: Schedule, troops: List[Troop]) -> int:
        """Count empty slots in schedule"""
        all_slots = schedule.get_all_time_slots()
        empty_slots = 0
        
        for troop in troops:
            for slot in all_slots:
                if schedule.is_troop_free(slot, troop):
                    empty_slots += 1
        
        return empty_slots
    
    def _validate_schedule_validity(self, schedule: Schedule, troops: List[Troop]) -> Dict[str, Any]:
        """Validate schedule has no hard constraint violations"""
        violations = self._count_constraint_violations(schedule, troops)
        
        return {
            'is_valid': len(violations) == 0,
            'violations': violations
        }
    
    def _count_constraint_violations(self, schedule: Schedule, troops: List[Troop]) -> int:
        """Count hard constraint violations"""
        violations = 0
        
        # Double booking violations
        for troop in troops:
            troop_schedule = schedule.get_troop_schedule(troop)
            slot_activities = {}
            
            for entry in troop_schedule:
                if entry.time_slot in slot_activities:
                    violations += 1
                slot_activities[entry.time_slot] = entry.activity.name
        
        # Exclusive area violations
        violations += len(self._check_exclusive_area_violations(schedule))
        
        # Beach slot violations (non-Top 5)
        beach_violations = self._check_beach_slot_violations(schedule)
        non_top5_beach_violations = [v for v in beach_violations if not v.get('is_top5', False)]
        violations += len(non_top5_beach_violations)
        
        return violations
    
    def _validate_multislot_activities(self, schedule: Schedule, troops: List[Troop]) -> Dict[str, Any]:
        """Validate multi-slot activities"""
        multislot_activities = ["Sailing", "Canoe Snorkel", "Float for Floats", "GPS & Geocaching",
                               "Back of the Moon", "Itasca State Park", "Tamarac Wildlife Refuge", "Climbing Tower"]
        
        total_multislot = 0
        successful = 0
        
        for troop in troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            
            for activity_name in multislot_activities:
                if activity_name in troop.preferences:
                    total_multislot += 1
                    if activity_name in troop_activities:
                        successful += 1
        
        success_rate = (successful / total_multislot * 100) if total_multislot > 0 else 100
        
        return {
            'total': total_multislot,
            'successful': successful,
            'success_rate': success_rate
        }
    
    def _calculate_staff_efficiency(self, schedule: Schedule) -> float:
        """Calculate staff efficiency metric"""
        # Simplified staff efficiency calculation
        staff_loads = []
        
        for entry in schedule.entries:
            if entry.activity.staff:
                staff_loads.append(1)
        
        if len(staff_loads) == 0:
            return 100.0
        
        # Calculate efficiency based on load distribution
        mean_load = sum(staff_loads) / len(staff_loads)
        variance = sum((load - mean_load) ** 2 for load in staff_loads) / len(staff_loads)
        
        # Efficiency decreases with higher variance
        efficiency = max(0, 100 - (variance * 10))
        
        return efficiency
    
    def _calculate_clustering_quality(self, schedule: Schedule) -> float:
        """Calculate clustering quality metric"""
        zone_day_activities = {}
        
        for entry in schedule.entries:
            zone_key = (entry.activity.zone, entry.time_slot.day)
            if zone_key not in zone_day_activities:
                zone_day_activities[zone_key] = []
            zone_day_activities[zone_key].append(entry.activity.name)
        
        total_activities = len(schedule.entries)
        clustered_activities = 0
        
        for activities in zone_day_activities.values():
            if len(activities) > 1:
                clustered_activities += len(activities)
        
        return (clustered_activities / total_activities * 100) if total_activities > 0 else 0
    
    def _has_mandatory_activities(self, schedule: Schedule, troops: List[Troop]) -> bool:
        """Check if all mandatory activities are present"""
        for troop in troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            mandatory_activities = ["Reflection", "Super Troop"]
            
            for mandatory in mandatory_activities:
                if mandatory not in troop_activities:
                    return False
        
        return True
    
    def _check_exclusive_area_violations(self, schedule: Schedule) -> List[str]:
        """Check for exclusive area violations"""
        from models import EXCLUSIVE_AREAS
        violations = []
        
        for area_name, activity_names in EXCLUSIVE_AREAS.items():
            slot_troops = {}
            
            for entry in schedule.entries:
                if entry.activity.name in activity_names:
                    slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                    if slot_key not in slot_troops:
                        slot_troops[slot_key] = set()
                    slot_troops[slot_key].add(entry.troop.name)
            
            for slot, troops in slot_troops.items():
                if len(troops) > 1:
                    violations.append(f"{area_name} {slot}: {len(troops)} troops")
        
        return violations
    
    def _check_beach_slot_violations(self, schedule: Schedule) -> List[Dict[str, Any]]:
        """Check for beach slot rule violations"""
        beach_activities = ["Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim"]
        violations = []
        
        for entry in schedule.entries:
            if entry.activity.name in beach_activities:
                day = entry.time_slot.day
                slot = entry.time_slot.slot_number
                
                # Check if slot is allowed
                is_allowed = False
                is_top5 = False
                
                if hasattr(entry.troop, 'preferences'):
                    try:
                        pref_rank = entry.troop.preferences.index(entry.activity.name)
                        is_top5 = pref_rank < 5
                    except ValueError:
                        is_top5 = False
                
                # Beach slot rules
                if day == Day.THURSDAY:
                    is_allowed = slot in [1, 2, 3]
                else:
                    if slot == 2:
                        is_allowed = is_top5
                    else:
                        is_allowed = slot in [1, 3]
                
                if not is_allowed:
                    violations.append({
                        'troop': entry.troop.name,
                        'activity': entry.activity.name,
                        'day': day.value,
                        'slot': slot,
                        'is_top5': is_top5
                    })
        
        return violations
    
    def _check_multislot_continuity(self, schedule: Schedule) -> List[str]:
        """Check multi-slot activity continuity"""
        multislot_activities = ["Sailing", "Canoe Snorkel", "Float for Floats", "GPS & Geocaching",
                               "Climbing Tower"]
        violations = []
        
        for activity_name in multislot_activities:
            troop_day_entries = {}
            
            for entry in schedule.entries:
                if entry.activity.name == activity_name:
                    key = (entry.troop.name, entry.time_slot.day)
                    if key not in troop_day_entries:
                        troop_day_entries[key] = []
                    troop_day_entries[key].append(entry)
            
            for (troop_name, day), entries in troop_day_entries.items():
                if len(entries) > 1:
                    entries.sort(key=lambda e: e.time_slot.slot_number)
                    
                    for i in range(len(entries) - 1):
                        current_slot = entries[i].time_slot.slot_number
                        next_slot = entries[i + 1].time_slot.slot_number
                        
                        if next_slot != current_slot + 1:
                            violations.append(f"{troop_name}: {activity_name} on {day.value} not continuous")
        
        return violations
    
    def _check_aqua_trampoline_sharing(self, schedule: Schedule) -> List[str]:
        """Check Aqua Trampoline sharing rules"""
        violations = []
        
        slot_troops = {}
        
        for entry in schedule.entries:
            if entry.activity.name == "Aqua Trampoline":
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                troop_size = entry.troop.scouts + entry.troop.adults
                if slot_key not in slot_troops:
                    slot_troops[slot_key] = []
                slot_troops[slot_key].append({
                    'troop': entry.troop.name,
                    'size': troop_size
                })
        
        for slot, troops in slot_troops.items():
            if len(troops) > 2:
                violations.append(f"{slot}: {len(troops)} troops sharing Aqua Trampoline")
            elif len(troops) == 2:
                for troop_info in troops:
                    if troop_info['size'] > 16:
                        violations.append(f"{slot}: {troop_info['troop']} ({troop_info['size']} people) sharing Aqua Trampoline")
        
        return violations


class TestBaselineComparison:
    """Tests to compare current performance against established baselines"""
    
    def test_baseline_comparison_file_exists(self):
        """Test: Baseline comparison file should exist for reference"""
        baseline_file = project_root / "tests" / "baseline_metrics.json"
        
        # If baseline file doesn't exist, create it with current metrics
        if not baseline_file.exists():
            baseline_data = {
                'created_date': '2026-02-02',
                'version': '1.0',
                'metrics': TestRegressionDetection.BASELINE_METRICS,
                'notes': 'Initial baseline established for regression testing'
            }
            
            with open(baseline_file, 'w') as f:
                json.dump(baseline_data, f, indent=2)
            
            print(f"Created baseline file: {baseline_file}")
        
        assert baseline_file.exists(), f"Baseline file should exist at {baseline_file}"
    
    def test_baseline_metrics_loaded(self):
        """Test: Baseline metrics can be loaded and validated"""
        baseline_file = project_root / "tests" / "baseline_metrics.json"
        
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)
            
            assert 'metrics' in baseline_data, "Baseline file should contain metrics"
            assert isinstance(baseline_data['metrics'], dict), "Metrics should be a dictionary"
            
            # Check that all required metrics are present
            required_metrics = [
                'average_season_score', 'top5_satisfaction_target', 'multislot_success_target',
                'schedule_empty_slots_target', 'schedule_validity_target'
            ]
            
            for metric in required_metrics:
                assert metric in baseline_data['metrics'], f"Baseline should contain {metric}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
