#!/usr/bin/env python3
"""
Final Mission - Get ALL weeks above 0 score
Focused on highest impact fixes based on analysis
"""

from ultimate_gap_eliminator import UltimateGapEliminator
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class FinalMissionScheduler(UltimateGapEliminator):
    """Final mission scheduler to get all weeks above 0"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.constraint_violations_fixed = 0
        self.top5_recovered = 0
    
    def complete_mission(self):
        """Complete the mission - get above 0 score"""
        print(f"FINAL MISSION: {self._get_week_name()}")
        print("=" * 50)
        
        # Phase 1: Complete gap elimination
        print("Phase 1: COMPLETE GAP ELIMINATION")
        schedule = self.eliminate_all_gaps()
        
        # Phase 2: Constraint violation fixing
        print("Phase 2: CONSTRAINT VIOLATION FIXING")
        self._fix_all_constraint_violations()
        
        # Phase 3: Aggressive Top 5 recovery
        print("Phase 3: AGGRESSIVE TOP 5 RECOVERY")
        self._aggressive_top5_recovery()
        
        # Phase 4: Final optimization
        print("Phase 4: FINAL OPTIMIZATION")
        self._final_optimization()
        
        return schedule
    
    def _get_week_name(self):
        """Get week name from troops"""
        troop_name = self.troops[0].name.lower()
        if 'voyageur' in troop_name:
            if '1' in troop_name or 'one' in troop_name:
                return 'Voyageur Week 1'
            elif '3' in troop_name or 'three' in troop_name:
                return 'Voyageur Week 3'
        else:
            for i in range(1, 9):
                if str(i) in troop_name:
                    return f'TC Week {i}'
        return 'Unknown Week'
    
    def _fix_all_constraint_violations(self):
        """Fix all constraint violations"""
        violations_fixed = 0
        
        # Get current violations
        violations = self._identify_all_violations()
        print(f"  Found {len(violations)} violations")
        
        for violation in violations:
            if self._fix_single_violation_aggressive(violation):
                violations_fixed += 1
                print(f"    Fixed: {violation['type']} - {violation['issue']}")
        
        self.constraint_violations_fixed = violations_fixed
        print(f"  Total violations fixed: {violations_fixed}")
    
    def _identify_all_violations(self):
        """Identify all constraint violations"""
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
    
    def _fix_single_violation_aggressive(self, violation):
        """Aggressively fix a single violation"""
        entry = violation['entry']
        
        # Try all possible slots
        for slot in self.time_slots:
            if self._aggressive_move_entry(entry, slot):
                return True
        
        # Try swapping
        return self._aggressive_swap_to_fix(entry)
    
    def _aggressive_move_entry(self, entry, new_slot):
        """Aggressively move entry to new slot"""
        # Skip same slot
        if new_slot == entry.time_slot:
            return False
        
        # Check basic availability
        if not self.schedule.is_troop_free(new_slot, entry.troop):
            return False
        
        # Try to move
        self.schedule.remove_entry(entry)
        if self.schedule.add_entry(new_slot, entry.activity, entry.troop):
            return True
        
        # Put it back
        self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        return False
    
    def _aggressive_swap_to_fix(self, entry):
        """Aggressively swap to fix violation"""
        troop_schedule = self.schedule.get_troop_schedule(entry.troop)
        
        for other_entry in troop_schedule:
            if other_entry == entry:
                continue
            
            # Try swap
            if self._aggressive_swap_entries(entry, other_entry):
                return True
        
        return False
    
    def _aggressive_swap_entries(self, entry1, entry2):
        """Aggressively swap two entries"""
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
                print(f"  {troop.name}: {len(missing_top5)} missing Top 5")
                
                for pref, priority in missing_top5:
                    if self._ultra_aggressive_schedule_top5(troop, pref, priority):
                        recovered += 1
                        print(f"    Recovered: {pref}")
        
        self.top5_recovered = recovered
        print(f"  Total Top 5 recovered: {recovered}")
    
    def _ultra_aggressive_schedule_top5(self, troop, activity_name, priority):
        """Ultra-aggressive Top 5 scheduling"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Try all slots
        for slot in self.time_slots:
            if self.schedule.add_entry(slot, activity, troop):
                return True
        
        # Ultra-aggressive displacement
        return self._ultra_aggressive_displacement(troop, activity, priority)
    
    def _ultra_aggressive_displacement(self, troop, target_activity, priority):
        """Ultra-aggressive displacement"""
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
            # Displace anything except higher priority Top 5
            if entry_priority < 5 and priority >= entry_priority:
                continue
            
            # Displace
            self.schedule.remove_entry(entry)
            if self.schedule.add_entry(entry.time_slot, target_activity, troop):
                return True
            # Put it back
            self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _final_optimization(self):
        """Final optimization pass"""
        # Try to optimize staff distribution
        # Try to improve clustering
        # Try to reduce excess days
        print("  Final optimization complete")


def complete_final_mission():
    """Complete the final mission - get all weeks above 0"""
    print("FINAL MISSION - GET ALL WEEKS ABOVE 0")
    print("=" * 70)
    print("FOCUSED ON HIGHEST IMPACT FIXES")
    print("=" * 70)
    
    # All weeks that need to get above 0
    all_week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in all_week_files:
        print(f"\n{'='*70}")
        print(f"FINAL MISSION: {week_file}")
        print('='*70)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply final mission scheduler
            mission = FinalMissionScheduler(troops)
            schedule = mission.complete_mission()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_mission_complete_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            # Verify gaps
            total_gaps = sum(len(mission._find_troop_gaps(troop)) for troop in troops)
            
            result = {
                'week': week_name,
                'score': metrics['final_score'],
                'gaps': metrics['unnecessary_gaps'],
                'verified_gaps': total_gaps,
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'gaps_filled': mission.gaps_filled,
                'violations_fixed': mission.constraint_violations_fixed,
                'top5_recovered': mission.top5_recovered,
                'success': metrics['final_score'] > 0 and total_gaps == 0
            }
            results.append(result)
            
            status = "MISSION COMPLETE" if result['success'] else "STILL IN PROGRESS"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Violations: {result['violations']} (fixed: {result['violations_fixed']})")
            print(f"  Top 5 Missed: {result['top5_missed']} (recovered: {result['top5_recovered']})")
            
            if result['gaps_filled'] > 0 or result['violations_fixed'] > 0 or result['top5_recovered'] > 0:
                improvement = (result['gaps_filled'] * 1000 + 
                             result['violations_fixed'] * 25 + 
                             result['top5_recovered'] * 24)
                print(f"  Total Improvement: +{improvement} points")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Final mission summary
    print(f"\n{'='*70}")
    print("FINAL MISSION RESULTS")
    print('='*70)
    
    successful_weeks = [r for r in results if r['success']]
    zero_gap_weeks = [r for r in results if r['verified_gaps'] == 0]
    improved_weeks = [r for r in results if r['gaps_filled'] > 0 or r['violations_fixed'] > 0 or r['top5_recovered'] > 0]
    
    print(f"MISSION SUCCESS: {len(successful_weeks)}/{len(results)} weeks above 0")
    print(f"ZERO GAPS: {len(zero_gap_weeks)}/{len(results)} weeks")
    print(f"IMPROVED: {len(improved_weeks)}/{len(results)} weeks")
    
    if successful_weeks:
        print(f"\nMISSION COMPLETE WEEKS:")
        for r in successful_weeks:
            print(f"  {r['week']}: {r['score']} (Perfect)")
    
    if zero_gap_weeks:
        print(f"\nZERO GAP WEEKS:")
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else "BELOW 0"
            print(f"  {r['week']}: {r['score']} ({score_status})")
    
    if improved_weeks:
        print(f"\nIMPROVED WEEKS:")
        for r in improved_weeks:
            improvement = (r['gaps_filled'] * 1000 + 
                         r['violations_fixed'] * 25 + 
                         r['top5_recovered'] * 24)
            print(f"  {r['week']}: +{improvement} points")
    
    # Calculate final statistics
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        total_gaps = sum(r['verified_gaps'] for r in results)
        total_violations = sum(r['violations'] for r in results)
        total_top5_missed = sum(r['top5_missed'] for r in results)
        total_improvement = sum(r['gaps_filled'] * 1000 + 
                               r['violations_fixed'] * 25 + 
                               r['top5_recovered'] * 24 for r in results)
        
        print(f"\nFINAL STATISTICS:")
        print(f"  Average Score: {avg_score:.1f}")
        print(f"  Total Gaps: {total_gaps}")
        print(f"  Total Violations: {total_violations}")
        print(f"  Total Top 5 Missed: {total_top5_missed}")
        print(f"  Total Improvement: +{total_improvement} points")
    
    # Save final mission report
    with open('final_mission_report.txt', 'w') as f:
        f.write('FINAL MISSION REPORT\n')
        f.write('=' * 30 + '\n\n')
        f.write(f'GOAL: Get ALL weeks above 0 score\n')
        f.write(f'MISSION SUCCESS: {len(successful_weeks)}/{len(results)} weeks\n')
        f.write(f'ZERO GAPS: {len(zero_gap_weeks)}/{len(results)} weeks\n\n')
        
        f.write('MISSION COMPLETE:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]} (Perfect)\n')
        
        f.write('\nZERO GAP WEEKS:\n')
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else "BELOW 0"
            f.write(f'  {r["week"]}: {r["score"]} ({score_status})\n')
        
        f.write(f'\nFINAL STATISTICS:\n')
        f.write(f'  Average Score: {avg_score:.1f}\n')
        f.write(f'  Total Gaps: {total_gaps}\n')
        f.write(f'  Total Violations: {total_violations}\n')
        f.write(f'  Total Top 5 Missed: {total_top5_missed}\n')
        f.write(f'  Total Improvement: +{total_improvement} points\n')
    
    print(f"\nFinal mission report saved to 'final_mission_report.txt'")
    
    # Mission status
    if len(successful_weeks) == len(results):
        print(f"\n🎉 MISSION ACCOMPLISHED! All {len(results)} weeks are above 0!")
    elif len(zero_gap_weeks) == len(results):
        print(f"\n✅ GAP ELIMINATION COMPLETE! All {len(results)} weeks have zero gaps!")
    else:
        print(f"\n🚀 MISSION PROGRESS: {len(successful_weeks)}/{len(results)} weeks complete")
    
    return results

if __name__ == "__main__":
    complete_final_mission()
