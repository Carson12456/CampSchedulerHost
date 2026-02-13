"""
Activity definitions for Camp Ten Chiefs.
"""
from .models import Activity, Zone


def get_all_activities() -> list[Activity]:
    """Returns all camp activities with their properties."""
    
    activities = [
        # Beach Zone - Unstaffed
        Activity(name="9 Square", slots=1, zone=Zone.BEACH),
        Activity(name="Gaga Ball", slots=1, zone=Zone.BEACH),
        Activity(name="Fishing", slots=1, zone=Zone.BEACH),
        Activity(name="Sauna", slots=1, zone=Zone.BEACH),
        Activity(name="Shower House", slots=1, zone=Zone.BEACH),
        Activity(name="Trading Post", slots=1, zone=Zone.BEACH),
        
        # Beach Zone - Staffed (2+ beach staff)
        Activity(name="Aqua Trampoline", slots=1, zone=Zone.BEACH, staff="Beach Staff"),
        Activity(name="Troop Canoe", slots=1, zone=Zone.BEACH, staff="Beach Staff"),
        Activity(name="Troop Kayak", slots=1, zone=Zone.BEACH, staff="Beach Staff"),
        Activity(name="Canoe Snorkel", slots=2, zone=Zone.BEACH, staff="Beach Staff"),
        Activity(name="Float for Floats", slots=2, zone=Zone.BEACH, staff="Beach Staff"),
        Activity(name="Greased Watermelon", slots=1, zone=Zone.BEACH, staff="Beach Staff"),
        Activity(name="Underwater Obstacle Course", slots=1, zone=Zone.BEACH, staff="Beach Staff", conflicts_with=["Troop Swim"]),
        Activity(name="Troop Swim", slots=1, zone=Zone.BEACH, staff="Beach Staff", conflicts_with=["Underwater Obstacle Course"]),
        Activity(name="Water Polo", slots=1, zone=Zone.BEACH, staff="Beach Staff"),
        Activity(name="Nature Canoe", slots=1, zone=Zone.BEACH, staff="Nature Director"),
        
        # Beach Zone - Director staffed
        Activity(name="Sailing", slots=1.5, zone=Zone.BEACH, staff="Boats Director"),  # 1.5 slots = 90 min
        Activity(name="Dr. DNA", slots=1, zone=Zone.BEACH, staff="Nature Director"),
        Activity(name="Loon Lore", slots=1, zone=Zone.BEACH, staff="Nature Director"),
        Activity(name="Hemp Craft", slots=1, zone=Zone.BEACH, staff="Handicrafts Director"),
        Activity(name="Monkey's Fist", slots=1, zone=Zone.BEACH, staff="Handicrafts Director"),
        Activity(name="Tie Dye", slots=1, zone=Zone.BEACH, staff="Handicrafts Director"),
        Activity(name="Woggle Neckerchief Slide", slots=1, zone=Zone.BEACH, staff="Handicrafts Director"),
        Activity(name="Archery", slots=1, zone=Zone.BEACH, staff="Commissioner"),
        Activity(name="Troop Rifle", slots=1, zone=Zone.BEACH, staff="Shooting Sports Director", conflicts_with=["Troop Shotgun"]),
        Activity(name="Troop Shotgun", slots=1, zone=Zone.BEACH, staff="Shooting Sports Director", conflicts_with=["Troop Rifle"]),
        
        # Tower Zone
        Activity(name="Climbing Tower", slots=1, zone=Zone.TOWER, staff="Climbing Tower Director"),  # Duration varies by troop size
        
        # Outdoor Skills Zone
        Activity(name="Chopped!", slots=1, zone=Zone.OUTDOOR_SKILLS, staff="Outdoor Skills Director"),
        Activity(name="GPS & Geocaching", slots=1, zone=Zone.OUTDOOR_SKILLS, staff="Outdoor Skills Director"),
        Activity(name="Knots and Lashings", slots=1, zone=Zone.OUTDOOR_SKILLS, staff="Outdoor Skills Director"),
        Activity(name="Orienteering", slots=1, zone=Zone.OUTDOOR_SKILLS, staff="Outdoor Skills Director"),
        Activity(name="Ultimate Survivor", slots=1, zone=Zone.OUTDOOR_SKILLS, staff="Outdoor Skills Director"),
        Activity(name="What's Cooking", slots=1, zone=Zone.OUTDOOR_SKILLS, staff="Outdoor Skills Director"),
        
        # Delta Zone
        Activity(name="Delta", slots=1, zone=Zone.DELTA, staff="Commissioner"),
        
        # Trading Post
        Activity(name="Super Troop", slots=1, zone=Zone.BEACH, staff="Commissioner"),  # Ideally Commissioner
        
        # Off-camp
        Activity(name="Back of the Moon", slots=3, zone=Zone.OFF_CAMP, staff="Staff"),
        Activity(name="Disc Golf", slots=1, zone=Zone.OFF_CAMP),
        Activity(name="Itasca State Park", slots=3, zone=Zone.OFF_CAMP),
        Activity(name="Tamarac Wildlife Refuge", slots=3, zone=Zone.OFF_CAMP),
        
        # Campsite
        Activity(name="Campsite Free Time", slots=1, zone=Zone.CAMPSITE),
        Activity(name="Reflection", slots=1, zone=Zone.CAMPSITE, staff="Commissioner"),  # Friday only
        
        # Other
        Activity(name="History Center", slots=1, zone=Zone.OFF_CAMP),  # Off-camp location
        
        # Nature Activities (Nature Director)
        Activity(name="Ecosystem in a Jar", slots=1, zone=Zone.BEACH, staff="Nature Director"),
        Activity(name="Nature Salad", slots=1, zone=Zone.BEACH, staff="Nature Director"),
        Activity(name="Nature Bingo", slots=1, zone=Zone.BEACH, staff="Nature Director"),
    ]
    
    return activities


def get_activity_by_name(name: str) -> Activity | None:
    """Find an activity by name."""
    for activity in get_all_activities():
        if activity.name == name:
            return activity
    return None
