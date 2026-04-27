"""
Activity definitions for Camp Ten Chiefs.
"""
from .models import Activity, Zone


def get_all_activities() -> list[Activity]:
    """Return all camp activities from SKULL.json."""
    from .scheduler import config_loader

    conflict_map: dict[str, list[str]] = {}
    for pair in config_loader.get_prohibited_pairs():
        if len(pair) != 2:
            continue
        left, right = pair
        conflict_map.setdefault(left, []).append(right)
        conflict_map.setdefault(right, []).append(left)

    activities = []
    for activity_data in config_loader.get_activity_definitions():
        name = activity_data["name"]
        zone = Zone[activity_data["zone"]]
        activities.append(
            Activity(
                name=name,
                slots=activity_data["duration"],
                zone=zone,
                staff=activity_data.get("staff_needed"),
                conflicts_with=conflict_map.get(name, []),
            )
        )

    return activities


def get_activity_by_name(name: str) -> Activity | None:
    """Find an activity by name."""
    for activity in get_all_activities():
        if activity.name == name:
            return activity
    return None
