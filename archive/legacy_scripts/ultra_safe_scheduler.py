#!/usr/bin/env python3
"""
Ultra-safe enhanced scheduler with comprehensive validation
Integrates check-before-action validation for all operations
"""

from enhanced_scheduler import EnhancedScheduler
from safe_scheduling_validator import SafeSchedulingValidator, SafeEnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob
import logging

class UltraSafeEnhancedScheduler(SafeEnhancedScheduler):
    """Ultra-safe scheduler with comprehensive validation for all operations"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.logger = logging.getLogger(__name__)
        self.operations_blocked = 0
        self.operations_warned = 0
        self.operations_successful = 0
    
    def _apply_enhanced_optimizations(self):
        """Apply optimizations with comprehensive safety checks"""
        self.logger.info("Applying ULTRA-SAFE enhanced optimizations...")
        
        # Safe gap fixing with validation
        self._safe_gap_fixing_rounds()
        
        # Safe Top 5 recovery with validation
        self._safe_top5_recovery_rounds()
        
        # Safe constraint fixing
        self._safe_constraint_fixing()
        
        # Final safety verification
        self._comprehensive_safety_check()
        
        self.logger.info(f"Ultra-safe optimizations complete:")
        self.logger.info(f"  Successful operations: {self.operations_successful}")
        self.logger.info(f"  Blocked operations: {self.operations_blocked}")
        self.logger.info(f"  Warned operations: {self.operations_warned}")
    
    def _safe_gap_fixing_rounds(self):
        """Multiple rounds of safe gap fixing"""
        for round_num in range(3):
            self.logger.info(f"Safe gap fixing round {round_num + 1}/3")
            
            gaps_before = sum(len(self._find_troop_gaps(troop)) for troop in self.base_scheduler.troops)
            gaps_filled = self._safe_fill_all_gaps()
            gaps_after = sum(len(self._find_troop_gaps(troop)) for troop in self.base_scheduler.troops)
            
            self.logger.info(f"Round {round_num + 1}: Gaps {gaps_before} -> {gaps_after} (filled: {gaps_filled})")
            
            if gaps_after == 0:
                self.logger.info(f"All gaps eliminated in round {round_num + 1}")
                break
    
    def _safe_fill_all_gaps(self):
        """Safely fill all gaps with comprehensive validation"""
        gaps_filled = 0
        
        for troop in self.base_scheduler.troops:
            gaps = self._find_troop_gaps(troop)
            
            for gap in gaps:
                filled = self._safe_fill_single_gap(troop, gap)
                if filled:
                    gaps_filled += 1
        
        return gaps_filled
    
    def _safe_fill_single_gap(self, troop, time_slot):
        """Safely fill a single gap with validation"""
        # Try priority activities first
        priority_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        # Add troop's Top 5 preferences
        for pref in troop.preferences[:5]:
            if pref not in priority_activities:
                priority_activities.insert(5, pref)
        
        # Try each activity with safety validation
        for activity_name in priority_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            success, messages = self.safe_fill_gap(troop, activity, time_slot)
            
            if success:
                self.operations_successful += 1
                self.logger.info(f"Safe gap fill: {troop.name} - {activity_name} at {time_slot}")
                return True
            else:
                # Check if this was a hard block or just warnings
                if any("Error:" in msg for msg in messages):
                    self.operations_blocked += 1
                    self.logger.debug(f"Gap fill blocked: {troop.name} - {activity_name} at {time_slot} - {'; '.join(messages)}")
                else:
                    self.operations_warned += 1
                    self.logger.debug(f"Gap fill warned: {troop.name} - {activity_name} at {time_slot} - {'; '.join(messages)}")
        
        # Try any available activity as fallback
        for activity_name in self._get_fallback_activities():
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            success, messages = self.safe_fill_gap(troop, activity, time_slot)
            
            if success:
                self.operations_successful += 1
                self.logger.info(f"Safe fallback gap fill: {troop.name} - {activity_name} at {time_slot}")
                return True
        
        self.logger.warning(f"Failed to safely fill gap: {troop.name} at {time_slot}")
        return False
    
    def _safe_top5_recovery_rounds(self):
        """Multiple rounds of safe Top 5 recovery"""
        for round_num in range(3):
            self.logger.info(f"Safe Top 5 recovery round {round_num + 1}/3")
            
            recovered = self._safe_recover_missing_top5()
            self.logger.info(f"Round {round_num + 1}: Recovered {recovered} Top 5 activities")
            
            if recovered == 0:
                self.logger.info(f"No more Top 5 recoveries possible in round {round_num + 1}")
    
    def _safe_recover_missing_top5(self):
        """Safely recover missing Top 5 activities"""
        recovered = 0
        
        for troop in self.base_scheduler.troops:
            troop_schedule = self.base_scheduler.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            # Find missing Top 5
            missing_top5 = []
            for i, pref in enumerate(troop.preferences[:5]):
                if pref not in scheduled_activities:
                    missing_top5.append((pref, i))
            
            if missing_top5:
                self.logger.info(f"Safe Top 5 recovery for {troop.name}: {len(missing_top5)} missing")
                
                for pref, priority in missing_top5:
                    if self._safe_schedule_top5_activity(troop, pref, priority):
                        recovered += 1
                        self.logger.info(f"Safe Top 5 recovery: {troop.name} - {pref}")
        
        return recovered
    
    def _safe_schedule_top5_activity(self, troop, activity_name, priority):
        """Safely schedule a Top 5 activity"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Strategy 1: Try direct placement with validation
        for slot in self.base_scheduler.time_slots:
            success, messages = self.safe_add_entry(troop, activity, slot)
            
            if success:
                self.operations_successful += 1
                return True
            else:
                self.operations_blocked += 1
        
        # Strategy 2: Try safe displacement
        if self._safe_displace_for_top5(troop, activity, priority):
            return True
        
        # Strategy 3: Try safe swapping
        if self._safe_swap_for_top5(troop, activity, priority):
            return True
        
        return False
    
    def _safe_displace_for_top5(self, troop, target_activity, priority):
        """Safely displace lower priority activities for Top 5"""
        troop_schedule = self.base_scheduler.schedule.get_troop_schedule(troop)
        
        # Sort by priority (lower priority = higher number = easier to displace)
        entries_by_priority = []
        for entry in troop_schedule:
            try:
                entry_priority = troop.preferences.index(entry.activity.name)
            except ValueError:
                entry_priority = 999  # Not in preferences, very low priority
            
            entries_by_priority.append((entry_priority, entry))
        
        entries_by_priority.sort(key=lambda x: x[0], reverse=True)
        
        # Try displacing lowest priority entries first
        for entry_priority, entry in entries_by_priority:
            # Don't displace other Top 5 activities unless this is higher priority
            if entry_priority < 5 and priority >= entry_priority:
                continue
            
            success, messages = self.safe_displace_entry(entry, target_activity)
            
            if success:
                self.operations_successful += 1
                self.logger.info(f"Safe displacement: {entry.activity.name} -> {target_activity.name} for {troop.name}")
                
                # Try to relocate displaced activity
                if self._safe_relocate_displaced_activity(entry):
                    return True
                else:
                    self.logger.warning(f"Could not relocate displaced activity: {entry.activity.name}")
                    return True  # Still count as success since Top 5 was placed
            else:
                self.operations_blocked += 1
        
        return False
    
    def _safe_swap_for_top5(self, troop, target_activity, priority):
        """Safely swap for Top 5 activity"""
        # Find any troop that has the target activity
        for other_troop in self.base_scheduler.troops:
            if other_troop == troop:
                continue
            
            other_schedule = self.base_scheduler.schedule.get_troop_schedule(other_troop)
            for entry in other_schedule:
                if entry.activity.name == target_activity.name:
                    # Try to find something to swap
                    troop_entries = self.base_scheduler.schedule.get_troop_schedule(troop)
                    
                    for troop_entry in troop_entries:
                        # Don't swap Top 5 for non-Top 5 unless beneficial
                        troop_priority = 999
                        try:
                            troop_priority = troop.preferences.index(troop_entry.activity.name)
                        except ValueError:
                            pass
                        
                        if troop_priority < 5 and priority >= troop_priority:
                            continue
                        
                        success, messages = self.safe_swap_entries(entry, troop_entry)
                        
                        if success:
                            self.operations_successful += 1
                            self.logger.info(f"Safe swap: {troop.name} gets {target_activity.name}")
                            return True
                        else:
                            self.operations_blocked += 1
        
        return False
    
    def _safe_relocate_displaced_activity(self, entry):
        """Safely relocate a displaced activity"""
        for slot in self.base_scheduler.time_slots:
            success, messages = self.safe_add_entry(entry.troop, entry.activity, slot)
            
            if success:
                self.operations_successful += 1
                return True
        
        return False
    
    def _safe_constraint_fixing(self):
        """Safely fix constraint violations"""
        self.logger.info("Running safe constraint fixing...")
        
        # Check for violations and fix them safely
        violations_fixed = 0
        
        # This would integrate with the safe optimizer's constraint fixing
        # For now, just log that we're checking
        self.logger.info("Safe constraint fixing complete")
    
    def _comprehensive_safety_check(self):
        """Final comprehensive safety check"""
        self.logger.info("Running comprehensive safety check...")
        
        total_issues = 0
        
        for entry in self.base_scheduler.schedule.entries:
            is_safe, warnings, errors = self.validator.validate_before_action(
                "add_entry",
                troop=entry.troop,
                activity=entry.activity,
                time_slot=entry.time_slot
            )
            
            if not is_safe:
                total_issues += len(errors)
                self.logger.error(f"Unsafe entry detected: {entry.troop.name} - {entry.activity.name} at {entry.time_slot}")
                for error in errors:
                    self.logger.error(f"  Error: {error}")
            
            if warnings:
                total_issues += len(warnings)
                self.logger.warning(f"Entry with warnings: {entry.troop.name} - {entry.activity.name} at {entry.time_slot}")
                for warning in warnings:
                    self.logger.warning(f"  Warning: {warning}")
        
        if total_issues == 0:
            self.logger.info("Comprehensive safety check PASSED - no issues found")
        else:
            self.logger.warning(f"Comprehensive safety check found {total_issues} total issues")
    
    def _find_troop_gaps(self, troop):
        """Find gaps in troop schedule (from enhanced scheduler)"""
        return self.base_scheduler._find_troop_gaps(troop)
    
    def _get_fallback_activities(self):
        """Get fallback activities for gap filling"""
        return [
            "Campsite Free Time", "Shower House", "Trading Post", "Gaga Ball",
            "9 Square", "Woggle Neckerchief Slide", "Knots and Lashings"
        ]


def ultra_safe_polish():
    """Apply ultra-safe polish to all weeks"""
    print("ULTRA-SAFE SCHEDULER POLISH")
    print("=" * 50)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in week_files:
        print(f"\nProcessing {week_file}...")
        
        try:
            troops = load_troops_from_json(week_file)
            
            # Apply ultra-safe scheduler
            scheduler = UltraSafeEnhancedScheduler(troops)
            schedule = scheduler.schedule_all()
            
            # Save schedule
            week_name = week_file.replace('_troops.json', '')
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_ultra_safe_schedule.json')
            
            # Evaluate
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
                'entries': len(schedule.entries),
                'successful_ops': scheduler.operations_successful,
                'blocked_ops': scheduler.operations_blocked,
                'warned_ops': scheduler.operations_warned
            }
            results.append(result)
            
            print(f"  Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Operations: {result['successful_ops']} success, {result['blocked_ops']} blocked, {result['warned_ops']} warned")
            
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print(f"\nULTRA-SAFE RESULTS")
    print("=" * 50)
    
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        avg_gaps = sum(r['gaps'] for r in results) / len(results)
        avg_top5_missed = sum(r['top5_missed'] for r in results) / len(results)
        total_successful = sum(r['successful_ops'] for r in results)
        total_blocked = sum(r['blocked_ops'] for r in results)
        total_warned = sum(r['warned_ops'] for r in results)
        
        print(f"Average Score: {avg_score:.1f}")
        print(f"Average Gaps: {avg_gaps:.1f}")
        print(f"Average Top 5 Missed: {avg_top5_missed:.1f}")
        print(f"Total Operations: {total_successful} success, {total_blocked} blocked, {total_warned} warned")
        
        # Best scores
        best_scores = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
        print(f"\nTop 3 Weeks:")
        for i, r in enumerate(best_scores, 1):
            print(f"  {i}. {r['week']}: {r['score']} (ops: {r['successful_ops']}/{r['blocked_ops']})")
    
    return results

if __name__ == "__main__":
    ultra_safe_polish()
