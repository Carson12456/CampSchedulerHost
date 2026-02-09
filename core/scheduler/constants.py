"""
Scheduler Constants Module.

Contains all class-level constants for the ConstrainedScheduler.
These are static configuration values that do not change during scheduling.
"""

from ..models import Day


class SchedulerConstants:
    """
    All class-level constants for the scheduler.
    
    Organized by category:
    - Activity lists (what activities belong to which category)
    - Constraint rules (what cannot be scheduled together)
    - Staff counts (how many staff each activity needs)
    - Area mappings (which activities belong to which physical area)
    """
    
    # =========================================================================
    # ACTIVITY LISTS
    # =========================================================================
    
    # Default priority order for filling remaining slots when troop doesn't have enough preferences
    # Note: Gaga Ball and 9 Square are at the END because they're flexible (middle of camp, short duration)
    # Note: Delta is NOT in this list - it's only scheduled for troops who request it in preferences
    DEFAULT_FILL_PRIORITY = [
        "Super Troop",
        "Aqua Trampoline",
        # "Climbing Tower",  # Removed to prevent accidental stacking as fill
        "Archery",
        "Water Polo",
        "Troop Rifle",
        "Gaga Ball",  # Balls last - flexible, middle of camp
        "9 Square",   # Balls last - flexible, middle of camp
        "Troop Swim",
        "Sailing",
        "Trading Post",  # Trading Post / Showerhouse
        "GPS & Geocaching",  # ODS Activity
        # "Disc Golf",  # Removed to prevent orphan entries (needs pair)
        "Hemp Craft",  # Handicrafts (Tie Dye removed - only schedule if requested)
        "Dr. DNA",  # Nature Activity
        "Loon Lore",  # Nature Activity
        "Fishing",
        "Campsite Free Time",  # In site time
    ]
    
    # Activities that can have multiple troops at once
    CONCURRENT_ACTIVITIES = ["Reflection", "Campsite Free Time"]
    
    # Beach activities that should ideally be on different days (soft constraint)
    BEACH_ACTIVITIES = [
        "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
        "Underwater Obstacle Course", "Float for Floats", "Canoe Snorkel"
    ]
    
    # WET activities - cannot have Tower/ODS immediately before or after
    WET_ACTIVITIES = [
        "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim",
        "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
        "Nature Canoe", "Float for Floats", "Sailing", "Sauna"
    ]
    
    # Tower and ODS activities - cannot be scheduled after wet activities
    TOWER_ODS_ACTIVITIES = [
        "Climbing Tower", "Knots and Lashings", "Orienteering", "GPS & Geocaching",
        "Ultimate Survivor", "What's Cooking", "Chopped!"
    ]
    
    # Accuracy activities (max 1 per day per troop)
    ACCURACY_ACTIVITIES = ["Troop Rifle", "Troop Shotgun", "Archery"]
    
    # 3-hour activities
    THREE_HOUR_ACTIVITIES = ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"]
    
    # Activities that don't need consecutive slot optimization
    NON_CONSECUTIVE_ACTIVITIES = [
        "Trading Post", "Campsite Free Time",
        "Itasca State Park", "Tamarac Wildlife Refuge", "Back of the Moon",
        "Disc Golf", "History Center"
    ]
    
    # Spine: "Any pair of: Aqua Trampoline, Water Polo, Greased Watermelon" - prohibited same day
    SPINE_BEACH_PROHIBITED_PAIR = {"Aqua Trampoline", "Water Polo", "Greased Watermelon"}
    
    # Canoe activities
    CANOE_ACTIVITIES = ['Nature Canoe', 'Canoe Snorkel', 'Float for Floats', 'Troop Canoe']
    
    # Beach activities that must follow slot rules (1/3 only, except Thu slot 2)
    BEACH_SLOT_ACTIVITIES = {
        "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
        "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
        "Nature Canoe", "Float for Floats"
        # "Sailing" removed - allowed in slot 2 due to 1.5 slot duration
    }
    
    # Beach activities that require staff (2 staff each)
    BEACH_STAFFED_ACTIVITIES = [
        'Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
        'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
        'Troop Swim', 'Water Polo'
    ]
    
    # ODS activities set for easy checking
    ODS_ACTIVITIES = {
        'Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
        'Ultimate Survivor', "What's Cooking", 'Chopped!'
    }
    
    # Low-priority activities used to fill gaps, can be swapped freely for clustering
    FILL_ACTIVITIES = {
        'Gaga Ball', '9 Square', 'Campsite Free Time', 'Trading Post',
        'Shower House', 'Sauna', 'Aqua Trampoline', 'Water Polo',
        'Greased Watermelon', 'Nature Canoe', 'Dr. DNA', 'Loon Lore'
    }
    
    # Exclusive activities - only 1 troop allowed per slot (limited equipment/safety)
    EXCLUSIVE_ACTIVITIES = {
        'Climbing Tower', 'Troop Rifle', 'Troop Shotgun', 'Archery',
        'Aqua Trampoline', 'Sailing'
    }
    
    # Maximum staff per zone per slot (capacity limits)
    MAX_STAFF_PER_ZONE = {
        'Beach': 6,      # Max 6 beach activities per slot
        'Tower': 1,      # 1 Tower per slot (single tower)
        'Rifle': 2,      # 2 ranges (rifle + shotgun stations)
        'Archery': 2,    # 2 archery ranges
        'ODS': 3,        # 3 concurrent ODS activities
        'Handicrafts': 2, # 2 handicrafts at once
        'Commissioner': 3, # 3 commissioners
    }
    
    # =========================================================================
    # CONSTRAINT RULES
    # =========================================================================

    
    # Activities that cannot be on the same day for a troop (HARD constraints)
    # NOTE: Per BRAIN.md v1.2.0, all prohibited pairs are now SOFT constraints.
    # This list is kept empty. Hard conflicts are enforced via exclusive_areas in SKULL.json.
    SAME_DAY_CONFLICTS = []
    
    # Activities to AVOID on same day (SOFT constraints - try to avoid)
    # NOTE: These now match SKULL.json soft_prohibited_pairs
    SOFT_SAME_DAY_CONFLICTS = [
        ("Trading Post", "Campsite Free Time"),
        ("Trading Post", "Shower House"),
        ("Troop Rifle", "Troop Shotgun"),
        ("Aqua Trampoline", "Water Polo"),
        ("Aqua Trampoline", "Greased Watermelon"),
        ("Water Polo", "Greased Watermelon"),
        ("Troop Canoe", "Canoe Snorkel"),
        ("Troop Canoe", "Nature Canoe"),
        ("Troop Canoe", "Float for Floats"),
        ("Canoe Snorkel", "Nature Canoe"),
        ("Canoe Snorkel", "Float for Floats"),
        ("Nature Canoe", "Float for Floats"),
        ("Fishing", "Trading Post"),
        ("Fishing", "Campsite Free Time"),
        ("Campsite Free Time", "Shower House"),
    ]
    
    # Activities that mildly prefer certain slots (SOFT preference)
    SLOT_PREFERENCES = {
        "Shower House": 3  # Prefer slot 3
    }
    
    # =========================================================================
    # STAFF COUNTS
    # =========================================================================
    
    # Staff count per activity - for total staff balancing across slots
    ACTIVITY_STAFF_COUNT = {
        # Beach Staff (2-3 staff each)
        'Aqua Trampoline': 2, 'Troop Canoe': 2, 'Troop Kayak': 2,
        'Canoe Snorkel': 3, 'Float for Floats': 3, 'Greased Watermelon': 2,
        'Underwater Obstacle Course': 2, 'Troop Swim': 2, 'Water Polo': 2,
        'Nature Canoe': 1,
        # Sailing
        'Sailing': 1,
        # Shooting Sports
        'Troop Rifle': 1, 'Troop Shotgun': 1,
        # Archery
        'Archery': 1,
        # Tower (director + assistant)
        'Climbing Tower': 2,
        # Outdoor Skills
        'Orienteering': 1, 'GPS & Geocaching': 1, 'Knots and Lashings': 1,
        'Ultimate Survivor': 1, "What's Cooking": 1, 'Chopped!': 1,
        # Nature
        'Loon Lore': 1, 'Dr. DNA': 1,
        # Handicrafts
        'Tie Dye': 1, 'Hemp Craft': 1, 'Woggle Neckerchief Slide': 1, "Monkey's Fist": 1,
        # Commissioner Activities
        'Reflection': 1, 'Delta': 1, 'Super Troop': 1,
    }
    
    # Beach staff limit - max staffed activities per slot
    MAX_BEACH_STAFFED_ACTIVITIES = 4
    
    # Canoe capacity - max 13 canoes = 26 people per slot
    MAX_CANOE_CAPACITY = 26
    
    # =========================================================================
    # AREA MAPPINGS
    # =========================================================================
    
    # Area pairs for chain scheduling (when scheduling one, try to chain the other)
    # NOTE: Delta is NOT paired with Tower/ODS - too far to walk between Delta and those areas
    # NOTE: Archery and Sailing are NOT paired - no need for consecutive scheduling
    # NOTE: Boats do NOT need consecutive scheduling
    AREA_PAIRS = {
        "Tower": "Outdoor Skills",
        "Outdoor Skills": "Tower",
        "Rifle Range": "Super Troop",
        "Super Troop": "Rifle Range",
        "Delta": "Sailing",
        "Sailing": "Delta",
        # HC and Disc Golf pair with unstaffed activities for transition time
        "History Center": "Gaga Ball",
        "Disc Golf": "9 Square"
    }
    
    # Staff zone mapping for activities
    STAFF_ZONE_MAP = {
        'Climbing Tower': 'Tower',
        'Troop Rifle': 'Rifle',
        'Troop Shotgun': 'Rifle',
        'Archery': 'Archery',
        'Knots and Lashings': 'ODS',
        'Orienteering': 'ODS',
        'GPS & Geocaching': 'ODS',
        'Ultimate Survivor': 'ODS',
        "What's Cooking": 'ODS',
        'Chopped!': 'ODS',
        'Tie Dye': 'Handicrafts',
        'Hemp Craft': 'Handicrafts',
        'Woggle Neckerchief Slide': 'Handicrafts',
        "Monkey's Fist": 'Handicrafts',
        'Aqua Trampoline': 'Beach',
        'Troop Canoe': 'Beach',
        'Troop Kayak': 'Beach',
        'Canoe Snorkel': 'Beach',
        'Float for Floats': 'Beach',
        'Greased Watermelon': 'Beach',
        'Underwater Obstacle Course': 'Beach',
        'Troop Swim': 'Beach',
        'Water Polo': 'Beach',
        'Nature Canoe': 'Beach',
        'Sailing': 'Beach',
        'Super Troop': 'Commissioner',
        'Delta': 'Commissioner',
    }
    
    # =========================================================================
    # COMMISSIONER CONFIGURATION
    # =========================================================================
    
    # Campsite order - grouped by geographic proximity based on camp map (14 campsites)
    # Northeast (near Delta/Beach): Massasoit, Tecumseh, Samoset, Black Hawk
    # Central (near Lodge/Commons): Taskalusa, Powhatan, Red Cloud, Cochise
    # South (near Tower/Handicrafts): Joseph, Tamanend, Pontiac
    # Far South: Skenandoa, Sequoyah, Roman Nose
    CAMPSITE_ORDER = [
        # North group
        "Massasoit", "Tecumseh", "Samoset", "Black Hawk", "Taskalusa",
        # Mid group
        "Powhatan", "Red Cloud", "Cochise", "Joseph", "Tamanend",
        # South group
        "Pontiac", "Skenandoa", "Sequoyah", "Roman Nose"
    ]
    
    # Commissioner day assignments - each commissioner has separate days for each activity
    # No two commissioners should do the same activity on the same day
    # Note: This includes troops from multiple weeks - unused troops are just ignored
    COMMISSIONER_TROOPS = {
        "Commissioner A": ["Massasoit", "Tecumseh", "Samoset", "Black Hawk", "Taskalusa"],
        "Commissioner B": ["Powhatan", "Red Cloud", "Cochise", "Joseph", "Tamanend"],
        "Commissioner C": ["Pontiac", "Skenandoa", "Sequoyah", "Roman Nose"]
    }
    
    # === AREA PAIR DAY BLOCKING ===
    # Paired areas share the same commissioner day for convenient scheduling
    # No commissioner overlap on any activity pair day
    
    # Delta+Boats - Commissioner Delta days - MATCH Super Troop days for same-day scheduling
    # Delta scheduled in slots 1-2, Super Troop in slot 3
    # EARLY WEEK BIAS: Shifted to Mon/Tue/Wed
    COMMISSIONER_DELTA_DAYS = {
        'Commissioner A': Day.MONDAY,
        'Commissioner B': Day.TUESDAY,
        'Commissioner C': Day.WEDNESDAY
    }
    
    # Commissioner Super Troop days (same as Delta for full commissioner days)
    COMMISSIONER_SUPER_TROOP_DAYS = {
        'Commissioner A': Day.MONDAY,
        'Commissioner B': Day.TUESDAY,
        'Commissioner C': Day.WEDNESDAY
    }
    
    # Archery+Sailing days (Wed/Fri/Mon stagger)
    COMMISSIONER_ARCHERY_DAYS = {
        "Commissioner A": Day.WEDNESDAY,
        "Commissioner B": Day.FRIDAY,
        "Commissioner C": Day.MONDAY
    }
    
    # Tower+ODS days (Thu/Mon/Tue - Friday kept free for reflections)
    COMMISSIONER_TOWER_ODS_DAYS = {
        "Commissioner A": Day.THURSDAY,
        "Commissioner B": Day.MONDAY,
        "Commissioner C": Day.TUESDAY
    }
