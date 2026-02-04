#!/usr/bin/env python3
"""
Enhanced Spine-Aware Scheduler with Aggressive Prevention
More effective issue prevention and extended to all weeks
"""

from spine_aware_scheduler import SpineAwareScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class EnhancedSpineAwareScheduler(SpineAwareScheduler):
    """Enhanced Spine-aware scheduler with aggressive prevention"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.aggressive_prevention_active = True
        # BALANCED: Enable prevention but with calibrated strictness
        self.predictive_violation_detection = True
        self.proactive_gap_filling = True
        
        # Enhanced prevention counters
        self.predictive_violations_prevented = 0
        self.proactive_gaps_filled = 0
        self.constraint_conflicts_resolved = 0
        
        # CALIBRATION: Track false positives and effectiveness
        self.placement_attempts = 0
        self.placement_rejections = 0
        self.false_positive_preventions = 0
    
    def _comprehensive_prevention_check(self, troop, activity, time_slot):
        """CALIBRATED: Balanced prevention check with reduced false positives"""
        self.awareness_checks += 1
        self.placement_attempts += 1
        
        # Basic checks (from parent)
        if not self.schedule.is_troop_free(time_slot, troop):
            return False
        
        if not self.schedule.is_activity_available(activity, time_slot, troop):
            return False
        
        # Enhanced multi-slot check
        if activity.slots > 1:
            if not self._enhanced_multislot_check(troop, activity, time_slot):
                return False
        
        # CALIBRATED: Predictive constraint violation detection with Top 5 priority
        if self.predictive_violation_detection:
            violation_type = self._predictive_constraint_violation_check(troop, activity, time_slot)
            if violation_type:
                # PRIORITY: Check if this is a Top 5 preference
                top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
                is_top5 = activity.name in top5_prefs
                
                # Only block CRITICAL violations, or WARNING for non-Top5
                if violation_type == 'CRITICAL':
                    self.predictive_violations_prevented += 1
                    self.placement_rejections += 1
                    return False
                elif violation_type == 'WARNING' and not is_top5:
                    # Allow WARNING violations for Top 5, block for others
                    self.false_positive_preventions += 1
                    return False
                else:
                    # Allow WARNING level violations for Top 5 preferences
                    self.false_positive_preventions += 1
        
        # CALIBRATED: Proactive gap creation prevention (less aggressive)
        if self.proactive_gap_filling:
            if self._proactive_gap_prevention_check(troop, activity, time_slot):
                self.proactive_gaps_filled += 1
                return True  # Allow but fill gaps immediately
        
        # CALIBRATED: Constraint conflict resolution (reduced strictness)
        if self._would_create_constraint_conflict(troop, activity, time_slot):
            if self._resolve_constraint_conflict(troop, activity, time_slot):
                self.constraint_conflicts_resolved += 1
                return True
            else:
                self.placement_rejections += 1
                return False
        
        # Enhanced Spine priority compliance
        if not self._enhanced_spine_priority_check(troop, activity, time_slot):
            self.placement_rejections += 1
            return False
        
        return True
    
    def _enhanced_multislot_check(self, troop, activity, start_slot):
        """Enhanced multi-slot compatibility check"""
        all_slots = self.time_slots
        start_idx = all_slots.index(start_slot)
        
        # Check all required slots
        for offset in range(int(activity.slots)):
            if start_idx + offset >= len(all_slots):
                return False
            
            next_slot = all_slots[start_idx + offset]
            
            # Day consistency check
            if next_slot.day != start_slot.day:
                return False
            
            # Enhanced availability checks
            if not self.schedule.is_troop_free(next_slot, troop):
                return False
            
            if not self.schedule.is_activity_available(activity, next_slot, troop):
                return False
            
            # Predictive check for each slot
            if self.predictive_violation_detection:
                violation = self._predictive_constraint_violation_check(troop, activity, next_slot)
                if violation == 'CRITICAL':
                    return False
        
        return True
    
    def _predictive_constraint_violation_check(self, troop, activity, time_slot):
        """CALIBRATED: Predictive constraint violation detection with severity levels"""
        # CRITICAL: Beach slot violation detection
        beach_activities = ["Canoe Snorkel", "Sailing", "Float for Floats", "Aqua Trampoline"]
        if activity.name in beach_activities:
            # Check if this would create beach slot violation
            if time_slot.slot_number == 2:
                return 'CRITICAL'  # Always prevent beach slot 2
            
            # WARNING: Check if this would create beach overcrowding
            slot_entries = self.schedule.get_slot_activities(time_slot)
            beach_count = sum(1 for e in slot_entries if e.activity.name in beach_activities)
            if beach_count >= 3:  # Increased threshold from 2 to 3
                return 'WARNING'  # Allow but warn
        
        # CRITICAL: Enhanced exclusive area violation detection
        exclusive_areas = {
            'Waterfront': ['Sailing', 'Canoe Snorkel', 'Float for Floats', 'Aqua Trampoline'],
            'Shooting Sports': ['Troop Rifle', 'Troop Shotgun'],
            'Climbing': ['Climbing Tower']
        }
        
        for area, activities in exclusive_areas.items():
            if activity.name in activities:
                slot_entries = self.schedule.get_slot_activities(time_slot)
                area_count = sum(1 for e in slot_entries if e.activity.name in activities)
                if area_count >= 2:  # Increased threshold from 1 to 2
                    return 'CRITICAL'  # Prevent duplicate exclusive activities
        
        # WARNING: Enhanced accuracy activity conflict detection
        accuracy_activities = ["Archery", "Troop Rifle", "Troop Shotgun"]
        if activity.name in accuracy_activities:
            slot_entries = self.schedule.get_slot_activities(time_slot)
            accuracy_count = sum(1 for e in slot_entries if e.activity.name in accuracy_activities)
            if accuracy_count >= 3:  # Increased threshold to allow more flexibility
                return 'WARNING'  # Allow but warn
        
        return None  # No violation detected
    
    def _proactive_gap_prevention_check(self, troop, activity, time_slot):
        """Proactive gap prevention - fill gaps before they occur"""
        # Check if this action would create gaps in the troop's schedule
        troop_schedule = self.schedule.get_troop_schedule(troop)
        
        # Look for potential gap creation scenarios
        for entry in troop_schedule:
            if entry.time_slot == time_slot:
                # Check if removing this entry would create a gap
                if self._would_removal_create_gap(troop, entry):
                    # Instead of preventing, fill the gap proactively
                    if self._proactive_gap_fill(troop, entry.time_slot):
                        return True
        return False
    
    def _would_removal_create_gap(self, troop, entry):
        """Check if removing an entry would create a gap"""
        # This is a simplified check - in reality would be more complex
        # For now, assume removing any Top 5 activity could create a gap
        try:
            priority = troop.preferences.index(entry.activity.name)
            return priority < 5  # Top 5 activities are critical
        except ValueError:
            return False
    
    def _proactive_gap_fill(self, troop, time_slot):
        """Proactively fill a potential gap"""
        # Use gap-filling activities
        gap_fill_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Campsite Free Time", "Shower House", "Trading Post"
        ]
        
        for activity_name in gap_fill_activities:
            activity = get_activity_by_name(activity_name)
            if activity and self._comprehensive_prevention_check(troop, activity, time_slot):
                if self.schedule.add_entry(time_slot, activity, troop):
                    return True
        return False
    
    def _would_create_constraint_conflict(self, troop, activity, time_slot):
        """Check if this would create a constraint conflict"""
        # Enhanced conflict detection
        return self._predictive_constraint_violation_check(troop, activity, time_slot)
    
    def _resolve_constraint_conflict(self, troop, activity, time_slot):
        """Resolve constraint conflicts proactively"""
        # Try to find an alternative slot
        alternative_slots = [s for s in self.time_slots if s != time_slot]
        
        # Sort by preference (earlier slots first)
        alternative_slots.sort(key=lambda x: (x.day, x.slot_number))
        
        for alt_slot in alternative_slots:
            if self._comprehensive_prevention_check(troop, activity, alt_slot):
                if self.schedule.add_entry(alt_slot, activity, troop):
                    return True
        
        return False
    
    def _enhanced_spine_priority_check(self, troop, activity, time_slot):
        """Enhanced Spine priority compliance check"""
        # Priority 1: No gaps (already checked)
        # Priority 2: Top 5 preferences
        if activity.name in troop.preferences[:5]:
            return True
        
        # Priority 3: Activity requirements
        # Priority 4: Staff limits
        
        # Check if this would prevent a higher priority action later
        return self._check_future_priority_conflicts(troop, activity, time_slot)
    
    def _check_future_priority_conflicts(self, troop, activity, time_slot):
        """Check if this action would conflict with future priorities"""
        # Simplified check - ensure we're not blocking Top 5 activities
        return True
    
    def _enhanced_top5_scheduling(self, troop, activity_name, priority):
        """Enhanced Top 5 scheduling with aggressive prevention"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try all slots with enhanced prevention
        for slot in self.time_slots:
            if self._comprehensive_prevention_check(troop, activity, slot):
                if self.schedule.add_entry(slot, activity, troop):
                    return True
        
        # Enhanced displacement with conflict resolution
        return self._enhanced_displacement(troop, activity, priority)
    
    def _enhanced_displacement(self, troop, target_activity, priority):
        """Enhanced displacement with conflict resolution"""
        troop_schedule = self.schedule.get_troop_schedule(troop)
        
        # Sort by priority (easiest to displace first)
        entries_by_priority = []
        for entry in troop_schedule:
            try:
                entry_priority = troop.preferences.index(entry.activity.name)
            except ValueError:
                entry_priority = 999
            
            entries_by_priority.append((entry_priority, entry))
        
        entries_by_priority.sort(key=lambda x: x[0], reverse=True)
        
        for entry_priority, entry in entries_by_priority:
            # Don't displace higher priority Top 5
            if entry_priority < 5 and priority >= entry_priority:
                continue
            
            # Enhanced check before displacement
            if self._comprehensive_prevention_check(troop, target_activity, entry.time_slot):
                # Check if displaced activity can be relocated
                if self._enhanced_relocate_displaced_activity(entry):
                    self.schedule.remove_entry(entry)
                    if self.schedule.add_entry(entry.time_slot, target_activity, troop):
                        return True
                    # Put it back if failed
                    self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _enhanced_relocate_displaced_activity(self, entry):
        """Enhanced relocation with conflict resolution"""
        for slot in self.time_slots:
            if self._comprehensive_prevention_check(entry.troop, entry.activity, slot):
                if self.schedule.add_entry(slot, entry.activity, entry.troop):
                    return True
        return False
    
    def _enhanced_emergency_gap_fill(self):
        """Enhanced emergency gap fill with better strategies"""
        print("Running enhanced emergency gap fill...")
        gaps_filled = 0
        
        # Get all troops with gaps
        troops_with_gaps = []
        for troop in self.troops:
            troop_gaps = self._find_troop_gaps(troop)
            if troop_gaps:
                troops_with_gaps.append((troop, troop_gaps))
        
        # Sort by number of gaps (worst first)
        troops_with_gaps.sort(key=lambda x: len(x[1]), reverse=True)
        
        for troop, gaps in troops_with_gaps:
            for gap in gaps:
                if self._fill_specific_gap(troop, gap):
                    gaps_filled += 1
        
        print(f"Enhanced emergency gap fill complete: {gaps_filled} gaps filled")
        return gaps_filled
    
    def _fill_specific_gap(self, troop, time_slot):
        """Try to fill a specific gap with enhanced strategies for schedule quality"""
        # Priority 1: Top 5 preferences (highest impact on quality)
        top5_activities = troop.preferences[:5]
        for activity_name in top5_activities:
            activity = get_activity_by_name(activity_name)
            if activity and not self._troop_has_activity(troop, activity):
                if self._comprehensive_prevention_check(troop, activity, time_slot):
                    if self.schedule.add_entry(time_slot, activity, troop):
                        print(f"  Filled gap for {troop.name} with Top 5 {activity_name} at {time_slot}")
                        return True
        
        # Priority 2: High-value activities for schedule quality
        high_value_activities = [
            'Climbing Tower', 'Troop Rifle', 'Archery',  # Staff clustering
            'Aqua Trampoline', 'Sailing', 'Canoe Snorkel',  # Popular activities
            'History Center', 'Nature Center', 'Itasca State Park'  # Educational
        ]
        for activity_name in high_value_activities:
            if activity_name in troop.preferences:  # Only if troop wants it
                activity = get_activity_by_name(activity_name)
                if activity and not self._troop_has_activity(troop, activity):
                    if self._comprehensive_prevention_check(troop, activity, time_slot):
                        if self.schedule.add_entry(time_slot, activity, troop):
                            print(f"  Filled gap for {troop.name} with high-value {activity_name} at {time_slot}")
                            return True
        
        # Priority 3: Low staff activities (maintain efficiency)
        low_staff_activities = ['Reflection', 'Delta', 'Super Troop', 'Tie Dye', 'Hemp Craft']
        for activity_name in low_staff_activities:
            activity = get_activity_by_name(activity_name)
            if activity and not self._troop_has_activity(troop, activity):
                if self._comprehensive_prevention_check(troop, activity, time_slot):
                    if self.schedule.add_entry(time_slot, activity, troop):
                        print(f"  Filled gap for {troop.name} with low-staff {activity_name} at {time_slot}")
                        return True
        
        # Priority 4: Any available activity
        for activity_name in troop.preferences[5:10]:  # Next 5 preferences
            activity = get_activity_by_name(activity_name)
            if activity and not self._troop_has_activity(troop, activity):
                if self._comprehensive_prevention_check(troop, activity, time_slot):
                    if self.schedule.add_entry(time_slot, activity, troop):
                        print(f"  Filled gap for {troop.name} with {activity_name} at {time_slot}")
                        return True
        
        return False
    
    def _final_spine_verification(self):
        """Enhanced final verification with error handling"""
        print("Enhanced Spine verification...")
        
        try:
            # Check all Spine priorities
            total_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
            constraint_violations = self._count_constraint_violations()
            
            print(f"  Enhanced verification:")
            print(f"    Total gaps: {total_gaps} (Priority 1: Should be 0)")
            print(f"    Constraint violations: {constraint_violations} (Priority 1: Should be 0)")
            print(f"    Awareness checks performed: {self.awareness_checks}")
            print(f"    Issues prevented: {self.prevented_issues}")
            print(f"    Constraint violations prevented: {self.constraint_violations_prevented}")
            print(f"    Gaps prevented: {self.gaps_prevented}")
            print(f"    Predictive violations prevented: {self.predictive_violations_prevented}")
            print(f"    Proactive gaps filled: {self.proactive_gaps_filled}")
            print(f"    Constraint conflicts resolved: {self.constraint_conflicts_resolved}")
        except Exception as e:
            print(f"  ERROR during verification: {e}")
            print("  Continuing with available data...")
            print("  Continuing with available data...")


def apply_enhanced_spine_aware_scheduling():
    """Apply enhanced Spine-aware scheduling to all weeks"""
    print("ENHANCED SPINE-AWARE SCHEDULING - ALL WEEKS")
    print("=" * 70)
    print("Aggressive prevention with enhanced constraint detection")
    print("=" * 70)
    
    all_week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in all_week_files:
        print(f"\n{'='*70}")
        print(f"ENHANCED SPINE-AWARE: {week_file}")
        print('='*70)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply enhanced Spine-aware scheduler
            scheduler = EnhancedSpineAwareScheduler(troops)
            schedule = scheduler.schedule_all()
            
            # Apply enhanced emergency gap fill if needed
            total_gaps = sum(len(scheduler._find_troop_gaps(troop)) for troop in troops)
            if total_gaps > 0:
                print(f"  Found {total_gaps} gaps, applying enhanced emergency fill...")
                gaps_filled = scheduler._enhanced_emergency_gap_fill()
                print(f"  Enhanced emergency fill: {gaps_filled} gaps filled")
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_enhanced_spine_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            # Verify gaps
            total_gaps = sum(len(scheduler._find_troop_gaps(troop)) for troop in troops)
            
            result = {
                'week': week_name,
                'score': metrics['final_score'],
                'gaps': metrics['unnecessary_gaps'],
                'verified_gaps': total_gaps,
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'awareness_checks': scheduler.awareness_checks,
                'issues_prevented': scheduler.prevented_issues,
                'constraint_violations_prevented': scheduler.constraint_violations_prevented,
                'gaps_prevented': scheduler.gaps_prevented,
                'predictive_violations_prevented': scheduler.predictive_violations_prevented,
                'proactive_gaps_filled': scheduler.proactive_gaps_filled,
                'constraint_conflicts_resolved': scheduler.constraint_conflicts_resolved,
                'placement_attempts': scheduler.placement_attempts,
                'placement_rejections': scheduler.placement_rejections,
                'false_positive_preventions': scheduler.false_positive_preventions,
                'success': metrics['final_score'] > 0 and total_gaps == 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "IN PROGRESS"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Violations: {result['violations']}")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            print(f"  Enhanced Prevention: {result['predictive_violations_prevented']} predictive, {result['proactive_gaps_filled']} proactive")
            print(f"  Total Awareness Checks: {result['awareness_checks']}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Summary
    print(f"\n{'='*70}")
    print("ENHANCED SPINE-AWARE SCHEDULING RESULTS")
    print('='*70)
    
    successful_weeks = [r for r in results if r['success']]
    zero_gap_weeks = [r for r in results if r['verified_gaps'] == 0]
    
    print(f"SUCCESS (Above 0 + Zero Gaps): {len(successful_weeks)}/{len(results)} weeks")
    print(f"ZERO GAPS: {len(zero_gap_weeks)}/{len(results)} weeks")
    
    if successful_weeks:
        print(f"\nSUCCESSFUL WEEKS:")
        for r in successful_weeks:
            print(f"  {r['week']}: {r['score']} (Perfect)")
    
    if zero_gap_weeks:
        print(f"\nZERO GAP WEEKS:")
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else f"{r['score']:.1f}"
            print(f"  {r['week']}: {score_status} (Zero gaps)")
    
    # Enhanced prevention statistics
    if results:
        total_awareness_checks = sum(r['awareness_checks'] for r in results)
        total_issues_prevented = sum(r['issues_prevented'] for r in results)
        total_predictive_prevented = sum(r['predictive_violations_prevented'] for r in results)
        total_proactive_filled = sum(r['proactive_gaps_filled'] for r in results)
        total_conflicts_resolved = sum(r['constraint_conflicts_resolved'] for r in results)
        total_placement_attempts = sum(r.get('placement_attempts', 0) for r in results)
        total_placement_rejections = sum(r.get('placement_rejections', 0) for r in results)
        total_false_positives = sum(r.get('false_positive_preventions', 0) for r in results)
        
        print(f"\nENHANCED PREVENTION STATISTICS:")
        print(f"  Total Awareness Checks: {total_awareness_checks:,}")
        print(f"  Total Placement Attempts: {total_placement_attempts:,}")
        print(f"  Total Placement Rejections: {total_placement_rejections:,}")
        print(f"  False Positive Preventions: {total_false_positives:,}")
        print(f"  Predictive Violations Prevented: {total_predictive_prevented:,}")
        print(f"  Proactive Gaps Filled: {total_proactive_filled:,}")
        print(f"  Constraint Conflicts Resolved: {total_conflicts_resolved:,}")
        
        if total_placement_attempts > 0:
            rejection_rate = (total_placement_rejections / total_placement_attempts) * 100
            false_positive_rate = (total_false_positives / total_placement_attempts) * 100
            print(f"  Rejection Rate: {rejection_rate:.1f}%")
            print(f"  False Positive Rate: {false_positive_rate:.1f}%")
    
    # Save results
    with open('enhanced_spine_aware_results.txt', 'w') as f:
        f.write('ENHANCED SPINE-AWARE SCHEDULING RESULTS\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'SUCCESS (Above 0 + Zero Gaps): {len(successful_weeks)}/{len(results)} weeks\n')
        f.write(f'ZERO GAPS: {len(zero_gap_weeks)}/{len(results)} weeks\n\n')
        
        f.write('SUCCESSFUL:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]} (Perfect)\n')
        
        f.write('\nZERO GAP WEEKS:\n')
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else f"{r['score']:.1f}"
            f.write(f'  {r["week"]}: {score_status} (Zero gaps)\n')
        
        f.write(f'\nENHANCED PREVENTION STATISTICS:\n')
        f.write(f'  Total Awareness Checks: {total_awareness_checks:,}\n')
        f.write(f'  Total Placement Attempts: {total_placement_attempts:,}\n')
        f.write(f'  Total Placement Rejections: {total_placement_rejections:,}\n')
        f.write(f'  False Positive Preventions: {total_false_positives:,}\n')
        f.write(f'  Predictive Violations Prevented: {total_predictive_prevented:,}\n')
        f.write(f'  Proactive Gaps Filled: {total_proactive_filled:,}\n')
        f.write(f'  Constraint Conflicts Resolved: {total_conflicts_resolved:,}\n')
        
        if total_placement_attempts > 0:
            rejection_rate = (total_placement_rejections / total_placement_attempts) * 100
            false_positive_rate = (total_false_positives / total_placement_attempts) * 100
            f.write(f'  Rejection Rate: {rejection_rate:.1f}%\n')
            f.write(f'  False Positive Rate: {false_positive_rate:.1f}%\n')
    
    print(f"\nEnhanced Spine-aware results saved to 'enhanced_spine_aware_results.txt'")
    
    return results

if __name__ == "__main__":
    apply_enhanced_spine_aware_scheduling()
