"""
Activity definitions sourced from SKULL.json.
"""

from __future__ import annotations

from .models import Activity, Zone

_activity_cache: list[Activity] | None = None
_activity_lookup: dict[str, Activity] | None = None
_activity_cache_source_id: int | None = None


def _parse_zone(zone_name: str) -> Zone:
    """Map SKULL zone names onto the core.models.Zone enum."""
    try:
        return Zone[zone_name]
    except KeyError:
        for zone in Zone:
            if zone.value == zone_name:
                return zone
    raise ValueError(f"Unknown zone '{zone_name}' in SKULL activity definition")


def _ensure_activity_cache() -> None:
    global _activity_cache, _activity_lookup, _activity_cache_source_id

    from .scheduler import config_loader

    skull = config_loader._load_skull()
    skull_source_id = id(skull)
    if _activity_cache is not None and _activity_lookup is not None and _activity_cache_source_id == skull_source_id:
        return

    activities: list[Activity] = []
    for definition in config_loader.get_activity_definitions():
        duration = definition.get("duration", definition.get("slots"))
        if duration is None:
            raise ValueError(f"Activity '{definition.get('name', '<unknown>')}' is missing duration in SKULL")

        activities.append(
            Activity(
                name=definition["name"],
                slots=duration,
                zone=_parse_zone(definition["zone"]),
                staff=definition.get("staff_needed"),
                conflicts_with=list(definition.get("conflicts_with", [])),
            )
        )

    _activity_cache = activities
    _activity_lookup = {activity.name: activity for activity in activities}
    _activity_cache_source_id = skull_source_id


def get_all_activities() -> list[Activity]:
    """Return the full activity catalog from SKULL."""
    _ensure_activity_cache()
    return list(_activity_cache or [])


def get_activity_by_name(name: str) -> Activity | None:
    """Find an activity by name using the SKULL-backed cache."""
    _ensure_activity_cache()
    if _activity_lookup is None:
        return None
    return _activity_lookup.get(name)
