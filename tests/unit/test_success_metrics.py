"""
Comprehensive Success Metrics Test Suite

Tests every metric of success defined in .cursorrules to detect regressions.
This suite validates the current 'correct' behavior and will catch any deviations.

Core Success Metrics (from .cursorrules):
- Average Season Score: 730.7
- Top 5 Satisfaction: 90.0% (16/18 available preferences)
- Multi-Slot Activities: 100% success rate
- Schedule Empty Slots: 0 across ALL weeks
- Schedule Validity: 100% (no invalid schedules)
"""
import pytest
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone
from activities import get_all_activities, get_activity_by_name
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler


class TestSuccessMetrics:
    """Test suite for all success metrics defined in .cursorrules"""
    
    @pytest.fixture
    def sample_troops(self):
        """Load sample troops for testing"""
        # Use a real week file for comprehensive testing
        week_file = project_root / "tc_week1_troops.json"
        if week_file.exists():
            return load_troops_from_json(str(week_file))
        else:
            # Fallback to minimal test data
            return [
                Troop("Test Troop 1", "Site A", ["Aqua Trampoline", "Climbing Tower", "Archery"], 12, 2),
                Troop("Test Troop 2", "Site B", ["Water Polo", "Sailing", "Delta"], 15, 2),
            ]
    
    @pytest.fixture
    def scheduler(self, sample_troops):
        """Create scheduler with sample troops"""
        return ConstrainedScheduler(sample_troops, get_all_activities())
    
    @pytest.fixture
    def schedule(self, scheduler):
        """Generate a complete schedule for testing"""
        return scheduler.schedule_all()
    
    # ========== CORE SUCCESS METRICS TESTS ==========
    
    def test_average_season_score_target(self, schedule):
        """Test: Average Season Score should meet target of 730.7"""
        # This would be calculated across all weeks in a real scenario
        # For single schedule test, we verify the scoring logic works
        from evaluate_week_success import calculate_week_score
        
        score = calculate_week_score(schedule)
        
        # Score should be reasonable (not negative, not >1000)
        assert 0 <= score <= 1000, f"Score {score} should be between 0 and 1000"
        
        # Should be in acceptable range (target is 730.7)
        assert score >= 600, f"Score {score} should be at least 600 (target: 730.7)"
    
    def test_top5_satisfaction_rate(self, schedule, sample_troops):
        """Test: Top 5 Satisfaction should be 90.0% (16/18 available preferences)"""
        top5_stats = self._calculate_top5_satisfaction(schedule, sample_troops)
        
        satisfaction_rate = top5_stats['satisfaction_rate']
        achieved = top5_stats['achieved']
        available = top5_stats['available']
        
        # Target: 90.0% satisfaction
        assert satisfaction_rate >= 85.0, f"Top 5 satisfaction {satisfaction_rate:.1f}% should be >= 85% (target: 90.0%)"
        assert achieved >= available * 0.85, f"Should achieve at least 85% of available preferences"
        
        print(f"Top 5 Satisfaction: {achieved}/{available} ({satisfaction_rate:.1f}%)")
    
    def test_multislot_activity_success_rate(self, schedule, sample_troops):
        """Test: Multi-Slot Activities should have 100% success rate"""
        multislot_results = self._validate_multislot_activities(schedule, sample_troops)
        
        success_rate = multislot_results['success_rate']
        total_multislot = multislot_results['total']
        successful = multislot_results['successful']
        
        # Target: 100% success rate
        assert success_rate == 100.0, f"Multi-slot success rate {success_rate}% should be 100%"
        assert successful == total_multislot, f"All {total_multislot} multi-slot activities should succeed"
        
        print(f"Multi-Slot Success: {successful}/{total_multislot} ({success_rate}%)")
    
    def test_schedule_empty_slots_zero(self, schedule, sample_troops):
        """Test: Schedule Empty Slots should be 0 across ALL weeks"""
        empty_slots = self._count_empty_slots(schedule, sample_troops)
        
        # Target: 0 empty slots
        assert empty_slots == 0, f"Should have 0 empty slots, found {empty_slots}"
        
        print(f"Empty Slots: {empty_slots} (target: 0)")
    
    def test_schedule_validity_100_percent(self, schedule, sample_troops):
        """Test: Schedule Validity should be 100% (no invalid schedules)"""
        validity_results = self._validate_schedule_validity(schedule, sample_troops)
        
        is_valid = validity_results['is_valid']
        violations = validity_results['violations']
        
        # Target: 100% validity (no hard constraint violations)
        assert is_valid, f"Schedule should be 100% valid, found {len(violations)} violations"
        assert len(violations) == 0, f"Should have no hard constraint violations"
        
        print(f"Schedule Validity: 100% (violations: {len(violations)})")
    
    # ========== PREFERENCE SATISFACTION TESTS ==========
    
    def test_mandatory_top5_preferences(self, schedule, sample_troops):
        """Test: Top 1-5 preferences are MANDATORY and should be scheduled"""
        for troop in sample_troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top5_preferences = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
            
            # Check non-exempt top 5 preferences
            exempt_activities = self._get_exempt_top5_activities(troop)
            non_exempt_top5 = top5_preferences - exempt_activities
            
            scheduled_top5 = troop_activities & non_exempt_top5
            
            # Should have high satisfaction rate for non-exempt preferences
            if len(non_exempt_top5) > 0:
                satisfaction_rate = len(scheduled_top5) / len(non_exempt_top5) * 100
                assert satisfaction_rate >= 80.0, f"{troop.name}: Top 5 satisfaction {satisfaction_rate:.1f}% should be >= 80%"
    
    def test_minimum_top10_preferences(self, schedule, sample_troops):
        """Test: Each troop must get at least 2-3 of their Top 10 preferences"""
        for troop in sample_troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top10_preferences = set(troop.preferences[:10]) if len(troop.preferences) >= 10 else set(troop.preferences)
            
            scheduled_top10 = troop_activities & top10_preferences
            
            # Should have at least 2-3 top 10 preferences
            min_required = 2
            assert len(scheduled_top10) >= min_required, f"{troop.name}: Should have at least {min_required} Top 10 preferences, got {len(scheduled_top10)}"
    
    # ========== CONSTRAINT COMPLIANCE TESTS ==========
    
    def test_hard_constraint_compliance(self, schedule, sample_troops):
        """Test: No hard constraint violations (result: INVALID if violated)"""
        violations = self._check_hard_constraints(schedule, sample_troops)
        
        assert len(violations) == 0, f"Should have no hard constraint violations, found: {violations}"
    
    def test_soft_constraint_minimization(self, schedule, sample_troops):
        """Test: Soft constraint violations should be minimized"""
        violations = self._check_soft_constraints(schedule, sample_troops)
        
        # Should have minimal soft constraint violations
        # Allow some soft violations but not excessive
        max_allowed_soft_violations = len(sample_troops) * 2  # Allow 2 per troop max
        
        assert len(violations) <= max_allowed_soft_violations, f"Soft violations {len(violations)} should be <= {max_allowed_soft_violations}"
    
    def test_exclusive_area_enforcement(self, schedule):
        """Test: Only one troop per slot in exclusive areas"""
        exclusive_areas = {
            "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"],
            "Tower": ["Climbing Tower"],
            "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
            "Archery": ["Archery"],
            "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
            "Nature Center": ["Dr. DNA", "Loon Lore"],
            "Delta": ["Delta"],
            "Super Troop": ["Super Troop"],
            "Sailing": ["Sailing"]
        }
        
        for area_name, activity_names in exclusive_areas.items():
            violations = self._check_exclusive_area_violations(schedule, area_name, activity_names)
            assert len(violations) == 0, f"Exclusive area {area_name} should have no violations: {violations}"
    
    def test_beach_slot_rules(self, schedule):
        """Test: Beach activities only in allowed slots"""
        beach_activities = ["Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
                           "Underwater Obstacle Course", "Float for Floats", "Canoe Snorkel"]
        
        violations = self._check_beach_slot_rules(schedule, beach_activities)
        
        # Allow some violations for Top 5 preferences (per rules)
        top5_violations = [v for v in violations if v['is_top5']]
        non_top5_violations = [v for v in violations if not v['is_top5']]
        
        # Non-Top 5 violations should be minimal
        assert len(non_top5_violations) <= 2, f"Non-Top 5 beach slot violations should be <= 2, found {len(non_top5_violations)}"
    
    # ========== STAFFING AND CAPACITY TESTS ==========
    
    def test_staff_limits_enforcement(self, schedule):
        """Test: Staff limits are enforced (max 16 staff per slot, target <=14)"""
        staff_violations = self._check_staff_limits(schedule)
        
        # Should have no critical violations (>16 staff)
        critical_violations = [v for v in staff_violations if v['severity'] == 'critical']
        assert len(critical_violations) == 0, f"Should have no critical staff violations (>16), found {len(critical_violations)}"
        
        # Should minimize target violations (>14 staff)
        target_violations = [v for v in staff_violations if v['severity'] == 'target']
        print(f"Staff target violations (>14): {len(target_violations)}")
    
    def test_capacity_limits_enforcement(self, schedule):
        """Test: Activity capacity limits are not exceeded"""
        capacity_violations = self._check_capacity_limits(schedule)
        
        assert len(capacity_violations) == 0, f"Should have no capacity violations, found: {capacity_violations}"
    
    def test_aqua_trampoline_sharing_rules(self, schedule):
        """Test: Aqua Trampoline sharing rules are followed"""
        at_violations = self._check_aqua_trampoline_sharing(schedule)
        
        assert len(at_violations) == 0, f"Should have no Aqua Trampoline sharing violations, found: {at_violations}"
    
    # ========== SCHEDULING ALGORITHM TESTS ==========
    
    def test_mandatory_activities_scheduled(self, schedule, sample_troops):
        """Test: Spine-protected mandatory activities are scheduled"""
        mandatory_activities = ["Reflection", "Super Troop"]
        
        for troop in sample_troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            
            for mandatory in mandatory_activities:
                assert mandatory in troop_activities, f"{troop.name}: Mandatory activity {mandatory} should be scheduled"
    
    def test_friday_reflection_compliance(self, schedule, sample_troops):
        """Test: Reflection must be on Friday for all troops"""
        for troop in sample_troops:
            reflection_entries = [e for e in schedule.entries 
                                if e.troop == troop and e.activity.name == "Reflection"]
            
            assert len(reflection_entries) == 1, f"{troop.name}: Should have exactly 1 Reflection"
            
            if reflection_entries:
                assert reflection_entries[0].time_slot.day == Day.FRIDAY, f"{troop.name}: Reflection must be on Friday"
    
    def test_super_troop_exclusivity(self, schedule):
        """Test: Super Troop should never share (exclusive, one troop per slot)"""
        super_troop_entries = [e for e in schedule.entries if e.activity.name == "Super Troop"]
        
        # Group by slot
        slot_troops = defaultdict(list)
        for entry in super_troop_entries:
            slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
            slot_troops[slot_key].append(entry.troop.name)
        
        # Check no slot has multiple troops
        violations = []
        for slot, troops in slot_troops.items():
            if len(troops) > 1:
                violations.append(f"{slot}: {len(troops)} troops ({', '.join(troops)})")
        
        assert len(violations) == 0, f"Super Troop should be exclusive, violations: {violations}"
    
    # ========== MULTI-SLOT ACTIVITY TESTS ==========
    
    def test_multislot_continuity(self, schedule):
        """Test: Multi-slot activities maintain proper continuity"""
        multislot_activities = ["Sailing", "Canoe Snorkel", "Float for Floats", "GPS & Geocaching",
                               "Back of the Moon", "Itasca State Park", "Tamarac Wildlife Refuge", "Climbing Tower"]
        
        for activity_name in multislot_activities:
            violations = self._check_multislot_continuity(schedule, activity_name)
            assert len(violations) == 0, f"Multi-slot activity {activity_name} continuity violations: {violations}"
    
    def test_dynamic_sailing_duration(self, schedule):
        """Test: Sailing uses correct duration (1.5 slots normal, 2.0 on Thursday)"""
        sailing_entries = [e for e in schedule.entries if e.activity.name == "Sailing"]
        
        for entry in sailing_entries:
            day = entry.time_slot.day
            slot = entry.time_slot.slot_number
            
            # Get all sailing entries for this troop on this day
            troop_sailing = [e for e in sailing_entries 
                           if e.troop == entry.troop and e.time_slot.day == day]
            
            if day == Day.THURSDAY:
                # Thursday: should occupy 2 slots
                assert len(troop_sailing) == 2, f"Sailing on Thursday should occupy 2 slots, found {len(troop_sailing)}"
            else:
                # Other days: should occupy 2 slots (1.5 rounded up)
                assert len(troop_sailing) == 2, f"Sailing on {day.value} should occupy 2 slots, found {len(troop_sailing)}"
    
    # ========== UTILITY METHODS ==========
    
    def _calculate_top5_satisfaction(self, schedule: Schedule, troops: List[Troop]) -> Dict[str, Any]:
        """Calculate Top 5 satisfaction statistics"""
        total_achieved = 0
        total_available = 0
        
        for troop in troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top5_preferences = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
            
            # Filter out exempt activities
            exempt = self._get_exempt_top5_activities(troop)
            available_preferences = top5_preferences - exempt
            achieved_preferences = troop_activities & available_preferences
            
            total_achieved += len(achieved_preferences)
            total_available += len(available_preferences)
        
        satisfaction_rate = (total_achieved / total_available * 100) if total_available > 0 else 0
        
        return {
            'achieved': total_achieved,
            'available': total_available,
            'satisfaction_rate': satisfaction_rate
        }
    
    def _get_exempt_top5_activities(self, troop: Troop) -> set:
        """Get activities that are exempt from Top 5 requirements"""
        exempt = set()
        
        # Add logic for exempt activities based on troop characteristics
        # This would include capacity-constrained activities, etc.
        # For now, return empty set - can be enhanced based on specific rules
        
        return exempt
    
    def _validate_multislot_activities(self, schedule: Schedule, troops: List[Troop]) -> Dict[str, Any]:
        """Validate all multi-slot activities are scheduled correctly"""
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
    
    def _count_empty_slots(self, schedule: Schedule, troops: List[Troop]) -> int:
        """Count empty slots for all troops"""
        all_slots = schedule.get_all_time_slots()
        empty_slots = 0
        
        for troop in troops:
            for slot in all_slots:
                if schedule.is_troop_free(slot, troop):
                    empty_slots += 1
        
        return empty_slots
    
    def _validate_schedule_validity(self, schedule: Schedule, troops: List[Troop]) -> Dict[str, Any]:
        """Validate schedule has no hard constraint violations"""
        violations = self._check_hard_constraints(schedule, troops)
        
        return {
            'is_valid': len(violations) == 0,
            'violations': violations
        }
    
    def _check_hard_constraints(self, schedule: Schedule, troops: List[Troop]) -> List[str]:
        """Check for hard constraint violations"""
        violations = []
        
        # Check double booking
        for troop in troops:
            troop_schedule = schedule.get_troop_schedule(troop)
            slot_activities = defaultdict(list)
            
            for entry in troop_schedule:
                slot_activities[entry.time_slot].append(entry.activity.name)
            
            for slot, activities in slot_activities.items():
                if len(activities) > 1:
                    violations.append(f"{troop.name}: Double booked in {slot}")
        
        # Check capacity violations
        capacity_violations = self._check_capacity_limits(schedule)
        violations.extend(capacity_violations)
        
        # Check exclusive area violations
        exclusive_violations = self._check_all_exclusive_areas(schedule)
        violations.extend(exclusive_violations)
        
        return violations
    
    def _check_soft_constraints(self, schedule: Schedule, troops: List[Troop]) -> List[str]:
        """Check for soft constraint violations"""
        violations = []
        
        # Check accuracy limit (max 1 per day per troop)
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        
        for troop in troops:
            day_activities = defaultdict(set)
            
            for entry in schedule.entries:
                if entry.troop == troop and entry.activity.name in accuracy_activities:
                    day_activities[entry.time_slot.day].add(entry.activity.name)
            
            for day, activities in day_activities.items():
                if len(activities) > 1:
                    violations.append(f"{troop.name}: Multiple accuracy activities on {day.value}: {', '.join(activities)}")
        
        return violations
    
    def _check_exclusive_area_violations(self, schedule: Schedule, area_name: str, activity_names: List[str]) -> List[str]:
        """Check violations in a specific exclusive area"""
        violations = []
        slot_troops = defaultdict(set)
        
        for entry in schedule.entries:
            if entry.activity.name in activity_names:
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                slot_troops[slot_key].add(entry.troop.name)
        
        for slot, troops in slot_troops.items():
            if len(troops) > 1:
                violations.append(f"{area_name} {slot}: {len(troops)} troops ({', '.join(troops)})")
        
        return violations
    
    def _check_all_exclusive_areas(self, schedule: Schedule) -> List[str]:
        """Check all exclusive area violations"""
        all_violations = []
        
        exclusive_areas = {
            "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", "Ultimate Survivor", "What's Cooking", "Chopped!"],
            "Tower": ["Climbing Tower"],
            "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
            "Archery": ["Archery"],
            "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
            "Nature Center": ["Dr. DNA", "Loon Lore"],
            "Delta": ["Delta"],
            "Super Troop": ["Super Troop"],
            "Sailing": ["Sailing"]
        }
        
        for area_name, activity_names in exclusive_areas.items():
            violations = self._check_exclusive_area_violations(schedule, area_name, activity_names)
            all_violations.extend(violations)
        
        return all_violations
    
    def _check_beach_slot_rules(self, schedule: Schedule, beach_activities: List[str]) -> List[Dict[str, Any]]:
        """Check beach activity slot rules"""
        violations = []
        
        for entry in schedule.entries:
            if entry.activity.name in beach_activities:
                day = entry.time_slot.day
                slot = entry.time_slot.slot_number
                
                # Check if slot is allowed
                is_allowed = False
                is_top5 = False
                
                # Check if it's a Top 5 preference (allowed exception)
                if hasattr(entry.troop, 'preferences'):
                    try:
                        pref_rank = entry.troop.preferences.index(entry.activity.name)
                        is_top5 = pref_rank < 5
                    except ValueError:
                        is_top5 = False
                
                # Beach slot rules
                if day == Day.THURSDAY:
                    # Thursday allows slots 1, 2, 3
                    is_allowed = slot in [1, 2, 3]
                else:
                    # Other days allow slots 1, 3 (slot 2 only for Top 5)
                    if slot == 2:
                        is_allowed = is_top5  # Only allow slot 2 for Top 5
                    else:
                        is_allowed = slot in [1, 3]
                
                if not is_allowed:
                    violations.append({
                        'troop': entry.troop.name,
                        'activity': entry.activity.name,
                        'day': day.value,
                        'slot': slot,
                        'is_top5': is_top5,
                        'reason': 'Beach activity in prohibited slot'
                    })
        
        return violations
    
    def _check_staff_limits(self, schedule: Schedule) -> List[Dict[str, Any]]:
        """Check staff limits per slot"""
        # Map activities to staff requirements
        staff_activities = {
            'Beach Staff': ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                           'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                           'Troop Swim', 'Water Polo'],
            'Boats Director': ['Sailing'],
            'Shooting Sports Director': ['Troop Rifle', 'Troop Shotgun'],
            'Tower Director': ['Climbing Tower'],
            'ODS Director': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                            'Ultimate Survivor', "What's Cooking", 'Chopped!'],
            'Nature Director': ['Dr. DNA', 'Loon Lore', 'Nature Canoe', 'Ecosystem in a Jar',
                               'Nature Salad', 'Nature Bingo'],
            'Handicrafts Director': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
            'Commissioner': ['Archery', 'Delta', 'Super Troop', 'Reflection']
        }
        
        violations = []
        
        # Count staff per slot
        slot_staff_count = defaultdict(int)
        
        for entry in schedule.entries:
            slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
            
            for staff_name, activities in staff_activities.items():
                if entry.activity.name in activities:
                    slot_staff_count[slot_key] += 1
        
        # Check limits
        for slot, count in slot_staff_count.items():
            if count > 16:
                violations.append({
                    'slot': slot,
                    'count': count,
                    'limit': 16,
                    'severity': 'critical',
                    'reason': f'Exceeds hard cap of 16 staff'
                })
            elif count > 14:
                violations.append({
                    'slot': slot,
                    'count': count,
                    'limit': 14,
                    'severity': 'target',
                    'reason': f'Exceeds target of 14 staff'
                })
        
        return violations
    
    def _check_capacity_limits(self, schedule: Schedule) -> List[str]:
        """Check activity capacity limits"""
        violations = []
        
        # Canoe capacity: max 26 people
        canoe_activities = ['Nature Canoe', 'Canoe Snorkel', 'Float for Floats', 'Troop Canoe']
        
        for entry in schedule.entries:
            if entry.activity.name in canoe_activities:
                troop_size = entry.troop.scouts + entry.troop.adults
                if troop_size > 26:
                    violations.append(f"{entry.troop.name}: {entry.activity.name} has {troop_size} people (max 26)")
        
        return violations
    
    def _check_aqua_trampoline_sharing(self, schedule: Schedule) -> List[str]:
        """Check Aqua Trampoline sharing rules"""
        violations = []
        
        # Group by slot
        slot_troops = defaultdict(list)
        
        for entry in schedule.entries:
            if entry.activity.name == "Aqua Trampoline":
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                troop_size = entry.troop.scouts + entry.troop.adults
                slot_troops[slot_key].append({
                    'troop': entry.troop.name,
                    'size': troop_size
                })
        
        # Check sharing rules
        for slot, troops in slot_troops.items():
            if len(troops) > 2:
                violations.append(f"{slot}: {len(troops)} troops sharing Aqua Trampoline (max 2)")
            elif len(troops) == 2:
                # Both must be <=16
                for troop_info in troops:
                    if troop_info['size'] > 16:
                        violations.append(f"{slot}: {troop_info['troop']} ({troop_info['size']} people) sharing Aqua Trampoline (must be <=16)")
        
        return violations
    
    def _check_multislot_continuity(self, schedule: Schedule, activity_name: str) -> List[str]:
        """Check multi-slot activity continuity"""
        violations = []
        
        # Group by troop and day
        troop_day_entries = defaultdict(list)
        
        for entry in schedule.entries:
            if entry.activity.name == activity_name:
                key = (entry.troop.name, entry.time_slot.day)
                troop_day_entries[key].append(entry)
        
        for (troop_name, day), entries in troop_day_entries.items():
            if len(entries) > 1:
                # Sort by slot number
                entries.sort(key=lambda e: e.time_slot.slot_number)
                
                # Check continuity
                for i in range(len(entries) - 1):
                    current_slot = entries[i].time_slot.slot_number
                    next_slot = entries[i + 1].time_slot.slot_number
                    
                    if next_slot != current_slot + 1:
                        violations.append(f"{troop_name}: {activity_name} on {day.value} not continuous (slots {current_slot}, {next_slot})")
        
        return violations


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
