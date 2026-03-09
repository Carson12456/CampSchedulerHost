"""Legacy ConstrainedScheduler methods (split mixin part)."""

from __future__ import annotations

import math
import os
import random
import typing
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

from ...activities import get_activity_by_name, get_all_activities
from ...models import Activity, Day, ScheduleEntry, TimeSlot, Troop, Zone, generate_time_slots
from .. import config_loader
from ..constants import SchedulerConstants
from ..validators import would_create_excess_day_for_entries

EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()

class LegacyPart08Mixin:
    """Scheduler legacy methods part 08."""

    def _comprehensive_prevention_check(self, timeslot, activity, troop, day=None):
        """Comprehensive prevention check before scheduling."""
        # Delegate to existing validation method
        return self._can_schedule(timeslot, activity, troop, day)


    def _eliminate_gaps(self):
        """Eliminate gaps in the schedule."""
        # Delegate to existing gap elimination methods
        self._fill_empty_slots_final()
        self._force_zero_gaps_absolute()


    def _resolve_constraint_conflicts(self):
        """Resolve constraint conflicts."""
        # Delegate to existing conflict resolution
        self._resolve_beach_slot_violations()
        self._resolve_wet_dry_patterns()


    def _intelligent_swaps(self):
        """Perform intelligent activity swaps."""
        # Delegate to existing swap methods
        return self._comprehensive_smart_swaps()


    def _force_placement(self, activity, troop, timeslot):
        """Force place an activity even with conflicts."""
        # Delegate to existing force placement
        return self._emergency_placement(activity, troop, timeslot)


    def _displacement_logic(self, activity, troop, timeslot):
        """Handle displacement logic for scheduling."""
        # Delegate to existing displacement methods
        return self._constraint_aware_displacement(activity, troop, timeslot)


    def _eliminate_empty_slots(self):
        """Eliminate empty slots in the schedule."""
        # Delegate to existing gap elimination
        return self._fill_empty_slots_final()


    def _enforce_constraint_compliance(self):
        """Enforce constraint compliance."""
        # Delegate to existing constraint enforcement
        self._validate_critical_constraints()
        self._reduce_constraint_violations()


    def _ensure_top5_satisfaction(self):
        """Ensure Top 5 preference satisfaction."""
        # Delegate to existing Top 5 methods
        return self._guarantee_all_top5()


    def _meet_activity_requirements(self):
        """Meet activity requirements."""
        # Delegate to existing requirement methods
        self._guarantee_mandatory_activities()
        self._schedule_three_hour_activities()


    def _optimize_clustering_efficiency(self):
        """Optimize clustering efficiency."""
        # Delegate to existing clustering methods
        return self._comprehensive_clustering_optimization()


    def _optimize_setup(self):
        """Optimize setup efficiency."""
        # Delegate to existing setup optimization
        return self._optimize_setup_efficiency()


    def _enhance_preferences(self):
        """Enhance preference satisfaction."""
        # Delegate to existing preference methods
        return self._schedule_preferences_range(1, 20)


    def _get_priority_level(self, activity, troop):
        """Get priority level for activity-troop pair."""
        # Delegate to existing priority logic
        try:
            priority = troop.get_priority(activity.name)
            if priority <= 5:
                return "CRITICAL"
            elif priority <= 10:
                return "HIGH"
            elif priority <= 15:
                return "MEDIUM"
            else:
                return "LOW"
        except:
            return "LOW"


    def _apply_priority_hierarchy(self):
        """Apply priority hierarchy in scheduling."""
        # This is already implemented in the main scheduling logic
        return True


    def _validate_constraints_before(self, timeslot, activity, troop):
        """Validate constraints before scheduling."""
        return self._can_schedule(timeslot, activity, troop)


    def _validate_constraints_after(self, entry):
        """Validate constraints after scheduling."""
        # Check if the entry violates any constraints
        violations = self._count_current_violations()
        return violations == 0

    def _calculate_staff_efficiency(self) -> float:
        """Return a simple staff-efficiency percentage for analytics tests."""
        if not getattr(self, "time_slots", None) or not getattr(self, "troops", None):
            return 0.0
        total_slots = len(self.time_slots) * len(self.troops)
        if total_slots == 0:
            return 0.0
        filled = 0
        for troop in self.troops:
            for slot in self.time_slots:
                if not self.schedule.is_troop_free(slot, troop):
                    filled += 1
        return (filled / total_slots) * 100.0

    def _generate_performance_report(self) -> dict:
        """Generate lightweight performance summary."""
        return {
            "staff_efficiency": self._calculate_staff_efficiency(),
            "total_entries": len(self.schedule.entries),
            "troops": len(getattr(self, "troops", [])),
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate simple recommendation list from current schedule shape."""
        recs: list[str] = []
        if self._calculate_staff_efficiency() < 80:
            recs.append("Improve slot fill rate for higher staff efficiency.")
        if not recs:
            recs.append("Maintain current scheduling balance and monitor drift.")
        return recs
