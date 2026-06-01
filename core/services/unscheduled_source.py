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


def _get_two_hour_canoe_activities() -> set[str]:
    """Canoe-family activities whose duration is two hours (slots >= 2).

    BRAIN §2 scopes the canoe-duplication exemption to *two-hour* canoe
    activities, so 1-hour canoe activities (which fit a single slot and do not
    contend for a 2-slot block) must not qualify.
    """
    from core.activities import get_all_activities

    canoe_family = _get_canoe_family_activities()
    return {
        activity.name
        for activity in get_all_activities()
        if activity.name in canoe_family and activity.slots >= 2
    }


def _top_n_requester_names(troops: List[Any], activity_name: str, n: int) -> set[str]:
    """Names of the top-n troops (by preference rank) that requested an activity.

    Mirrors the scheduler's HC/DG placement, which grants each activity to its
    top-3 requesters via independent per-area loops (see
    ``_schedule_hc_dg_tuesday``). The saturation exemption must forgive exactly
    the misses that legitimately lost this ranked competition.
    """
    ranked: List[tuple[int, str]] = []
    for troop in troops:
        prefs = getattr(troop, "preferences", None) or []
        if activity_name in prefs:
            ranked.append((prefs.index(activity_name), troop.name))
    ranked.sort(key=lambda item: item[0])
    return {name for _, name in ranked[:n]}


def _is_exempt_missing(
    activity_name: str,
    has_3hr_scheduled: bool,
    hc_dg_saturation_exempt: bool,
    has_other_two_hour_canoe_scheduled: bool,
    day_requested_names: set[str] | None = None,
    day_request_displaces: bool = False,
) -> bool:
    if activity_name in _get_three_hour_activities() and has_3hr_scheduled:
        return True
    # HC/DG Tuesday saturation and two-hour canoe duplication are already
    # resolved per (troop, activity) by the caller, so they are passed in as
    # decided booleans rather than re-derived here.
    if hc_dg_saturation_exempt:
        return True
    if has_other_two_hour_canoe_scheduled:
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
    troop_name: str,
    missing_activity_name: str,
    day_request_displacements: set | None,
) -> bool:
    """Return True when a MUST-HONOR day request actually displaced this miss.

    BRAIN §2 Exemption 4(b) / §10.2 T6: a missed preference is exempt only when
    an honored day request "occupies a slot the Top 5 would have needed." That
    causality is knowable only inside the scheduler at displacement time, so the
    aggressive day-request seal records each displaced ``(troop_name,
    activity_name)`` pair as provenance (the scheduler's
    ``day_request_displacements`` set, persisted to schedule JSON).

    The previous rank heuristic was unsound in both directions: it exempted
    unrelated higher-ranked misses whenever any lower/unranked honored request
    existed (masking real non-exempt failures), and it failed to exempt a
    better-ranked Top-5 that a request legitimately displaced (aborting a valid
    run). Consulting the recorded provenance fixes both.
    """
    if not day_request_displacements:
        return False
    return (troop_name, missing_activity_name) in day_request_displacements


def build_unscheduled_data(
    troops: List[Any],
    schedule: Any,
    sailing_half_fills: Dict[str, Dict[str, Any]] | None = None,
    day_request_displacements: set | None = None,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Build unscheduled payload in canonical JSON format:
    {
      "<troop>": {
        "top5": [{"name","rank","is_exempt"}, ...],
        "top10": [{"name","rank","is_exempt"}, ...]
      }
    }

    ``day_request_displacements`` is the scheduler's set of
    ``(troop_name, activity_name)`` preferences displaced by an honored
    MUST-HONOR day request (see ``_day_request_displaces_preference``). It
    drives BRAIN §2 Exemption 4(b); when omitted, no displacement exemption is
    granted.
    """
    unscheduled_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    # HC and DG occupy separate exclusive Tuesday areas, each with three slots,
    # and the scheduler grants them via independent top-3 loops. Track each area
    # independently so a free DG slot never forgives an HC miss (or vice versa).
    hc_tuesday_slots: set[int] = set()
    dg_tuesday_slots: set[int] = set()
    for entry in schedule.entries:
        if entry.time_slot.day.name != "TUESDAY":
            continue
        if entry.activity.name == "History Center":
            hc_tuesday_slots.add(entry.time_slot.slot_number)
        elif entry.activity.name == "Disc Golf":
            dg_tuesday_slots.add(entry.time_slot.slot_number)
    hc_saturated = len(hc_tuesday_slots) >= 3
    dg_saturated = len(dg_tuesday_slots) >= 3
    hc_top3_requesters = _top_n_requester_names(troops, "History Center", 3)
    dg_top3_requesters = _top_n_requester_names(troops, "Disc Golf", 3)
    two_hour_canoe_activities = _get_two_hour_canoe_activities()

    for troop in troops:
        troop_schedule = schedule.get_troop_schedule(troop)
        scheduled_activity_names = {entry.activity.name for entry in troop_schedule}
        scheduled_activity_names |= get_request_credit_fill_activities(troop, sailing_half_fills)
        three_hour_activities = _get_three_hour_activities()
        has_3hr_scheduled = any(name in three_hour_activities for name in scheduled_activity_names)
        # honored names are no longer needed for the displacement exemption (now
        # provenance-driven); authored day-request names still drive Exemption 4(a).
        day_requested_names, _ = _collect_day_request_context(troop, troop_schedule)

        def _classify_miss(pref_name: str, rank: int) -> Dict[str, Any]:
            # Tuesday HC/DG saturation: exempt only when this troop lost the
            # ranked competition for its own area *and* that area is full.
            hc_dg_saturation_exempt = False
            if pref_name == "History Center":
                hc_dg_saturation_exempt = hc_saturated and troop.name not in hc_top3_requesters
            elif pref_name == "Disc Golf":
                hc_dg_saturation_exempt = dg_saturated and troop.name not in dg_top3_requesters

            # Two-hour canoe duplication: both the miss and an already-scheduled
            # activity must be two-hour canoe activities to qualify.
            has_other_two_hour_canoe_scheduled = (
                pref_name in two_hour_canoe_activities
                and any(
                    name in two_hour_canoe_activities and name != pref_name
                    for name in scheduled_activity_names
                )
            )

            return {
                "name": pref_name,
                "rank": rank,
                "is_exempt": _is_exempt_missing(
                    pref_name,
                    has_3hr_scheduled,
                    hc_dg_saturation_exempt,
                    has_other_two_hour_canoe_scheduled,
                    day_requested_names,
                    _day_request_displaces_preference(
                        troop.name,
                        pref_name,
                        day_request_displacements,
                    ),
                ),
            }

        missing_top5: List[Dict[str, Any]] = []
        for idx, pref_name in enumerate(troop.preferences[:5]):
            if pref_name not in scheduled_activity_names:
                missing_top5.append(_classify_miss(pref_name, idx + 1))

        missing_top10: List[Dict[str, Any]] = []
        for idx, pref_name in enumerate(troop.preferences[5:10]):
            if pref_name not in scheduled_activity_names:
                missing_top10.append(_classify_miss(pref_name, idx + 6))

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
