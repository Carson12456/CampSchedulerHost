"""
Capacity and slot-availability rules sourced from SKULL-backed configuration.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Set

from core.scheduler import config_loader


class CapacityRules:
    """
    Business rules for capacity constraints and slot-time availability.

    This is the shared rule layer used by both the live Schedule model and the
    clean-architecture validator, so it intentionally relies on duck-typed
    access to activity/troop/entry fields instead of concrete classes.
    """

    BEACH_STAFF_ACTIVITIES = set(config_loader.get_beach_staff_activities())
    MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT = config_loader.get_constraints().get(
        "max_beach_staffed_activities",
        4,
    )
    CONCURRENT_ACTIVITIES = set(config_loader.get_concurrent_activities())
    TUESDAY_ONLY_ACTIVITIES = set(config_loader.get_tuesday_only_activities())
    AQUA_TRAMPOLINE_RULES = config_loader.get_aqua_trampoline_rules()
    WATER_POLO_RULES = config_loader.get_special_activity_config("Water Polo")

    def get_beach_staff_activities(self) -> Set[str]:
        """Get the set of activities that consume beach-staff capacity."""
        return self.BEACH_STAFF_ACTIVITIES.copy()

    def is_beach_staff_activity(self, activity_name: str) -> bool:
        """Check if an activity requires beach-staff capacity."""
        return activity_name in self.BEACH_STAFF_ACTIVITIES

    def get_max_beach_staff_activities_per_slot(self) -> int:
        """Get the maximum number of beach-staffed activities allowed per slot."""
        return self.MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT

    def can_add_beach_staff_activity(self, current_count: int) -> bool:
        """Check if another beach-staffed activity can be added to a slot."""
        return current_count < self.MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT

    def get_max_concurrent_count(
        self,
        activity_name: str,
        time_slot: Optional[Any] = None,
        requesting_troop: Optional[Any] = None,
    ) -> Optional[int]:
        """
        Get the configured occupancy limit for an activity in a slot.

        `None` means the activity is globally concurrent in that slot.
        """
        if activity_name in self.CONCURRENT_ACTIVITIES:
            return None

        if activity_name == "Water Polo":
            return int(self.WATER_POLO_RULES.get("max_troops_per_slot", 2))

        if activity_name == "Aqua Trampoline":
            max_small = int(self.AQUA_TRAMPOLINE_RULES.get("max_small_troops", 2))
            size_limit = int(self.AQUA_TRAMPOLINE_RULES.get("small_troop_size", 16))
            return 1 if self._troop_size(requesting_troop) > size_limit else max_small

        if activity_name == "Sailing" and time_slot is not None:
            day_name = self._day_name(time_slot.day)
            if day_name != "THURSDAY" and int(time_slot.slot_number) == 2:
                return 2
            return 1

        return 1

    def can_place_activity(
        self,
        time_slot: Any,
        activity: Any,
        requesting_troop: Optional[Any],
        existing_entries: Iterable[Any],
    ) -> bool:
        """
        Determine whether an activity can be placed in the given slot.

        This consolidates the live schedule-availability checks so the repo
        does not maintain multiple partially-overlapping implementations.
        """
        activity_name = activity.name
        slot_entries = [entry for entry in existing_entries if self._same_slot(entry.time_slot, time_slot)]

        if activity_name in self.TUESDAY_ONLY_ACTIVITIES and self._day_name(time_slot.day) != "TUESDAY":
            return False

        if activity_name == "Sailing":
            if not self._can_place_sailing(time_slot, existing_entries):
                return False

        elif activity_name == "Aqua Trampoline":
            if not self._can_place_aqua_trampoline(slot_entries, requesting_troop):
                return False

        elif activity_name == "Water Polo":
            same_activity_count = sum(1 for entry in slot_entries if entry.activity.name == activity_name)
            if same_activity_count >= self.get_max_concurrent_count(activity_name):
                return False

        for entry in slot_entries:
            entry_activity_name = entry.activity.name

            if entry_activity_name == activity_name:
                if activity_name in self.CONCURRENT_ACTIVITIES:
                    continue
                if activity_name in {"Aqua Trampoline", "Water Polo", "Sailing"}:
                    continue
                return False

            if self._shares_exclusive_area(activity_name, entry_activity_name):
                return False

            if activity_name in getattr(entry.activity, "conflicts_with", []):
                return False
            if entry_activity_name in getattr(activity, "conflicts_with", []):
                return False

        if self.is_beach_staff_activity(activity_name):
            existing_staffed_count = sum(
                1 for entry in slot_entries if self.is_beach_staff_activity(entry.activity.name)
            )
            allowed_limit = self.MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT
            if activity_name == "Aqua Trampoline" and self._is_top5_request(requesting_troop, activity_name):
                allowed_limit += 1
            if existing_staffed_count >= allowed_limit:
                return False

        return True

    def _can_place_aqua_trampoline(self, slot_entries: list[Any], requesting_troop: Optional[Any]) -> bool:
        aqua_entries = [entry for entry in slot_entries if entry.activity.name == "Aqua Trampoline"]
        if not aqua_entries:
            return True

        max_small_troops = int(self.AQUA_TRAMPOLINE_RULES.get("max_small_troops", 2))
        size_limit = int(self.AQUA_TRAMPOLINE_RULES.get("small_troop_size", 16))
        requesting_size = self._troop_size(requesting_troop)

        if requesting_size > size_limit:
            return False

        if any(self._troop_size(entry.troop) > size_limit for entry in aqua_entries):
            return False

        return len(aqua_entries) < max_small_troops

    def _can_place_sailing(self, time_slot: Any, existing_entries: Iterable[Any]) -> bool:
        slot_number = int(time_slot.slot_number)
        if slot_number not in (1, 2):
            return False

        max_slot = self._max_slot_for_day(time_slot.day)
        occupied_slot_numbers = [slot_number]
        if slot_number < max_slot:
            occupied_slot_numbers.append(slot_number + 1)

        sailing_starts = [
            entry
            for entry in existing_entries
            if entry.activity.name == "Sailing"
            and self._day_name(entry.time_slot.day) == self._day_name(time_slot.day)
            and self._is_sailing_start(entry, existing_entries)
        ]

        if any(int(entry.time_slot.slot_number) == slot_number for entry in sailing_starts):
            return False

        day_name = self._day_name(time_slot.day)
        for occupied_slot in occupied_slot_numbers:
            current_occupancy = sum(
                1
                for start in sailing_starts
                if occupied_slot in self._occupied_sailing_slots(start.time_slot)
            )
            allowed = 2 if day_name != "THURSDAY" and occupied_slot == 2 else 1
            if current_occupancy >= allowed:
                return False

        return True

    def _is_sailing_start(self, entry: Any, existing_entries: Iterable[Any]) -> bool:
        prev_slot_num = int(entry.time_slot.slot_number) - 1
        if prev_slot_num < 1:
            return True

        for other in existing_entries:
            if other.activity.name != "Sailing":
                continue
            if not self._same_troop(other.troop, entry.troop):
                continue
            if self._day_name(other.time_slot.day) != self._day_name(entry.time_slot.day):
                continue
            if int(other.time_slot.slot_number) == prev_slot_num:
                return False

        return True

    def _occupied_sailing_slots(self, time_slot: Any) -> set[int]:
        max_slot = self._max_slot_for_day(time_slot.day)
        occupied = {int(time_slot.slot_number)}
        if int(time_slot.slot_number) < max_slot:
            occupied.add(int(time_slot.slot_number) + 1)
        return occupied

    def _shares_exclusive_area(self, activity_name: str, other_activity_name: str) -> bool:
        activity_area = config_loader.get_area_for_activity(activity_name)
        other_area = config_loader.get_area_for_activity(other_activity_name)
        return activity_area is not None and activity_area == other_area

    def _same_slot(self, slot_a: Any, slot_b: Any) -> bool:
        return (
            self._day_name(slot_a.day) == self._day_name(slot_b.day)
            and int(slot_a.slot_number) == int(slot_b.slot_number)
        )

    def _same_troop(self, troop_a: Any, troop_b: Any) -> bool:
        if troop_a is None or troop_b is None:
            return troop_a is troop_b
        return getattr(troop_a, "name", troop_a) == getattr(troop_b, "name", troop_b)

    def _troop_size(self, troop: Optional[Any]) -> int:
        if troop is None:
            return 0
        size = getattr(troop, "size", None)
        if size is not None:
            return int(size)
        return int(getattr(troop, "scouts", 0)) + int(getattr(troop, "adults", 0))

    def _is_top5_request(self, troop: Optional[Any], activity_name: str) -> bool:
        if troop is None:
            return False
        if hasattr(troop, "get_priority"):
            return int(troop.get_priority(activity_name)) < 5
        preferences = list(getattr(troop, "preferences", []) or [])
        return activity_name in preferences[:5]

    def _max_slot_for_day(self, day: Any) -> int:
        return 2 if self._day_name(day) == "THURSDAY" else 3

    def _day_name(self, day: Any) -> str:
        if hasattr(day, "name"):
            return str(day.name).upper()
        return str(day).upper()
