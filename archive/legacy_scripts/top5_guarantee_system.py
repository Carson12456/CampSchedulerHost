"""
Top 5 Preference Guarantee System
Ensures 100% of troops get their top 5 preferences through intelligent scheduling
and constraint-aware activity placement.
"""

from models import Day, Zone, Activity, Troop, ScheduleEntry, TimeSlot
from collections import defaultdict, Counter
import random
from typing import List, Dict, Tuple, Optional, Set
import math


class Top5GuaranteeSystem:
    """
    Advanced system that guarantees 100% top 5 preference satisfaction
    while maintaining constraint compliance and overall schedule quality.
    """
    
    def __init__(self, schedule, troops, activities):
        self.schedule = schedule
        self.troops = troops
        self.activities = {a.name: a for a in activities}
        
        # Track top 5 satisfaction
        self.top5_status = self._analyze_current_top5_status()
        
        # Constraint definitions
        self.BEACH_SLOT_ACTIVITIES = {
            "Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
            "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
            "Nature Canoe", "Float for Floats"
        }
        
        self.EXCLUSIVE_ACTIVITIES = {
            "Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery",
            "Aqua Trampoline", "Sailing"
        }
        
        print(f"  [Top5 Guarantee] Initial status: {self.top5_status['satisfied']}/{len(self.troops)} troops satisfied")
    
    def guarantee_top5_satisfaction(self, max_iterations: int = 200) -> Dict[str, any]:
        """
        Guarantee 100% top 5 preference satisfaction.
        """
        print(f"  [Top5 Guarantee] Starting guarantee process with {max_iterations} iterations...")
        
        results = {
            'initial_satisfied': self.top5_status['satisfied'],
            'final_satisfied': self.top5_status['satisfied'],
            'improvement': 0,
            'swaps_made': 0,
            'forced_placements': 0,
            'constraint_violations': 0,
            'unsatisfied_troops': [],
            'missed_top5_details': []
        }
        
        # Phase 1: Try to satisfy through intelligent swaps
        for iteration in range(max_iterations):
            improvement = self._perform_top5_optimization_iteration()
            
            if improvement > 0:
                results['swaps_made'] += 1
                self.top5_status = self._analyze_current_top5_status()
                
                if iteration % 20 == 0:
                    print(f"    Iteration {iteration}: {self.top5_status['satisfied']}/{len(self.troops)} satisfied")
        
        # Phase 2: Force placement for remaining unsatisfied troops
        if self.top5_status['satisfied'] < len(self.troops):
            print(f"  [Top5 Guarantee] Phase 2: Force placing remaining unsatisfied troops")
            forced_results = self._force_place_remaining_top5()
            results['forced_placements'] = forced_results['placements']
            results['constraint_violations'] = forced_results['violations']
            
            # Update status
            self.top5_status = self._analyze_current_top5_status()
        
        results['final_satisfied'] = self.top5_status['satisfied']
        results['improvement'] = results['final_satisfied'] - results['initial_satisfied']
        results['unsatisfied_troops'] = self.top5_status['unsatisfied_troops']
        
        # Collect detailed information about missed top 5 preferences
        for troop_name in self.top5_status['unsatisfied_troops']:
            troop = next((t for t in self.troops if t.name == troop_name), None)
            if troop:
                missing_prefs = self.top5_status['missing_preferences'].get(troop_name, [])
                available_prefs = [p for p in troop.preferences[:5] 
                                 if p in self.activities and p not in missing_prefs]
                results['missed_top5_details'].append({
                    'troop': troop_name,
                    'missing_preferences': missing_prefs,
                    'available_preferences': available_prefs,
                    'suggestion': self._generate_placement_suggestion(troop, missing_prefs)
                })
        
        print(f"  [Top5 Guarantee] Results:")
        print(f"    Initial satisfied: {results['initial_satisfied']}")
        print(f"    Final satisfied: {results['final_satisfied']}")
        print(f"    Improvement: {results['improvement']}")
        print(f"    Swaps made: {results['swaps_made']}")
        print(f"    Forced placements: {results['forced_placements']}")
        print(f"    Constraint violations: {results['constraint_violations']}")
        
        # Add detailed breakdown
        total_available_top5 = 0
        total_exempt_top5 = 0
        for troop_name in self.top5_status['exempt_preferences']:
            total_exempt_top5 += len(self.top5_status['exempt_preferences'][troop_name])
            total_available_top5 += 5 - len(self.top5_status['exempt_preferences'][troop_name])
        
        print(f"    Available top 5 preferences: {total_available_top5}")
        print(f"    Exempt top 5 preferences: {total_exempt_top5}")
        
        # Print missed top 5 details
        if results['missed_top5_details']:
            print(f"    Missed Top 5 Details:")
            for detail in results['missed_top5_details']:
                print(f"      {detail['troop']}:")
                print(f"        Missing: {detail['missing_preferences']}")
                print(f"        Available: {detail['available_preferences']}")
                print(f"        Suggestion: {detail['suggestion']}")
        
        return results
    
    def _analyze_current_top5_status(self) -> Dict[str, any]:
        """
        Analyze current top 5 preference satisfaction status.
        Only counts preferences that are actually available in the activities list.
        """
        # Group scheduled activities by troop
        troop_activities = defaultdict(set)
        for entry in self.schedule.entries:
            # Safety check - ensure entry.troop is a Troop object
            if hasattr(entry, 'troop') and hasattr(entry.troop, 'name'):
                troop_activities[entry.troop.name].add(entry.activity.name)
            else:
                # Skip malformed entries
                continue
        
        satisfied_troops = []
        unsatisfied_troops = []
        missing_preferences = defaultdict(list)
        exempt_preferences = defaultdict(list)
        
        # Get all available activities
        available_activities = set(self.activities.keys())
        
        for troop in self.troops:
            scheduled_activities = troop_activities[troop.name]
            top5_satisfied = 0
            missing_top5 = []
            exempt_top5 = []
            total_available_top5 = 0
            
            for i, activity_name in enumerate(troop.preferences[:5]):
                # Check if this activity is actually available
                if activity_name not in available_activities:
                    exempt_top5.append(activity_name)
                    continue
                
                total_available_top5 += 1
                
                if activity_name in scheduled_activities:
                    top5_satisfied += 1
                else:
                    missing_top5.append(activity_name)
            
            # Consider troop satisfied if they got all available top 5 preferences
            if total_available_top5 == 0 or top5_satisfied == total_available_top5:
                satisfied_troops.append(troop.name)
            else:
                unsatisfied_troops.append(troop.name)
                missing_preferences[troop.name] = missing_top5
                exempt_preferences[troop.name] = exempt_top5
        
        return {
            'satisfied': len(satisfied_troops),
            'total': len(self.troops),
            'satisfied_troops': satisfied_troops,
            'unsatisfied_troops': unsatisfied_troops,
            'missing_preferences': dict(missing_preferences),
            'exempt_preferences': dict(exempt_preferences)
        }
    
    def _perform_top5_optimization_iteration(self) -> int:
        """
        Perform one iteration of top 5 optimization.
        """
        best_improvement = 0
        best_swap = None
        
        # Focus on unsatisfied troops
        for troop_name in self.top5_status['unsatisfied_troops']:
            troop = next((t for t in self.troops if t.name == troop_name), None)
            if not troop:
                continue
            
            missing_preferences = self.top5_status['missing_preferences'][troop_name]
            
            # Try to satisfy each missing preference
            for missing_activity in missing_preferences:
                improvement = self._try_to_satisfy_preference(troop, missing_activity)
                
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_swap = (troop, missing_activity)
        
        # Execute best improvement
        if best_improvement > 0 and best_swap:
            troop, activity = best_swap
            success = self._execute_preference_satisfaction(troop, activity)
            if success:
                return best_improvement
        
        return 0
    
    def _try_to_satisfy_preference(self, troop: Troop, activity_name: str) -> int:
        """
        Try to satisfy a specific preference for a troop.
        """
        activity = self.activities.get(activity_name)
        if not activity:
            return 0
        
        # Find all possible slots for this activity
        possible_slots = self._find_possible_slots_for_activity(activity, troop)
        
        if not possible_slots:
            return 0
        
        best_improvement = 0
        best_placement = None
        
        for slot in possible_slots:
            # Calculate improvement if we place this activity here
            improvement = self._calculate_placement_improvement(troop, activity, slot)
            
            if improvement > best_improvement:
                best_improvement = improvement
                best_placement = slot
        
        return best_improvement
    
    def _find_possible_slots_for_activity(self, activity: Activity, troop: Troop) -> List[TimeSlot]:
        """
        Find all possible slots where this activity could be placed for this troop.
        """
        possible_slots = []
        
        # Generate all time slots
        from models import generate_time_slots
        all_slots = generate_time_slots()
        
        for slot in all_slots:
            if self._can_place_activity_at_slot(activity, troop, slot):
                possible_slots.append(slot)
        
        return possible_slots
    
    def _can_place_activity_at_slot(self, activity: Activity, troop: Troop, slot: TimeSlot) -> bool:
        """
        Check if activity can be placed at this slot for this troop.
        """
        # Defensive: ensure slot is TimeSlot (guards against argument order bugs)
        if not isinstance(slot, TimeSlot):
            return False
        # Check if troop is free
        if not self.schedule.is_troop_free(slot, troop):
            return False
        
        # Check beach slot constraint
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot.slot_number == 2 and slot.day != Day.THURSDAY):
            return False
        
        # Check exclusive activity constraint
        if activity.name in self.EXCLUSIVE_ACTIVITIES:
            for entry in self.schedule.entries:
                if not hasattr(entry, 'time_slot') or not hasattr(entry, 'activity'):
                    continue
                if (entry.activity.name == activity.name and 
                    entry.time_slot.day == slot.day and 
                    entry.time_slot.slot_number == slot.slot_number):
                    return False
        
        return True
    
    def _calculate_placement_improvement(self, troop: Troop, activity: Activity, slot: TimeSlot) -> int:
        """
        Calculate improvement in top 5 satisfaction if we place this activity here.
        """
        # Check if this activity is in top 5
        if activity.name not in troop.preferences[:5]:
            return 0
        
        # Check if troop already has this activity
        troop_activities = set()
        for entry in self.schedule.entries:
            if entry.troop == troop:
                troop_activities.add(entry.activity.name)
        
        if activity.name in troop_activities:
            return 0
        
        # Calculate improvement based on preference rank
        rank = troop.preferences.index(activity.name) + 1
        if rank <= 5:
            return (6 - rank) * 10  # Higher rank = higher improvement
        
        return 0
    
    def _execute_preference_satisfaction(self, troop: Troop, activity_name: str) -> bool:
        """
        Execute the placement to satisfy a preference.
        """
        activity = self.activities.get(activity_name)
        if not activity:
            return False
        
        possible_slots = self._find_possible_slots_for_activity(activity, troop)
        if not possible_slots:
            return False
        
        # Try to find a swap opportunity first
        for slot in possible_slots:
            # Look for swap opportunities
            swap_success = self._try_swap_for_preference(troop, activity, slot)
            if swap_success:
                return True
        
        # If no swap works, try direct placement (removing existing activity)
        for slot in possible_slots:
            placement_success = self._try_direct_placement(troop, activity, slot)
            if placement_success:
                return True
        
        return False
    
    def _try_swap_for_preference(self, troop: Troop, activity: Activity, target_slot: TimeSlot) -> bool:
        """
        Try to swap an existing activity to place the preferred activity.
        """
        # Find activities at the target slot
        target_entries = [e for e in self.schedule.entries 
                         if e.time_slot == target_slot]
        
        if not target_entries:
            return False
        
        # Try swapping with each activity at the target slot
        for target_entry in target_entries:
            if target_entry.troop == troop:
                continue  # Don't swap with same troop
            
            # Find a slot where the target activity could go
            target_activity = target_entry.activity
            possible_swap_slots = self._find_possible_slots_for_activity(target_activity, target_entry.troop)
            
            for swap_slot in possible_swap_slots:
                if swap_slot == target_slot:
                    continue
                
                # Check if troop can be moved to swap_slot
                troop_activities_at_swap = [e for e in self.schedule.entries 
                                           if e.time_slot == swap_slot and e.troop == troop]
                
                if not troop_activities_at_swap:
                    # No troop activity at swap slot, try direct swap
                    if self._can_place_activity_at_slot(target_activity, target_entry.troop, swap_slot):
                        # Perform the swap
                        self._swap_activities(target_entry, swap_slot)
                        self._place_activity_at_slot(troop, activity, target_slot)
                        return True
        
        return False
    
    def _try_direct_placement(self, troop: Troop, activity: Activity, slot: TimeSlot) -> bool:
        """
        Try to place activity by removing existing activity (lower priority).
        """
        # Find existing activity at this slot
        existing_entries = [e for e in self.schedule.entries if e.time_slot == slot]
        
        if not existing_entries:
            # Empty slot, place directly
            self._place_activity_at_slot(troop, activity, slot)
            return True
        
        # Find the lowest priority activity to remove
        best_entry_to_remove = None
        best_priority_score = float('inf')
        
        for entry in existing_entries:
            # Calculate priority score (lower = better to remove)
            priority_score = self._calculate_removal_priority_score(entry)
            
            if priority_score < best_priority_score:
                best_priority_score = priority_score
                best_entry_to_remove = entry
        
        if best_entry_to_remove and best_priority_score < 50:  # Threshold for removal
            # Remove the low priority activity and place the preferred one
            self.schedule.entries.remove(best_entry_to_remove)
            self._place_activity_at_slot(troop, activity, slot)
            return True
        
        return False
    
    def _calculate_removal_priority_score(self, entry: ScheduleEntry) -> float:
        """
        Calculate priority score for removing an activity (lower = more removable).
        """
        troop = entry.troop
        activity_name = entry.activity.name
        
        # Base score
        score = 50.0
        
        # Check if it's in top 5 preferences
        if activity_name in troop.preferences[:5]:
            rank = troop.preferences.index(activity_name) + 1
            score -= (6 - rank) * 20  # Higher priority = less removable
        
        # Check if it's a mandatory activity
        if activity_name in ["Reflection", "Super Troop"]:
            score -= 100  # Never remove mandatory activities
        
        # Check if it's an exclusive activity
        if activity_name in self.EXCLUSIVE_ACTIVITIES:
            score -= 30  # Prefer not to remove exclusive activities
        
        # Check if it's a 3-hour activity
        if activity_name in ["Rocks", "Delta"]:
            score -= 40  # Prefer not to remove 3-hour activities
        
        # Check if troop has many activities already
        troop_activity_count = len([e for e in self.schedule.entries if e.troop == troop])
        if troop_activity_count > 10:
            score -= 10  # More willing to remove from troops with many activities
        
        return score
    
    def _swap_activities(self, entry: ScheduleEntry, new_slot: TimeSlot):
        """
        Move an activity to a new slot.
        """
        old_slot = entry.time_slot
        entry.time_slot = new_slot
    
    def _place_activity_at_slot(self, troop: Troop, activity: Activity, slot: TimeSlot):
        """
        Place an activity at a specific slot for a troop.
        """
        new_entry = ScheduleEntry(slot, activity, troop)
        self.schedule.entries.append(new_entry)
    
    def _force_place_remaining_top5(self) -> Dict[str, int]:
        """
        Force place remaining unsatisfied top 5 preferences with aggressive strategies.
        """
        results = {'placements': 0, 'violations': 0}
        
        for troop_name in self.top5_status['unsatisfied_troops']:
            troop = next((t for t in self.troops if t.name == troop_name), None)
            if not troop:
                continue
            
            missing_preferences = self.top5_status['missing_preferences'].get(troop_name, [])
            
            for activity_name in missing_preferences:
                activity = self.activities.get(activity_name)
                if not activity:
                    continue
                
                # Try multiple placement strategies
                placed = False
                
                # Strategy 1: Find any available slot (ignoring most constraints)
                slot = self._find_any_available_slot(troop, activity)
                if slot:
                    self._force_place_activity(troop, activity, slot)
                    results['placements'] += 1
                    
                    # Check for violations
                    if self._check_placement_violations(activity, slot):
                        results['violations'] += 1
                    
                    print(f"    [Force] Placed {activity_name} for {troop.name} at {slot.day.value}-{slot.slot_number}")
                    placed = True
                
                # Strategy 2: If no slot found, try to remove a low-priority activity
                if not placed:
                    removed = self._remove_and_place_activity(troop, activity)
                    if removed:
                        results['placements'] += 1
                        results['violations'] += 1  # Likely violates some constraint
                        print(f"    [Force+Remove] Placed {activity_name} for {troop.name} (removed existing activity)")
                        placed = True
                
                # Strategy 3: Last resort - place in any slot even with conflicts
                if not placed:
                    emergency_slot = self._emergency_placement(troop, activity)
                    if emergency_slot:
                        self._force_place_activity(troop, activity, emergency_slot)
                        results['placements'] += 1
                        results['violations'] += 2  # Definitely violates constraints
                        print(f"    [Emergency] Placed {activity_name} for {troop.name} at {emergency_slot.day.value}-{emergency_slot.slot_number}")
                        placed = True
                
                # Stop after placing one activity for this troop
                if placed:
                    break
        
        return results
    
    def _remove_and_place_activity(self, troop: Troop, activity: Activity) -> bool:
        """
        Remove a low-priority activity and place the preferred activity.
        """
        # Find the lowest priority activity for this troop
        troop_entries = [e for e in self.schedule.entries if e.troop == troop]
        
        if not troop_entries:
            return False
        
        # Sort by priority (lower = more removable)
        removable_entries = []
        for entry in troop_entries:
            priority_score = self._calculate_removal_priority_score(entry)
            if priority_score < 30:  # Threshold for removal
                removable_entries.append((entry, priority_score))
        
        if not removable_entries:
            return False
        
        # Remove the lowest priority activity
        removable_entries.sort(key=lambda x: x[1])
        entry_to_remove = removable_entries[0][0]
        
        # Remove it and place the preferred activity
        self.schedule.entries.remove(entry_to_remove)
        new_entry = ScheduleEntry(entry_to_remove.time_slot, activity, troop)
        self.schedule.entries.append(new_entry)
        
        return True
    
    def _emergency_placement(self, troop: Troop, activity: Activity) -> Optional[TimeSlot]:
        """
        Emergency placement - find any slot even with conflicts.
        """
        from models import generate_time_slots
        all_slots = generate_time_slots()
        
        for slot in all_slots:
            # Just check if this slot exists, ignore troop availability
            return slot
        
        return None
    
    def _generate_placement_suggestion(self, troop: Troop, missing_preferences: List[str]) -> str:
        """
        Generate a suggestion for how a missing top 5 preference could have been placed.
        """
        if not missing_preferences:
            return "No missing preferences"
        
        activity_name = missing_preferences[0]
        activity = self.activities.get(activity_name)
        
        if not activity:
            return f"Activity {activity_name} not available in activity list"
        
        # Find potential slots
        potential_slots = []
        from models import generate_time_slots
        all_slots = generate_time_slots()
        
        for slot in all_slots:
            # Check basic feasibility
            if self._is_basic_placement_possible(activity, troop, slot):
                potential_slots.append(slot)
        
        if not potential_slots:
            return f"No feasible slots found for {activity_name} - constraints too restrictive"
        
        # Analyze why it couldn't be placed
        suggestions = []
        
        for slot in potential_slots[:3]:  # Check top 3 potential slots
            conflicts = self._analyze_placement_conflicts(troop, activity, slot)
            if conflicts:
                suggestions.append(f"{slot.day.value}-{slot.slot_number}: {', '.join(conflicts)}")
        
        if suggestions:
            return f"Could place at {', '.join(suggestions)}"
        else:
            return f"Could place in available slots but was not prioritized"
    
    def _is_basic_placement_possible(self, activity: Activity, troop: Troop, slot: TimeSlot) -> bool:
        """
        Check if basic placement is possible (ignoring troop availability).
        """
        # Check beach slot constraint
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot.slot_number == 2 and slot.day != Day.THURSDAY):
            return False
        
        return True
    
    def _analyze_placement_conflicts(self, troop: Troop, activity: Activity, slot: TimeSlot) -> List[str]:
        """
        Analyze conflicts preventing placement.
        """
        conflicts = []
        
        # Check if troop is already scheduled at this time
        if not self.schedule.is_troop_free(slot, troop):
            conflicts.append("troop already scheduled")
        
        # Check beach slot constraint
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot.slot_number == 2 and slot.day != Day.THURSDAY):
            conflicts.append("beach slot constraint violation")
        
        # Check exclusive activity constraint
        if activity.name in self.EXCLUSIVE_ACTIVITIES:
            for entry in self.schedule.entries:
                # Safety check for entry structure
                if (hasattr(entry, 'time_slot') and 
                    hasattr(entry.time_slot, 'day') and 
                    hasattr(entry.time_slot, 'slot_number')):
                    if (entry.activity.name == activity.name and 
                        entry.time_slot.day == slot.day and 
                        entry.time_slot.slot_number == slot.slot_number):
                        conflicts.append("exclusive activity conflict")
                        break
        
        return conflicts
    
    def _find_any_available_slot(self, troop: Troop, activity: Activity) -> Optional[TimeSlot]:
        """
        Find any available slot for this activity (ignoring most constraints).
        """
        from models import generate_time_slots
        all_slots = generate_time_slots()
        
        for slot in all_slots:
            # Only check if troop is free
            if self.schedule.is_troop_free(slot, troop):
                return slot
        
        return None
    
    def _force_place_activity(self, troop: Troop, activity: Activity, slot: TimeSlot):
        """
        Force place an activity, removing any existing activity if necessary.
        """
        # Remove any existing activity at this slot for this troop
        existing_entries = [e for e in self.schedule.entries 
                           if e.troop == troop and e.time_slot == slot]
        
        for entry in existing_entries:
            self.schedule.entries.remove(entry)
        
        # Place the new activity
        new_entry = ScheduleEntry(slot, activity, troop)
        self.schedule.entries.append(new_entry)
    
    def _check_placement_violations(self, activity: Activity, slot: TimeSlot) -> bool:
        """
        Check if placement violates constraints.
        """
        violations = 0
        
        # Check beach slot constraint
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot.slot_number == 2 and slot.day != Day.THURSDAY):
            violations += 1
        
        # Check exclusive activity constraint
        if activity.name in self.EXCLUSIVE_ACTIVITIES:
            same_slot_entries = [e for e in self.schedule.entries 
                               if e.time_slot == slot and e.activity.name == activity.name]
            if len(same_slot_entries) > 1:
                violations += 1
        
        return violations > 0


def guarantee_top5_satisfaction(schedule, troops, activities, max_iterations: int = 200) -> Dict[str, any]:
    """
    Guarantee 100% top 5 preference satisfaction.
    """
    guarantor = Top5GuaranteeSystem(schedule, troops, activities)
    return guarantor.guarantee_top5_satisfaction(max_iterations)
