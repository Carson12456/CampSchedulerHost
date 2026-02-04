"""
Interfaces for Summer Camp Scheduler
Abstract definitions for data access and external services
"""

from .repositories import (
    TroopRepository,
    ScheduleRepository,
    ActivityRepository,
    ConfigRepository
)

__all__ = [
    'TroopRepository',
    'ScheduleRepository',
    'ActivityRepository',
    'ConfigRepository'
]
