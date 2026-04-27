"""
Authoritative Top-5/Top-10 unscheduled source helpers.

All Top-5 miss reporting MUST come from schedule JSON `unscheduled.top5`.
"""

from typing import Any, Dict, List

from .sailing_half_fills import get_request_credit_fill_activities


HC_DG_ACTIVITIES = {"History Center", "Disc Golf"}


def _get_three_hour_activities() -> set[str]:
    from core.scheduler import config_loader

    return set(config_loader.get_three_hour_activities())


def _get_canoe_family_activities() -> set[str]:
    from core.scheduler import config_loader

    return set(config_loader.get_canoe_activities())


def _is_exempt_missing(
    activity_name: str,
    has_3hr_scheduled: bool,
    hc_dg_tuesday_full: bool,
    has_other_canoe_family_scheduled: bool,
    day_requested_names: set[str] | None = None,
    day_request_displaces: bool = False,
) -> bool:
    if activity_name in _get_three_hour_activities() and has_3hr_scheduled:
        return True
    if activity_name in HC_DG_ACTIVITIES and hc_dg_tuesday_full:
        return True
    if activity_name in _get_canoe_family_activities() and has_other_canoe_family_scheduled:
        return True
    if activity_name in (day_requested_names or set()):
        return True
    if day_request_displaces:
        return True
    return False


def _collect_day_request_context(troop: Any, troop_schedule: List[Any]) -> tuple[set[str], set[str]]:
    """Return authored and honored day-request activity names for exemption checks."""
    day_requested_names: set[str] = set()
    honored_day_request_names: set[str] = set()

    for day_name, activities in (getattr(troop, "day_requests", None) or {}).items():
        day_key = str(day_name).upper()
        for activity_name in activities:
            day_requested_names.add(activity_name)
            if any(
                entry.activity.name == activity_name
                and entry.time_slot.day.name.upper() == day_key
                for entry in troop_schedule
            ):
                honored_day_request_names.add(activity_name)

    return day_requested_names, honored_day_request_names


def _day_request_displaces_preference(
    troop: Any,
    missing_activity_name: str,
    missing_rank: int,
    honored_day_request_names: set[str],
) -> bool:
    """
    Return True when an honored day request plausibly displaced this miss.

    A blanket "any honored request exempts any miss" hides real Top-5 failures.
    This keeps BRAIN's MUST-HONOR displacement exemption, but only when the
    honored request is lower priority than the missed preference or not ranked.
    """
    for activity_name in honored_day_request_names:
        if activity_name == missing_activity_name:
            continue
        priority = troop.get_priority(activity_name) if hasattr(troop, "get_priority") else 999
        honored_rank = priority + 1 if priority != 999 else 999
        if honored_rank > missing_rank:
            return True
    return False


def build_unscheduled_data(
    troops: List[Any],
    schedule: Any,
    sailing_half_fills: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Build unscheduled payload in canonical JSON format:
    {
      "<troop>": {
        "top5": [{"name","rank","is_exempt"}, ...],
        "top10": [{"name","rank","is_exempt"}, ...]
      }
    }
    """
    unscheduled_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    tuesday_hc_dg_slots = set()
    for entry in schedule.entries:
        if entry.time_slot.day.name == "TUESDAY" and entry.activity.name in HC_DG_ACTIVITIES:
            tuesday_hc_dg_slots.add(entry.time_slot.slot_number)
    hc_dg_tuesday_full = tuesday_hc_dg_slots >= {1, 2, 3}

    for troop in troops:
        troop_schedule = schedule.get_troop_schedule(troop)
        scheduled_activity_names = {entry.activity.name for entry in troop_schedule}
        scheduled_activity_names |= get_request_credit_fill_activities(troop, sailing_half_fills)
        three_hour_activities = _get_three_hour_activities()
        canoe_family_activities = _get_canoe_family_activities()
        has_3hr_scheduled = any(name in three_hour_activities for name in scheduled_activity_names)
        day_requested_names, honored_day_request_names = _collect_day_request_context(troop, troop_schedule)

        missing_top5: List[Dict[str, Any]] = []
        for idx, pref_name in enumerate(troop.preferences[:5]):
            if pref_name not in scheduled_activity_names:
                has_other_canoe_family_scheduled = (
                    pref_name in canoe_family_activities
                    and any(
                        name in canoe_family_activities and name != pref_name
                        for name in scheduled_activity_names
                    )
                )
                missing_top5.append(
                    {
                        "name": pref_name,
                        "rank": idx + 1,
                        "is_exempt": _is_exempt_missing(
                            pref_name,
                            has_3hr_scheduled,
                            hc_dg_tuesday_full,
                            has_other_canoe_family_scheduled,
                            day_requested_names,
                            _day_request_displaces_preference(
                                troop,
                                pref_name,
                                idx + 1,
                                honored_day_request_names,
                            ),
                        ),
                    }
                )

        missing_top10: List[Dict[str, Any]] = []
        for idx, pref_name in enumerate(troop.preferences[5:10]):
            if pref_name not in scheduled_activity_names:
                has_other_canoe_family_scheduled = (
                    pref_name in canoe_family_activities
                    and any(
                        name in canoe_family_activities and name != pref_name
                        for name in scheduled_activity_names
                    )
                )
                missing_top10.append(
                    {
                        "name": pref_name,
                        "rank": idx + 6,
                        "is_exempt": _is_exempt_missing(
                            pref_name,
                            has_3hr_scheduled,
                            hc_dg_tuesday_full,
                            has_other_canoe_family_scheduled,
                            day_requested_names,
                            _day_request_displaces_preference(
                                troop,
                                pref_name,
                                idx + 6,
                                honored_day_request_names,
                            ),
                        ),
                    }
                )

        if missing_top5 or missing_top10:
            unscheduled_data[troop.name] = {"top5": missing_top5, "top10": missing_top10}

    return unscheduled_data


def summarize_non_exempt_misses(unscheduled: Dict[str, Any]) -> Dict[str, int]:
    """Return authoritative miss counts from unscheduled JSON only."""
    missing_top5 = 0
    missing_top10 = 0

    for troop_data in (unscheduled or {}).values():
        for item in troop_data.get("top5", []):
            if not item.get("is_exempt", False):
                missing_top5 += 1
                missing_top10 += 1
        for item in troop_data.get("top10", []):
            if not item.get("is_exempt", False):
                missing_top10 += 1

    return {"missing_top5": missing_top5, "missing_top10": missing_top10}
