#!/usr/bin/env python3
"""
Ultimate Gap Eliminator - Enhanced with Spine-based Prevention and Multi-Strategy Approach
Implements comprehensive gap elimination with prevention-first methodology
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
from activities import get_activity_by_name, get_all_activities
from models import ScheduleEntry, TimeSlot
from prevention_aware_validator import PreventionValidator
import glob
import logging

class UltimateGapEliminator(EnhancedScheduler):
    """Enhanced ultimate gap eliminator with Spine-based prevention and multi-strategy approach"""
    
    def __init__(self, troops, time_slots=None):
        super().__init__(troops, time_slots)
        self.gaps_filled = 0
        self.emergency_operations = 0
        
        # Initialize prevention validator
        self.validator = PreventionValidator(self.schedule)
        
        # Strategy tracking
        self.strategy_usage = {
            'top5': 0,
            'high_value': 0,
            'standard': 0,
            'basic': 0,
            'force_fill': 0
        }
        
        # Activity priority hierarchy (from Spine)
        self.high_value_activities = [
            "Super Troop", "Delta", "Climbing Tower", "Aqua Trampoline", 
            "Itasca State Park", "Tamarac Wildlife Refuge", "Back of the Moon"
        ]
        
        self.standard_activities = [
            "Archery", "Sailing", "Water Polo", "Troop Rifle", "Troop Shotgun",
            "Ultimate Survivor", "What's Cooking", "Chopped!", "GPS & Geocaching",
            "Orienteering", "Knots and Lashings", "Trading Post", "Shower House"
        ]
        
        self.basic_activities = [
            "Campsite Free Time", "Gaga Ball", "9 Square", "Troop Swim",
            "Fishing", "Dr. DNA", "Loon Lore", "Hemp Craft"
        ]
    
    def eliminate_all_gaps(self):
        """Enhanced gap elimination with Spine-based multi-strategy approach"""
        self.logger.info("Starting enhanced ultimate gap elimination...")
        
        # Generate base schedule
        schedule = super().schedule_all()
        
        # Identify all gaps
        all_gaps = self._identify_all_gaps()
        self.logger.info(f"Found {len(all_gaps)} total gaps")
        
        # Multi-strategy gap elimination (Spine approach)
        self._spine_based_gap_elimination(all_gaps)
        
        # Final verification
        remaining_gaps = self._identify_all_gaps()
        if remaining_gaps:
            self.logger.info(f"{len(remaining_gaps)} gaps remain - emergency elimination...")
            emergency_filled = self._emergency_gap_elimination(remaining_gaps)
            self.logger.info(f"Emergency filled {emergency_filled} gaps")
        
        final_gaps = self._identify_all_gaps()
        self.logger.info(f"Final gaps: {len(final_gaps)}")
        
        return schedule
    
    def _spine_based_gap_elimination(self, all_gaps):
        """Implement Spine-based gap filling hierarchy"""
        self.logger.info("Starting Spine-based gap elimination...")
        
        # Strategy 1: Top 5 Preferences (highest priority)
        top5_filled = self._fill_top5_preferences(all_gaps)
        self.strategy_usage['top5'] = top5_filled
        self.gaps_filled += top5_filled
        
        # Strategy 2: High-Value Activities
        high_value_filled = self._fill_high_value_activities(all_gaps)
        self.strategy_usage['high_value'] = high_value_filled
        self.gaps_filled += high_value_filled
        
        # Strategy 3: Standard Activities
        standard_filled = self._fill_standard_activities(all_gaps)
        self.strategy_usage['standard'] = standard_filled
        self.gaps_filled += standard_filled
        
        # Strategy 4: Basic Activities
        basic_filled = self._fill_basic_activities(all_gaps)
        self.strategy_usage['basic'] = basic_filled
        self.gaps_filled += basic_filled
        
        self.logger.info(f"Spine-based elimination filled {self.gaps_filled} gaps")
        self.logger.info(f"Strategy usage: {self.strategy_usage}")
    
    def _fill_top5_preferences(self, all_gaps):
        """Strategy 1: Fill gaps with Top 5 preferences"""
        filled = 0
        
        for troop in self.troops:
            troop_gaps = [gap for gap in all_gaps if gap['troop'] == troop]
            top5_prefs = troop.preferences[:5] if len(troop.preferences) >= 5 else troop.preferences
            
            for gap_info in troop_gaps:
                gap_slot = gap_info['slot']
                
                # Try each top 5 preference in order
                for pref_activity in top5_prefs:
                    activity = get_activity_by_name(pref_activity.name)
                    if not activity:
                        continue
                    
                    # Use prevention validator for comprehensive check
                    validation = self.validator.comprehensive_prevention_check(troop, activity, gap_slot)
                    
                    if validation['valid']:
                        # Place the activity
                        entry = ScheduleEntry(troop, activity, gap_slot)
                        self.schedule.add_entry(entry)
                        filled += 1
                        all_gaps.remove(gap_info)  # Remove from list
                        break
                    else:
                        # Try displacement strategy for top 5
                        if self._try_displacement_for_top5(troop, activity, gap_slot):
                            filled += 1
                            all_gaps.remove(gap_info)
                            break
        
        self.logger.info(f"Top 5 strategy filled {filled} gaps")
        return filled
    
    def _fill_high_value_activities(self, all_gaps):
        """Strategy 2: Fill gaps with high-value activities"""
        filled = 0
        
        for troop in self.troops:
            troop_gaps = [gap for gap in all_gaps if gap['troop'] == troop]
            
            for gap_info in troop_gaps:
                gap_slot = gap_info['slot']
                
                # Try high-value activities in priority order
                for activity_name in self.high_value_activities:
                    activity = get_activity_by_name(activity_name)
                    if not activity:
                        continue
                    
                    validation = self.validator.comprehensive_prevention_check(troop, activity, gap_slot)
                    
                    if validation['valid']:
                        entry = ScheduleEntry(troop, activity, gap_slot)
                        self.schedule.add_entry(entry)
                        filled += 1
                        all_gaps.remove(gap_info)
                        break
        
        self.logger.info(f"High-value strategy filled {filled} gaps")
        return filled
    
    def _fill_standard_activities(self, all_gaps):
        """Strategy 3: Fill gaps with standard activities"""
        filled = 0
        
        for troop in self.troops:
            troop_gaps = [gap for gap in all_gaps if gap['troop'] == troop]
            
            for gap_info in troop_gaps:
                gap_slot = gap_info['slot']
                
                # Try standard activities
                for activity_name in self.standard_activities:
                    activity = get_activity_by_name(activity_name)
                    if not activity:
                        continue
                    
                    validation = self.validator.comprehensive_prevention_check(troop, activity, gap_slot)
                    
                    if validation['valid']:
                        entry = ScheduleEntry(troop, activity, gap_slot)
                        self.schedule.add_entry(entry)
                        filled += 1
                        all_gaps.remove(gap_info)
                        break
        
        self.logger.info(f"Standard strategy filled {filled} gaps")
        return filled
    
    def _fill_basic_activities(self, all_gaps):
        """Strategy 4: Fill gaps with basic activities"""
        filled = 0
        
        for troop in self.troops:
            troop_gaps = [gap for gap in all_gaps if gap['troop'] == troop]
            
            for gap_info in troop_gaps:
                gap_slot = gap_info['slot']
                
                # Try basic activities
                for activity_name in self.basic_activities:
                    activity = get_activity_by_name(activity_name)
                    if not activity:
                        continue
                    
                    validation = self.validator.comprehensive_prevention_check(troop, activity, gap_slot)
                    
                    if validation['valid']:
                        entry = ScheduleEntry(troop, activity, gap_slot)
                        self.schedule.add_entry(entry)
                        filled += 1
                        all_gaps.remove(gap_info)
                        break
        
        self.logger.info(f"Basic strategy filled {filled} gaps")
        return filled
    
    def _try_displacement_for_top5(self, troop, activity, time_slot):
        """Try to displace a lower-priority activity to make room for Top 5"""
        # Find existing activities that could be displaced
        troop_entries = self.schedule.get_troop_entries(troop)
        
        # Sort by priority (lower priority first)
        displacable_entries = []
        for entry in troop_entries:
            if self._can_displace_entry(entry, activity):
                displacable_entries.append(entry)
        
        displacable_entries.sort(key=lambda e: self._get_displacement_priority(e))
        
        # Try to displace the lowest priority entry
        for entry in displacable_entries:
            # Try to move the displaced activity to another slot
            if self._move_entry_to_new_slot(entry):
                # Place the top 5 activity in the freed slot
                new_entry = ScheduleEntry(troop, activity, time_slot)
                self.schedule.add_entry(new_entry)
                return True
        
        return False
    
    def _can_displace_entry(self, entry, new_activity):
        """Check if an entry can be displaced for a new activity"""
        # Don't displace other top 5 activities
        troop_prefs = entry.troop.preferences[:5]
        if entry.activity.name in [pref.name for pref in troop_prefs]:
            return False
        
        # Don't displace high-value activities for standard activities
        if entry.activity.name in self.high_value_activities and new_activity.name not in self.high_value_activities:
            return False
        
        return True
    
    def _get_displacement_priority(self, entry):
        """Get displacement priority (lower number = easier to displace)"""
        if entry.activity.name in self.basic_activities:
            return 1
        elif entry.activity.name in self.standard_activities:
            return 2
        elif entry.activity.name in self.high_value_activities:
            return 3
        else:
            return 4
    
    def _move_entry_to_new_slot(self, entry):
        """Try to move an entry to a new valid slot"""
        available_slots = self.schedule.get_remaining_slots_for_troop(entry.troop)
        
        for slot in available_slots:
            validation = self.validator.comprehensive_prevention_check(entry.troop, entry.activity, slot)
            if validation['valid']:
                # Move the entry
                self.schedule.remove_entry(entry)
                new_entry = ScheduleEntry(entry.troop, entry.activity, slot)
                self.schedule.add_entry(new_entry)
                return True
        
        return False
    
    def _identify_all_gaps(self):
        """Identify all gaps across all troops"""
        all_gaps = []
        for troop in self.troops:
            gaps = self._find_troop_gaps(troop)
            for gap in gaps:
                all_gaps.append({'troop': troop, 'time_slot': gap})
        return all_gaps
    
    def _ultimate_gap_elimination(self, gaps):
        """Ultimate gap elimination - try everything"""
        gaps_filled = 0
        
        for gap_info in gaps:
            troop = gap_info['troop']
            time_slot = gap_info['time_slot']
            
            print(f"  Filling gap: {troop.name} at {time_slot}")
            
            if self._ultimate_fill_single_gap(troop, time_slot):
                gaps_filled += 1
                print(f"    SUCCESS")
            else:
                print(f"    FAILED")
        
        return gaps_filled
    
    def _ultimate_fill_single_gap(self, troop, time_slot):
        """Fill a single gap with ultimate aggression"""
        
        # Strategy 1: Try all activities
        if self._try_all_activities(troop, time_slot):
            return True
        
        # Strategy 2: Try displacement
        if self._try_displacement(troop, time_slot):
            return True
        
        # Strategy 3: Emergency activities
        if self._try_emergency_activities(troop, time_slot):
            return True
        
        return False
    
    def _try_all_activities(self, troop, time_slot):
        """Try all possible activities"""
        
        # Priority 1: Troop's Top 5
        for pref in troop.preferences[:5]:
            activity = get_activity_by_name(pref)
            if activity and self._safe_add_activity(troop, activity, time_slot):
                return True
        
        # Priority 2: High-value activities
        high_value = [
            "Super Troop", "Delta", "Climbing Tower", "Sailing", "Archery",
            "Troop Rifle", "Troop Shotgun", "Swimming", "Nature Canoe", "Fishing"
        ]
        
        for activity_name in high_value:
            activity = get_activity_by_name(activity_name)
            if activity and self._safe_add_activity(troop, activity, time_slot):
                return True
        
        # Priority 3: All other activities
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
        
        return False
    
    def _try_displacement(self, troop, time_slot):
        """Try displacing an existing activity"""
        troop_entries = self.schedule.get_troop_schedule(troop)
        
        # Sort by priority (easiest to displace first)
        entries_by_priority = []
        for entry in troop_entries:
            try:
                entry_priority = troop.preferences.index(entry.activity.name)
            except ValueError:
                entry_priority = 999
            entries_by_priority.append((entry_priority, entry))
        
        entries_by_priority.sort(key=lambda x: x[0], reverse=True)
        
        # Try displacing each entry
        for entry_priority, entry in entries_by_priority:
            if entry_priority < 5:  # Don't displace Top 5
                continue
            
            # Try to place entry.activity in the gap slot
            if self._safe_add_activity(troop, entry.activity, time_slot):
                self.schedule.remove_entry(entry)
                self.emergency_operations += 1
                return True
        
        return False
    
    def _try_emergency_activities(self, troop, time_slot):
        """Try emergency activities"""
        emergency_activities = ["Campsite Free Time", "Shower House", "Trading Post"]
        
        for activity_name in emergency_activities:
            activity = get_activity_by_name(activity_name)
            if activity:
                try:
                    if self.schedule.add_entry(time_slot, activity, troop):
                        self.gaps_filled += 1
                        return True
                except:
                    continue
        
        return False
    
    def _safe_add_activity(self, troop, activity, time_slot):
        """Safely add an activity"""
        try:
            if self.schedule.add_entry(time_slot, activity, troop):
                self.gaps_filled += 1
                return True
        except:
            pass
        return False
    
    def _emergency_gap_elimination(self, gaps):
        """Emergency gap elimination"""
        emergency_filled = 0
        
        for gap_info in gaps:
            troop = gap_info['troop']
            time_slot = gap_info['time_slot']
            
            # Force add Campsite Free Time
            activity = get_activity_by_name("Campsite Free Time")
            if activity:
                try:
                    # Create entry directly
                    from models import ScheduleEntry
                    entry = ScheduleEntry(time_slot, activity, troop)
                    self.schedule.entries.append(entry)
                    emergency_filled += 1
                    print(f"  Emergency filled: {troop.name} at {time_slot}")
                except:
                    pass
        
        return emergency_filled


def ultimate_gap_fix_all_weeks():
    """Apply ultimate gap eliminator to all weeks"""
    print("ULTIMATE GAP ELIMINATOR - ALL WEEKS")
    print("=" * 60)
    
    # Focus on weeks with gaps
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
        print(f"ULTIMATE GAP ELIMINATION: {week_file}")
        print('='*60)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Apply ultimate gap eliminator
            eliminator = UltimateGapEliminator(troops)
            schedule = eliminator.eliminate_all_gaps()
            
            # Save schedule
            save_schedule_to_json(schedule, troops, f'schedules/{week_name}_ultimate_gap_schedule.json')
            
            # Evaluate results
            metrics = evaluate_week(week_file)
            
            # Verify gaps
            total_gaps = sum(len(eliminator._find_troop_gaps(troop)) for troop in troops)
            
            result = {
                'week': week_name,
                'score': metrics['final_score'],
                'gaps': metrics['unnecessary_gaps'],
                'verified_gaps': total_gaps,
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'gaps_filled': eliminator.gaps_filled,
                'emergency_ops': eliminator.emergency_operations,
                'success': metrics['final_score'] > 0 and total_gaps == 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "NEEDS WORK"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']} (verified: {result['verified_gaps']})")
            print(f"  Gaps filled: {result['gaps_filled']}")
            print(f"  Emergency ops: {result['emergency_ops']}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print("ULTIMATE GAP ELIMINATOR RESULTS")
    print('='*60)
    
    successful_weeks = [r for r in results if r['success']]
    zero_gap_weeks = [r for r in results if r['verified_gaps'] == 0]
    
    print(f"Perfect Weeks (0 gaps + >0 score): {len(successful_weeks)}/{len(results)}")
    print(f"Zero Gap Weeks: {len(zero_gap_weeks)}/{len(results)}")
    
    if successful_weeks:
        print(f"\nPERFECT WEEKS:")
        for r in successful_weeks:
            print(f"  {r['week']}: {r['score']} (0 gaps)")
    
    if zero_gap_weeks:
        print(f"\nZERO GAP WEEKS:")
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else "BELOW 0"
            print(f"  {r['week']}: {r['score']} ({score_status})")
    
    # Calculate statistics
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        total_gaps = sum(r['verified_gaps'] for r in results)
        total_gaps_filled = sum(r['gaps_filled'] for r in results)
        
        print(f"\nSTATISTICS:")
        print(f"  Average Score: {avg_score:.1f}")
        print(f"  Total Gaps: {total_gaps}")
        print(f"  Total Gaps Filled: {total_gaps_filled}")
    
    # Save results
    with open('ultimate_gap_results.txt', 'w') as f:
        f.write('ULTIMATE GAP ELIMINATOR RESULTS\n')
        f.write('=' * 40 + '\n\n')
        f.write(f'Perfect Weeks (0 gaps + >0 score): {len(successful_weeks)}/{len(results)}\n')
        f.write(f'Zero Gap Weeks: {len(zero_gap_weeks)}/{len(results)}\n\n')
        
        f.write('PERFECT WEEKS:\n')
        for r in successful_weeks:
            f.write(f'  {r["week"]}: {r["score"]} (0 gaps)\n')
        
        f.write('\nZERO GAP WEEKS:\n')
        for r in zero_gap_weeks:
            score_status = "ABOVE 0" if r['score'] > 0 else "BELOW 0"
            f.write(f'  {r["week"]}: {r["score"]} ({score_status})\n')
    
    print(f"\nResults saved to ultimate_gap_results.txt")
    return results

if __name__ == "__main__":
    ultimate_gap_fix_all_weeks()
