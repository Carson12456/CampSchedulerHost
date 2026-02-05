#!/usr/bin/env python3
"""
Final targeted fix - focus on getting remaining weeks above 0
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class FinalTargetedFixer:
    """Final targeted fixer for remaining struggling weeks"""
    
    def __init__(self, troops, week_name):
        self.week_name = week_name
        self.scheduler = EnhancedScheduler(troops)
        self.troops = troops
        self.operations = 0
    
    def targeted_fix(self):
        """Targeted fix to get above 0"""
        print(f"Targeted fixing {self.week_name}...")
        
        # Generate base schedule
        schedule = self.scheduler.schedule_all()
        
        # Get current metrics
        metrics = evaluate_week(self.week_name + '_troops.json')
        current_score = metrics['final_score']
        current_gaps = metrics['unnecessary_gaps']
        
        print(f"  Current: Score {current_score}, Gaps {current_gaps}")
        
        if current_score <= 0:
            # Calculate what we need
            needed_improvement = 1 - current_score
            print(f"  Need {needed_improvement} points improvement")
            
            # Focus on the biggest impact: eliminate gaps
            if current_gaps > 0:
                print(f"  Focusing on gap elimination (+{current_gaps * 1000} potential)...")
                gaps_eliminated = self._targeted_gap_elimination()
                print(f"    Eliminated {gaps_eliminated} gaps")
            
            # Additional Top 5 recovery
            print(f"  Additional Top 5 recovery...")
            top5_recovered = self._targeted_top5_recovery()
            print(f"    Recovered {top5_recovered} Top 5 activities")
        
        return schedule
    
    def _targeted_gap_elimination(self):
        """Targeted gap elimination"""
        gaps_eliminated = 0
        
        for troop in self.troops:
            gaps = self._find_troop_gaps(troop)
            
            for gap in gaps:
                if self._targeted_fill_gap(troop, gap):
                    gaps_eliminated += 1
        
        return gaps_eliminated
    
    def _targeted_top5_recovery(self):
        """Targeted Top 5 recovery"""
        recovered = 0
        
        for troop in self.troops:
            troop_schedule = self.scheduler.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            # Find missing Top 5
            missing_top5 = []
            for i, pref in enumerate(troop.preferences[:5]):
                if pref not in scheduled_activities:
                    missing_top5.append((pref, i))
            
            if missing_top5:
                for pref, priority in missing_top5:
                    if self._targeted_schedule_top5(troop, pref, priority):
                        recovered += 1
        
        return recovered
    
    def _targeted_fill_gap(self, troop, time_slot):
        """Targeted gap filling"""
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
            
            # Try to add
            if self.scheduler.schedule.add_entry(time_slot, activity, troop):
                self.operations += 1
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
            
            if self.scheduler.schedule.add_entry(time_slot, activity, troop):
                self.operations += 1
                return True
        
        return False
    
    def _targeted_schedule_top5(self, troop, activity_name, priority):
        """Targeted Top 5 scheduling"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try any slot
        for slot in self.scheduler.time_slots:
            if self.scheduler.schedule.add_entry(slot, activity, troop):
                self.operations += 1
                return True
        
        # Try displacement
        if self._targeted_displacement(troop, activity):
            return True
        
        return False
    
    def _targeted_displacement(self, troop, target_activity):
        """Targeted displacement"""
        troop_schedule = self.scheduler.schedule.get_troop_schedule(troop)
        
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
            if entry_priority < 5:
                continue
            
            # Displace
            self.scheduler.schedule.remove_entry(entry)
            if self.scheduler.schedule.add_entry(entry.time_slot, target_activity, troop):
                self.operations += 1
                return True
            # Put it back if failed
            self.scheduler.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _find_troop_gaps(self, troop):
        """Find gaps in troop schedule"""
        return self.scheduler._find_troop_gaps(troop)


def final_targeted_fix_all():
    """Final targeted fix for all remaining struggling weeks"""
    print("FINAL TARGETED FIX - GET ALL WEEKS ABOVE 0")
    print("=" * 60)
    
    # Focus on weeks that are still below 0
    struggling_files = [
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
    
    for week_file in struggling_files:
        print(f"\n{'='*60}")
        print(f"FINAL TARGETED FIX: {week_file}")
        print('='*60)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply targeted fix
            fixer = FinalTargetedFixer(troops, week_name)
            schedule = fixer.targeted_fix()
            
            # Save fixed schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_final_fixed_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            # Verify gaps
            total_gaps = sum(len(fixer._find_troop_gaps(troop)) for troop in troops)
            
            result = {
                'week': week_name,
                'score': metrics['final_score'],
                'gaps': metrics['unnecessary_gaps'],
                'verified_gaps': total_gaps,
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'operations': fixer.operations,
                'success': metrics['final_score'] > 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "STILL BELOW 0"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Violations: {result['violations']}")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            print(f"  Operations: {result['operations']}")
            
        except Exception as e:
            print(f"ERROR fixing {week_file}: {e}")
            continue
    
    # Final summary
    print(f"\n{'='*60}")
    print("FINAL TARGETED FIX RESULTS")
    print('='*60)
    
    successful_weeks = [r for r in results if r['success']]
    failed_weeks = [r for r in results if not r['success']]
    
    print(f"SUCCESSFULLY FIXED: {len(successful_weeks)}/{len(results)} weeks")
    print(f"STILL BELOW 0: {len(failed_weeks)} weeks")
    
    if successful_weeks:
        print(f"\nSUCCESSFUL WEEKS (Above 0):")
        for r in successful_weeks:
            print(f"  {r['week']}: {r['score']}")
    
    if failed_weeks:
        print(f"\nSTILL BELOW 0:")
        for r in failed_weeks:
            print(f"  {r['week']}: {r['score']} (G:{r['gaps']} V:{r['violations']} T5:{r['top5_missed']})")
    
    # Calculate overall statistics
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        total_gaps = sum(r['gaps'] for r in results)
        total_violations = sum(r['violations'] for r in results)
        total_top5_missed = sum(r['top5_missed'] for r in results)
        
        print(f"\nFINAL STATISTICS:")
        print(f"  Average Score: {avg_score:.1f}")
        print(f"  Total Gaps: {total_gaps}")
        print(f"  Total Violations: {total_violations}")
        print(f"  Total Top 5 Missed: {total_top5_missed}")
        print(f"  Success Rate: {len(successful_weeks)}/{len(results)} ({len(successful_weeks)/len(results)*100:.1f}%)")
    
    # Save final results
    with open('final_targeted_fix_results.txt', 'w') as f:
        f.write('FINAL TARGETED FIX RESULTS\n')
        f.write('=' * 40 + '\n\n')
        f.write(f'GOAL: Get ALL weeks above 0 score\n')
        f.write(f'SUCCESSFULLY FIXED: {len(successful_weeks)}/{len(results)} weeks\n\n')
        
        f.write('SUCCESSFUL (Above 0):\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]}\n')
        
        f.write('\nSTILL BELOW 0:\n')
        for r in failed_weeks:
            f.write(f'  {r["week"]}: {r["score"]} (G:{r["gaps"]} V:{r["violations"]} T5:{r["top5_missed"]})\n')
        
        f.write(f'\nFINAL STATISTICS:\n')
        f.write(f'  Average Score: {avg_score:.1f}\n')
        f.write(f'  Total Gaps: {total_gaps}\n')
        f.write(f'  Total Violations: {total_violations}\n')
        f.write(f'  Total Top 5 Missed: {total_top5_missed}\n')
        f.write(f'  Success Rate: {len(successful_weeks)}/{len(results)} ({len(successful_weeks)/len(results)*100:.1f}%)\n')
    
    print(f"\nFinal results saved to final_targeted_fix_results.txt")
    
    # Mission status
    if len(successful_weeks) == len(results):
        print(f"\nMISSION ACCOMPLISHED! All {len(results)} weeks are now above 0 score!")
    elif len(successful_weeks) > 0:
        print(f"\nPARTIAL SUCCESS: {len(successful_weeks)}/{len(results)} weeks above 0 score")
    else:
        print(f"\nCHALLENGE COMPLETE: Need different approach for remaining weeks")
    
    return results

if __name__ == "__main__":
    final_targeted_fix_all()
