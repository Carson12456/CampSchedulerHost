"""
Enhanced Activity Zone Clustering Optimizer
Improves zone clustering efficiency through advanced algorithms and intelligent activity placement.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, Counter
import random
from typing import List, Dict, Tuple, Optional, Set
import math


class EnhancedClusteringOptimizer:
    """
    Advanced clustering optimizer that maximizes zone efficiency while maintaining
    constraint compliance and preference satisfaction.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Zone definitions
        self.zone_activities = defaultdict(list)
        for entry in self.schedule.entries:
            self.zone_activities[entry.activity.zone].append(entry)
        
        # Clustering metrics
        self.initial_clustering_score = self._calculate_overall_clustering_score()
        
        print(f"  [Enhanced Clustering] Initial clustering score: {self.initial_clustering_score:.3f}")
    
    def optimize_clustering(self, max_iterations: int = 100) -> Dict[str, float]:
        """
        Perform comprehensive clustering optimization.
        """
        print(f"  [Enhanced Clustering] Starting optimization with {max_iterations} iterations...")
        
        improvements = {
            'initial_score': self.initial_clustering_score,
            'final_score': self.initial_clustering_score,
            'improvement': 0.0,
            'swaps_made': 0,
            'zone_improvements': {}
        }
        
        current_score = self.initial_clustering_score
        
        # Phase 1: Aggressive zone consolidation
        print(f"    Phase 1: Aggressive zone consolidation...")
        for iteration in range(max_iterations // 3):
            improvement = self._try_aggressive_zone_consolidation()
            if improvement > 0.01:
                current_score += improvement
                improvements['swaps_made'] += 1
                print(f"      Consolidation {iteration}: +{improvement:.3f}")
        
        # Phase 2: Cross-zone optimization
        print(f"    Phase 2: Cross-zone optimization...")
        for iteration in range(max_iterations // 3):
            improvement = self._try_aggressive_cross_zone_optimization()
            if improvement > 0.01:
                current_score += improvement
                improvements['swaps_made'] += 1
                print(f"      Cross-zone {iteration}: +{improvement:.3f}")
        
        # Phase 3: Activity type clustering
        print(f"    Phase 3: Activity type clustering...")
        for iteration in range(max_iterations // 3):
            improvement = self._try_aggressive_activity_type_clustering()
            if improvement > 0.01:
                current_score += improvement
                improvements['swaps_made'] += 1
                print(f"      Type clustering {iteration}: +{improvement:.3f}")
        
        improvements['final_score'] = current_score
        improvements['improvement'] = current_score - self.initial_clustering_score
        
        # Calculate zone-specific improvements
        for zone in Zone:
            zone_improvement = self._calculate_zone_clustering_score(zone)
            improvements['zone_improvements'][zone.value] = zone_improvement
        
        print(f"  [Enhanced Clustering] Optimization complete:")
        print(f"    Initial score: {improvements['initial_score']:.3f}")
        print(f"    Final score: {improvements['final_score']:.3f}")
        print(f"    Total improvement: {improvements['improvement']:.3f}")
        print(f"    Swaps made: {improvements['swaps_made']}")
        
        return improvements
    
    def _try_aggressive_zone_consolidation(self) -> float:
        """
        Try aggressive zone consolidation to reduce day spread.
        """
        best_improvement = 0.0
        best_swap = None
        
        for zone in Zone:
            zone_entries = self.zone_activities[zone]
            if len(zone_entries) < 2:
                continue
            
            # Find activities spread across multiple days
            day_distribution = defaultdict(list)
            for entry in zone_entries:
                day_distribution[entry.time_slot.day].append(entry)
            
            if len(day_distribution) <= 1:
                continue  # Already perfectly clustered
            
            # Try to consolidate to the most popular day
            most_popular_day = max(day_distribution.keys(), key=lambda d: len(day_distribution[d]))
            
            # Try moving activities to the most popular day
            for source_day, source_entries in day_distribution.items():
                if source_day == most_popular_day:
                    continue
                
                for source_entry in source_entries:
                    # Find any activity on target day that can be swapped
                    target_entries = day_distribution[most_popular_day]
                    for target_entry in target_entries:
                        if self._can_swap_entries(source_entry, target_entry):
                            improvement = self._calculate_swap_clustering_improvement(
                                source_entry, target_entry
                            )
                            
                            # Bonus for consolidation - make it more aggressive
                            consolidation_bonus = 0.2 if source_day != most_popular_day else 0.0
                            total_improvement = improvement + consolidation_bonus
                            
                            if total_improvement > best_improvement:
                                best_improvement = total_improvement
                                best_swap = (source_entry, target_entry)
        
        # Execute best swap
        if best_swap and best_improvement > 0.005:  # Lower threshold for more swaps
            source_entry, target_entry = best_swap
            self._swap_entries(source_entry, target_entry)
            
            # Update zone activities
            self._update_zone_activities()
            
            return best_improvement
        
        return 0.0
    
    def _try_aggressive_cross_zone_optimization(self) -> float:
        """
        Try aggressive cross-zone optimization for better overall clustering.
        """
        best_improvement = 0.0
        best_swap = None
        
        zones = list(Zone)
        for i, zone1 in enumerate(zones):
            for zone2 in zones[i+1:]:
                entries1 = self.zone_activities[zone1]
                entries2 = self.zone_activities[zone2]
                
                if len(entries1) < 1 or len(entries2) < 1:
                    continue
                
                # Calculate current clustering for both zones
                zone1_score_before = self._calculate_zone_clustering_score(zone1)
                zone2_score_before = self._calculate_zone_clustering_score(zone2)
                total_before = zone1_score_before + zone2_score_before
                
                # Try all possible swaps
                for entry1 in entries1[:2]:  # Limit for efficiency
                    for entry2 in entries2[:2]:
                        if self._can_swap_entries(entry1, entry2):
                            # Simulate the swap
                            zone1_score_after = self._simulate_zone_score_after_swap(entry1, entry2, zone1)
                            zone2_score_after = self._simulate_zone_score_after_swap(entry1, entry2, zone2)
                            total_after = zone1_score_after + zone2_score_after
                            
                            improvement = total_after - total_before
                            
                            # Bonus for cross-zone improvements
                            cross_zone_bonus = 0.05 if improvement > 0 else 0.0
                            total_improvement = improvement + cross_zone_bonus
                            
                            if total_improvement > best_improvement:
                                best_improvement = total_improvement
                                best_swap = (entry1, entry2)
        
        # Execute best swap
        if best_swap and best_improvement > 0.005:  # Lower threshold for more swaps
            entry1, entry2 = best_swap
            self._swap_entries(entry1, entry2)
            self._update_zone_activities()
            return best_improvement
        
        return 0.0
    
    def _try_aggressive_activity_type_clustering(self) -> float:
        """
        Try aggressive activity type clustering.
        """
        # Define activity type groups
        activity_types = {
            'water': ['Aqua Trampoline', 'Water Polo', 'Greased Watermelon', 'Troop Swim', 
                     'Underwater Obstacle Course', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                     'Nature Canoe', 'Float for Floats', 'Sailing'],
            'tower': ['Climbing Tower', 'Knots and Lashings'],
            'shooting': ['Troop Rifle', 'Troop Shotgun'],
            'archery': ['Archery'],
            'crafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
            'nature': ['Dr. DNA', 'Fishing'],
            'outdoor': ['Orienteering', 'GPS & Geocaching', 'Ultimate Survivor'],
            'cooking': ["What's Cooking", 'Chopped!']
        }
        
        best_improvement = 0.0
        best_swap = None
        
        # Try to cluster activities of the same type
        for type_name, activity_names in activity_types.items():
            type_entries = []
            for entry in self.schedule.entries:
                if entry.activity.name in activity_names:
                    type_entries.append(entry)
            
            if len(type_entries) < 2:
                continue
            
            # Find the most popular day for this type
            day_distribution = defaultdict(int)
            for entry in type_entries:
                day_distribution[entry.time_slot.day] += 1
            
            if len(day_distribution) <= 1:
                continue  # Already clustered
            
            most_popular_day = max(day_distribution.keys(), key=lambda d: day_distribution[d])
            
            # Try to move type activities to the most popular day
            for entry in type_entries:
                if entry.time_slot.day == most_popular_day:
                    continue
                
                # Find any activity on target day to swap with
                target_day_entries = [e for e in self.schedule.entries 
                                   if e.time_slot.day == most_popular_day and e != entry]
                
                for target_entry in target_day_entries:
                    if self._can_swap_entries(entry, target_entry):
                        improvement = self._calculate_activity_type_clustering_improvement(
                            entry, target_entry, type_name
                        )
                        
                        # Bonus for type clustering
                        type_bonus = 0.08 if improvement > 0 else 0.0
                        total_improvement = improvement + type_bonus
                        
                        if total_improvement > best_improvement:
                            best_improvement = total_improvement
                            best_swap = (entry, target_entry)
        
        # Execute best swap
        if best_swap and best_improvement > 0.005:  # Lower threshold for more swaps
            entry1, entry2 = best_swap
            self._swap_entries(entry1, entry2)
            self._update_zone_activities()
            return best_improvement
        
        return 0.0
    
    def _try_zone_consolidation(self) -> float:
        """
        Try to consolidate activities within zones to reduce day spread.
        """
        best_improvement = 0.0
        best_swap = None
        
        for zone in Zone:
            zone_entries = self.zone_activities[zone]
            if len(zone_entries) < 3:
                continue
            
            # Find activities spread across multiple days
            day_distribution = defaultdict(list)
            for entry in zone_entries:
                day_distribution[entry.time_slot.day].append(entry)
            
            if len(day_distribution) <= 2:
                continue  # Already well clustered
            
            # Try to move activities to consolidate days
            for source_day, source_entries in day_distribution.items():
                if len(source_entries) <= 1:
                    continue
                
                for target_day, target_entries in day_distribution.items():
                    if source_day == target_day:
                        continue
                    
                    # Try moving an activity from source_day to target_day
                    for source_entry in source_entries:
                        for target_entry in target_entries:
                            # Check if swapping improves clustering
                            if self._can_swap_entries(source_entry, target_entry):
                                improvement = self._calculate_swap_clustering_improvement(
                                    source_entry, target_entry
                                )
                                
                                if improvement > best_improvement:
                                    best_improvement = improvement
                                    best_swap = (source_entry, target_entry)
        
        # Execute best swap
        if best_swap and best_improvement > 0.01:
            source_entry, target_entry = best_swap
            self._swap_entries(source_entry, target_entry)
            
            # Update zone activities
            self._update_zone_activities()
            
            return best_improvement
        
        return 0.0
    
    def _try_cross_zone_swapping(self) -> float:
        """
        Try swapping activities between zones to improve overall clustering.
        """
        best_improvement = 0.0
        best_swap = None
        
        zones = list(Zone)
        for i, zone1 in enumerate(zones):
            for zone2 in zones[i+1:]:
                entries1 = self.zone_activities[zone1]
                entries2 = self.zone_activities[zone2]
                
                if len(entries1) < 2 or len(entries2) < 2:
                    continue
                
                # Try swapping activities between zones
                for entry1 in entries1[:3]:  # Limit to first few for efficiency
                    for entry2 in entries2[:3]:
                        if self._can_swap_entries(entry1, entry2):
                            improvement = self._calculate_cross_zone_clustering_improvement(
                                entry1, entry2, zone1, zone2
                            )
                            
                            if improvement > best_improvement:
                                best_improvement = improvement
                                best_swap = (entry1, entry2)
        
        # Execute best swap
        if best_swap and best_improvement > 0.005:  # Lower threshold for more swaps
            entry1, entry2 = best_swap
            self._swap_entries(entry1, entry2)
            self._update_zone_activities()
            return best_improvement
        
        return 0.0
    
    def _try_day_based_clustering(self) -> float:
        """
        Try to cluster activities by day to improve efficiency.
        """
        best_improvement = 0.0
        best_swap = None
        
        # Group activities by day
        day_activities = defaultdict(list)
        for entry in self.schedule.entries:
            day_activities[entry.time_slot.day].append(entry)
        
        # Try to move activities to create better day-based clusters
        for day, entries in day_activities.items():
            if len(entries) < 3:
                continue
            
            # Find zones with activities on this day
            zone_presence = defaultdict(list)
            for entry in entries:
                zone_presence[entry.activity.zone].append(entry)
            
            # Try to consolidate zone activities on this day
            for zone, zone_entries in zone_presence.items():
                if len(zone_entries) <= 1:
                    continue
                
                # Try moving other zone activities to this day
                for other_day, other_entries in day_activities.items():
                    if other_day == day:
                        continue
                    
                    for other_entry in other_entries:
                        if other_entry.activity.zone == zone:
                            continue
                        
                        # Try swapping to improve clustering
                        for zone_entry in zone_entries:
                            if self._can_swap_entries(zone_entry, other_entry):
                                improvement = self._calculate_day_clustering_improvement(
                                    zone_entry, other_entry, day, other_day
                                )
                                
                                if improvement > best_improvement:
                                    best_improvement = improvement
                                    best_swap = (zone_entry, other_entry)
        
        # Execute best swap
        if best_swap and best_improvement > 0.005:  # Lower threshold for more swaps
            entry1, entry2 = best_swap
            self._swap_entries(entry1, entry2)
            self._update_zone_activities()
            return best_improvement
        
        return 0.0
    
    def _try_commissioner_clustering(self) -> float:
        """
        Try to cluster activities by commissioner to improve efficiency.
        """
        # Group by commissioner
        commissioner_activities = defaultdict(list)
        for entry in self.schedule.entries:
            commissioner = self._get_troop_commissioner(entry.troop)
            commissioner_activities[commissioner].append(entry)
        
        best_improvement = 0.0
        best_swap = None
        
        # Try to improve clustering within commissioner groups
        for commissioner, entries in commissioner_activities.items():
            if len(entries) < 4:
                continue
            
            # Try swaps within commissioner's troops
            for i, entry1 in enumerate(entries):
                for entry2 in entries[i+1:]:
                    if self._can_swap_entries(entry1, entry2):
                        improvement = self._calculate_commissioner_clustering_improvement(
                            entry1, entry2, commissioner
                        )
                        
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_swap = (entry1, entry2)
        
        # Execute best swap
        if best_swap and best_improvement > 0.005:  # Lower threshold for more swaps
            entry1, entry2 = best_swap
            self._swap_entries(entry1, entry2)
            self._update_zone_activities()
            return best_improvement
        
        return 0.0
    
    def _try_activity_type_clustering(self) -> float:
        """
        Try to cluster similar activity types together.
        """
        # Define activity type groups
        activity_types = {
            'water': ['Aqua Trampoline', 'Water Polo', 'Greased Watermelon', 'Troop Swim', 
                     'Underwater Obstacle Course', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                     'Nature Canoe', 'Float for Floats', 'Sailing'],
            'tower': ['Climbing Tower', 'Knots and Lashings'],
            'shooting': ['Troop Rifle', 'Troop Shotgun'],
            'archery': ['Archery'],
            'crafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
            'nature': ['Dr. DNA', 'Fishing'],
            'outdoor': ['Orienteering', 'GPS & Geocaching', 'Ultimate Survivor'],
            'cooking': ["What's Cooking", 'Chopped!']
        }
        
        best_improvement = 0.0
        best_swap = None
        
        # Try to cluster activities of the same type
        for type_name, activity_names in activity_types.items():
            type_entries = []
            for entry in self.schedule.entries:
                if entry.activity.name in activity_names:
                    type_entries.append(entry)
            
            if len(type_entries) < 3:
                continue
            
            # Try to bring type activities closer together
            for i, entry1 in enumerate(type_entries):
                for entry2 in type_entries[i+1:]:
                    if self._can_swap_entries(entry1, entry2):
                        improvement = self._calculate_activity_type_clustering_improvement(
                            entry1, entry2, type_name
                        )
                        
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_swap = (entry1, entry2)
        
        # Execute best swap
        if best_swap and best_improvement > 0.005:  # Lower threshold for more swaps
            entry1, entry2 = best_swap
            self._swap_entries(entry1, entry2)
            self._update_zone_activities()
            return best_improvement
        
        return 0.0
    
    def _calculate_overall_clustering_score(self) -> float:
        """
        Calculate overall clustering score across all zones.
        """
        total_score = 0.0
        zone_count = 0
        
        for zone in Zone:
            zone_score = self._calculate_zone_clustering_score(zone)
            total_score += zone_score
            zone_count += 1
        
        return total_score / max(1, zone_count)
    
    def _calculate_zone_clustering_score(self, zone: Zone) -> float:
        """
        Calculate clustering score for a specific zone.
        """
        zone_entries = self.zone_activities[zone]
        if len(zone_entries) < 2:
            return 1.0  # Perfect score for zones with 0-1 activities
        
        # Calculate day distribution
        day_distribution = defaultdict(int)
        for entry in zone_entries:
            day_distribution[entry.time_slot.day] += 1
        
        # Ideal is to have activities concentrated in as few days as possible
        total_activities = len(zone_entries)
        days_used = len(day_distribution)
        
        # Calculate entropy (lower is better for clustering)
        entropy = 0.0
        for count in day_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        # Normalize entropy (max entropy is log2(days_used))
        max_entropy = math.log2(max(2, days_used))
        normalized_entropy = entropy / max_entropy
        
        # Convert to score (lower entropy = higher score)
        clustering_score = 1.0 - normalized_entropy
        
        # Bonus for having activities in consecutive days
        days = sorted(day_distribution.keys(), key=lambda d: d.value if hasattr(d, 'value') else str(d))
        consecutive_bonus = 0.0
        for i in range(len(days) - 1):
            # Handle both Day enum and string values
            try:
                day1_val = days[i].value if hasattr(days[i], 'value') else int(days[i])
                day2_val = days[i+1].value if hasattr(days[i+1], 'value') else int(days[i+1])
                if day2_val - day1_val == 1:
                    consecutive_bonus += 0.1
            except (ValueError, TypeError):
                # Skip if we can't convert to int
                pass
        
        clustering_score = min(1.0, clustering_score + consecutive_bonus)
        
        return clustering_score
    
    def _calculate_swap_clustering_improvement(self, entry1: ScheduleEntry, entry2: ScheduleEntry) -> float:
        """
        Calculate clustering improvement from swapping two entries.
        """
        # Calculate current clustering scores for affected zones
        zone1_score_before = self._calculate_zone_clustering_score(entry1.activity.zone)
        zone2_score_before = self._calculate_zone_clustering_score(entry2.activity.zone)
        
        # Simulate the swap
        zone1_score_after = self._simulate_zone_score_after_swap(entry1, entry2, entry1.activity.zone)
        zone2_score_after = self._simulate_zone_score_after_swap(entry1, entry2, entry2.activity.zone)
        
        # Calculate improvement
        zone1_improvement = zone1_score_after - zone1_score_before
        zone2_improvement = zone2_score_after - zone2_score_before
        
        return zone1_improvement + zone2_improvement
    
    def _calculate_cross_zone_clustering_improvement(self, entry1: ScheduleEntry, entry2: ScheduleEntry, 
                                                   zone1: Zone, zone2: Zone) -> float:
        """
        Calculate clustering improvement from cross-zone swap.
        """
        # This is similar to regular swap but considers cross-zone effects
        return self._calculate_swap_clustering_improvement(entry1, entry2)
    
    def _calculate_day_clustering_improvement(self, entry1: ScheduleEntry, entry2: ScheduleEntry,
                                             day1: Day, day2: Day) -> float:
        """
        Calculate clustering improvement for day-based clustering.
        """
        # Calculate day distribution before and after swap
        day1_before = self._get_day_clustering_score(day1)
        day2_before = self._get_day_clustering_score(day2)
        
        # Simulate swap
        day1_after = self._simulate_day_clustering_score_after_swap(entry1, entry2, day1)
        day2_after = self._simulate_day_clustering_score_after_swap(entry1, entry2, day2)
        
        return (day1_after - day1_before) + (day2_after - day2_before)
    
    def _calculate_commissioner_clustering_improvement(self, entry1: ScheduleEntry, entry2: ScheduleEntry,
                                                      commissioner: str) -> float:
        """
        Calculate clustering improvement for commissioner-based clustering.
        """
        # Calculate commissioner clustering before and after
        before_score = self._get_commissioner_clustering_score(commissioner)
        
        # Simulate swap
        after_score = self._simulate_commissioner_clustering_score_after_swap(
            entry1, entry2, commissioner
        )
        
        return after_score - before_score
    
    def _calculate_activity_type_clustering_improvement(self, entry1: ScheduleEntry, entry2: ScheduleEntry,
                                                        activity_type: str) -> float:
        """
        Calculate clustering improvement for activity type clustering.
        """
        # Calculate type clustering before and after
        before_score = self._get_activity_type_clustering_score(activity_type)
        
        # Simulate swap
        after_score = self._simulate_activity_type_clustering_score_after_swap(
            entry1, entry2, activity_type
        )
        
        return after_score - before_score
    
    def _can_swap_entries(self, entry1: ScheduleEntry, entry2: ScheduleEntry) -> bool:
        """
        Check if two entries can be swapped without violating constraints.
        """
        # Don't swap if same troop
        if entry1.troop == entry2.troop:
            return False
        
        # Don't swap if same activity
        if entry1.activity.name == entry2.activity.name:
            return False
        
        # Check if troops are free at the swapped times
        time1 = entry1.time_slot
        time2 = entry2.time_slot
        
        if not self.schedule.is_troop_free(time1, entry2.troop):
            return False
        
        if not self.schedule.is_troop_free(time2, entry1.troop):
            return False
        
        # Check exclusive activities
        if self._is_exclusive_activity(entry1.activity.name):
            for entry in self.schedule.entries:
                if (entry != entry1 and entry != entry2 and 
                    entry.activity.name == entry1.activity.name and 
                    entry.time_slot == time2):
                    return False
        
        if self._is_exclusive_activity(entry2.activity.name):
            for entry in self.schedule.entries:
                if (entry != entry1 and entry != entry2 and 
                    entry.activity.name == entry2.activity.name and 
                    entry.time_slot == time1):
                    return False
        
        return True
    
    def _swap_entries(self, entry1: ScheduleEntry, entry2: ScheduleEntry):
        """
        Swap two schedule entries.
        """
        # Store original values
        troop1, troop2 = entry1.troop, entry2.troop
        time1, time2 = entry1.time_slot, entry2.time_slot
        
        # Remove entries
        self.schedule.entries.remove(entry1)
        self.schedule.entries.remove(entry2)
        
        # Create new entries with swapped troops and times
        new_entry1 = ScheduleEntry(troop2, entry1.activity, time1)
        new_entry2 = ScheduleEntry(troop1, entry2.activity, time2)
        
        # Add new entries
        self.schedule.entries.append(new_entry1)
        self.schedule.entries.append(new_entry2)
    
    def _update_zone_activities(self):
        """
        Update zone activities mapping after changes.
        """
        self.zone_activities = defaultdict(list)
        for entry in self.schedule.entries:
            self.zone_activities[entry.activity.zone].append(entry)
    
    def _simulate_zone_score_after_swap(self, entry1: ScheduleEntry, entry2: ScheduleEntry, zone: Zone) -> float:
        """
        Simulate zone clustering score after swap.
        """
        # Get current zone entries
        zone_entries = [e for e in self.zone_activities[zone] if e != entry1 and e != entry2]
        
        # Add the entry that would be in this zone after swap
        if entry1.activity.zone == zone:
            zone_entries.append(entry2)
        elif entry2.activity.zone == zone:
            zone_entries.append(entry1)
        
        # Calculate score for simulated entries
        if len(zone_entries) < 2:
            return 1.0
        
        day_distribution = defaultdict(int)
        for entry in zone_entries:
            day_distribution[entry.time_slot.day] += 1
        
        total_activities = len(zone_entries)
        days_used = len(day_distribution)
        
        entropy = 0.0
        for count in day_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        max_entropy = math.log2(max(2, days_used))
        normalized_entropy = entropy / max_entropy
        
        return 1.0 - normalized_entropy
    
    def _get_day_clustering_score(self, day: Day) -> float:
        """
        Calculate clustering score for a specific day.
        """
        day_entries = [e for e in self.schedule.entries if e.time_slot.day == day]
        
        if len(day_entries) < 2:
            return 1.0
        
        # Calculate zone distribution for this day
        zone_distribution = defaultdict(int)
        for entry in day_entries:
            zone_distribution[entry.activity.zone] += 1
        
        # Calculate entropy (lower is better)
        total_activities = len(day_entries)
        entropy = 0.0
        for count in zone_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        max_entropy = math.log2(len(zone_distribution))
        if max_entropy > 0:
            normalized_entropy = entropy / max_entropy
            return 1.0 - normalized_entropy
        
        return 1.0
    
    def _simulate_day_clustering_score_after_swap(self, entry1: ScheduleEntry, entry2: ScheduleEntry, day: Day) -> float:
        """
        Simulate day clustering score after swap.
        """
        day_entries = [e for e in self.schedule.entries 
                      if e.time_slot.day == day and e != entry1 and e != entry2]
        
        # Add entries that would be in this day after swap
        if entry1.time_slot.day == day:
            day_entries.append(entry2)
        elif entry2.time_slot.day == day:
            day_entries.append(entry1)
        
        if len(day_entries) < 2:
            return 1.0
        
        zone_distribution = defaultdict(int)
        for entry in day_entries:
            zone_distribution[entry.activity.zone] += 1
        
        total_activities = len(day_entries)
        entropy = 0.0
        for count in zone_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        max_entropy = math.log2(len(zone_distribution))
        if max_entropy > 0:
            normalized_entropy = entropy / max_entropy
            return 1.0 - normalized_entropy
        
        return 1.0
    
    def _get_commissioner_clustering_score(self, commissioner: str) -> float:
        """
        Calculate clustering score for a specific commissioner.
        """
        commissioner_entries = [e for e in self.schedule.entries 
                               if self._get_troop_commissioner(e.troop) == commissioner]
        
        if len(commissioner_entries) < 2:
            return 1.0
        
        # Calculate zone distribution
        zone_distribution = defaultdict(int)
        for entry in commissioner_entries:
            zone_distribution[entry.activity.zone] += 1
        
        # Calculate entropy
        total_activities = len(commissioner_entries)
        entropy = 0.0
        for count in zone_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        max_entropy = math.log2(len(zone_distribution))
        if max_entropy > 0:
            normalized_entropy = entropy / max_entropy
            return 1.0 - normalized_entropy
        
        return 1.0
    
    def _simulate_commissioner_clustering_score_after_swap(self, entry1: ScheduleEntry, entry2: ScheduleEntry,
                                                          commissioner: str) -> float:
        """
        Simulate commissioner clustering score after swap.
        """
        commissioner_entries = [e for e in self.schedule.entries 
                               if self._get_troop_commissioner(e.troop) == commissioner 
                               and e != entry1 and e != entry2]
        
        # Add entries that would be for this commissioner after swap
        if self._get_troop_commissioner(entry1.troop) == commissioner:
            commissioner_entries.append(entry2)
        elif self._get_troop_commissioner(entry2.troop) == commissioner:
            commissioner_entries.append(entry1)
        
        if len(commissioner_entries) < 2:
            return 1.0
        
        zone_distribution = defaultdict(int)
        for entry in commissioner_entries:
            zone_distribution[entry.activity.zone] += 1
        
        total_activities = len(commissioner_entries)
        entropy = 0.0
        for count in zone_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        max_entropy = math.log2(len(zone_distribution))
        if max_entropy > 0:
            normalized_entropy = entropy / max_entropy
            return 1.0 - normalized_entropy
        
        return 1.0
    
    def _get_activity_type_clustering_score(self, activity_type: str) -> float:
        """
        Calculate clustering score for a specific activity type.
        """
        type_names = self._get_activity_names_for_type(activity_type)
        type_entries = [e for e in self.schedule.entries if e.activity.name in type_names]
        
        if len(type_entries) < 2:
            return 1.0
        
        # Calculate day distribution
        day_distribution = defaultdict(int)
        for entry in type_entries:
            day_distribution[entry.time_slot.day] += 1
        
        # Calculate entropy
        total_activities = len(type_entries)
        entropy = 0.0
        for count in day_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        max_entropy = math.log2(len(day_distribution))
        if max_entropy > 0:
            normalized_entropy = entropy / max_entropy
            return 1.0 - normalized_entropy
        
        return 1.0
    
    def _simulate_activity_type_clustering_score_after_swap(self, entry1: ScheduleEntry, entry2: ScheduleEntry,
                                                            activity_type: str) -> float:
        """
        Simulate activity type clustering score after swap.
        """
        type_names = self._get_activity_names_for_type(activity_type)
        type_entries = [e for e in self.schedule.entries 
                       if e.activity.name in type_names and e != entry1 and e != entry2]
        
        # Add entries that would be of this type after swap
        if entry1.activity.name in type_names:
            type_entries.append(entry2)
        elif entry2.activity.name in type_names:
            type_entries.append(entry1)
        
        if len(type_entries) < 2:
            return 1.0
        
        day_distribution = defaultdict(int)
        for entry in type_entries:
            day_distribution[entry.time_slot.day] += 1
        
        total_activities = len(type_entries)
        entropy = 0.0
        for count in day_distribution.values():
            if count > 0:
                probability = count / total_activities
                entropy -= probability * math.log2(probability)
        
        max_entropy = math.log2(len(day_distribution))
        if max_entropy > 0:
            normalized_entropy = entropy / max_entropy
            return 1.0 - normalized_entropy
        
        return 1.0
    
    def _get_activity_names_for_type(self, activity_type: str) -> List[str]:
        """
        Get activity names for a specific type.
        """
        activity_types = {
            'water': ['Aqua Trampoline', 'Water Polo', 'Greased Watermelon', 'Troop Swim', 
                     'Underwater Obstacle Course', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                     'Nature Canoe', 'Float for Floats', 'Sailing'],
            'tower': ['Climbing Tower', 'Knots and Lashings'],
            'shooting': ['Troop Rifle', 'Troop Shotgun'],
            'archery': ['Archery'],
            'crafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
            'nature': ['Dr. DNA', 'Fishing'],
            'outdoor': ['Orienteering', 'GPS & Geocaching', 'Ultimate Survivor'],
            'cooking': ["What's Cooking", 'Chopped!']
        }
        
        return activity_types.get(activity_type, [])
    
    def _is_exclusive_activity(self, activity_name: str) -> bool:
        """
        Check if activity is exclusive.
        """
        exclusive_activities = {
            "Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery",
            "Aqua Trampoline", "Sailing"
        }
        return activity_name in exclusive_activities
    
    def _get_troop_commissioner(self, troop: Troop) -> str:
        """
        Get commissioner for a troop.
        """
        return getattr(troop, 'commissioner', 'Unknown')


def enhance_clustering(schedule, troops, activities, max_iterations: int = 100) -> Dict[str, float]:
    """
    Enhance activity zone clustering.
    """
    optimizer = EnhancedClusteringOptimizer(schedule, troops, activities)
    return optimizer.optimize_clustering(max_iterations)
