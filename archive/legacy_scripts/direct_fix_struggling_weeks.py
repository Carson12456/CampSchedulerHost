#!/usr/bin/env python3
"""
Direct struggling weeks fix - bypass validation issues
Focus on core gap elimination and Top 5 recovery
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class DirectWeekFixer:
    """Direct week fixer without complex validation"""
    
    def __init__(self, troops, week_name):
        self.week_name = week_name
        self.scheduler = EnhancedScheduler(troops)
        self.troops = troops
        self.operations = 0
    
    def fix_week(self):
        """Apply direct fixes"""
        print(f"Direct fixing {self.week_name}...")
        
        # Generate base schedule first
        print("  Generating base schedule...")
        schedule = self.scheduler.schedule_all()
        
        # Apply direct fixes
        print("  Applying direct fixes...")
        
        # Phase 1: Direct gap elimination
        gaps_filled = self._direct_gap_elimination()
        print(f"    Filled {gaps_filled} gaps")
        
        # Phase 2: Direct Top 5 recovery
        top5_recovered = self._direct_top5_recovery()
        print(f"    Recovered {top5_recovered} Top 5 activities")
        
        return schedule
    
    def _direct_gap_elimination(self):
        """Direct gap elimination without validation"""
        gaps_filled = 0
        
        for troop in self.troops:
            gaps = self._find_troop_gaps(troop)
            
            for gap in gaps:
                if self._direct_fill_gap(troop, gap):
                    gaps_filled += 1
        
        return gaps_filled
    
    def _direct_top5_recovery(self):
        """Direct Top 5 recovery without validation"""
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
                    if self._direct_schedule_top5(troop, pref, priority):
                        recovered += 1
        
        return recovered
    
    def _direct_fill_gap(self, troop, time_slot):
        """Direct gap filling without validation"""
        # Priority activities
        priority_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        # Add troop's Top 5 preferences
        for pref in troop.preferences[:5]:
            if pref not in priority_activities:
                priority_activities.insert(5, pref)
        
        # Try each activity
        for activity_name in priority_activities:
            activity = get_activity_by_name(activity_name)
            if not activity:
                continue
            
            # Direct add without validation
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
    
    def _direct_schedule_top5(self, troop, activity_name, priority):
        """Direct Top 5 scheduling without validation"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try any available slot
        for slot in self.scheduler.time_slots:
            if self.scheduler.schedule.add_entry(slot, activity, troop):
                self.operations += 1
                return True
        
        # Try displacement
        if self._direct_displacement(troop, activity):
            return True
        
        return False
    
    def _direct_displacement(self, troop, target_activity):
        """Direct displacement without validation"""
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
            
            # Direct displacement
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


def fix_all_struggling_weeks_direct():
    """Fix all struggling weeks using direct approach"""
    print("DIRECT STRUGGLING WEEKS FIX")
    print("=" * 50)
    
    struggling_files = [
        'tc_week3_troops.json',
        'tc_week8_troops.json', 
        'tc_week1_troops.json',
        'voyageur_week3_troops.json',
        'voyageur_week1_troops.json',
        'tc_week6_troops.json',
        'tc_week4_troops.json',
        'tc_week5_troops.json',
        'tc_week7_troops.json'
    ]
    
    results = []
    
    for week_file in struggling_files:
        print(f"\n{'='*50}")
        print(f"FIXING: {week_file}")
        print('='*50)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply direct fix
            fixer = DirectWeekFixer(troops, week_name)
            schedule = fixer.fix_week()
            
            # Save fixed schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_direct_fixed_schedule.json')
            
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
            
            status = "SUCCESS" if result['success'] else "STILL STRUGGLING"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Violations: {result['violations']}")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            print(f"  Operations: {result['operations']}")
            
        except Exception as e:
            print(f"ERROR fixing {week_file}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print(f"\n{'='*50}")
    print("DIRECT FIX RESULTS SUMMARY")
    print('='*50)
    
    successful_weeks = [r for r in results if r['success']]
    failed_weeks = [r for r in results if not r['success']]
    
    print(f"Successfully Fixed: {len(successful_weeks)}/{len(results)} weeks")
    print(f"Still Struggling: {len(failed_weeks)} weeks")
    
    if successful_weeks:
        print(f"\nSUCCESSFUL WEEKS:")
        for r in successful_weeks:
            print(f"  {r['week']}: {r['score']}")
    
    if failed_weeks:
        print(f"\nSTILL NEED WORK:")
        for r in failed_weeks:
            print(f"  {r['week']}: {r['score']} (G:{r['gaps']} V:{r['violations']} T5:{r['top5_missed']})")
    
    # Calculate improvement
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        total_gaps = sum(r['gaps'] for r in results)
        total_violations = sum(r['violations'] for r in results)
        total_top5_missed = sum(r['top5_missed'] for r in results)
        
        print(f"\nIMPROVEMENT SUMMARY:")
        print(f"  Average Score: {avg_score:.1f}")
        print(f"  Total Gaps: {total_gaps}")
        print(f"  Total Violations: {total_violations}")
        print(f"  Total Top 5 Missed: {total_top5_missed}")
    
    # Save results
    with open('direct_fix_results.txt', 'w') as f:
        f.write('DIRECT STRUGGLING WEEKS FIX RESULTS\n')
        f.write('=' * 40 + '\n\n')
        f.write(f'Successfully Fixed: {len(successful_weeks)}/{len(results)} weeks\n\n')
        
        f.write('SUCCESSFUL:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]}\n')
        
        f.write('\nSTILL NEED WORK:\n')
        for r in failed_weeks:
            f.write(f'  {r["week"]}: {r["score"]} (G:{r["gaps"]} V:{r["violations"]} T5:{r["top5_missed"]})\n')
    
    print(f"\nResults saved to direct_fix_results.txt")
    return results

if __name__ == "__main__":
    fix_all_struggling_weeks_direct()
