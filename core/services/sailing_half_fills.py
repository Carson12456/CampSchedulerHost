"""
Helpers for 30-minute Sailing half-slot fills.

These fills are sidecar metadata rather than full schedule entries because they
occupy half of a slot. The scheduler and GUI can both consume the same
deterministic assignment logic.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional


HALF_FILL_CANDIDATES: List[str] = ["Gaga Ball", "9 Square", "Trading Post"]
DEFAULT_HALF_FILL_PRIORITY = {name: idx for idx, name in enumerate(HALF_FILL_CANDIDATES)}
HALF_FILL_FALLBACK = "Campsite Free Time"


def make_sailing_fill_key(day_name: str, slot_num: int, troop_name: str) -> str:
    """Return a stable string key for a Sailing half-slot fill."""
    return f"{day_name}|{slot_num}|{troop_name}"


def get_request_credit_fill_activities(
    troop: Any,
    sailing_half_fills: Optional[Dict[str, Dict[str, Any]]],
) -> set[str]:
    """Activities that should count as fulfilled requests for this troop."""
    credited: set[str] = set()
    for fill in (sailing_half_fills or {}).values():
        if fill.get("troop_name") != troop.name:
            continue
        if fill.get("counts_as_request"):
            activity_name = fill.get("activity_name")
            if activity_name:
                credited.add(activity_name)
    return credited


def build_sailing_half_fills(troops: Iterable[Any], schedule: Any) -> Dict[str, Dict[str, Any]]:
    """
    Build deterministic 30-minute fills for Sailing split slots.

    Rules:
    - Candidate activities are Gaga Ball, 9 Square, Trading Post.
    - Requested candidates are preferred first by request rank.
    - Unrequested candidates fall back to Gaga Ball -> 9 Square -> Trading Post.
    - If all three are unavailable, fallback to Campsite Free Time.
    - A top-10 request may use the half-slot fill, but does NOT count as
      fulfilling that request; 11-20 does count.
    """
    troop_map = {troop.name: troop for troop in troops}
    troop_activity_names: Dict[str, set[str]] = {
        troop.name: {entry.activity.name for entry in schedule.get_troop_schedule(troop)}
        for troop in troop_map.values()
    }

    sailing_by_troop_day: Dict[tuple[str, str], List[int]] = defaultdict(list)
    blocked_full_slots: set[tuple[str, int, str]] = set()

    for entry in schedule.entries:
        day_name = entry.time_slot.day.name
        slot_num = entry.time_slot.slot_number
        blocked_full_slots.add((day_name, slot_num, entry.activity.name))
        if entry.activity.name == "Sailing":
            sailing_by_troop_day[(entry.troop.name, day_name)].append(slot_num)

    half_fill_occupancy: set[tuple[str, int, str, str]] = set()
    fills: Dict[str, Dict[str, Any]] = {}

    def _effective_priority(name: str, troop: Any) -> Optional[int]:
        """Return 0-indexed request rank (0-19) if requested, else None.

        Troop.get_priority returns 999 for unrequested activities; normalize
        that to None so the fill-selection logic can distinguish "requested"
        from "not requested".
        """
        raw = troop.get_priority(name)
        if raw is None or raw >= 20:
            return None
        return raw

    def choose_fill_activity(troop: Any, day_name: str, fill_slot: int, fill_half: str) -> tuple[str, Optional[int], bool]:
        candidate_order = sorted(
            HALF_FILL_CANDIDATES,
            key=lambda name: (
                0 if _effective_priority(name, troop) is not None else 1,
                _effective_priority(name, troop) if _effective_priority(name, troop) is not None else 999,
                DEFAULT_HALF_FILL_PRIORITY[name],
            ),
        )

        for activity_name in candidate_order:
            if activity_name in troop_activity_names.get(troop.name, set()):
                continue
            if (day_name, fill_slot, activity_name) in blocked_full_slots:
                continue
            if (day_name, fill_slot, activity_name, fill_half) in half_fill_occupancy:
                continue

            priority = _effective_priority(activity_name, troop)
            counts_as_request = priority is not None and 10 <= priority < 20
            return activity_name, priority, counts_as_request

        return HALF_FILL_FALLBACK, _effective_priority(HALF_FILL_FALLBACK, troop), False

    day_order = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    ordered_sessions = sorted(
        sailing_by_troop_day.items(),
        key=lambda item: (
            day_order.index(item[0][1]) if item[0][1] in day_order else 999,
            min(item[1]) if item[1] else 999,
            item[0][0],
        ),
    )

    for (troop_name, day_name), slot_numbers in ordered_sessions:
        troop = troop_map.get(troop_name)
        if troop is None or not slot_numbers:
            continue

        # Thursday only has 2 slots, so the single Sailing session there is
        # awarded (elsewhere) to the biggest troop and occupies BOTH slots as
        # one continuous 2-hour Sailing block — no 30-minute buffer / half-slot
        # fill. Skip it.
        if day_name == "THURSDAY":
            continue

        start_slot = min(slot_numbers)
        if start_slot not in (1, 2):
            continue

        fill_slot = 2
        fill_half = "bottom" if start_slot == 1 else "top"
        activity_name, priority, counts_as_request = choose_fill_activity(troop, day_name, fill_slot, fill_half)

        if activity_name in HALF_FILL_CANDIDATES:
            half_fill_occupancy.add((day_name, fill_slot, activity_name, fill_half))
        troop_activity_names.setdefault(troop_name, set()).add(activity_name)

        fill_key = make_sailing_fill_key(day_name, fill_slot, troop_name)
        fills[fill_key] = {
            "troop_name": troop_name,
            "day": day_name,
            "slot": fill_slot,
            "activity_name": activity_name,
            "fill_half": fill_half,
            "requested_rank": (priority + 1) if priority is not None else None,
            "counts_as_request": counts_as_request,
        }

    return fills
