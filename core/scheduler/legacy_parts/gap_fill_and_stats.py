"""Legacy ConstrainedScheduler methods (split mixin part)."""

from __future__ import annotations

import math
import os
import random
import typing
import json
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

from ...activities import get_activity_by_name, get_all_activities
from ...models import Activity, Day, ScheduleEntry, TimeSlot, Troop, Zone, generate_time_slots
from .. import config_loader
from ..constants import SchedulerConstants
from ..validators import CLUSTER_AREAS, would_create_excess_day_for_entries

EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()

class LegacyPart05Mixin:
    """Scheduler legacy methods part 05."""

    def _debug_log(self, hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None:
        # #region agent log
        try:
            payload = {
                "sessionId": "574b8a",
                "runId": getattr(self, "_debug_run_id", "pre-fix"),
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000),
            }
            with open("debug-574b8a.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, separators=(",", ":")) + "\n")
        except Exception:
            pass
        # #endregion

    def _check_consecutive_slots(self, troop: Troop, activity: Activity, 
                                  start_index: int, slots_needed: int) -> bool:
        """Check if consecutive slots are available."""
        if start_index + slots_needed > len(self.time_slots):
            return False

        start_slot = self.time_slots[start_index]

        # Calculate the maximum slot number for this day
        max_slot = 2 if start_slot.day == Day.THURSDAY else 3

        # Check if the activity would extend beyond the day's available slots
        end_slot_number = start_slot.slot_number + slots_needed - 1
        if end_slot_number > max_slot:
            return False  # Would extend beyond available slots for this day

        for offset in range(slots_needed):
            next_slot = self.time_slots[start_index + offset]
            if next_slot.day != start_slot.day:
                return False
            if not self.schedule.is_troop_free(next_slot, troop):
                return False
            if activity.name not in self.CONCURRENT_ACTIVITIES:
                if not self.schedule.is_activity_available(next_slot, activity, troop):
                    return False
        return True


    def _troop_has_activity(self, troop: Troop, activity: Activity) -> bool:
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.activity.name == activity.name:
                return True
        return False


    def _has_beach_today(self, troop: Troop, day: Day) -> bool:
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.time_slot.day == day and entry.activity.name in self.BEACH_ACTIVITIES:
                return True
        return False


    def _has_accuracy_today(self, troop: Troop, day: Day) -> bool:
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.time_slot.day == day and entry.activity.name in self.ACCURACY_ACTIVITIES:
                return True
        return False


    def _count_top5_today(self, troop: Troop, day: Day) -> int:
        count = 0
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.time_slot.day == day:
                if troop.get_priority(entry.activity.name) < 5:
                    count += 1
        return count


    def _count_top10_today(self, troop: Troop, day: Day) -> int:
        count = 0
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.time_slot.day == day:
                priority = troop.get_priority(entry.activity.name)
                if 5 <= priority < 10:
                    count += 1
        return count

    def _get_activity_family_name(self, activity_name: str) -> Optional[str]:
        """Return the durable family-policy key for an activity, if any."""
        if activity_name in {"Delta", "Sailing"}:
            return "Delta/Sailing"
        if activity_name == "Super Troop":
            return "Super Troop"
        if activity_name == "Climbing Tower" or activity_name in self.TOWER_ODS_ACTIVITIES:
            return "Tower/ODS"
        if activity_name in {"Troop Rifle", "Troop Shotgun"}:
            return "Rifle"
        return None

    def _set_family_day_policy(
        self,
        family_name: str,
        *,
        policy_type: str,
        allowed_days: Optional[List[Day]] = None,
        preferred_days: Optional[List[Day]] = None,
        target_days: Optional[List[Day]] = None,
        protect_from_phase_d: bool = False,
        shared_staff_group: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Persist a normalized family-policy object for the current run."""
        weekday_order = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

        def _normalize(days: Optional[List[Day]]) -> List[Day]:
            if not days:
                return []
            seen = set()
            ordered = []
            for day in days:
                if day in weekday_order and day not in seen:
                    ordered.append(day)
                    seen.add(day)
            return ordered

        policy = {
            "family_name": family_name,
            "policy_type": policy_type,
            "allowed_days": _normalize(allowed_days) or list(weekday_order),
            "preferred_days": _normalize(preferred_days),
            "target_days": _normalize(target_days),
            "protect_from_phase_d": protect_from_phase_d,
            "shared_staff_group": shared_staff_group,
            "metadata": metadata or {},
        }
        self.family_day_policies[family_name] = policy
        return policy

    def _get_family_day_policy(
        self,
        family_name: Optional[str] = None,
        *,
        activity_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Fetch a stored family day policy by family or activity."""
        if family_name is None and activity_name is not None:
            family_name = self._get_activity_family_name(activity_name)
        if not family_name:
            return None
        return (getattr(self, "family_day_policies", {}) or {}).get(family_name)

    def _get_activity_policy_days(self, activity_name: str) -> tuple[list[Day], list[Day], list[Day]]:
        """Return (preferred_days, target_days, allowed_days) for an activity."""
        policy = self._get_family_day_policy(activity_name=activity_name)
        if not policy:
            return [], [], []
        preferred = list(policy.get("preferred_days") or [])
        target = list(policy.get("target_days") or preferred)
        allowed = list(policy.get("allowed_days") or [])
        if not allowed:
            allowed = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
        return preferred, target, allowed

    def _family_policy_allows_day(self, activity_name: str, day: Day, *, strict: bool = False) -> bool:
        """Check whether the family policy allows using ``day`` for ``activity_name``."""
        preferred, target, allowed = self._get_activity_policy_days(activity_name)
        if not allowed and not target and not preferred:
            return True
        if strict:
            active_days = target or preferred or allowed
            return day in active_days
        return day in allowed

    def _count_family_policy_drift(self) -> int:
        """Count scheduled entries that drift outside strict family target days."""
        drift = 0
        for entry in self.schedule.entries:
            family = self._get_activity_family_name(entry.activity.name)
            if not family:
                continue
            policy = self._get_family_day_policy(family)
            if not policy:
                continue
            target_days = policy.get("target_days") or policy.get("preferred_days") or []
            if target_days and entry.time_slot.day not in target_days:
                drift += 1
        return drift


    def _get_cluster_areas_map(self, include_commissioner: bool = True) -> dict:
        """
        Return clustered area -> activity mapping used by placement/swap logic.
        Uses configured exclusive areas and optional commissioner activities.
        """
        cluster_areas = {}
        for area_name, activities in EXCLUSIVE_AREAS.items():
            if activities:
                cluster_areas[area_name] = set(activities)

        if include_commissioner:
            cluster_areas["Commissioner"] = {"Super Troop", "Delta"}

        return cluster_areas

    def _get_multi_slot_activity_names(self) -> set[str]:
        """Return activities that should be protected as multi-slot/rock placements."""
        names = set(getattr(self, "THREE_HOUR_ACTIVITIES", set()) or set())
        for activity in getattr(self, "activities", []) or []:
            if getattr(activity, "slots", 1) > 1:
                names.add(activity.name)
        # Climbing Tower is a setup-heavy rock in legacy Top-5 swap protection.
        if any(getattr(activity, "name", None) == "Climbing Tower" for activity in getattr(self, "activities", []) or []):
            names.add("Climbing Tower")
        return names

    def _get_protected_activity_names(self, extra=()) -> set[str]:
        """Return activities that preference recovery should not displace."""
        protected = set(getattr(self, "NON_DISPLACEABLE_ACTIVITIES", set()) or set())
        protected.update(getattr(self, "MANDATORY_ANCHORS", set()) or set())
        protected.update(extra or ())
        return protected

    def _get_swappable_fill_names(self) -> set[str]:
        """Return low-risk filler activities that can be swapped during cleanup."""
        configured = set(getattr(self, "SWAPPABLE_FILL_ACTIVITIES", set()) or set())
        if configured:
            return configured
        return {"Gaga Ball", "9 Square", "Campsite Free Time"}

    def _get_authoritative_gap_area_map(self) -> dict:
        """Return the exact area set used by official gap scoring."""
        area_priority = (
            config_loader.get_constraints()
            .get("optimization", {})
            .get("area_clustering_priority", [])
        )
        cluster_area_names = [a for a in area_priority if a in EXCLUSIVE_AREAS]
        cluster_area_names.extend(
            a for a, acts in EXCLUSIVE_AREAS.items()
            if len(acts) >= 3 and a not in cluster_area_names
        )
        return {
            area_name: set(EXCLUSIVE_AREAS.get(area_name, []))
            for area_name in cluster_area_names
        }

    def _get_cluster_area_name_for_activity(
        self,
        activity_name: str,
        include_commissioner: bool = True,
        authoritative_gap: bool = False,
    ) -> Optional[str]:
        """Return the cluster-area name for an activity, if any."""
        area_map = (
            self._get_authoritative_gap_area_map()
            if authoritative_gap
            else self._get_cluster_areas_map(include_commissioner=include_commissioner)
        )
        for area_name, activities in area_map.items():
            if activity_name in activities:
                return area_name
        return None

    def _phase_prefers_existing_cluster_days(self) -> bool:
        """Late phases should consolidate onto existing days over ownership heuristics."""
        phase = getattr(self, "current_pipeline_phase", "init").strip().lower()
        return phase in {"remaining", "polish", "final"}

    def _day_clustering_sort_key(self, day: Day) -> int:
        """Stable weekday ordering with Friday last."""
        order = {
            Day.MONDAY: 0,
            Day.TUESDAY: 1,
            Day.WEDNESDAY: 2,
            Day.THURSDAY: 3,
            Day.FRIDAY: 4,
        }
        return order.get(day, 99)


    def _get_activity_commissioner_group(self, activity_name: str):
        """Return commissioner-managed activity group key and member activities."""
        if activity_name == "Delta":
            return "Delta", {"Delta"}
        if activity_name == "Super Troop":
            return "Super Troop", {"Super Troop"}
        if activity_name in {"Troop Rifle", "Troop Shotgun"}:
            return "Rifle", {"Troop Rifle", "Troop Shotgun"}
        if activity_name == "Archery":
            return "Archery", {"Archery"}
        if activity_name == "Sailing":
            return "Sailing", {"Sailing"}
        if activity_name == "Climbing Tower" or activity_name in self.TOWER_ODS_ACTIVITIES:
            return "TowerODS", set(EXCLUSIVE_AREAS.get("Tower", []) + EXCLUSIVE_AREAS.get("Outdoor Skills", []))
        return None, set()


    def _get_activity_commissioner_day_fixed(self, troop: Troop, activity_name: str):
        """
        Return configured commissioner day for activity/troop from static mappings.
        """
        commissioner = self.troop_commissioner.get(troop.name) or getattr(troop, "commissioner", None)
        if not commissioner:
            return None

        if activity_name == "Delta":
            return self.COMMISSIONER_DELTA_DAYS.get(commissioner)
        if activity_name == "Super Troop":
            return self.COMMISSIONER_SUPER_TROOP_DAYS.get(commissioner)
        if activity_name in {"Troop Rifle", "Troop Shotgun"}:
            return self.COMMISSIONER_RIFLE_DAYS.get(commissioner)
        if activity_name == "Archery":
            return self.COMMISSIONER_ARCHERY_DAYS.get(commissioner)
        if activity_name == "Sailing":
            return self.COMMISSIONER_SAILING_DAYS.get(commissioner)
        if activity_name == "Climbing Tower" or activity_name in self.TOWER_ODS_ACTIVITIES:
            return self.COMMISSIONER_TOWER_ODS_DAYS.get(commissioner)
        return None


    def _get_commissioner_day_map_for_activity(self, activity_name: str):
        """Return commissioner->day mapping for commissioner-managed activities."""
        if activity_name == "Delta":
            return self.COMMISSIONER_DELTA_DAYS
        if activity_name == "Super Troop":
            return self.COMMISSIONER_SUPER_TROOP_DAYS
        if activity_name in {"Troop Rifle", "Troop Shotgun"}:
            return self.COMMISSIONER_RIFLE_DAYS
        if activity_name == "Archery":
            return self.COMMISSIONER_ARCHERY_DAYS
        if activity_name == "Sailing":
            return self.COMMISSIONER_SAILING_DAYS
        if activity_name == "Climbing Tower" or activity_name in self.TOWER_ODS_ACTIVITIES:
            return self.COMMISSIONER_TOWER_ODS_DAYS
        return {}


    def _get_commissioner_day_tiers(self, troop: Troop, activity_name: str):
        """
        Build commissioner day tiers for placement priority.

        Priority contract:
        1) Assigned commissioner day (when still actively honoring ownership)
        2) Overflow/fill days (prefer regular weekdays, Friday last)
        3) Other commissioners' assigned days
        """
        day_order = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
        commissioner = self.troop_commissioner.get(troop.name) or getattr(troop, "commissioner", None)
        day_map = self._get_commissioner_day_map_for_activity(activity_name) or {}
        if not commissioner or not day_map:
            return None, [], []

        pref_rank = troop.get_priority(activity_name)
        assigned_day = day_map.get(commissioner)
        softened_fill_days = []

        # Thursday only has two visible slots, so treat it as an open/fill day
        # unless we're still in the early anchor phases for a high-value request.
        if assigned_day == Day.THURSDAY and (
            self._phase_prefers_existing_cluster_days()
            or pref_rank is None
            or pref_rank >= 5
        ):
            softened_fill_days.append(assigned_day)
            assigned_day = None

        primary_days = []
        for day in day_order:
            if any(mapped_day == day for mapped_day in day_map.values()) and day not in primary_days:
                primary_days.append(day)

        # Friday is the worst generic spill day for clustering, so keep it last.
        fill_days = []
        fill_order = softened_fill_days + [d for d in day_order if d not in softened_fill_days]
        if activity_name == "Super Troop":
            for day in fill_order:
                if (
                    day != Day.FRIDAY
                    and (day not in primary_days or day in softened_fill_days)
                    and day != assigned_day
                ):
                    fill_days.append(day)
            if Day.FRIDAY not in fill_days:
                fill_days.append(Day.FRIDAY)
        else:
            for day in fill_order:
                if (day not in primary_days or day in softened_fill_days) and day != assigned_day:
                    fill_days.append(day)
            if Day.FRIDAY in fill_days:
                fill_days = [d for d in fill_days if d != Day.FRIDAY] + [Day.FRIDAY]

        other_comm_days = [
            day for day in primary_days
            if day not in {assigned_day, Day.FRIDAY} and day not in softened_fill_days
        ]
        return assigned_day, fill_days, other_comm_days


    def _reorder_days_with_commissioner_priority(self, candidate_days: list, troop: Troop, activity_name: str) -> list:
        """Reorder day list to match commissioner priority tiers."""
        candidates = []
        seen = set()
        for d in candidate_days:
            if d not in seen:
                candidates.append(d)
                seen.add(d)

        policy = self._get_family_day_policy(activity_name=activity_name)
        if policy:
            preferred_days, target_days, allowed_days = self._get_activity_policy_days(activity_name)

            day_counts = defaultdict(int)
            for e in self.schedule.entries:
                if e.troop == troop:
                    day_counts[e.time_slot.day] += 1

            area_day_counts = defaultdict(int)
            area_name = self._get_cluster_area_name_for_activity(
                activity_name,
                include_commissioner=False,
            )
            if area_name:
                area_activities = self._get_cluster_areas_map(include_commissioner=False).get(area_name, set())
                for e in self.schedule.entries:
                    if e.activity.name in area_activities:
                        area_day_counts[e.time_slot.day] += 1

            strict_phase = getattr(self, "current_pipeline_phase", "init").strip().lower() in {
                "remaining",
                "polish",
                "final",
            }

            def policy_bucket(day: Day) -> tuple[int, int]:
                if day in preferred_days:
                    return (0, preferred_days.index(day))
                if day in target_days:
                    return (1, target_days.index(day))
                if day in allowed_days:
                    return (2, allowed_days.index(day))
                # In late phases, keep disallowed days last so drift does not grow.
                return (4 if strict_phase else 3, self._day_clustering_sort_key(day))

            candidates.sort(
                key=lambda d: (
                    policy_bucket(d),
                    -area_day_counts[d],
                    -day_counts[d],
                    self._day_clustering_sort_key(d),
                )
            )

            for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
                if day not in seen:
                    candidates.append(day)
                    seen.add(day)
            return candidates

        if self._phase_prefers_existing_cluster_days():
            day_counts = defaultdict(int)
            for e in self.schedule.entries:
                if e.troop == troop:
                    day_counts[e.time_slot.day] += 1

            area_day_counts = defaultdict(int)
            area_name = self._get_cluster_area_name_for_activity(
                activity_name,
                include_commissioner=False,
            )
            if area_name:
                area_activities = self._get_cluster_areas_map(include_commissioner=False).get(area_name, set())
                for e in self.schedule.entries:
                    if e.activity.name in area_activities:
                        area_day_counts[e.time_slot.day] += 1

            assigned_day, fill_days, other_comm_days = self._get_commissioner_day_tiers(troop, activity_name)

            def commissioner_tie_break(day: Day) -> int:
                if assigned_day and day == assigned_day:
                    return 0
                if day in fill_days:
                    return 1
                if day in other_comm_days:
                    return 2
                return 3

            candidates.sort(
                key=lambda d: (
                    -area_day_counts[d],
                    -day_counts[d],
                    commissioner_tie_break(d),
                    self._day_clustering_sort_key(d),
                )
            )

            for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
                if day not in seen:
                    candidates.append(day)
                    seen.add(day)
            return candidates

        assigned_day, fill_days, other_comm_days = self._get_commissioner_day_tiers(troop, activity_name)
        if not assigned_day and not fill_days and not other_comm_days:
            return candidates

        ordered = []
        seen = set()
        tier_days = []
        if assigned_day:
            tier_days.append(assigned_day)
        tier_days.extend(fill_days)
        tier_days.extend(other_comm_days)

        for day in tier_days:
            if day in candidate_days and day not in seen:
                ordered.append(day)
                seen.add(day)

        for day in candidate_days:
            if day not in seen:
                ordered.append(day)
                seen.add(day)

        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]:
            if day not in seen:
                ordered.append(day)
                seen.add(day)
        return ordered


    def _get_commissioner_ownership_day(self, troop: Troop, activity_name: str):
        """
        Infer best ownership day by clustering same commissioner/group activities.
        """
        commissioner = self.troop_commissioner.get(troop.name) or getattr(troop, "commissioner", None)
        if not commissioner:
            return None, 0

        _, group_activities = self._get_activity_commissioner_group(activity_name)
        if not group_activities:
            return None, 0

        day_counts = defaultdict(int)
        for entry in self.schedule.entries:
            entry_comm = self.troop_commissioner.get(entry.troop.name) or getattr(entry.troop, "commissioner", None)
            if entry_comm != commissioner:
                continue
            if entry.activity.name in group_activities:
                day_counts[entry.time_slot.day] += 1

        if day_counts:
            best_day = sorted(day_counts.items(), key=lambda x: (-x[1], x[0].value))[0]
            return best_day[0], best_day[1]

        # No established ownership cluster yet: prefer early-week anchor.
        return Day.MONDAY, 0


    def _get_activity_commissioner_day(self, troop: Troop, activity_name: str):
        """
        Mode-aware commissioner clustering day selector.
        Modes:
        - strong: static commissioner map
        - ownership: dynamic same-commissioner ownership day
        - mixed: static map with ownership override when cluster is established
        """
        mode = getattr(self, "commissioner_clustering_mode", "mixed")
        fixed_day = self._get_activity_commissioner_day_fixed(troop, activity_name)
        pref_rank = troop.get_priority(activity_name)
        current_phase = getattr(self, "current_pipeline_phase", "init").strip().lower()
        early_phase = current_phase in {"foundation", "core"}
        late_phase = self._phase_prefers_existing_cluster_days()
        if mode == "strong":
            return fixed_day

        ownership_day, ownership_count = self._get_commissioner_ownership_day(troop, activity_name)
        if mode == "ownership":
            return ownership_day

        # Mixed: late fill/cleanup should consolidate onto existing cluster days
        # instead of reopening commissioner ownership days.
        if late_phase:
            return None

        # Thursday ownership is too rigid for low-priority or filler-style placements.
        if fixed_day == Day.THURSDAY and (pref_rank is None or pref_rank >= 5):
            return None

        # Early anchor phases should still respect commissioner-day ownership.
        if early_phase:
            if not fixed_day:
                return ownership_day
            if ownership_day and ownership_day != fixed_day:
                if (
                    activity_name in self.TOWER_ODS_ACTIVITIES
                    or activity_name in {"Climbing Tower", "Archery", "Troop Rifle", "Troop Shotgun"}
                ) and ownership_count >= 2:
                    return ownership_day
            return fixed_day

        # Mixed outside anchor phases: Top 5 stays commissioner-led. Lower priorities can float.
        if pref_rank is not None and pref_rank >= 5:
            return None

        if not fixed_day:
            return ownership_day

        if ownership_day and ownership_day != fixed_day:
            if (
                activity_name in self.TOWER_ODS_ACTIVITIES
                or activity_name in {"Climbing Tower", "Archery", "Troop Rifle", "Troop Shotgun"}
            ) and ownership_count >= 2:
                return ownership_day
        return fixed_day


    def _update_progress(self, troop: Troop, activity_name: str):
        priority = troop.get_priority(activity_name)
        if priority < 5:
            self.troop_top5_scheduled[troop.name] += 1
        elif priority < 10:
            self.troop_top10_scheduled[troop.name] += 1


    def _get_cluster_ordered_slots(self, troop: Troop, activity: Activity) -> list:
        """
        Return time slots ordered by clustering preference.

        Priority:
        1. Days where troop already has activities (cluster days)
        2. Adjacent slots on those days (better consecutiveness)
        3. Consider staff load to avoid overloading slots
        4. Fall back to regular slot order
        """
        import math

        # Get troop's current schedule
        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

        # Find days with activity counts
        day_counts = {}
        day_slots = {}  # Track which slots are used on each day
        for e in troop_entries:
            day = e.time_slot.day
            if day not in day_counts:
                day_counts[day] = 0
                day_slots[day] = set()
            day_counts[day] += 1
            day_slots[day].add(e.time_slot.slot_number)

        # Calculate staff load per slot (for balancing)
        slot_loads = {}
        for slot in self.time_slots:
            entries_in_slot = [e for e in self.schedule.entries if e.time_slot == slot]
            # Use correct staff counting matching GUI
            total_staff = sum(self._get_activity_staff_count(e.activity.name) for e in entries_in_slot)
            slot_loads[slot] = total_staff

        # ============================================================
        # PRE-CALCULATE STAFF AREA DEMAND AND PRIMARY DAYS
        # This determines how many days to use BEFORE we start scheduling
        # ============================================================

        # Cluster areas: use full configured set so clustering covers all clustered activities.
        STAFF_AREAS = self._get_cluster_areas_map(include_commissioner=True)

        # Find which staff area this activity belongs to
        activity_staff_area = None
        for area_name, area_activities in STAFF_AREAS.items():
            if activity.name in area_activities:
                activity_staff_area = area_name
                break

        # Calculate TOTAL DEMAND for this area across ALL troops (not just current)
        area_primary_days = None

        # === NEW: STRICT COMMISSIONER-BASED CLUSTERING ===
        # If this is a commissioner-managed area, FORCE the primary day to be the commissioner's day
        # This overrides the "existing demand" logic which is empty at start of scheduling

        # 1. Determine troop's commissioner
        comm = self.troop_commissioner.get(troop.name)
        preferred_policy_days, target_policy_days, allowed_policy_days = self._get_activity_policy_days(
            activity.name
        )

        # 2. Check if this activity belongs to a commissioner-managed area
        forced_day = None

        # Durable family policies take precedence over inferred late-phase drift.
        if target_policy_days:
            area_primary_days = set(target_policy_days)
            forced_day = target_policy_days[0]
        else:
            # Commissioner-day assignment is mode-aware (strong / ownership / mixed).
            forced_day = self._get_activity_commissioner_day(troop, activity.name)

        if forced_day and area_primary_days is None:
            # STRICT ENFORCEMENT: The primary day is THE day.
            area_primary_days = {forced_day}
            # For Rifle/Shotgun, if we have both, we need a second day.
            # But the constraint says "Max 1 accuracy per day".
            # The simple logic: Stick to the main day. If full, adjacent days will naturally be picked by adjacency score.

        elif activity_staff_area and area_primary_days is None:
            area_activities_set = STAFF_AREAS[activity_staff_area]

            # Count total demand from all troops preferences
            # SPECIAL: For Rifle area, troops with BOTH Rifle and Shotgun need 2 days (can't be same day)
            total_demand = 0
            if activity_staff_area == 'Rifle Range':
                for t in self.troops:
                    has_rifle = any(p == 'Troop Rifle' for p in t.preferences[:15])
                    has_shotgun = any(p == 'Troop Shotgun' for p in t.preferences[:15])
                    if has_rifle:
                        total_demand += 1
                    if has_shotgun:
                        total_demand += 1
                    # If they have both, they MUST be on different days - add penalty to min_days
            else:
                for t in self.troops:
                    for pref in t.preferences[:15]:  # Top 15 preferences
                        if pref in area_activities_set:
                            total_demand += 1

            # Align primary-day budgeting with the official excess-day formula.
            # Let constraints force extra spread only when they truly have to.
            min_days_needed = max(1, math.ceil(total_demand / 3))

            # Determine PRIMARY days based on what's already scheduled + preferred order
            PREFERRED_DAY_ORDER = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

            # Get current distribution for this area
            area_day_distribution = {}
            for e in self.schedule.entries:
                if e.activity.name in area_activities_set:
                    if e.time_slot.day not in area_day_distribution:
                        area_day_distribution[e.time_slot.day] = 0
                    area_day_distribution[e.time_slot.day] += 1

            # Primary days = top N days by current count, filled with preferred order
            if area_day_distribution:
                sorted_days = sorted(area_day_distribution.keys(), 
                                    key=lambda d: area_day_distribution[d], reverse=True)
                area_primary_days = set(sorted_days[:min_days_needed])
                # Fill remaining from preferred order
                for pd in PREFERRED_DAY_ORDER:
                    if len(area_primary_days) >= min_days_needed:
                        break
                    area_primary_days.add(pd)
            else:
                # No activities yet - use first N preferred days
                area_primary_days = set(PREFERRED_DAY_ORDER[:min_days_needed])

        if allowed_policy_days:
            area_primary_days = {
                day for day in (area_primary_days or set()) if day in set(allowed_policy_days)
            } or set(allowed_policy_days[: max(1, len(area_primary_days or []))])

        if activity.name == 'Climbing Tower':
             print(f"DEBUG_TOWER: {troop.name} ({comm}) -> Forced Day: {forced_day}")
             print(f"DEBUG_TOWER: Primary Days: {area_primary_days}")

        # Calculate clustering score for each slot
        # Key improvements:
        # 1. AT sharing allowed when both troops ≤16 people
        # 2. Delta prefers end of week (Thu/Fri)
        # 3. 3rd slot bonus when day already has 2 activities
        # 4. Shower House and Trading Post are exclusive per slot
        # 5. Troop-based spreading

        # Exclusive activities that can only have 1 troop at a time
        EXCLUSIVE = {'Delta', 'Super Troop', 'Climbing Tower', 'Archery', 
                    'Troop Rifle', 'Troop Shotgun', 'Gaga Ball', '9 Square',
                    'Shower House', 'Trading Post'}  # Added SH and TP

        # Activities that can be shared if conditions are met
        SHAREABLE = {'Aqua Trampoline', 'Water Polo'}  # AT can be shared if both troops ≤16

        def has_exclusive_conflict(slot: TimeSlot, act: Activity, requesting_troop: Troop = None) -> bool:
            """Check if activity would conflict with existing entries in this slot."""
            existing = [e for e in self.schedule.entries if e.time_slot == slot]

            # Check shareable activities first (AT with size check)
            if act.name in SHAREABLE:
                if act.name == 'Aqua Trampoline':
                    # Allow if current troop ≤16 scouts+adults AND existing troop ≤16 scouts+adults
                    AT_MAX = 16
                    troop_size = (requesting_troop.scouts + requesting_troop.adults) if requesting_troop else 999
                    if troop_size > AT_MAX:
                        for e in existing:
                            if e.activity.name == 'Aqua Trampoline':
                                return True  # Can't share - we're too big
                    else:
                        for e in existing:
                            if e.activity.name == 'Aqua Trampoline':
                                existing_size = e.troop.scouts + e.troop.adults
                                if existing_size > AT_MAX:
                                    return True  # Can't share - they're too big
                                at_count = sum(1 for x in existing if x.activity.name == 'Aqua Trampoline')
                                if at_count >= 2:
                                    return True  # Already 2 ATs (max capacity)
                        return False  # Can share!
                elif act.name == "Water Polo":
                    # Water Polo can have up to 2 troops
                    wp_count = sum(1 for e in existing if e.activity.name == "Water Polo")
                    if wp_count >= 2:
                        return True # Already 2 Water Polo troops, can't add more
                    return False # Can share if less than 2
                return False

            # Standard exclusive check
            if act.name not in EXCLUSIVE:
                return False
            for e in existing:
                if e.activity.name == act.name:
                    return True
            return False

        # Use troop index to spread starting days
        troop_idx = self.troops.index(troop) if troop in self.troops else 0
        preferred_day_offset = troop_idx % 5
        days = list(Day)[:5]

        def slot_score(slot: TimeSlot) -> int:
            day = slot.day
            slot_num = slot.slot_number

            # CRITICAL: Block slots with exclusive activity conflicts
            if has_exclusive_conflict(slot, activity, troop):
                return -1000

            score = 0

            # Clustering bonus - BALANCED to prefer clustering but not override Top 5
            day_count = day_counts.get(day, 0)

            # Check if this is a Top 5 activity - reduce clustering bonus to prioritize satisfaction
            activity_priority = troop.get_priority(activity.name)
            is_top5 = (activity_priority is not None and activity_priority < 5)

            if is_top5:
                # For Top 5, use moderate clustering bonus (don't let clustering override preference satisfaction)
                score += day_count * 50  # Moderate bonus for Top 5 clustering
            else:
                # For non-Top 5, use stronger clustering bonus
                score += day_count * 75  # Strong bonus for non-Top 5 clustering

            # AREA CLUSTERING BONUS: Extra bonus if this activity is from a staff area and day already has activities from same area
            if activity_staff_area:
                area_activities_set = STAFF_AREAS.get(activity_staff_area, set())
                area_count_on_day = sum(1 for e in self.schedule.entries 
                                       if e.activity.name in area_activities_set 
                                       and e.time_slot.day == day)
                if area_count_on_day > 0:
                    if is_top5:
                        score += area_count_on_day * 50  # Moderate bonus for Top 5 area clustering
                    else:
                        score += area_count_on_day * 100  # Strong bonus for non-Top 5 area clustering

                # Excess-day avoidance: penalize placements that spread this troop's
                # area beyond ceil(n/3). Keep this local during initial placement;
                # official global excess is enforced by guarded Phase D passes.
                if self._would_create_excess_day(activity.name, day, troop=troop):
                    if is_top5:
                        score -= 120  # Keep flexibility for critical preferences.
                    else:
                        score -= 260

            # Adjacency bonus
            if day in day_slots:
                existing_slots = day_slots[day]
                if (slot_num - 1) in existing_slots or (slot_num + 1) in existing_slots:
                    score += 30

            # 3RD SLOT BONUS: If day already has 2 activities, prefer filling the 3rd
            if day_count == 2 and day != Day.THURSDAY:  # Thu only has 2 slots
                if day in day_slots:
                    used_slots = day_slots[day]
                    if slot_num not in used_slots:
                        score += 40  # Strong bonus to fill the gap

            # Staff load penalty for gap-fill scoring. F-24: cap sourced from SKULL
            # (constraints.max_staff_global) instead of a hardcoded 16.
            current_load = slot_loads.get(slot, 0)
            STAFF_MAX = config_loader.get_capacity_limits().get("max_staff_global", 16)

            # IMPROVEMENT 4: Enhanced staff balance awareness
            # BONUS for underloaded slots (encourages distribution)
            avg_staff = sum(slot_loads.values()) / len(slot_loads) if slot_loads else 0

            # Calculate staff variance for this slot vs ideal distribution
            if avg_staff > 0:
                # Ideal load per slot for perfect balance
                ideal_load = avg_staff
                load_variance = abs(current_load - ideal_load)

                # Strong bonus for slots significantly under ideal (reduces variance)
                if current_load < ideal_load * 0.5:  # Very underloaded
                    if not is_top5:  # Only for non-Top 5 to protect preferences
                        score += 50  # Strong bonus for very underloaded slots
                elif current_load < ideal_load * 0.7:  # Moderately underloaded
                    if not is_top5:
                        score += 25  # Moderate bonus
                elif current_load < ideal_load * 0.85:  # Slightly underloaded
                    score += 10  # Small bonus
            else:
                # No average yet (early scheduling) - use fixed thresholds
                if current_load <= 8:
                    score += 40  # Strong bonus for very light slots
                elif current_load <= 10:
                    score += 20  # Moderate bonus for light slots
                elif current_load <= 12:
                    score += 10  # Small bonus

            # Progressive penalty as we approach the limit
            if current_load >= STAFF_MAX:
                score -= 1000  # Extreme penalty - slot is full!
            elif current_load >= STAFF_MAX - 1: # 15 staff
                score -= 200   # Severe penalty - only 1 spot left
            elif current_load >= STAFF_MAX - 2: # 14 staff
                score -= 100   # High penalty - nearing capacity
            elif current_load >= STAFF_MAX - 3: # 13 staff
                score -= 50    # Moderate penalty
            elif current_load >= STAFF_MAX - 4: # 12 staff
                score -= 30    # Minor penalty (NEW)
            else:
                score -= min(current_load * 3, 30)  # Scaled load balancing

            # AGGRESSIVE AT SHARING: Bonus for small troops to share AT
            if activity.name == 'Aqua Trampoline':
                troop_size = troop.scouts + troop.adults
                if troop_size <= 16:
                    # Check if another small troop already has AT in this slot - give BONUS!
                    for e in self.schedule.entries:
                        if e.time_slot == slot and e.activity.name == 'Aqua Trampoline':
                            existing_size = e.troop.scouts + e.troop.adults
                            if existing_size <= 16:
                                score += 60  # Strong bonus to encourage sharing!
                                break

            # BEACH SLOT 2 PENALTY: Strongly prefer Slots 1/3, use Slot 2 only as fallback
            # This ensures Slot 2 is still allowed but heavily disfavored
            beach_slot_activities = set(self.BEACH_SLOT_ACTIVITIES)
            if activity.name in beach_slot_activities:
                if slot_num == 2 and day != Day.THURSDAY:  # Thursday allows Slot 2 normally
                    score -= 300  # Heavy penalty to make Slot 2 a last resort

            # DELTA: Prefer BEGINNING of week (Mon=+30, Tue=+20, Wed=+10)
            # IMPROVEMENT 3: Bonus for Delta+Sailing pairing (same day)
            # ENHANCED: Better bonus logic with Top 5 protection
            if activity.name == 'Delta':
                if day == Day.MONDAY:
                    score += 30
                elif day == Day.TUESDAY:
                    score += 20
                elif day == Day.WEDNESDAY:
                    score += 10

                # ENHANCED: Stronger bonus for Delta+Sailing pairing when already paired
                # Only apply if this is not a Top 5 activity
                if not is_top5 and "Sailing" in troop.preferences:
                    has_sailing_today = any(
                        e.troop == troop and e.activity.name == "Sailing" and e.time_slot.day == day
                        for e in self.schedule.entries
                    )
                    if has_sailing_today:
                        score += 40  # Increased from 25 to 40 (still conservative)

            # IMPROVEMENT 3: Super Troop + Rifle pairing bonus
            # ENHANCED: Stronger bonus for Super Troop+Rifle pairing when already paired
            if not is_top5 and activity.name in ['Troop Rifle', 'Troop Shotgun']:
                if "Super Troop" in troop.preferences:
                    has_st_today = any(
                        e.troop == troop and e.activity.name == "Super Troop" and e.time_slot.day == day
                        for e in self.schedule.entries
                    )
                    if has_st_today:
                        score += 40  # Increased from 25 to 40 (still conservative)

            # IMPROVEMENT 3: Sailing pairing bonus (for Delta+Sailing)
            # ENHANCED: Stronger bonus for Sailing+Delta pairing when already paired
            if not is_top5 and activity.name == 'Sailing':
                if "Delta" in troop.preferences:
                    has_delta_today = any(
                        e.troop == troop and e.activity.name == "Delta" and e.time_slot.day == day
                        for e in self.schedule.entries
                    )
                    if has_delta_today:
                        score += 40  # Increased from 25 to 40 (still conservative)

                # IMPROVEMENT 2: Enhanced Sailing same-day pairing - prefer days with 1 existing Sailing
                # ENHANCED: Stronger bonus for optimal 2-per-day Sailing pattern
                if not is_top5:
                    sailing_on_day = sum(1 for e in self.schedule.entries 
                                        if e.activity.name == "Sailing" and e.time_slot.day == day)
                    if sailing_on_day == 1 and day != Day.FRIDAY and day != Day.THURSDAY:
                        score += 50  # Increased from 30 to 50 (encourages optimal 2-per-day pattern)

            # Spreading: troop's preferred starting day
            if day in days:
                day_idx = days.index(day)
                if day_count == 0 and day_idx == preferred_day_offset:
                    score += 25

            # ============================================================
            # ENHANCED: Better cluster gap detection and prevention
            # ============================================================
            if day in day_slots:
                filled_on_day = day_slots[day]
                has_slot_1 = 1 in filled_on_day
                has_slot_2 = 2 in filled_on_day
                has_slot_3 = 3 in filled_on_day

                if slot_num == 2 and not has_slot_2:
                    if has_slot_1 and has_slot_3:
                        # Check if this would fill a cluster gap for the same area
                        cluster_gap_bonus = 0
                        if activity_staff_area:
                            area_activities_set = STAFF_AREAS.get(activity_staff_area, set())
                            # Check if slots 1 and 3 have activities from the same area
                            slot_1_area = None
                            slot_3_area = None
                            for e in self.schedule.entries:
                                if e.time_slot.day == day:
                                    if e.time_slot.slot_number == 1 and e.activity.name in area_activities_set:
                                        slot_1_area = activity_staff_area
                                    elif e.time_slot.slot_number == 3 and e.activity.name in area_activities_set:
                                        slot_3_area = activity_staff_area
                            # If both slots 1 and 3 have activities from the same area, this is a cluster gap
                            if slot_1_area and slot_1_area == slot_3_area and slot_1_area == activity_staff_area:
                                cluster_gap_bonus = 200  # MASSIVE bonus for filling cluster gap

                        score += 300  # EXTREME bonus - must fill middle gap
                        score += cluster_gap_bonus  # Additional bonus for cluster gaps
                    elif has_slot_1 or has_slot_3:
                        score += 150  # Strong bonus to prevent future gap

            # ============================================================
            # STAFF AREA CLUSTERING (BULLETPROOF WITH PRE-CALCULATED DEMAND)
            # Uses pre-calculated primary days and STRONGLY PREFERS primary days
            # ============================================================
            if activity_staff_area and area_primary_days:
                area_activities_set = STAFF_AREAS[activity_staff_area]
                assigned_day, fill_days, other_comm_days = self._get_commissioner_day_tiers(troop, activity.name)
                # BALANCED bonus for primary days - less aggressive for Top 5
                if day in area_primary_days:
                    if is_top5:
                        score += 50  # Moderate bonus for Top 5 on primary days
                    else:
                        score += 100  # Strong bonus for non-Top 5 on primary days
                else:
                    if is_top5:
                        score -= 20   # Light penalty for Top 5 on non-primary days
                    else:
                        score -= 50   # Penalty for non-Top 5 on non-primary days

                # Count current distribution on each day for this area
                area_day_counts = {}
                for e in self.schedule.entries:
                    if e.activity.name in area_activities_set:
                        if e.time_slot.day not in area_day_counts:
                            area_day_counts[e.time_slot.day] = 0
                        area_day_counts[e.time_slot.day] += 1

                # Is this a primary day?
                is_primary_day = day in area_primary_days
                existing_area_count = area_day_counts.get(day, 0)

                if is_primary_day:
                    # BALANCED bonus for primary days - less aggressive for Top 5
                    if is_top5:
                        score += 200  # Moderate bonus for Top 5 on primary days
                        if existing_area_count > 0:
                            score += 50 + (existing_area_count * 25)  # Reduced bonus for Top 5
                    else:
                        score += 500  # Strong bonus for non-Top 5 on primary days
                        if existing_area_count > 0:
                            score += 200 + (existing_area_count * 100)  # Full bonus for non-Top 5

                        # FULL DAY BONUS: If this would complete a 3-slot day (only for non-Top 5)
                        # IMPROVEMENT 5: Enhanced cluster gap prevention
                        if day != Day.THURSDAY:  # Thu only has 2 slots
                            area_slots_on_day = set()
                            for e in self.schedule.entries:
                                if e.activity.name in area_activities_set and e.time_slot.day == day:
                                    area_slots_on_day.add(e.time_slot.slot_number)

                            if len(area_slots_on_day) == 2 and slot_num not in area_slots_on_day:
                                score += 500  # MASSIVE bonus to complete the day
                                # IMPROVEMENT 5: Extra bonus if this prevents a cluster gap (slots 1&3 exist, filling slot 2)
                                # FURTHER REDUCED: Only apply if not Top 5, very conservative
                                if not is_top5 and 1 in area_slots_on_day and 3 in area_slots_on_day and slot_num == 2:
                                    score += 50  # Further reduced: was +100, now +50 (very conservative, only for non-Top 5)

                elif assigned_day and day in fill_days:
                    # Second tier: use fill/overflow days before borrowing another
                    # commissioner's ownership day.
                    if day == Day.FRIDAY:
                        score += 220
                    else:
                        score += 180
                elif assigned_day and day in other_comm_days:
                    score -= 120
                elif area_primary_days:
                     score -= 100  # General penalty for non-primary days
                else:
                    # NOT a primary day
                    # Check if primary days still have capacity
                    primary_days_full = True
                    for pd in area_primary_days:
                        pd_count = area_day_counts.get(pd, 0)
                        max_per_day = 2 if pd == Day.THURSDAY else 3
                        if pd_count < max_per_day:
                            primary_days_full = False
                            break

                    if not primary_days_full:
                        # Primary days have capacity - HARD BLOCK this non-primary day
                        score -= 1000  # Effectively impossible
                    elif existing_area_count > 0:
                        # Primary days full, but this day already has entries - moderate penalty
                        score -= 100
                    else:
                        # Primary days full and this is a new day - severe penalty
                        score -= 400

            return score

        # Sort all slots by score (highest first)
        ordered_slots = sorted(self.time_slots, key=slot_score, reverse=True)

        return ordered_slots


    def _ensure_hc_dg_pairing(self):
        """
        Ensure any troop with HC/DG also has Gaga Ball or 9 Square.

        HC and DG are half-slot activities that require a balls activity
        (Gaga Ball or 9 Square) to fill the other half of the slot.
        """
        balls_activity = get_activity_by_name('Gaga Ball')
        nine_square = get_activity_by_name('9 Square')

        if not balls_activity:
            return

        # Low-priority fill activities that can be displaced
        # DISPLACEABLE = {'Shower House', 'Trading Post', 'Campsite Free Time', 'Dr. DNA', 'Fishing'}
        # MODIFIED: Logic now allows displacing ANY non-Top 5 activity (checked below)

        paired_count = 0

        for troop in self.troops:
            entries = [e for e in self.schedule.entries if e.troop == troop]
            activity_names = {e.activity.name for e in entries}

            has_hc_dg = 'History Center' in activity_names or 'Disc Golf' in activity_names
            has_balls = 'Gaga Ball' in activity_names or '9 Square' in activity_names

            if has_hc_dg and not has_balls:
                # Find an empty slot to add Gaga Ball or 9 Square
                # Prefer the same day as HC/DG
                hc_dg_day = None
                for e in entries:
                    if e.activity.name in ['History Center', 'Disc Golf']:
                        hc_dg_day = e.time_slot.day
                        break

                # Build ordered list of slots to try (HC/DG day first)
                slots_to_try = []
                if hc_dg_day:
                    for slot in self.time_slots:
                        if slot.day == hc_dg_day:
                            slots_to_try.append(slot)
                for slot in self.time_slots:
                    if slot not in slots_to_try:
                        slots_to_try.append(slot)

                added = False

                # Pass 1: Try to find an empty slot
                for activity in [balls_activity, nine_square]:
                    if not activity or added:
                        continue
                    for slot in slots_to_try:
                        if self.schedule.is_troop_free(slot, troop):
                            if self._check_activity_capacity(slot, activity, troop):
                                self._add_to_schedule(slot, activity, troop)
                                print(f"  [HC/DG Pairing] {troop.name}: Added {activity.name} -> {slot}")
                                paired_count += 1
                                added = True
                                break

                # Pass 2: Displace a low-priority activity if no empty slots
                if not added:
                    for slot in slots_to_try:
                        existing = [e for e in self.schedule.entries 
                                   if e.troop == troop and e.time_slot == slot]

                        for e in existing:
                            if True: # aggressively allow any (checks pref rank below)
                                # NEVER replace a Top 5 preference!
                                try:
                                    pref_rank = troop.preferences.index(e.activity.name)
                                    if pref_rank < 5:
                                        continue  # Skip - this is a Top 5 preference
                                except ValueError:
                                    pass  # Not in preferences - OK to displace

                                # Found a displaceable activity - replace it
                                self.schedule.entries.remove(e)

                                for activity in [balls_activity, nine_square]:
                                    if not activity:
                                        continue
                                    if self._check_activity_capacity(slot, activity, troop):
                                        self._add_to_schedule(slot, activity, troop)
                                        print(f"  [HC/DG Pairing] {troop.name}: {activity.name} -> {slot} (replaced {e.activity.name})")
                                        paired_count += 1
                                        added = True
                                        break

                                if added:
                                    break
                                else:
                                    # Restore original if we couldn't add
                                    self.schedule.entries.append(e)

                        if added:
                            break

        if paired_count > 0:
            print(f"  Added {paired_count} balls activities for HC/DG pairing")


    def _analyze_gap_patterns(self):
        """
        Analyze gap patterns to identify critical gaps that need priority filling.
        Returns analysis of which day/slot combinations have the most gaps.
        """
        from ...models import Day

        gap_counts = {}
        for day in Day:
            max_slots = 3
            if day == Day.THURSDAY:
                max_slots = 2  # Thursday only has 2 slots

            for slot_num in range(1, max_slots + 1):
                gap_counts[(day, slot_num)] = 0

        # Count gaps per day/slot across all troops
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            filled_slots = set()

            for entry in troop_entries:
                filled_slots.add((entry.time_slot.day, entry.time_slot.slot_number))

            # Count gaps for this troop
            for day in Day:
                max_slots = 3
                if day == Day.THURSDAY:
                    max_slots = 2  # Thursday only has 2 slots

                for slot_num in range(1, max_slots + 1):
                    if (day, slot_num) not in filled_slots:
                        gap_counts[(day, slot_num)] += 1

        # Sort gaps by severity (most gaps first)
        sorted_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            'gap_counts': gap_counts,
            'sorted_gaps': sorted_gaps,
            'critical_gaps': [(day, slot) for (day, slot), count in sorted_gaps if count >= 3]  # 3+ troops with gaps
        }


    def _fill_gaps_with_valuable_moves(self):
        """
        ENHANCED PROACTIVE GAP-FILLING: Move valuable activities into attractive gaps.

        For each troop, find days with staffed activities but empty slots ("attractive days").
        Then find high-priority activities on OTHER days that could move into those gaps.
        This is BETTER than filling gaps with Gaga Ball/9 Square.

        ENHANCED: Special handling for Thursday Slot 3 gaps and smarter activity selection.
        MORE AGGRESSIVE: Increased move attempts and better activity selection.
        """
        from ...models import ScheduleEntry

        # SKULL-driven activity groups.
        STAFFED_ACTIVITIES = {
            a.name for a in self.activities if config_loader.get_staff_need(a.name) > 0
        }
        FLEXIBLE_ACTIVITIES = {
            n for n in config_loader.get_activities_with_tag("fill")
            if config_loader.get_staff_need(n) <= 0
        }
        PROTECTED = (
            set(self.NON_DISPLACEABLE_ACTIVITIES)
            | set(self.THREE_HOUR_ACTIVITIES)
            | set(self.TUESDAY_ONLY_ACTIVITIES)
            | {"Sailing"}
        )

        # Build area mapping from the same areas official excess/gap scoring uses.
        CLUSTER_AREAS = self._get_authoritative_gap_area_map()

        activity_to_area = {}
        for area, acts in CLUSTER_AREAS.items():
            for act in acts:
                activity_to_area[act] = area

        days_list = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
        slots_per_day = {Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3, Day.THURSDAY: 2, Day.FRIDAY: 3}

        total_moves = 0

        # ENHANCED: Analyze gap patterns first to prioritize critical gaps
        gap_analysis = self._analyze_gap_patterns()

        # ENHANCED: Multiple passes with different strategies
        for pass_num in range(3):  # 3 passes with increasing aggression
            moves_this_pass = 0

            for troop in self.troops:
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                # Build map of what's scheduled where
                scheduled = {}
                for e in troop_entries:
                    key = (e.time_slot.day, e.time_slot.slot_number)
                    scheduled[key] = e

                # Find attractive days: have staffed activities but also have gaps
                # ENHANCED: Prioritize gaps based on gap analysis
                attractive_gaps = []  # List of (day, slot_num, cluster_score, priority_bonus)
                for day in days_list:
                    max_slot = slots_per_day[day]

                    # Count staffed activities on this day
                    staffed_on_day = [scheduled.get((day, s)) for s in range(1, max_slot + 1)
                                      if (day, s) in scheduled and scheduled[(day, s)].activity.name in STAFFED_ACTIVITIES]

                    if not staffed_on_day and pass_num < 2:
                        continue  # Pass 1-2: require staffed activities, Pass 3: any gap

                    # Find empty slots on this day
                    for slot_num in range(1, max_slot + 1):
                        if (day, slot_num) not in scheduled:
                            # Calculate cluster score for this gap
                            cluster_score = len(staffed_on_day)

                            # ENHANCED: Add priority bonus based on gap analysis
                            priority_bonus = 0
                            if (day, slot_num) in gap_analysis['critical_gaps']:
                                priority_bonus = 10 + (pass_num * 5)  # Increasing priority per pass

                            # Special bonus for Thursday patterns
                            if day == Day.THURSDAY and slot_num == 2:
                                priority_bonus += 5  # Thursday slot 2 is valuable

                            attractive_gaps.append((day, slot_num, cluster_score, priority_bonus))

                if not attractive_gaps:
                    continue

                # ENHANCED: Sort gaps by priority (critical gaps first)
                attractive_gaps.sort(key=lambda x: (x[3], x[2]), reverse=True)

                # Find movable activities on other days
                candidates = []  # List of (entry, target_day, target_slot, score)

                # Calculate PRIMARY DAYS for each staff area to protect clustering
                import math
                STAFF_AREA_PRIMARY_DAYS = {}
                for area, area_acts in CLUSTER_AREAS.items():
                    area_entries = [e for e in self.schedule.entries if e.activity.name in area_acts]
                    if not area_entries:
                        continue
                    from collections import Counter
                    day_dist = Counter(e.time_slot.day for e in area_entries)
                    total = len(area_entries)
                    min_days = math.ceil(total / 3)
                    # Primary days = top N days by count
                    primary = set(d for d, _ in day_dist.most_common(min_days))
                    STAFF_AREA_PRIMARY_DAYS[area] = primary

                # ENHANCED: Expand activity pool based on pass number
                allowed_activities = STAFFED_ACTIVITIES.copy()
                if pass_num >= 1:
                    allowed_activities.update(FLEXIBLE_ACTIVITIES)

                for source_entry in troop_entries:
                    if source_entry.activity.name in PROTECTED:
                        continue
                    if source_entry.activity.name not in allowed_activities:
                        continue  # Only move allowed activities for this pass

                    source_day = source_entry.time_slot.day
                    source_slot = source_entry.time_slot.slot_number

                    # PROTECT CLUSTERING: Don't move staff area activities FROM primary days (except in pass 3)
                    if pass_num < 3:
                        activity_area = activity_to_area.get(source_entry.activity.name)
                        if activity_area:
                            primary_days = STAFF_AREA_PRIMARY_DAYS.get(activity_area, set())
                            if source_day in primary_days:
                                continue  # Don't move from primary day!

                    # Check if moving this would help (leaving a bad day for a good one)
                    source_staffed_count = sum(1 for s in range(1, slots_per_day[source_day] + 1)
                                              if (source_day, s) in scheduled 
                                              and scheduled[(source_day, s)].activity.name in STAFFED_ACTIVITIES)

                    for target_day, target_slot, target_cluster_score, priority_bonus in attractive_gaps:
                        if target_day == source_day:
                            continue  # Same day, no benefit

                        # Score the move
                        score = 0

                        # 1. ENHANCED: Priority gap bonus (increases with pass)
                        score += priority_bonus * (2 + pass_num)

                        # 2. Cluster improvement: moving to a day with more staffed activities
                        score += (target_cluster_score - source_staffed_count + 1) * 2

                        # 3. Area clustering bonus
                        activity_area = activity_to_area.get(source_entry.activity.name)
                        if activity_area:
                            target_area_count = sum(1 for e in troop_entries 
                                                   if e.time_slot.day == target_day 
                                                   and e.activity.name in CLUSTER_AREAS.get(activity_area, []))
                            score += target_area_count * 3

                        # 4. Leaving isolation bonus (source day only has 1 activity)
                        if source_staffed_count <= 1:
                            score += 2  # Good to leave isolated day

                        # 5. Priority bonus
                        priority = troop.get_priority(source_entry.activity.name)
                        if priority is not None and priority < 10:
                            score += 1  # Top 10 activity

                        # 6. ENHANCED: Staff load consideration
                        # Prefer moves that don't overload target slot
                        target_load = sum(self._get_activity_staff_count(e.activity.name) 
                                        for e in self.schedule.entries 
                                        if e.time_slot.day == target_day and e.time_slot.slot_number == target_slot)
                        if target_load < 12:  # Underloaded slot
                            score += 3
                        elif target_load > 15:  # Overloaded slot
                            score -= 5  # Penalty for overloading

                        # 7. ENHANCED: Pass-specific bonuses
                        if pass_num >= 2:
                            # Later passes: bonus for any move that fills a gap
                            score += 5

                        if score > 0:
                            candidates.append((source_entry, target_day, target_slot, score))

                # Sort by score (highest first) and execute best moves
                candidates.sort(key=lambda x: x[3], reverse=True)

                moves_for_troop = 0
                max_moves_per_troop = 2 if pass_num < 2 else 3  # More moves in later passes

                for source_entry, target_day, target_slot, score in candidates:
                    if moves_for_troop >= max_moves_per_troop:
                        break

                    # Check if source entry still exists
                    if source_entry not in self.schedule.entries:
                        continue

                    # Check if target slot is still empty
                    if (target_day, target_slot) in scheduled:
                        continue

                    # Try the move
                    try:
                        # Create new entry for target
                        new_entry = ScheduleEntry(
                            TimeSlot(day=target_day, slot_number=target_slot),
                            source_entry.activity,
                            troop
                        )

                        # Remove old entry and add new one
                        self.schedule.entries.remove(source_entry)
                        self.schedule.entries.append(new_entry)

                        total_moves += 1
                        moves_this_pass += 1
                        moves_for_troop += 1

                        # Update scheduled map
                        del scheduled[(source_entry.time_slot.day, source_entry.time_slot.slot_number)]
                        scheduled[(target_day, target_slot)] = new_entry

                    except Exception as e:
                        # Move failed, continue
                        continue

            if moves_this_pass == 0:
                break  # No moves this pass, stop early

        return total_moves


    def _total_excess_cluster_days(self) -> int:
        """Total excess cluster days across all CLUSTER_AREAS for the
        current schedule state. Mirrors regression checker's definition:
        required_days = ceil(activity_count / 3), excess = max(0, days_used - required).
        """
        import math
        total_excess = 0
        for _area, activities in self._get_authoritative_gap_area_map().items():
            area_entries = [
                e for e in self.schedule.entries
                if e.activity.name in activities
            ]
            if not area_entries:
                continue
            days_used = len({e.time_slot.day for e in area_entries})
            required_days = math.ceil(len(area_entries) / 3.0)
            total_excess += max(0, days_used - required_days)
        return total_excess


    def _finalize_filler_replacement_audit(self) -> dict:
        """Post-pipeline safe-swap audit (runs ONCE at the very end).

        For each placed generic-filler activity, try to swap in the
        highest-ranked unscheduled preference that fits the slot. Commit
        only when ALL safety guards pass:

          * Strict _can_schedule(relax_constraints=False)
          * Top-5 non-exempt miss count NOT increased
          * Top-10 global count NOT decreased
          * Soft metrics are measured for diagnostics, but do not block a
            valid requested activity from replacing a generic filler.

        If any guard fails, the state is restored and the next candidate
        preference is tried. If none pass, the filler is left untouched.

        Returns a stats dict suitable for reporting.
        """
        FILLER_SET = set(self.FINAL_AUDIT_FILLER_ACTIVITIES)
        MANDATORY_ANCHORS = self._get_protected_activity_names({"Honor Camper", "Director's Game", "Delta"})

        stats = {
            "candidates_seen": 0,
            "swaps_committed": 0,
            "blocked_by_can_schedule": 0,
            "blocked_by_top5": 0,
            "blocked_by_top10": 0,
            "blocked_by_cluster": 0,
            "blocked_by_staff": 0,
            "no_pref_fit": 0,
            "generic_cft_swaps": 0,
            "rank_histogram": {},
        }

        # Snapshot baseline metrics for relative comparison across the full pass
        try:
            top5_baseline, _ = self._count_non_exempt_top5_misses()
        except Exception:
            top5_baseline = 0
        top10_baseline = self._count_top10_in_schedule()
        excess_baseline = self._total_excess_cluster_days()
        try:
            staff_baseline = self._calculate_staff_variance()
        except Exception:
            staff_baseline = 0.0

        print(
            f"  [Final Audit] baseline: top5_miss={top5_baseline}, "
            f"top10={top10_baseline}, excess_days={excess_baseline}, "
            f"staff_var={staff_baseline:.3f}"
        )

        filler_entries = [
            e for e in list(self.schedule.entries)
            if e.activity.name in FILLER_SET
            and e.activity.name not in MANDATORY_ANCHORS
            and not getattr(e, "is_continuation", False)
            # F-04A: a day-requested filler (e.g. Campsite Free Time, Shower
            # House) placed on its requested day is a honored MUST-HONOR
            # request, not replaceable filler. Leave it untouched.
            and not self._is_honored_day_request_entry(e)
        ]

        for filler_entry in filler_entries:
            if filler_entry not in self.schedule.entries:
                continue
            stats["candidates_seen"] += 1

            troop = filler_entry.troop
            slot = filler_entry.time_slot
            day = slot.day

            scheduled_names = {
                e.activity.name for e in self.schedule.entries if e.troop == troop
            }
            current_rank = troop.get_priority(filler_entry.activity.name)
            if current_rank is not None and current_rank >= 999:
                current_rank = None

            committed_this_filler = False

            for pref_rank, pref_name in enumerate(troop.preferences or []):
                if current_rank is not None and pref_rank >= current_rank:
                    break
                if pref_name in scheduled_names:
                    continue
                pref_activity = get_activity_by_name(pref_name)
                if not pref_activity:
                    continue

                # Transactional swap: snapshot, remove filler, add pref, measure.
                snapshot = self._snapshot_scheduler_state()

                self._remove_from_schedule(filler_entry)

                if not self._can_schedule(
                    troop, pref_activity, slot, day, relax_constraints=False,
                ):
                    self._restore_scheduler_state(snapshot)
                    stats["blocked_by_can_schedule"] += 1
                    continue

                if not self._add_to_schedule(slot, pref_activity, troop):
                    self._restore_scheduler_state(snapshot)
                    stats["blocked_by_can_schedule"] += 1
                    continue

                # Post-swap metric evaluation
                try:
                    top5_after, _ = self._count_non_exempt_top5_misses()
                except Exception:
                    top5_after = top5_baseline
                top10_after = self._count_top10_in_schedule()
                excess_after = self._total_excess_cluster_days()
                try:
                    staff_after = self._calculate_staff_variance()
                except Exception:
                    staff_after = staff_baseline

                if top5_after > top5_baseline:
                    self._restore_scheduler_state(snapshot)
                    stats["blocked_by_top5"] += 1
                    continue
                if top10_after < top10_baseline:
                    self._restore_scheduler_state(snapshot)
                    stats["blocked_by_top10"] += 1
                    continue
                # All guards passed — commit. Update progress tracking so
                # downstream sailing-balls metadata sees the new pref.
                self._update_progress(troop, pref_activity.name)
                stats["swaps_committed"] += 1
                stats["rank_histogram"][pref_rank + 1] = (
                    stats["rank_histogram"].get(pref_rank + 1, 0) + 1
                )

                # Update baselines so subsequent swaps are evaluated
                # against the new (improved) state, not the stale original.
                top10_baseline = top10_after
                excess_baseline = excess_after
                staff_baseline = staff_after

                # #region agent log
                self._debug_log(
                    "H-AUDIT",
                    "gap_fill_and_stats.py:_finalize_filler_replacement_audit",
                    "Safe swap: filler -> unscheduled preference",
                    {
                        "troop": troop.name,
                        "day": day.name,
                        "slot": slot.slot_number,
                        "replaced": filler_entry.activity.name,
                        "placedPref": pref_name,
                        "prefRank": pref_rank + 1,
                        "top10": top10_after,
                        "excessDays": excess_after,
                        "staffVar": round(staff_after, 4),
                        "runId": "final-audit",
                    },
                )
                # #endregion
                print(
                    f"  [Final Audit] {troop.name}: {filler_entry.activity.name} "
                    f"-> {pref_name} (#{pref_rank + 1}) @ {day.name[:3]}-{slot.slot_number}"
                )
                committed_this_filler = True
                break

            if not committed_this_filler:
                cft_activity = get_activity_by_name("Campsite Free Time")
                if (
                    cft_activity
                    and current_rank is None
                    and filler_entry.activity.name != "Campsite Free Time"
                    and "Campsite Free Time" not in scheduled_names
                ):
                    snapshot = self._snapshot_scheduler_state()
                    self._remove_from_schedule(filler_entry)
                    if (
                        self._can_schedule(
                            troop,
                            cft_activity,
                            slot,
                            day,
                            relax_constraints=False,
                        )
                        and self._add_to_schedule(slot, cft_activity, troop)
                    ):
                        try:
                            top5_after, _ = self._count_non_exempt_top5_misses()
                        except Exception:
                            top5_after = top5_baseline
                        top10_after = self._count_top10_in_schedule()
                        if top5_after <= top5_baseline and top10_after >= top10_baseline:
                            stats["generic_cft_swaps"] += 1
                            committed_this_filler = True
                            print(
                                f"  [Final Audit] {troop.name}: {filler_entry.activity.name} "
                                f"-> Campsite Free Time @ {day.name[:3]}-{slot.slot_number}"
                            )
                        else:
                            self._restore_scheduler_state(snapshot)
                    else:
                        self._restore_scheduler_state(snapshot)

            if not committed_this_filler:
                stats["no_pref_fit"] += 1

        print(
            f"  [Final Audit] candidates={stats['candidates_seen']}, "
            f"committed={stats['swaps_committed']}, "
            f"generic_cft={stats['generic_cft_swaps']}, "
            f"no_pref_fit={stats['no_pref_fit']}, "
            f"blocked[can_sched={stats['blocked_by_can_schedule']}, "
            f"top5={stats['blocked_by_top5']}, top10={stats['blocked_by_top10']}, "
            f"cluster={stats['blocked_by_cluster']}, staff={stats['blocked_by_staff']}]"
        )
        if stats["rank_histogram"]:
            ranks_str = ", ".join(
                f"#{r}:{c}" for r, c in sorted(stats["rank_histogram"].items())
            )
            print(f"  [Final Audit] rank histogram: {ranks_str}")
        return stats


    def _guarantee_no_gaps(self):
        """
        ABSOLUTE FINAL SAFETY NET: Ensure every troop has an activity in every slot.

        This runs as the very last phase after all other scheduling and cleanup.
        For any remaining empty slots, FORCE-fill with harmless activities.

        This method is intentionally aggressive for completeness, but must still
        preserve scheduling validity by using Schedule.add_entry() for all inserts.
        """
        days_list = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
        slots_per_day = {
            Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
            Day.THURSDAY: 2, Day.FRIDAY: 3
        }

        # Generic fills come from SKULL fill_priority. Requests are prepended
        # per gap below, so a generic fill is only used when no request fits.
        FORCE_FILL_ACTIVITIES = list(self.DEFAULT_FILL_PRIORITY or self.EMERGENCY_FILL_ACTIVITIES)

        def _ordered_gap_fill_names(troop):
            scheduled_names = {
                e.activity.name for e in self.schedule.entries if e.troop == troop
            }
            remaining_prefs = [
                p for p in (troop.preferences or []) if p not in scheduled_names
            ]
            return remaining_prefs + [
                f for f in FORCE_FILL_ACTIVITIES if f not in remaining_prefs
            ]

        def _try_gap_fill(troop, slot, day, relax_constraints=False):
            for fill_name in _ordered_gap_fill_names(troop):
                activity = get_activity_by_name(fill_name)
                if not activity or self._troop_has_activity(troop, activity):
                    continue
                if not self._can_schedule(
                    troop,
                    activity,
                    slot,
                    day,
                    relax_constraints=relax_constraints,
                ):
                    continue
                if self._add_to_schedule(slot, activity, troop):
                    if fill_name in (troop.preferences or []):
                        self._update_progress(troop, fill_name)
                    return fill_name, activity
            return None

        gaps_filled = 0
        max_iterations = 8  # Increased iterations for more aggressive filling

        print(f"  [Gap Fill] Starting ABSOLUTE gap detection and filling...")

        for iteration in range(max_iterations):
            iteration_fills = 0
            print(f"    Iteration {iteration + 1}/{max_iterations}...")

            for troop in self.troops:
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                # Build filled_slots accounting for multi-slot activities
                # Use the actual is_troop_free method to detect gaps
                filled_slots = set()

                # First pass: Mark all directly occupied slots
                for day in days_list:
                    for slot_num in range(1, slots_per_day[day] + 1):
                        slot = next((s for s in self.time_slots 
                                    if s.day == day and s.slot_number == slot_num), None)
                        if slot and not self.schedule.is_troop_free(slot, troop):
                            # Troop is NOT free = slot is filled
                            filled_slots.add((day, slot_num))

                # Second pass: Mark slots occupied by multi-slot activities
                for entry in self.schedule.entries:
                    if entry.troop == troop:
                        day = entry.time_slot.day
                        start_slot = entry.time_slot.slot_number

                        # Get effective slots for this activity
                        effective_slots = self.schedule._get_effective_slots(entry.activity, troop)
                        slots_occupied = int(effective_slots + 0.5)  # Round up

                        # Mark all slots this activity occupies
                        for offset in range(slots_occupied):
                            occupied_slot_num = start_slot + offset
                            if occupied_slot_num <= slots_per_day[day]:
                                filled_slots.add((day, occupied_slot_num))

                # Find and fill gaps - CLUSTER-AWARE: days with more activities first
                activities_per_day = {}
                for day in days_list:
                    count = len([e for e in troop_entries if e.time_slot.day == day])
                    activities_per_day[day] = count
                sorted_days = sorted(days_list, key=lambda d: activities_per_day.get(d, 0), reverse=True)

                for day in sorted_days:
                    for slot_num in range(1, slots_per_day[day] + 1):
                        if (day, slot_num) not in filled_slots:
                            # Found a gap - force fill it
                            slot = next((s for s in self.time_slots 
                                        if s.day == day and s.slot_number == slot_num), None)
                            if not slot:
                                continue

                            # Double-check: Use is_troop_free to verify this is actually a gap
                            if not self.schedule.is_troop_free(slot, troop):
                                # Not actually a gap - might be occupied by multi-slot activity
                                # Update filled_slots to avoid re-checking
                                filled_slots.add((day, slot_num))
                                continue

                            # SPECIAL HANDLING: Check if this gap should be filled as a continuation of a 1.5-slot activity
                            should_fill_as_continuation = False
                            if slot_num > 1:  # Only check slots 2 and 3
                                prev_slot = next((s for s in self.time_slots 
                                                if s.day == day and s.slot_number == slot_num - 1), None)
                                if prev_slot:
                                    # Check if there's a 1.5-slot activity starting in previous slot
                                    for entry in self.schedule.entries:
                                        if (entry.troop == troop and 
                                            entry.time_slot == prev_slot):
                                            effective_slots = self.schedule._get_effective_slots(entry.activity, troop)
                                            if effective_slots >= 1.5:
                                                should_fill_as_continuation = True
                                                # Fill with the same activity as continuation
                                                activity = entry.activity
                                                if self._add_to_schedule(slot, activity, troop):
                                                    print(f"  [CONTINUATION] {troop.name}: {activity.name} -> {day.name[:3]}-{slot_num} (continuation of {prev_slot.slot_number})")
                                                    filled = True
                                                    iteration_fills += 1
                                                    gaps_filled += 1
                                                    filled_slots.add((day, slot_num))
                                                break

                            if should_fill_as_continuation:
                                continue  # Skip normal gap filling

                            filled = False

                            if iteration >= 5:
                                placed = _try_gap_fill(troop, slot, day, relax_constraints=True)
                                if placed:
                                    fill_name, _activity = placed
                                    # #region agent log
                                    self._debug_log(
                                        "H1",
                                        "gap_fill_and_stats.py:_guarantee_no_gaps:late",
                                        "Late gap fill used request-first ordering",
                                        {
                                            "troop": troop.name,
                                            "day": day.name,
                                            "slot": slot_num,
                                            "fillName": fill_name,
                                            "iteration": iteration,
                                            "phase": getattr(self, "current_pipeline_phase", "unknown"),
                                        },
                                    )
                                    # #endregion
                                    print(f"  [FORCE FILL] {troop.name}: {fill_name} -> {day.name[:3]}-{slot_num}")
                                    filled = True
                                    iteration_fills += 1
                                    gaps_filled += 1
                                    filled_slots.add((day, slot_num))
                                    troop_entries = [e for e in self.schedule.entries if e.troop == troop]
                            else:
                                placed = _try_gap_fill(
                                    troop,
                                    slot,
                                    day,
                                    relax_constraints=iteration >= 3,
                                )
                                if placed:
                                    fill_name, _activity = placed
                                    # #region agent log
                                    self._debug_log(
                                        "H2",
                                        "gap_fill_and_stats.py:_guarantee_no_gaps:request_first",
                                        "Gap fill selected request-first candidate",
                                        {
                                            "troop": troop.name,
                                            "day": day.name,
                                            "slot": slot_num,
                                            "chosenFill": fill_name,
                                            "iteration": iteration,
                                            "phase": getattr(self, "current_pipeline_phase", "unknown"),
                                        },
                                    )
                                    # #endregion
                                    tag = "[RELAXED FILL]" if iteration >= 3 else "[Gap Fill]"
                                    print(f"  {tag} {troop.name}: {fill_name} -> {day.name[:3]}-{slot_num}")
                                    filled = True
                                    iteration_fills += 1
                                    gaps_filled += 1
                                    filled_slots.add((day, slot_num))
                                    troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                                # If still not filled after all candidates, attempt safe emergency fill.
                                if not filled and iteration >= 3:
                                    placed = _try_gap_fill(troop, slot, day, relax_constraints=True)
                                    if placed:
                                        fill_name, _activity = placed
                                        print(f"  [SAFE EMERGENCY FILL] {troop.name}: {fill_name} -> {day.name[:3]}-{slot_num}")
                                        filled = True
                                        iteration_fills += 1
                                        gaps_filled += 1
                                        filled_slots.add((day, slot_num))
                                        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

            print(f"  Total gaps filled: {gaps_filled}")

            # Check if we're done
            if iteration_fills == 0:
                print(f"  No gaps filled in iteration {iteration + 1} - checking if complete...")
                # Verify no gaps remain
                total_gaps = 0
                for troop in self.troops:
                    for day in days_list:
                        for slot_num in range(1, slots_per_day[day] + 1):
                            slot = next((s for s in self.time_slots 
                                        if s.day == day and s.slot_number == slot_num), None)
                            if slot and self.schedule.is_troop_free(slot, troop):
                                total_gaps += 1

                if total_gaps == 0:
                    print(f"  SUCCESS: All gaps filled!")
                    break
                else:
                    print(f"  Still have {total_gaps} gaps, continuing...")
            else:
                print(f"  Filled {iteration_fills} gaps this iteration")

        # Final verification
        final_gaps = 0
        for troop in self.troops:
            for day in days_list:
                for slot_num in range(1, slots_per_day[day] + 1):
                    slot = next((s for s in self.time_slots 
                                if s.day == day and s.slot_number == slot_num), None)
                    if slot and self.schedule.is_troop_free(slot, troop):
                        final_gaps += 1

        if final_gaps > 0:
            print(f"  WARNING: {final_gaps} gaps remain after all attempts!")
            # Last resort still honors request-first, then SKULL fill_priority.
            for troop in self.troops:
                for day in days_list:
                    for slot_num in range(1, slots_per_day[day] + 1):
                        slot = next((s for s in self.time_slots 
                                    if s.day == day and s.slot_number == slot_num), None)
                        if slot and self.schedule.is_troop_free(slot, troop):
                            placed = _try_gap_fill(troop, slot, day, relax_constraints=True)
                            if placed:
                                fill_name, _activity = placed
                                print(f"  [EMERGENCY FILL] {troop.name}: {fill_name} -> {day.name[:3]}-{slot_num}")
                                final_gaps -= 1
                            else:
                                print(f"  [UNRESOLVED GAP] {troop.name}: {day.name[:3]}-{slot_num} (no safe fill found)")

        print(f"  Final gap filling complete. Total filled: {gaps_filled}")
        return gaps_filled


    def _force_zero_gaps_absolute(self):
        """
        ABSOLUTE FINAL METHOD: Force 0 gaps by any means necessary.

        This is the last resort method that attempts to fill remaining gaps
        with safe fallback activities while preserving Schedule.add_entry checks.
        """
        from ...activities import get_activity_by_name
        from ...models import Day

        days_list = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
        slots_per_day = {
            Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
            Day.THURSDAY: 2, Day.FRIDAY: 3
        }

        print(f"  [ABSOLUTE] Forcing 0 gaps - final emergency measure...")

        total_gaps_found = 0
        total_gaps_filled = 0

        for troop in self.troops:
            troop_gaps = 0

            for day in days_list:
                for slot_num in range(1, slots_per_day[day] + 1):
                    slot = next((s for s in self.time_slots 
                                if s.day == day and s.slot_number == slot_num), None)
                    if not slot:
                        continue

                    # Check if troop is actually free
                    if self.schedule.is_troop_free(slot, troop):
                        troop_gaps += 1
                        total_gaps_found += 1

                        # Try multiple safe filler activities; never bypass add_entry checks.
                        placed = False
                        for fill_name in self.EMERGENCY_FILL_ACTIVITIES:
                            activity = get_activity_by_name(fill_name)
                            if not activity:
                                continue
                            if self.schedule.add_entry(slot, activity, troop):
                                print(f"  [EMERGENCY] {troop.name}: {fill_name} -> {day.name[:3]}-{slot_num}")
                                total_gaps_filled += 1
                                placed = True
                                break
                        if not placed:
                            print(f"  [UNRESOLVED GAP] {troop.name}: {day.name[:3]}-{slot_num} (no safe fill found)")

            if troop_gaps > 0:
                print(f"  {troop.name}: {troop_gaps} gaps filled")

        print(f"  [ABSOLUTE] Total gaps found: {total_gaps_found}")
        print(f"  [ABSOLUTE] Total gaps filled: {total_gaps_filled}")

        if total_gaps_found == total_gaps_filled:
            print(f"  [SUCCESS] ALL GAPS ELIMINATED!")
        else:
            print(f"  [WARNING] {total_gaps_found - total_gaps_filled} gaps could not be filled")

        return total_gaps_filled


    def _get_activity_score(self, troop, activity, slot, day):
        """
        Calculate score for an activity placement.
        Higher scores = better placement.
        """


    def get_stats(self) -> dict:
        stats = {'total_entries': len(self.schedule.entries), 'troops': {}}

        for troop in self.troops:
            entries = self.schedule.get_troop_schedule(troop)
            top5_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 5)
            top10_count = sum(1 for e in entries if troop.get_priority(e.activity.name) < 10)
            has_reflection = any(e.activity.name == "Reflection" for e in entries)

            stats['troops'][troop.name] = {
                'total_scheduled': len(entries),
                'top5_achieved': top5_count,
                'top10_achieved': top10_count,
                'has_reflection': has_reflection
            }

        return stats


    def _calculate_staff_load_by_slot(self) -> dict:
        """
        Calculate staff workload for each time slot.
        Returns: {TimeSlot: total_staff_count}
        """
        staff_loads = {}
        for slot in self.time_slots:
            # Count total staff usage in this slot
            entries = [e for e in self.schedule.entries if e.time_slot == slot]
            total_staff = sum(self._get_activity_staff_count(e.activity.name) for e in entries)
            staff_loads[slot] = total_staff

        return staff_loads


    def _get_staff_balance_score(self, staff_loads: dict = None) -> float:
        """
        Calculate balance score - lower is better.
        Uses standard deviation of total staff counts per slot.
        """
        if staff_loads is None:
            staff_loads = self._calculate_staff_load_by_slot()

        # Get total staff count per slot (sum across all zones)
        slot_totals = []
        for slot, zones in staff_loads.items():
            total = sum(count for zone, count in zones.items() if zone != "UNSTAFFED")
            slot_totals.append(total)

        # Calculate standard deviation
        if not slot_totals:
            return 0.0

        mean = sum(slot_totals) / len(slot_totals)
        variance = sum((x - mean) ** 2 for x in slot_totals) / len(slot_totals)
        std_dev = variance ** 0.5

        return std_dev


    def _balance_staff_loads(self):
        """
        Optimization phase to balance staff workload across slots.
        Focuses on reducing peaks (>14 staff) and severe underuse (<5 staff) by moving/swapping activities.

        ENHANCED: More aggressive balancing with better target selection and staff variance reduction.
        """
        print("\n--- Balancing Staff Loads (Peak Reduction & Underuse Fix) ---")

        STAFF_HIGH_WATER = 14  # Try to keep slots at or below this
        SEVERE_UNDERUSE_THRESHOLD = 5  # Slots with <5 staff are severely underused
        PROTECTED = {'Reflection', 'Delta', 'Super Troop'}

        improvements = 0
        max_attempts = 400  # ENHANCED: Increased from 300 to 400 for more aggressive balancing

        # ENHANCED: Calculate ideal staff distribution for better balancing
        total_staff = sum(self._get_activity_staff_count(e.activity.name) for e in self.schedule.entries)
        total_slots = len(self.time_slots)
        ideal_staff_per_slot = total_staff / total_slots

        for attempt in range(max_attempts):
            loads = self._calculate_staff_load_by_slot()

            # Identify high-load slots, sorted worst first
            high_slots = [(slot, load) for slot, load in loads.items() if load > STAFF_HIGH_WATER]
            high_slots.sort(key=lambda x: x[1], reverse=True)

            # NEW: Identify severely underused slots
            underused_slots = [(slot, load) for slot, load in loads.items() if load < SEVERE_UNDERUSE_THRESHOLD]
            underused_slots.sort(key=lambda x: x[1])  # Lowest first

            # ENHANCED: Also identify slots far from ideal (variance reduction)
            variance_slots = []
            for slot, load in loads.items():
                if abs(load - ideal_staff_per_slot) > ideal_staff_per_slot * 0.4:  # More than 40% from ideal
                    variance_slots.append((slot, load, abs(load - ideal_staff_per_slot)))
            variance_slots.sort(key=lambda x: x[2], reverse=True)  # Worst variance first

            # Priority: Fix high loads first, then severe underuse, then variance
            if high_slots:
                # Try to fix the worst slot
                source_slot, current_load = high_slots[0]
                target_type = "high"
            elif underused_slots:
                # Try to improve underused slots by moving staffed activities there
                target_slot, target_load = underused_slots[0]
                target_type = "underuse"
            elif variance_slots:
                # Try to reduce variance
                if variance_slots[0][1] > ideal_staff_per_slot:
                    source_slot, current_load, variance = variance_slots[0]
                    target_type = "variance_high"
                else:
                    target_slot, target_load, variance = variance_slots[0]
                    target_type = "variance_low"
            else:
                break  # All slots are balanced!

            moved = False

            if target_type == "high":
                # Find a movable single-slot entry in this slot (avoid partial multi-slot moves)
                source_entries = [e for e in self.schedule.entries if e.time_slot == source_slot and e.activity.slots <= 1.0]
                source_entries.sort(key=lambda e: (
                    e.activity.name in PROTECTED,
                    (e.troop.get_priority(e.activity.name) or 999) < 5,
                    e.troop.get_priority(e.activity.name) if e.troop.get_priority(e.activity.name) is not None else 999
                ))

                for entry in source_entries:
                    if entry.activity.name in PROTECTED:
                        continue

                    # Logic: can we move this to a slot with lower load?
                    entry_staff = self._get_activity_staff_count(entry.activity.name)

                    # Find valid target slots (load + entry_staff <= STAFF_HIGH_WATER)
                    # Use _can_schedule to respect Spine (beach slot, wet-dry, etc.)
                    # Prefer underused slots to kill two birds with one stone
                    candidates = []
                    for candidate_slot, candidate_load in loads.items():
                        if candidate_slot == source_slot: continue
                        if candidate_load + entry_staff <= STAFF_HIGH_WATER and self.schedule.is_troop_free(candidate_slot, entry.troop):
                            if self._can_schedule(entry.troop, entry.activity, candidate_slot, candidate_slot.day, relax_constraints=False):
                                bonus = 100 if candidate_load < SEVERE_UNDERUSE_THRESHOLD else 0
                                candidates.append((candidate_slot, candidate_load, bonus))

                    if candidates:
                        # Pick best candidate (prefer underused, then same day > adjacent day)
                        candidates.sort(key=lambda x: (-x[2], abs(list(Day).index(x[0].day) - list(Day).index(source_slot.day))))
                        for target, target_load, _ in candidates:
                            if not self._can_schedule(entry.troop, entry.activity, target, target.day, relax_constraints=False):
                                continue
                            self.schedule.entries.remove(entry)
                            self.schedule.add_entry(target, entry.activity, entry.troop)
                            self._fill_vacated_slot(entry.troop, source_slot)
                            print(f"  [Load Balance] {entry.troop.name}: {entry.activity.name} {source_slot} ({current_load}) -> {target} ({target_load})")
                            improvements += 1
                            moved = True
                            break
                        if moved:
                            break
            else:
                # target_type == "underuse": Try to move staffed activities TO underused slots
                # Use _can_schedule to respect Spine; _fill_vacated_slot to avoid gaps.
                # Only move single-slot activities to avoid partial multi-slot moves.
                all_staffed_entries = []
                for entry in self.schedule.entries:
                    if entry.activity.name in PROTECTED:
                        continue
                    if entry.activity.slots > 1.0:
                        continue  # Skip multi-slot to avoid partial moves
                    entry_staff = self._get_activity_staff_count(entry.activity.name)
                    if entry_staff == 0:
                        continue
                    source_slot = entry.time_slot
                    source_load = loads.get(source_slot, 0)
                    entry_priority = entry.troop.get_priority(entry.activity.name)
                    priority_score = entry_priority if entry_priority is not None else 999
                    all_staffed_entries.append((entry, source_load, priority_score, entry_staff))

                all_staffed_entries.sort(key=lambda x: (-x[1], x[2]))

                for entry, source_load, priority_score, entry_staff in all_staffed_entries:
                    source_slot = entry.time_slot

                    # Find underused target slots
                    for target_slot, target_load in loads.items():
                        if target_slot == source_slot:
                            continue
                        if target_load >= SEVERE_UNDERUSE_THRESHOLD + 2:
                            continue
                        if not self.schedule.is_troop_free(target_slot, entry.troop):
                            continue
                        if not self._can_schedule(entry.troop, entry.activity, target_slot, target_slot.day, relax_constraints=False):
                            continue
                        new_target_load = target_load + entry_staff
                        new_source_load = source_load - entry_staff
                        if new_target_load >= SEVERE_UNDERUSE_THRESHOLD and new_source_load >= SEVERE_UNDERUSE_THRESHOLD - 1:
                            self.schedule.entries.remove(entry)
                            self.schedule.add_entry(target_slot, entry.activity, entry.troop)
                            self._fill_vacated_slot(entry.troop, source_slot)
                            print(f"  [Underuse Fix] {entry.troop.name}: {entry.activity.name} {source_slot} ({source_load}) -> {target_slot} ({target_load} -> {new_target_load})")
                            improvements += 1
                            moved = True
                            break

            if not moved:
                break # Could not improve, stop to avoid infinite loop

        final_loads = self._calculate_staff_load_by_slot()
        max_final = max(final_loads.values()) if final_loads else 0
        min_final = min(final_loads.values()) if final_loads else 0
        underused_count = sum(1 for load in final_loads.values() if load < SEVERE_UNDERUSE_THRESHOLD)
        print(f"  Final max load: {max_final}, min load: {min_final}, underused slots: {underused_count}")
        if max_final > 16:
            print(f"  WARNING: Still exceeding hard limit of 16 in some slots!")


    def _proactive_cluster_establishment(self):
        """
        Establish cluster seeds for all clustered areas before Top 5 scheduling.

        Uses demand-based seeding with commissioner-day preference so clustered
        activities naturally land on fewer days and require fewer repair swaps later.
        """
        print("\n--- Proactive Cluster Establishment ---")
        import math
        from collections import defaultdict

        cluster_areas = self._get_cluster_areas_map(include_commissioner=False)
        total_established = 0
        day_order = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]

        for area_name, area_activities in cluster_areas.items():
            # Demand pool: top 10 requests in this area that are not yet scheduled.
            demand = []
            for troop in self.troops:
                for activity_name in troop.preferences[:10]:
                    if activity_name not in area_activities:
                        continue
                    activity = get_activity_by_name(activity_name)
                    if not activity or self._troop_has_activity(troop, activity):
                        continue
                    rank = troop.get_priority(activity_name)
                    demand.append((troop, activity, rank))

            if not demand:
                continue

            # Keep only strongest request per troop for this area seed phase.
            best_by_troop = {}
            for troop, activity, rank in demand:
                current = best_by_troop.get(troop.name)
                if current is None or rank < current[2]:
                    best_by_troop[troop.name] = (troop, activity, rank)
            demand = sorted(best_by_troop.values(), key=lambda x: x[2])

            # Required days for current known demand (ceil(n/3)); cap seed spread early.
            required_days = max(1, math.ceil(len(demand) / 3.0))
            target_day_budget = min(3, required_days)

            # Build preferred target days with commissioner alignment first.
            preferred_days = []
            comm_day_counts = defaultdict(int)
            for troop, activity, _ in demand:
                comm_day = self._get_activity_commissioner_day(troop, activity.name)
                if comm_day:
                    comm_day_counts[comm_day] += 1
            for day, _ in sorted(comm_day_counts.items(), key=lambda x: (-x[1], x[0].value)):
                preferred_days.append(day)
            for day in day_order:
                if day not in preferred_days:
                    preferred_days.append(day)
            target_days = preferred_days[:target_day_budget]

            placed_in_area = 0
            # Seed up to one full day-equivalent (3) per area to establish anchor clusters.
            for troop, activity, rank in demand[: max(3, target_day_budget * 2)]:
                if self._troop_has_activity(troop, activity):
                    continue

                placed = False
                for target_day in target_days:
                    day_slots = sorted(
                        [s for s in self.time_slots if s.day == target_day],
                        key=lambda s: s.slot_number
                    )
                    for slot in day_slots:
                        if self._can_schedule(troop, activity, slot, target_day):
                            self._add_to_schedule(slot, activity, troop)
                            placed_in_area += 1
                            total_established += 1
                            placed = True
                            print(
                                f"  [Cluster Seed] {troop.name}: {activity.name} -> "
                                f"{target_day.name}-{slot.slot_number} (#{rank + 1}, {area_name})"
                            )
                            break
                    if placed:
                        break

                if placed_in_area >= 3:
                    break

        print(f"  Established {total_established} cluster seeds")


    def _build_commissioner_busy_map(self):
        """
        Build map of which time slots each commissioner is busy running activities.
        This enables dynamic blocking instead of fixed day assignments.
        """
        self.commissioner_busy_map = {}

        # Activities that require commissioner presence
        commissioner_activities = {
            "Delta", 
            "Super Troop", 
            "Reflection", 
            "Archery"
        }

        # Scan all scheduled entries
        for entry in self.schedule.entries:
            if entry.activity.name in commissioner_activities:
                commissioner = self.troop_commissioner.get(entry.troop.name)
                if commissioner:
                    if commissioner not in self.commissioner_busy_map:
                        self.commissioner_busy_map[commissioner] = set()
                    self.commissioner_busy_map[commissioner].add(entry.time_slot)

        # Log the busy map for transparency
        print(f"  Commissioner busy slots mapped:")
        for commissioner in sorted(self.commissioner_busy_map.keys()):
            busy_slots = sorted(self.commissioner_busy_map[commissioner], 
                              key=lambda s: (s.day.value, s.slot_number))
            slot_str = ", ".join(str(s) for s in busy_slots)
            print(f"    {commissioner}: {slot_str}")


    def _phase_swap_optimization(self):
        """
        Slot Swap Optimization: Find clustering outliers and swap activities between troops.

        An outlier is an activity that breaks an otherwise clean staff cluster for a troop.
        If another troop has a different activity in that slot, we can swap to improve clustering.

        Target areas for clustering: Tower, Rifle Range, Outdoor Skills, Handicrafts
        """
        # Staff areas to optimize for clustering
        # Staff areas to optimize for clustering
        # Dynamic CLUSTER_AREAS based on configuration
        priority_areas = config_loader.get_optimization_rules().get("area_clustering_priority", 
                                        ["Tower", "Rifle Range", "Archery", "Outdoor Skills"])

        CLUSTER_AREAS = {}
        for area_name in priority_areas:
             if area_name in EXCLUSIVE_AREAS:
                  CLUSTER_AREAS[area_name] = EXCLUSIVE_AREAS[area_name]

        # Build reverse mapping: activity -> area
        activity_to_area = {}
        for area, activities in CLUSTER_AREAS.items():
            for act in activities:
                activity_to_area[act] = area

        # Protected activities that should NEVER be swapped
        PROTECTED = {"Delta", "Super Troop", "Reflection", "Archery", 
                     "Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}

        # Track swaps to prevent oscillation
        # Key: (troop_a_name, troop_b_name, slot) -> True
        swapped_pairs = set()

        total_swaps = 0
        max_iterations = 3  # Limit iterations to avoid infinite loops

        for iteration in range(max_iterations):
            swaps_this_iteration = 0

            # For each troop, find clustering outliers
            for troop in self.troops:
                outliers = self._find_clustering_outliers(troop, activity_to_area, PROTECTED)

                if not outliers:
                    continue

                for outlier in outliers:
                    swap_made = self._try_swap_for_outlier(
                        troop, outlier, activity_to_area, PROTECTED, swapped_pairs
                    )
                    if swap_made:
                        swaps_this_iteration += 1
                        total_swaps += 1

            print(f"  Iteration {iteration + 1}: Made {swaps_this_iteration} swap(s)")

            if swaps_this_iteration == 0:
                break  # No more improvements possible

        print(f"  Total slot swaps: {total_swaps}")


    def _find_clustering_outliers(self, troop, activity_to_area, protected):
        """
        Find slots where an activity breaks a cluster OR could extend a cluster for this troop.

        Two types of outliers:
        1. GAP OUTLIER: Activity in slot 2 when slots 1 and 3 have the same cluster area
        2. EXTENSION OPPORTUNITY: Activity adjacent to a cluster that could be swapped to extend it

        Returns list of dicts with slot, outlier_activity, desired_area, desired_activities.
        """
        outliers = []

        # Get troop's schedule by day
        troop_entries = [e for e in self.schedule.entries if e.troop == troop]

        for day in Day:
            day_entries = [e for e in troop_entries if e.time_slot.day == day]
            if len(day_entries) < 2:
                continue  # Need at least 2 activities

            # Sort by slot number
            day_entries.sort(key=lambda e: e.time_slot.slot_number)

            # Create slot -> entry mapping
            slot_to_entry = {e.time_slot.slot_number: e for e in day_entries}

            # Check each target clustering area
            for area, area_activities in EXCLUSIVE_AREAS.items():
                if area not in activity_to_area.values():
                    continue  # Not a target clustering area

                # Find entries in this area
                area_entries = [e for e in day_entries if e.activity.name in area_activities]

                if not area_entries:
                    continue  # No activities in this area on this day

                # CASE 1: Single activity - check if adjacent slot could extend
                if len(area_entries) == 1:
                    cluster_slot = area_entries[0].time_slot.slot_number

                    # Check adjacent slots
                    for adj_slot_num in [cluster_slot - 1, cluster_slot + 1]:
                        if adj_slot_num < 1 or adj_slot_num > 3:
                            continue

                        if adj_slot_num in slot_to_entry:
                            adj_entry = slot_to_entry[adj_slot_num]
                            if adj_entry.activity.name not in area_activities:
                                if adj_entry.activity.name not in protected:
                                    # This could be swapped to extend the cluster
                                    outliers.append({
                                        'slot': adj_entry.time_slot,
                                        'activity': adj_entry.activity,
                                        'desired_area': area,
                                        'desired_activities': area_activities,
                                        'type': 'extension'
                                    })

                # CASE 2: Two+ activities - check for gaps or additional extensions
                elif len(area_entries) >= 2:
                    slots_in_area = sorted([e.time_slot.slot_number for e in area_entries])

                    # Check for gaps between cluster activities
                    for i in range(len(slots_in_area) - 1):
                        gap_start = slots_in_area[i]
                        gap_end = slots_in_area[i + 1]

                        for gap_slot in range(gap_start + 1, gap_end):
                            if gap_slot in slot_to_entry:
                                gap_entry = slot_to_entry[gap_slot]
                                if gap_entry.activity.name not in area_activities:
                                    if gap_entry.activity.name not in protected:
                                        outliers.append({
                                            'slot': gap_entry.time_slot,
                                            'activity': gap_entry.activity,
                                            'desired_area': area,
                                            'desired_activities': area_activities,
                                            'type': 'gap'
                                        })

        return outliers


    def _try_swap_for_outlier(self, troop, outlier, activity_to_area, protected, swapped_pairs):
        """
        Try to find another troop to swap with for this outlier.

        Simplified approach: Try ANY troop that has a different activity in this slot.
        If the swap passes constraints and doesn't hurt either troop too much, do it.

        Args:
            swapped_pairs: Set of (troop_a, troop_b, slot) tuples to prevent re-swapping

        Returns True if a swap was made.
        """
        slot = outlier['slot']
        outlier_activity = outlier['activity']
        desired_activities = outlier['desired_activities']

        # SKIP MULTI-SLOT OUTLIER: Cannot blindly swap multi-slot activities
        if outlier_activity.slots > 1.0:
            return False

        # Find troops that have a DIFFERENT activity in this slot
        for other_troop in self.troops:
            if other_troop == troop:
                continue

            # Find the other troop's entry in this slot
            other_entry = next((e for e in self.schedule.entries 
                               if e.troop == other_troop and e.time_slot == slot), None)

            if not other_entry:
                continue

            other_activity = other_entry.activity

            # SKIP MULTI-SLOT TARGET: Cannot blindly swap multi-slot activities
            if other_activity.slots > 1.0:
                continue

            # Skip if other troop has a protected activity
            if other_activity.name in protected:
                continue

            # Skip if same activity (no point swapping)
            if other_activity.name == outlier_activity.name:
                continue

            # Skip if we've already swapped this pair in this slot (prevent oscillation)
            swap_key = tuple(sorted([troop.name, other_troop.name]) + [str(slot)])
            if swap_key in swapped_pairs:
                continue

            # BONUS: Prefer if other_troop has a desired activity (cluster helper)
            is_cluster_helper = other_activity.name in desired_activities

            # Check if the swap is beneficial for both
            if not self._swap_is_beneficial(troop, other_troop, outlier_activity, other_activity, slot):
                continue

            # Check constraints after swap
            if not self._swap_is_valid(troop, other_troop, outlier_activity, other_activity, slot):
                continue

            # Execute the swap
            self._execute_swap(troop, other_troop, outlier_activity, other_activity, slot)
            swapped_pairs.add(swap_key)  # Track this swap to prevent re-swapping
            cluster_note = " [CLUSTER]" if is_cluster_helper else ""
            print(f"    SWAP{cluster_note}: {troop.name} and {other_troop.name} in {slot}")
            print(f"          {troop.name}: {outlier_activity.name} -> {other_activity.name}")
            print(f"          {other_troop.name}: {other_activity.name} -> {outlier_activity.name}")
            return True

        return False


    def _swap_is_beneficial(self, troop_a, troop_b, activity_a, activity_b, slot):
        """
        Check if swapping is acceptable for both troops.

        Accept the swap if:
        1. Neither troop loses more than 10 preference ranks, AND
        2. Clustering improvement is the primary goal (always beneficial for troop_a)
        """
        # Troop A gets activity_b, Troop B gets activity_a

        # Get preference rankings (lower = better)
        # get_priority returns 999 if not in preferences, None if activity not found
        pref_a_for_a = troop_a.get_priority(activity_a.name)  # Current
        pref_a_for_b = troop_a.get_priority(activity_b.name)  # After swap
        pref_b_for_b = troop_b.get_priority(activity_b.name)  # Current
        pref_b_for_a = troop_b.get_priority(activity_a.name)  # After swap

        # Normalize: treat 999 and None as "not in preferences" = rank 20
        # This is a neutral default - neither good nor bad
        DEFAULT_RANK = 20

        def normalize(rank):
            if rank is None or rank >= 999:
                return DEFAULT_RANK
            return rank

        a_current = normalize(pref_a_for_a)
        a_after = normalize(pref_a_for_b)
        a_change = a_after - a_current  # Negative = improvement

        b_current = normalize(pref_b_for_b)
        b_after = normalize(pref_b_for_a)
        b_change = b_after - b_current  # Negative = improvement

        # Reject if either troop loses more than 10 ranks
        # (this is a significant preference drop)
        if a_change > 10:
            return False
        if b_change > 10:
            return False

        # Accept the swap - clustering improvement justifies it
        return True


    def _swap_is_valid(self, troop_a, troop_b, activity_a, activity_b, slot):
        """
        Check if the swap would violate any hard constraints.
        """
        day = slot.day

        # Check if troop_a already has activity_b on another day
        if self._troop_has_activity(troop_a, activity_b):
            return False

        # Check if troop_b already has activity_a on another day
        if self._troop_has_activity(troop_b, activity_a):
            return False

        # === EXCLUSIVITY CHECK: Multi-slot activities (Tower for 15+ scouts) ===
        # Don't swap into a slot where another troop has a multi-slot activity continuation
        EXCLUSIVE_ACTIVITIES = (
            {"Super Troop", "Delta"}
            | set(EXCLUSIVE_AREAS.get("Tower", []))
            | set(EXCLUSIVE_AREAS.get("Archery", []))
            | set(EXCLUSIVE_AREAS.get("Rifle Range", []))
        )

        if activity_a.name in EXCLUSIVE_ACTIVITIES or activity_b.name in EXCLUSIVE_ACTIVITIES:
            # Check for other troops' exclusive activities in this slot
            other_entries = [e for e in self.schedule.entries 
                           if e.time_slot == slot 
                           and e.troop != troop_a 
                           and e.troop != troop_b
                           and e.activity.name in EXCLUSIVE_ACTIVITIES]
            if other_entries:
                # Can't swap - another troop has an exclusive activity here
                return False

        # Check accuracy constraints (max 1 per day)
        if activity_b.name in self.ACCURACY_ACTIVITIES:
            troop_a_acc = [e for e in self.schedule.entries 
                          if e.troop == troop_a and e.time_slot.day == day 
                          and e.activity.name in self.ACCURACY_ACTIVITIES
                          and e.time_slot != slot]
            if troop_a_acc:
                return False

        if activity_a.name in self.ACCURACY_ACTIVITIES:
            troop_b_acc = [e for e in self.schedule.entries 
                          if e.troop == troop_b and e.time_slot.day == day 
                          and e.activity.name in self.ACCURACY_ACTIVITIES
                          and e.time_slot != slot]
            if troop_b_acc:
                return False

        # Check wet->tower/ODS constraint
        if slot.slot_number > 1:
            prev_slot = [s for s in self.time_slots 
                        if s.day == day and s.slot_number == slot.slot_number - 1][0]

            # Check for troop_a getting activity_b
            if activity_b.name in self.TOWER_ODS_ACTIVITIES:
                prev_a = [e for e in self.schedule.entries 
                         if e.troop == troop_a and e.time_slot == prev_slot]
                if prev_a and prev_a[0].activity.name in self.WET_ACTIVITIES:
                    return False

            # Check for troop_b getting activity_a
            if activity_a.name in self.TOWER_ODS_ACTIVITIES:
                prev_b = [e for e in self.schedule.entries 
                         if e.troop == troop_b and e.time_slot == prev_slot]
                if prev_b and prev_b[0].activity.name in self.WET_ACTIVITIES:
                    return False

        return True


    def _execute_swap(self, troop_a, troop_b, activity_a, activity_b, slot):
        """
        Execute the swap: troop_a gets activity_b, troop_b gets activity_a.
        """
        # Find and remove the entries
        entry_a = None
        entry_b = None

        for entry in self.schedule.entries[:]:  # Copy list for safe removal
            if entry.troop == troop_a and entry.time_slot == slot:
                entry_a = entry
            elif entry.troop == troop_b and entry.time_slot == slot:
                entry_b = entry

        if entry_a:
            self.schedule.entries.remove(entry_a)
        if entry_b:
            self.schedule.entries.remove(entry_b)

        # Add swapped entries
        self.schedule.add_entry(slot, activity_b, troop_a)
        self.schedule.add_entry(slot, activity_a, troop_b)


    def _comprehensive_smart_swaps(self):
        """
        Comprehensive smart swap optimization for ALL activities.

        Goal: Minimize total days used by clustering activities onto fewer days.
        Dynamically finds which days have the most of each activity and consolidates.
        """
        from ...models import ScheduleEntry
        from collections import defaultdict

        print("\n--- Comprehensive Smart Swap Analysis ---")

        # High-value activities that benefit from clustering
        CLUSTER_ACTIVITIES = [
            'Archery', 'Climbing Tower', 'Troop Rifle', 'Troop Shotgun',
            'Knots and Lashings', 'Orienteering', 'GPS & Geocaching', 
            'Ultimate Survivor', 'What\'s Cooking', 'Chopped!'
        ]

        # Protected activities that should never be swapped
        PROTECTED = {"Delta", "Super Troop", "Reflection", 
                    "Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}

        swaps_made = 0
        max_iterations = 3

        for iteration in range(max_iterations):
            iteration_swaps = 0

            # Analyze each cluster activity
            for activity_name in CLUSTER_ACTIVITIES:
                # Find all instances of this activity
                activity_entries = [e for e in self.schedule.entries 
                                   if e.activity.name == activity_name]

                if len(activity_entries) < 2:
                    continue  # Need at least 2 to cluster

                # Count how many troops have this activity on each day
                day_counts = defaultdict(int)
                for entry in activity_entries:
                    day_counts[entry.time_slot.day] += 1

                # Find the top 2 days with most activity (cluster days)
                sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)

                if len(sorted_days) <= 2:
                    continue  # Already on 2 or fewer days - well clustered

                # Get the top 2 cluster days
                cluster_days = [day for day, count in sorted_days[:2]]

                # Find entries NOT on cluster days (outliers)
                outlier_entries = [e for e in activity_entries 
                                  if e.time_slot.day not in cluster_days]

                # Try to move outliers to cluster days
                for entry in outlier_entries:
                    swap_result = self._try_smart_activity_swap(
                        entry, cluster_days, PROTECTED
                    )

                    if swap_result:
                        iteration_swaps += 1
                        swaps_made += 1
                        print(f"  [OK] {entry.troop.name}: {activity_name} " +
                              f"{entry.time_slot.day.name}-{entry.time_slot.slot_number} -> " +
                              f"{swap_result['new_day'].name}-{swap_result['new_slot']}")
                        print(f"    Clustering: {activity_name} now on {len(cluster_days)} days instead of {len(sorted_days)}")

            print(f"  Iteration {iteration + 1}: {iteration_swaps} smart swaps")

            if iteration_swaps == 0:
                break  # No more improvements

        print(f"  Total comprehensive swaps: {swaps_made}")


    def _neutral_beneficial_swaps(self):
        """
        WITHIN-TROOP SLOT SWAPS: Swap any two activities within a troop's schedule
        to improve overall clustering without violating constraints.

        ENHANCED LOGIC:
        1. Area-based clustering (all Outdoor Skills count together, etc.)
        2. Multi-criteria scoring (clustering, preference rank, staff load)
        3. Bi-directional benefit (both activities can benefit from swap)
        4. EXCESS DAY REDUCTION: Heavily weights swaps that reduce excess cluster days
        5. GAP REDUCTION: Heavily weights swaps that fill cluster gaps (slots 1&3 full, slot 2 empty)
        """
        from ...models import ScheduleEntry
        from collections import defaultdict
        import math

        print("\n--- Aggressive Within-Troop Slot Swaps ---")

        # Optimize the same cluster areas official scoring uses. Delta/Super
        # Troop may still be swap targets, but they are not excess-day areas.
        CLUSTER_AREAS = self._get_authoritative_gap_area_map()

        # Build activity -> area mapping
        activity_to_area = {}
        for area, activities in CLUSTER_AREAS.items():
            for act in activities:
                activity_to_area[act] = area

        # Protected activities that should NEVER have their slots swapped
        PROTECTED = {"Reflection", "Sailing",
                     "Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}

        # Exclusive activities (only 1 troop per slot)
        EXCLUSIVE = {"Delta", "Super Troop", "Archery", "Climbing Tower", "Troop Rifle", "Troop Shotgun"}

        # Track swapped pairs to prevent oscillation
        swapped_pairs = set()  # Set of (troop_name, activity1, activity2) tuples

        total_swaps = 0
        max_iterations = 5  # More iterations for cascading improvements

        for iteration in range(max_iterations):
            iteration_swaps = 0
            best_global_swap = None
            best_global_score = 0

            for troop in self.troops:
                troop_entries = [e for e in self.schedule.entries if e.troop == troop]

                # Get entries that are part of cluster areas (worth moving to better days)
                cluster_entries = [e for e in troop_entries 
                                  if e.activity.name in activity_to_area
                                  and e.activity.name not in PROTECTED
                                  and e.activity.slots <= 1.0]  # Only swap single-slot activities

                # Get entries that can be swapped with (not protected)
                swappable_entries = [e for e in troop_entries 
                                    if e.activity.name not in PROTECTED
                                    and e.activity.slots <= 1.0]  # Only swap single-slot activities

                # For each cluster activity, check if swapping with another activity improves clustering
                for cluster_entry in cluster_entries:
                    cluster_activity = cluster_entry.activity.name
                    cluster_area = activity_to_area[cluster_activity]
                    current_slot = cluster_entry.time_slot
                    current_day = current_slot.day

                    # Count AREA-based clustering (how many activities from same area on this day)
                    area_activities = CLUSTER_AREAS[cluster_area]
                    current_area_count = sum(1 for e in self.schedule.entries 
                                            if e.activity.name in area_activities 
                                            and e.time_slot.day == current_day)

                    # Also count exact activity for tighter clustering
                    current_activity_count = sum(1 for e in self.schedule.entries 
                                                if e.activity.name == cluster_activity 
                                                and e.time_slot.day == current_day)

                    for swap_entry in swappable_entries:
                        if swap_entry == cluster_entry:
                            continue

                        swap_slot = swap_entry.time_slot
                        swap_day = swap_slot.day
                        swap_activity = swap_entry.activity.name

                        if swap_day == current_day:
                            continue  # Same day, no clustering improvement
                        if not self._family_policy_allows_day(cluster_activity, swap_day, strict=True):
                            continue
                        if not self._family_policy_allows_day(swap_activity, current_day, strict=True):
                            continue

                        # Check if this pair was already swapped (prevent oscillation)
                        pair_key = tuple(sorted([cluster_activity, swap_activity]))
                        if (troop.name, pair_key) in swapped_pairs:
                            continue

                        # Check if entries still exist
                        if cluster_entry not in self.schedule.entries:
                            break
                        if swap_entry not in self.schedule.entries:
                            continue

                        # Calculate improvement scores with EXCESS DAY and GAP analysis

                        # Helper: Calculate excess days for an area
                        def calc_excess_days(area_name, area_acts):
                            area_entries = [e for e in self.schedule.entries 
                                           if e.activity.name in area_acts]
                            if not area_entries:
                                return 0
                            days_used = set(e.time_slot.day for e in area_entries)
                            num_activities = len(area_entries)
                            min_days = math.ceil(num_activities / 3.0)
                            return max(0, len(days_used) - min_days)

                        # Helper: Check if removing an entry from a day reduces excess days
                        def would_remove_excess_day(area_name, area_acts, day, entry_to_remove):
                            # Calculate current excess
                            current_excess = calc_excess_days(area_name, area_acts)
                            if current_excess == 0:
                                return False  # No excess to reduce

                            # Check if this day is currently excess
                            area_entries = [e for e in self.schedule.entries 
                                          if e.activity.name in area_acts]
                            days_used = set(e.time_slot.day for e in area_entries)
                            if day not in days_used:
                                return False  # Day not used, can't be excess

                            # Count activities on this day
                            activities_on_day = sum(1 for e in area_entries if e.time_slot.day == day)
                            if activities_on_day <= 1:
                                # Removing this would remove the day entirely
                                # Recalculate excess after removal
                                temp_entries = [e for e in area_entries if e != entry_to_remove]
                                if not temp_entries:
                                    return False
                                temp_days = set(e.time_slot.day for e in temp_entries)
                                temp_min = math.ceil(len(temp_entries) / 3.0)
                                temp_excess = max(0, len(temp_days) - temp_min)
                                return temp_excess < current_excess

                            return False  # Day has other activities, won't reduce excess

                        # Helper: Check for cluster gap (slots 1&3 full, slot 2 empty) for an area on a day
                        def has_cluster_gap(area_name, area_acts, day, troop):
                            troop_entries = [e for e in self.schedule.entries 
                                           if e.troop == troop and e.time_slot.day == day]
                            slots_filled = {e.time_slot.slot_number for e in troop_entries 
                                          if e.activity.name in area_acts}
                            # Check if slots 1 and 3 are filled but slot 2 is empty
                            return 1 in slots_filled and 3 in slots_filled and 2 not in slots_filled

                        # 1. EXCESS DAY REDUCTION: Does moving cluster_activity reduce excess days?
                        excess_reduction_cluster = 0
                        if cluster_area in CLUSTER_AREAS:
                            current_excess = calc_excess_days(cluster_area, area_activities)
                            # Check if removing from current_day and adding to swap_day reduces excess
                            if would_remove_excess_day(cluster_area, area_activities, current_day, cluster_entry):
                                excess_reduction_cluster = 1  # Removing from excess day
                            # Check if swap_day already has this area (won't create new excess)
                            swap_day_has_area = any(e.activity.name in area_activities 
                                                   and e.time_slot.day == swap_day 
                                                   and e != cluster_entry
                                                   for e in self.schedule.entries)
                            if swap_day_has_area:
                                excess_reduction_cluster += 1  # Moving to existing day

                        # 2. GAP REDUCTION: Does moving cluster_activity fill a cluster gap?
                        gap_reduction_cluster = 0
                        if cluster_area in CLUSTER_AREAS:
                            # Check if swap_day has a cluster gap that this would fill
                            if has_cluster_gap(cluster_area, area_activities, swap_day, troop):
                                # Check if cluster_activity would fill slot 2
                                if swap_slot.slot_number == 2:
                                    gap_reduction_cluster = 2  # Fills cluster gap (high value)

                        # 3. Area-based clustering for cluster_activity on target day
                        target_area_count = sum(1 for e in self.schedule.entries 
                                               if e.activity.name in area_activities 
                                               and e.time_slot.day == swap_day
                                               and e != cluster_entry)
                        area_improvement = target_area_count - current_area_count + 1  # +1 for moving there

                        # 4. Exact activity clustering on target day
                        target_activity_count = sum(1 for e in self.schedule.entries 
                                                   if e.activity.name == cluster_activity 
                                                   and e.time_slot.day == swap_day
                                                   and e != cluster_entry)
                        activity_improvement = target_activity_count - current_activity_count + 1

                        # 5. Bi-directional: Does the swap_activity ALSO benefit from this swap?
                        swap_area = activity_to_area.get(swap_activity)
                        bidirectional_excess_reduction = 0
                        bidirectional_gap_reduction = 0
                        bidirectional_area_improvement = 0

                        if swap_area:
                            swap_area_activities = CLUSTER_AREAS[swap_area]

                            # Excess day reduction for swap_activity
                            if swap_area in CLUSTER_AREAS:
                                if would_remove_excess_day(swap_area, swap_area_activities, swap_day, swap_entry):
                                    bidirectional_excess_reduction = 1
                                # Check if current_day already has this area
                                current_day_has_area = any(e.activity.name in swap_area_activities 
                                                          and e.time_slot.day == current_day 
                                                          and e != swap_entry
                                                          for e in self.schedule.entries)
                                if current_day_has_area:
                                    bidirectional_excess_reduction += 1

                            # Gap reduction for swap_activity
                            if swap_area in CLUSTER_AREAS:
                                if has_cluster_gap(swap_area, swap_area_activities, current_day, troop):
                                    if current_slot.slot_number == 2:
                                        bidirectional_gap_reduction = 2

                            # Area improvement for swap_activity
                            swap_current_area = sum(1 for e in self.schedule.entries 
                                                   if e.activity.name in swap_area_activities 
                                                   and e.time_slot.day == swap_day
                                                   and e != swap_entry)
                            swap_target_area = sum(1 for e in self.schedule.entries 
                                                  if e.activity.name in swap_area_activities 
                                                  and e.time_slot.day == current_day
                                                  and e != cluster_entry)
                            bidirectional_area_improvement = swap_target_area - swap_current_area

                        # Combined score (weighted heavily for excess day and gap reduction)
                        # Excess day reduction is HUGE (50 points each) - reduces penalty by 8 points
                        # Gap reduction is also HUGE (30 points) - reduces penalty by 12 points
                        score = (activity_improvement * 3) + (area_improvement * 2) + \
                                (excess_reduction_cluster * 50) + (gap_reduction_cluster * 30) + \
                                (bidirectional_excess_reduction * 50) + (bidirectional_gap_reduction * 30) + \
                                (bidirectional_area_improvement * 2)

                        # Only proceed if there's some benefit
                        if score <= 0:
                            continue

                        # Intra-troop swap scoring: relax soft rules; only bypass day-request
                        # checks when troop has no day_requests (MUST-HONOR otherwise).
                        ign_dr = self._optimization_may_ignore_day_requests(troop)
                        can_move_cluster = self._can_schedule(
                            troop, cluster_entry.activity, swap_slot, swap_day,
                            relax_constraints=True, ignore_day_requests=ign_dr,
                        )
                        can_move_swap = self._can_schedule(
                            troop, swap_entry.activity, current_slot, current_day,
                            relax_constraints=True, ignore_day_requests=ign_dr,
                        )

                        # Both must be valid - constraint compliance is mandatory
                        valid = can_move_cluster and can_move_swap

                        # Additional check: Ensure no exclusive conflicts after swap
                        if valid:
                            # Temporarily check exclusivity
                            temp_entries = [e for e in self.schedule.entries 
                                          if e != cluster_entry and e != swap_entry]
                            # Check if swap_slot would have exclusive conflict for cluster_activity
                            if cluster_activity in EXCLUSIVE:
                                conflicts = [e for e in temp_entries 
                                            if e.activity.name == cluster_activity 
                                            and e.time_slot == swap_slot]
                                if conflicts:
                                    valid = False

                            # Check if current_slot would have exclusive conflict for swap_activity
                            if valid and swap_activity in EXCLUSIVE:
                                conflicts = [e for e in temp_entries 
                                            if e.activity.name == swap_activity 
                                            and e.time_slot == current_slot]
                                if conflicts:
                                    valid = False

                        if valid and score > best_global_score:
                            best_global_swap = {
                                'troop': troop,
                                'cluster_entry': cluster_entry,
                                'swap_entry': swap_entry,
                                'cluster_activity': cluster_activity,
                                'swap_activity': swap_activity,
                                'current_slot': current_slot,
                                'swap_slot': swap_slot,
                                'score': score,
                                'activity_gain': activity_improvement,
                                'area_gain': area_improvement,
                                'excess_reduction_cluster': excess_reduction_cluster,
                                'gap_reduction_cluster': gap_reduction_cluster,
                                'bidirectional_excess': bidirectional_excess_reduction,
                                'bidirectional_gap': bidirectional_gap_reduction,
                                'bidirectional_area': bidirectional_area_improvement
                            }
                            best_global_score = score

            # Execute the best global swap for this iteration
            if best_global_swap:
                s = best_global_swap
                troop = s['troop']
                cluster_entry = s['cluster_entry']
                swap_entry = s['swap_entry']

                # Double-check entries still exist
                if cluster_entry in self.schedule.entries and swap_entry in self.schedule.entries:
                    # FINAL VALIDATION: Use full _can_schedule before executing swap
                    # Constraint compliance is MANDATORY - no exceptions
                    can_move_cluster = self._can_schedule(troop, cluster_entry.activity, s['swap_slot'], 
                                                        s['swap_slot'].day, relax_constraints=False)
                    can_move_swap = self._can_schedule(troop, swap_entry.activity, s['current_slot'],
                                                      s['current_slot'].day, relax_constraints=False)

                    if not (can_move_cluster and can_move_swap):
                        # Constraint violation detected - skip this swap
                        continue

                    self.schedule.entries.remove(cluster_entry)
                    self.schedule.entries.remove(swap_entry)

                    new_cluster = ScheduleEntry(time_slot=s['swap_slot'], activity= cluster_entry.activity, troop= troop)
                    new_swap = ScheduleEntry(time_slot=s['current_slot'], activity= swap_entry.activity, troop= troop)

                    self.schedule.entries.append(new_cluster)
                    self.schedule.entries.append(new_swap)

                    iteration_swaps += 1
                    total_swaps += 1

                    # Track this pair to prevent oscillation
                    pair_key = tuple(sorted([s['cluster_activity'], s['swap_activity']]))
                    swapped_pairs.add((troop.name, pair_key))

                    details = []
                    if s.get('activity_gain', 0) > 0:
                        details.append(f"activity +{s['activity_gain']}")
                    if s.get('area_gain', 0) > 0:
                        details.append(f"area +{s['area_gain']}")
                    if s.get('excess_reduction_cluster', 0) > 0:
                        details.append(f"excess -{s['excess_reduction_cluster']}")
                    if s.get('gap_reduction_cluster', 0) > 0:
                        details.append(f"gap -{s['gap_reduction_cluster']}")
                    if s.get('bidirectional_excess', 0) > 0:
                        details.append(f"bidir-excess -{s['bidirectional_excess']}")
                    if s.get('bidirectional_gap', 0) > 0:
                        details.append(f"bidir-gap -{s['bidirectional_gap']}")
                    if s.get('bidirectional_area', 0) > 0:
                        details.append(f"bidir-area +{s['bidirectional_area']}")

                    print(f"  [WITHIN-TROOP] {troop.name}: {s['cluster_activity']} <-> {s['swap_activity']}")
                    print(f"    {s['current_slot']} <-> {s['swap_slot']} (score={s['score']}, {', '.join(details)})")
                    print(f"    HUGE BENEFIT: Excess day reduction + Gap reduction!")

            print(f"  Iteration {iteration + 1}: {iteration_swaps} within-troop swaps")

            if iteration_swaps == 0:
                break

        print(f"  Total within-troop swaps: {total_swaps}")

        # NEW: AGGRESSIVE WITHIN-TROOP SWAPS for excess day reduction
        # This finds swaps like: BH Archery (Mon) <-> BH Hemp Craft (Wed)
        # If other Archery on Wed and other Hemp Craft on Mon, swap consolidates both areas
        print("\n--- Aggressive Within-Troop Swaps for Excess Day Reduction ---")
        excess_reduction_swaps = self._aggressive_excess_day_reduction_swaps()
        print(f"  Total excess day reduction swaps: {excess_reduction_swaps}")

        # AGGRESSIVE PASS: Look for swaps that specifically reduce excess days or fill gaps
        # Even if overall score is lower, these are huge wins
        print("\n--- Aggressive Excess Day & Gap Reduction Pass ---")
        aggressive_swaps = 0

        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]

            # Get all cluster activities
            cluster_entries = [e for e in troop_entries 
                              if e.activity.name in activity_to_area
                              and e.activity.name not in PROTECTED
                              and e.activity.slots <= 1.0]

            swappable_entries = [e for e in troop_entries 
                                if e.activity.name not in PROTECTED
                                and e.activity.slots <= 1.0]

            for cluster_entry in cluster_entries:
                cluster_activity = cluster_entry.activity.name
                cluster_area = activity_to_area[cluster_activity]
                current_slot = cluster_entry.time_slot
                current_day = current_slot.day
                area_activities = CLUSTER_AREAS[cluster_area]

                # Check if removing this would reduce excess days
                def would_remove_excess(entry):
                    area_entries = [e for e in self.schedule.entries 
                                  if e.activity.name in area_activities]
                    if not area_entries:
                        return False
                    days_used = set(e.time_slot.day for e in area_entries)
                    num_activities = len(area_entries)
                    min_days = math.ceil(num_activities / 3.0)
                    current_excess = max(0, len(days_used) - min_days)

                    if current_excess == 0:
                        return False

                    activities_on_day = sum(1 for e in area_entries if e.time_slot.day == entry.time_slot.day)
                    if activities_on_day <= 1:
                        temp_entries = [e for e in area_entries if e != entry]
                        if not temp_entries:
                            return False
                        temp_days = set(e.time_slot.day for e in temp_entries)
                        temp_min = math.ceil(len(temp_entries) / 3.0)
                        temp_excess = max(0, len(temp_days) - temp_min)
                        return temp_excess < current_excess
                    return False

                # Check if this would fill a cluster gap
                def would_fill_gap(entry, target_day, target_slot):
                    if target_slot.slot_number != 2:
                        return False
                    target_entries = [e for e in troop_entries if e.time_slot.day == target_day]
                    slots_filled = {e.time_slot.slot_number for e in target_entries 
                                  if e.activity.name in area_activities}
                    return 1 in slots_filled and 3 in slots_filled and 2 not in slots_filled

                removes_excess = would_remove_excess(cluster_entry)

                for swap_entry in swappable_entries:
                    if swap_entry == cluster_entry:
                        continue

                    swap_slot = swap_entry.time_slot
                    swap_day = swap_slot.day

                    if swap_day == current_day:
                        continue

                    # Check if this swap would fill a gap
                    fills_gap = would_fill_gap(cluster_entry, swap_day, swap_slot)
                    swap_removes_excess = would_remove_excess(swap_entry)

                    # Only proceed if there's a clear, significant benefit
                    # Priority: gap filling > excess reduction (both activities) > single excess reduction
                    clear_benefit = False
                    if fills_gap:
                        clear_benefit = True  # Filling gap is always valuable
                    elif removes_excess and swap_removes_excess:
                        clear_benefit = True  # Both reduce excess - huge win
                    elif removes_excess or swap_removes_excess:
                        # Single excess reduction - proceed
                        clear_benefit = True

                    if clear_benefit:
                        # Validate constraints - use strict validation to prevent violations
                        can_move_cluster = self._can_schedule(troop, cluster_entry.activity, swap_slot, swap_day,
                                                              relax_constraints=False)  # Strict - no violations
                        can_move_swap = self._can_schedule(troop, swap_entry.activity, current_slot, current_day,
                                                            relax_constraints=False)  # Strict - no violations

                        if can_move_cluster and can_move_swap:
                            # Execute swap temporarily to validate
                            self.schedule.entries.remove(cluster_entry)
                            self.schedule.entries.remove(swap_entry)

                            new_cluster = ScheduleEntry(time_slot=swap_slot, activity= cluster_entry.activity, troop= troop)
                            new_swap = ScheduleEntry(time_slot=current_slot, activity= swap_entry.activity, troop= troop)

                            self.schedule.entries.append(new_cluster)
                            self.schedule.entries.append(new_swap)

                            # POST-SWAP VALIDATION: Ensure no hard constraint violations
                            # Check for same-day conflicts
                            swap_day_acts = [e.activity.name for e in self.schedule.entries 
                                           if e.troop == troop and e.time_slot.day == swap_day]
                            current_day_acts = [e.activity.name for e in self.schedule.entries 
                                               if e.troop == troop and e.time_slot.day == current_day]

                            # Check Delta+Tower/ODS conflicts
                            TOWER_ODS = EXCLUSIVE_AREAS.get("Tower", []) + EXCLUSIVE_AREAS.get("Outdoor Skills", [])
                            has_delta_swap = "Delta" in swap_day_acts
                            has_tower_ods_swap = any(a in TOWER_ODS for a in swap_day_acts)
                            has_delta_current = "Delta" in current_day_acts
                            has_tower_ods_current = any(a in TOWER_ODS for a in current_day_acts)

                            # Check Rifle+Shotgun conflicts
                            has_rifle_swap = "Troop Rifle" in swap_day_acts
                            has_shotgun_swap = "Troop Shotgun" in swap_day_acts
                            has_rifle_current = "Troop Rifle" in current_day_acts
                            has_shotgun_current = "Troop Shotgun" in current_day_acts

                            # Check accuracy limit (max 1 of Rifle/Shotgun/Archery per day)
                            ACCURACY = self.ACCURACY_ACTIVITIES
                            accuracy_swap = sum(1 for a in swap_day_acts if a in ACCURACY)
                            accuracy_current = sum(1 for a in current_day_acts if a in ACCURACY)

                            # Validate no violations
                            valid_swap = True
                            if (has_delta_swap and has_tower_ods_swap) or (has_delta_current and has_tower_ods_current):
                                valid_swap = False
                            if (has_rifle_swap and has_shotgun_swap) or (has_rifle_current and has_shotgun_current):
                                valid_swap = False
                            if accuracy_swap > 1 or accuracy_current > 1:
                                valid_swap = False

                            if not valid_swap:
                                # Revert swap
                                self.schedule.entries.remove(new_cluster)
                                self.schedule.entries.remove(new_swap)
                                self.schedule.entries.append(cluster_entry)
                                self.schedule.entries.append(swap_entry)
                                continue

                            aggressive_swaps += 1
                            benefits = []
                            if removes_excess:
                                benefits.append("reduces excess day")
                            if fills_gap:
                                benefits.append("fills cluster gap")
                            if swap_removes_excess:
                                benefits.append("swap reduces excess")

                            print(f"  [AGGRESSIVE] {troop.name}: {cluster_activity} <-> {swap_entry.activity.name} "
                                  f"({current_day.name[:3]}-{current_slot.slot_number} <-> {swap_day.name[:3]}-{swap_slot.slot_number}) "
                                  f"[{', '.join(benefits)}]")
                            break  # One swap per cluster entry

        if aggressive_swaps > 0:
            print(f"  Made {aggressive_swaps} aggressive excess/gap reduction swaps")


    def _optimize_outlier_activities(self):
        """
        Identify and optimize outlier activities:
        - Activities that are non-back-to-back (isolated, not adjacent to other activities)
        - Activities that are the only instance of that activity type on a day

        Strategy:
        1. Move to existing days where that activity already exists (clustering)
        2. Fill gaps (especially cluster gaps: slots 1&3 full, slot 2 empty)
        3. Create consecutiveness (move adjacent to other activities)

        Constraint compliance is MANDATORY - all moves must pass _can_schedule.
        """
        from ...models import ScheduleEntry
        from collections import defaultdict
        import math

        print("\n--- Outlier Activity Optimization ---")

        # Protected activities should never be moved in outlier optimization.
        PROTECTED = (
            set(self.NON_DISPLACEABLE_ACTIVITIES)
            | set(self.THREE_HOUR_ACTIVITIES)
            | {"Sailing"}
        )

        # Passive fillers should not drive outlier optimization.
        FILL_ACTIVITIES = {
            n
            for n in config_loader.get_activities_with_tag("fill")
            if config_loader.get_staff_need(n) <= 0
        }

        outliers = []

        # Step 1: Identify outlier activities
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]

            # Group by day
            by_day = defaultdict(list)
            for e in troop_entries:
                by_day[e.time_slot.day].append(e)

            for day, entries in by_day.items():
                # Sort by slot number
                entries.sort(key=lambda e: e.time_slot.slot_number)

                for entry in entries:
                    activity_name = entry.activity.name

                    # Skip protected and fill activities
                    if activity_name in PROTECTED or activity_name in FILL_ACTIVITIES:
                        continue

                    # BRAIN §11: never move a Sailing-paired Delta as an outlier.
                    if self._is_pair_protected_delta(entry):
                        continue

                    # Skip multi-slot activities (they're handled separately)
                    if entry.activity.slots > 1.0:
                        continue

                    slot_num = entry.time_slot.slot_number
                    is_outlier = False
                    outlier_reason = []

                    # Check 1: Is it non-back-to-back? (isolated, not adjacent to other activities)
                    adjacent_slots = []
                    if slot_num > 1:
                        adjacent_slots.append(slot_num - 1)
                    max_slot = 2 if day == Day.THURSDAY else 3
                    if slot_num < max_slot:
                        adjacent_slots.append(slot_num + 1)

                    has_adjacent = any(e.time_slot.slot_number in adjacent_slots 
                                     for e in entries if e != entry)
                    if not has_adjacent:
                        is_outlier = True
                        outlier_reason.append("non-back-to-back")

                    # Check 2: Is it the only instance of this activity on this day?
                    same_activity_count = sum(1 for e in self.schedule.entries 
                                            if e.activity.name == activity_name 
                                            and e.time_slot.day == day)
                    if same_activity_count == 1:
                        is_outlier = True
                        outlier_reason.append("only-on-day")

                    if is_outlier:
                        outliers.append({
                            'entry': entry,
                            'troop': troop,
                            'activity': entry.activity,
                            'current_day': day,
                            'current_slot': entry.time_slot,
                            'reasons': outlier_reason
                        })

        print(f"  Found {len(outliers)} outlier activities")

        if not outliers:
            print("  No outlier activities to optimize")
            return

        moves_made = 0

        # Step 2: Try to optimize each outlier
        debug_count = 0
        for outlier in outliers:
            entry = outlier['entry']
            troop = outlier['troop']
            activity = outlier['activity']
            current_day = outlier['current_day']
            current_slot = outlier['current_slot']
            activity_name = activity.name

            # Skip if entry no longer exists
            if entry not in self.schedule.entries:
                continue

            best_move = None
            best_score = -999
            debug_attempts = 0
            debug_blocked = 0

            # Strategy 1: Move to existing day where this activity already exists (clustering)
            activity_days = defaultdict(int)
            for e in self.schedule.entries:
                if e.activity.name == activity_name and e != entry:
                    activity_days[e.time_slot.day] += 1

            for target_day, count in activity_days.items():
                if target_day == current_day:
                    continue

                # Try each slot on target day
                max_slot = 2 if target_day == Day.THURSDAY else 3
                for slot_num in range(1, max_slot + 1):
                    target_slot = TimeSlot(day=target_day, slot_number=slot_num)

                    # Check if troop is free and activity can be scheduled
                    debug_attempts += 1
                    if not self.schedule.is_troop_free(target_slot, troop):
                        debug_blocked += 1
                        continue

                    ign_dr = self._optimization_may_ignore_day_requests(troop)
                    if not self._can_schedule(
                        troop, activity, target_slot, target_day,
                        relax_constraints=True, ignore_day_requests=ign_dr,
                    ):
                        debug_blocked += 1
                        continue

                    # Score: Higher count = better clustering
                    score = count * 10

                    if score > best_score:
                        best_move = {
                            'target_slot': target_slot,
                            'target_day': target_day,
                            'score': score,
                            'reason': f"clustering (day has {count} {activity_name})"
                        }
                        best_score = score

            # Strategy 2: Fill official area-level cluster gaps (slots 1&3 full, slot 2 empty)
            CLUSTER_AREAS = self._get_authoritative_gap_area_map()

            # Find which area this activity belongs to
            activity_area = None
            for area, activities in CLUSTER_AREAS.items():
                if activity_name in activities:
                    activity_area = area
                    break

            if activity_area:
                # Check all days for cluster gaps
                for day in Day:
                    if day == current_day:
                        continue

                    max_slot = 2 if day == Day.THURSDAY else 3
                    if max_slot < 3:
                        continue  # Thursday only has 2 slots, can't have 1-3-2 gap

                    # Check if this day has an official area-level cluster gap.
                    day_entries = [e for e in self.schedule.entries if e.time_slot.day == day]
                    area_activities = CLUSTER_AREAS[activity_area]
                    slots_filled = {e.time_slot.slot_number for e in day_entries
                                  if e.activity.name in area_activities}

                    # Check for cluster gap (slots 1&3 full, slot 2 empty)
                    if 1 in slots_filled and 3 in slots_filled and 2 not in slots_filled:
                        # Try slot 2
                        target_slot = TimeSlot(day=day, slot_number=2)
                        if self.schedule.is_troop_free(target_slot, troop):
                            ign_dr = self._optimization_may_ignore_day_requests(troop)
                            if self._can_schedule(
                                troop, activity, target_slot, day,
                                relax_constraints=True, ignore_day_requests=ign_dr,
                            ):
                                score = 50  # High value for filling cluster gap
                                if score > best_score:
                                    best_move = {
                                        'target_slot': target_slot,
                                        'target_day': day,
                                        'score': score,
                                        'reason': f"fill cluster gap ({activity_area})"
                                    }
                                    best_score = score

            # Strategy 3: Create consecutiveness (move adjacent to other activities)
            for day in Day:
                if day == current_day:
                    continue

                max_slot = 2 if day == Day.THURSDAY else 3
                troop_entries_day = [e for e in self.schedule.entries 
                                   if e.troop == troop and e.time_slot.day == day]

                if not troop_entries_day:
                    continue  # No activities on this day, can't create consecutiveness

                filled_slots = {e.time_slot.slot_number for e in troop_entries_day}

                # Try slots adjacent to existing activities
                for slot_num in range(1, max_slot + 1):
                    if slot_num in filled_slots:
                        continue

                    # Check if adjacent to existing activity
                    is_adjacent = (slot_num - 1 in filled_slots) or (slot_num + 1 in filled_slots)
                    if not is_adjacent:
                        continue

                    target_slot = TimeSlot(day=day, slot_number=slot_num)
                    if not self.schedule.is_troop_free(target_slot, troop):
                        continue

                    ign_dr = self._optimization_may_ignore_day_requests(troop)
                    if not self._can_schedule(
                        troop, activity, target_slot, day,
                        relax_constraints=True, ignore_day_requests=ign_dr,
                    ):
                        continue

                    # Score based on how many adjacent activities
                    adjacent_count = sum(1 for s in [slot_num - 1, slot_num + 1] if s in filled_slots)
                    score = 20 + (adjacent_count * 5)

                    if score > best_score:
                        best_move = {
                            'target_slot': target_slot,
                            'target_day': day,
                            'score': score,
                            'reason': f"create consecutiveness ({adjacent_count} adjacent)"
                        }
                        best_score = score

            # Execute best move if found
            if best_move and best_score > 0:
                # Remove old entry
                self.schedule.entries.remove(entry)

                # Add to new slot
                new_entry = ScheduleEntry(time_slot=best_move['target_slot'], activity= activity, troop= troop)
                self.schedule.entries.append(new_entry)

                moves_made += 1
                print(f"  [Outlier] {troop.name}: {activity_name} {current_day.name[:3]}-{current_slot.slot_number} -> "
                      f"{best_move['target_day'].name[:3]}-{best_move['target_slot'].slot_number} "
                      f"({best_move['reason']}, score={best_score})")

                # Fill vacated slot
                self._fill_vacated_slot(troop, current_slot)
            else:
                # Debug: Why no move found?
                debug_count += 1
                if debug_count <= 5:  # Only show first 5 for brevity
                    if debug_attempts > 0:
                        print(f"  [Debug] {troop.name}: {activity_name} ({outlier['reasons']}) - "
                              f"attempted {debug_attempts} moves, {debug_blocked} blocked by constraints")

        if moves_made > 0:
            print(f"  Optimized {moves_made} outlier activities")
        else:
            print(f"  No beneficial moves found for {len(outliers)} outlier activities")


    def _try_smart_activity_swap(self, entry, ideal_days, protected):
        """
        Try to swap an activity to an ideal day.

        ENHANCED: Now scores swaps based on:
        - Staff load balancing (fewer days per staff area = better)
        - Wet constraint compliance (avoid tower after beach)
        - Preference rank improvement

        Returns dict with swap details if successful, None otherwise.
        """
        from ...models import ScheduleEntry
        from collections import defaultdict

        # Map activities to their staff areas for load calculation
        STAFF_AREA_MAP = {
            'Climbing Tower': 'Tower',
            'Archery': 'Archery',
            'Troop Rifle': 'Rifle Range',
            'Troop Shotgun': 'Rifle Range',
            'Knots and Lashings': 'Outdoor Skills',
            'Orienteering': 'Outdoor Skills',
            'GPS & Geocaching': 'Outdoor Skills',
            'Ultimate Survivor': 'Outdoor Skills',
            "What's Cooking": 'Outdoor Skills',
            'Chopped!': 'Outdoor Skills',
            'Hemp Craft': 'Handicrafts',
            'Leather Craft': 'Handicrafts',
            'Tie Dye': 'Handicrafts',
        }

        troop = entry.troop
        activity = entry.activity
        current_slot = entry.time_slot

        # Store candidate swaps with scores
        candidates = []

        # Try each ideal day
        for ideal_day in ideal_days:
            if ideal_day == current_slot.day:
                continue  # Already on this day

            # Get all slots on ideal day
            ideal_day_slots = [s for s in self.time_slots if s.day == ideal_day]

            for target_slot in ideal_day_slots:
                # Check what troop currently has in target slot
                target_entry = next(
                    (e for e in self.schedule.entries 
                     if e.troop == troop and e.time_slot == target_slot),
                    None
                )

                if not target_entry:
                    continue  # Slot is empty (shouldn't happen)

                # Don't swap protected activities
                if target_entry.activity.name in protected:
                    continue

                # CRITICAL FIX: Don't swap OUT multi-slot activities (they break if moved to end of day)
                if target_entry.activity.slots > 1.0:
                    continue
                if activity.slots > 1.0:
                    continue

                # Calculate preference ranks
                activity_rank = troop.get_priority(activity.name) or 999
                target_rank = troop.get_priority(target_entry.activity.name) or 999

                # Only swap if target activity is lower or equal priority
                if target_rank < activity_rank:
                    continue  # Don't swap out higher priority

                # Try the swap
                self.schedule.entries.remove(entry)
                self.schedule.entries.remove(target_entry)

                new_entry = ScheduleEntry(
                    time_slot=target_slot,
                    activity=activity,
                    troop=troop
                )
                swapped_entry = ScheduleEntry(
                    time_slot=current_slot,
                    activity=target_entry.activity,
                    troop=troop
                )

                self.schedule.entries.append(new_entry)
                self.schedule.entries.append(swapped_entry)

                # Validate constraints
                valid = self._validate_swap_constraints(troop, new_entry, swapped_entry)

                if not valid:
                    # Revert
                    self.schedule.entries.remove(new_entry)
                    self.schedule.entries.remove(swapped_entry)
                    self.schedule.entries.append(entry)
                    self.schedule.entries.append(target_entry)
                    continue

                # Calculate swap score (higher = better)
                score = 0

                # 1. Staff load balancing score
                staff_area = STAFF_AREA_MAP.get(activity.name)
                if staff_area:
                    # Count days this staff area is used AFTER the swap
                    area_days = set()
                    for e in self.schedule.entries:
                        if STAFF_AREA_MAP.get(e.activity.name) == staff_area:
                            area_days.add(e.time_slot.day)

                    # Fewer days = better clustering = higher score
                    # Max score of 50 for perfect clustering (1 day)
                    days_used = len(area_days)
                    if days_used > 0:
                        score += (50 / days_used)

                # 2. Wet constraint bonus
                # Reward swaps that avoid wet→tower violations
                if activity.name in self.TOWER_ODS_ACTIVITIES:
                    # Check if we're moving AWAY from a wet slot (good!)
                    if self._has_wet_before_slot(troop, current_slot) or self._has_wet_after_slot(troop, current_slot):
                        score += 20  # Bonus for avoiding wet violation

                if target_entry.activity.name in self.WET_ACTIVITIES:
                    # Moving wet activity to current slot - check if safe
                    if not (self._has_tower_ods_before_slot(troop, current_slot) or self._has_tower_ods_after_slot(troop, current_slot)):
                        score += 10  # Bonus for safe wet placement

                # 3. Clustering bonus (moving to ideal day)
                score += 30  # Base bonus for clustering

                # 4. Preference improvement bonus
                if target_rank > activity_rank:
                    score += (target_rank - activity_rank)  # Small bonus for preference improvement

                # Store candidate with score
                candidates.append({
                    'new_entry': new_entry,
                    'swapped_entry': swapped_entry,
                    'original_entry': entry,
                    'original_target': target_entry,
                    'new_day': ideal_day,
                    'new_slot': target_slot.slot_number,
                    'score': score,
                    'target_name': target_entry.activity.name
                })

                # Revert for now (will apply best candidate later)
                self.schedule.entries.remove(new_entry)
                self.schedule.entries.remove(swapped_entry)
                self.schedule.entries.append(entry)
                self.schedule.entries.append(target_entry)

        # Select best candidate by score
        if not candidates:
            return None

        best = max(candidates, key=lambda x: x['score'])

        # Apply the best swap
        self.schedule.entries.remove(best['original_entry'])
        self.schedule.entries.remove(best['original_target'])
        self.schedule.entries.append(best['new_entry'])
        self.schedule.entries.append(best['swapped_entry'])

        reason = f"Moved {activity.name} to ideal day (score: {best['score']:.1f}), swapped with {best['target_name']}"
        return {
            'new_day': best['new_day'],
            'new_slot': best['new_slot'],
            'reason': reason,
            'score': best['score']
        }

        return None


    def _validate_swap_constraints(self, troop, new_entry, swapped_entry):
        """
        COMPREHENSIVE constraint validation for swaps using _can_schedule.
        This ensures ALL hard constraints are checked before executing any swap.
        Constraint compliance is MANDATORY - no exceptions.
        """
        # Use full _can_schedule validation for both activities
        # This checks ALL constraints: exclusivity, wet/dry patterns, beach slots, 
        # capacity limits, same-day conflicts, staff limits, etc.
        can_move_new = self._can_schedule(troop, new_entry.activity, new_entry.time_slot, 
                                         new_entry.time_slot.day, relax_constraints=False)
        can_move_swapped = self._can_schedule(troop, swapped_entry.activity, swapped_entry.time_slot,
                                             swapped_entry.time_slot.day, relax_constraints=False)

        # Both must pass - constraint compliance is non-negotiable
        if not (can_move_new and can_move_swapped):
            return False

        # Additional check: Ensure no duplicate activities after swap
        # (This is already checked in _can_schedule, but double-check for safety)
        troop_activities_after = [e.activity.name for e in self.schedule.entries 
                               if e.troop == troop and e not in [new_entry, swapped_entry]]
        troop_activities_after.extend([new_entry.activity.name, swapped_entry.activity.name])
        if len(troop_activities_after) != len(set(troop_activities_after)):
            return False  # Would create duplicate

        return True
