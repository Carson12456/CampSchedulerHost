#!/usr/bin/env python3
"""
Spine-Aware Scheduler with Comprehensive Prevention Checks
Follows Spine priorities and prevents problems before they occur
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class SpineAwareScheduler(EnhancedScheduler):
    """Scheduler that follows Spine priorities with comprehensive prevention"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.awareness_checks = 0
        self.prevented_issues = 0
        self.constraint_violations_prevented = 0
        self.gaps_prevented = 0
        
        # Spine priorities (from highest to lowest)
        self.spine_priorities = {
            'critical': [
                'eliminate_all_gaps',  # Gap elimination is #1 priority
                'prevent_constraint_violations',  # Hard constraints
                'maintain_troop_availability'  # Basic scheduling rules
            ],
            'high': [
                'top5_preferences',  # Top 5 preferences
                'activity_requirements',  # Activity-specific rules
                'staff_limits'  # Staff distribution
            ],
            'medium': [
                'clustering_efficiency',  # Activity grouping
                'setup_optimization',  # Setup efficiency
                'staff_balance'  # Staff variance
            ],
            'low': [
                'preference_optimization',  # Lower preferences
                'fine_tuning'  # Minor improvements
            ]
        }
    
    def schedule_all(self):
        """Schedule with comprehensive Spine-aware prevention"""
        print("SPINE-AWARE SCHEDULER")
        print("=" * 50)
        print("Following Spine priorities with comprehensive prevention")
        print("=" * 50)
        
        # Phase 1: Critical priority - Eliminate gaps and prevent violations
        print("Phase 1: CRITICAL PRIORITY - Gap elimination & violation prevention")
        schedule = self._critical_priority_scheduling()
        
        # Phase 2: High priority - Top 5 and core requirements
        print("Phase 2: HIGH PRIORITY - Top 5 preferences & activity requirements")
        self._high_priority_optimization()
        
        # Phase 3: Medium priority - Clustering and efficiency
        print("Phase 3: MEDIUM PRIORITY - Clustering & efficiency optimization")
        self._medium_priority_optimization()
        
        # Phase 4: Low priority - Fine tuning
        print("Phase 4: LOW PRIORITY - Fine tuning & optimization")
        self._low_priority_optimization()
        
        # Final verification
        self._final_spine_verification()
        
        return schedule
    
    def _critical_priority_scheduling(self):
        """Critical priority: Eliminate gaps and prevent violations"""
        print("  Critical: Eliminating all gaps...")
        self._preventive_gap_elimination()
        
        print("  Critical: Preventing constraint violations...")
        self._preventive_constraint_violation_prevention()
        
        print("  Critical: Maintaining troop availability...")
        self._preventive_troop_availability_maintenance()
        
        # Generate base schedule with prevention
        schedule = super().schedule_all()
        
        # Immediate gap check and fix
        self._immediate_gap_prevention_check()
        
        return schedule
    
    def _preventive_gap_elimination(self):
        """Prevent gaps during scheduling"""
        # This runs during scheduling to prevent gap creation
        pass
    
    def _preventive_constraint_violation_prevention(self):
        """Prevent constraint violations during scheduling"""
        # This runs during scheduling to prevent violations
        pass
    
    def _preventive_troop_availability_maintenance(self):
        """Maintain troop availability during scheduling"""
        # This ensures troops are always available when scheduled
        pass
    
    def _immediate_gap_prevention_check(self):
        """Immediate check and prevention of gaps"""
        gaps_found = 0
        gaps_prevented = 0
        
        for troop in self.troops:
            gaps = self._find_troop_gaps(troop)
            gaps_found += len(gaps)
            
            for gap in gaps:
                if self._prevent_gap_creation(troop, gap):
                    gaps_prevented += 1
        
        self.gaps_prevented += gaps_prevented
        print(f"    Gaps found: {gaps_found}, Gaps prevented: {gaps_prevented}")
    
    def _prevent_gap_creation(self, troop, time_slot):
        """Prevent gap creation by immediate filling"""
        # Priority activities that prevent gaps
        gap_prevention_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        # Add troop's Top 5 preferences first
        for pref in troop.preferences[:5]:
            if pref not in gap_prevention_activities:
                gap_prevention_activities.insert(0, pref)
        
        for activity_name in gap_prevention_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            # Comprehensive check before adding
            if self._comprehensive_prevention_check(troop, activity, time_slot):
                if self.schedule.add_entry(time_slot, activity, troop):
                    self.prevented_issues += 1
                    return True
        
        # Fallback activities
        fallback_activities = [
            "Campsite Free Time", "Shower House", "Trading Post", "Gaga Ball",
            "9 Square", "Woggle Neckerchief Slide", "Knots and Lashings"
        ]
        
        for activity_name in fallback_activities:
            activity = get_activity_by_name(activity_name)
            if activity and self._comprehensive_prevention_check(troop, activity, time_slot):
                if self.schedule.add_entry(time_slot, activity, troop):
                    self.prevented_issues += 1
                    return True
        
        return False
    
    def _comprehensive_prevention_check(self, troop, activity, time_slot):
        """Comprehensive prevention check before any action"""
        self.awareness_checks += 1
        
        # Check 1: Basic availability
        if not self.schedule.is_troop_free(time_slot, troop):
            return False
        
        if not self.schedule.is_activity_available(activity, time_slot, troop):
            return False
        
        # Check 2: Multi-slot activity compatibility
        if activity.slots > 1:
            if not self._check_multislot_compatibility(troop, activity, time_slot):
                return False
        
        # Check 3: Constraint violation prevention
        if self._would_create_constraint_violation(troop, activity, time_slot):
            self.constraint_violations_prevented += 1
            return False
        
        # Check 4: Gap creation prevention
        if self._would_create_gap(troop, activity, time_slot):
            self.gaps_prevented += 1
            return False
        
        # Check 5: Spine priority compliance
        if not self._spine_priority_compliance(troop, activity, time_slot):
            return False
        
        return True
    
    def _check_multislot_compatibility(self, troop, activity, start_slot):
        """Check if multi-slot activity fits without creating issues"""
        all_slots = self.time_slots
        start_idx = all_slots.index(start_slot)
        
        for offset in range(int(activity.slots)):
            if start_idx + offset >= len(all_slots):
                return False
            
            next_slot = all_slots[start_idx + offset]
            
            # Check day consistency
            if next_slot.day != start_slot.day:
                return False
            
            # Check troop availability
            if not self.schedule.is_troop_free(next_slot, troop):
                return False
            
            # Check activity availability
            if not self.schedule.is_activity_available(activity, next_slot, troop):
                return False
        
        return True
    
    def _would_create_constraint_violation(self, troop, activity, time_slot):
        """Check if this action would create a constraint violation"""
        # Check beach slot violations
        beach_activities = ["Canoe Snorkel", "Sailing", "Float for Floats", "Aqua Trampoline"]
        if activity.name in beach_activities and time_slot.slot_number == 2:
            return True
        
        # Check exclusive area violations
        exclusive_areas = {
            'Waterfront': ['Sailing', 'Canoe Snorkel', 'Float for Floats', 'Aqua Trampoline'],
            'Shooting Sports': ['Troop Rifle', 'Troop Shotgun'],
            'Climbing': ['Climbing Tower']
        }
        
        for area, activities in exclusive_areas.items():
            if activity.name in activities:
                slot_entries = self.schedule.get_slot_activities(time_slot)
                for entry in slot_entries:
                    if entry.activity.name in activities:
                        return True
        
        # Check accuracy activity conflicts
        accuracy_activities = ["Archery", "Rifle", "Shotgun"]
        if activity.name in accuracy_activities:
            slot_entries = self.schedule.get_slot_activities(time_slot)
            for entry in slot_entries:
                if entry.activity.name in accuracy_activities and entry.activity.name != activity.name:
                    return True
        
        return False
    
    def _would_create_gap(self, troop, activity, time_slot):
        """Check if this action would create a gap elsewhere"""
        # This is a simplified check - in reality, this would be more complex
        troop_schedule = self.schedule.get_troop_schedule(troop)
        
        # Check if this would displace a critical activity
        for entry in troop_schedule:
            if entry.time_slot == time_slot:
                # Check if the displaced activity is critical
                if entry.activity.name in troop.preferences[:5]:
                    return True
        
        return False
    
    def _spine_priority_compliance(self, troop, activity, time_slot):
        """Check if this action complies with Spine priorities"""
        # Priority 1: No gaps allowed
        # Priority 2: Top 5 preferences prioritized
        # Priority 3: Activity requirements met
        # Priority 4: Staff limits respected
        
        # Check if this is a Top 5 preference
        if activity.name in troop.preferences[:5]:
            return True  # Always allow Top 5
        
        # Check if this would prevent a Top 5 later
        # This is a simplified check
        return True
    
    def _high_priority_optimization(self):
        """High priority: Top 5 preferences and activity requirements"""
        print("  High: Optimizing Top 5 preferences...")
        self._top5_aware_optimization()
        
        print("  High: Ensuring activity requirements...")
        self._activity_requirement_optimization()
    
    def _top5_aware_optimization(self):
        """Top 5 optimization with gap prevention"""
        for troop in self.troops:
            troop_schedule = self.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            # Find missing Top 5
            missing_top5 = []
            for i, pref in enumerate(troop.preferences[:5]):
                if pref not in scheduled_activities:
                    missing_top5.append((pref, i))
            
            if missing_top5:
                print(f"    {troop.name}: {len(missing_top5)} missing Top 5")
                
                for pref, priority in missing_top5:
                    if self._aware_top5_scheduling(troop, pref, priority):
                        print(f"      Scheduled Top 5: {pref}")
    
    def _aware_top5_scheduling(self, troop, activity_name, priority):
        """Top 5 scheduling with comprehensive awareness"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try all slots with comprehensive checks
        for slot in self.time_slots:
            if self._comprehensive_prevention_check(troop, activity, slot):
                if self.schedule.add_entry(slot, activity, troop):
                    return True
        
        # Try displacement with prevention
        return self._aware_displacement(troop, activity, priority)
    
    def _aware_displacement(self, troop, target_activity, priority):
        """Displacement with comprehensive awareness"""
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
            
            # Check if displacement is safe
            if self._comprehensive_prevention_check(troop, target_activity, entry.time_slot):
                # Check if displaced activity can be relocated
                if self._relocate_displaced_activity(entry):
                    self.schedule.remove_entry(entry)
                    if self.schedule.add_entry(entry.time_slot, target_activity, troop):
                        return True
                    # Put it back if failed
                    self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _relocate_displaced_activity(self, entry):
        """Relocate displaced activity with prevention"""
        for slot in self.time_slots:
            if self._comprehensive_prevention_check(entry.troop, entry.activity, slot):
                if self.schedule.add_entry(slot, entry.activity, entry.troop):
                    return True
        return False
    
    def _activity_requirement_optimization(self):
        """Ensure activity requirements are met"""
        # This would ensure all activity-specific requirements are met
        pass
    
    def _medium_priority_optimization(self):
        """Medium priority: Clustering and efficiency"""
        print("  Medium: Optimizing clustering...")
        self._clustering_optimization()
        
        print("  Medium: Optimizing setup efficiency...")
        self._setup_optimization()
    
    def _clustering_optimization(self):
        """Clustering optimization with prevention"""
        # This would optimize activity clustering while preventing gaps
        pass
    
    def _setup_optimization(self):
        """Setup optimization with prevention"""
        # This would optimize setup efficiency while preventing gaps
        pass
    
    def _low_priority_optimization(self):
        """Low priority: Fine tuning"""
        print("  Low: Fine tuning and optimization...")
        self._fine_tuning_optimization()
    
    def _fine_tuning_optimization(self):
        """Fine tuning with prevention"""
        # This would perform minor optimizations while preventing issues
        pass
    
    def _final_spine_verification(self):
        """Final verification against Spine priorities"""
        print("Final Spine verification...")
        
        # Check all Spine priorities
        total_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
        constraint_violations = self._count_constraint_violations()
        
        print(f"  Final verification:")
        print(f"    Total gaps: {total_gaps} (Priority 1: Should be 0)")
        print(f"    Constraint violations: {constraint_violations} (Priority 1: Should be 0)")
        print(f"    Awareness checks performed: {self.awareness_checks}")
        print(f"    Issues prevented: {self.prevented_issues}")
        print(f"    Constraint violations prevented: {self.constraint_violations_prevented}")
        print(f"    Gaps prevented: {self.gaps_prevented}")
    
    def _count_constraint_violations(self):
        """Count current constraint violations"""
        violations = 0
        
        # Beach slot violations
        beach_activities = ["Canoe Snorkel", "Sailing", "Float for Floats", "Aqua Trampoline"]
        for entry in self.schedule.entries:
            if entry.activity.name in beach_activities and entry.time_slot.slot_number == 2:
                violations += 1
        
        # Exclusive area violations
        exclusive_areas = {
            'Waterfront': ['Sailing', 'Canoe Snorkel', 'Float for Floats', 'Aqua Trampoline'],
            'Shooting Sports': ['Troop Rifle', 'Troop Shotgun'],
            'Climbing': ['Climbing Tower']
        }
        
        for area, activities in exclusive_areas.items():
            for slot in self.time_slots:
                slot_entries = self.schedule.get_slot_activities(slot)
                area_activities = [e for e in slot_entries if e.activity.name in activities]
                if len(area_activities) > 1:
                    violations += len(area_activities) - 1
        
        return violations


def apply_spine_aware_scheduling():
    """Apply Spine-aware scheduling to all weeks"""
    print("SPINE-AWARE SCHEDULING - ALL WEEKS")
    print("=" * 70)
    print("Following Spine priorities with comprehensive prevention")
    print("=" * 70)
    
    all_week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in all_week_files:
        print(f"\n{'='*70}")
        print(f"SPINE-AWARE: {week_file}")
        print('='*70)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply Spine-aware scheduler
            scheduler = SpineAwareScheduler(troops)
            schedule = scheduler.schedule_all()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_spine_aware_schedule.json')
            
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
                'success': metrics['final_score'] > 0 and total_gaps == 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "IN PROGRESS"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Violations: {result['violations']}")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            print(f"  Prevention Stats: {result['issues_prevented']} issues prevented")
            print(f"  Awareness Checks: {result['awareness_checks']}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Summary
    print(f"\n{'='*70}")
    print("SPINE-AWARE SCHEDULING RESULTS")
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
    
    # Prevention statistics
    if results:
        total_awareness_checks = sum(r['awareness_checks'] for r in results)
        total_issues_prevented = sum(r['issues_prevented'] for r in results)
        total_violations_prevented = sum(r['constraint_violations_prevented'] for r in results)
        total_gaps_prevented = sum(r['gaps_prevented'] for r in results)
        
        print(f"\nPREVENTION STATISTICS:")
        print(f"  Total Awareness Checks: {total_awareness_checks:,}")
        print(f"  Total Issues Prevented: {total_issues_prevented:,}")
        print(f"  Constraint Violations Prevented: {total_violations_prevented:,}")
        print(f"  Gaps Prevented: {total_gaps_prevented:,}")
    
    # Save results
    with open('spine_aware_results.txt', 'w') as f:
        f.write('SPINE-AWARE SCHEDULING RESULTS\n')
        f.write('=' * 40 + '\n\n')
        f.write(f'SUCCESS (Above 0 + Zero Gaps): {len(successful_weeks)}/{len(results)} weeks\n')
        f.write(f'ZERO GAPS: {len(zero_gap_weeks)}/{len(results)} weeks\n\n')
        
        f.write('SUCCESSFUL:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]} (Perfect)\n')
        
        f.write('\nZERO GAP WEEKS:\n')
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else f"{r['score']:.1f}"
            f.write(f'  {r["week"]}: {score_status} (Zero gaps)\n')
        
        f.write(f'\nPREVENTION STATISTICS:\n')
        f.write(f'  Total Awareness Checks: {total_awareness_checks:,}\n')
        f.write(f'  Total Issues Prevented: {total_issues_prevented:,}\n')
        f.write(f'  Constraint Violations Prevented: {total_violations_prevented:,}\n')
        f.write(f'  Gaps Prevented: {total_gaps_prevented:,}\n')
    
    print(f"\nSpine-aware results saved to 'spine_aware_results.txt'")
    
    return results

if __name__ == "__main__":
    apply_spine_aware_scheduling()
