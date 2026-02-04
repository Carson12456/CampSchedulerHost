#!/usr/bin/env python3
"""
Score Optimizer - Get all weeks above 0 score
Focus on constraint violations and Top 5 recovery
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class ScoreOptimizer(EnhancedScheduler):
    """Score optimizer focused on getting above 0 score"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.violations_fixed = 0
        self.top5_recovered = 0
        self.score_improvement = 0
    
    def optimize_to_above_zero(self):
        """Optimize schedule to get above 0 score"""
        print("SCORE OPTIMIZER - GET ABOVE 0")
        print("=" * 50)
        
        # Generate base schedule
        schedule = super().schedule_all()
        
        # Get current metrics
        metrics = evaluate_week(self.troops[0].name.replace(' Troop', '').replace(' ', '_').lower() + '_week' + 
                              (self.troops[0].name.split()[1] if len(self.troops[0].name.split()) > 1 else '1') + '_troops.json')
        
        current_score = metrics['final_score']
        current_violations = metrics['constraint_violations']
        current_top5_missed = metrics['missing_top5']
        
        print(f"Current: Score {current_score}, Violations {current_violations}, Top 5 Missed {current_top5_missed}")
        
        if current_score <= 0:
            needed_improvement = 1 - current_score
            print(f"Need {needed_improvement} points improvement")
            
            # Phase 1: Constraint violation fixing (25 points each)
            if current_violations > 0:
                print(f"Phase 1: Fix {current_violations} violations (+{current_violations * 25} potential)")
                violations_fixed = self._fix_constraint_violations()
                print(f"  Fixed {violations_fixed} violations")
            
            # Phase 2: Top 5 recovery (24 points each)
            print(f"Phase 2: Top 5 recovery (+{current_top5_missed * 24} potential)")
            top5_recovered = self._aggressive_top5_recovery()
            print(f"  Recovered {top5_recovered} Top 5 activities")
            
            # Phase 3: Score optimization
            print(f"Phase 3: Additional score optimization")
            additional_improvement = self._additional_score_optimization()
            print(f"  Additional improvement: {additional_improvement}")
        
        return schedule
    
    def _fix_constraint_violations(self):
        """Fix constraint violations"""
        violations_fixed = 0
        
        # Get current violations
        violations = self._identify_violations()
        
        for violation in violations:
            if self._fix_single_violation(violation):
                violations_fixed += 1
        
        return violations_fixed
    
    def _identify_violations(self):
        """Identify current constraint violations"""
        violations = []
        
        # Check beach slot violations
        for entry in self.schedule.entries:
            if entry.activity.name in ["Canoe Snorkel", "Sailing", "Float for Floats", "Aqua Trampoline"]:
                if entry.time_slot.slot_number == 2:  # Beach slot 2 is problematic
                    violations.append({
                        'type': 'beach_slot',
                        'entry': entry,
                        'issue': f'{entry.activity.name} in slot 2 on {entry.time_slot.day}'
                    })
        
        # Check exclusive area violations
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
                    for entry in area_activities[1:]:  # All but first
                        violations.append({
                            'type': 'exclusive_area',
                            'entry': entry,
                            'issue': f'Multiple {area} activities in {slot}'
                        })
        
        return violations
    
    def _fix_single_violation(self, violation):
        """Fix a single violation"""
        entry = violation['entry']
        
        if violation['type'] == 'beach_slot':
            return self._fix_beach_slot_violation(entry)
        elif violation['type'] == 'exclusive_area':
            return self._fix_exclusive_area_violation(entry, violation['issue'])
        
        return False
    
    def _fix_beach_slot_violation(self, entry):
        """Fix beach slot violation"""
        # Try to move to a different slot
        for slot in self.time_slots:
            if slot.day == entry.time_slot.day and slot.slot_number != 2:
                if self._safe_move_entry(entry, slot):
                    self.violations_fixed += 1
                    return True
        
        # Try to swap with another activity
        return self._swap_to_fix_violation(entry)
    
    def _fix_exclusive_area_violation(self, entry, issue):
        """Fix exclusive area violation"""
        # Try to move to a different time slot
        for slot in self.time_slots:
            if self._safe_move_entry(entry, slot):
                self.violations_fixed += 1
                return True
        
        return False
    
    def _safe_move_entry(self, entry, new_slot):
        """Safely move an entry to a new slot"""
        # Check if new slot is available
        if not self.schedule.is_troop_free(new_slot, entry.troop):
            return False
        
        if not self.schedule.is_activity_available(entry.activity, new_slot, entry.troop):
            return False
        
        # Move the entry
        self.schedule.remove_entry(entry)
        if self.schedule.add_entry(new_slot, entry.activity, entry.troop):
            return True
        
        # Put it back if failed
        self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        return False
    
    def _swap_to_fix_violation(self, entry):
        """Swap entry to fix violation"""
        troop_schedule = self.schedule.get_troop_schedule(entry.troop)
        
        for other_entry in troop_schedule:
            if other_entry == entry:
                continue
            
            # Try swapping
            if self._safe_swap_entries(entry, other_entry):
                self.violations_fixed += 1
                return True
        
        return False
    
    def _safe_swap_entries(self, entry1, entry2):
        """Safely swap two entries"""
        # Check if swap is possible
        if not self.schedule.is_activity_available(entry1.activity, entry2.time_slot, entry1.troop):
            return False
        
        if not self.schedule.is_activity_available(entry2.activity, entry1.time_slot, entry2.troop):
            return False
        
        # Perform swap
        self.schedule.remove_entry(entry1)
        self.schedule.remove_entry(entry2)
        
        success1 = self.schedule.add_entry(entry2.time_slot, entry1.activity, entry1.troop)
        success2 = self.schedule.add_entry(entry1.time_slot, entry2.activity, entry2.troop)
        
        if success1 and success2:
            return True
        
        # Rollback if failed
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
        
        return recovered
    
    def _aggressive_schedule_top5(self, troop, activity_name, priority):
        """Aggressive Top 5 scheduling"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try direct placement
        for slot in self.time_slots:
            if self.schedule.add_entry(slot, activity, troop):
                self.top5_recovered += 1
                return True
        
        # Try displacement
        if self._aggressive_displacement(troop, activity, priority):
            return True
        
        return False
    
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
                self.top5_recovered += 1
                return True
            # Put it back if failed
            self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _additional_score_optimization(self):
        """Additional score optimization"""
        improvement = 0
        
        # Try to optimize staff distribution
        # Try to improve clustering
        # Try to reduce excess days
        
        return improvement


def optimize_all_weeks_to_above_zero():
    """Optimize all weeks to get above 0 score"""
    print("SCORE OPTIMIZER - ALL WEEKS TO ABOVE 0")
    print("=" * 60)
    
    # Focus on weeks that are below 0 but have no gaps
    below_zero_files = [
        'tc_week1_troops.json',
        'tc_week3_troops.json', 
        'tc_week4_troops.json',
        'tc_week5_troops.json',
        'tc_week6_troops.json',
        'tc_week7_troops.json',
        'tc_week8_troops.json',
        'voyageur_week1_troops.json',
        'voyageur_week3_troops.json'
    ]
    
    results = []
    
    for week_file in below_zero_files:
        print(f"\n{'='*60}")
        print(f"SCORE OPTIMIZATION: {week_file}")
        print('='*60)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply score optimizer
            optimizer = ScoreOptimizer(troops)
            schedule = optimizer.optimize_to_above_zero()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_optimized_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            result = {
                'week': week_name,
                'score': metrics['final_score'],
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'violations_fixed': optimizer.violations_fixed,
                'top5_recovered': optimizer.top5_recovered,
                'success': metrics['final_score'] > 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "STILL BELOW 0"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Violations: {result['violations']} (fixed: {result['violations_fixed']})")
            print(f"  Top 5 Missed: {result['top5_missed']} (recovered: {result['top5_recovered']})")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print("SCORE OPTIMIZER RESULTS")
    print('='*60)
    
    successful_weeks = [r for r in results if r['success']]
    improved_weeks = [r for r in results if r['violations_fixed'] > 0 or r['top5_recovered'] > 0]
    
    print(f"Above 0 Score: {len(successful_weeks)}/{len(results)} weeks")
    print(f"Improved: {len(improved_weeks)}/{len(results)} weeks")
    
    if successful_weeks:
        print(f"\nSUCCESSFUL WEEKS:")
        for r in successful_weeks:
            print(f"  {r['week']}: {r['score']}")
    
    if improved_weeks:
        print(f"\nIMPROVED WEEKS:")
        for r in improved_weeks:
            print(f"  {r['week']}: +{r['violations_fixed']*25 + r['top5_recovered']*24} points")
    
    # Calculate statistics
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        total_violations_fixed = sum(r['violations_fixed'] for r in results)
        total_top5_recovered = sum(r['top5_recovered'] for r in results)
        total_improvement = total_violations_fixed * 25 + total_top5_recovered * 24
        
        print(f"\nSTATISTICS:")
        print(f"  Average Score: {avg_score:.1f}")
        print(f"  Total Violations Fixed: {total_violations_fixed}")
        print(f"  Total Top 5 Recovered: {total_top5_recovered}")
        print(f"  Total Score Improvement: +{total_improvement}")
    
    # Save results
    with open('score_optimizer_results.txt', 'w') as f:
        f.write('SCORE OPTIMIZER RESULTS\n')
        f.write('=' * 30 + '\n\n')
        f.write(f'Above 0 Score: {len(successful_weeks)}/{len(results)} weeks\n')
        f.write(f'Improved: {len(improved_weeks)}/{len(results)} weeks\n\n')
        
        f.write('SUCCESSFUL:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]}\n')
        
        f.write('\nIMPROVED:\n')
        for r in improved_weeks:
            f.write(f'  {r["week"]}: +{r["violations_fixed"]*25 + r["top5_recovered"]*24} points\n')
    
    print(f"\nResults saved to score_optimizer_results.txt")
    return results

if __name__ == "__main__":
    optimize_all_weeks_to_above_zero()
