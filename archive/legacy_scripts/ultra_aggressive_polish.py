#!/usr/bin/env python3
"""
Ultra-aggressive scheduler to maximize scores
Targets remaining gaps and Top 5 misses
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name
import glob

class UltraAggressiveScheduler(EnhancedScheduler):
    """Ultra-aggressive scheduler focused on maximizing scores"""
    
    def _apply_enhanced_optimizations(self):
        """Ultra-aggressive optimizations"""
        self.logger.info("Applying ULTRA-AGGRESSIVE optimizations...")
        
        # Multiple rounds of gap fixing
        for round_num in range(3):
            self.logger.info(f"Gap fixing round {round_num + 1}/3")
            gaps_before = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
            self._emergency_gap_fix()
            gaps_after = sum(len(self._find_troop_gaps(troop)) for troop in self.troops)
            
            if gaps_after == 0:
                self.logger.info(f"All gaps eliminated in round {round_num + 1}")
                break
            else:
                self.logger.info(f"Gaps reduced from {gaps_before} to {gaps_after}")
        
        # Ultra-aggressive Top 5 recovery
        for round_num in range(3):
            self.logger.info(f"Top 5 recovery round {round_num + 1}/3")
            self._ultra_aggressive_top5_recovery()
        
        # Final verification
        self._verify_no_gaps()
        
        self.logger.info(f"Ultra-aggressive optimizations complete")
    
    def _ultra_aggressive_top5_recovery(self):
        """Ultra-aggressive Top 5 recovery"""
        for troop in self.troops:
            troop_schedule = self.schedule.get_troop_schedule(troop)
            scheduled_activities = {e.activity.name for e in troop_schedule}
            
            # Check all Top 5 preferences
            missing_top5 = []
            for i, pref in enumerate(troop.preferences[:5]):
                if pref not in scheduled_activities:
                    missing_top5.append((pref, i))
            
            if missing_top5:
                self.logger.info(f"Ultra-aggressive recovery for {troop.name}: {len(missing_top5)} missing Top 5")
                
                for pref, priority in missing_top5:
                    # Try ultra-aggressive strategies
                    if self._ultra_schedule_activity(troop, pref, priority):
                        self.logger.info(f"SUCCESS: Ultra-aggressive recovery {pref} for {troop.name}")
                        self.successful_optimizations += 1
    
    def _ultra_schedule_activity(self, troop, activity_name: str, priority: int) -> bool:
        """Ultra-aggressive activity scheduling"""
        activity = get_activity_by_name(activity_name)
        if not activity:
            return False
        
        # Strategy 1: Direct placement
        for slot in self.time_slots:
            if self._can_schedule_in_slot(troop, activity, slot):
                if activity.slots > 1:
                    if self._check_consecutive_slots_available(troop, activity, slot):
                        self.schedule.add_entry(slot, activity, troop)
                        return True
                else:
                    self.schedule.add_entry(slot, activity, troop)
                    return True
        
        # Strategy 2: Force displacement (even Top 5)
        if self._force_displace_anything(troop, activity, priority):
            return True
        
        # Strategy 3: Multi-troop swaps
        if self._complex_multi_troop_swap(troop, activity, priority):
            return True
        
        return False
    
    def _force_displace_anything(self, troop, activity, priority: int) -> bool:
        """Displace ANY activity to make room for Top 5"""
        troop_schedule = self.schedule.get_troop_schedule(troop)
        
        for entry in troop_schedule:
            # Remove temporarily
            self.schedule.remove_entry(entry)
            
            # Try to schedule Top 5 activity
            if self._can_schedule_in_slot(troop, activity, entry.time_slot):
                if activity.slots > 1:
                    if self._check_consecutive_slots_available(troop, activity, entry.time_slot):
                        self.schedule.add_entry(entry.time_slot, activity, troop)
                        # Try to relocate displaced activity
                        if self._relocate_displaced_activity(entry):
                            self.logger.info(f"Force displaced {entry.activity.name} for Top 5 {activity.name}")
                            return True
                else:
                    self.schedule.add_entry(entry.time_slot, activity, troop)
                    # Try to relocate displaced activity
                    if self._relocate_displaced_activity(entry):
                        self.logger.info(f"Force displaced {entry.activity.name} for Top 5 {activity.name}")
                        return True
            
            # Put it back if failed
            self.schedule.add_entry(entry.time_slot, entry.activity, entry.troop)
        
        return False
    
    def _relocate_displaced_activity(self, entry) -> bool:
        """Try to relocate a displaced activity"""
        for slot in self.time_slots:
            if self._can_schedule_in_slot(entry.troop, entry.activity, slot):
                self.schedule.add_entry(slot, entry.activity, entry.troop)
                return True
        return False
    
    def _complex_multi_troop_swap(self, troop, activity, priority: int) -> bool:
        """Complex multi-troop swapping"""
        # Find any troop that has the desired activity
        for other_troop in self.troops:
            if other_troop == troop:
                continue
            
            other_schedule = self.schedule.get_troop_schedule(other_troop)
            for entry in other_schedule:
                if entry.activity.name == activity.name:
                    # Try to find a 3-way or 4-way swap
                    if self._attempt_complex_swap(troop, other_troop, activity, entry):
                        return True
        return False
    
    def _attempt_complex_swap(self, troop1, troop2, desired_activity, entry_to_swap) -> bool:
        """Attempt complex multi-troop swap"""
        # For now, fall back to simple swap
        return self._perform_swap(troop1, troop2, desired_activity, entry_to_swap)


def ultra_aggressive_polish():
    """Apply ultra-aggressive polish to all weeks"""
    print("ULTRA-AGGRESSIVE SCHEDULER POLISH")
    print("=" * 50)
    
    week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in week_files:
        print(f"\nProcessing {week_file}...")
        
        try:
            troops = load_troops_from_json(week_file)
            
            # Apply ultra-aggressive scheduler
            scheduler = UltraAggressiveScheduler(troops)
            schedule = scheduler.schedule_all()
            
            # Save schedule
            week_name = week_file.replace('_troops.json', '')
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_ultra_schedule.json')
            
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
                'entries': len(schedule.entries)
            }
            results.append(result)
            
            print(f"  Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Summary
    print(f"\nULTRA-AGGRESSIVE RESULTS")
    print("=" * 50)
    
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        avg_gaps = sum(r['gaps'] for r in results) / len(results)
        avg_top5_missed = sum(r['top5_missed'] for r in results) / len(results)
        
        print(f"Average Score: {avg_score:.1f}")
        print(f"Average Gaps: {avg_gaps:.1f}")
        print(f"Average Top 5 Missed: {avg_top5_missed:.1f}")
        
        # Best scores
        best_scores = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
        print(f"\nTop 3 Weeks:")
        for i, r in enumerate(best_scores, 1):
            print(f"  {i}. {r['week']}: {r['score']}")
    
    return results

if __name__ == "__main__":
    ultra_aggressive_polish()
