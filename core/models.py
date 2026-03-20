"""
Summer Camp Scheduler - Data Models
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# Import config_loader locally in methods to avoid circular imports if necessary, 
# or rely on runtime loading. We'll use local imports for safety.


class Zone(str, Enum):
    DELTA = "Delta"
    BEACH = "Beach"
    OUTDOOR_SKILLS = "Outdoor Skills"
    TOWER = "Tower"
    OFF_CAMP = "Off-camp"
    CAMPSITE = "Campsite"


class Day(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"


class Activity(BaseModel):
    """Represents a camp activity."""
    name: str
    slots: float = Field(..., description="Duration in slots (1, 1.5, 2, or 3)")
    zone: Zone
    staff: Optional[str] = None  # None means unstaffed
    conflicts_with: List[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)  # Make it hashable

    def __init__(self, *args, **kwargs):
        # Legacy compatibility: allow positional construction
        if args:
            arg_keys = ("name", "slots", "zone", "staff", "conflicts_with")
            for idx, value in enumerate(args):
                if idx < len(arg_keys) and arg_keys[idx] not in kwargs:
                    kwargs[arg_keys[idx]] = value
        super().__init__(**kwargs)

    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Activity):
            return self.name == other.name
        return False


class TimeSlot(BaseModel):
    """Represents a time slot in the schedule."""
    day: Day
    slot_number: int

    model_config = ConfigDict(frozen=True)

    def __init__(self, *args, **kwargs):
        # Legacy compatibility: allow TimeSlot(day, slot_number)
        if args:
            if len(args) >= 1 and "day" not in kwargs:
                kwargs["day"] = args[0]
            if len(args) >= 2 and "slot_number" not in kwargs:
                kwargs["slot_number"] = args[1]
        super().__init__(**kwargs)

    def __hash__(self):
        return hash((self.day, self.slot_number))
    
    def __eq__(self, other):
        if isinstance(other, TimeSlot):
            return self.day == other.day and self.slot_number == other.slot_number
        return False
    
    def __repr__(self):
        return f"{self.day.value[:3]}-{self.slot_number}"
    
    def __str__(self):
        return self.__repr__()


class Troop(BaseModel):
    """Represents a troop with their preferences."""
    name: str
    campsite: str
    preferences: List[str]
    scouts: int = 10
    adults: int = 2
    commissioner: str = ""
    day_requests: Dict[str, List[str]] = Field(default_factory=dict)
    
    model_config = ConfigDict(arbitrary_types_allowed=True) # Allow flexible types if needed

    def __init__(self, *args, **kwargs):
        # Legacy compatibility: allow positional construction
        if args:
            arg_keys = (
                "name",
                "campsite",
                "preferences",
                "scouts",
                "adults",
                "commissioner",
                "day_requests",
            )
            for idx, value in enumerate(args):
                if idx < len(arg_keys) and arg_keys[idx] not in kwargs:
                    kwargs[arg_keys[idx]] = value
        super().__init__(**kwargs)

    @property
    def size(self) -> int:
        """Total troop size (scouts + adults)."""
        return self.scouts + self.adults
    
    @property
    def size_category(self) -> str:
        """Size category based on scout count."""
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
        return self.scouts >= 25
    
    def get_priority(self, activity_name: str) -> int:
        try:
            return self.preferences.index(activity_name)
        except ValueError:
            return 999


class ScheduleEntry(BaseModel):
    """A single entry in the schedule."""
    time_slot: TimeSlot
    activity: Activity
    troop: Troop
    
    model_config = ConfigDict(frozen=True)

    def __init__(self, *args, **kwargs):
        # Legacy compatibility:
        # - ScheduleEntry(time_slot, activity, troop)
        # - ScheduleEntry(troop, activity, time_slot) (mis-ordered usage in tests)
        if args and not kwargs:
            if len(args) >= 3:
                first, second, third = args[0], args[1], args[2]
                if isinstance(first, TimeSlot):
                    kwargs = {"time_slot": first, "activity": second, "troop": third}
                elif isinstance(third, TimeSlot):
                    kwargs = {"time_slot": third, "activity": second, "troop": first}
                else:
                    kwargs = {"time_slot": first, "activity": second, "troop": third}
        elif args:
            if len(args) >= 1 and "time_slot" not in kwargs:
                kwargs["time_slot"] = args[0]
            if len(args) >= 2 and "activity" not in kwargs:
                kwargs["activity"] = args[1]
            if len(args) >= 3 and "troop" not in kwargs:
                kwargs["troop"] = args[2]
        super().__init__(**kwargs)

    def __hash__(self):
        return hash((self.time_slot, self.activity.name, self.troop.name))
    
    def __eq__(self, other):
        if isinstance(other, ScheduleEntry):
            return (self.time_slot == other.time_slot and 
                   self.activity.name == other.activity.name and
                   self.troop.name == other.troop.name)
        return False


def generate_time_slots() -> List[TimeSlot]:
    """Generate all 14 time slots for the week."""
    slots = []
    for day in Day:
        max_slot = 2 if day == Day.THURSDAY else 3
        for slot_num in range(1, max_slot + 1):
            slots.append(TimeSlot(day=day, slot_number=slot_num))
    return slots


class Schedule(BaseModel):
    """Complete schedule for all troops."""
    entries: List[ScheduleEntry] = Field(default_factory=list)

    def get_all_time_slots(self) -> List[TimeSlot]:
        """Legacy helper used by tests and analyzers."""
        return generate_time_slots()

    def _get_effective_slots(self, activity: Activity, troop: Troop) -> float:
        """Get effective slot duration for activity based on troop size."""
        if activity.name == "Climbing Tower" and hasattr(troop, 'scouts'):
            if troop.scouts > 15:  # 16+ scouts
                return 2.0
        return activity.slots
    
    def add_entry(self, time_slot: TimeSlot, activity: Activity, troop: Troop) -> bool:
        """Add entry for activity with atomic validation."""
        if not self.is_troop_free(time_slot, troop):
            return False
        if not self.is_activity_available(time_slot, activity, troop):
            return False

        effective_slots = self._get_effective_slots(activity, troop)
        slots_needed = int(effective_slots + 0.5)
        
        all_slots = generate_time_slots()
        try:
            start_idx = all_slots.index(time_slot)
        except ValueError:
            return False # Slot not found?

        # Check continuations
        for offset in range(slots_needed):
            if start_idx + offset >= len(all_slots):
                return False
            next_slot = all_slots[start_idx + offset]
            # Must be same day
            if next_slot.day != time_slot.day:
                return False
            if not self.is_troop_free(next_slot, troop):
                return False
        
        # Add entries
        self.entries.append(ScheduleEntry(time_slot=time_slot, activity=activity, troop=troop))
        
        if effective_slots >= 1.5:
             for offset in range(1, slots_needed):
                if start_idx + offset < len(all_slots):
                    next_slot = all_slots[start_idx + offset]
                    if next_slot.day == time_slot.day:
                        self.entries.append(ScheduleEntry(time_slot=next_slot, activity=activity, troop=troop))
        return True
    
    def get_troop_schedule(self, troop: Troop) -> List[ScheduleEntry]:
        return [e for e in self.entries if e.troop.name == troop.name]
    
    def get_slot_activities(self, time_slot: TimeSlot) -> List[ScheduleEntry]:
        return [e for e in self.entries if e.time_slot == time_slot]
    
    def remove_entry(self, entry: ScheduleEntry) -> bool:
        try:
            self.entries.remove(entry)
            return True
        except ValueError:
            return False
    
    def is_activity_available(self, time_slot: TimeSlot, activity: Activity, requesting_troop: Troop = None) -> bool:
        """Check slot availability through the shared rules layer."""
        from core.rules.capacity_rules import CapacityRules  # Lazy import to avoid cycles

        return CapacityRules().can_place_activity(
            time_slot=time_slot,
            activity=activity,
            requesting_troop=requesting_troop,
            existing_entries=self.entries,
        )

    def is_troop_free(self, time_slot: TimeSlot, troop: Troop) -> bool:
        # Check exact slot
        for entry in self.entries:
            if entry.troop.name == troop.name and entry.time_slot == time_slot:
                return False
        
        # Check multi-slot overlap: only consider START entries (skip continuations)
        troop_entries = self.get_troop_schedule(troop)
        for entry in troop_entries:
            if entry.time_slot.day != time_slot.day:
                continue
            effective_slots = self._get_effective_slots(entry.activity, entry.troop)
            if effective_slots <= 1.0:
                continue
            # Skip if this is a continuation (earlier slot exists for same troop/activity/day)
            is_start = not any(
                e.activity.name == entry.activity.name and e.time_slot.slot_number < entry.time_slot.slot_number
                for e in troop_entries if e.time_slot.day == entry.time_slot.day
            )
            if not is_start:
                continue
            start_slot = entry.time_slot.slot_number
            slots_occupied = int(effective_slots + 0.5)
            max_slot = 2 if time_slot.day == Day.THURSDAY else 3
            end_slot = min(start_slot + slots_occupied - 1, max_slot)
            if start_slot <= time_slot.slot_number <= end_slot:
                return False
        return True

    # Delegates
    def get_troop_entries(self, troop: Troop) -> List[ScheduleEntry]:
        return self.get_troop_schedule(troop)

    def get_entry(self, troop: Troop, time_slot: TimeSlot) -> Optional[ScheduleEntry]:
        for entry in self.entries:
            if entry.troop.name == troop.name and entry.time_slot == time_slot:
                return entry
        return None
    
    def get_troop_activities(self, troop: Troop) -> List[Activity]:
        return [e.activity for e in self.get_troop_entries(troop)]
    
    @property
    def troops(self) -> List[Troop]:
        # Dedup by name
        seen = set()
        unique = []
        for e in self.entries:
            if e.troop.name not in seen:
                seen.add(e.troop.name)
                unique.append(e.troop)
        return unique

