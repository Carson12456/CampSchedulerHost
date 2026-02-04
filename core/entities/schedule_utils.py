"""
Utility functions for schedule entities
Pure domain utilities with no external dependencies
"""
from typing import List

from .time_slot import TimeSlot, Day


def generate_time_slots() -> List[TimeSlot]:
    """
    Generate all 14 time slots for the week.
    
    Returns:
        List of TimeSlot objects representing all available slots
    """
    slots = []
    for day in Day:
        max_slot = 2 if day == Day.THURSDAY else 3
        for slot_num in range(1, max_slot + 1):
            slots.append(TimeSlot(day, slot_num))
    return slots


def get_slots_for_day(day: Day) -> List[TimeSlot]:
    """
    Get all time slots for a specific day.
    
    Args:
        day: The day to get slots for
        
    Returns:
        List of TimeSlot objects for the specified day
    """
    max_slot = 2 if day == Day.THURSDAY else 3
    return [TimeSlot(day, slot_num) for slot_num in range(1, max_slot + 1)]


def get_day_name(day: Day) -> str:
    """
    Get the full name of a day.
    
    Args:
        day: Day enum value
        
    Returns:
        Full day name as string
    """
    return day.value


def get_day_abbreviation(day: Day) -> str:
    """
    Get the 3-letter abbreviation of a day.
    
    Args:
        day: Day enum value
        
    Returns:
        3-letter day abbreviation as string
    """
    return day.value[:3]
