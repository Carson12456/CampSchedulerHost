"""
Schedule Optimizer for Summer Camp Scheduler.

Provides post-scheduling optimization passes: clustering consolidation,
excess day reduction, staff balancing, and preference-improving swaps.

NOTE: This is a facade layer. The actual optimization logic remains in
ConstrainedScheduler for now. This module provides:
1. A clean interface for optimization operations
2. Statistics and reporting on optimization results
3. Future home for extracted optimization methods
"""
from typing import Dict, List, Any, TYPE_CHECKING
from collections import defaultdict

from core.scheduler.config_loader import get_exclusive_areas

if TYPE_CHECKING:
    from core.models import Schedule, Troop, Day


class ScheduleOptimizer:
    """
    High-level optimizer for camp schedules.
    
    Current implementation: Wraps optimization calls to ConstrainedScheduler.
    Future implementation: Contains extracted optimization logic directly.
    """
    
    def __init__(self, schedule: 'Schedule', troops: List['Troop']):
        self.schedule = schedule
        self.troops = troops
    
    # === Clustering Analysis ===
    
    def get_clustering_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze current clustering efficiency for each exclusive area.
        
        Returns dict of area_name -> {
            'days_used': int,
            'target_days': int,
            'excess_days': int,
            'activities_scheduled': int,
            'activities_by_day': {day: count}
        }
        """
        from core.models import Day
        
        stats = {}
        exclusive_areas = get_exclusive_areas()
        
        for area, activities in exclusive_areas.items():
            day_counts = defaultdict(int)
            total = 0
            
            for entry in self.schedule.entries:
                if entry.activity.name in activities:
                    day_counts[entry.time_slot.day.name] += 1
                    total += 1
            
            if total == 0:
                continue
            
            days_used = len(day_counts)
            # Target: ceil(total / 3) days (at least 3 activities per cluster day)
            target_days = max(2, (total + 2) // 3)
            
            stats[area] = {
                'days_used': days_used,
                'target_days': target_days,
                'excess_days': max(0, days_used - target_days),
                'activities_scheduled': total,
                'activities_by_day': dict(day_counts),
            }
        
        return stats
    
    def get_total_excess_cluster_days(self) -> int:
        """Get total excess cluster days across all areas."""
        return sum(s['excess_days'] for s in self.get_clustering_stats().values())
    
    def get_worst_clustered_areas(self, limit: int = 5) -> List[str]:
        """Get the area names with worst clustering (most excess days)."""
        stats = self.get_clustering_stats()
        sorted_areas = sorted(stats.items(), key=lambda x: x[1]['excess_days'], reverse=True)
        return [area for area, s in sorted_areas[:limit] if s['excess_days'] > 0]
    
    # === Staff Distribution Analysis ===
    
    def get_staff_distribution_by_slot(self) -> Dict[str, Dict[int, int]]:
        """
        Get staff counts per slot per day.
        
        Returns dict of day_name -> {slot_number: staff_count}
        """
        from core.scheduler.config_loader import get_staff_needs
        
        staff_needs = get_staff_needs()
        distribution = defaultdict(lambda: defaultdict(int))
        
        for entry in self.schedule.entries:
            day_name = entry.time_slot.day.name
            slot_num = entry.time_slot.slot_number
            staff = staff_needs.get(entry.activity.name, 0)
            distribution[day_name][slot_num] += staff
        
        return {day: dict(slots) for day, slots in distribution.items()}
    
    def get_staff_variance(self) -> float:
        """Calculate variance of staff distribution across all slots."""
        dist = self.get_staff_distribution_by_slot()
        all_counts = [count for slots in dist.values() for count in slots.values()]
        
        if not all_counts:
            return 0.0
        
        mean = sum(all_counts) / len(all_counts)
        variance = sum((x - mean) ** 2 for x in all_counts) / len(all_counts)
        return variance
    
    # === Optimization Reporting ===
    
    def print_optimization_report(self) -> None:
        """Print a summary of optimization opportunities."""
        print("\n--- Optimization Report ---")
        
        # Clustering
        excess = self.get_total_excess_cluster_days()
        print(f"  Excess Cluster Days: {excess}")
        worst = self.get_worst_clustered_areas(3)
        if worst:
            print(f"  Worst Areas: {', '.join(worst)}")
        
        # Staff variance
        variance = self.get_staff_variance()
        print(f"  Staff Variance: {variance:.2f}")
        
        print("---------------------------\n")
