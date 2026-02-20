"""
Scheduler state initialization for ConstrainedScheduler.

This mixin centralizes runtime state setup so `core/constrained_scheduler.py`
can focus on scheduling behavior.
"""

import os
from collections import defaultdict

from ..activities import get_all_activities
from ..models import Schedule, generate_time_slots
from . import config_loader
from .constants import SchedulerConstants


class SchedulerState:
    """Initialize runtime scheduler state from SKULL-driven constants."""

    def _initialize_state(self, troops, activities, voyageur_mode):
        from ..scheduler_cache import SchedulerCache
        from ..scheduler_logging import get_logger

        self.logger = get_logger()
        self.cache = SchedulerCache()

        self.troops = troops
        self.activities = activities or get_all_activities()
        self.voyageur_mode = voyageur_mode
        self.schedule = Schedule()
        self.time_slots = generate_time_slots()

        self.cache.initialize_activities(self.activities)

        # Core source-of-truth mappings from SKULL/Constants.
        self.CAMPSITE_ORDER = SchedulerConstants.CAMPSITE_ORDER
        self.COMMISSIONER_TROOPS = SchedulerConstants.COMMISSIONER_TROOPS
        self.COMMISSIONER_DELTA_DAYS = config_loader.get_commissioner_activity_days("Delta")
        self.COMMISSIONER_SUPER_TROOP_DAYS = config_loader.get_commissioner_activity_days("Super Troop")
        self.COMMISSIONER_RIFLE_DAYS = config_loader.get_commissioner_activity_days("Troop Rifle")
        self.COMMISSIONER_ARCHERY_DAYS = config_loader.get_commissioner_activity_days("Archery")
        self.COMMISSIONER_SAILING_DAYS = config_loader.get_commissioner_activity_days("Sailing")
        self.COMMISSIONER_TOWER_ODS_DAYS = config_loader.get_commissioner_activity_days("Climbing Tower")

        for config in [
            self.COMMISSIONER_DELTA_DAYS,
            self.COMMISSIONER_SUPER_TROOP_DAYS,
            self.COMMISSIONER_RIFLE_DAYS,
            self.COMMISSIONER_ARCHERY_DAYS,
            self.COMMISSIONER_SAILING_DAYS,
            self.COMMISSIONER_TOWER_ODS_DAYS,
        ]:
            for suffix in ["A", "B", "C"]:
                comm_key = f"Commissioner {suffix}"
                if comm_key in config:
                    config[f"Voyageur {suffix}"] = config[comm_key]

        self.AREA_PAIRS = SchedulerConstants.AREA_PAIRS.copy()

        self.troop_commissioner = {}
        for comm, troop_names in self.COMMISSIONER_TROOPS.items():
            for troop_name in troop_names:
                self.troop_commissioner[troop_name] = comm

        for troop in self.troops:
            if troop.commissioner:
                is_known_tc_troop = any(
                    troop.name in t_list for t_list in self.COMMISSIONER_TROOPS.values()
                )
                if not is_known_tc_troop or self.voyageur_mode:
                    self.troop_commissioner[troop.name] = troop.commissioner

        self.cache.initialize_troops(self.troops, self.troop_commissioner)

        self.troop_top5_scheduled = {t.name: 0 for t in troops}
        self.troop_top10_scheduled = {t.name: 0 for t in troops}
        self.troop_progress = {troop.name: set() for troop in self.troops}
        self.troop_has_delta = {t.name: False for t in troops}
        self.troop_has_super_troop = {t.name: False for t in troops}
        self.delta_was_swapped = set()
        self.sailing_balls_fills = {}
        self._friday_slots = None

        self.staff_load_by_slot = defaultdict(lambda: defaultdict(int))

        # Dynamic staff-zone map from loaded activity metadata.
        self.STAFF_ZONE_MAP = {}
        for activity in self.activities:
            if activity.zone.name == "BEACH":
                self.STAFF_ZONE_MAP[activity.name] = "Beach"
            elif activity.zone.name == "TOWER":
                self.STAFF_ZONE_MAP[activity.name] = "Tower"
            elif activity.zone.name == "OUTDOOR_SKILLS":
                self.STAFF_ZONE_MAP[activity.name] = "ODS"
            elif activity.zone.name == "HANDICRAFTS":
                self.STAFF_ZONE_MAP[activity.name] = "Handicrafts"
            elif activity.name in ["Troop Rifle", "Troop Shotgun"]:
                self.STAFF_ZONE_MAP[activity.name] = "Rifle"
            elif activity.name in ["Archery"]:
                self.STAFF_ZONE_MAP[activity.name] = "Archery"
            elif activity.name in ["Super Troop", "Delta"]:
                self.STAFF_ZONE_MAP[activity.name] = "Commissioner"

        if "Climbing Tower" not in self.STAFF_ZONE_MAP:
            self.STAFF_ZONE_MAP["Climbing Tower"] = "Tower"
        if "Troop Rifle" not in self.STAFF_ZONE_MAP:
            self.STAFF_ZONE_MAP["Troop Rifle"] = "Rifle"

        self._troop_day_counts_cache = {}
        self._cache_valid = True
        self.total_staff_by_slot = defaultdict(int)
        self.prioritize_staff_balance = False
        self.commissioner_activity_day_assignments = {}
        mode = os.getenv("COMM_CLUSTER_MODE", "mixed").strip().lower()
        if mode not in {"strong", "ownership", "mixed"}:
            mode = "mixed"
        self.commissioner_clustering_mode = mode
        self.ODS_ACTIVITIES = SchedulerConstants.ODS_ACTIVITIES
        self.FILL_ACTIVITIES = SchedulerConstants.FILL_ACTIVITIES
        self.CONCURRENT_ACTIVITIES = SchedulerConstants.CONCURRENT_ACTIVITIES
