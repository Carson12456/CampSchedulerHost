"""
Scheduler Constants Module.

Recreated from core/scheduler/config/SKULL.json and codebase analysis.
Provides static configuration for the ConstrainedScheduler.
"""
from core.scheduler import config_loader

class SchedulerConstants:
    """
    Static configuration constants for the scheduler.
    """
    
    # =========================================================================
    # CAMPSITE & COMMISSIONER CONFIGURATION
    # =========================================================================
    
    # Derived from SKULL.json 'commissioner_groups'
    # North + Central + South
    CAMPSITE_ORDER = config_loader._load_skull().get("camp_map", {}).get("campsite_order", [])
    
    # Map Commissioner to Troops (North->A, Central->B, South->C)
    COMMISSIONER_TROOPS = config_loader.get_commissioner_groups()
    
    # =========================================================================
    # ACTIVITY LISTS & TAGS
    # =========================================================================
    
    # From SKULL.json 'constraints.three_hour_activities'
    THREE_HOUR_ACTIVITIES = config_loader.get_three_hour_activities()
    
    # From SKULL.json 'activity_tags.beach'
    # Note: Using 'beach_slot_restricted' tag for exact match with previous logic if available,
    # otherwise falling back to 'beach' or specific set derived from config.
    # The previous hardcoded set matches 'beach_slot_restricted' in SKULL.json
    BEACH_SLOT_ACTIVITIES = set(config_loader.get_activities_with_tag("beach_slot_restricted"))
    
    # From SKULL.json 'constraints.fill_priority'
    FILL_PRIORITY = config_loader.get_fill_priority()
    
    # From SKULL.json 'constraints.fill_activities' (as set)
    FILL_ACTIVITIES = set(config_loader.get_fill_activities())
    
    # From SKULL.json 'concurrent_activities'
    CONCURRENT_ACTIVITIES = config_loader.get_concurrent_activities()
    CONCURRENT_EXCLUSIVITY_EXCEPTIONS = config_loader.get_concurrent_exclusivity_exceptions()
    MANDATORY_ANCHORS = set(config_loader.get_mandatory_anchors())
    TUESDAY_ONLY_ACTIVITIES = set(config_loader.get_tuesday_only_activities())
    
    # From SKULL.json 'non_consecutive'
    NON_CONSECUTIVE_ACTIVITIES = config_loader.get_non_consecutive_activities()
    
    # From SKULL.json 'prohibited_pairs'
    SAME_DAY_CONFLICTS = config_loader.get_prohibited_pairs()
    
    # From SKULL.json 'soft_prohibited_pairs'
    SOFT_SAME_DAY_CONFLICTS = config_loader.get_soft_prohibited_pairs()
    
    # From SKULL.json 'preferences.slot_specific'
    SLOT_PREFERENCES = config_loader._load_skull().get("preferences", {}).get("slot_specific", {})

    
    # =========================================================================
    # EXCLUSIVE AREAS & STAFF ZONES
    # =========================================================================
    
    # Flattened set of ALL activities in 'exclusive_areas'
    # Derived dynamically
    EXCLUSIVE_ACTIVITIES = set()
    for activities in config_loader.get_exclusive_areas().values():
        EXCLUSIVE_ACTIVITIES.update(activities)
    
    # Staff Count per Activity (from 'staff_needs')
    ACTIVITY_STAFF_COUNT = config_loader.get_staff_needs()
    
    # Map Activity -> Staff Zone
    # Used for load balancing. Derived from 'exclusive_areas' keys.
    # Inverts the {'Zone': ['Act1', 'Act2']} mapping to {'Act1': 'Zone'}
    STAFF_ZONE_MAP = {}
    for zone, activities in config_loader.get_exclusive_areas().items():
        for activity in activities:
            STAFF_ZONE_MAP[activity] = zone
            
    # Zone Capacities (from 'constraints.zone_capacities')
    # Controls max staff load per zone
    MAX_STAFF_PER_ZONE = config_loader.get_zone_capacities()
    ZONE_CAPACITIES = MAX_STAFF_PER_ZONE # Alias for clarity

    # Cluster Areas (from 'optimization.cluster_areas')
    CLUSTER_AREAS = config_loader.get_cluster_areas()

    # Activities requiring unified capacity checking
    CAPACITY_CHECK_ACTIVITIES = set(config_loader.get_capacity_check_activities())

    # Derived Activity Lists by Tag
    BEACH_ACTIVITIES = config_loader.get_activities_with_tag("beach")
    WET_ACTIVITIES = config_loader.get_activities_with_tag("wet")
    TOWER_ODS_ACTIVITIES = config_loader.get_activities_with_tag("tower_ods")
    # Derived ODS Activities (Outdoor Skills exclusive area)
    ODS_ACTIVITIES = set(config_loader.get_exclusive_areas().get("Outdoor Skills", []))
    ACCURACY_ACTIVITIES = config_loader.get_activities_with_tag("accuracy")
    CANOE_ACTIVITIES = config_loader.get_activities_with_tag("canoe")
    
    # Specific Constraints
    MAX_BEACH_STAFFED_ACTIVITIES = config_loader.get_constraints().get("max_beach_staffed_activities", 4)
    MAX_CANOE_CAPACITY = config_loader.get_constraints().get("max_canoe_capacity", 26)
    
    # Area Pairs
    AREA_PAIRS = config_loader.get_area_pairs()
    BATCH_SETUP_ACTIVITIES = set(config_loader.get_batch_setup_activities())
    SWAPPABLE_FILL_ACTIVITIES = set(config_loader.get_swappable_fill_activities())
    SMART_BALLS_ACTIVITIES = list(config_loader.get_smart_balls_activities())
    FINAL_AUDIT_FILLER_ACTIVITIES = set(config_loader.get_final_audit_filler_activities())
    EMERGENCY_FILL_ACTIVITIES = list(config_loader.get_emergency_fill_activities())
    MOVABLE_FILL_ACTIVITIES = set(config_loader.get_movable_fill_activities())
    
    # Spine Beach Prohibited Pair (set of beach activities that should not mix).
    # Derived from SKULL soft_prohibited_pairs + special_activities instead of hardcoding.
    _special_activities = set(config_loader._load_skull().get("special_activities", {}).keys())
    SPINE_BEACH_PROHIBITED_PAIR = set()
    for pair in config_loader.get_soft_prohibited_pairs():
        if len(pair) != 2:
            continue
        a, b = pair
        if a in BEACH_ACTIVITIES and b in BEACH_ACTIVITIES and (a in _special_activities or b in _special_activities):
            SPINE_BEACH_PROHIBITED_PAIR.update([a, b])
    
    # Beach Staffed Activities (Staff needed > 0 AND in Beach zone)
    BEACH_STAFFED_ACTIVITIES = [
        act for act in BEACH_ACTIVITIES 
        if config_loader.get_staff_need(act) > 0
    ]
    
    # Staff Role Logic (Role -> List of Activities)
    # Replaces hardcoded STAFF_MAP in regression checker
    STAFF_ROLE_MAP = config_loader.get_staff_role_map()
