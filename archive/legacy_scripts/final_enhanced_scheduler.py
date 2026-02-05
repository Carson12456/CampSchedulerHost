#!/usr/bin/env python3
"""
Final enhanced scheduler with smart validation
Focus on practical improvements with check-before-action validation
"""

from enhanced_scheduler import EnhancedScheduler
from smart_safe_scheduler import SmartSchedulingValidator
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class FinalEnhancedScheduler(EnhancedScheduler):
    """Final enhanced scheduler with smart validation"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.validator = SmartSchedulingValidator(self.schedule, self.time_slots, troops)
        self.operations_safe = 0
        self.operations_blocked = 0
        self.operations_warned = 0
    
    def _apply_enhanced_optimizations(self):
        """Apply optimizations with smart validation"""
        print("Applying FINAL ENHANCED optimizations with validation...")
        
        # Enhanced gap fixing with validation
        self._validated_gap_fixing()
        
        # Enhanced Top 5 recovery with validation
        self._validated_top5_recovery()
        
        # Final verification
        self._final_validation()
        
        print(f"Final enhanced optimizations complete:")
        print(f"  Safe operations: {self.operations_safe}")
        print(f"  Blocked operations: {self.operations_blocked}")
        print(f"  Warned operations: {self.operations_warned}")
    
    def _validated_gap_fixing(self):
        """Enhanced gap fixing with validation"""
        print("Running validated gap fixing...")
        
        total_gaps_filled = 0
        max_iterations = 3
        
        for iteration in range(max_iterations):
            gaps_before = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
            
            if gaps_before == 0:
                print(f"  No gaps found in iteration {iteration + 1}")
                break
            
            iteration_filled = 0
            
            for troop in self.troops:
                gaps = self._find_troop_gaps(troop)
                
                for gap in gaps:
                    if self._validated_fill_gap(troop, gap):
                        iteration_filled += 1
                        total_gaps_filled += 1
            
            gaps_after = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
            
            print(f"  Iteration {iteration + 1}: {gaps_before} -> {gaps_after} gaps (filled: {iteration_filled})")
            
            if gaps_after == 0:
                print(f"  All gaps eliminated in iteration {iteration + 1}")
                break
        
        print(f"Total gaps filled: {total_gaps_filled}")
    
    def _validated_fill_gap(self, troop, time_slot):
        """Fill a gap with validation"""
        # Priority activities
        priority_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        # Add troop's Top 5 preferences
        for pref in troop.preferences[:5]:
            if pref not in priority_activities:
                priority_activities.insert(5, pref)
        
        # Try each activity with validation
        for activity_name in priority_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            success, messages = self._validated_add_entry(troop, activity, time_slot)
            
            if success:
                self.operations_safe += 1
                return True
            else:
                self.operations_blocked += 1
        
        # Try fallback activities
        fallback_activities = [
            "Campsite Free Time", "Shower House", "Trading Post", "Gaga Ball",
            "9 Square", "Woggle Neckerchief Slide", "Knots and Lashings"
        ]
        
        for activity_name in fallback_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            success, messages = self._validated_add_entry(troop, activity, time_slot)
            
            if success:
                self.operations_safe += 1
                return True
            else:
                self.operations_blocked += 1
        
        return False
    
    def _validated_top5_recovery(self):
        """Enhanced Top 5 recovery with validation"""
        print("Running validated Top 5 recovery...")
        
        total_recovered = 0
        max_rounds = 3
        
        for round_num in range(max_rounds):
            round_recovered = 0
            
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
                        if self._validated_schedule_top5(troop, pref, priority):
                            round_recovered += 1
                            total_recovered += 1
            
            print(f"  Round {round_num + 1}: Recovered {round_recovered} Top 5 activities")
            
            if round_recovered == 0:
                break
        
        print(f"Total Top 5 activities recovered: {total_recovered}")
    
    def _validated_schedule_top5(self, troop, activity_name, priority):
        """Schedule a Top 5 activity with validation"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try direct placement
        for slot in self.time_slots:
            success, messages = self._validated_add_entry(troop, activity, slot)
            
            if success:
                return True
        
        # Try displacement
        if self._validated_displacement(troop, activity, priority):
            return True
        
        return False
    
    def _validated_displacement(self, troop, target_activity, priority):
        """Displace lower priority activity with validation"""
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
        
        # Try displacing lowest priority entries
        for entry_priority, entry in entries_by_priority:
            # Don't displace other Top 5 unless this is higher priority
            if entry_priority < 5 and priority >= entry_priority:
                continue
            
            success, messages = self._validated_displace_entry(entry, target_activity)
            
            if success:
                self.operations_safe += 1
                return True
            else:
                self.operations_blocked += 1
        
        return False
    
    def _validated_add_entry(self, troop, activity, time_slot):
        """Add entry with validation"""
        is_safe, warnings, errors = self.validator.validate_action(
            "add_entry",
            troop=troop,
            activity=activity,
            time_slot=time_slot
        )
        
        if not is_safe:
            return False, errors
        
        if warnings:
            self.operations_warned += 1
        
        # Perform the action
        self.schedule.add_entry(time_slot, activity, troop)
        return True, warnings
    
    def _validated_displace_entry(self, existing_entry, new_activity):
        """Displace entry with validation"""
        is_safe, warnings, errors = self.validator.validate_action(
            "displace_entry",
            existing_entry=existing_entry,
            new_activity=new_activity
        )
        
        if not is_safe:
            return False, errors
        
        if warnings:
            self.operations_warned += 1
        
        # Perform the displacement
        self.schedule.remove_entry(existing_entry)
        self.schedule.add_entry(existing_entry.time_slot, new_activity, existing_entry.troop)
        return True, warnings
    
    def _final_validation(self):
        """Final validation check"""
        print("Running final validation...")
        
        total_issues = 0
        
        for entry in self.schedule.entries:
            is_safe, warnings, errors = self.validator.validate_action(
                "add_entry",
                troop=entry.troop,
                activity=entry.activity,
                time_slot=entry.time_slot
            )
            
            if not is_safe:
                total_issues += len(errors)
            if warnings:
                total_issues += len(warnings)
        
        if total_issues == 0:
            print("  Final validation PASSED - no issues found")
        else:
            print(f"  Final validation found {total_issues} total issues")


def final_enhanced_polish():
    """Apply final enhanced polish to all weeks"""
    print("FINAL ENHANCED SCHEDULER POLISH")
    print("=" * 50)
    
    week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in week_files:
        print(f"\nProcessing {week_file}...")
        
        try:
            troops = load_troops_from_json(week_file)
            
            # Apply final enhanced scheduler
            scheduler = FinalEnhancedScheduler(troops)
            schedule = scheduler.schedule_all()
            
            # Save schedule
            week_name = week_file.replace('_troops.json', '')
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_final_enhanced_schedule.json')
            
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
                'safe_ops': scheduler.operations_safe,
                'blocked_ops': scheduler.operations_blocked,
                'warned_ops': scheduler.operations_warned
            }
            results.append(result)
            
            print(f"  Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Operations: {result['safe_ops']} safe, {result['blocked_ops']} blocked")
            
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Summary
    print(f"\nFINAL ENHANCED RESULTS")
    print("=" * 50)
    
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        avg_gaps = sum(r['gaps'] for r in results) / len(results)
        avg_top5_missed = sum(r['top5_missed'] for r in results) / len(results)
        total_safe = sum(r['safe_ops'] for r in results)
        total_blocked = sum(r['blocked_ops'] for r in results)
        
        print(f"Average Score: {avg_score:.1f}")
        print(f"Average Gaps: {avg_gaps:.1f}")
        print(f"Average Top 5 Missed: {avg_top5_missed:.1f}")
        print(f"Total Operations: {total_safe} safe, {total_blocked} blocked")
        
        # Best scores
        best_scores = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
        print(f"\nTop 3 Weeks:")
        for i, r in enumerate(best_scores, 1):
            print(f"  {i}. {r['week']}: {r['score']} (ops: {r['safe_ops']}/{r['blocked_ops']})")
        
        # Improvement analysis
        zero_gap_weeks = sum(1 for r in results if r['verified_gaps'] == 0)
        zero_violation_weeks = sum(1 for r in results if r['violations'] == 0)
        zero_top5_missed = sum(1 for r in results if r['top5_missed'] == 0)
        
        print(f"\nPerfect Weeks:")
        print(f"  Zero Gaps: {zero_gap_weeks}/{len(results)}")
        print(f"  Zero Violations: {zero_violation_weeks}/{len(results)}")
        print(f"  Zero Top 5 Missed: {zero_top5_missed}/{len(results)}")
    
    return results

if __name__ == "__main__":
    final_enhanced_polish()
