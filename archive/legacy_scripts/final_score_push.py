#!/usr/bin/env python3
"""
Final Score Push - Get remaining weeks above 0
Direct approach with constraint violation fixing
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class FinalScorePusher(EnhancedScheduler):
    """Final score pusher to get above 0"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.violations_fixed = 0
        self.top5_recovered = 0
    
    def push_above_zero(self):
        """Push score above 0"""
        print("FINAL SCORE PUSH")
        print("=" * 40)
        
        # Generate base schedule
        schedule = super().schedule_all()
        
        # Get current metrics
        week_file = self._get_week_file()
        metrics = evaluate_week(week_file)
        
        current_score = metrics['final_score']
        current_violations = metrics['constraint_violations']
        current_top5_missed = metrics['missing_top5']
        
        print(f"Current: Score {current_score}")
        print(f"Violations: {current_violations} (-{current_violations * 25} points)")
        print(f"Top 5 Missed: {current_top5_missed} (-{current_top5_missed * 24} points)")
        
        if current_score <= 0:
            needed = 1 - current_score
            print(f"Need {needed} points to get above 0")
            
            # Focus on biggest impact: violations first
            if current_violations > 0:
                print(f"Fixing violations (+{current_violations * 25} potential)...")
                self._fix_violations()
            
            # Then Top 5 recovery
            if current_top5_missed > 0:
                print(f"Recovering Top 5 (+{current_top5_missed * 24} potential)...")
                self._recover_top5()
        
        return schedule
    
    def _get_week_file(self):
        """Get the week file name"""
        # Try to determine from troop names
        troop_name = self.troops[0].name.lower()
        
        if 'voyageur' in troop_name:
            if '1' in troop_name or 'one' in troop_name:
                return 'voyageur_week1_troops.json'
            elif '3' in troop_name or 'three' in troop_name:
                return 'voyageur_week3_troops.json'
        else:
            # TC weeks
            for i in range(1, 9):
                if str(i) in troop_name:
                    return f'tc_week{i}_troops.json'
        
        # Default to tc_week1
        return 'tc_week1_troops.json'
    
    def _fix_violations(self):
        """Fix constraint violations"""
        # Focus on beach slot violations first
        beach_violations = []
        
        for entry in self.schedule.entries:
            if entry.activity.name in ["Canoe Snorkel", "Sailing", "Float for Floats", "Aqua Trampoline"]:
                if entry.time_slot.slot_number == 2:
                    beach_violations.append(entry)
        
        print(f"  Found {len(beach_violations)} beach slot violations")
        
        for violation in beach_violations:
            if self._fix_beach_violation(violation):
                self.violations_fixed += 1
                print(f"    Fixed beach violation: {violation.activity.name} at {violation.time_slot}")
    
    def _fix_beach_violation(self, entry):
        """Fix a beach slot violation"""
        # Try to move to slot 1 or 3 on same day
        for slot_num in [1, 3]:
            for slot in self.time_slots:
                if (slot.day == entry.time_slot.day and 
                    slot.slot_number == slot_num and
                    self.schedule.is_troop_free(slot, entry.troop) and
                    self.schedule.is_activity_available(entry.activity, slot, entry.troop)):
                    
                    # Move the entry
                    self.schedule.remove_entry(entry)
                    if self.schedule.add_entry(slot, entry.activity, entry.troop):
                        return True
                    # Put it back if failed
                    self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _recover_top5(self):
        """Recover Top 5 activities"""
        for troop in self.troops:
            troop_schedule = self.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            # Find missing Top 5
            missing_top5 = []
            for i, pref in enumerate(troop.preferences[:5]):
                if pref not in scheduled_activities:
                    missing_top5.append((pref, i))
            
            if missing_top5:
                print(f"  {troop.name} missing {len(missing_top5)} Top 5 activities")
                
                for pref, priority in missing_top5:
                    if self._schedule_top5(troop, pref, priority):
                        self.top5_recovered += 1
                        print(f"    Recovered Top 5: {pref}")
    
    def _schedule_top5(self, troop, activity_name, priority):
        """Schedule a Top 5 activity"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try direct placement
        for slot in self.time_slots:
            if self.schedule.add_entry(slot, activity, troop):
                return True
        
        # Try displacement
        return self._displace_for_top5(troop, activity, priority)
    
    def _displace_for_top5(self, troop, target_activity, priority):
        """Displace for Top 5"""
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
            # Put it back if failed
            self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False


def final_push_all_weeks():
    """Final push for all weeks below 0"""
    print("FINAL SCORE PUSH - ALL WEEKS")
    print("=" * 60)
    
    # Weeks that need final push
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
        print(f"FINAL PUSH: {week_file}")
        print('='*60)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply final push
            pusher = FinalScorePusher(troops)
            schedule = pusher.push_above_zero()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_final_push_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            result = {
                'week': week_name,
                'score': metrics['final_score'],
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'violations_fixed': pusher.violations_fixed,
                'top5_recovered': pusher.top5_recovered,
                'success': metrics['final_score'] > 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "STILL BELOW 0"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Violations: {result['violations']} (fixed: {result['violations_fixed']})")
            print(f"  Top 5 Missed: {result['top5_missed']} (recovered: {result['top5_recovered']})")
            
            if result['violations_fixed'] > 0 or result['top5_recovered'] > 0:
                improvement = result['violations_fixed'] * 25 + result['top5_recovered'] * 24
                print(f"  Improvement: +{improvement} points")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print("FINAL PUSH RESULTS")
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
            improvement = r['violations_fixed'] * 25 + r['top5_recovered'] * 24
            print(f"  {r['week']}: +{improvement} points")
    
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
    with open('final_push_results.txt', 'w') as f:
        f.write('FINAL PUSH RESULTS\n')
        f.write('=' * 30 + '\n\n')
        f.write(f'Above 0 Score: {len(successful_weeks)}/{len(results)} weeks\n')
        f.write(f'Improved: {len(improved_weeks)}/{len(results)} weeks\n\n')
        
        f.write('SUCCESSFUL:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]}\n')
        
        f.write('\nIMPROVED:\n')
        for r in improved_weeks:
            improvement = r['violations_fixed'] * 25 + r['top5_recovered'] * 24
            f.write(f'  {r["week"]}: +{improvement} points\n')
    
    print(f"\nResults saved to final_push_results.txt")
    return results

if __name__ == "__main__":
    final_push_all_weeks()
