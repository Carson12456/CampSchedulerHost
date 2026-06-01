"""
Constrained scheduler for Iteration 2 - Fixed version.
Fixes: Reflection for all, Delta→Super Troop sequencing.

Refactored Architecture:
- SchedulerConstants: Static configuration (activity lists, constraints)
- Mixin classes provide modular functionality (see core/scheduler/)
"""
import random
from collections import defaultdict
from .models import Activity, Troop, ScheduleEntry, TimeSlot, Day, Zone, generate_time_slots
from core.scheduler import config_loader
from .activities import get_all_activities, get_activity_by_name
import typing
from typing import List, Dict, Set, Optional, Any

# Alias for backward compatibility if used in this file
EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()

# Import mixin classes for modular composition
from .scheduler.constants import SchedulerConstants
from .scheduler.pipeline import SchedulingPipelineMixin
from .scheduler.state import SchedulerState
from .scheduler.utilities import UtilityMixin
from .scheduler.validators import ValidatorMixin, would_create_excess_day_for_entries
from .scheduler.phase_a_foundation import PhaseAFoundationMixin
from .scheduler.phase_b_core import PhaseBCoreMixin

from .scheduler.phase_d_cleanup import PhaseDCleanupMixin
from .scheduler.legacy_interface import LegacyInterfaceMixin
from .scheduler.legacy_parts import (
    PlacementAndStateMixin,
    Top5AndSwapsMixin,
    PreferenceAndLimitedMixin,
    SequencingAndConstraintsMixin,
    GapFillAndStatsMixin,
    ClusteringAndOptimizationMixin,
    SafetyAndExportMixin,
    CompatibilityBridgesMixin,
)


class ConstrainedScheduler(
    LegacyInterfaceMixin,
    PlacementAndStateMixin,
    Top5AndSwapsMixin,
    PreferenceAndLimitedMixin,
    SequencingAndConstraintsMixin,
    GapFillAndStatsMixin,
    ClusteringAndOptimizationMixin,
    SafetyAndExportMixin,
    CompatibilityBridgesMixin,
    SchedulerState,
    SchedulingPipelineMixin,
    UtilityMixin,
    ValidatorMixin,
    PhaseAFoundationMixin,
    PhaseBCoreMixin,
    PhaseDCleanupMixin
):

    """
    Advanced scheduler with constraints:
    1. Beach activity in slot 1/3 daily (Thu slot 2)
    2. Max 1 accuracy (Rifle/Shotgun/Archery) per day
    3. Spread preferences (1 Top-5/day, 1 Top-10/day)
    4. Friday Reflection required for ALL troops
    5. Staff optimization (Tower full days, Commissioners, then back-to-back)
    6. Delta → Super Troop sequence (early week, only 1 Super Troop at a time)
    """
    
    
    # Default priority order for filling remaining slots when troop doesn't have enough preferences
    DEFAULT_FILL_PRIORITY = SchedulerConstants.FILL_PRIORITY
    
    # Activities that can have multiple troops at once
    CONCURRENT_ACTIVITIES = SchedulerConstants.CONCURRENT_ACTIVITIES

    # Mandatory anchors from BRAIN/SKULL should not be displaced by preference recovery.
    NON_DISPLACEABLE_ACTIVITIES = set(SchedulerConstants.MANDATORY_ANCHORS)
    TUESDAY_ONLY_ACTIVITIES = set(SchedulerConstants.TUESDAY_ONLY_ACTIVITIES)
    REGRESSION_ALIGNMENT_PREF_CUTOFF = 10
    
    # Beach activities that should ideally be on different days (soft constraint)
    BEACH_ACTIVITIES = SchedulerConstants.BEACH_ACTIVITIES
    
    # WET activities - cannot have Tower/ODS immediately before or after
    WET_ACTIVITIES = SchedulerConstants.WET_ACTIVITIES
    
    # Tower and ODS activities - cannot be scheduled after wet activities
    TOWER_ODS_ACTIVITIES = SchedulerConstants.TOWER_ODS_ACTIVITIES
    
    # Accuracy activities (max 1 per day per troop)
    ACCURACY_ACTIVITIES = SchedulerConstants.ACCURACY_ACTIVITIES
    
    # 3-hour activities
    THREE_HOUR_ACTIVITIES = SchedulerConstants.THREE_HOUR_ACTIVITIES
    
    # Activities that don't need consecutive slot optimization
    NON_CONSECUTIVE_ACTIVITIES = SchedulerConstants.NON_CONSECUTIVE_ACTIVITIES
    
    # Spine: "Any pair of: Aqua Trampoline, Water Polo, Greased Watermelon" - prohibited same day
    SPINE_BEACH_PROHIBITED_PAIR = SchedulerConstants.SPINE_BEACH_PROHIBITED_PAIR
    
    # Activities that cannot be on the same day for a troop (HARD constraints)
    SAME_DAY_CONFLICTS = SchedulerConstants.SAME_DAY_CONFLICTS
    
    # Activities to AVOID on same day (SOFT constraints - try to avoid)
    SOFT_SAME_DAY_CONFLICTS = SchedulerConstants.SOFT_SAME_DAY_CONFLICTS
    
    # Activities that mildly prefer certain slots (SOFT preference)
    SLOT_PREFERENCES = SchedulerConstants.SLOT_PREFERENCES
    
    # Staff count per activity - for total staff balancing across slots
    ACTIVITY_STAFF_COUNT = SchedulerConstants.ACTIVITY_STAFF_COUNT
    
    # Beach staff limit - max staffed activities per slot
    MAX_BEACH_STAFFED_ACTIVITIES = SchedulerConstants.MAX_BEACH_STAFFED_ACTIVITIES
    
    # Canoe capacity - max 13 canoes = 26 people per slot
    MAX_CANOE_CAPACITY = SchedulerConstants.MAX_CANOE_CAPACITY
    CANOE_ACTIVITIES = SchedulerConstants.CANOE_ACTIVITIES
    
    # Beach activities that must follow slot rules
    BEACH_SLOT_ACTIVITIES = SchedulerConstants.BEACH_SLOT_ACTIVITIES

    # Beach activities that require staff (2 staff each)
    BEACH_STAFFED_ACTIVITIES = SchedulerConstants.BEACH_STAFFED_ACTIVITIES
    
    # Area pairs for chain scheduling (when scheduling one, try to chain the other)
    # NOTE: Delta is NOT paired with Tower/ODS - too far to walk between Delta and those areas
    # NOTE: Archery and Sailing are NOT paired - no need for consecutive scheduling
    # NOTE: Boats do NOT need consecutive scheduling
    AREA_PAIRS = SchedulerConstants.AREA_PAIRS
    
    # Non-exclusive areas (multiple activities can run): Beach, Campsite, Off-Camp
    MANDATORY_ANCHORS = SchedulerConstants.MANDATORY_ANCHORS
    BATCH_SETUP_ACTIVITIES = SchedulerConstants.BATCH_SETUP_ACTIVITIES
    SWAPPABLE_FILL_ACTIVITIES = SchedulerConstants.SWAPPABLE_FILL_ACTIVITIES
    SMART_BALLS_ACTIVITIES = SchedulerConstants.SMART_BALLS_ACTIVITIES
    FINAL_AUDIT_FILLER_ACTIVITIES = SchedulerConstants.FINAL_AUDIT_FILLER_ACTIVITIES
    EMERGENCY_FILL_ACTIVITIES = SchedulerConstants.EMERGENCY_FILL_ACTIVITIES
    MOVABLE_FILL_ACTIVITIES = SchedulerConstants.MOVABLE_FILL_ACTIVITIES
    STAFF_ROLE_MAP = SchedulerConstants.STAFF_ROLE_MAP
    
    def __init__(
        self,
        troops: list[Troop],
        activities: list[Activity] = None,
        voyageur_mode: bool = False,
        snapshot_recorder=None,
    ):
        self._initialize_state(troops, activities, voyageur_mode)
        self.snapshot_recorder = snapshot_recorder
