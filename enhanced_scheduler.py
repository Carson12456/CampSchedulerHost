#!/usr/bin/env python3
"""
Enhanced scheduler with improved constraint validation and performance optimizations.
Addresses key issues found in the comprehensive analysis:
1. Better constraint validation in optimization phases
2. Improved staff distribution balancing
3. Enhanced Top 5 enforcement
4. Performance optimizations
"""

from constrained_scheduler import ConstrainedScheduler
from models import Schedule, ScheduleEntry, TimeSlot, Day, EXCLUSIVE_AREAS
from activities import get_all_activities, get_activity_by_name
from typing import List, Dict, Set, Tuple
import random


class EnhancedScheduler(ConstrainedScheduler):
    """
    Enhanced scheduler with improved constraint handling and performance.
    Inherits from ConstrainedScheduler but adds better validation and optimization.
    """
    
    def __init__(self, troops: List, activities: List = None, voyageur_mode: bool = False):
        super().__init__(troops, activities, voyageur_mode)
        
        # Enhanced tracking for better optimization
        self.constraint_violations = []
        self.optimization_attempts = 0
        self.successful_optimizations = 0
        
        # Performance caches
        self._slot_availability_cache = {}
        self._troop_availability_cache = {}
        
    def schedule_all(self) -> Schedule:
        """Enhanced scheduling with better error handling and validation."""
        try:
            # Run the base scheduler
            schedule = super().schedule_all()
            
            # Apply enhanced optimizations
            self._apply_enhanced_optimizations()
            
            # Final validation
            self._validate_final_schedule()
            
            return schedule
            
        except Exception as e:
            self.logger.error(f"Enhanced scheduling failed: {e}")
            # Fallback to base scheduler
            return super().schedule_all()
    
    def _apply_enhanced_optimizations(self):
        """Apply targeted optimizations to improve schedule quality."""
        self.logger.info("Applying enhanced optimizations...")
        
        # CRITICAL FIX: First ensure no gaps exist
        self._emergency_gap_fix()
        
        # 1. Fix constraint violations
        self._fix_constraint_violations()
        
        # 2. Improve staff distribution
        self._improve_staff_distribution()
        
        # 3. Recover missing Top 5 activities
        self._recover_missing_top5()
        
        # 4. Optimize clustering
        self._optimize_clustering()
        
        # FINAL: Verify no gaps were created
        self._verify_no_gaps()
        
        self.logger.info(f"Enhanced optimizations complete. {self.successful_optimizations}/{self.optimization_attempts} successful")
    
    def _emergency_gap_fix(self):
        """Emergency fix to eliminate all gaps - CRITICAL for score."""
        self.logger.info("Running emergency gap fix...")
        
        gaps_filled = 0
        max_iterations = 10
        
        for iteration in range(max_iterations):
            iteration_filled = 0
            
            for troop in self.troops:
                # Find all gaps for this troop
                gaps = self._find_troop_gaps(troop)
                
                for gap_slot in gaps:
                    if self._fill_gap_safely(troop, gap_slot):
                        iteration_filled += 1
                        gaps_filled += 1
            
            self.logger.debug(f"Gap fix iteration {iteration + 1}: filled {iteration_filled} gaps")
            
            if iteration_filled == 0:
                break  # No more gaps to fill
        
        self.logger.info(f"Emergency gap fix complete: {gaps_filled} gaps filled")
    
    def _find_troop_gaps(self, troop) -> List[TimeSlot]:
        """Find all time slots where this troop has no activity."""
        gaps = []
        troop_schedule = self.schedule.get_troop_schedule(troop)
        occupied_slots = {(e.time_slot.day, e.time_slot.slot_number) for e in troop_schedule}
        
        for slot in self.time_slots:
            slot_key = (slot.day, slot.slot_number)
            if slot_key not in occupied_slots:
                gaps.append(slot)
        
        return gaps
    
    def _fill_gap_safely(self, troop, gap_slot: TimeSlot) -> bool:
        """Fill a specific gap with any available activity."""
        # Priority order for gap filling
        fill_activities = [
            "Campsite Free Time", "Super Troop", "Trading Post", "Shower House",
            "9 Square", "Gaga Ball", "Fishing", "Sauna", "Hemp Craft",
            "Dr. DNA", "Loon Lore", "Monkey's Fist", "Tie Dye",
            "Archery", "Water Polo", "Aqua Trampoline"
        ]
        
        # Debug: Print what we're trying
        self.logger.debug(f"Trying to fill gap for {troop.name} at {gap_slot.day.value}-{gap_slot.slot_number}")
        
        # Try each activity in priority order
        for activity_name in fill_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            # Check if troop already has this activity
            if self._troop_has_activity(troop, activity):
                continue
            
            # Check if activity can be scheduled in this slot
            try:
                if self._can_schedule_in_slot(troop, activity, gap_slot):
                    self.schedule.add_entry(gap_slot, activity, troop)
                    self.logger.debug(f"Successfully filled gap with {activity_name}")
                    return True
                else:
                    self.logger.debug(f"Cannot schedule {activity_name} in slot")
            except Exception as e:
                self.logger.debug(f"Error scheduling {activity_name}: {e}")
                continue
        
        # If no preferred activities work, try ANY available activity
        for activity in self.activities:
            if activity.slots > 1:  # Skip multi-slot for gap filling
                continue
            
            if self._troop_has_activity(troop, activity):
                continue
            
            try:
                if self._can_schedule_in_slot(troop, activity, gap_slot):
                    self.schedule.add_entry(gap_slot, activity, troop)
                    self.logger.debug(f"Successfully filled gap with fallback {activity.name}")
                    return True
            except Exception as e:
                self.logger.debug(f"Error with fallback {activity.name}: {e}")
                continue
        
        self.logger.warning(f"Failed to fill gap for {troop.name} at {gap_slot.day.value}-{gap_slot.slot_number}")
        return False
    
    def _troop_has_activity(self, troop, activity) -> bool:
        """Check if troop already has this activity."""
        for entry in self.schedule.get_troop_schedule(troop):
            if entry.activity.name == activity.name:
                return True
        return False
    
    def _can_schedule_in_slot(self, troop, activity, slot: TimeSlot) -> bool:
        """Check if activity can be scheduled in specific slot."""
        if not self.schedule.is_troop_free(slot, troop):
            return False
        
        if not self.schedule.is_activity_available(slot, activity, troop):
            return False
        
        # Additional constraint checks
        if self._would_violate_constraints_for_slot(troop, activity, slot):
            return False
        
        return True
    
    def _would_violate_constraints_for_slot(self, troop, activity, slot: TimeSlot) -> bool:
        """Check if scheduling would violate constraints."""
        # Check accuracy constraints
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        if activity.name in accuracy_activities:
            day_entries = [e for e in self.schedule.entries 
                          if e.troop == troop 
                          and e.time_slot.day == slot.day
                          and e.activity.name in accuracy_activities]
            if len(day_entries) > 0:
                return True
        
        # Check beach slot constraints
        if (activity.name in self.BEACH_SLOT_ACTIVITIES and 
            slot.day != Day.THURSDAY and 
            slot.slot_number == 2):
            return True
        
        # Check same-day conflicts
        day_activities = [e.activity.name for e in self.schedule.entries 
                        if e.troop == troop and e.time_slot.day == slot.day]
        
        # Prohibited pairs
        prohibited_pairs = [
            ("Troop Rifle", "Troop Shotgun"),
            ("Trading Post", "Campsite Free Time"),
            ("Trading Post", "Shower House")
        ]
        
        for act1, act2 in prohibited_pairs:
            if activity.name == act1 and act2 in day_activities:
                return True
            if activity.name == act2 and act1 in day_activities:
                return True
        
        return False
    
    def _verify_no_gaps(self):
        """Final verification that no gaps exist."""
        total_gaps = 0
        for troop in self.troops:
            gaps = len(self._find_troop_gaps(troop))
            if gaps > 0:
                self.logger.warning(f"Troop {troop.name} still has {gaps} gaps!")
                total_gaps += gaps
        
        if total_gaps == 0:
            self.logger.info("SUCCESS: No gaps detected - schedule is complete")
        else:
            self.logger.error(f"CRITICAL: {total_gaps} gaps remain - schedule incomplete")
            # Try one more emergency fill
            self._emergency_gap_fill_final(total_gaps)
    
    def _emergency_gap_fill_final(self, remaining_gaps: int):
        """Final emergency gap fill - use any activity possible."""
        self.logger.info(f"Running final emergency gap fill for {remaining_gaps} gaps...")
        
        filled = 0
        for troop in self.troops:
            gaps = self._find_troop_gaps(troop)
            
            for gap_slot in gaps:
                if self._fill_gap_with_anything(troop, gap_slot):
                    filled += 1
        
        self.logger.info(f"Final emergency fill: {filled} gaps filled")
        
        # Re-verify
        final_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
        if final_gaps == 0:
            self.logger.info("SUCCESS: All gaps eliminated after final emergency fill")
        else:
            self.logger.error(f"FAILED: {final_gaps} gaps remain after all attempts")
    
    def _fill_gap_with_anything(self, troop, gap_slot: TimeSlot) -> bool:
        """Fill gap with absolutely any activity - last resort."""
        # Try all activities, even duplicates
        for activity in self.activities:
            if activity.slots > 1:  # Skip multi-slot
                continue
            
            # Basic availability check
            if not self.schedule.is_troop_free(gap_slot, troop):
                continue
            
            if not self.schedule.is_activity_available(gap_slot, activity, troop):
                continue
            
            # Skip only the most critical constraint violations
            if self._would_cause_critical_violation(troop, activity, gap_slot):
                continue
            
            self.schedule.add_entry(gap_slot, activity, troop)
            return True
        
        return False
    
    def _would_cause_critical_violation(self, troop, activity, slot: TimeSlot) -> bool:
        """Check only for critical violations that would invalidate schedule."""
        # Only check the most critical constraints
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        
        # Critical: Multiple accuracy activities same day
        if activity.name in accuracy_activities:
            day_entries = [e for e in self.schedule.entries 
                          if e.troop == troop 
                          and e.time_slot.day == slot.day
                          and e.activity.name in accuracy_activities]
            if len(day_entries) > 0:
                return True
        
        # Critical: Rifle + Shotgun same day
        day_activities = [e.activity.name for e in self.schedule.entries 
                        if e.troop == troop and e.time_slot.day == slot.day]
        
        if activity.name == "Troop Rifle" and "Troop Shotgun" in day_activities:
            return True
        if activity.name == "Troop Shotgun" and "Troop Rifle" in day_activities:
            return True
        
        return False
    
    def _fix_constraint_violations(self):
        """Fix constraint violations with better validation."""
        violations = self._detect_constraint_violations()
        
        for violation in violations:
            self.optimization_attempts += 1
            
            if self._fix_violation_safely(violation):
                self.successful_optimizations += 1
                self.logger.debug(f"Fixed violation: {violation['type']}")
    
    def _detect_constraint_violations(self) -> List[Dict]:
        """Detect all constraint violations in the current schedule."""
        violations = []
        
        # Check beach slot violations
        for entry in self.schedule.entries:
            if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.day != Day.THURSDAY and 
                entry.time_slot.slot_number == 2):
                violations.append({
                    'type': 'beach_slot_violation',
                    'entry': entry,
                    'description': f"{entry.activity.name} in slot 2 on {entry.time_slot.day.value}"
                })
        
        # Check accuracy conflicts
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        for troop in self.troops:
            troop_entries = [e for e in self.schedule.entries if e.troop == troop]
            day_activities = {}
            
            for entry in troop_entries:
                day = entry.time_slot.day
                if day not in day_activities:
                    day_activities[day] = []
                day_activities[day].append(entry.activity.name)
            
            for day, activities in day_activities.items():
                accuracy_count = sum(1 for act in activities if act in accuracy_activities)
                if accuracy_count > 1:
                    violations.append({
                        'type': 'accuracy_conflict',
                        'troop': troop.name,
                        'day': day,
                        'activities': [act for act in activities if act in accuracy_activities]
                    })
        
        return violations
    
    def _fix_violation_safely(self, violation: Dict) -> bool:
        """Safely fix a constraint violation without creating new ones."""
        if violation['type'] == 'beach_slot_violation':
            entry = violation['entry']
            
            # Find alternative slots
            alternative_slots = [
                slot for slot in self.time_slots
                if (slot.day == entry.time_slot.day and 
                    slot.slot_number in [1, 3] and
                    self.schedule.is_troop_free(slot, entry.troop) and
                    self.schedule.is_activity_available(slot, entry.activity, entry.troop))
            ]
            
            if alternative_slots:
                # Move to the best alternative
                new_slot = min(alternative_slots, key=lambda s: s.slot_number)
                self.schedule.remove_entry(entry)
                self.schedule.add_entry(new_slot, entry.activity, entry.troop)
                return True
        
        elif violation['type'] == 'accuracy_conflict':
            # Find the lowest priority accuracy activity to move
            troop = next(t for t in self.troops if t.name == violation['troop'])
            day = violation['day']
            
            day_entries = [e for e in self.schedule.entries 
                          if e.troop.name == troop.name and e.time_slot.day == day
                          and e.activity.name in violation['activities']]
            
            if day_entries:
                # Move the lowest priority (highest rank) activity
                lowest_priority_entry = max(day_entries, 
                                          key=lambda e: troop.get_priority(e.activity.name))
                
                # Find new slot
                for slot in self.time_slots:
                    if (self.schedule.is_troop_free(slot, lowest_priority_entry.troop) and
                        self.schedule.is_activity_available(slot, lowest_priority_entry.activity, lowest_priority_entry.troop)):
                        
                        # Check if this would create accuracy conflict on new day
                        new_day_entries = [e for e in self.schedule.entries 
                                         if e.troop == lowest_priority_entry.troop 
                                         and e.time_slot.day == slot.day
                                         and e.activity.name in accuracy_activities]
                        
                        if len(new_day_entries) == 0:  # No conflict on new day
                            self.schedule.remove_entry(lowest_priority_entry)
                            self.schedule.add_entry(slot, lowest_priority_entry.activity, lowest_priority_entry.troop)
                            return True
        
        return False
    
    def _improve_staff_distribution(self):
        """Improve staff distribution across slots."""
        from evaluate_week_success import STAFF_MAP, ALL_STAFF_ACTIVITIES
        
        # Calculate current staff load per slot
        slot_loads = {}
        for slot in self.time_slots:
            slot_entries = self.schedule.get_slot_activities(slot)
            staff_count = sum(1 for e in slot_entries if e.activity.name in ALL_STAFF_ACTIVITIES)
            slot_loads[slot] = staff_count
        
        # Calculate average and identify outliers
        loads = list(slot_loads.values())
        avg_load = sum(loads) / len(loads) if loads else 0
        
        # Find overstaffed and understaffed slots
        overstaffed = [slot for slot, load in slot_loads.items() if load > avg_load + 2]
        understaffed = [slot for slot, load in slot_loads.items() if load < avg_load - 2]
        
        # Try to balance by moving flexible activities
        for over_slot in overstaffed:
            for under_slot in understaffed:
                if self._move_activity_between_slots(over_slot, under_slot):
                    # Update loads and continue
                    over_entries = self.schedule.get_slot_activities(over_slot)
                    under_entries = self.schedule.get_slot_activities(under_slot)
                    slot_loads[over_slot] = sum(1 for e in over_entries if e.activity.name in ALL_STAFF_ACTIVITIES)
                    slot_loads[under_slot] = sum(1 for e in under_entries if e.activity.name in ALL_STAFF_ACTIVITIES)
                    break
    
    def _move_activity_between_slots(self, from_slot: TimeSlot, to_slot: TimeSlot) -> bool:
        """Try to move a flexible activity from one slot to another."""
        from_entries = self.schedule.get_slot_activities(from_slot)
        
        # Prioritize moving low-priority or fill activities
        flexible_entries = [e for e in from_entries 
                          if e.activity.name in self.DEFAULT_FILL_PRIORITY]
        
        if not flexible_entries:
            flexible_entries = from_entries  # Fall back to any activity
        
        for entry in flexible_entries:
            if (self.schedule.is_troop_free(to_slot, entry.troop) and
                self.schedule.is_activity_available(to_slot, entry.activity, entry.troop)):
                
                # Check if this move would violate constraints
                if not self._would_violate_constraints(entry, to_slot):
                    self.schedule.remove_entry(entry)
                    self.schedule.add_entry(to_slot, entry.activity, entry.troop)
                    return True
        
        return False
    
    def _would_violate_constraints(self, entry: ScheduleEntry, new_slot: TimeSlot) -> bool:
        """Check if moving an entry would violate constraints."""
        # Basic availability already checked
        
        # Check accuracy constraints
        accuracy_activities = ["Troop Rifle", "Troop Shotgun", "Archery"]
        if entry.activity.name in accuracy_activities:
            day_entries = [e for e in self.schedule.entries 
                          if e.troop == entry.troop 
                          and e.time_slot.day == new_slot.day
                          and e.activity.name in accuracy_activities]
            if len(day_entries) > 0:
                return True
        
        # Check beach slot constraints
        if (entry.activity.name in self.BEACH_SLOT_ACTIVITIES and 
            new_slot.day != Day.THURSDAY and 
            new_slot.slot_number == 2):
            return True
        
        return False
    
    def _recover_missing_top5(self):
        """Enhanced recovery of missing Top 5 activities - CRITICAL for score."""
        self.logger.info("Running enhanced Top 5 recovery...")
        
        for troop in self.troops:
            troop_schedule = self.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            # Check Top 5 preferences
            missing_top5 = []
            for i, pref in enumerate(troop.preferences[:5]):
                if pref not in scheduled_activities:
                    missing_top5.append((pref, i))
            
            if missing_top5:
                self.logger.info(f"Troop {troop.name} missing {len(missing_top5)} Top 5 activities")
                
                # Try to schedule each missing Top 5 activity
                for pref, priority in missing_top5:
                    if self._schedule_missing_activity_aggressive(troop, pref, priority):
                        self.logger.info(f"SUCCESS: Recovered missing Top {priority+1} for {troop.name}: {pref}")
                        self.successful_optimizations += 1
                    else:
                        self.logger.warning(f"FAILED: Could not recover Top {priority+1} for {troop.name}: {pref}")
    
    def _schedule_missing_activity_aggressive(self, troop, activity_name: str, priority: int) -> bool:
        """Aggressively try to schedule a missing Top 5 activity."""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        self.optimization_attempts += 1
        
        # STRATEGY 1: Try to find any available slot
        slots_by_preference = self._get_slots_by_preference(troop, activity)
        
        for slot in slots_by_preference:
            if self._can_schedule_in_slot(troop, activity, slot):
                # Check multi-slot requirements
                if activity.slots > 1:
                    if self._check_consecutive_slots_available(troop, activity, slot):
                        self.schedule.add_entry(slot, activity, troop)
                        return True
                else:
                    self.schedule.add_entry(slot, activity, troop)
                    return True
        
        # STRATEGY 2: Try to displace a lower priority activity
        if self._displace_for_top5(troop, activity, priority):
            return True
        
        # STRATEGY 3: Try to swap with another troop
        if self._swap_for_top5(troop, activity, priority):
            return True
        
        return False
    
    def _displace_for_top5(self, troop, activity, priority: int) -> bool:
        """Try to displace a lower priority activity for Top 5."""
        troop_schedule = self.schedule.get_troop_schedule(troop)
        
        # Find entries that can be displaced (lower priority than current Top 5)
        for entry in troop_schedule:
            current_priority = troop.get_priority(entry.activity.name)
            
            # Only displace if current activity is lower priority than missing Top 5
            if current_priority > priority:
                # Try to move the displaced activity to another slot
                if self._move_entry_to_new_slot(entry):
                    # Now schedule the Top 5 activity in the freed slot
                    self.schedule.add_entry(entry.time_slot, activity, troop)
                    self.logger.info(f"Displaced {entry.activity.name} (priority {current_priority}) for Top 5 {activity.name}")
                    return True
        
        return False
    
    def _move_entry_to_new_slot(self, entry) -> bool:
        """Try to move an entry to a new slot."""
        # Remove temporarily
        self.schedule.remove_entry(entry)
        
        # Try to find new slot
        for slot in self.time_slots:
            if self._can_schedule_in_slot(entry.troop, entry.activity, slot):
                self.schedule.add_entry(slot, entry.activity, entry.troop)
                return True
        
        # Couldn't find new slot, put it back
        self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        return False
    
    def _swap_for_top5(self, troop, activity, priority: int) -> bool:
        """Try to swap activities with another troop to get Top 5."""
        # Find troops that have the desired activity but don't need it as much
        for other_troop in self.troops:
            if other_troop == troop:
                continue
            
            other_schedule = self.schedule.get_troop_schedule(other_troop)
            other_priority = other_troop.get_priority(activity.name)
            
            # Only swap if other troop values it less
            if other_priority > priority:
                for entry in other_schedule:
                    if entry.activity.name == activity.name:
                        # Try to find a swap that works for both troops
                        if self._perform_swap(troop, other_troop, activity, entry):
                            return True
        
        return False
    
    def _perform_swap(self, troop1, troop2, desired_activity, entry_to_swap) -> bool:
        """Perform a swap between two troops."""
        # Find an activity from troop1 that troop2 could take
        troop1_schedule = self.schedule.get_troop_schedule(troop1)
        
        for entry1 in troop1_schedule:
            # Don't swap Top 5 activities
            if troop1.get_priority(entry1.activity.name) < 5:
                continue
            
            # Check if troop2 can take troop1's activity
            if self._can_schedule_in_slot(troop2, entry1.activity, entry_to_swap.time_slot):
                # Check if troop1 can take the desired activity
                if self._can_schedule_in_slot(troop1, desired_activity, entry1.time_slot):
                    # Perform the swap
                    self.schedule.remove_entry(entry_to_swap)
                    self.schedule.remove_entry(entry1)
                    
                    self.schedule.add_entry(entry_to_swap.time_slot, entry1.activity, troop2)
                    self.schedule.add_entry(entry1.time_slot, desired_activity, troop1)
                    
                    self.logger.info(f"Swapped {entry1.activity.name} from {troop1.name} with {desired_activity.name} from {troop2.name}")
                    return True
        
        return False
    
    def _get_slots_by_preference(self, troop, activity) -> List[TimeSlot]:
        """Get slots ordered by preference for this troop and activity."""
        # Simple heuristic: prefer earlier in the week, avoid conflicts
        slots = list(self.time_slots)
        
        # Sort by day preference (Monday to Friday)
        day_order = {Day.MONDAY: 0, Day.TUESDAY: 1, Day.WEDNESDAY: 2, 
                    Day.THURSDAY: 3, Day.FRIDAY: 4}
        
        slots.sort(key=lambda s: (day_order[s.day], s.slot_number))
        
        return slots
    
    def _check_consecutive_slots_available(self, troop, activity, start_slot: TimeSlot) -> bool:
        """Check if consecutive slots are available for multi-slot activities."""
        slots_needed = int(activity.slots + 0.5)  # Round up
        
        start_idx = self.time_slots.index(start_slot)
        
        for offset in range(slots_needed):
            if start_idx + offset >= len(self.time_slots):
                return False
            
            slot = self.time_slots[start_idx + offset]
            
            # Must be same day
            if slot.day != start_slot.day:
                return False
            
            # Must be available
            if not self.schedule.is_troop_free(slot, troop):
                return False
            
            if not self.schedule.is_activity_available(slot, activity, troop):
                return False
        
        return True
    
    def _optimize_clustering(self):
        """Optimize activity clustering to reduce excess days."""
        # This is a simplified version - full clustering optimization is complex
        cluster_areas = ["Tower", "Outdoor Skills", "Rifle Range", "Handicrafts"]
        
        for area in cluster_areas:
            self._consolidate_cluster_area(area)
    
    def _consolidate_cluster_area(self, area: str):
        """Try to consolidate activities in a cluster area."""
        activities = EXCLUSIVE_AREAS.get(area, [])
        if not activities:
            return
        
        # Find all entries for this area
        area_entries = [e for e in self.schedule.entries if e.activity.name in activities]
        
        # Group by day
        days_used = {}
        for entry in area_entries:
            day = entry.time_slot.day
            if day not in days_used:
                days_used[day] = []
            days_used[day].append(entry)
        
        # If using more days than necessary, try to consolidate
        if len(days_used) > 1:
            # Find the day with the most activities (primary day)
            primary_day = max(days_used.keys(), key=lambda d: len(days_used[d]))
            
            # Try to move activities from other days to primary day
            for day, entries in days_used.items():
                if day == primary_day:
                    continue
                
                for entry in entries:
                    # Try to find a slot on primary day
                    for slot in self.time_slots:
                        if (slot.day == primary_day and
                            self.schedule.is_troop_free(slot, entry.troop) and
                            self.schedule.is_activity_available(slot, entry.activity, entry.troop)):
                            
                            self.schedule.remove_entry(entry)
                            self.schedule.add_entry(slot, entry.activity, entry.troop)
                            break
    
    def _validate_final_schedule(self):
        """Final validation to ensure no critical violations."""
        violations = self._detect_constraint_violations()
        
        if violations:
            self.logger.warning(f"Final schedule has {len(violations)} violations:")
            for v in violations:
                self.logger.warning(f"  - {v['type']}: {v.get('description', 'N/A')}")
        else:
            self.logger.info("Final schedule validation passed - no violations detected")


# Factory function for easy integration
def create_enhanced_scheduler(troops: List, activities: List = None, voyageur_mode: bool = False):
    """Create an enhanced scheduler instance."""
    return EnhancedScheduler(troops, activities, voyageur_mode)
