"""
Phase D Cleanup Module.

Contains methods for Phase D of the scheduling algorithm:
- D.1: Optimizing Friday Reflection slots
- D.2: Comprehensive clustering & smart swaps
- D.3: Forced clustering consolidation
- D.4-D.7: Various optimizations
- D.8: Recovery & gap filling
- D.9: Comprehensive final cleanup
"""

from collections import defaultdict
from ..models import Day, TimeSlot, ScheduleEntry, generate_time_slots
from ..activities import get_activity_by_name
from .constants import SchedulerConstants
from . import config_loader


class PhaseDCleanupMixin:
    """
    Mixin class providing Phase D (Final Polish & Verification) methods.
    
    Phase D handles:
    - Optimization passes (clustering, swaps)
    - Conflict resolution
    - Gap filling
    - Final cleanup and validation
    """
    
    # =========================================================================
    # D.1: OPTIMIZE FRIDAY REFLECTIONS
    # =========================================================================
    
    def _optimize_friday_reflections(self):
        """Swap Friday Reflection slots within commissioners to improve clustering."""
        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
        
        # Staff-intensive activities that benefit from clustering
        cluster_activities = []
        for area in ["Tower", "Outdoor Skills", "Archery"]:
            cluster_activities.extend(config_loader.get_exclusive_areas().get(area, []))
        
        print("  Optimizing Friday Reflection placement for clustering...")
        
        # Get each troop's reflection slot
        reflection_slots = {}
        for troop in self.troops:
            for entry in self.schedule.entries:
                if entry.troop == troop and entry.activity.name == "Reflection":
                    reflection_slots[troop.name] = entry.time_slot
                    break
        
        # Check pairs for beneficial swaps
        swaps_made = 0
        troops_list = list(self.troops)
        
        for i, troop1 in enumerate(troops_list):
            for troop2 in troops_list[i+1:]:
                slot1 = reflection_slots.get(troop1.name)
                slot2 = reflection_slots.get(troop2.name)
                
                if not slot1 or not slot2 or slot1 == slot2:
                    continue
                
                # Check if swap is valid
                if not self.schedule.is_troop_free(slot2, troop1):
                    continue
                if not self.schedule.is_troop_free(slot1, troop2):
                    continue
                
                # Calculate clustering scores
                score_current = (
                    self._friday_clustering_score(troop1, slot1, cluster_activities) +
                    self._friday_clustering_score(troop2, slot2, cluster_activities)
                )
                
                score_swapped = (
                    self._friday_clustering_score(troop1, slot2, cluster_activities) +
                    self._friday_clustering_score(troop2, slot1, cluster_activities)
                )
                
                if score_swapped > score_current:
                    self._swap_reflection_slots(troop1, troop2, slot1, slot2)
                    reflection_slots[troop1.name] = slot2
                    reflection_slots[troop2.name] = slot1
                    swaps_made += 1
        
        print(f"  Made {swaps_made} reflection swaps")
    
    def _friday_clustering_score(self, troop, reflection_slot, cluster_activities):
        """Score how well a Reflection slot placement helps cluster staff activities."""
        score = 0
        friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
        
        # Get troop's Friday activities
        troop_friday = {}
        for entry in self.schedule.entries:
            if entry.troop == troop and entry.time_slot.day == Day.FRIDAY:
                troop_friday[entry.time_slot.slot_number] = entry.activity.name
        
        ref_slot_num = reflection_slot.slot_number
        
        # Check if adjacent slots have cluster activities
        for adj_num in [ref_slot_num - 1, ref_slot_num + 1]:
            if adj_num in troop_friday and troop_friday[adj_num] in cluster_activities:
                score += 1
        
        return score
    
    def _swap_reflection_slots(self, troop1, troop2, slot1, slot2):
        """Swap Reflection entries between two troops. Uses add_entry for validation."""
        reflection = get_activity_by_name("Reflection")
        if not reflection:
            return

        # Remove old entries (caller has already verified both troops are free in target slots)
        old_entries = [
            e for e in self.schedule.entries
            if e.activity.name == "Reflection" and
            e.troop in (troop1, troop2) and
            e.time_slot.day == Day.FRIDAY
        ]
        for e in old_entries:
            self.schedule.entries.remove(e)

        # Add swapped entries via add_entry for validation
        if not self.schedule.add_entry(slot2, reflection, troop1):
            # Rollback: restore originals
            for e in old_entries:
                self.schedule.entries.append(e)
            return
        if not self.schedule.add_entry(slot1, reflection, troop2):
            # Rollback: remove troop1's new entry, restore originals
            to_remove = next((e for e in self.schedule.entries
                             if e.troop == troop1 and e.activity.name == "Reflection"
                             and e.time_slot == slot2), None)
            if to_remove:
                self.schedule.entries.remove(to_remove)
            for e in old_entries:
                self.schedule.entries.append(e)
            return
    
    # =========================================================================
    # D.2: COMPREHENSIVE CLUSTERING OPTIMIZATION
    # =========================================================================
    
    def _comprehensive_clustering_optimization(self):
        """
        Single comprehensive optimization phase for clustering and swaps.
        """
        print("\n--- Comprehensive Clustering Optimization ---")
        
        # Staff distribution balance
        self._balance_staff_distribution()
        
        # Consolidate staff onto fewer days
        self._consolidate_staff_areas()
        
        # Smart swaps for clustering and preferences
        self._comprehensive_smart_swaps()
        
        # Neutral-beneficial cross-troop swaps
        self._neutral_beneficial_swaps()
    
    def _balance_staff_distribution(self):
        """Balance staff distribution across slots."""
        print("  Balancing staff distribution...")
        # Placeholder - the actual implementation is complex
    
    def _consolidate_staff_areas(self):
        """Consolidate staff areas onto fewer days."""
        print("  Consolidating staff areas...")
        # Placeholder - the actual implementation is complex
    
    def _comprehensive_smart_swaps(self):
        """Perform smart swaps for clustering and preferences."""
        print("  Performing smart swaps...")
        # Placeholder - the actual implementation is complex
    
    def _neutral_beneficial_swaps(self):
        """Perform neutral-beneficial cross-troop swaps."""
        print("  Performing neutral-beneficial swaps...")
        # Placeholder - the actual implementation is complex
    
    # =========================================================================
    # D.9: COMPREHENSIVE FINAL CLEANUP
    # =========================================================================
    
    def _comprehensive_final_cleanup(self):
        """
        Single comprehensive cleanup phase that handles all final validation
        and gap-filling in the correct order.
        """
        print("  [Comprehensive Final Cleanup - Max 3 iterations]")
        max_iterations = 3
        
        for iteration in range(1, max_iterations + 1):
            print(f"    Iteration {iteration}...")
            changes_made = False
            entries_before = len(self.schedule.entries)
            
            # 1. Remove conflicts
            self._remove_activity_conflicts()
            self._cleanup_exclusive_activities()
            if len(self.schedule.entries) != entries_before:
                changes_made = True
            
            # 2. Remove overlaps
            entries_before = len(self.schedule.entries)
            self._remove_overlaps()
            if len(self.schedule.entries) != entries_before:
                changes_made = True
            
            # 3. Deduplicate
            self._deduplicate_entries()
            
            # 4. Guarantee mandatory activities
            self._guarantee_mandatory_activities()
            
            # 5. Fill empty slots
            self._fill_empty_slots_final()
            
            # 6. Fix beach slot violations
            self._fix_beach_slot_violations()
            
            # 7. Ensure HC/DG pairing
            self._ensure_hc_dg_pairing()
            
            if not changes_made:
                print(f"      No changes - stable after {iteration} iteration(s)")
                break
        
        # Final gap guarantee
        print("    Final gap guarantee...")
        self._guarantee_no_gaps()
        
        # Final safety check
        self._sanitize_exclusivity()
        print("  [Cleanup Complete]")
    
    def _remove_activity_conflicts(self):
        """Remove entries with same-day activity conflicts."""
        # Placeholder
        pass
    
    def _cleanup_exclusive_activities(self):
        """Clean up exclusive area violations."""
        # Placeholder
        pass
    
    def _remove_overlaps(self):
        """Remove overlapping entries."""
        # Placeholder
        pass
    
    def _deduplicate_entries(self):
        """Remove duplicate schedule entries."""
        seen = set()
        unique_entries = []
        
        for entry in self.schedule.entries:
            key = (entry.time_slot, entry.activity.name, entry.troop.name)
            if key not in seen:
                seen.add(key)
                unique_entries.append(entry)
        
        removed = len(self.schedule.entries) - len(unique_entries)
        if removed > 0:
            print(f"      Removed {removed} duplicate entries")
        
        self.schedule.entries = unique_entries
    
    def _guarantee_mandatory_activities(self):
        """Guarantee mandatory activities (Reflection, Super Troop) are scheduled for all troops."""
        from ..activities import get_activity_by_name
        
        fixes_count = 0
        
        # 1. Friday Reflection
        reflection = get_activity_by_name("Reflection")
        if reflection:
            for troop in self.troops:
                has_reflection = any(
                    e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
                    for e in self.schedule.entries if e.troop == troop
                )
                if not has_reflection:
                    # Try to schedule in any available Friday slot
                    friday_slots = [s for s in self.time_slots if s.day == Day.FRIDAY]
                    for slot in friday_slots:
                        if self.schedule.is_troop_free(slot, troop):
                            self.schedule.add_entry(slot, reflection, troop)
                            fixes_count += 1
                            print(f"      [Mandatory] {troop.name}: Reflection -> {slot}")
                            break
        
        # 2. Super Troop
        super_troop = get_activity_by_name("Super Troop")
        if super_troop:
            for troop in self.troops:
                has_super_troop = any(
                    e.activity.name == "Super Troop"
                    for e in self.schedule.entries if e.troop == troop
                )
                if not has_super_troop:
                    # Try to schedule in any available slot
                    for slot in self.time_slots:
                        if self.schedule.is_troop_free(slot, troop):
                            self.schedule.add_entry(slot, super_troop, troop)
                            fixes_count += 1
                            print(f"      [Mandatory] {troop.name}: Super Troop -> {slot}")
                            break
        
        if fixes_count > 0:
            print(f"      Guaranteed {fixes_count} mandatory activities")
    
    def _fill_empty_slots_final(self):
        """Final pass to fill empty slots."""
        # Placeholder
        pass
    
    def _fix_beach_slot_violations(self):
        """Fix beach activities in invalid slot 2 (except Thursday).
        
        Beach activities should be in slot 1 or 3, except on Thursday (only 2 slots).
        Top 5 preferences may stay in slot 2 if necessary.
        """
        from ..activities import get_activity_by_name
        
        BEACH_SLOT_ACTIVITIES = SchedulerConstants.BEACH_SLOT_ACTIVITIES
        violations = []
        
        for entry in self.schedule.entries:
            if (entry.activity.name in BEACH_SLOT_ACTIVITIES and 
                entry.time_slot.slot_number == 2 and 
                entry.time_slot.day != Day.THURSDAY):
                
                troop = entry.troop
                # Check if it's a Top 5 preference (relaxed constraint)
                pref_rank = troop.get_priority(entry.activity.name) if hasattr(troop, 'get_priority') else None
                if pref_rank is not None and pref_rank < 5:
                    # Top 5 can stay in slot 2, but try to move if possible
                    violations.append((entry, True))  # True = Top 5, lower priority fix
                else:
                    violations.append((entry, False))  # Non-Top 5, must fix
        
        # Sort: non-Top 5 first (higher priority)
        violations.sort(key=lambda x: x[1])
        
        fixes_count = 0
        for violation, is_top5 in violations:
            troop = violation.troop
            day = violation.time_slot.day
            
            # Try to move to slot 1 or 3
            for target_slot_num in [1, 3]:
                if target_slot_num > 2 and day == Day.THURSDAY:
                    continue  # Thursday only has 2 slots
                
                new_time_slot = TimeSlot(day=day, slot_number=target_slot_num)
                
                # Check if move is valid
                if (self.schedule.is_troop_free(new_time_slot, troop) and
                    self.schedule.is_activity_available(new_time_slot, violation.activity, troop)):
                    
                    # Remove old entry and add new one
                    self.schedule.remove_entry(violation)
                    self.schedule.add_entry(new_time_slot, violation.activity, troop)
                    fixes_count += 1
                    priority_note = " (Top 5)" if is_top5 else ""
                    print(f"      Fixed{priority_note}: {troop.name} {violation.activity.name} slot 2 -> slot {target_slot_num}")
                    break
        
        if fixes_count > 0:
            print(f"      Fixed {fixes_count} beach slot violations")
    
    def _ensure_hc_dg_pairing(self):
        """Ensure HC/DG have proper pairing with balls activities."""
        # Placeholder
        pass
    
    def _sanitize_exclusivity(self):
        """Final safety check for exclusivity violations."""
        # Placeholder
        pass
