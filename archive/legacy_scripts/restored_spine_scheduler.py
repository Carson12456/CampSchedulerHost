#!/usr/bin/env python3
"""
Restored Spine Scheduler - Back to Basics with Helpful Components Only
Restores what was working and adds only the beneficial Spine components
"""

from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class RestoredSpineScheduler(ConstrainedScheduler):
    """Restored scheduler with baseline performance + only helpful Spine components"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        
        # ONLY HELPFUL COMPONENTS - No complex interference
        self.spine_analytics = {
            'top5_recovered': 0,
            'gaps_filled': 0,
            'constraint_fixes': 0,
            'total_actions': 0
        }
        
        # Simple Top 5 priority tracking
        self.top5_priority_troops = set()
        
    def schedule_all(self):
        """Restored scheduling with baseline performance + helpful enhancements"""
        print("=== RESTORED SPINE SCHEDULER ===")
        print("Baseline performance + helpful components only")
        print("=" * 50)
        
        # Use the working baseline scheduler
        schedule = super().schedule_all()
        
        # ONLY HELPFUL ENHANCEMENTS
        self._apply_helpful_enhancements()
        
        # Report results
        self._report_results()
        
        return schedule
    
    def _apply_helpful_enhancements(self):
        """Apply only the helpful enhancements that don't interfere"""
        print("\n--- Applying Helpful Enhancements ---")
        
        # 1. Top 5 Recovery (simple version)
        self._simple_top5_recovery()
        
        # 2. Gap Filling (simple version)
        self._simple_gap_fill()
        
        # 3. Basic constraint fixing
        self._simple_constraint_fixes()
    
    def _simple_top5_recovery(self):
        """Simple Top 5 recovery without complex interference"""
        recovered = 0
        
        for troop in self.troops:
            top5_prefs = troop.preferences[:5]
            for activity_name in top5_prefs:
                activity = get_activity_by_name(activity_name)
                if activity and not self._troop_has_activity(troop, activity):
                    # Try to place Top 5 preference
                    for time_slot in self.time_slots:
                        if self._can_schedule(troop, activity, time_slot, time_slot.day):
                            if self.schedule.add_entry(time_slot, activity, troop):
                                recovered += 1
                                break
        
        self.spine_analytics['top5_recovered'] = recovered
        print(f"  Top 5 Recovery: {recovered} activities placed")
    
    def _simple_gap_fill(self):
        """Simple gap filling without complex interference"""
        gaps_filled = 0
        
        for troop in self.troops:
            for time_slot in self.time_slots:
                if self.schedule.is_troop_free(time_slot, troop):
                    # Check if this is actually a gap
                    has_activity = any(e.troop == troop and e.time_slot == time_slot for e in self.schedule.entries)
                    if not has_activity:
                        # Fill with any available activity
                        for activity_name in troop.preferences:
                            activity = get_activity_by_name(activity_name)
                            if activity and not self._troop_has_activity(troop, activity):
                                if self._can_schedule(troop, activity, time_slot, time_slot.day):
                                    if self.schedule.add_entry(time_slot, activity, troop):
                                        gaps_filled += 1
                                        break
        
        self.spine_analytics['gaps_filled'] = gaps_filled
        print(f"  Gap Fill: {gaps_filled} gaps filled")
    
    def _simple_constraint_fixes(self):
        """Simple constraint fixes without complex interference"""
        fixes = 0
        
        # Fix basic beach slot violations
        beach_activities = ["Canoe Snorkel", "Sailing", "Float for Floats", "Aqua Trampoline"]
        for entry in self.schedule.entries[:]:  # Copy to avoid modification during iteration
            if entry.activity.name in beach_activities and entry.time_slot.slot_number == 2:
                # Try to move to a different slot
                for alt_slot in self.time_slots:
                    if alt_slot.slot_number != 2 and alt_slot.day == entry.time_slot.day:
                        if self._can_schedule(entry.troop, entry.activity, alt_slot, alt_slot.day):
                            self.schedule.entries.remove(entry)
                            self.schedule.add_entry(alt_slot, entry.activity, entry.troop)
                            fixes += 1
                            break
        
        self.spine_analytics['constraint_fixes'] = fixes
        print(f"  Constraint Fixes: {fixes} violations fixed")
    
    def _report_results(self):
        """Report results with simple metrics"""
        total_actions = sum(self.spine_analytics.values())
        print(f"\n--- Restored Spine Results ---")
        print(f"  Top 5 Recovered: {self.spine_analytics['top5_recovered']}")
        print(f"  Gaps Filled: {self.spine_analytics['gaps_filled']}")
        print(f"  Constraint Fixes: {self.spine_analytics['constraint_fixes']}")
        print(f"  Total Actions: {total_actions}")
    
    def _calculate_simple_metrics(self):
        """Calculate simple performance metrics"""
        # Top 5 satisfaction
        total_troops = len(self.troops)
        satisfied_troops = 0
        
        for troop in self.troops:
            top5_prefs = troop.preferences[:5]
            satisfied_count = 0
            for activity_name in top5_prefs:
                activity = get_activity_by_name(activity_name)
                if activity and self._troop_has_activity(troop, activity):
                    satisfied_count += 1
            
            if satisfied_count == len(top5_prefs):
                satisfied_troops += 1
        
        top5_satisfaction = (satisfied_troops / total_troops * 100) if total_troops > 0 else 0
        
        # Empty slots
        empty_slots = self._comprehensive_gap_check("Metrics")
        
        return {
            'top5_satisfaction': top5_satisfaction,
            'empty_slots': empty_slots,
            'total_troops': total_troops
        }


def apply_restored_spine_scheduling():
    """Apply Restored Spine scheduling to all weeks"""
    print("RESTORED SPINE SCHEDULING - BACK TO BASICS")
    print("=" * 70)
    print("Baseline performance + helpful components only")
    print("=" * 70)
    
    all_week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in all_week_files:
        print(f"\n{'='*70}")
        print(f"RESTORED SPINE: {week_file}")
        print('='*70)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply Restored Spine scheduler
            scheduler = RestoredSpineScheduler(troops)
            schedule = scheduler.schedule_all()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_restored_spine_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            # Calculate simple metrics
            simple_metrics = scheduler._calculate_simple_metrics()
            
            # Verify gaps
            total_gaps = scheduler._comprehensive_gap_check("Final Verification")
            
            result = {
                'week': week_name,
                'score': metrics.get('score', 0),
                'gaps': total_gaps,
                'success': total_gaps == 0,
                'top5_satisfaction': simple_metrics['top5_satisfaction'],
                'spine_analytics': scheduler.spine_analytics
            }
            results.append(result)
            
            print(f"  Result: {result['score']} points, {result['gaps']} gaps")
            print(f"  Top 5 Satisfaction: {result['top5_satisfaction']:.1f}%")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({'week': week_file, 'error': str(e)})
    
    # Summary
    print(f"\n{'='*70}")
    print("RESTORED SPINE SCHEDULING SUMMARY")
    print('='*70)
    
    successful = [r for r in results if r.get('success', False)]
    print(f"SUCCESS (Zero Gaps): {len(successful)}/{len(results)} weeks")
    
    if successful:
        print(f"\nSUCCESSFUL WEEKS:")
        for result in successful:
            print(f"  {result['week']}: {result['score']} points (Zero gaps)")
    
    # Average metrics
    if results:
        avg_top5 = sum(r.get('top5_satisfaction', 0) for r in results) / len(results)
        print(f"\nAVERAGE TOP 5 SATISFACTION: {avg_top5:.1f}%")
    
    return results


if __name__ == "__main__":
    apply_restored_spine_scheduling()
