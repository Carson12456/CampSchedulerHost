"""
Scheduler State Module.

Contains the SchedulerState mixin class that initializes and manages
all instance-level state for the ConstrainedScheduler.

This includes tracking dictionaries, caches, and runtime configuration
that changes during the scheduling process.
"""

from collections import defaultdict
from ..models import Schedule, generate_time_slots, Day
from ..activities import get_all_activities
from .constants import SchedulerConstants


class SchedulerState:
    """
    Mixin class that provides state initialization for the scheduler.
    
    All instance variables that track scheduling progress are initialized here.
    This class should be mixed into ConstrainedScheduler.
    """
    
    def _initialize_state(self, troops, activities, voyageur_mode):
        """
        Initialize all scheduler state.
        
        Args:
            troops: List of Troop objects to schedule
            activities: List of Activity objects (or None to use all)
            voyageur_mode: Boolean flag for Voyageur-specific rules
        """
        # Import logging and caching
        from ..scheduler_logging import get_logger
        from ..scheduler_cache import SchedulerCache
        
        self.logger = get_logger()
        self.cache = SchedulerCache()
        
        # Core data
        self.troops = troops
        self.activities = activities or get_all_activities()
        self.voyageur_mode = voyageur_mode
        self.schedule = Schedule()
        self.time_slots = generate_time_slots()
        
        # Initialize cache with activities
        self.cache.initialize_activities(self.activities)
        
        # Copy class-level constants to instance for modification
        self.CAMPSITE_ORDER = list(SchedulerConstants.CAMPSITE_ORDER)
        self.COMMISSIONER_TROOPS = dict(SchedulerConstants.COMMISSIONER_TROOPS)
        self.COMMISSIONER_DELTA_DAYS = dict(SchedulerConstants.COMMISSIONER_DELTA_DAYS)
        self.COMMISSIONER_SUPER_TROOP_DAYS = dict(SchedulerConstants.COMMISSIONER_SUPER_TROOP_DAYS)
        self.COMMISSIONER_RIFLE_DAYS = self.COMMISSIONER_SUPER_TROOP_DAYS
        self.COMMISSIONER_ARCHERY_DAYS = dict(SchedulerConstants.COMMISSIONER_ARCHERY_DAYS)
        self.COMMISSIONER_SAILING_DAYS = self.COMMISSIONER_DELTA_DAYS
        self.COMMISSIONER_TOWER_ODS_DAYS = dict(SchedulerConstants.COMMISSIONER_TOWER_ODS_DAYS)
        
        # Expand configs for Voyageur commissioners (inherit from Commissioner A/B/C)
        for config in [self.COMMISSIONER_DELTA_DAYS, self.COMMISSIONER_SUPER_TROOP_DAYS]:
            for suffix in ['A', 'B', 'C']:
                comm_key = f"Commissioner {suffix}"
                if comm_key in config:
                    config[f"Voyageur {suffix}"] = config[comm_key]
        
        # Copy AREA_PAIRS to instance to allow modification
        self.AREA_PAIRS = dict(SchedulerConstants.AREA_PAIRS)
        
        # Voyageur Rule: History Center must have a balls activity before or after
        # ENABLED GLOBALLY (User request: HC/DG need balls/reserve)
        self.AREA_PAIRS["History Center"] = "Gaga Ball"
        self.AREA_PAIRS["Gaga Ball"] = "History Center"
        self.AREA_PAIRS["Disc Golf"] = "9 Square"
        
        # Build troop -> commissioner mapping
        self.troop_commissioner = {}
        for comm, troop_names in self.COMMISSIONER_TROOPS.items():
            for troop_name in troop_names:
                self.troop_commissioner[troop_name] = comm
        
        # Override with explicit troop commissioner if present (e.g. for Voyageur troops)
        for troop in self.troops:
            if troop.commissioner:
                is_known_tc_troop = any(
                    troop.name in t_list 
                    for t_list in self.COMMISSIONER_TROOPS.values()
                )
                if not is_known_tc_troop or self.voyageur_mode:
                    self.troop_commissioner[troop.name] = troop.commissioner
        
        # Initialize cache with troops
        self.cache.initialize_troops(self.troops, self.troop_commissioner)
        
        # === PROGRESS TRACKING ===
        self.troop_top5_scheduled = {t.name: 0 for t in troops}
        self.troop_top10_scheduled = {t.name: 0 for t in troops}
        self.troop_progress = {troop.name: set() for troop in self.troops}
        
        # Track which troops have Delta (optional activity)
        self.troop_has_delta = {t.name: False for t in troops}
        
        # Track which troops have Super Troop (mandatory for all)
        self.troop_has_super_troop = {t.name: False for t in troops}
        
        # Track troops whose Delta was swapped out during optimization
        self.delta_was_swapped = set()
        
        # Track sailing + balls fills (30 min partial slot during sailing)
        # Format: {(slot, troop_name): "Gaga Ball" or "9 Square"}
        self.sailing_balls_fills = {}
        
        # Cache for Friday slots (used by smart Reflection)
        self._friday_slots = None
        
        # === STAFF LOAD TRACKING ===
        # Track staff loads per slot for each zone during scheduling
        # Format: {slot: {'Tower': count, 'Rifle': count, 'ODS': count, 'Beach': count, 'Handicrafts': count}}
        self.staff_load_by_slot = defaultdict(lambda: defaultdict(int))
        
        # Staff zone mapping (copied from constants for instance access)
        self.STAFF_ZONE_MAP = dict(SchedulerConstants.STAFF_ZONE_MAP)
        
        # Cache for troop day activity counts (invalidated when schedule changes)
        self._troop_day_counts_cache = {}
        self._cache_valid = True
        
        # Track total staff count per slot (across ALL zones) for balanced distribution
        self.total_staff_by_slot = defaultdict(int)
        
        # When True, prioritize staff load balance over clustering for slot selection
        self.prioritize_staff_balance = False
        
        # Commissioner activity-day assignments
        # Format: {(activity_name, day): {'commissioner': 'Commissioner A', 'troops': ['Troop1', 'Troop2']}}
        self.commissioner_activity_day_assignments = {}
        
        # ODS activities set (copied for instance access)
        self.ODS_ACTIVITIES = set(SchedulerConstants.ODS_ACTIVITIES)
        
        # Fill activities set (copied for instance access)
        self.FILL_ACTIVITIES = set(SchedulerConstants.FILL_ACTIVITIES)
        
        # Concurrent activities (can have multiple troops)
        self.CONCURRENT_ACTIVITIES = set(SchedulerConstants.CONCURRENT_ACTIVITIES)
