#!/usr/bin/env python3
"""
Final Comprehensive Push - Get All Weeks in Good Spot
Apply best strategies from all developed systems for optimal results
"""

from enhanced_scheduler import EnhancedScheduler
from ultimate_gap_eliminator import UltimateGapEliminator
from specialized_constraint_fixer import SpecializedConstraintFixer
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class FinalComprehensiveScheduler(EnhancedScheduler):
    """Final comprehensive scheduler combining best strategies"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.gaps_filled = 0
        self.violations_fixed = 0
        self.top5_recovered = 0
        self.optimizations_applied = 0
    
    def comprehensive_optimize(self):
        """Comprehensive optimization using best strategies"""
        print(f"FINAL COMPREHENSIVE OPTIMIZATION")
        print("=" * 50)
        
        # Phase 1: Generate solid base schedule
        print("Phase 1: Generating solid base schedule...")
        schedule = super().schedule_all()
        
        # Phase 2: Ultimate gap elimination
        print("Phase 2: Ultimate gap elimination...")
        self._ultimate_gap_elimination()
        
        # Phase 3: Smart constraint fixing
        print("Phase 3: Smart constraint fixing...")
        self._smart_constraint_fixing()
        
        # Phase 4: Aggressive Top 5 recovery
        print("Phase 4: Aggressive Top 5 recovery...")
        self._aggressive_top5_recovery()
        
        # Phase 5: Final optimization pass
        print("Phase 5: Final optimization pass...")
        self._final_optimization_pass()
        
        return schedule
    
    def _ultimate_gap_elimination(self):
        """Ultimate gap elimination strategy"""
        gaps_filled = 0
        
        for troop in self.troops:
            gaps = self._find_troop_gaps(troop)
            
            for gap in gaps:
                if self._fill_gap_with_best_strategy(troop, gap):
                    gaps_filled += 1
        
        self.gaps_filled += gaps_filled
        print(f"  Gaps filled: {gaps_filled}")
    
    def _fill_gap_with_best_strategy(self, troop, time_slot):
        """Fill gap using best available strategy"""
        # Strategy 1: Try Top 5 preferences first
        for pref in troop.preferences[:5]:
            activity = get_activity_by_name(pref)
            if activity and self._safe_add_activity(troop, activity, time_slot):
                return True
        
        # Strategy 2: Try high-value activities
        high_value = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        for activity_name in high_value:
            activity = get_activity_by_name(activity_name)
            if activity and self._safe_add_activity(troop, activity, time_slot):
                return True
        
        # Strategy 3: Try any available activity
        all_activities = [
            "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Tie Dye",
            "Monkey's Fist", "Dr. DNA", "Loon Lore", "What's Cooking",
            "Campsite Free Time", "Shower House", "Trading Post", "Gaga Ball",
            "9 Square", "Woggle Neckerchief Slide", "Knots and Lashings"
        ]
        
        for activity_name in all_activities:
            activity = get_activity_by_name(activity_name)
            if activity and self._safe_add_activity(troop, activity, time_slot):
                return True
        
        # Strategy 4: Force add if necessary
        return self._force_fill_gap(troop, time_slot)
    
    def _safe_add_activity(self, troop, activity, time_slot):
        """Safely add activity with basic checks"""
        try:
            if self.schedule.is_troop_free(time_slot, troop):
                if self.schedule.is_activity_available(activity, time_slot, troop):
                    if self.schedule.add_entry(time_slot, activity, troop):
                        return True
        except:
            pass
        return False
    
    def _force_fill_gap(self, troop, time_slot):
        """Force fill gap as last resort"""
        basic_activities = ["Campsite Free Time", "Shower House", "Trading Post"]
        
        for activity_name in basic_activities:
            activity = get_activity_by_name(activity_name)
            if activity:
                try:
                    if self.schedule.add_entry(time_slot, activity, troop):
                        return True
                except:
                    continue
        
        return False
    
    def _smart_constraint_fixing(self):
        """Smart constraint fixing strategy"""
        violations_fixed = 0
        
        # Identify violations
        violations = self._identify_constraint_violations()
        
        for violation in violations:
            if self._fix_violation_smart(violation):
                violations_fixed += 1
        
        self.violations_fixed += violations_fixed
        print(f"  Violations fixed: {violations_fixed}")
    
    def _identify_constraint_violations(self):
        """Identify constraint violations"""
        violations = []
        
        # Beach slot violations
        beach_activities = ["Canoe Snorkel", "Sailing", "Float for Floats", "Aqua Trampoline"]
        for entry in self.schedule.entries:
            if entry.activity.name in beach_activities and entry.time_slot.slot_number == 2:
                violations.append({
                    'type': 'beach_slot',
                    'entry': entry,
                    'issue': f'{entry.activity.name} in slot 2 on {entry.time_slot.day}'
                })
        
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
                    for entry in area_activities[1:]:
                        violations.append({
                            'type': 'exclusive_area',
                            'entry': entry,
                            'issue': f'Multiple {area} activities in {slot}'
                        })
        
        return violations
    
    def _fix_violation_smart(self, violation):
        """Smart violation fixing"""
        entry = violation['entry']
        
        # Try to move to different slot
        for slot in self.time_slots:
            if slot != entry.time_slot:
                if self._safe_add_activity(entry.troop, entry.activity, slot):
                    self.schedule.remove_entry(entry)
                    if self.schedule.add_entry(slot, entry.activity, entry.troop):
                        return True
                    # Put it back
                    self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        # Try to swap with another activity
        return self._smart_swap_to_fix(entry)
    
    def _smart_swap_to_fix(self, entry):
        """Smart swap to fix violation"""
        troop_schedule = self.schedule.get_troop_schedule(entry.troop)
        
        for other_entry in troop_schedule:
            if other_entry == entry:
                continue
            
            # Try swap
            if self._safe_swap_entries(entry, other_entry):
                return True
        
        return False
    
    def _safe_swap_entries(self, entry1, entry2):
        """Safely swap two entries"""
        # Remove both
        self.schedule.remove_entry(entry1)
        self.schedule.remove_entry(entry2)
        
        # Try swap
        success1 = self.schedule.add_entry(entry2.time_slot, entry1.activity, entry1.troop)
        success2 = self.schedule.add_entry(entry1.time_slot, entry2.activity, entry2.troop)
        
        if success1 and success2:
            return True
        
        # Rollback
        self.schedule.add_entry(entry1.time_slot, entry1.activity, entry1.troop)
        self.schedule.add_entry(entry2.time_slot, entry2.activity, entry2.troop)
        return False
    
    def _aggressive_top5_recovery(self):
        """Aggressive Top 5 recovery"""
        recovered = 0
        
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
                    if self._aggressive_schedule_top5(troop, pref, priority):
                        recovered += 1
        
        self.top5_recovered += recovered
        print(f"  Top 5 recovered: {recovered}")
    
    def _aggressive_schedule_top5(self, troop, activity_name, priority):
        """Aggressive Top 5 scheduling"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try direct placement
        for slot in self.time_slots:
            if self._safe_add_activity(troop, activity, slot):
                return True
        
        # Try displacement
        return self._aggressive_displacement(troop, activity, priority)
    
    def _aggressive_displacement(self, troop, target_activity, priority):
        """Aggressive displacement for Top 5"""
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
            
            # Displace
            self.schedule.remove_entry(entry)
            if self.schedule.add_entry(entry.time_slot, target_activity, troop):
                return True
            # Put it back
            self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _final_optimization_pass(self):
        """Final optimization pass"""
        # Final gap check
        remaining_gaps = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
        if remaining_gaps > 0:
            print(f"  Final gap check: {remaining_gaps} gaps remaining")
            self._ultimate_gap_elimination()
        
        # Final Top 5 check
        for troop in self.troops:
            troop_schedule = self.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            missing_top5 = sum(1 for pref in troop.preferences[:5] if pref not in scheduled_activities)
            if missing_top5 > 0:
                print(f"  {troop.name}: {missing_top5} Top 5 still missing")
        
        self.optimizations_applied += 1
        print(f"  Final optimization complete")


def final_comprehensive_push():
    """Final comprehensive push for all weeks"""
    print("FINAL COMPREHENSIVE PUSH - GET ALL WEEKS IN GOOD SPOT")
    print("=" * 70)
    print("Applying best strategies from all developed systems")
    print("=" * 70)
    
    all_week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in all_week_files:
        print(f"\n{'='*70}")
        print(f"FINAL PUSH: {week_file}")
        print('='*70)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Get current status
            current_metrics = evaluate_week(week_file)
            print(f"Current: Score {current_metrics['final_score']}, Gaps {current_metrics['unnecessary_gaps']}")
            
            # Apply final comprehensive scheduler
            scheduler = FinalComprehensiveScheduler(troops)
            schedule = scheduler.comprehensive_optimize()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_final_comprehensive_schedule.json')
            
            # Evaluate results
            final_metrics = evaluate_week(week_file)
            
            # Verify gaps
            total_gaps = sum(len(scheduler._find_troop_gaps(troop)) for troop in troops)
            
            result = {
                'week': week_name,
                'initial_score': current_metrics['final_score'],
                'final_score': final_metrics['final_score'],
                'improvement': final_metrics['final_score'] - current_metrics['final_score'],
                'gaps': final_metrics['unnecessary_gaps'],
                'verified_gaps': total_gaps,
                'violations': final_metrics['constraint_violations'],
                'top5_missed': final_metrics['missing_top5'],
                'gaps_filled': scheduler.gaps_filled,
                'violations_fixed': scheduler.violations_fixed,
                'top5_recovered': scheduler.top5_recovered,
                'success': final_metrics['final_score'] > 0,
                'good_spot': final_metrics['final_score'] > -200  # Good spot definition
            }
            results.append(result)
            
            status = "EXCELLENT" if result['success'] else "GOOD" if result['good_spot'] else "NEEDS WORK"
            print(f"\n{status}: {week_name}")
            print(f"  Initial Score: {result['initial_score']:.1f}")
            print(f"  Final Score: {result['final_score']:.1f} ({result['improvement']:+.1f})")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Violations: {result['violations']}")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            print(f"  Actions: {result['gaps_filled']} gaps filled, {result['violations_fixed']} violations fixed, {result['top5_recovered']} Top5 recovered")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL COMPREHENSIVE PUSH RESULTS")
    print('='*70)
    
    excellent_weeks = [r for r in results if r['success']]
    good_weeks = [r for r in results if r['good_spot']]
    zero_gap_weeks = [r for r in results if r['verified_gaps'] == 0]
    
    print(f"EXCELLENT (Above 0): {len(excellent_weeks)}/{len(results)} weeks")
    print(f"GOOD SPOT (Above -200): {len(good_weeks)}/{len(results)} weeks")
    print(f"ZERO GAPS: {len(zero_gap_weeks)}/{len(results)} weeks")
    
    if excellent_weeks:
        print(f"\nEXCELLENT WEEKS:")
        for r in excellent_weeks:
            print(f"  {r['week']}: {r['final_score']:.1f} ({r['improvement']:+.1f})")
    
    if good_weeks:
        print(f"\nGOOD SPOT WEEKS:")
        for r in good_weeks:
            if not r['success']:  # Don't duplicate excellent weeks
                print(f"  {r['week']}: {r['final_score']:.1f} ({r['improvement']:+.1f})")
    
    # Calculate overall improvements
    if results:
        total_improvement = sum(r['improvement'] for r in results)
        total_gaps_filled = sum(r['gaps_filled'] for r in results)
        total_violations_fixed = sum(r['violations_fixed'] for r in results)
        total_top5_recovered = sum(r['top5_recovered'] for r in results)
        
        print(f"\nOVERALL IMPROVEMENTS:")
        print(f"  Total Score Improvement: {total_improvement:+.1f} points")
        print(f"  Total Gaps Filled: {total_gaps_filled}")
        print(f"  Total Violations Fixed: {total_violations_fixed}")
        print(f"  Total Top 5 Recovered: {total_top5_recovered}")
        
        avg_score = sum(r['final_score'] for r in results) / len(results)
        print(f"  Average Final Score: {avg_score:.1f}")
    
    # Save final results
    with open('final_comprehensive_results.txt', 'w') as f:
        f.write('FINAL COMPREHENSIVE PUSH RESULTS\n')
        f.write('=' * 40 + '\n\n')
        f.write(f'EXCELLENT (Above 0): {len(excellent_weeks)}/{len(results)} weeks\n')
        f.write(f'GOOD SPOT (Above -200): {len(good_weeks)}/{len(results)} weeks\n')
        f.write(f'ZERO GAPS: {len(zero_gap_weeks)}/{len(results)} weeks\n\n')
        
        f.write('EXCELLENT WEEKS:\n')
        for r in excellent_weeks:
            f.write(f'  {r["week"]}: {r["final_score"]:.1f} ({r["improvement"]:+.1f})\n')
        
        f.write('\nGOOD SPOT WEEKS:\n')
        for r in good_weeks:
            if not r['success']:
                f.write(f'  {r["week"]}: {r["final_score"]:.1f} ({r["improvement"]:+.1f})\n')
        
        f.write(f'\nOVERALL IMPROVEMENTS:\n')
        f.write(f'  Total Score Improvement: {total_improvement:+.1f} points\n')
        f.write(f'  Total Gaps Filled: {total_gaps_filled}\n')
        f.write(f'  Total Violations Fixed: {total_violations_fixed}\n')
        f.write(f'  Total Top 5 Recovered: {total_top5_recovered}\n')
        f.write(f'  Average Final Score: {avg_score:.1f}\n')
    
    print(f"\nFinal comprehensive results saved to 'final_comprehensive_results.txt'")
    
    return results

if __name__ == "__main__":
    final_comprehensive_push()
