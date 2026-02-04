"""
Advanced Preference Optimization System
Implements sophisticated algorithms for maximizing troop preference satisfaction
while maintaining constraint compliance and schedule quality.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, Counter
import math
import random
from typing import List, Tuple, Dict, Set


class AdvancedPreferenceOptimizer:
    """
    Advanced preference optimization using multi-objective optimization
    and intelligent activity swapping to maximize troop satisfaction.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        self.time_slots = self._generate_time_slots()
        
        # Preference weights for different optimization goals
        self.PREFERENCE_WEIGHTS = {
            'top5': 10.0,      # Highest priority
            'top6_10': 5.0,    # High priority
            'top11_15': 2.0,   # Medium priority
            'top16_20': 1.0,   # Low priority
            'constraint_penalty': -50.0,  # Heavy penalty for violations
            'staff_balance': 2.0,  # Staff workload balance
            'clustering': 1.5   # Activity clustering efficiency
        }
        
        # Activity categories for optimization
        self.SAFE_SWAP_ACTIVITIES = {
            'Gaga Ball', '9 Square', 'Fishing', 'Trading Post', 
            'Campsite Free Time', 'Dr. DNA', 'Loon Lore'
        }
        
        self.HIGH_VALUE_ACTIVITIES = {
            'Climbing Tower', 'Sailing', 'Aqua Trampoline', 'Troop Canoe',
            'Troop Kayak', 'Canoe Snorkel', 'Archery', 'Troop Rifle'
        }
        
        # Constraint definitions
        self.BEACH_SLOT_ACTIVITIES = {
            "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats"
        }
        
        self.WET_ACTIVITIES = {
            "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", 
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats", "Sailing", "Sauna"
        }
        
        self.TOWER_ODS_ACTIVITIES = {
            "Climbing Tower", "Knots and Lashings", "Orienteering", "GPS & Geocaching",
            "Ultimate Survivor", "What's Cooking", "Chopped!"
        }
    
    def _generate_time_slots(self):
        """Generate all time slots for the week."""
        slots = []
        for day in Day:
            max_slot = 2 if day == Day.THURSDAY else 3
            for slot_num in range(1, max_slot + 1):
                slots.append(TimeSlot(day, slot_num))
        return slots
    
    def optimize_preferences(self, max_iterations=100):
        """
        Advanced preference optimization using simulated annealing
        and intelligent activity swapping.
        """
        print("=== ADVANCED PREFERENCE OPTIMIZER ===")
        
        # Calculate initial score
        initial_score = self._calculate_schedule_score()
        print(f"Initial schedule score: {initial_score:.2f}")
        
        best_score = initial_score
        best_schedule_state = self._capture_schedule_state()
        
        # Optimization iterations
        for iteration in range(max_iterations):
            if iteration % 20 == 0:
                print(f"  Iteration {iteration}/{max_iterations} (best: {best_score:.2f})")
            
            # Generate candidate moves
            candidate_moves = self._generate_candidate_moves()
            
            if not candidate_moves:
                continue
            
            # Evaluate and apply best move
            best_move = None
            best_move_score = float('-inf')
            
            for move in candidate_moves:
                # Apply move temporarily
                self._apply_move(move)
                
                # Calculate new score
                new_score = self._calculate_schedule_score()
                
                # Calculate improvement
                improvement = new_score - best_score
                
                # Accept if improvement or probabilistic acceptance (simulated annealing)
                temperature = max(0.1, 1.0 - (iteration / max_iterations))
                acceptance_prob = math.exp(improvement / temperature) if improvement < 0 else 1.0
                
                if improvement > 0 or random.random() < acceptance_prob:
                    if new_score > best_move_score:
                        best_move = move
                        best_move_score = new_score
                
                # Revert move
                self._revert_move(move)
            
            # Apply best move found
            if best_move and best_move_score > best_score * 0.99:  # Small tolerance for noise
                self._apply_move(best_move)
                best_score = best_move_score
                best_schedule_state = self._capture_schedule_state()
                
                if iteration % 20 == 0:
                    print(f"    Applied move: {best_move['type']} -> {best_move_score:.2f}")
        
        # Restore best schedule
        self._restore_schedule_state(best_schedule_state)
        
        final_score = self._calculate_schedule_score()
        improvement = final_score - initial_score
        
        print(f"\n=== OPTIMIZATION COMPLETE ===")
        print(f"Initial score: {initial_score:.2f}")
        print(f"Final score: {final_score:.2f}")
        print(f"Improvement: {improvement:.2f} ({improvement/initial_score*100:.1f}%)")
        
        return improvement
    
    def _calculate_schedule_score(self):
        """Calculate comprehensive schedule quality score."""
        score = 0.0
        
        # Preference satisfaction scores
        preference_stats = self._calculate_preference_stats()
        
        # Top 5 preferences (highest weight)
        score += preference_stats['top5_satisfaction'] * self.PREFERENCE_WEIGHTS['top5']
        
        # Top 6-10 preferences
        score += preference_stats['top6_10_satisfaction'] * self.PREFERENCE_WEIGHTS['top6_10']
        
        # Top 11-15 preferences
        score += preference_stats['top11_15_satisfaction'] * self.PREFERENCE_WEIGHTS['top11_15']
        
        # Top 16-20 preferences
        score += preference_stats['top16_20_satisfaction'] * self.PREFERENCE_WEIGHTS['top16_20']
        
        # Constraint penalties
        constraint_violations = self._count_constraint_violations()
        score += constraint_violations * self.PREFERENCE_WEIGHTS['constraint_penalty']
        
        # Staff balance bonus
        staff_variance = self._calculate_staff_variance()
        staff_balance_score = max(0, 2.0 - staff_variance)  # Lower variance = higher score
        score += staff_balance_score * self.PREFERENCE_WEIGHTS['staff_balance']
        
        # Clustering efficiency bonus
        clustering_score = self._calculate_clustering_efficiency()
        score += clustering_score * self.PREFERENCE_WEIGHTS['clustering']
        
        return score
    
    def _calculate_preference_stats(self):
        """Calculate preference satisfaction statistics."""
        stats = {
            'top5_satisfaction': 0.0,
            'top6_10_satisfaction': 0.0,
            'top11_15_satisfaction': 0.0,
            'top16_20_satisfaction': 0.0
        }
        
        total_troops = len(self.troops)
        if total_troops == 0:
            return stats
        
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled_activities = {e.activity.name for e in troop_entries}
            
            # Calculate satisfaction for each preference tier
            for i, activity_name in enumerate(troop.preferences):
                if activity_name in scheduled_activities:
                    if i < 5:
                        stats['top5_satisfaction'] += 1
                    elif i < 10:
                        stats['top6_10_satisfaction'] += 1
                    elif i < 15:
                        stats['top11_15_satisfaction'] += 1
                    elif i < 20:
                        stats['top16_20_satisfaction'] += 1
        
        # Normalize by total possible
        stats['top5_satisfaction'] /= (total_troops * 5)
        stats['top6_10_satisfaction'] /= (total_troops * 5)
        stats['top11_15_satisfaction'] /= (total_troops * 5)
        stats['top16_20_satisfaction'] /= (total_troops * 5)
        
        return stats
    
    def _count_constraint_violations(self):
        """Count total constraint violations."""
        violations = 0
        
        # Beach slot violations
        for entry in self.schedule.entries:
            if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.slot_number == 2 and 
                entry.time_slot.day != Day.THURSDAY):
                violations += 1
        
        # Wet/Dry violations
        violations += self._count_wet_dry_violations()
        
        # Friday Reflection violations
        violations += self._count_friday_reflection_violations()
        
        return violations
    
    def _count_wet_dry_violations(self):
        """Count wet/dry pattern violations."""
        violations = 0
        
        for troop in self.troops:
            troop_entries = sorted(
                [e for e in self.schedule.entries if e.troop == troop],
                key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
            )
            
            # Group by day
            by_day = defaultdict(list)
            for entry in troop_entries:
                by_day[entry.time_slot.day].append(entry)
            
            for day, day_entries in by_day.items():
                day_entries.sort(key=lambda e: e.time_slot.slot_number)
                
                # Check wet->tower/ods violations
                for i in range(len(day_entries) - 1):
                    curr = day_entries[i]
                    next_e = day_entries[i + 1]
                    
                    if (curr.activity.name in self.WET_ACTIVITIES and 
                        next_e.activity.name in self.TOWER_ODS_ACTIVITIES):
                        violations += 1
                
                # Check wet-dry-wet pattern
                if len(day_entries) >= 3:
                    slot_map = {e.time_slot.slot_number: e for e in day_entries}
                    if (1 in slot_map and 2 in slot_map and 3 in slot_map):
                        s1_wet = slot_map[1].activity.name in self.WET_ACTIVITIES
                        s2_wet = slot_map[2].activity.name in self.WET_ACTIVITIES
                        s3_wet = slot_map[3].activity.name in self.WET_ACTIVITIES
                        
                        if s1_wet and not s2_wet and s3_wet:
                            violations += 1
        
        return violations
    
    def _count_friday_reflection_violations(self):
        """Count Friday Reflection violations."""
        violations = 0
        
        for troop in self.troops:
            has_reflection = any(
                e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                for e in self.schedule.entries if e.troop == troop
            )
            if not has_reflection:
                violations += 1
        
        return violations
    
    def _calculate_staff_variance(self):
        """Calculate staff workload variance."""
        staff_loads = defaultdict(int)
        
        for entry in self.schedule.entries:
            activity_name = entry.activity.name
            if activity_name in self._get_staff_zone_map():
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                staff_loads[slot_key] += 1
        
        if not staff_loads:
            return 0.0
        
        loads = list(staff_loads.values())
        avg_load = sum(loads) / len(loads)
        variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)
        
        return variance
    
    def _get_staff_zone_map(self):
        """Get staff zone mapping for activities."""
        return {
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
        }
    
    def _calculate_clustering_efficiency(self):
        """Calculate activity clustering efficiency score."""
        clustering_score = 0.0
        
        # Group activities by zone and check clustering
        zone_activities = defaultdict(list)
        for entry in self.schedule.entries:
            zone = entry.activity.zone
            zone_activities[zone].append(entry)
        
        for zone, entries in zone_activities.items():
            if len(entries) < 2:
                continue
            
            # Calculate clustering efficiency
            days_used = set(e.time_slot.day for e in entries)
            max_possible_days = len(Day)
            
            # Higher score for fewer days used (better clustering)
            efficiency = 1.0 - (len(days_used) - 1) / max_possible_days
            clustering_score += efficiency
        
        return clustering_score / len(zone_activities) if zone_activities else 0.0
    
    def _generate_candidate_moves(self):
        """Generate intelligent candidate moves for optimization."""
        moves = []
        
        # 1. Preference improvement moves
        moves.extend(self._generate_preference_improvement_moves())
        
        # 2. Constraint violation fixes
        moves.extend(self._generate_constraint_fix_moves())
        
        # 3. Staff balance improvements
        moves.extend(self._generate_staff_balance_moves())
        
        # 4. Clustering improvements
        moves.extend(self._generate_clustering_moves())
        
        return moves
    
    def _generate_preference_improvement_moves(self):
        """Generate moves to improve preference satisfaction."""
        moves = []
        
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            scheduled_activities = {e.activity.name for e in troop_entries}
            
            # Find unscheduled high-priority preferences
            for rank, activity_name in enumerate(troop.preferences[:10]):  # Focus on top 10
                if activity_name not in scheduled_activities:
                    activity = self.activities.get(activity_name)
                    if not activity:
                        continue
                    
                    # Find potential slots for this activity
                    for slot in self.time_slots:
                        if (self.schedule.is_troop_free(slot, troop) and
                            self.schedule.is_activity_available(slot, activity, troop)):
                            
                            # Find low-value activity to swap
                            swap_candidate = self._find_swap_candidate(troop, slot, rank)
                            if swap_candidate:
                                moves.append({
                                    'type': 'preference_improvement',
                                    'troop': troop,
                                    'activity': activity,
                                    'slot': slot,
                                    'swap_out': swap_candidate['activity'],
                                    'swap_out_slot': swap_candidate['slot'],
                                    'priority_rank': rank
                                })
                                break
        
        return moves
    
    def _find_swap_candidate(self, troop, target_slot, priority_rank):
        """Find low-value activity to swap for preference improvement."""
        # Look for safe swap activities in the same day
        target_day = target_slot.day
        
        for entry in self.schedule.entries:
            if (entry.troop == troop and 
                entry.time_slot.day == target_day and
                entry.activity.name in self.SAFE_SWAP_ACTIVITIES):
                
                # Check if we can move this to the target slot
                if self.schedule.is_activity_available(target_slot, entry.activity, troop):
                    return {
                        'activity': entry.activity,
                        'slot': entry.time_slot
                    }
        
        return None
    
    def _generate_constraint_fix_moves(self):
        """Generate moves to fix constraint violations."""
        moves = []
        
        # Beach slot violation fixes
        for entry in self.schedule.entries:
            if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.slot_number == 2 and 
                entry.time_slot.day != Day.THURSDAY):
                
                # Try to move to slot 1 or 3
                for target_slot in [1, 3]:
                    new_time_slot = TimeSlot(entry.time_slot.day, target_slot)
                    
                    if (self.schedule.is_troop_free(new_time_slot, entry.troop) and
                        self.schedule.is_activity_available(new_time_slot, entry.activity, entry.troop)):
                        
                        moves.append({
                            'type': 'constraint_fix',
                            'sub_type': 'beach_slot',
                            'troop': entry.troop,
                            'activity': entry.activity,
                            'from_slot': entry.time_slot,
                            'to_slot': new_time_slot
                        })
                        break
        
        return moves
    
    def _generate_staff_balance_moves(self):
        """Generate moves to improve staff workload balance."""
        moves = []
        
        # Calculate current staff distribution
        staff_loads = defaultdict(int)
        slot_entries = defaultdict(list)
        
        for entry in self.schedule.entries:
            activity_name = entry.activity.name
            if activity_name in self._get_staff_zone_map():
                slot_key = (entry.time_slot.day, entry.time_slot.slot_number)
                staff_loads[slot_key] += 1
                slot_entries[slot_key].append(entry)
        
        if not staff_loads:
            return moves
        
        # Find overloaded and underloaded slots
        avg_load = sum(staff_loads.values()) / len(staff_loads)
        
        overloaded = [(slot, load) for slot, load in staff_loads.items() if load > avg_load * 1.2]
        underloaded = [(slot, load) for slot, load in staff_loads.items() if load < avg_load * 0.8]
        
        # Generate moves between overloaded and underloaded slots
        for (over_slot, over_load), (under_slot, under_load) in zip(overloaded, underloaded):
            for entry in slot_entries[over_slot]:
                if entry.activity.name in self.SAFE_SWAP_ACTIVITIES:
                    # Try to move to underloaded slot
                    new_time_slot = TimeSlot(under_slot[0], under_slot[1])
                    
                    if (self.schedule.is_troop_free(new_time_slot, entry.troop) and
                        self.schedule.is_activity_available(new_time_slot, entry.activity, entry.troop)):
                        
                        moves.append({
                            'type': 'staff_balance',
                            'troop': entry.troop,
                            'activity': entry.activity,
                            'from_slot': entry.time_slot,
                            'to_slot': new_time_slot
                        })
                        break
        
        return moves
    
    def _generate_clustering_moves(self):
        """Generate moves to improve activity clustering."""
        moves = []
        
        # Group activities by zone
        zone_entries = defaultdict(list)
        for entry in self.schedule.entries:
            zone = entry.activity.zone
            zone_entries[zone].append(entry)
        
        # Find clustering opportunities
        for zone, entries in zone_entries.items():
            if len(entries) < 2:
                continue
            
            # Calculate current clustering
            days_used = defaultdict(list)
            for entry in entries:
                days_used[entry.time_slot.day].append(entry)
            
            # Find days with single activities that could be clustered
            single_days = [(day, day_entries[0]) for day, day_entries in days_used.items() if len(day_entries) == 1]
            
            if len(single_days) < 2:
                continue
            
            # Try to cluster single activities
            for i, (day1, entry1) in enumerate(single_days):
                for day2, entry2 in single_days[i+1:]:
                    # Try to move entry2 to day1
                    for slot in self.time_slots:
                        if (slot.day == day1 and 
                            self.schedule.is_troop_free(slot, entry2.troop) and
                            self.schedule.is_activity_available(slot, entry2.activity, entry2.troop)):
                            
                            moves.append({
                                'type': 'clustering',
                                'troop': entry2.troop,
                                'activity': entry2.activity,
                                'from_slot': entry2.time_slot,
                                'to_slot': slot,
                                'zone': zone
                            })
                            break
        
        return moves
    
    def _apply_move(self, move):
        """Apply a move to the schedule."""
        if move['type'] == 'preference_improvement':
            # Remove swap_out activity and add new preference
            self.schedule.remove_entry_by_troop_activity(move['troop'], move['swap_out'], move['swap_out_slot'])
            self.schedule.add_entry(move['slot'], move['activity'], move['troop'])
            
        elif move['type'] in ['constraint_fix', 'staff_balance', 'clustering']:
            # Simple move
            self.schedule.remove_entry_by_troop_activity(move['troop'], move['activity'], move['from_slot'])
            self.schedule.add_entry(move['to_slot'], move['activity'], move['troop'])
    
    def _revert_move(self, move):
        """Revert a move from the schedule."""
        if move['type'] == 'preference_improvement':
            # Remove new preference and restore swap_out
            self.schedule.remove_entry_by_troop_activity(move['troop'], move['activity'], move['slot'])
            self.schedule.add_entry(move['swap_out_slot'], move['swap_out'], move['troop'])
            
        elif move['type'] in ['constraint_fix', 'staff_balance', 'clustering']:
            # Revert move
            self.schedule.remove_entry_by_troop_activity(move['troop'], move['activity'], move['to_slot'])
            self.schedule.add_entry(move['from_slot'], move['activity'], move['troop'])
    
    def _capture_schedule_state(self):
        """Capture current schedule state for restoration."""
        return [(e.troop.name, e.activity.name, e.time_slot.day, e.time_slot.slot_number) 
                for e in self.schedule.entries]
    
    def _restore_schedule_state(self, state):
        """Restore schedule from captured state."""
        # Clear current schedule
        self.schedule.entries.clear()
        
        # Restore entries
        for troop_name, activity_name, day, slot_num in state:
            troop = next((t for t in self.troops if t.name == troop_name), None)
            activity = self.activities.get(activity_name)
            time_slot = TimeSlot(day, slot_num)
            
            if troop and activity and time_slot:
                self.schedule.add_entry(time_slot, activity, troop)


def optimize_advanced_preferences(schedule, troops, activities, max_iterations=100):
    """
    Optimize schedule preferences using advanced algorithms.
    """
    optimizer = AdvancedPreferenceOptimizer(schedule, troops, activities)
    return optimizer.optimize_preferences(max_iterations)
