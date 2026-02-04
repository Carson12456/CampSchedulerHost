"""
Activity definitions for Camp Ten Chiefs.
"""
from models import Activity, Zone


def get_all_activities() -> list[Activity]:
    """Returns all camp activities with their properties."""
    
    activities = [
        # Beach Zone - Unstaffed
        Activity("9 Square", 1, Zone.BEACH),
        Activity("Gaga Ball", 1, Zone.BEACH),
        Activity("Fishing", 1, Zone.BEACH),
        Activity("Sauna", 1, Zone.BEACH),
        Activity("Shower House", 1, Zone.BEACH),
        Activity("Trading Post", 1, Zone.BEACH),
        
        # Beach Zone - Staffed (2+ beach staff)
        Activity("Aqua Trampoline", 1, Zone.BEACH, "Beach Staff"),
        Activity("Troop Canoe", 1, Zone.BEACH, "Beach Staff"),
        Activity("Troop Kayak", 1, Zone.BEACH, "Beach Staff"),
        Activity("Canoe Snorkel", 2, Zone.BEACH, "Beach Staff"),
        Activity("Float for Floats", 2, Zone.BEACH, "Beach Staff"),
        Activity("Greased Watermelon", 1, Zone.BEACH, "Beach Staff"),
        Activity("Underwater Obstacle Course", 1, Zone.BEACH, "Beach Staff", ["Troop Swim"]),
        Activity("Troop Swim", 1, Zone.BEACH, "Beach Staff", ["Underwater Obstacle Course"]),
        Activity("Water Polo", 1, Zone.BEACH, "Beach Staff"),
        Activity("Nature Canoe", 1, Zone.BEACH, "Nature Director"),
        
        # Beach Zone - Director staffed
        Activity("Sailing", 1.5, Zone.BEACH, "Boats Director"),  # 1.5 slots = 90 min
        Activity("Dr. DNA", 1, Zone.BEACH, "Nature Director"),
        Activity("Loon Lore", 1, Zone.BEACH, "Nature Director"),
        Activity("Hemp Craft", 1, Zone.BEACH, "Handicrafts Director"),
        Activity("Monkey's Fist", 1, Zone.BEACH, "Handicrafts Director"),
        Activity("Tie Dye", 1, Zone.BEACH, "Handicrafts Director"),
        Activity("Woggle Neckerchief Slide", 1, Zone.BEACH, "Handicrafts Director"),
        Activity("Archery", 1, Zone.BEACH, "Commissioner"),
        Activity("Troop Rifle", 1, Zone.BEACH, "Shooting Sports Director", ["Troop Shotgun"]),
        Activity("Troop Shotgun", 1, Zone.BEACH, "Shooting Sports Director", ["Troop Rifle"]),
        
        # Tower Zone
        Activity("Climbing Tower", 1, Zone.TOWER, "Climbing Tower Director"),  # Duration varies by troop size
        
        # Outdoor Skills Zone
        Activity("Chopped!", 1, Zone.OUTDOOR_SKILLS, "Outdoor Skills Director"),
        Activity("GPS & Geocaching", 1, Zone.OUTDOOR_SKILLS, "Outdoor Skills Director"),
        Activity("Knots and Lashings", 1, Zone.OUTDOOR_SKILLS, "Outdoor Skills Director"),
        Activity("Orienteering", 1, Zone.OUTDOOR_SKILLS, "Outdoor Skills Director"),
        Activity("Ultimate Survivor", 1, Zone.OUTDOOR_SKILLS, "Outdoor Skills Director"),
        Activity("What's Cooking", 1, Zone.OUTDOOR_SKILLS, "Outdoor Skills Director"),
        
        # Delta Zone
        Activity("Delta", 1, Zone.DELTA, "Commissioner"),
        
        # Trading Post
        Activity("Super Troop", 1, Zone.BEACH, "Commissioner"),  # Ideally Commissioner
        
        # Off-camp
        Activity("Back of the Moon", 3, Zone.OFF_CAMP, "Staff"),
        Activity("Disc Golf", 1, Zone.OFF_CAMP),
        Activity("Itasca State Park", 3, Zone.OFF_CAMP),
        Activity("Tamarac Wildlife Refuge", 3, Zone.OFF_CAMP),
        
        # Campsite
        Activity("Campsite Free Time", 1, Zone.CAMPSITE),
        Activity("Reflection", 1, Zone.CAMPSITE, "Commissioner"),  # Friday only
        
        # Other
        Activity("History Center", 1, Zone.OFF_CAMP),  # Off-camp location
        
        # Nature Activities (Nature Director)
        Activity("Ecosystem in a Jar", 1, Zone.BEACH, "Nature Director"),
        Activity("Nature Salad", 1, Zone.BEACH, "Nature Director"),
        Activity("Nature Bingo", 1, Zone.BEACH, "Nature Director"),
    ]
    
    return activities


def get_activity_by_name(name: str) -> Activity | None:
    """Find an activity by name."""
    for activity in get_all_activities():
        if activity.name == name:
            return activity
    return None
