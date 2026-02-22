"""
Authoritative Top-5/Top-10 unscheduled source helpers.

All Top-5 miss reporting MUST come from schedule JSON `unscheduled.top5`.
"""

from typing import Any, Dict, List


THREE_HOUR_ACTIVITIES = {"Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}
HC_DG_ACTIVITIES = {"History Center", "Disc Golf"}
CANOE_FAMILY_ACTIVITIES = {
    "Troop Canoe",
    "Troop Kayak",
    "Canoe Snorkel",
    "Nature Canoe",
    "Float for Floats",
}


def _is_exempt_missing(
    activity_name: str,
    has_3hr_scheduled: bool,
    hc_dg_tuesday_full: bool,
    has_other_canoe_family_scheduled: bool,
) -> bool:
    if activity_name in THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
        return True
    if activity_name in HC_DG_ACTIVITIES and hc_dg_tuesday_full:
        return True
    if activity_name in CANOE_FAMILY_ACTIVITIES and has_other_canoe_family_scheduled:
        return True
    return False


def build_unscheduled_data(troops: List[Any], schedule: Any) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
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
        has_3hr_scheduled = any(name in THREE_HOUR_ACTIVITIES for name in scheduled_activity_names)

        missing_top5: List[Dict[str, Any]] = []
        for idx, pref_name in enumerate(troop.preferences[:5]):
            if pref_name not in scheduled_activity_names:
                has_other_canoe_family_scheduled = (
                    pref_name in CANOE_FAMILY_ACTIVITIES
                    and any(
                        name in CANOE_FAMILY_ACTIVITIES and name != pref_name
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
                        ),
                    }
                )

        missing_top10: List[Dict[str, Any]] = []
        for idx, pref_name in enumerate(troop.preferences[5:10]):
            if pref_name not in scheduled_activity_names:
                has_other_canoe_family_scheduled = (
                    pref_name in CANOE_FAMILY_ACTIVITIES
                    and any(
                        name in CANOE_FAMILY_ACTIVITIES and name != pref_name
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
