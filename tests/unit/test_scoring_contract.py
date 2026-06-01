import json

from core.activities import get_activity_by_name
from core.models import Day, Schedule, ScheduleEntry, TimeSlot, Troop
from core.scheduler import config_loader
from utils.regression_checker import (
    _calculate_at_sharing_misses,
    _calculate_delta_timing_penalty,
    DEFAULT_WEIGHTS,
    evaluate_week,
)


def test_voyageur_commissioner_alias_maps_commissioner_to_voyageur():
    """F-05: the shared alias mirrors Commissioner A/B/C days onto Voyageur A/B/C."""
    base = config_loader.get_commissioner_activity_days("Delta")
    assert "Commissioner A" in base  # sanity: rotation defines a Delta day

    aliased = config_loader.apply_voyageur_commissioner_alias(dict(base))
    for suffix in ("A", "B", "C"):
        if f"Commissioner {suffix}" in base:
            assert aliased[f"Voyageur {suffix}"] == base[f"Commissioner {suffix}"]


def test_evaluate_week_commissioner_pct_nonzero_for_voyageur(tmp_path):
    """F-05: a Voyageur troop (commissioner 'Voyageur A') must produce real
    commissioner-day checks, not collapse to 0 checks / 0.0% as before."""
    week_name = "voyageur_alias_week"
    troop_file = tmp_path / f"{week_name}.json"
    schedule_file = tmp_path / f"{week_name}_schedule.json"

    delta_day = config_loader.get_commissioner_activity_days("Delta")["Commissioner A"]

    troop = {
        "name": "Voyageur Troop",
        "campsite": "Site",
        "scouts": 10,
        "adults": 2,
        "commissioner": "Voyageur A",
        "preferences": ["Delta", "Super Troop", "Reflection", "Fishing", "Gaga Ball"],
    }
    troop_file.write_text(json.dumps({"troops": [troop]}), encoding="utf-8")

    # Schedule all five Top-5 preferences so the authoritative unscheduled
    # payload ({}) matches the computed misses (0) and the cross-check passes.
    entries = [
        {"troop_name": "Voyageur Troop", "activity_name": "Delta", "day": delta_day.name, "slot": 1},
        {"troop_name": "Voyageur Troop", "activity_name": "Fishing", "day": "TUESDAY", "slot": 1},
        {"troop_name": "Voyageur Troop", "activity_name": "Gaga Ball", "day": "TUESDAY", "slot": 2},
        {"troop_name": "Voyageur Troop", "activity_name": "Super Troop", "day": "FRIDAY", "slot": 2},
        {"troop_name": "Voyageur Troop", "activity_name": "Reflection", "day": "FRIDAY", "slot": 3},
    ]
    schedule_file.write_text(
        json.dumps({"troops": [troop], "entries": entries, "unscheduled": {}}),
        encoding="utf-8",
    )

    metrics = evaluate_week(str(troop_file), schedules_dir=tmp_path)

    # Before F-05 the Voyageur alias was absent in the checker, so no day-map key
    # matched, commissioner_day_checks was 0, and compliance collapsed to 0.0.
    assert metrics["commissioner_day_checks"] >= 1
    assert metrics["commissioner_day_compliance_pct"] > 0.0


def _entry(troop, activity_name, day, slot):
    activity = get_activity_by_name(activity_name)
    assert activity is not None, f"Missing test activity: {activity_name}"
    return ScheduleEntry(TimeSlot(day, slot), activity, troop)


def test_delta_timing_penalty_uses_earliest_needed_window():
    schedule = Schedule()
    monday_only_troops = [
        Troop(f"Troop {idx}", "Site", ["Delta"], 10, 2)
        for idx in range(3)
    ]
    schedule.entries.append(_entry(monday_only_troops[0], "Delta", Day.WEDNESDAY, 1))

    penalty, details, required_idx = _calculate_delta_timing_penalty(
        schedule,
        monday_only_troops,
        DEFAULT_WEIGHTS,
    )

    assert required_idx == 0
    assert penalty == 4.0
    assert details

    monday_tuesday_troops = [
        Troop(f"Troop {idx}", "Site", ["Delta"], 10, 2)
        for idx in range(6)
    ]
    later_penalty, _, later_required_idx = _calculate_delta_timing_penalty(
        schedule,
        monday_tuesday_troops,
        DEFAULT_WEIGHTS,
    )

    assert later_required_idx == 1
    assert later_penalty == 2.0


def test_at_sharing_counts_only_avoidable_missed_pairs():
    troops = [Troop(f"Troop {idx}", "Site", ["Aqua Trampoline"], 10, 2) for idx in range(4)]
    unshared = Schedule(
        entries=[
            _entry(troops[0], "Aqua Trampoline", Day.MONDAY, 1),
            _entry(troops[1], "Aqua Trampoline", Day.MONDAY, 2),
            _entry(troops[2], "Aqua Trampoline", Day.TUESDAY, 1),
            _entry(troops[3], "Aqua Trampoline", Day.TUESDAY, 2),
        ]
    )
    shared = Schedule(
        entries=[
            _entry(troops[0], "Aqua Trampoline", Day.MONDAY, 1),
            _entry(troops[1], "Aqua Trampoline", Day.MONDAY, 1),
            _entry(troops[2], "Aqua Trampoline", Day.TUESDAY, 1),
            _entry(troops[3], "Aqua Trampoline", Day.TUESDAY, 1),
        ]
    )

    assert _calculate_at_sharing_misses(unshared) == 2
    assert _calculate_at_sharing_misses(shared) == 0


def test_evaluate_week_uses_bounded_point_components(tmp_path):
    week_name = "scoring_contract_week"
    troop_file = tmp_path / f"{week_name}.json"
    schedule_file = tmp_path / f"{week_name}_schedule.json"

    preferences = [
        "Delta",
        "Super Troop",
        "Reflection",
        "Fishing",
        "9 Square",
        "Gaga Ball",
        "Trading Post",
        "Shower House",
        "Dr. DNA",
        "Loon Lore",
        "Hemp Craft",
        "Monkey's Fist",
        "Tie Dye",
        "Woggle Neckerchief Slide",
        "Campsite Free Time",
        "History Center",
        "Disc Golf",
        "Ecosystem in a Jar",
        "Nature Salad",
        "Nature Bingo",
    ]
    troop = {
        "name": "Scoring Troop",
        "campsite": "Site",
        "scouts": 10,
        "adults": 2,
        "preferences": preferences,
    }
    troop_file.write_text(json.dumps({"troops": [troop]}), encoding="utf-8")

    base_entries = [
        ("Delta", "MONDAY", 1),
        ("Fishing", "MONDAY", 2),
        ("9 Square", "MONDAY", 3),
        ("History Center", "TUESDAY", 1),
        ("Disc Golf", "TUESDAY", 2),
        ("Gaga Ball", "TUESDAY", 3),
        ("Dr. DNA", "WEDNESDAY", 1),
        ("Loon Lore", "WEDNESDAY", 2),
        ("Hemp Craft", "WEDNESDAY", 3),
        ("Trading Post", "THURSDAY", 1),
        ("Shower House", "THURSDAY", 2),
        ("Campsite Free Time", "FRIDAY", 1),
        ("Super Troop", "FRIDAY", 2),
        ("Reflection", "FRIDAY", 3),
    ]
    extra_deep_hits = [
        ("Monkey's Fist", "MONDAY", 1),
        ("Tie Dye", "MONDAY", 2),
        ("Woggle Neckerchief Slide", "MONDAY", 3),
        ("Ecosystem in a Jar", "WEDNESDAY", 1),
        ("Nature Salad", "WEDNESDAY", 2),
        ("Nature Bingo", "WEDNESDAY", 3),
    ]
    entries = [
        {
            "troop_name": "Scoring Troop",
            "activity_name": activity_name,
            "day": day,
            "slot": slot,
        }
        for activity_name, day, slot in base_entries + extra_deep_hits
    ]
    schedule_file.write_text(
        json.dumps({"troops": [troop], "entries": entries, "unscheduled": {}}),
        encoding="utf-8",
    )

    metrics = evaluate_week(str(troop_file), schedules_dir=tmp_path)

    assert metrics["score_components"]["preference_points"] == DEFAULT_WEIGHTS["preference_base_score"]
    assert "preference_bonuses" not in metrics["score_components"]
    assert metrics["raw_bonus_total"] == 0.0
    assert metrics["effective_bonus_total"] == 0.0
    assert metrics["final_score"] == round(metrics["core_goal_score"])
    assert metrics["final_score"] <= DEFAULT_WEIGHTS["max_score"]
