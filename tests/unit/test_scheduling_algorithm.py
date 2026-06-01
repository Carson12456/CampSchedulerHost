import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from activities import get_activity_by_name, get_all_activities
from constrained_scheduler import ConstrainedScheduler
from core.services.unscheduled_source import (
    build_unscheduled_data,
    summarize_non_exempt_misses,
)
from models import Day, Schedule, ScheduleEntry, TimeSlot, Troop


@pytest.fixture
def sample_troops():
    return [
        Troop(
            "Troop A",
            "Site A",
            ["Reflection", "Super Troop", "Aqua Trampoline", "Climbing Tower", "Archery"],
            12,
            2,
        ),
        Troop(
            "Troop B",
            "Site B",
            ["Reflection", "Super Troop", "Water Polo", "Sailing", "Delta"],
            15,
            2,
        ),
        Troop(
            "Troop C",
            "Site C",
            ["Reflection", "Super Troop", "Troop Rifle", "Nature Canoe", "GPS & Geocaching"],
            8,
            2,
        ),
    ]


@pytest.fixture
def scheduler(sample_troops):
    return ConstrainedScheduler(sample_troops, get_all_activities())


def test_mandatory_anchors_are_scheduled(scheduler):
    schedule = scheduler.schedule_all()

    for troop in scheduler.troops:
        reflection_entries = [
            entry
            for entry in schedule.entries
            if entry.troop == troop and entry.activity.name == "Reflection"
        ]
        super_troop_entries = [
            entry
            for entry in schedule.entries
            if entry.troop == troop and entry.activity.name == "Super Troop"
        ]

        assert len(reflection_entries) == 1
        assert reflection_entries[0].time_slot.day == Day.FRIDAY
        assert len(super_troop_entries) == 1


def test_top5_contract_uses_authoritative_unscheduled_summary(scheduler):
    schedule = scheduler.schedule_all()
    unscheduled = build_unscheduled_data(scheduler.troops, schedule)
    summary = summarize_non_exempt_misses(unscheduled)

    assert summary["missing_top5"] == 0


def test_final_schedule_has_no_double_bookings(scheduler):
    schedule = scheduler.schedule_all()

    for troop in scheduler.troops:
        seen_slots = set()
        for entry in schedule.get_troop_schedule(troop):
            assert entry.time_slot not in seen_slots
            seen_slots.add(entry.time_slot)


def test_friday_gap_uses_first_available_default_fill():
    """Default fill should respect SKULL fill priority for a Friday slot."""
    troop = Troop("Test Troop", "Site A", [], 12, 2)
    scheduler = ConstrainedScheduler([troop], get_all_activities())

    occupied = [
        (Day.MONDAY, 1, "Aqua Trampoline"),
        (Day.MONDAY, 2, "Archery"),
        (Day.MONDAY, 3, "Water Polo"),
        (Day.TUESDAY, 1, "History Center"),
        (Day.TUESDAY, 2, "Disc Golf"),
        (Day.TUESDAY, 3, "Fishing"),
        (Day.WEDNESDAY, 1, "Troop Swim"),
        (Day.WEDNESDAY, 2, "Trading Post"),
        (Day.WEDNESDAY, 3, "Dr. DNA"),
        (Day.THURSDAY, 1, "Loon Lore"),
        (Day.THURSDAY, 2, "9 Square"),
        (Day.FRIDAY, 2, "Super Troop"),
        (Day.FRIDAY, 3, "Reflection"),
    ]
    for day, slot_num, activity_name in occupied:
        scheduler.schedule.entries.append(
            ScheduleEntry(
                TimeSlot(day, slot_num),
                get_activity_by_name(activity_name),
                troop,
            )
        )

    scheduler._fill_all_remaining()

    friday_slot_one = [
        entry.activity.name
        for entry in scheduler.schedule.entries
        if entry.troop == troop
        and entry.time_slot.day == Day.FRIDAY
        and entry.time_slot.slot_number == 1
    ]
    assert friday_slot_one == ["Campsite Free Time"]


def test_water_games_same_day_pair_is_soft_violation():
    troop = Troop(
        "Test Troop",
        "Site A",
        ["Aqua Trampoline", "Water Polo", "Greased Watermelon"],
        12,
        2,
    )
    scheduler = ConstrainedScheduler([troop], get_all_activities())

    scheduler.schedule.entries.append(
        ScheduleEntry(
            TimeSlot(Day.THURSDAY, 1),
            get_activity_by_name("Aqua Trampoline"),
            troop,
        )
    )
    water_polo = get_activity_by_name("Water Polo")

    assert not scheduler._can_schedule(
        troop,
        water_polo,
        TimeSlot(Day.THURSDAY, 2),
        Day.THURSDAY,
        relax_constraints=False,
    )
    assert scheduler._can_schedule(
        troop,
        water_polo,
        TimeSlot(Day.THURSDAY, 2),
        Day.THURSDAY,
        relax_constraints=True,
    )

    scheduler.schedule.entries = [
        ScheduleEntry(
            TimeSlot(Day.MONDAY, 1),
            get_activity_by_name("Aqua Trampoline"),
            troop,
        ),
        ScheduleEntry(TimeSlot(Day.MONDAY, 2), water_polo, troop),
        ScheduleEntry(
            TimeSlot(Day.MONDAY, 3),
            get_activity_by_name("Greased Watermelon"),
            troop,
        ),
    ]

    assert scheduler._count_global_water_games_pair_violations() == 3


def _f02_troop():
    """Troop with a Top-5 list used by the F-02 displacement-exemption tests."""
    return Troop(
        "Troop X",
        "Site X",
        ["Climbing Tower", "Archery", "Sailing", "Water Polo", "Fishing"],
        12,
        2,
        day_requests={"Wednesday": ["Trading Post"]},
    )


def test_f02_unrelated_honored_day_request_does_not_exempt_real_miss():
    """F-02 over-loose direction: an unrelated honored (free-slot) day request
    must NOT blanket-exempt a higher-ranked Top-5 miss it never displaced.

    The legacy rank heuristic exempted any higher-ranked miss whenever an
    unranked honored request existed (here Trading Post), masking the real
    Climbing Tower miss. With provenance, no displacement was recorded, so the
    miss is correctly non-exempt.
    """
    troop = _f02_troop()
    schedule = Schedule()
    # Trading Post honored on its requested day in a free slot (displaced nothing).
    schedule.entries.append(
        ScheduleEntry(TimeSlot(Day.WEDNESDAY, 1), get_activity_by_name("Trading Post"), troop)
    )
    # Archery (#2) placed; Climbing Tower (#1) is a genuine, undisplaced miss.
    schedule.entries.append(
        ScheduleEntry(TimeSlot(Day.MONDAY, 1), get_activity_by_name("Archery"), troop)
    )

    unscheduled = build_unscheduled_data([troop], schedule, day_request_displacements=set())
    tower = next(item for item in unscheduled["Troop X"]["top5"] if item["name"] == "Climbing Tower")
    assert tower["is_exempt"] is False


def test_f02_displaced_preference_is_exempt_via_provenance():
    """F-02 over-strict direction: a Top-5 that a MUST-HONOR request actually
    displaced (recorded as provenance) IS exempt, so the run is not aborted."""
    troop = _f02_troop()
    schedule = Schedule()
    schedule.entries.append(
        ScheduleEntry(TimeSlot(Day.WEDNESDAY, 1), get_activity_by_name("Trading Post"), troop)
    )
    displacements = {("Troop X", "Climbing Tower")}

    unscheduled = build_unscheduled_data([troop], schedule, day_request_displacements=displacements)
    tower = next(item for item in unscheduled["Troop X"]["top5"] if item["name"] == "Climbing Tower")
    assert tower["is_exempt"] is True

    # All five Top-5 are missing; only the displaced Climbing Tower is exempt,
    # so the authoritative non-exempt summary counts the other four.
    summary = summarize_non_exempt_misses(unscheduled)
    assert summary["missing_top5"] == 4


def test_f02_missed_activity_itself_day_requested_is_exempt():
    """BRAIN §2 Exemption 4(a): a missed activity that is itself day-requested
    stays exempt (physical impossibility accepted), independent of provenance."""
    troop = Troop(
        "Troop X",
        "Site X",
        ["Climbing Tower", "Archery", "Sailing", "Water Polo", "Fishing"],
        12,
        2,
        day_requests={"Monday": ["Climbing Tower"]},
    )
    schedule = Schedule()
    schedule.entries.append(
        ScheduleEntry(TimeSlot(Day.MONDAY, 1), get_activity_by_name("Archery"), troop)
    )

    unscheduled = build_unscheduled_data([troop], schedule, day_request_displacements=set())
    tower = next(item for item in unscheduled["Troop X"]["top5"] if item["name"] == "Climbing Tower")
    assert tower["is_exempt"] is True


def test_f02_scheduler_exposes_day_request_displacement_provenance(scheduler):
    """The aggressive seal must expose a (troop, activity) provenance set so the
    Top-5 gate and schedule JSON can reproduce Exemption 4(b)."""
    scheduler.schedule_all()
    assert isinstance(scheduler.day_request_displacements, set)
    for item in scheduler.day_request_displacements:
        assert isinstance(item, tuple) and len(item) == 2


def test_f04a_is_honored_day_request_entry_detects_requested_day_only():
    """The protection predicate must match the activity on its requested day only."""
    troop = Troop(
        "Troop X", "Site X",
        ["Archery", "Fishing", "Orienteering", "Loon Lore", "Tie Dye"],
        12, 2, "", {"Monday": ["Campsite Free Time"]},
    )
    scheduler = ConstrainedScheduler([troop], get_all_activities())
    cft = get_activity_by_name("Campsite Free Time")

    honored = ScheduleEntry(TimeSlot(Day.MONDAY, 1), cft, troop)
    wrong_day = ScheduleEntry(TimeSlot(Day.TUESDAY, 1), cft, troop)
    other = ScheduleEntry(TimeSlot(Day.MONDAY, 2), get_activity_by_name("Archery"), troop)

    assert scheduler._is_honored_day_request_entry(honored) is True
    assert scheduler._is_honored_day_request_entry(wrong_day) is False
    assert scheduler._is_honored_day_request_entry(other) is False


def test_f04a_honored_day_request_filler_survives_final_audit():
    """F-04A: a day-requested filler placed on its requested day must NOT be
    swapped out by the final filler->preference audit, even when a higher-ranked
    unscheduled preference would otherwise fit the slot."""
    troop = Troop(
        "Troop X", "Site X",
        ["Archery", "Fishing", "Orienteering", "Loon Lore", "Tie Dye"],
        12, 2, "", {"Monday": ["Campsite Free Time"]},
    )
    scheduler = ConstrainedScheduler([troop], get_all_activities())
    scheduler.schedule.entries.append(
        ScheduleEntry(TimeSlot(Day.MONDAY, 1), get_activity_by_name("Campsite Free Time"), troop)
    )

    scheduler._finalize_filler_replacement_audit()

    monday1 = [
        e.activity.name
        for e in scheduler.schedule.entries
        if e.troop == troop and e.time_slot == TimeSlot(Day.MONDAY, 1)
    ]
    assert monday1 == ["Campsite Free Time"]


def test_f04a_honored_beach_day_request_survives_saturation_fix():
    """F-04A: beach saturation must not displace a honored day-requested beach
    activity (BRAIN §10.3 lets MUST-HONOR exceed the beach staff cap)."""
    activities = get_all_activities()
    beach_staffed = [
        "Underwater Obstacle Course", "Aqua Trampoline", "Water Polo",
        "Troop Swim", "Greased Watermelon",
    ]
    # First troop day-requests its (unranked) beach activity so, absent the
    # protection, it would be the first-chosen victim during saturation.
    troops = []
    for idx, act_name in enumerate(beach_staffed):
        day_requests = {"Monday": [act_name]} if idx == 0 else {}
        troops.append(
            Troop(f"BT{idx}", f"Site{idx}", ["Archery", "Fishing", "Orienteering"], 10, 2, "", day_requests)
        )
    scheduler = ConstrainedScheduler(troops, activities)
    for troop, act_name in zip(troops, beach_staffed):
        scheduler.schedule.entries.append(
            ScheduleEntry(TimeSlot(Day.MONDAY, 1), get_activity_by_name(act_name), troop)
        )

    scheduler._fix_beach_activity_saturation()

    protected = [
        e for e in scheduler.schedule.entries
        if e.troop == troops[0]
        and e.time_slot == TimeSlot(Day.MONDAY, 1)
        and e.activity.name == "Underwater Obstacle Course"
    ]
    assert protected, "Honored beach day request must survive saturation fixing"


def test_f04a_revalidate_raises_when_sealed_day_request_dropped():
    """The fail-closed audit must raise iff a sealed honored request is gone."""
    troop = Troop(
        "Troop X", "Site X", ["Archery", "Fishing", "Orienteering"],
        12, 2, "", {"Monday": ["Shower House"]},
    )
    scheduler = ConstrainedScheduler([troop], get_all_activities())
    sh_entry = ScheduleEntry(TimeSlot(Day.MONDAY, 1), get_activity_by_name("Shower House"), troop)
    scheduler.schedule.entries.append(sh_entry)

    scheduler._sealed_honored_day_requests = scheduler._collect_honored_day_requests()
    assert ("Troop X", "MONDAY", "Shower House") in scheduler._sealed_honored_day_requests

    # Still honored -> no raise.
    scheduler._revalidate_sealed_day_requests()

    # Drop the honored request -> fail closed.
    scheduler.schedule.entries.remove(sh_entry)
    with pytest.raises(ValueError):
        scheduler._revalidate_sealed_day_requests()


def test_f04a_day_request_filler_honored_after_full_schedule():
    """End-to-end: a day-requested filler is honored on its requested day and
    survives the entire schedule_all() tail (seal + post-seal mutators)."""
    troop = Troop(
        "Troop X", "Site X",
        ["Archery", "Fishing", "Orienteering", "Loon Lore", "Tie Dye"],
        12, 2, "", {"Monday": ["Campsite Free Time"]},
    )
    scheduler = ConstrainedScheduler([troop], get_all_activities())
    schedule = scheduler.schedule_all()

    honored = [
        e for e in schedule.entries
        if e.troop == troop
        and e.time_slot.day == Day.MONDAY
        and e.activity.name == "Campsite Free Time"
    ]
    assert honored, "Day-requested Campsite Free Time should be honored on Monday"
    assert ("Troop X", "MONDAY", "Campsite Free Time") in scheduler._sealed_honored_day_requests


def test_exclusive_activity_caps_allow_sailing_slot_two_overlap(scheduler):
    schedule = scheduler.schedule_all()
    exclusive_activities = {"Climbing Tower", "Aqua Trampoline", "Sailing"}

    for activity_name in exclusive_activities:
        slot_troops = {}
        for entry in schedule.entries:
            if entry.activity.name == activity_name:
                slot_troops.setdefault(entry.time_slot, []).append(entry.troop.name)

        for slot, troops in slot_troops.items():
            if activity_name == "Aqua Trampoline":
                assert len(troops) <= 2
            elif activity_name == "Sailing":
                max_cap = 2 if slot.slot_number == 2 else 1
                assert len(troops) <= max_cap
            else:
                assert len(troops) == 1
