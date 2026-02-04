"""
Enhanced Top 5 Strategy - Aggressive Priority Placement
Strategy 1: Enhanced top 5 priority placement with aggressive swaps
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, Counter
import random
from typing import List, Dict, Tuple, Optional, Set
import math


class EnhancedTop5Strategy:
    """
    Enhanced Top 5 Strategy with aggressive placement and intelligent swaps.
    Focuses on maximizing top 5 satisfaction while maintaining schedule quality.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Enhanced constraint definitions with more flexibility for top 5
        self.BEACH_SLOT_ACTIVITIES = {
            "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats"
        }
        
        self.EXCLUSIVE_ACTIVITIES = {
            "Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery",
            "Aqua Trampoline", "Sailing"
        }
        
        # NEW: Enhanced priority scoring for top 5
        self.TOP5_PRIORITY_WEIGHTS = {
            1: 100,  # #1 preference gets highest weight
            2: 80,   # #2 preference
            3: 60,   # #3 preference
            4: 40,   # #4 preference
            5: 20    # #5 preference
        }
        
        # NEW: Aggressive swap thresholds
        self.AGGRESSIVE_SWAP_THRESHOLD = 15  # Minimum improvement to justify swap
        self.FORCE_PLACEMENT_THRESHOLD = 50  # Minimum priority score for force placement
        
        print(f"  [Enhanced Top5] Initialized with aggressive placement strategy")
    
    def enhance_top5_placement(self, max_iterations: int = 300) -> Dict[str, any]:
        """
        Enhanced top 5 placement with aggressive strategies.
        """
        print(f"  [Enhanced Top5] Starting enhanced placement with {max_iterations} iterations...")
        
        results = {
            'initial_satisfied': 0,
            'final_satisfied': 0,
            'improvement': 0,
            'aggressive_swaps': 0,
            'force_placements': 0,
            'constraint_violations': 0,
            'top5_details': []
        }
        
        # Analyze initial status
        initial_status = self._analyze_top5_status()
        results['initial_satisfied'] = initial_status['satisfied']
        
        # Phase 1: Aggressive intelligent swaps
        print(f"  [Enhanced Top5] Phase 1: Aggressive intelligent swaps...")
        for iteration in range(max_iterations // 2):
            improvement = self._perform_aggressive_swap_iteration()
            
            if improvement > 0:
                results['aggressive_swaps'] += 1
                if iteration % 25 == 0:
                    current_status = self._analyze_top5_status()
                    print(f"    Swap iteration {iteration}: {current_status['satisfied']}/{len(self.troops)} satisfied")
        
        # Phase 2: Multi-target optimization
        print(f"  [Enhanced Top5] Phase 2: Multi-target optimization...")
        for iteration in range(max_iterations // 2):
            improvement = self._perform_multi_target_optimization()
            
            if improvement > 0:
                results['aggressive_swaps'] += 1
                if iteration % 25 == 0:
                    current_status = self._analyze_top5_status()
                    print(f"    Multi-target iteration {iteration}: {current_status['satisfied']}/{len(self.troops)} satisfied")
        
        # Phase 3: Strategic force placement for remaining gaps
        current_status = self._analyze_top5_status()
        if current_status['satisfied'] < len(self.troops):
            print(f"  [Enhanced Top5] Phase 3: Strategic force placement...")
            force_results = self._strategic_force_placement()
            results['force_placements'] = force_results['placements']
            results['constraint_violations'] = force_results['violations']
        
        # Final analysis
        final_status = self._analyze_top5_status()
        results['final_satisfied'] = final_status['satisfied']
        results['improvement'] = results['final_satisfied'] - results['initial_satisfied']
        
        # Collect detailed top 5 information
        results['top5_details'] = self._collect_top5_details(final_status)
        
        print(f"  [Enhanced Top5] Results:")
        print(f"    Initial: {results['initial_satisfied']}/{len(self.troops)} satisfied")
        print(f"    Final: {results['final_satisfied']}/{len(self.troops)} satisfied")
        print(f"    Improvement: +{results['improvement']}")
        print(f"    Aggressive swaps: {results['aggressive_swaps']}")
        print(f"    Force placements: {results['force_placements']}")
        print(f"    Constraint violations: {results['constraint_violations']}")
        
        return results
    
    def _analyze_top5_status(self) -> Dict[str, any]:
        """Analyze current top 5 satisfaction status."""
        troop_activities = defaultdict(set)
        for entry in self.schedule.entries:
            if hasattr(entry, 'troop') and hasattr(entry.troop, 'name'):
                troop_activities[entry.troop.name].add(entry.activity.name)
        
        satisfied_troops = []
        unsatisfied_troops = []
        missing_preferences = defaultdict(list)
        
        available_activities = set(self.activities.keys())
        
        for troop in self.troops:
            scheduled_activities = troop_activities[troop.name]
            top5_satisfied = 0
            missing_top5 = []
            total_available_top5 = 0
            
            for i, activity_name in enumerate(troop.preferences[:5]):
                if activity_name not in available_activities:
                    continue
                
                total_available_top5 += 1
                if activity_name in scheduled_activities:
                    top5_satisfied += 1
                else:
                    missing_top5.append(activity_name)
            
            if total_available_top5 == 0 or top5_satisfied == total_available_top5:
                satisfied_troops.append(troop.name)
            else:
                unsatisfied_troops.append(troop.name)
                missing_preferences[troop.name] = missing_top5
        
        return {
            'satisfied': len(satisfied_troops),
            'total': len(self.troops),
            'satisfied_troops': satisfied_troops,
            'unsatisfied_troops': unsatisfied_troops,
            'missing_preferences': dict(missing_preferences)
        }
    
    def _perform_aggressive_swap_iteration(self) -> int:
        """Perform one iteration of aggressive swap optimization."""
        best_improvement = 0
        best_swap = None
        
        current_status = self._analyze_top5_status()
        
        # Focus on unsatisfied troops
        for troop_name in current_status['unsatisfied_troops']:
            troop = next((t for t in self.troops if t.name == troop_name), None)
            if not troop:
                continue
            
            missing_preferences = current_status['missing_preferences'][troop_name]
            
            # Try to satisfy each missing preference with aggressive strategies
            for missing_activity in missing_preferences:
                improvement = self._try_aggressive_satisfaction(troop, missing_activity)
                
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_swap = (troop, missing_activity)
        
        # Execute best improvement if it meets threshold
        if best_improvement >= self.AGGRESSIVE_SWAP_THRESHOLD and best_swap:
            troop, activity = best_swap
            success = self._execute_aggressive_placement(troop, activity)
            if success:
                return best_improvement
        
        return 0
    
    def _perform_multi_target_optimization(self) -> int:
        """Optimize for multiple troops simultaneously."""
        total_improvement = 0
        
        # Find swap opportunities that benefit multiple troops
        swap_opportunities = self._find_multi_troop_swaps()
        
        for opportunity in swap_opportunities:
            improvement = opportunity['improvement']
            if improvement >= self.AGGRESSIVE_SWAP_THRESHOLD:
                success = self._execute_multi_troop_swap(opportunity)
                if success:
                    total_improvement += improvement
                    break  # Only execute one swap per iteration
        
        return total_improvement
    
    def _try_aggressive_satisfaction(self, troop: Troop, activity_name: str) -> int:
        """Try to satisfy a preference with aggressive strategies."""
        activity = self.activities.get(activity_name)
        if not activity:
            return 0
        
        # Calculate priority score
        if activity_name not in troop.preferences[:5]:
            return 0
        
        rank = troop.preferences.index(activity_name) + 1
        base_improvement = self.TOP5_PRIORITY_WEIGHTS.get(rank, 0)
        
        # Find all possible slots with relaxed constraints for top 5
        possible_slots = self._find_aggressive_slots(activity, troop)
        
        if not possible_slots:
            return 0
        
        # Calculate improvement with bonus for difficult placements
        difficulty_bonus = len(possible_slots) * 5  # Fewer slots = higher bonus
        total_improvement = base_improvement + difficulty_bonus
        
        return total_improvement
    
    def _find_aggressive_slots(self, activity: Activity, troop: Troop) -> List[TimeSlot]:
        """Find possible slots with relaxed constraints for top 5 preferences."""
        possible_slots = []
        
        from models import generate_time_slots
        all_slots = generate_time_slots()
        
        for slot in all_slots:
            if self._can_place_aggressively(activity, troop, slot):
                possible_slots.append(slot)
        
        return possible_slots
    
    def _can_place_aggressively(self, activity: Activity, troop: Troop, slot: TimeSlot) -> bool:
        """Check if activity can be placed with relaxed constraints for top 5."""
        # Basic troop availability check
        if not self.schedule.is_troop_free(slot, troop):
            return False
        
        # Relaxed beach slot constraint for top 5
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot.slot_number == 2 and slot.day != Day.THURSDAY):
            # Allow beach activities in slot 2 if it's a top 5 preference
            if activity.name in troop.preferences[:5]:
                return True  # Relaxed constraint for top 5
            return False
        
        # Relaxed exclusive activity constraint for top 5
        if activity.name in self.EXCLUSIVE_ACTIVITIES:
            if activity.name in troop.preferences[:5]:
                # Allow concurrent exclusive activities for top 5 (rare)
                concurrent_count = len([e for e in self.schedule.entries 
                                     if e.time_slot == slot and e.activity.name == activity.name])
                return concurrent_count < 2  # Allow 2 instead of 1
            else:
                # Normal constraint for non-top-5
                for entry in self.schedule.entries:
                    if (entry.activity.name == activity.name and 
                        entry.time_slot.day == slot.day and 
                        entry.time_slot.slot_number == slot.slot_number):
                        return False
        
        return True
    
    def _execute_aggressive_placement(self, troop: Troop, activity_name: str) -> bool:
        """Execute aggressive placement for top 5 preference."""
        activity = self.activities.get(activity_name)
        if not activity:
            return False
        
        possible_slots = self._find_aggressive_slots(activity, troop)
        if not possible_slots:
            return False
        
        # Try swaps first, then direct placement
        for slot in possible_slots:
            if self._try_aggressive_swap(troop, activity, slot):
                return True
        
        for slot in possible_slots:
            if self._try_aggressive_direct_placement(troop, activity, slot):
                return True
        
        return False
    
    def _try_aggressive_swap(self, troop: Troop, activity: Activity, target_slot: TimeSlot) -> bool:
        """Try aggressive swap with lower priority activities."""
        target_entries = [e for e in self.schedule.entries if e.time_slot == target_slot]
        
        if not target_entries:
            return False
        
        for target_entry in target_entries:
            if target_entry.troop == troop:
                continue
            
            # Calculate swap value
            swap_value = self._calculate_aggressive_swap_value(troop, activity, target_entry, target_slot)
            
            if swap_value > 0:
                # Find a slot for the target activity
                target_activity = target_entry.activity
                swap_slots = self._find_aggressive_slots(target_activity, target_entry.troop)
                
                for swap_slot in swap_slots:
                    if swap_slot == target_slot:
                        continue
                    
                    # Perform the swap
                    if self._can_place_aggressively(target_activity, target_entry.troop, swap_slot):
                        self._swap_activities(target_entry, swap_slot)
                        self._place_activity_at_slot(troop, activity, target_slot)
                        return True
        
        return False
    
    def _calculate_aggressive_swap_value(self, troop: Troop, activity: Activity, 
                                        target_entry: ScheduleEntry, target_slot: TimeSlot) -> int:
        """Calculate the value of an aggressive swap."""
        # Value for placing top 5 activity
        if activity.name not in troop.preferences[:5]:
            return 0
        
        rank = troop.preferences.index(activity.name) + 1
        placement_value = self.TOP5_PRIORITY_WEIGHTS.get(rank, 0)
        
        # Cost of displacing existing activity
        target_troop = target_entry.troop
        target_activity = target_entry.activity.name
        
        displacement_cost = 0
        if target_activity in target_troop.preferences[:5]:
            target_rank = target_troop.preferences.index(target_activity) + 1
            displacement_cost = self.TOP5_PRIORITY_WEIGHTS.get(target_rank, 0) // 2  # Half cost for displacement
        
        return placement_value - displacement_cost
    
    def _try_aggressive_direct_placement(self, troop: Troop, activity: Activity, slot: TimeSlot) -> bool:
        """Try direct placement with aggressive removal."""
        existing_entries = [e for e in self.schedule.entries if e.time_slot == slot]
        
        if not existing_entries:
            # Empty slot
            self._place_activity_at_slot(troop, activity, slot)
            return True
        
        # Find lowest priority entry to remove
        best_entry_to_remove = None
        best_removal_score = float('inf')
        
        for entry in existing_entries:
            removal_score = self._calculate_aggressive_removal_score(entry)
            if removal_score < best_removal_score:
                best_removal_score = removal_score
                best_entry_to_remove = entry
        
        # Remove if score is below threshold
        if best_entry_to_remove and best_removal_score < self.FORCE_PLACEMENT_THRESHOLD:
            self.schedule.entries.remove(best_entry_to_remove)
            self._place_activity_at_slot(troop, activity, slot)
            return True
        
        return False
    
    def _calculate_aggressive_removal_score(self, entry: ScheduleEntry) -> float:
        """Calculate removal score with aggressive thresholds for top 5."""
        troop = entry.troop
        activity_name = entry.activity.name
        
        score = 100.0  # Base score
        
        # Heavy penalty for removing top 5 activities
        if activity_name in troop.preferences[:5]:
            rank = troop.preferences.index(activity_name) + 1
            score -= self.TOP5_PRIORITY_WEIGHTS.get(rank, 0) * 2  # Double penalty
        
        # Penalty for mandatory activities
        if activity_name in ["Reflection", "Super Troop"]:
            score -= 200  # Very high penalty
        
        # Penalty for exclusive activities
        if activity_name in self.EXCLUSIVE_ACTIVITIES:
            score -= 60
        
        # Penalty for 3-hour activities
        if activity_name in ["Rocks", "Delta"]:
            score -= 80
        
        return score
    
    def _find_multi_troop_swaps(self) -> List[Dict]:
        """Find swap opportunities that benefit multiple troops."""
        opportunities = []
        
        current_status = self._analyze_top5_status()
        
        # Look for 3-way swaps that benefit 2+ troops
        for troop1_name in current_status['unsatisfied_troops']:
            troop1 = next((t for t in self.troops if t.name == troop1_name), None)
            if not troop1:
                continue
            
            missing1 = current_status['missing_preferences'][troop1_name]
            
            for missing_activity in missing1[:2]:  # Check top 2 missing
                activity = self.activities.get(missing_activity)
                if not activity:
                    continue
                
                # Find troops that have this activity but want other activities
                for entry in self.schedule.entries:
                    if entry.activity.name == missing_activity and entry.troop != troop1:
                        troop2 = entry.troop
                        
                        # Check if troop2 has missing preferences that troop1 has
                        if troop2.name in current_status['unsatisfied_troops']:
                            missing2 = current_status['missing_preferences'][troop2.name]
                            
                            # Find mutual benefit
                            troop1_activities = set(e.activity.name for e in self.schedule.entries if e.troop == troop1)
                            mutual_benefits = [a for a in missing2 if a in troop1_activities]
                            
                            if mutual_benefits:
                                improvement = self._calculate_multi_swap_improvement(
                                    troop1, troop2, missing_activity, mutual_benefits[0]
                                )
                                
                                if improvement >= self.AGGRESSIVE_SWAP_THRESHOLD:
                                    opportunities.append({
                                        'type': 'multi_troop',
                                        'troop1': troop1,
                                        'troop2': troop2,
                                        'activity1': missing_activity,
                                        'activity2': mutual_benefits[0],
                                        'improvement': improvement,
                                        'entry': entry
                                    })
        
        # Sort by improvement
        opportunities.sort(key=lambda x: x['improvement'], reverse=True)
        return opportunities[:5]  # Top 5 opportunities
    
    def _calculate_multi_swap_improvement(self, troop1: Troop, troop2: Troop, 
                                       activity1: str, activity2: str) -> int:
        """Calculate improvement for multi-troop swap."""
        improvement = 0
        
        # Value for troop1 getting activity1
        if activity1 in troop1.preferences[:5]:
            rank1 = troop1.preferences.index(activity1) + 1
            improvement += self.TOP5_PRIORITY_WEIGHTS.get(rank1, 0)
        
        # Value for troop2 getting activity2
        if activity2 in troop2.preferences[:5]:
            rank2 = troop2.preferences.index(activity2) + 1
            improvement += self.TOP5_PRIORITY_WEIGHTS.get(rank2, 0)
        
        # Cost of displacing current activities
        cost = 0
        if activity1 in troop2.preferences[:5]:
            rank1_displace = troop2.preferences.index(activity1) + 1
            cost += self.TOP5_PRIORITY_WEIGHTS.get(rank1_displace, 0) // 3
        
        if activity2 in troop1.preferences[:5]:
            rank2_displace = troop1.preferences.index(activity2) + 1
            cost += self.TOP5_PRIORITY_WEIGHTS.get(rank2_displace, 0) // 3
        
        return improvement - cost
    
    def _execute_multi_troop_swap(self, opportunity: Dict) -> bool:
        """Execute multi-troop swap."""
        troop1 = opportunity['troop1']
        troop2 = opportunity['troop2']
        activity1_name = opportunity['activity1']
        activity2_name = opportunity['activity2']
        entry = opportunity['entry']
        
        activity1 = self.activities.get(activity1_name)
        activity2 = self.activities.get(activity2_name)
        
        if not activity1 or not activity2:
            return False
        
        # Find entry for activity2 in troop1's schedule
        troop1_activity2_entry = None
        for e in self.schedule.entries:
            if e.troop == troop1 and e.activity.name == activity2_name:
                troop1_activity2_entry = e
                break
        
        if not troop1_activity2_entry:
            return False
        
        # Perform the swap
        slot1 = entry.time_slot
        slot2 = troop1_activity2_entry.time_slot
        
        # Remove old entries
        self.schedule.entries.remove(entry)
        self.schedule.entries.remove(troop1_activity2_entry)
        
        # Add new entries
        self.schedule.entries.append(ScheduleEntry(slot1, activity2, troop1))
        self.schedule.entries.append(ScheduleEntry(slot2, activity1, troop2))
        
        return True
    
    def _strategic_force_placement(self) -> Dict[str, int]:
        """Strategic force placement for remaining unsatisfied top 5."""
        results = {'placements': 0, 'violations': 0}
        
        current_status = self._analyze_top5_status()
        
        for troop_name in current_status['unsatisfied_troops']:
            troop = next((t for t in self.troops if t.name == troop_name), None)
            if not troop:
                continue
            
            missing_preferences = current_status['missing_preferences'][troop_name]
            
            # Prioritize by preference rank
            for activity_name in missing_preferences:
                activity = self.activities.get(activity_name)
                if not activity:
                    continue
                
                # Calculate priority score
                if activity_name in troop.preferences[:5]:
                    rank = troop.preferences.index(activity_name) + 1
                    priority_score = self.TOP5_PRIORITY_WEIGHTS.get(rank, 0)
                    
                    if priority_score >= self.FORCE_PLACEMENT_THRESHOLD:
                        placed = self._strategic_place_activity(troop, activity)
                        if placed:
                            results['placements'] += 1
                            results['violations'] += 1  # Likely violates constraints
                            print(f"    [Strategic] Placed {activity_name} for {troop.name} (priority: {priority_score})")
                            break
        
        return results
    
    def _strategic_place_activity(self, troop: Troop, activity: Activity) -> bool:
        """Strategically place an activity with minimal violations."""
        from models import generate_time_slots
        all_slots = generate_time_slots()
        
        # Find best slot with minimum violations
        best_slot = None
        min_violations = float('inf')
        
        for slot in all_slots:
            violations = self._count_slot_violations(troop, activity, slot)
            if violations < min_violations:
                min_violations = violations
                best_slot = slot
        
        if best_slot and min_violations <= 2:  # Allow up to 2 violations
            self._force_place_activity(troop, activity, best_slot)
            return True
        
        return False
    
    def _count_slot_violations(self, troop: Troop, activity: Activity, slot: TimeSlot) -> int:
        """Count constraint violations for a potential placement."""
        violations = 0
        
        # Troop availability
        if not self.schedule.is_troop_free(slot, troop):
            violations += 1
        
        # Beach slot constraint
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot.slot_number == 2 and slot.day != Day.THURSDAY):
            violations += 1
        
        # Exclusive activity constraint
        if activity.name in self.EXCLUSIVE_ACTIVITIES:
            for entry in self.schedule.entries:
                if (entry.activity.name == activity.name and 
                    entry.time_slot.day == slot.day and 
                    entry.time_slot.slot_number == slot.slot_number):
                    violations += 1
                    break
        
        return violations
    
    def _swap_activities(self, entry: ScheduleEntry, new_slot: TimeSlot):
        """Move an activity to a new slot."""
        entry.time_slot = new_slot
    
    def _place_activity_at_slot(self, troop: Troop, activity: Activity, slot: TimeSlot):
        """Place an activity at a specific slot."""
        new_entry = ScheduleEntry(slot, activity, troop)
        self.schedule.entries.append(new_entry)
    
    def _force_place_activity(self, troop: Troop, activity: Activity, slot: TimeSlot):
        """Force place an activity, removing conflicts."""
        # Remove existing activity at this slot for this troop
        existing_entries = [e for e in self.schedule.entries 
                           if e.troop == troop and e.time_slot == slot]
        
        for entry in existing_entries:
            self.schedule.entries.remove(entry)
        
        # Place the new activity
        new_entry = ScheduleEntry(slot, activity, troop)
        self.schedule.entries.append(new_entry)
    
    def _collect_top5_details(self, status: Dict) -> List[Dict]:
        """Collect detailed top 5 information."""
        details = []
        
        for troop_name in status['unsatisfied_troops']:
            troop = next((t for t in self.troops if t.name == troop_name), None)
            if not troop:
                continue
            
            missing = status['missing_preferences'].get(troop_name, [])
            scheduled = set()
            for entry in self.schedule.entries:
                if entry.troop == troop:
                    scheduled.add(entry.activity.name)
            
            satisfied_top5 = [p for p in troop.preferences[:5] if p in scheduled]
            
            details.append({
                'troop': troop_name,
                'missing_preferences': missing,
                'satisfied_top5': satisfied_top5,
                'total_top5': len([p for p in troop.preferences[:5] if p in self.activities])
            })
        
        return details


def enhance_top5_placement(schedule, troops, activities, max_iterations: int = 300) -> Dict[str, any]:
    """
    Enhanced top 5 placement with aggressive strategies.
    """
    enhancer = EnhancedTop5Strategy(schedule, troops, activities)
    return enhancer.enhance_top5_placement(max_iterations)
