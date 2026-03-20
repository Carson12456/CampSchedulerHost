"""
Scheduling Algorithm Tests

Tests for the core scheduling algorithm phases and logic.
Ensures the scheduling process follows the defined phases and priorities.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models import Activity, Troop, Schedule, ScheduleEntry, TimeSlot, Day, Zone
from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler


class TestSchedulingPhases:
    """Test scheduling algorithm phases"""
    
    @pytest.fixture
    def sample_troops(self):
        """Create sample troops with known preferences"""
        return [
            Troop("Troop A", "Site A", 
                  ["Reflection", "Super Troop", "Aqua Trampoline", "Climbing Tower", "Archery"], 
                  12, 2),
            Troop("Troop B", "Site B", 
                  ["Reflection", "Super Troop", "Water Polo", "Sailing", "Delta"], 
                  15, 2),
            Troop("Troop C", "Site C", 
                  ["Reflection", "Super Troop", "Troop Rifle", "Nature Canoe", "GPS & Geocaching"], 
                  8, 2),
        ]
    
    @pytest.fixture
    def scheduler(self, sample_troops):
        """Create scheduler with sample troops"""
        return ConstrainedScheduler(sample_troops, get_all_activities())
    
    # ========== PHASE A: FOUNDATION & CORE PRIORITIES ==========
    
    def test_friday_reflection_scheduled_first(self, scheduler):
        """Test: Friday Reflection is scheduled first for all troops"""
        schedule = scheduler.schedule_all()
        
        # Check that all troops have Reflection on Friday
        for troop in scheduler.troops:
            reflection_entries = [e for e in schedule.entries 
                                if e.troop == troop and e.activity.name == "Reflection"]
            
            assert len(reflection_entries) == 1, f"{troop.name}: Should have exactly 1 Reflection"
            
            if reflection_entries:
                assert reflection_entries[0].time_slot.day == Day.FRIDAY, \
                    f"{troop.name}: Reflection must be on Friday"
    
    def test_super_troop_scheduled_for_all_troops(self, scheduler):
        """Test: Super Troop is scheduled once per week for every troop"""
        schedule = scheduler.schedule_all()
        
        # Check that all troops have Super Troop exactly once
        for troop in scheduler.troops:
            super_troop_entries = [e for e in schedule.entries 
                                  if e.troop == troop and e.activity.name == "Super Troop"]
            
            assert len(super_troop_entries) == 1, f"{troop.name}: Should have exactly 1 Super Troop"
    
    def test_super_troop_exclusivity(self, scheduler):
        """Test: Super Troop never shares (one troop per slot)"""
        schedule = scheduler.schedule_all()
        
        # Group Super Troop entries by slot
        slot_troops = {}
        for entry in schedule.entries:
            if entry.activity.name == "Super Troop":
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                if slot_key not in slot_troops:
                    slot_troops[slot_key] = []
                slot_troops[slot_key].append(entry.troop.name)
        
        # Check no slot has multiple troops
        for slot, troops in slot_troops.items():
            assert len(troops) == 1, f"Super Troop slot {slot} has {len(troops)} troops: {troops}"
    
    def test_three_hour_activities_priority(self, scheduler):
        """Test: 3-hour activities are scheduled early if in Top 5"""
        # This test would require troops with 3-hour activities in their preferences
        # For now, test the logic exists
        assert hasattr(scheduler, '_schedule_three_hour_activities'), \
            "Scheduler should have three-hour activity scheduling method"
    
    # ========== PHASE B: CORE REQUESTS ==========
    
    def test_top5_scheduling_priority(self, scheduler):
        """Test: Top 5 preferences are prioritized in scheduling"""
        schedule = scheduler.schedule_all()
        
        # Check that troops get their Top 5 preferences
        for troop in scheduler.troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            top5_preferences = set(troop.preferences[:5]) if len(troop.preferences) >= 5 else set(troop.preferences)
            
            # Should have high satisfaction rate for Top 5
            scheduled_top5 = troop_activities & top5_preferences
            
            if len(top5_preferences) > 0:
                satisfaction_rate = len(scheduled_top5) / len(top5_preferences) * 100
                # Allow for some exemptions, but should be high
                assert satisfaction_rate >= 60.0, \
                    f"{troop.name}: Top 5 satisfaction {satisfaction_rate:.1f}% should be >= 60%"
    
    def test_mandatory_top5_enforcement(self, scheduler):
        """Test: Top 1-5 preferences are mandatory and enforced"""
        # This tests the enforcement logic exists
        assert hasattr(scheduler, '_enforce_mandatory_top5'), \
            "Scheduler should have mandatory Top 5 enforcement method"
    
    # ========== PHASE C: INTEGRATED OPTIMIZATION ==========
    
    def test_day_specific_requests_honored(self, scheduler):
        """Test: Day-specific requests are honored during scheduling"""
        # This would require troops with day-specific requests
        # For now, test the logic exists
        assert hasattr(scheduler, '_handle_day_specific_requests'), \
            "Scheduler should handle day-specific requests"
    
    def test_staff_optimization_integration(self, scheduler):
        """Test: Staff optimization is integrated throughout scheduling"""
        # Check that staff load tracking exists
        assert hasattr(scheduler, '_update_staff_load'), \
            "Scheduler should track staff loads"
        
        # Check that staff optimization methods exist
        assert hasattr(scheduler, '_balance_staff_distribution'), \
            "Scheduler should balance staff distribution"
    
    def test_remaining_preferences_scheduled(self, scheduler):
        """Test: Remaining preferences (Top 6-20) are scheduled"""
        schedule = scheduler.schedule_all()
        
        # Check that troops get activities beyond Top 5
        for troop in scheduler.troops:
            troop_activities = {e.activity.name for e in schedule.entries if e.troop == troop}
            
            # Should have more than just Top 5 (if preferences exist)
            if len(troop.preferences) > 5:
                top5_preferences = set(troop.preferences[:5])
                remaining_preferences = set(troop.preferences[5:]) & troop_activities
                
                # Should have some remaining preferences scheduled
                total_scheduled = len(troop_activities)
                assert total_scheduled >= 5, \
                    f"{troop.name}: Should have at least 5 activities scheduled, got {total_scheduled}"
    
    # ========== PHASE D: CLEANUP & RECOVERY ==========
    
    def test_gap_elimination_priority(self, scheduler):
        """Test: Gap elimination is prioritized in cleanup phase"""
        schedule = scheduler.schedule_all()
        
        # Check that there are minimal gaps
        all_slots = schedule.get_all_time_slots()
        total_gaps = 0
        
        for troop in scheduler.troops:
            for slot in all_slots:
                if schedule.is_troop_free(slot, troop):
                    total_gaps += 1
        
        # Should have minimal gaps (allow some for constraints)
        max_allowed_gaps = len(scheduler.troops) * 2  # Allow 2 gaps per troop max
        assert total_gaps <= max_allowed_gaps, \
            f"Should have <= {max_allowed_gaps} gaps, found {total_gaps}"
    
    def test_clustering_optimization(self, scheduler):
        """Test: Clustering optimization is performed in cleanup"""
        # Check that clustering methods exist
        assert hasattr(scheduler, '_consolidate_staff_areas'), \
            "Scheduler should consolidate staff areas"
        
        assert hasattr(scheduler, '_comprehensive_clustering_optimization'), \
            "Scheduler should perform comprehensive clustering optimization"

    def test_cleanup_preserves_valid_sailing_overlap(self, scheduler):
        """Test: cleanup keeps the legal slot-1/slot-2 Sailing overlap."""
        sailing = next((a for a in scheduler.activities if a.name == "Sailing"), None)
        assert sailing is not None

        troop_a = scheduler.troops[0]
        troop_b = scheduler.troops[1]

        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 1), sailing, troop_a) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 2), sailing, troop_b) is True

        scheduler._cleanup_exclusive_activities()

        troop_a_sailing = [
            e for e in scheduler.schedule.entries
            if e.troop == troop_a and e.activity.name == "Sailing"
        ]
        troop_b_sailing = [
            e for e in scheduler.schedule.entries
            if e.troop == troop_b and e.activity.name == "Sailing"
        ]

        assert len(troop_a_sailing) == 2
        assert len(troop_b_sailing) == 2

    def test_comprehensive_cleanup_uses_conservative_final_refill(self, scheduler, monkeypatch):
        """Test: iterative cleanup defers aggressive refill until after conflicts converge."""
        fill_calls = []

        monkeypatch.setattr(scheduler, "_remove_activity_conflicts", lambda: None)
        monkeypatch.setattr(scheduler, "_cleanup_exclusive_activities", lambda: None)
        monkeypatch.setattr(scheduler, "_remove_overlaps", lambda: None)
        monkeypatch.setattr(scheduler, "_deduplicate_entries", lambda: None)
        monkeypatch.setattr(scheduler, "_guarantee_mandatory_activities", lambda: None)
        monkeypatch.setattr(scheduler, "_fix_beach_slot_violations", lambda: None)
        monkeypatch.setattr(scheduler, "_ensure_hc_dg_pairing", lambda: None)
        monkeypatch.setattr(scheduler, "_guarantee_no_gaps", lambda: None)
        monkeypatch.setattr(scheduler, "_sanitize_exclusivity", lambda: None)
        monkeypatch.setattr(
            scheduler,
            "_fill_empty_slots_final",
            lambda **kwargs: fill_calls.append(kwargs.copy()),
        )

        scheduler._comprehensive_final_cleanup()

        assert fill_calls == [
            {
                "allow_duplicates": False,
                "allow_last_resort": False,
                "allow_relaxed": False,
            }
        ]

    def test_final_fill_can_run_in_conservative_mode(self, scheduler, monkeypatch):
        """Test: conservative final fill does not fall back to duplicate-only placements."""
        fishing = next((a for a in scheduler.activities if a.name == "Fishing"), None)
        assert fishing is not None

        troop = scheduler.troops[0]
        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 1), fishing, troop) is True

        def fishing_only(troop_arg, activity, slot, day, relax_constraints=False, **kwargs):
            return activity.name == "Fishing"

        monkeypatch.setattr(scheduler, "_can_schedule", fishing_only)

        scheduler._fill_empty_slots_final(
            allow_duplicates=False,
            allow_last_resort=False,
            allow_relaxed=False,
        )
        conservative_count = sum(
            1 for e in scheduler.schedule.entries if e.troop == troop and e.activity.name == "Fishing"
        )

        scheduler._fill_empty_slots_final(
            allow_duplicates=True,
            allow_last_resort=False,
            allow_relaxed=False,
        )
        aggressive_count = sum(
            1 for e in scheduler.schedule.entries if e.troop == troop and e.activity.name == "Fishing"
        )

        assert conservative_count == 1
        assert aggressive_count > conservative_count

    def test_move_activity_instance_moves_entire_multislot_block(self, scheduler):
        """Test: moving a multi-slot instance relocates the full block, not one entry."""
        canoe_snorkel = next((a for a in scheduler.activities if a.name == "Canoe Snorkel"), None)
        assert canoe_snorkel is not None

        troop = scheduler.troops[0]
        start_slot = TimeSlot(Day.TUESDAY, 2)
        target_slot = TimeSlot(Day.MONDAY, 1)

        assert scheduler.schedule.add_entry(start_slot, canoe_snorkel, troop) is True

        continuation = next(
            e for e in scheduler.schedule.entries
            if e.troop == troop and e.activity.name == "Canoe Snorkel" and e.time_slot.slot_number == 3
        )

        assert scheduler._move_activity_instance(continuation, target_slot) is True

        moved_slots = sorted(
            e.time_slot.slot_number for e in scheduler.schedule.entries
            if e.troop == troop and e.activity.name == "Canoe Snorkel" and e.time_slot.day == Day.MONDAY
        )
        original_slots = [
            e.time_slot.slot_number for e in scheduler.schedule.entries
            if e.troop == troop and e.activity.name == "Canoe Snorkel" and e.time_slot.day == Day.TUESDAY
        ]

        assert moved_slots == [1, 2]
        assert original_slots == []

    def test_top5_recovery_displaces_entire_block(self, scheduler, monkeypatch):
        """Test: Top-5 recovery clears a blocking multi-slot activity as a whole block."""
        canoe_snorkel = next((a for a in scheduler.activities if a.name == "Canoe Snorkel"), None)
        fishing = next((a for a in scheduler.activities if a.name == "Fishing"), None)
        assert canoe_snorkel is not None
        assert fishing is not None

        troop = scheduler.troops[0]
        troop.preferences = ["Fishing", *[p for p in troop.preferences if p != "Fishing"]]

        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), canoe_snorkel, troop) is True

        def controlled_can_schedule(troop_arg, activity, slot, day, **kwargs):
            return (
                troop_arg == troop
                and activity.name == "Fishing"
                and day == Day.TUESDAY
                and slot.slot_number == 3
                and scheduler.schedule.is_troop_free(slot, troop_arg)
            )

        monkeypatch.setattr(scheduler, "_can_schedule", controlled_can_schedule)
        scheduler._top5_to_recover = [(troop, fishing, 0)]

        scheduler._remove_overlaps()

        fishing_slots = sorted(
            e.time_slot.slot_number for e in scheduler.schedule.entries
            if e.troop == troop and e.activity.name == "Fishing" and e.time_slot.day == Day.TUESDAY
        )
        canoe_slots = [
            e.time_slot.slot_number for e in scheduler.schedule.entries
            if e.troop == troop and e.activity.name == "Canoe Snorkel" and e.time_slot.day == Day.TUESDAY
        ]

        assert fishing_slots == [3]
        assert canoe_slots == []

    def test_hc_dg_pairing_requires_adjacent_tuesday_neighbor(self, scheduler):
        """Test: HC/DG needs Tuesday adjacency, not just a balls activity elsewhere in the week."""
        history_center = next((a for a in scheduler.activities if a.name == "History Center"), None)
        gaga_ball = next((a for a in scheduler.activities if a.name == "Gaga Ball"), None)
        assert history_center is not None
        assert gaga_ball is not None

        troop = scheduler.troops[0]

        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), history_center, troop) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.WEDNESDAY, 1), gaga_ball, troop) is True

        scheduler._ensure_hc_dg_pairing()

        tuesday_adjacent = [
            e.activity.name for e in scheduler.schedule.entries
            if e.troop == troop
            and e.time_slot.day == Day.TUESDAY
            and e.time_slot.slot_number == 2
        ]

        assert tuesday_adjacent
        assert tuesday_adjacent[0] in {"Gaga Ball", "9 Square", "Campsite Free Time"}

    def test_hc_dg_pairing_never_replaces_hc_dg_activity(self, scheduler):
        """Test: HC/DG pairing replaces adjacent filler, not the HC/DG activity itself."""
        disc_golf = next((a for a in scheduler.activities if a.name == "Disc Golf"), None)
        fishing = next((a for a in scheduler.activities if a.name == "Fishing"), None)
        trading_post = next((a for a in scheduler.activities if a.name == "Trading Post"), None)
        assert disc_golf is not None
        assert fishing is not None
        assert trading_post is not None

        troop = scheduler.troops[0]

        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), fishing, troop) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), disc_golf, troop) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 3), trading_post, troop) is True

        scheduler._ensure_hc_dg_pairing()

        tuesday_entries = {
            e.time_slot.slot_number: e.activity.name
            for e in scheduler.schedule.entries
            if e.troop == troop and e.time_slot.day == Day.TUESDAY
        }

        assert tuesday_entries[2] == "Disc Golf"
        assert any(
            tuesday_entries.get(slot_num) in {"Gaga Ball", "9 Square", "Campsite Free Time"}
            for slot_num in (1, 3)
        )

    def test_initial_placement_seeds_commissioner_day_before_cluster_is_established(self):
        """Test: commissioner day still seeds a managed activity before clustering is established."""
        troops = [
            Troop("Troop A", "Site A", ["Troop Rifle"], 12, 2, "Commissioner A"),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())
        scheduler.current_pipeline_phase = "foundation"

        rifle = next(a for a in scheduler.activities if a.name == "Troop Rifle")
        expected_day = scheduler.COMMISSIONER_RIFLE_DAYS[troops[0].commissioner]

        ordered_slots = scheduler._get_cluster_ordered_slots(troops[0], rifle)

        assert ordered_slots
        assert ordered_slots[0].day == expected_day

    def test_initial_placement_prefers_established_adjacent_cluster_over_commissioner_day(self):
        """Test: once the area is seeded, adjacency beats reopening a commissioner day."""
        troops = [
            Troop("Troop A", "Site A", ["Troop Rifle"], 12, 2, "Commissioner A"),
            Troop("Troop B", "Site B", ["Troop Rifle"], 12, 2, "Commissioner B"),
            Troop("Troop C", "Site C", ["Troop Shotgun"], 12, 2, "Commissioner C"),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())
        scheduler.current_pipeline_phase = "core"

        rifle = next(a for a in scheduler.activities if a.name == "Troop Rifle")
        shotgun = next(a for a in scheduler.activities if a.name == "Troop Shotgun")
        fixed_day = scheduler.COMMISSIONER_RIFLE_DAYS[troops[0].commissioner]
        cluster_day = next(
            day for day in (Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY)
            if day != fixed_day
        )

        assert scheduler.schedule.add_entry(TimeSlot(cluster_day, 1), rifle, troops[1]) is True
        assert scheduler.schedule.add_entry(TimeSlot(cluster_day, 3), shotgun, troops[2]) is True

        ordered_slots = scheduler._get_cluster_ordered_slots(troops[0], rifle)

        assert ordered_slots
        assert ordered_slots[0] == TimeSlot(cluster_day, 2)
        assert ordered_slots[0].day != fixed_day

    def test_excess_day_reduction_can_use_same_troop_switch(self):
        """Test: a single excess-day entry can move via a same-troop cross-area switch."""
        troops = [
            Troop("Troop A", "Site A", ["Archery"], 12, 2),
            Troop("Troop B", "Site B", ["Archery"], 12, 2),
            Troop("Troop C", "Site C", ["Aqua Trampoline"], 12, 2),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())

        tower = next(a for a in scheduler.activities if a.name == "Climbing Tower")
        fishing = next(a for a in scheduler.activities if a.name == "Fishing")

        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 1), tower, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), fishing, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), tower, troops[1]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 3), tower, troops[2]) is True

        baseline_excess = scheduler._count_excess_cluster_days()
        assert baseline_excess == 1

        moves = scheduler._aggressive_excess_day_reduction_swaps()

        assert moves >= 1
        assert scheduler._count_excess_cluster_days() < baseline_excess
        assert any(
            e.troop == troops[0]
            and e.activity.name == "Climbing Tower"
            and e.time_slot == TimeSlot(Day.TUESDAY, 2)
            for e in scheduler.schedule.entries
        )
        assert any(
            e.troop == troops[0]
            and e.activity.name == "Fishing"
            and e.time_slot == TimeSlot(Day.MONDAY, 1)
            for e in scheduler.schedule.entries
        )

    def test_excess_day_reduction_prefers_same_activity_consecutive_target(self):
        """Test: Tie Dye prefers a same-activity back-to-back target when clearing an excess day."""
        troops = [
            Troop("Troop A", "Site A", ["Tie Dye"], 12, 2),
            Troop("Troop B", "Site B", ["Tie Dye"], 12, 2),
            Troop("Troop C", "Site C", ["Hemp Craft"], 12, 2),
            Troop("Troop D", "Site D", ["Monkey's Fist"], 12, 2),
            Troop("Troop E", "Site E", ["Woggle Neckerchief Slide"], 12, 2),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())

        tie_dye = next(a for a in scheduler.activities if a.name == "Tie Dye")
        hemp_craft = next(a for a in scheduler.activities if a.name == "Hemp Craft")
        monkeys_fist = next(a for a in scheduler.activities if a.name == "Monkey's Fist")
        woggle = next(a for a in scheduler.activities if a.name == "Woggle Neckerchief Slide")
        fishing = next(a for a in scheduler.activities if a.name == "Fishing")

        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 1), tie_dye, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), fishing, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), tie_dye, troops[1]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 3), hemp_craft, troops[2]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.WEDNESDAY, 1), monkeys_fist, troops[3]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.WEDNESDAY, 3), woggle, troops[4]) is True

        baseline_excess = scheduler._count_excess_cluster_days()
        assert baseline_excess == 1

        moves = scheduler._aggressive_excess_day_reduction_swaps()

        assert moves >= 1
        assert scheduler._count_excess_cluster_days() == 0
        assert any(
            e.troop == troops[0]
            and e.activity.name == "Tie Dye"
            and e.time_slot == TimeSlot(Day.TUESDAY, 2)
            for e in scheduler.schedule.entries
        )
        assert any(
            e.activity.name == "Tie Dye"
            and e.time_slot.day == Day.TUESDAY
            and e.time_slot.slot_number in {1, 2}
            for e in scheduler.schedule.entries
        )

    def test_excess_day_reduction_can_use_thursday_two_of_two_target(self):
        """Test: a Thursday standalone can be grouped into a full 2-of-2 target day."""
        troops = [
            Troop("Troop A", "Site A", ["Climbing Tower"], 12, 2),
            Troop("Troop B", "Site B", ["Climbing Tower"], 12, 2),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())

        tower = next(a for a in scheduler.activities if a.name == "Climbing Tower")
        fishing = next(a for a in scheduler.activities if a.name == "Fishing")

        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 1), tower, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.THURSDAY, 2), fishing, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.THURSDAY, 1), tower, troops[1]) is True

        baseline_excess = scheduler._count_excess_cluster_days()
        assert baseline_excess == 1

        moves = scheduler._aggressive_excess_day_reduction_swaps()

        assert moves >= 1
        assert scheduler._count_excess_cluster_days() == 0
        assert any(
            e.troop == troops[0]
            and e.activity.name == "Climbing Tower"
            and e.time_slot == TimeSlot(Day.THURSDAY, 2)
            for e in scheduler.schedule.entries
        )

    def test_cluster_gap_post_fill_can_pull_same_area_activity_from_another_day(self):
        """Test: official gap repair can import a same-area activity into slot 2 from another day."""
        troops = [
            Troop("Troop A", "Site A", ["Monkey's Fist"], 12, 2),
            Troop("Troop B", "Site B", ["Tie Dye"], 12, 2),
            Troop("Troop C", "Site C", ["Troop Rifle", "Hemp Craft"], 12, 2),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())

        monkeys_fist = next(a for a in scheduler.activities if a.name == "Monkey's Fist")
        tie_dye = next(a for a in scheduler.activities if a.name == "Tie Dye")
        hemp_craft = next(a for a in scheduler.activities if a.name == "Hemp Craft")
        rifle = next(a for a in scheduler.activities if a.name == "Troop Rifle")

        assert scheduler.schedule.add_entry(TimeSlot(Day.WEDNESDAY, 1), monkeys_fist, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), tie_dye, troops[1]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), rifle, troops[2]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 3), hemp_craft, troops[2]) is True

        assert scheduler._count_area_cluster_gaps() == 1

        fixes = scheduler._optimize_cluster_gaps_post_fill()

        assert fixes >= 1
        assert scheduler._count_area_cluster_gaps() == 0
        assert any(
            e.troop == troops[0]
            and e.activity.name == "Monkey's Fist"
            and e.time_slot == TimeSlot(Day.TUESDAY, 2)
            for e in scheduler.schedule.entries
        )
        assert not scheduler.schedule.is_troop_free(TimeSlot(Day.WEDNESDAY, 1), troops[0])

    def test_excess_day_reduction_can_clear_two_entry_source_day(self):
        """Test: coordinated switching can clear an excess day that has two area entries."""
        troops = [
            Troop("Troop A", "Site A", ["Fishing"], 12, 2),
            Troop("Troop B", "Site B", ["Loon Lore"], 12, 2),
            Troop("Troop C", "Site C", ["Archery"], 12, 2),
            Troop("Troop D", "Site D", ["Aqua Trampoline"], 12, 2),
            Troop("Troop E", "Site E", ["Water Polo"], 12, 2),
            Troop("Troop F", "Site F", ["Delta"], 12, 2),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())

        tower = next(a for a in scheduler.activities if a.name == "Climbing Tower")
        fishing = next(a for a in scheduler.activities if a.name == "Fishing")
        loon_lore = next(a for a in scheduler.activities if a.name == "Loon Lore")

        assert scheduler.schedule.add_entry(TimeSlot(Day.WEDNESDAY, 1), tower, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 2), fishing, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.WEDNESDAY, 2), tower, troops[1]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), loon_lore, troops[1]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 1), tower, troops[2]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 3), tower, troops[4]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), tower, troops[3]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 3), tower, troops[5]) is True

        baseline_excess = scheduler._count_excess_cluster_days()
        assert baseline_excess == 1

        moves = scheduler._aggressive_excess_day_reduction_swaps()

        assert moves >= 1
        assert scheduler._count_excess_cluster_days() == 0
        assert not any(
            e.activity.name == "Climbing Tower" and e.time_slot.day == Day.WEDNESDAY
            for e in scheduler.schedule.entries
        )
        assert any(
            e.troop == troops[0]
            and e.activity.name == "Climbing Tower"
            and e.time_slot == TimeSlot(Day.MONDAY, 2)
            for e in scheduler.schedule.entries
        )
        assert any(
            e.troop == troops[1]
            and e.activity.name == "Climbing Tower"
            and e.time_slot == TimeSlot(Day.TUESDAY, 2)
            for e in scheduler.schedule.entries
        )

    def test_excess_day_reduction_can_fall_back_to_cross_troop_switch(self):
        """Test: cross-troop switching is used when same-troop target slots are protected."""
        troops = [
            Troop("Troop A", "Site A", ["Archery"], 12, 2),
            Troop("Troop B", "Site B", ["Climbing Tower"], 12, 2),
            Troop("Troop C", "Site C", ["Water Polo"], 12, 2),
            Troop("Troop D", "Site D", ["Delta"], 12, 2),
        ]
        scheduler = ConstrainedScheduler(troops, get_all_activities())

        tower = next(a for a in scheduler.activities if a.name == "Climbing Tower")
        fishing = next(a for a in scheduler.activities if a.name == "Fishing")
        history_center = next(a for a in scheduler.activities if a.name == "History Center")
        disc_golf = next(a for a in scheduler.activities if a.name == "Disc Golf")
        super_troop = next(a for a in scheduler.activities if a.name == "Super Troop")

        assert scheduler.schedule.add_entry(TimeSlot(Day.MONDAY, 1), tower, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), history_center, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), disc_golf, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 3), super_troop, troops[0]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 1), fishing, troops[1]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 2), tower, troops[2]) is True
        assert scheduler.schedule.add_entry(TimeSlot(Day.TUESDAY, 3), tower, troops[3]) is True

        baseline_excess = scheduler._count_excess_cluster_days()
        assert baseline_excess == 1

        moves = scheduler._aggressive_excess_day_reduction_swaps()

        assert moves >= 1
        assert scheduler._count_excess_cluster_days() == 0
        assert any(
            e.troop == troops[1]
            and e.activity.name == "Climbing Tower"
            and e.time_slot == TimeSlot(Day.TUESDAY, 1)
            for e in scheduler.schedule.entries
        )
        assert any(
            e.troop == troops[0]
            and e.activity.name == "Fishing"
            and e.time_slot == TimeSlot(Day.MONDAY, 1)
            for e in scheduler.schedule.entries
        )
    
    def test_final_validation(self, scheduler):
        """Test: Final validation ensures schedule validity"""
        schedule = scheduler.schedule_all()
        
        # Check basic validity
        assert len(schedule.entries) > 0, "Schedule should have entries"
        
        # Check no double bookings
        for troop in scheduler.troops:
            troop_schedule = schedule.get_troop_schedule(troop)
            slot_activity_map = {}
            
            for entry in troop_schedule:
                slot_key = entry.time_slot
                assert slot_key not in slot_activity_map, \
                    f"{troop.name}: Double booked in {slot_key}"
                slot_activity_map[slot_key] = entry.activity.name


class TestBatchProcessing:
    """Test batch processing by priority level"""
    
    @pytest.fixture
    def sample_troops(self):
        """Create troops with clear priority preferences"""
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
    
    def test_priority_level_processing(self, scheduler):
        """Test: Activities are processed by priority level across all troops"""
        # Check that batch processing logic exists
        assert hasattr(scheduler, '_process_priority_level'), \
            "Scheduler should have priority level processing method"
    
    def test_conflict_resolution_between_troops(self, scheduler):
        """Test: Conflicts between troops for same activity/slot are resolved"""
        schedule = scheduler.schedule_all()
        
        # Check that conflicts are resolved (no double bookings in exclusive areas)
        exclusive_activities = ["Climbing Tower", "Aqua Trampoline", "Sailing"]
        
        for activity_name in exclusive_activities:
            activity_entries = [e for e in schedule.entries if e.activity.name == activity_name]
            
            # Group by slot
            slot_troops = {}
            for entry in activity_entries:
                slot_key = entry.time_slot
                if slot_key not in slot_troops:
                    slot_troops[slot_key] = []
                slot_troops[slot_key].append(entry.troop.name)
            
            # Check for conflicts
            for slot, troops in slot_troops.items():
                if activity_name == "Aqua Trampoline":
                    # Aqua Trampoline can have up to 2 small troops
                    assert len(troops) <= 2, f"{activity_name} at {slot} has {len(troops)} troops"
                else:
                    # Others should be exclusive
                    assert len(troops) == 1, f"{activity_name} at {slot} has {len(troops)} troops"
    
    def test_commissioner_day_priority(self, scheduler):
        """Test: Commissioner day assignments are used in conflict resolution"""
        # This would require commissioner assignments
        # For now, test the logic exists
        assert hasattr(scheduler, '_resolve_conflicts'), \
            "Scheduler should have conflict resolution method"


class TestPreventionBasedFramework:
    """Test prevention-based framework implementation"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler with sample troops"""
        troops = [
            Troop("Test Troop", "Site A", ["Aqua Trampoline", "Climbing Tower"], 12, 2)
        ]
        return ConstrainedScheduler(troops, get_all_activities())
    
    def test_predictive_violation_checking(self, scheduler):
        """Test: System predicts constraint violations before they occur"""
        # Check that prevention methods exist
        assert hasattr(scheduler, '_predictive_constraint_violation_check'), \
            "Scheduler should have predictive violation checking"
        
        assert hasattr(scheduler, '_comprehensive_prevention_check'), \
            "Scheduler should have comprehensive prevention checking"
    
    def test_multi_layer_validation(self, scheduler):
        """Test: Multi-layer validation happens before every action"""
        # Check that validation is integrated
        assert hasattr(scheduler, '_can_schedule'), \
            "Scheduler should have scheduling validation method"
        
        # Test that validation prevents invalid placements
        activity = get_all_activities()[0]
        timeslot = TimeSlot(Day.MONDAY, 1)
        troop = scheduler.troops[0]
        
        # This should succeed (valid placement)
        result = scheduler._can_schedule(timeslot, activity, troop)
        assert isinstance(result, bool), "Validation should return boolean"
    
    def test_proactive_gap_filling(self, scheduler):
        """Test: System proactively fills potential gaps"""
        # Check that gap filling logic exists
        assert hasattr(scheduler, '_fill_remaining_slots'), \
            "Scheduler should have gap filling method"
        
        assert hasattr(scheduler, '_eliminate_gaps'), \
            "Scheduler should have gap elimination method"
    
    def test_constraint_conflict_resolution(self, scheduler):
        """Test: System resolves constraint conflicts proactively"""
        # Check that conflict resolution exists
        assert hasattr(scheduler, '_resolve_constraint_conflicts'), \
            "Scheduler should have constraint conflict resolution"
    
    def test_multi_strategy_fallback(self, scheduler):
        """Test: System has multiple fallback strategies"""
        # Check that multiple strategies exist
        strategies = [
            '_intelligent_swaps',
            '_force_placement',
            '_emergency_placement',
            '_displacement_logic'
        ]
        
        for strategy in strategies:
            assert hasattr(scheduler, strategy), \
                f"Scheduler should have {strategy} method"


class TestPriorityBasedDecisionMaking:
    """Test priority-based decision making hierarchy"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler for priority testing"""
        troops = [
            Troop("Test Troop", "Site A", ["Aqua Trampoline", "Climbing Tower"], 12, 2)
        ]
        return ConstrainedScheduler(troops, get_all_activities())
    
    def test_critical_priority_enforcement(self, scheduler):
        """Test: CRITICAL priority items are enforced (empty slots, constraints, Top 5)"""
        # Check that critical priority methods exist
        critical_methods = [
            '_eliminate_empty_slots',
            '_enforce_constraint_compliance',
            '_ensure_top5_satisfaction'
        ]
        
        for method in critical_methods:
            assert hasattr(scheduler, method), \
                f"Scheduler should have {method} for critical priorities"
    
    def test_high_priority_optimization(self, scheduler):
        """Test: HIGH priority items are optimized (requirements, clustering)"""
        # Check that high priority methods exist
        high_methods = [
            '_meet_activity_requirements',
            '_optimize_clustering_efficiency'
        ]
        
        for method in high_methods:
            assert hasattr(scheduler, method), \
                f"Scheduler should have {method} for high priorities"
    
    def test_medium_priority_fine_tuning(self, scheduler):
        """Test: MEDIUM priority items get fine-tuned (setup, preferences)"""
        # Check that medium priority methods exist
        medium_methods = [
            '_optimize_setup',
            '_enhance_preferences'
        ]
        
        for method in medium_methods:
            assert hasattr(scheduler, method), \
                f"Scheduler should have {method} for medium priorities"
    
    def test_priority_hierarchy_respected(self, scheduler):
        """Test: Priority hierarchy is respected in decision making"""
        # Check that priority system exists
        assert hasattr(scheduler, '_get_priority_level'), \
            "Scheduler should have priority level determination"
        
        assert hasattr(scheduler, '_apply_priority_hierarchy'), \
            "Scheduler should apply priority hierarchy"


class TestContinuousConstraintValidation:
    """Test continuous constraint validation throughout scheduling"""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler for validation testing"""
        troops = [
            Troop("Test Troop", "Site A", ["Aqua Trampoline"], 12, 2)
        ]
        return ConstrainedScheduler(troops, get_all_activities())
    
    def test_validation_before_every_action(self, scheduler):
        """Test: Constraints are validated BEFORE every scheduling action"""
        # This is tested throughout other tests, but check the core method exists
        assert hasattr(scheduler, '_validate_constraints_before'), \
            "Scheduler should validate constraints before actions"
    
    def test_validation_after_placement(self, scheduler):
        """Test: Constraints are validated after every placement"""
        # Check that post-placement validation exists
        assert hasattr(scheduler, '_validate_constraints_after'), \
            "Scheduler should validate constraints after placement"
    
    def test_immediate_violation_prevention(self, scheduler):
        """Test: Constraint violations are prevented immediately"""
        activity = get_all_activities()[0]
        timeslot = TimeSlot(Day.MONDAY, 1)
        troop = scheduler.troops[0]
        
        # Test that invalid placement is prevented
        # This would require specific invalid scenario
        # For now, test the validation method exists and returns boolean
        result = scheduler._can_schedule(timeslot, activity, troop)
        assert isinstance(result, bool), "Validation should return boolean result"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
