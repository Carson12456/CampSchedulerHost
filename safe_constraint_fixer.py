#!/usr/bin/env python3
"""
Safe Constraint Violation Fixer - Only fixes violations without creating new ones.
"""

class SafeConstraintFixer:
    """Safe constraint violation reduction system."""
    
    def __init__(self, safe_optimizer):
        self.optimizer = safe_optimizer
        self.schedule = safe_optimizer.schedule
        self.troops = safe_optimizer.troops
        self.time_slots = safe_optimizer.time_slots
        
        # Activity replacements for constraint fixes
        self.replacement_activities = {
            'accuracy_conflicts': ['Nature Canoe', 'Troop Canoe', 'Dr. DNA', 'Loon Lore'],
            'wet_dry_wet': ['Swimming', 'Canoeing', 'Kayaking', 'Aqua Trampoline'],
            'same_area': ['Nature Canoe', 'Troop Canoe', 'Dr. DNA', 'Loon Lore', 'Orienteering'],
            'beach_slot': ['Swimming', 'Aqua Trampoline', 'Canoeing', 'Kayaking'],
            'capacity': ['Nature Canoe', 'Troop Canoe', 'Dr. DNA', 'Loon Lore']
        }
    
    def fix_constraint_violations_safely(self):
        """Safely fix constraint violations without creating new ones."""
        print("    [Safe Constraint Fix] Starting comprehensive violation reduction...")
        
        total_fixed = 0
        max_iterations = 3  # Conservative approach
        
        for iteration in range(max_iterations):
            print(f"      Iteration {iteration + 1}/{max_iterations}")
            
            iteration_fixed = 0
            iteration_fixed += self._fix_accuracy_conflicts_safely()
            iteration_fixed += self._fix_wet_dry_wet_patterns_safely()
            iteration_fixed += self._fix_same_area_same_day_conflicts_safely()
            iteration_fixed += self._fix_beach_slot_conflicts_safely()
            iteration_fixed += self._fix_capacity_violations_safely()
            iteration_fixed += self._fix_overlapping_activities_safely()
            iteration_fixed += self._fix_exclusive_area_conflicts_safely()
            
            print(f"      Fixed {iteration_fixed} violations in iteration {iteration + 1}")
            total_fixed += iteration_fixed
            
            if iteration_fixed == 0:
                print("      No more violations can be fixed safely")
                break
        
        print(f"    [Safe Constraint Fix] Total violations fixed: {total_fixed}")
        return total_fixed
    
    def _fix_accuracy_conflicts_safely(self):
        """Safely fix accuracy conflicts by replacing lower priority activities."""
        accuracy_activities = ['Troop Rifle', 'Troop Shotgun', 'Archery']
        fixed = 0
        
        for troop in self.troops:
            troop_entries = self.schedule.get_troop_schedule(troop)
            
            # Group by day
            day_accuracy = {}
            for entry in troop_entries:
                if entry.activity.name in accuracy_activities:
                    day = entry.time_slot.day
                    if day not in day_accuracy:
                        day_accuracy[day] = []
                    day_accuracy[day].append(entry)
            
            # Fix days with multiple accuracy activities
            for day, entries in day_accuracy.items():
                if len(entries) > 1:
                    # Sort by priority (higher priority = keep)
                    entries.sort(key=lambda e: troop.get_priority(e.activity.name))
                    
                    # Replace lower priority accuracy activities
                    for entry in entries[1:]:  # Keep the highest priority
                        replacements = self.replacement_activities['accuracy_conflicts']
                        
                        for replacement_name in replacements:
                            # Try to find a safe replacement
                            replacement_activity = self._find_activity_by_name(replacement_name)
                            if replacement_activity:
                                if self.optimizer.safe_move_entry(entry, entry.time_slot):
                                    # Actually replace the activity
                                    self.schedule.remove_entry(entry)
                                    self.schedule.add_entry(entry.time_slot, replacement_activity, troop)
                                    fixed += 1
                                    print(f"        Fixed accuracy conflict: Replaced {entry.activity.name} with {replacement_name} for {troop.name}")
                                    break
                        else:
                            print(f"        Could not fix accuracy conflict for {troop.name} - no safe replacements found")
        
        return fixed
    
    def _fix_wet_dry_wet_patterns_safely(self):
        """Safely fix wet-dry-wet patterns by replacing middle dry activities."""
        wet_activities = ['Swimming', 'Canoeing', 'Kayaking', 'Sailing', 'Aqua Trampoline', 'Canoe Snorkel']
        dry_activities = ['Climbing Tower', 'Archery', 'Rifle', 'Shotgun', 'Orienteering']
        fixed = 0
        
        for troop in self.troops:
            troop_entries = self.schedule.get_troop_schedule(troop)
            
            # Check each day for wet-dry-wet patterns
            for day in set(entry.time_slot.day for entry in troop_entries):
                day_entries = [e for e in troop_entries if e.time_slot.day == day]
                day_entries.sort(key=lambda x: x.time_slot.slot_number)
                
                # Look for wet-dry-wet patterns
                for i in range(len(day_entries) - 2):
                    entry1, entry2, entry3 = day_entries[i:i+3]
                    
                    is_wet1 = entry1.activity.name in wet_activities
                    is_dry2 = entry2.activity.name in dry_activities
                    is_wet3 = entry3.activity.name in wet_activities
                    
                    if is_wet1 and is_dry2 and is_wet3:
                        # Replace the middle dry activity with a wet one
                        replacements = self.replacement_activities['wet_dry_wet']
                        
                        for replacement_name in replacements:
                            replacement_activity = self._find_activity_by_name(replacement_name)
                            if replacement_activity:
                                if self.optimizer.safe_move_entry(entry2, entry2.time_slot):
                                    # Replace the activity
                                    self.schedule.remove_entry(entry2)
                                    self.schedule.add_entry(entry2.time_slot, replacement_activity, troop)
                                    fixed += 1
                                    print(f"        Fixed wet-dry-wet: Replaced {entry2.activity.name} with {replacement_name} for {troop.name}")
                                    break
                        else:
                            print(f"        Could not fix wet-dry-wet for {troop.name} - no safe replacements found")
        
        return fixed
    
    def _fix_same_area_same_day_conflicts_safely(self):
        """Safely fix same area same day conflicts."""
        from models import EXCLUSIVE_AREAS
        fixed = 0
        
        for troop in self.troops:
            troop_entries = self.schedule.get_troop_schedule(troop)
            
            # Check for same area conflicts
            for area, activities in EXCLUSIVE_AREAS.items():
                area_entries = [e for e in troop_entries if e.activity.name in activities]
                
                # Group by day
                day_area_entries = {}
                for entry in area_entries:
                    day = entry.time_slot.day
                    if day not in day_area_entries:
                        day_area_entries[day] = []
                    day_area_entries[day].append(entry)
                
                # Fix days with multiple activities from same area
                for day, entries in day_area_entries.items():
                    if len(entries) > 1:
                        # Sort by priority (higher priority = keep)
                        entries.sort(key=lambda e: troop.get_priority(e.activity.name))
                        
                        # Replace lower priority activities
                        for entry in entries[1:]:
                            replacements = self.replacement_activities['same_area']
                            
                            for replacement_name in replacements:
                                replacement_activity = self._find_activity_by_name(replacement_name)
                                if replacement_activity:
                                    if self.optimizer.safe_move_entry(entry, entry.time_slot):
                                        self.schedule.remove_entry(entry)
                                        self.schedule.add_entry(entry.time_slot, replacement_activity, troop)
                                        fixed += 1
                                        print(f"        Fixed same area conflict: Replaced {entry.activity.name} with {replacement_name} for {troop.name}")
                                        break
                            else:
                                print(f"        Could not fix same area conflict for {troop.name} - no safe replacements found")
        
        return fixed
    
    def _fix_beach_slot_conflicts_safely(self):
        """Safely fix beach slot violations."""
        beach_activities = ['Swimming', 'Aqua Trampoline', 'Canoeing', 'Kayaking', 'Sailing']
        non_beach_activities = ['Climbing Tower', 'Archery', 'Rifle', 'Shotgun']
        fixed = 0
        
        # Find non-beach activities in beach slots
        for entry in self.schedule.entries:
            if (entry.activity.name in non_beach_activities and 
                entry.time_slot.slot_number in [1, 2]):  # Beach slots
                
                # Try to move to a non-beach slot
                for time_slot in self.time_slots:
                    if (time_slot.day == entry.time_slot.day and 
                        time_slot.slot_number not in [1, 2] and  # Non-beach slots
                        self.optimizer.safe_move_entry(entry, time_slot)):
                        fixed += 1
                        print(f"        Fixed beach slot: Moved {entry.troop.name} {entry.activity.name} to non-beach slot")
                        break
                else:
                    # If can't move, try to replace with beach activity
                    replacements = self.replacement_activities['beach_slot']
                    
                    for replacement_name in replacements:
                        replacement_activity = self._find_activity_by_name(replacement_name)
                        if replacement_activity:
                            if self.optimizer.safe_move_entry(entry, entry.time_slot):
                                self.schedule.remove_entry(entry)
                                self.schedule.add_entry(entry.time_slot, replacement_activity, entry.troop)
                                fixed += 1
                                print(f"        Fixed beach slot: Replaced {entry.activity.name} with {replacement_name} for {entry.troop.name}")
                                break
                    else:
                        print(f"        Could not fix beach slot violation for {entry.troop.name} {entry.activity.name}")
        
        return fixed
    
    def _fix_capacity_violations_safely(self):
        """Safely fix capacity violations."""
        fixed = 0
        
        # Check each time slot for capacity violations
        for time_slot in self.time_slots:
            slot_entries = self.schedule.get_entries_at_time(time_slot)
            
            # Define capacity limits
            max_capacity = 20
            if any(e.activity.name == 'Climbing Tower' for e in slot_entries):
                max_capacity = 15
            elif any(e.activity.name in ['Rifle', 'Shotgun'] for e in slot_entries):
                max_capacity = 12
            
            if len(slot_entries) > max_capacity:
                # Move excess entries to other slots
                excess_entries = slot_entries[max_capacity:]
                
                # Sort by priority (lower priority = move first)
                excess_entries.sort(key=lambda e: e.troop.get_priority(e.activity.name))
                
                for entry in excess_entries:
                    # Try to find alternative slot same day
                    for alt_slot in self.time_slots:
                        if (alt_slot.day == time_slot.day and 
                            alt_slot != time_slot and
                            self.optimizer.safe_move_entry(entry, alt_slot)):
                            fixed += 1
                            print(f"        Fixed capacity: Moved {entry.troop.name} {entry.activity.name} from overcrowded slot")
                            break
                    else:
                        # Try different day
                        for alt_slot in self.time_slots:
                            if (alt_slot != time_slot and
                                self.optimizer.safe_move_entry(entry, alt_slot)):
                                fixed += 1
                                print(f"        Fixed capacity: Moved {entry.troop.name} {entry.activity.name} to different day")
                                break
                        else:
                            print(f"        Could not fix capacity violation for {entry.troop.name} {entry.activity.name}")
        
        return fixed
    
    def _fix_overlapping_activities_safely(self):
        """Safely fix overlapping activities."""
        fixed = 0
        
        for troop in self.troops:
            troop_entries = self.schedule.get_troop_schedule(troop)
            
            # Check for overlaps
            for i, entry1 in enumerate(troop_entries):
                for entry2 in troop_entries[i+1:]:
                    if (entry1.time_slot.day == entry2.time_slot.day and
                        abs(entry1.time_slot.slot_number - entry2.time_slot.slot_number) < 1):
                        
                        # Found overlap - move lower priority entry
                        priority1 = troop.get_priority(entry1.activity.name)
                        priority2 = troop.get_priority(entry2.activity.name)
                        
                        entry_to_move = entry1 if priority1 > priority2 else entry2
                        
                        # Try to find alternative slot
                        for alt_slot in self.time_slots:
                            if self.optimizer.safe_move_entry(entry_to_move, alt_slot):
                                fixed += 1
                                print(f"        Fixed overlap: Moved {entry_to_move.troop.name} {entry_to_move.activity.name}")
                                break
                        else:
                            print(f"        Could not fix overlap for {entry_to_move.troop.name} {entry_to_move.activity.name}")
        
        return fixed
    
    def _fix_exclusive_area_conflicts_safely(self):
        """Safely fix exclusive area conflicts."""
        from models import EXCLUSIVE_AREAS
        fixed = 0
        
        # Check each time slot for exclusive area conflicts
        for time_slot in self.time_slots:
            slot_entries = self.schedule.get_entries_at_time(time_slot)
            
            # Check for Tower and Rifle Range conflicts
            exclusive_areas = ['Tower', 'Rifle Range']
            
            for area in exclusive_areas:
                area_activities = EXCLUSIVE_AREAS.get(area, [])
                area_entries = [e for e in slot_entries if e.activity.name in area_activities]
                
                if len(area_entries) > 1:
                    # Multiple troops in exclusive area - move lower priority entries
                    area_entries.sort(key=lambda e: e.troop.get_priority(e.activity.name))
                    
                    for entry in area_entries[1:]:  # Keep highest priority
                        for alt_slot in self.time_slots:
                            if self.optimizer.safe_move_entry(entry, alt_slot):
                                fixed += 1
                                print(f"        Fixed exclusive area: Moved {entry.troop.name} {entry.activity.name} from {area}")
                                break
                        else:
                            print(f"        Could not fix exclusive area conflict for {entry.troop.name} {entry.activity.name}")
        
        return fixed
    
    def _find_activity_by_name(self, activity_name):
        """Find activity object by name."""
        # This would need to be implemented based on your activity data structure
        # For now, return a mock object
        class MockActivity:
            def __init__(self, name):
                self.name = name
        
        return MockActivity(activity_name)
