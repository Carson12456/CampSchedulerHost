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
