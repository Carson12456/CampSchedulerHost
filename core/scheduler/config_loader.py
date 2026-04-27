"""
Configuration Loader for Summer Camp Scheduler.

Loads and provides access to SKULL.json configuration, serving as the
single source of truth for camp-specific rules and data.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

# Resolve path to SKULL.json relative to this file
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_SKULL_PATH = _CONFIG_DIR / "SKULL.json"

# Cached configuration
_skull_cache: Optional[Dict[str, Any]] = None


def _load_skull() -> Dict[str, Any]:
    """Load SKULL.json and cache it."""
    global _skull_cache
    if _skull_cache is None:
        if not _SKULL_PATH.exists():
            raise FileNotFoundError(f"SKULL.json not found at {_SKULL_PATH}")
        with open(_SKULL_PATH, 'r', encoding='utf-8') as f:
            _skull_cache = json.load(f)
    return _skull_cache


def reload_skull() -> None:
    """Force reload of SKULL.json (useful for testing)."""
    global _skull_cache
    _skull_cache = None
    _load_skull()


# === Exclusive Areas ===

def get_exclusive_areas() -> Dict[str, List[str]]:
    """Get exclusive areas mapping (area_name -> list of activities)."""
    return _load_skull().get("exclusive_areas", {})


def get_activity_definitions() -> List[Dict[str, Any]]:
    """Get configured activity definitions."""
    return _load_skull().get("activities", [])


def get_area_for_activity(activity_name: str) -> Optional[str]:
    """Get the exclusive area name for a given activity, or None if not exclusive."""
    for area, activities in get_exclusive_areas().items():
        if activity_name in activities:
            return area
    return None


def is_exclusive_activity(activity_name: str) -> bool:
    """Check if an activity belongs to any exclusive area."""
    return get_area_for_activity(activity_name) is not None


# === Staff Needs ===

def get_staff_needs() -> Dict[str, int]:
    """Get staff requirements per activity."""
    return _load_skull().get("staff_needs", {})


def get_staff_need(activity_name: str) -> int:
    """Get staff count needed for a specific activity (default 0)."""
    return get_staff_needs().get(activity_name, 0)


def get_staff_role_map() -> Dict[str, List[str]]:
    """
    Get mapping of Staff Role -> List[Activity Names].
    Derived from the 'activities' list in SKULL.json.
    """
    skull = _load_skull()
    activities = skull.get("activities", [])
    role_map = {}
    
    for act in activities:
        role = act.get("staff_needed")
        if role:
            if role not in role_map:
                role_map[role] = []
            role_map[role].append(act["name"])
    
    return role_map


# === Constraints ===

def get_constraints() -> Dict[str, Any]:
    """Get all constraint configuration."""
    return _load_skull().get("constraints", {})


def get_max_staff_global() -> int:
    """Get maximum global staff count per slot."""
    return get_constraints().get("max_staff_global", 16)


def get_target_staff_global() -> int:
    """Get target global staff count per slot."""
    return get_constraints().get("target_staff_global", 14)


def get_three_hour_activities() -> List[str]:
    """Get list of 3-hour activities."""
    return get_constraints().get("three_hour_activities", [])


def get_fill_activities() -> List[str]:
    """Get list of activities used to fill empty slots."""
    return get_constraints().get("fill_activities", [])


# === Optimization Rules ===

def get_optimization_rules() -> Dict[str, Any]:
    """Get optimization rules configuration."""
    return get_constraints().get("optimization", {})


def get_aqua_trampoline_rules() -> Dict[str, Any]:
    """Get Aqua Trampoline specific rules."""
    return get_constraints().get("aqua_trampoline_rules", {})


def get_capacity_limits() -> Dict[str, Any]:
    """Get capacity limit configuration."""
    constraints = get_constraints()
    return {
        "beach_staff_per_slot": constraints.get("beach_staff_per_slot", 12),
        "canoe_capacity": constraints.get("max_canoe_capacity", 26),
        "tower_extended_size": constraints.get("tower_extended_size", 15),
        "sailing_extended_size": constraints.get("sailing_extended_size", 12)
    }


def get_zone_capacities() -> Dict[str, int]:
    """Get max concurrent activities per zone."""
    return get_constraints().get("zone_capacities", {})


# === Prohibited Pairs ===

def get_prohibited_pairs() -> List[List[str]]:
    """Get list of prohibited activity pairs (cannot be same day)."""
    return _load_skull().get("prohibited_pairs", [])


def are_activities_prohibited_together(act1: str, act2: str) -> bool:
    """Check if two activities cannot be scheduled on the same day."""
    for pair in get_prohibited_pairs():
        if act1 in pair and act2 in pair:
            return True
    return False


# === Commissioner Groups ===

def get_commissioner_groups() -> Dict[str, List[str]]:
    """Get commissioner group assignments (region -> list of troop names)."""
    return _load_skull().get("commissioner_groups", {})


def get_commissioner_for_troop(troop_name: str) -> Optional[str]:
    """Get the commissioner region for a troop, or None if not found."""
    for region, troops in get_commissioner_groups().items():
        if troop_name in troops:
            return region
    return None


# === Activity Tags (Future Expansion) ===

def get_activity_tags() -> Dict[str, List[str]]:
    """Get activity tags for generic rule matching.
    
    Returns dict of tag_name -> list of activities with that tag.
    Example: {"wet": ["Aqua Trampoline", "Water Polo", ...], "accuracy": [...]}
    """
    return _load_skull().get("activity_tags", {})


def activity_has_tag(activity_name: str, tag: str) -> bool:
    """Check if an activity has a specific tag."""
    tags = get_activity_tags()
    return activity_name in tags.get(tag, [])


def get_activities_with_tag(tag: str) -> List[str]:
    """Get all activities with a specific tag."""
    return get_activity_tags().get(tag, [])


# === Slot Rules ===

def get_slot_rules() -> Dict[str, Any]:
    """Get slot placement rules."""
    return _load_skull().get("slot_rules", {})


def get_beach_allowed_slots() -> List[int]:
    """Get allowed slots for beach activities (default [1, 3])."""
    return get_slot_rules().get("beach_allowed_slots", [1, 3])


def get_beach_thursday_slots() -> List[int]:
    """Get allowed slots for beach activities on Thursday."""
    return get_slot_rules().get("beach_thursday_slots", [1, 2])


# === Special Activities ===

def get_special_activities() -> Dict[str, Dict[str, Any]]:
    """Get special activity configurations."""
    return _load_skull().get("special_activities", {})


def get_special_activity_config(activity_name: str) -> Dict[str, Any]:
    """Get configuration for a specific special activity."""
    return get_special_activities().get(activity_name, {})


# === Soft Prohibited Pairs ===

def get_soft_prohibited_pairs() -> List[List[str]]:
    """Get list of soft prohibited activity pairs (avoid same day if possible)."""
    return _load_skull().get("soft_prohibited_pairs", [])


def are_activities_soft_prohibited_together(act1: str, act2: str) -> bool:
    """Check if two activities should avoid being scheduled on the same day."""
    for pair in get_soft_prohibited_pairs():
        if act1 in pair and act2 in pair:
            return True
    return False


# === Request-Only Activities ===

def get_request_only_activities() -> List[str]:
    """Get list of activities that should only be scheduled if explicitly requested."""
    return _load_skull().get("request_only_activities", [])


def is_request_only_activity(activity_name: str) -> bool:
    """Check if an activity should only be scheduled when explicitly requested."""
    return activity_name in get_request_only_activities()


# === Sequence Rules ===

def get_sequence_rules() -> Dict[str, Any]:
    """Get sequence rules configuration (e.g., not_back_to_back rules)."""
    return _load_skull().get("sequence_rules", {})


def get_not_back_to_back_rules() -> List[Dict[str, Any]]:
    """Get list of not-back-to-back rules.
    
    Each rule has:
    - activity_a: The primary activity name
    - activity_b_tags: List of tags for activities that cannot be adjacent
    """
    return get_sequence_rules().get("not_back_to_back", [])


def are_activities_not_back_to_back(act1: str, act2: str) -> bool:
    """Check if two activities cannot be scheduled in adjacent slots.
    
    Returns True if act1 and act2 should NOT be back-to-back.
    """
    # Sailing has an intentional 30-minute travel buffer built into its split
    # session, so adjacency restrictions should not block activities before or
    # after Sailing (including Tower / ODS families).
    if act1 == "Sailing" or act2 == "Sailing":
        return False

    rules = get_not_back_to_back_rules()
    tags = get_activity_tags()
    
    for rule in rules:
        activity_a = rule.get("activity_a", "")
        b_tags = rule.get("activity_b_tags", [])
        
        # Check if act1 is activity_a and act2 has any of the b_tags
        if act1 == activity_a:
            for tag in b_tags:
                if act2 in tags.get(tag, []):
                    return True
        
        # Check reverse (act2 is activity_a, act1 has b_tags)
        if act2 == activity_a:
            for tag in b_tags:
                if act1 in tags.get(tag, []):
                    return True
    
    return False


# === Optimization and Rules ===

def get_concurrent_activities() -> List[str]:
    """Get list of activities that can schedule multiple troops simultaneously."""
    return get_constraints().get("concurrent_activities", [])


def get_concurrent_exclusivity_exceptions() -> List[str]:
    """
    Activities that should be ignored by exclusivity conflict cleanup.

    This is intentionally separate from `concurrent_activities` because some
    activities (e.g. 3-hour off-camp) are treated as exclusivity exceptions
    without being globally concurrent in every scheduling rule.
    """
    constraints = get_constraints()
    configured = constraints.get("concurrent_exclusivity_exceptions", [])
    if configured:
        return configured
    # Backward-compatible fallback aligned with prior behavior.
    return list(dict.fromkeys(get_concurrent_activities() + get_three_hour_activities() + ["Shower House"]))


def get_mandatory_anchors() -> List[str]:
    """
    Get mandatory anchor activities used for hard acceptance checks.

    Preferred source: constraints.mandatory_anchors.
    Backward-compatible fallback includes activity_tags.mandatory plus BRAIN
    Tuesday-only anchors.
    """
    constraints = get_constraints()
    configured = constraints.get("mandatory_anchors", [])
    if configured:
        return configured

    tags = get_activities_with_tag("mandatory")
    fallback = list(dict.fromkeys(tags + ["History Center", "Disc Golf"]))
    return fallback


def get_tuesday_only_activities() -> List[str]:
    """Get activities constrained to Tuesday-only placement."""
    constraints = get_constraints()
    configured = constraints.get("tuesday_only_activities", [])
    if configured:
        return configured
    return ["History Center", "Disc Golf"]


def validate_brain_skull_alignment() -> None:
    """
    Fail fast when SKULL hard-policy lists diverge from BRAIN-required anchors.
    """
    brain_required_anchors = {"Reflection", "Super Troop", "History Center", "Disc Golf"}
    brain_tuesday_only = {"History Center", "Disc Golf"}

    mandatory = set(get_mandatory_anchors())
    tuesday_only = set(get_tuesday_only_activities())

    missing_mandatory = brain_required_anchors - mandatory
    if missing_mandatory:
        raise ValueError(
            "BRAIN/SKULL mismatch: mandatory anchors missing from SKULL "
            f"mandatory_anchors: {sorted(missing_mandatory)}"
        )

    missing_tuesday = brain_tuesday_only - tuesday_only
    if missing_tuesday:
        raise ValueError(
            "BRAIN/SKULL mismatch: Tuesday-only anchors missing from SKULL "
            f"tuesday_only_activities: {sorted(missing_tuesday)}"
        )


def get_non_consecutive_activities() -> List[str]:
    """Get list of activities that do not need to be consecutive slots."""
    return get_constraints().get("non_consecutive", [])


def get_fill_priority() -> List[str]:
    """Get fill priority list."""
    return _load_skull().get("constraints", {}).get("fill_priority", [])


def get_area_pairs() -> Dict[str, str]:
    """Get area pairing configuration."""
    return get_constraints().get("optimization", {}).get("area_pairs", {})


def get_batch_setup_activities() -> List[str]:
    """Get activities that benefit from setup batching."""
    return get_optimization_rules().get("batch_setup_activities", [])


def get_swappable_fill_activities() -> List[str]:
    """Get low-risk filler activities that can be swapped during optimization."""
    return get_optimization_rules().get("swappable_fill_activities", [])


def get_smart_balls_activities() -> List[str]:
    """Get simple ball-game activities used by smart fill scheduling."""
    return get_optimization_rules().get("smart_balls_activities", [])


def get_final_audit_filler_activities() -> List[str]:
    """Get generic fillers eligible for final preference replacement audit."""
    return get_optimization_rules().get("final_audit_filler_activities", [])


def get_emergency_fill_activities() -> List[str]:
    """Get conservative emergency fills for last-resort gap closure."""
    return get_optimization_rules().get("emergency_fill_activities", [])


def get_movable_fill_activities() -> List[str]:
    """Get filler activities that optimization can move freely."""
    return get_optimization_rules().get("movable_fill_activities", [])


def get_canoe_activities() -> List[str]:
    """Get canoe activities (using 'canoe' tag)."""
    return get_activities_with_tag("canoe")


def get_rotation_schedule() -> Dict[str, Dict[str, List[str]]]:
    """Get commissioner rotation schedule."""
    return _load_skull().get("rotation_schedule", {})


def get_commissioner_activity_days(activity_name: str) -> Dict[str, Any]:
    """
    Get the day assignment for a specific activity per commissioner.
    Returns: {'Commissioner A': Day.MONDAY, ...}
    derived from rotation_schedule.
    """
    from core.models import Day
    rotation = get_rotation_schedule()
    result = {}
    
    # Map string days to Day enum
    day_map = {
        "Monday": Day.MONDAY,
        "Tuesday": Day.TUESDAY, 
        "Wednesday": Day.WEDNESDAY,
        "Thursday": Day.THURSDAY,
        "Friday": Day.FRIDAY
    }
    
    for comm, schedule in rotation.items():
        for day_str, activities in schedule.items():
            if activity_name in activities:
                # Add for base commissioner (e.g. "Commissioner A")
                if "Voyageur" not in comm:
                    result[comm] = day_map.get(day_str)
                    
    return result


def get_cluster_areas() -> List[str]:
    """Get cluster areas for optimization."""
    return get_constraints().get("optimization", {}).get("cluster_areas", [])


def get_capacity_check_activities() -> List[str]:
    """Get activities that require unified capacity checking."""
    return _load_skull().get("constraints", {}).get("capacity_check_activities", [])
