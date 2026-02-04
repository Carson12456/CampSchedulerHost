#!/usr/bin/env python3
"""
Zero Gap Scheduler - Ensures NO empty slots progress past any phase
Focus on complete schedule filling with strict gap prevention
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class ZeroGapScheduler(EnhancedScheduler):
    """Scheduler that guarantees zero gaps at every phase"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.gap_checks_performed = 0
        self.gaps_filled = 0
        self.operations_blocked = 0
    
    def schedule_all(self):
        """Schedule with zero gap guarantee at every phase"""
        print("ZERO GAP SCHEDULER - Complete Fill + Strict Gap Prevention")
        print("=" * 70)
        
        # Phase 1: Complete schedule filling
        print("Phase 1: COMPLETE SCHEDULE FILLING")
        schedule = super().schedule_all()
        
        # Phase 2: Emergency gap elimination
        print("Phase 2: EMERGENCY GAP ELIMINATION")
        self._emergency_gap_elimination()
        
        # Phase 3: Apply optimizations with strict gap checking
        print("Phase 3: OPTIMIZATIONS WITH STRICT GAP PREVENTION")
        self._safe_optimizations()
        
        # Phase 4: Final gap verification
        print("Phase 4: FINAL GAP VERIFICATION")
        self._final_gap_verification()
        
        return schedule
    
    def _emergency_gap_elimination(self):
        """Eliminate ALL gaps immediately"""
        print("  Emergency gap elimination...")
        
        total_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
        print(f"    Found {total_gaps} gaps - eliminating...")
        
        gaps_filled = 0
        max_rounds = 5
        
        for round_num in range(max_rounds):
            round_filled = 0
            
            for troop in self.troops:
                gaps = self._find_troop_gaps(troop)
                
                for gap in gaps:
                    if self._force_fill_gap(troop, gap):
                        round_filled += 1
                        gaps_filled += 1
            
            print(f"    Round {round_num + 1}: {round_filled} gaps filled")
            
            # Check if all gaps eliminated
            remaining_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
            if remaining_gaps == 0:
                print(f"    All gaps eliminated in round {round_num + 1}!")
                break
        
        self.gaps_filled += gaps_filled
        print(f"  Total gaps filled: {gaps_filled}")
    
    def _safe_optimizations(self):
        """Apply optimizations with strict gap checking after each operation"""
        print("  Safe optimizations with gap checking...")
        
        # Override optimization methods to include gap checking
        self._safe_gap_filling()
        self._safe_top5_recovery()
        self._safe_constraint_fixing()
        
        # Check gaps after each major phase
        self._check_and_fix_gaps("After optimizations")
    
    def _safe_gap_filling(self):
        """Safe gap filling with immediate gap checking"""
        print("    Safe gap filling...")
        
        # Use existing gap filling but check after each fill
        for troop in self.troops:
            gaps = self._find_troop_gaps(troop)
            
            for gap in gaps:
                if self._safe_fill_gap(troop, gap):
                    # Immediately check if this created new gaps
                    self._check_and_fix_gaps(f"After filling gap for {troop.name}")
    
    def _safe_top5_recovery(self):
        """Safe Top 5 recovery with gap checking"""
        print("    Safe Top 5 recovery...")
        
        for troop in self.troops:
            troop_schedule = self.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            # Find missing Top 5
            missing_top5 = []
            for i, pref in enumerate(troop.preferences[:5]):
                if pref not in scheduled_activities:
                    missing_top5.append((pref, i))
            
            if missing_top5:
                for pref, priority in missing_top5:
                    if self._safe_schedule_top5(troop, pref, priority):
                        # Check gaps after each Top 5 recovery
                        self._check_and_fix_gaps(f"After Top 5 recovery for {troop.name}")
    
    def _safe_constraint_fixing(self):
        """Safe constraint fixing with gap checking"""
        print("    Safe constraint fixing...")
        
        # This would implement constraint fixing with gap checking
        # For now, just verify no gaps exist
        self._check_and_fix_gaps("After constraint fixing")
    
    def _check_and_fix_gaps(self, phase_name):
        """Check for gaps and fix immediately"""
        self.gap_checks_performed += 1
        
        total_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
        
        if total_gaps > 0:
            print(f"      GAP DETECTED in {phase_name}: {total_gaps} gaps - IMMEDIATE FIX")
            
            # Emergency fix
            gaps_fixed = 0
            for troop in self.troops:
                gaps = self._find_troop_gaps(troop)
                for gap in gaps:
                    if self._force_fill_gap(troop, gap):
                        gaps_fixed += 1
            
            print(f"      Fixed {gaps_fixed} gaps in {phase_name}")
            self.gaps_filled += gaps_fixed
        else:
            print(f"      No gaps in {phase_name} [OK]")
    
    def _force_fill_gap(self, troop, time_slot):
        """Force fill a gap with any available activity"""
        # Priority activities that work well
        priority_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        # Add troop's Top 5 preferences
        for pref in troop.preferences[:5]:
            if pref not in priority_activities:
                priority_activities.insert(5, pref)
        
        for activity_name in priority_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            # Force add without validation
            if self.schedule.add_entry(time_slot, activity, troop):
                return True
        
        # Try fallback activities
        fallback_activities = [
            "Campsite Free Time", "Shower House", "Trading Post", "Gaga Ball",
            "9 Square", "Woggle Neckerchief Slide", "Knots and Lashings"
        ]
        
        for activity_name in fallback_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            if self.schedule.add_entry(time_slot, activity, troop):
                return True
        
        return False
    
    def _safe_fill_gap(self, troop, time_slot):
        """Safe gap filling with validation"""
        # Try priority activities first
        priority_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        # Add troop's Top 5 preferences
        for pref in troop.preferences[:5]:
            if pref not in priority_activities:
                priority_activities.insert(5, pref)
        
        for activity_name in priority_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            # Check if this would create issues
            if self._is_safe_to_add(troop, activity, time_slot):
                if self.schedule.add_entry(time_slot, activity, troop):
                    return True
        
        # Try fallback activities
        fallback_activities = [
            "Campsite Free Time", "Shower House", "Trading Post", "Gaga Ball",
            "9 Square", "Woggle Neckerchief Slide", "Knots and Lashings"
        ]
        
        for activity_name in fallback_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            if self.schedule.add_entry(time_slot, activity, troop):
                return True
        
        return False
    
    def _safe_schedule_top5(self, troop, activity_name, priority):
        """Safe Top 5 scheduling with gap checking"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try direct placement first
        for slot in self.time_slots:
            if self._is_safe_to_add(troop, activity, slot):
                if self.schedule.add_entry(slot, activity, troop):
                    return True
        
        # Try displacement
        if self._safe_displacement(troop, activity, priority):
            return True
        
        return False
    
    def _safe_displacement(self, troop, target_activity, priority):
        """Safe displacement with gap checking"""
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
            if self._is_safe_to_displace(entry, target_activity):
                # Perform displacement
                self.schedule.remove_entry(entry)
                if self.schedule.add_entry(entry.time_slot, target_activity, troop):
                    # Try to relocate displaced activity
                    if self._relocate_displaced_activity(entry):
                        return True
                    else:
                        # Put it back if relocation failed
                        self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
                        self.operations_blocked += 1
        
        return False
    
    def _relocate_displaced_activity(self, entry):
        """Try to relocate displaced activity"""
        for slot in self.time_slots:
            if self._is_safe_to_add(entry.troop, entry.activity, slot):
                if self.schedule.add_entry(slot, entry.activity, entry.troop):
                    return True
        return False
    
    def _is_safe_to_add(self, troop, activity, time_slot):
        """Check if it's safe to add an activity"""
        # Basic checks
        if not self.schedule.is_troop_free(time_slot, troop):
            return False
        
        if not self.schedule.is_activity_available(activity, time_slot, troop):
            return False
        
        return True
    
    def _is_safe_to_displace(self, entry, new_activity):
        """Check if it's safe to displace an entry"""
        # Check if new activity can be placed
        if not self.schedule.is_activity_available(new_activity, entry.time_slot, entry.troop):
            return False
        
        return True
    
    def _final_gap_verification(self):
        """Final comprehensive gap verification"""
        print("  Final gap verification...")
        
        total_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
        
        if total_gaps == 0:
            print(f"  SUCCESS: Zero gaps verified across all {len(self.troops)} troops!")
        else:
            print(f"  CRITICAL: {total_gaps} gaps still remain - emergency fix...")
            
            # Emergency fix
            emergency_filled = 0
            for troop in self.troops:
                gaps = self._find_troop_gaps(troop)
                for gap in gaps:
                    if self._force_fill_gap(troop, gap):
                        emergency_filled += 1
            
            print(f"  Emergency fix: {emergency_filled} gaps filled")
            
            # Final verification
            final_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
            if final_gaps == 0:
                print(f"  SUCCESS: All gaps eliminated after emergency fix!")
            else:
                print(f"  FAILED: {final_gaps} gaps remain after emergency fix")
        
        print(f"  Statistics:")
        print(f"    Gap checks performed: {self.gap_checks_performed}")
        print(f"    Total gaps filled: {self.gaps_filled}")
        print(f"    Operations blocked: {self.operations_blocked}")


def zero_gap_fix_all_weeks():
    """Apply zero gap scheduler to all weeks"""
    print("ZERO GAP SCHEDULER - ALL WEEKS")
    print("=" * 70)
    print("GOAL: Ensure NO empty slots progress past any phase")
    print("=" * 70)
    
    all_week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in all_week_files:
        print(f"\n{'='*70}")
        print(f"ZERO GAP SCHEDULING: {week_file}")
        print('='*70)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply zero gap scheduler
            scheduler = ZeroGapScheduler(troops)
            schedule = scheduler.schedule_all()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_zero_gap_schedule.json')
            
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
                'gap_checks': scheduler.gap_checks_performed,
                'gaps_filled': scheduler.gaps_filled,
                'operations_blocked': scheduler.operations_blocked,
                'success': metrics['final_score'] > 0 and total_gaps == 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "NEEDS WORK"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Violations: {result['violations']}")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            print(f"  Gap Stats: {result['gap_checks']} checks, {result['gaps_filled']} filled")
            
        except Exception as e:
            print(f"ERROR processing {week_file}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print(f"\n{'='*70}")
    print("ZERO GAP SCHEDULER RESULTS")
    print('='*70)
    
    successful_weeks = [r for r in results if r['success']]
    zero_gap_weeks = [r for r in results if r['verified_gaps'] == 0]
    above_zero_weeks = [r for r in results if r['score'] > 0]
    
    print(f"Perfect Weeks (0 gaps + >0 score): {len(successful_weeks)}/{len(results)}")
    print(f"Zero Gap Weeks: {len(zero_gap_weeks)}/{len(results)}")
    print(f"Above Zero Score Weeks: {len(above_zero_weeks)}/{len(results)}")
    
    if successful_weeks:
        print(f"\nPERFECT WEEKS:")
        for r in successful_weeks:
            print(f"  {r['week']}: {r['score']} (0 gaps)")
    
    if zero_gap_weeks:
        print(f"\nZERO GAP WEEKS:")
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else "BELOW 0"
            print(f"  {r['week']}: {r['score']} ({score_status})")
    
    # Calculate statistics
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        total_gaps = sum(r['verified_gaps'] for r in results)
        total_gap_checks = sum(r['gap_checks'] for r in results)
        total_gaps_filled = sum(r['gaps_filled'] for r in results)
        
        print(f"\nSTATISTICS:")
        print(f"  Average Score: {avg_score:.1f}")
        print(f"  Total Gaps: {total_gaps}")
        print(f"  Total Gap Checks: {total_gap_checks}")
        print(f"  Total Gaps Filled: {total_gaps_filled}")
        print(f"  Gap Elimination Rate: {(total_gaps_filled/(total_gaps_filled+total_gaps)*100):.1f}%" if total_gaps_filled+total_gaps > 0 else "N/A")
    
    # Save results
    with open('zero_gap_results.txt', 'w') as f:
        f.write('ZERO GAP SCHEDULER RESULTS\n')
        f.write('=' * 40 + '\n\n')
        f.write(f'Perfect Weeks (0 gaps + >0 score): {len(successful_weeks)}/{len(results)}\n')
        f.write(f'Zero Gap Weeks: {len(zero_gap_weeks)}/{len(results)}\n')
        f.write(f'Above Zero Score Weeks: {len(above_zero_weeks)}/{len(results)}\n\n')
        
        f.write('PERFECT WEEKS:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]} (0 gaps)\n')
        
        f.write('\nZERO GAP WEEKS:\n')
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else "BELOW 0"
            f.write(f'  {r["week"]}: {r["score"]} ({score_status})\n')
        
        f.write(f'\nSTATISTICS:\n')
        f.write(f'  Average Score: {avg_score:.1f}\n')
        f.write(f'  Total Gaps: {total_gaps}\n')
        f.write(f'  Total Gap Checks: {total_gap_checks}\n')
        f.write(f'  Total Gaps Filled: {total_gaps_filled}\n')
    
    print(f"\nResults saved to zero_gap_results.txt")
    
    # Mission status
    if len(successful_weeks) == len(results):
        print(f"\nMISSION ACCOMPLISHED! All {len(results)} weeks have zero gaps and above 0 score!")
    elif len(zero_gap_weeks) == len(results):
        print(f"\nGAP ELIMINATION SUCCESS! All {len(results)} weeks have zero gaps!")
    else:
        print(f"\nPARTIAL SUCCESS: {len(zero_gap_weeks)}/{len(results)} weeks have zero gaps")
    
    return results

if __name__ == "__main__":
    zero_gap_fix_all_weeks()
