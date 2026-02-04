"""
Summer Camp Scheduler - Data Models
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# Activity exclusive areas - only one troop can have activities from each area per slot
EXCLUSIVE_AREAS = {
    "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching", "Ultimate Survivor", 
                      "What's Cooking", "Chopped!"],
    "Tower": ["Climbing Tower"],
    "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
    "Archery": ["Archery"],
    "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
    "Nature Center": ["Dr. DNA", "Loon Lore"],
    # Commissioner-led activities - EXCLUSIVE (one troop at a time per commissioner)
    "Delta": ["Delta"],
    "Super Troop": ["Super Troop"],
    "Sailing": ["Sailing"],  # Sailing IS exclusive - only 1 troop per slot
    # Note: Reflection can have multiple troops (all troops do Reflection on Friday)
    # Note: 3-hour off-camp activities can have multiple troops
    # Beach activities - each exclusive (only one troop per activity per slot)
    "Aqua Trampoline": ["Aqua Trampoline"],
    "Water Polo": ["Water Polo"],
    "Greased Watermelon": ["Greased Watermelon"],
    "Troop Swim": ["Troop Swim"],
    "Float for Floats": ["Float for Floats"],
    "Canoe Snorkel": ["Canoe Snorkel"],
    "Troop Canoe": ["Troop Canoe"],
    "Nature Canoe": ["Nature Canoe"],
    "Fishing": ["Fishing"],
    # Other activities
    "History Center": ["History Center"],
    "Trading Post": ["Trading Post"],
    "Sauna": ["Sauna"],
    "Shower House": ["Shower House"],
    "Disc Golf": ["Disc Golf"],
}



# Beach staff activities - limited to 4 per slot to prevent overcrowding
# These require beach staff supervision (not including unstaffed beach activities)
BEACH_STAFF_ACTIVITIES = {
    "Aqua Trampoline", "Troop Canoe", "Troop Kayak", "Canoe Snorkel", 
    "Float for Floats", "Greased Watermelon", "Underwater Obstacle Course",
    "Troop Swim", "Water Polo", "Nature Canoe", "Sailing"
}
MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT = 4

class Zone(Enum):
    DELTA = "Delta"
    BEACH = "Beach"
    OUTDOOR_SKILLS = "Outdoor Skills"
    TOWER = "Tower"
    OFF_CAMP = "Off-camp"
    CAMPSITE = "Campsite"


class Day(Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"


@dataclass
class Activity:
    """Represents a camp activity."""
    name: str
    slots: float  # 1, 1.5, 2, or 3
    zone: Zone
    staff: Optional[str] = None  # None means unstaffed
    conflicts_with: list[str] = field(default_factory=list)  # Activity names that can't run simultaneously
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Activity):
            return self.name == other.name
        return False


@dataclass
class TimeSlot:
    """Represents a time slot in the schedule."""
    day: Day
    slot_number: int  # 1, 2, or 3 (Tuesday only has 1, 2)
    
    def __hash__(self):
        return hash((self.day, self.slot_number))
    
    def __eq__(self, other):
        if isinstance(other, TimeSlot):
            return self.day == other.day and self.slot_number == other.slot_number
        return False
    
    def __repr__(self):
        return f"{self.day.value[:3]}-{self.slot_number}"



@dataclass
class Troop:
    """Represents a troop with their preferences."""
    name: str
    campsite: str
    preferences: list[str]  # Ranked list of activity names (index 0 = top choice)
    scouts: int = 10  # Number of scouts in troop
    adults: int = 2   # Number of adult leaders
    commissioner: str = ""  # Assigned commissioner (e.g., "Commissioner A")
    day_requests: dict = field(default_factory=dict)  # {"Monday": ["Tie Dye"], "Thursday": ["Itasca"]}
    
    @property
    def size(self) -> int:
        """Total troop size (scouts + adults)."""
        return self.scouts + self.adults
    
    @property
    def size_category(self) -> str:
        """
        Size category based on scout count:
        - Extra Small: 2-5 scouts
        - Small: 6-10 scouts
        - Medium: 11-15 scouts
        - Large: 16-24 scouts
        - Split: 25+ scouts (needs separate schedules)
        """
        if self.scouts <= 5:
            return "Extra Small"
        elif self.scouts <= 10:
            return "Small"
        elif self.scouts <= 15:
            return "Medium"
        elif self.scouts <= 24:
            return "Large"
        else:
            return "Split"
    
    def needs_split(self) -> bool:
        """Troops with 25+ scouts need completely separate schedules."""
        return self.scouts >= 25
    
    def get_priority(self, activity_name: str) -> int:
        """Returns priority (lower is better). Returns 999 if not in preferences."""
        try:
            return self.preferences.index(activity_name)
        except ValueError:
            return 999


@dataclass
class ScheduleEntry:
    """A single entry in the schedule."""
    time_slot: TimeSlot
    activity: Activity
    troop: Troop
    
    def __post_init__(self):
        """Normalize argument order if constructed with wrong parameter order."""
        # Accept mis-ordered construction (troop, activity, slot) and reorder by type
        ts = None
        act = None
        tr = None
        for value in (self.time_slot, self.activity, self.troop):
            if isinstance(value, TimeSlot):
                ts = value
            elif isinstance(value, Activity):
                act = value
            elif isinstance(value, Troop):
                tr = value
        if ts and act and tr:
            self.time_slot = ts
            self.activity = act
            self.troop = tr
    
    def __hash__(self):
        """Make ScheduleEntry hashable for use in sets."""
        return hash((self.time_slot, self.activity.name, self.troop.name))
    
    def __eq__(self, other):
        """Equality check for ScheduleEntry."""
        if isinstance(other, ScheduleEntry):
            return (self.time_slot == other.time_slot and 
                   self.activity.name == other.activity.name and
                   self.troop.name == other.troop.name)
        return False


@dataclass  
class Schedule:
    """Complete schedule for all troops."""
    entries: list[ScheduleEntry] = field(default_factory=list)
    
    def _get_effective_slots(self, activity: Activity, troop: Troop) -> float:
        """Get effective slot duration for activity based on troop size.
        
        Climbing Tower: 16+ scouts = 2.0 slots (spans 2 full slots, otherwise 1 slot)
        """
        if activity.name == "Climbing Tower" and hasattr(troop, 'scouts'):
            if troop.scouts > 15:  # 16+ scouts
                return 2.0  # Full 2 slots (e.g., Mon-1 and Mon-2)
        return activity.slots
    
    def add_entry(self, time_slot: TimeSlot, activity: Activity, troop: Troop) -> bool:
        """Add entry for activity. For 1.5+ slot activities, add continuation entries."""
        # Prevent overlap for the same troop
        if not self.is_troop_free(time_slot, troop):
            return False
        # Prevent double-booking exclusive activities (e.g. two troops in same slot for Climbing Tower)
        if not self.is_activity_available(time_slot, activity, troop):
            return False

        # Get effective slots (may differ from activity.slots based on troop size)
        effective_slots = self._get_effective_slots(activity, troop)
        slots_needed = int(effective_slots + 0.5)
        
        # Ensure continuation slots are also free before adding anything
        all_slots = generate_time_slots()
        start_idx = all_slots.index(time_slot)
        for offset in range(slots_needed):
            if start_idx + offset >= len(all_slots):
                return False
            next_slot = all_slots[start_idx + offset]
            if next_slot.day != time_slot.day:
                return False
            if not self.is_troop_free(next_slot, troop):
                return False
        
        self.entries.append(ScheduleEntry(time_slot, activity, troop))
        
        # For 1.5+ slot activities, add continuation entries  
        if effective_slots >= 1.5:
            if effective_slots == 1.5:
                # For 1.5 slot activities, add one continuation entry
                if start_idx + 1 < len(all_slots):
                    next_slot = all_slots[start_idx + 1]
                    if next_slot.day == time_slot.day:
                        self.entries.append(ScheduleEntry(next_slot, activity, troop))
            else:
                # For 2+ slot activities, add all continuation entries
                for offset in range(1, slots_needed):
                    if start_idx + offset < len(all_slots):
                        next_slot = all_slots[start_idx + offset]
                        if next_slot.day == time_slot.day:
                            self.entries.append(ScheduleEntry(next_slot, activity, troop))
        
        return True
    
    def get_troop_schedule(self, troop: Troop) -> list[ScheduleEntry]:
        """Get all entries for a specific troop."""
        return [e for e in self.entries if e.troop == troop]
    
    def get_slot_activities(self, time_slot: TimeSlot) -> list[ScheduleEntry]:
        """Get all activities scheduled for a time slot."""
        return [e for e in self.entries if e.time_slot == time_slot]
    
    def remove_entry(self, entry: ScheduleEntry) -> bool:
        """Remove a schedule entry."""
        try:
            self.entries.remove(entry)
            return True
        except ValueError:
            return False
    
    def is_activity_available(self, time_slot: TimeSlot, activity: Activity, requesting_troop: Troop = None) -> bool:
        """Check if an activity is available (not already booked) for a time slot.
        
        Special handling for Aqua Trampoline:
        - Troops with ≤16 scouts+adults can share a slot (max 2 small troops)
        - Troops with 17+ scouts+adults need exclusive use of both trampolines
        """
        slot_entries = self.get_slot_activities(time_slot)

        # Reflection can be shared by multiple troops in the same slot
        if activity.name == "Reflection":
            return True
        
        # Find which exclusive area this activity belongs to
        activity_area = None
        for area, activities in EXCLUSIVE_AREAS.items():
            if activity.name in activities:
                activity_area = area
                break
        
        # Cache for performance optimization
        entry_activity_names = [entry.activity.name for entry in slot_entries]
        
        for entry in slot_entries:
            # Special handling for Aqua Trampoline sharing
            if activity.name == "Aqua Trampoline" and entry.activity.name == "Aqua Trampoline":
                # Check if sharing is possible
                existing_troop = entry.troop
                existing_size = (existing_troop.scouts + existing_troop.adults) if hasattr(existing_troop, 'scouts') else 16
                requesting_size = (requesting_troop.scouts + requesting_troop.adults) if requesting_troop and hasattr(requesting_troop, 'scouts') else 16
                
                # Count how many troops already have Aqua Trampoline this slot
                aqua_tramp_count = sum(1 for e in slot_entries if e.activity.name == "Aqua Trampoline")
                
                # Allow sharing if: both troops ≤16 scouts+adults AND only 1 troop so far
                if existing_size <= 16 and requesting_size <= 16 and aqua_tramp_count <= 1:
                    continue  # Allow the share
                else:
                    return False  # Either too big or already 2 troops
            
            # Check if activity is already booked by name (non-shareable) - use cached names
            if entry.activity.name == activity.name:
                # SPECIAL: Water Polo allows up to 2 troops (they play each other)
                if activity.name == "Water Polo":
                    polo_count = entry_activity_names.count("Water Polo")
                    if polo_count < 2:
                        continue
                
                # SPECIAL: Sailing allows 2 per day (1.5 + 1.5 = 3 slots)
                # Sailing is exclusive per slot, not per starting slot
                # Sailing can have: one starting at slot 1 (occupies 1-2), one starting at slot 2 (occupies 2-3)
                # They share slot 2, which is allowed because Sailing is 1.5 slots
                if activity.name == "Sailing":
                    # Check if there's already a Sailing session that occupies this slot on this day
                    # (exclusive per slot, allowing 2 per day with different starting slots)
                    for e in slot_entries:
                        if e.activity.name == "Sailing" and e.troop != requesting_troop:
                            # Find the starting slot for this existing Sailing (lowest slot for this troop/day)
                            day_entries = [ent for ent in self.entries 
                                         if ent.troop == e.troop 
                                         and ent.activity.name == "Sailing"
                                         and ent.time_slot.day == e.time_slot.day]
                            if day_entries:
                                existing_starting_slot = min(day_entries, key=lambda x: x.time_slot.slot_number).time_slot.slot_number
                                # Check if the existing Sailing occupies the slot we're trying to use
                                if existing_starting_slot == 1:  # Existing Sailing starts at 1 (occupies 1-2)
                                    if time_slot.slot_number == 1:
                                        return False  # Cannot have two Sailing sessions starting at Slot 1
                                    # Allow Slot 2 start! They share Slot 2.
                                    
                                elif existing_starting_slot == 2:  # Existing Sailing starts at 2 (occupies 2-3)
                                    if time_slot.slot_number == 2:
                                        return False  # Cannot have two Sailing sessions starting at Slot 2
                                    # Allow Slot 1 start! They share Slot 2.
                    # No slot conflict - either no existing Sailing, or existing doesn't occupy this slot
                    continue

                return False
                
            # Check if another activity from the same exclusive area is booked
            if activity_area:
                for area, activities in EXCLUSIVE_AREAS.items():
                    if area == activity_area and entry.activity.name in activities:
                        return False
            
            # Check explicit conflicts
            if activity.name in entry.activity.conflicts_with:
                return False
            if entry.activity.name in activity.conflicts_with:
                return False
        
        # Check beach staff limit (max 4 staffed beach activities per slot)
        if activity.name in BEACH_STAFF_ACTIVITIES:
            beach_count = sum(1 for name in entry_activity_names if name in BEACH_STAFF_ACTIVITIES)
            if beach_count >= MAX_BEACH_STAFF_ACTIVITIES_PER_SLOT:
                return False
        
        return True
    
    def is_troop_free(self, time_slot: TimeSlot, troop: Troop) -> bool:
        """Check if a troop is free during a time slot.
        
        This checks:
        1. If the troop has an activity starting in this exact slot
        2. If the troop has a multi-slot activity that extends INTO this slot
        """
        # Check if troop has an activity in this exact slot
        for entry in self.entries:
            if entry.troop == troop and entry.time_slot == time_slot:
                return False
        
        # Check if troop has a multi-slot activity that extends into this slot
        # For example, Sailing in slot 1 extends into slot 2
        # Only check original entries, not continuation entries
        troop_entries = self.get_troop_schedule(troop)
        
        # Group entries by activity to find original entries (first occurrence)
        activity_first_occurrence = {}
        for entry in troop_entries:
            activity_key = (entry.activity.name, entry.time_slot.day)
            if activity_key not in activity_first_occurrence or entry.time_slot.slot_number < activity_first_occurrence[activity_key].time_slot.slot_number:
                activity_first_occurrence[activity_key] = entry
        
        for entry in activity_first_occurrence.values():
            if entry.activity.slots > 1:
                # Get the entry's starting slot and calculate which slots it occupies
                start_slot = entry.time_slot
                
                # Only check activities on the same day
                if start_slot.day != time_slot.day:
                    continue
                
                # Calculate how many slots this activity occupies
                # FIX: Use _get_effective_slots to handle dynamic duration (e.g. Large Troop Tower)
                effective_slots = self._get_effective_slots(entry.activity, entry.troop)
                slots_occupied = int(effective_slots + 0.5)  # Round up
                
                # Check if the requested slot falls within the range of occupied slots
                # For example, if Sailing starts at slot 1 and occupies 2 slots (rounds 1.5 up),
                # it occupies slots 1 and 2
                for i in range(slots_occupied):
                    occupied_slot_number = start_slot.slot_number + i
                    if occupied_slot_number == time_slot.slot_number:
                        return False  # This slot is occupied by the multi-slot activity
        
        return True

    # Additional methods needed for Spine implementation
    def get_troop_entries(self, troop: Troop) -> list[ScheduleEntry]:
        """Get all entries for a specific troop (alias for get_troop_schedule)."""
        return self.get_troop_schedule(troop)
    
    def get_entry(self, troop: Troop, time_slot: TimeSlot) -> Optional[ScheduleEntry]:
        """Get the entry for a specific troop and time slot."""
        for entry in self.entries:
            if entry.troop == troop and entry.time_slot == time_slot:
                return entry
        return None
    
    def get_troop_activities(self, troop: Troop) -> list[Activity]:
        """Get all activities for a specific troop."""
        return [entry.activity for entry in self.get_troop_entries(troop)]
    
    def get_troop_activities_for_day(self, troop: Troop, day: Day) -> list[Activity]:
        """Get all activities for a specific troop on a specific day."""
        return [
            entry.activity for entry in self.get_troop_entries(troop)
            if entry.time_slot.day == day
        ]
    
    def get_activity_count(self, activity: Activity, time_slot: TimeSlot) -> int:
        """Get the count of a specific activity in a time slot."""
        return sum(1 for entry in self.get_slot_activities(time_slot) if entry.activity.name == activity.name)
    
    def get_exclusive_activities(self, zone: str, time_slot: TimeSlot) -> list[Activity]:
        """Get all activities in an exclusive area for a time slot."""
        exclusive_activities = []
        if zone in EXCLUSIVE_AREAS:
            zone_activities = EXCLUSIVE_AREAS[zone]
            slot_entries = self.get_slot_activities(time_slot)
            exclusive_activities = [
                entry.activity for entry in slot_entries
                if entry.activity.name in zone_activities
            ]
        return exclusive_activities
    
    def get_remaining_slots_for_troop(self, troop: Troop) -> list[TimeSlot]:
        """Get all remaining slots for a specific troop."""
        all_slots = generate_time_slots()
        occupied_slots = [entry.time_slot for entry in self.get_troop_entries(troop)]
        return [slot for slot in all_slots if slot not in occupied_slots]
    
    def get_all_time_slots(self) -> list[TimeSlot]:
        """Get all time slots."""
        return generate_time_slots()
    
    @property
    def troops(self) -> list[Troop]:
        """Get all troops in the schedule."""
        return list(set(entry.troop for entry in self.entries))


def generate_time_slots() -> list[TimeSlot]:
    """Generate all 14 time slots for the week."""
    slots = []
    for day in Day:
        max_slot = 2 if day == Day.THURSDAY else 3
        for slot_num in range(1, max_slot + 1):
            slots.append(TimeSlot(day, slot_num))
    return slots
