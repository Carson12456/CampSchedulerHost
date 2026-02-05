"""
Performance Caching System for Scheduler
Reduces redundant calculations and lookups
"""
from functools import lru_cache
from typing import Optional, Set, Dict, Tuple, Any
from collections import defaultdict


class SchedulerCache:
    """
    Intelligent caching system for scheduler operations
    Caches constraint checks, lookups, and computed properties
    """
    
    def __init__(self):
        # Activity lookups
        self._activity_by_name = {}  # name -> Activity
        self._activities_by_zone = defaultdict(list)  # zone -> [Activities]
        self._activities_by_staff = defaultdict(list)  # staff -> [Activities]
        
        # Troop lookups
        self._troop_by_name = {}  # name -> Troop
        self._troop_commissioner = {}  # troop_name -> commissioner
        self._troops_by_commissioner = defaultdict(list)  # commissioner -> [Troops]
        
        # Constraint check cache
        # Key: (troop_name, activity_name, day, slot_num, schedule_version)
        self._constraint_cache = {}
        self._schedule_version = 0  # Increment when schedule changes
        
        # Computed properties cache
        self._troop_activities_cache = {}  # troop_name -> set of activity names
        self._day_activities_cache = {}  # day -> set of activity names
        self._slot_occupancy_cache = {}  # (day, slot_num) -> set of troop names
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    def initialize_activities(self, activities: list):
        """Load all activities into cache"""
        self._activity_by_name.clear()
        self._activities_by_zone.clear()
        self._activities_by_staff.clear()
        
        for activity in activities:
            self._activity_by_name[activity.name] = activity
            self._activities_by_zone[activity.zone].append(activity)
            if activity.staff:
                self._activities_by_staff[activity.staff].append(activity)
    
    def initialize_troops(self, troops: list, commissioner_map: dict):
        """Load all troops into cache"""
        self._troop_by_name.clear()
        self._troop_commissioner.clear()
        self._troops_by_commissioner.clear()
        
        for troop in troops:
            self._troop_by_name[troop.name] = troop
            commissioner = commissioner_map.get(troop.name)
            if commissioner:
                self._troop_commissioner[troop.name] = commissioner
                self._troops_by_commissioner[commissioner].append(troop)
    
    def get_activity(self, name: str):
        """Fast activity lookup by name"""
        return self._activity_by_name.get(name)
    
    def get_activities_by_zone(self, zone):
        """Get all activities in a zone"""
        return self._activities_by_zone.get(zone, [])
    
    def get_activities_by_staff(self, staff: str):
        """Get all activities run by a staff member"""
        return self._activities_by_staff.get(staff, [])
    
    def get_troop(self, name: str):
        """Fast troop lookup by name"""
        return self._troop_by_name.get(name)
    
    def get_commissioner(self, troop_name: str) -> Optional[str]:
        """Fast commissioner lookup for troop"""
        if troop_name in self._troop_commissioner:
            self.hits += 1
            return self._troop_commissioner[troop_name]
        self.misses += 1
        return None
    
    def get_troops_by_commissioner(self, commissioner: str):
        """Get all troops assigned to a commissioner"""
        return self._troops_by_commissioner.get(commissioner, [])
    
    def invalidate_schedule_caches(self):
        """Call this whenever the schedule changes"""
        self._schedule_version += 1
        self._constraint_cache.clear()
        self._troop_activities_cache.clear()
        self._day_activities_cache.clear()
        self._slot_occupancy_cache.clear()
    
    def cache_constraint_check(
        self, 
        troop_name: str, 
        activity_name: str, 
        day: str, 
        slot_num: int, 
        result: bool
    ):
        """Cache a constraint check result"""
        key = (troop_name, activity_name, day, slot_num, self._schedule_version)
        self._constraint_cache[key] = result
    
    def get_cached_constraint_check(
        self, 
        troop_name: str, 
        activity_name: str, 
        day: str, 
        slot_num: int
    ) -> Optional[bool]:
        """Retrieve cached constraint check result"""
        key = (troop_name, activity_name, day, slot_num, self._schedule_version)
        if key in self._constraint_cache:
            self.hits += 1
            return self._constraint_cache[key]
        self.misses += 1
        return None
    
    def cache_troop_activities(self, troop_name: str, activities: Set[str]):
        """Cache the set of activities a troop has scheduled"""
        self._troop_activities_cache[troop_name] = activities.copy()
    
    def get_cached_troop_activities(self, troop_name: str) -> Optional[Set[str]]:
        """Get cached set of troop's activities"""
        if troop_name in self._troop_activities_cache:
            self.hits += 1
            return self._troop_activities_cache[troop_name]
        self.misses += 1
        return None
    
    def cache_day_activities(self, day: str, activities: Set[str]):
        """Cache the set of activities happening on a day"""
        self._day_activities_cache[day] = activities.copy()
    
    def get_cached_day_activities(self, day: str) -> Optional[Set[str]]:
        """Get cached set of activities on a day"""
        if day in self._day_activities_cache:
            self.hits += 1
            return self._day_activities_cache[day]
        self.misses += 1
        return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'schedule_version': self._schedule_version,
            'constraint_cache_size': len(self._constraint_cache),
            'troop_cache_size': len(self._troop_by_name),
            'activity_cache_size': len(self._activity_by_name),
        }
    
    def print_stats(self):
        """Print cache statistics"""
        stats = self.get_cache_stats()
        print("\n" + "=" * 70)
        print("CACHE PERFORMANCE STATISTICS")
        print("=" * 70)
        print(f"  Cache Hits:           {stats['hits']:,}")
        print(f"  Cache Misses:         {stats['misses']:,}")
        print(f"  Total Requests:       {stats['total_requests']:,}")
        print(f"  Hit Rate:             {stats['hit_rate']}")
        print(f"  Schedule Version:     {stats['schedule_version']}")
        print(f"  Constraint Cache:     {stats['constraint_cache_size']} entries")
        print(f"  Activities Cached:    {stats['activity_cache_size']}")
        print(f"  Troops Cached:        {stats['troop_cache_size']}")
        print("=" * 70)
    
    def clear_all(self):
        """Clear all caches"""
        self._activity_by_name.clear()
        self._activities_by_zone.clear()
        self._activities_by_staff.clear()
        self._troop_by_name.clear()
        self._troop_commissioner.clear()
        self._troops_by_commissioner.clear()
        self._constraint_cache.clear()
        self._troop_activities_cache.clear()
        self._day_activities_cache.clear()
        self._slot_occupancy_cache.clear()
        self._schedule_version = 0
        self.hits = 0
        self.misses = 0


# Decorator for caching expensive function results
def cache_result(maxsize=128):
    """
    Decorator to cache function results
    
    Usage:
        @cache_result(maxsize=256)
        def expensive_calculation(troop, activity):
            # ... complex logic ...
            return result
    """
    return lru_cache(maxsize=maxsize)


if __name__ == "__main__":
    # Demo/test caching system
    from dataclasses import dataclass
    
    @dataclass
    class MockActivity:
        name: str
        zone: str
        staff: str = None
    
    @dataclass
    class MockTroop:
        name: str
    
    cache = SchedulerCache()
    
    # Test activity caching
    activities = [
        MockActivity("Archery", "Beach", "Archery Director"),
        MockActivity("Tower", "Tower", "Tower Director"),
        MockActivity("Gaga Ball", "Beach"),
    ]
    
    cache.initialize_activities(activities)
    
    print("Testing activity lookups:")
    print(f"  Archery: {cache.get_activity('Archery')}")
    print(f"  Unknown: {cache.get_activity('Unknown')}")
    print(f"  Beach activities: {len(cache.get_activities_by_zone('Beach'))}")
    
    # Test constraint caching
    print("\nTesting constraint caching:")
    cache.cache_constraint_check("Tecumseh", "Archery", "Monday", 1, True)
    result = cache.get_cached_constraint_check("Tecumseh", "Archery", "Monday", 1)
    print(f"  Cached result: {result}")
    
    # Test performance stats
    for i in range(10):
        cache.get_commissioner(f"Troop{i}")  # Misses
    
    cache._troop_commissioner["Troop5"] = "Commissioner A"
    for i in range(5):
        cache.get_commissioner("Troop5")  # Hits
    
    cache.print_stats()
