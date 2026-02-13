#!/usr/bin/env python3
"""
ENHANCED Regression Checker - Automated Testing for Every Code Change

This version ONLY analyzes the 10 actual week files, not all variants.
Uses the authoritative unscheduled_analyzer.py service for top 5 detection.
Now includes comprehensive schedule quality metrics from evaluate_week_success.py.
"""

import sys
import json
import os
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path to allow importing from core and utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.services.unscheduled_analyzer import UnscheduledAnalyzer
from core.constrained_scheduler import ConstrainedScheduler
from core.activities import get_all_activities, get_activity_by_name
from core.io_handler import load_troops_from_json, load_schedule_from_json
from core.models import Day, TimeSlot, generate_time_slots
from core.scheduler.constants import SchedulerConstants
from core.scheduler import config_loader

# Alias for backward compatibility if used in this file
EXCLUSIVE_AREAS = SchedulerConstants.EXCLUSIVE_ACTIVITIES # Wait, EXCLUSIVE_AREAS was a dict in models.py?
# In regression_checker line 128: EXCLUSIVE_AREAS.get(area, [])
# So it expects a dict.
# SchedulerConstants doesn't expose the dict directly?
# config_loader.get_exclusive_areas() returns the dict.
EXCLUSIVE_AREAS = config_loader.get_exclusive_areas()

# --- Configuration for Scoring (0-1000 perfect, can go negative) ---
# Target: 1000 = perfect schedule
# Components: Preferences (450) + Cluster (250) + Soft Constraints (150) + Staff (100) + Bonuses (50)
DEFAULT_WEIGHTS = {
    "max_score": 1000.0,

    # Preferences: Base Score ~450 pts (Innocent until proven guilty)
    # Deductions for Misses (Ranks 1-14)
    # Bonuses for Hits (Ranks 15-20)
    "preference_base_score": 450.0,
    "preference_weights": {
        "top5": [5.4, 4.7, 4.1, 3.4, 2.7],       # Ranks 1-5 (Mandatory) - Miss Penalty
        "top6_10": [2.6, 2.4, 2.3, 2.2, 2.0],    # Ranks 6-10 (Gradual) - Miss Penalty
        "top11_14": [1.8, 1.6, 1.4, 1.2],        # Ranks 11-14 - Miss Penalty
        "top15_20": [1.0, 0.8, 0.6, 0.4, 0.2, 0.0] # Ranks 15-20 - HIT BONUS
    },
    
    # Cluster Efficiency: 250 pts (HIGH PRIORITY - more important than staff)
    "cluster_efficiency_points": 250.0,
    
    # Soft Constraint Compliance: 150 pts (budget for soft violations)
    "soft_constraint_points": 150.0,
    
    # Staff Balance: 100 pts (secondary to clustering)
    "staff_balance_points": 100.0,
    
    # Bonuses: ~50 pts
    "early_week_points": 10.0,
    "activity_batching_points": 10.0,
    "promoted_pairing_points": 10.0,
    "sailing_full_day_points": 10.0,
    "sailing_same_day_points": 10.0,
    "at_sharing_bonus": 50.0,  # NEW: Bonus for AT slot sharing (2 small troops)

    # Penalties
    "excess_cluster_day_penalty": 25.0,   # INCREASED: Each excess cluster day costs significantly
    "cluster_gap_penalty": 15.0,          # INCREASED: Cluster gaps (1-x-3 pattern) 
    "staff_variance_penalty": 5.0,        # Per point of variance
    "severe_underuse_penalty": 3.0,       # Per severely underused slot
    "excessive_staff_penalty": 2.0,       # Per excessive staff slot
    "soft_violation_penalty": 10.0,       # NEW: Per soft constraint violation
    "top5_miss_penalty": 5.0,             # Per missed Top 5 activity
    "beach_slot_2_penalty": 3.0           # Per beach activity in slot 2 (non-Thursday)
}


# Staffed Activity Definition
STAFF_MAP = SchedulerConstants.STAFF_ROLE_MAP

ALL_STAFF_ACTIVITIES = set()
for acts in STAFF_MAP.values():
    ALL_STAFF_ACTIVITIES.update(acts)


def evaluate_week(week_file, weights=None):
    if weights is None:
        weights = DEFAULT_WEIGHTS

    troops = load_troops_from_json(week_file)
    all_activities = get_all_activities()
    
    # Try to load existing schedule from disk
    week_basename = os.path.splitext(os.path.basename(week_file))[0]
    # Update path to look in data/schedules/ relative to root
    schedule_file = os.path.join("data", "schedules", f"{week_basename}_schedule.json")
    
    if os.path.exists(schedule_file):
        #print(f"Loading existing schedule from {schedule_file}...")
        try:
            schedule = load_schedule_from_json(schedule_file, troops, all_activities)
            # Re-link schedule to valid objects if needed, but the loader handles mapping.
        except Exception as e:
            print(f"Error loading schedule: {e}")
            print("Falling back to fresh scheduling...")
            scheduler = ConstrainedScheduler(troops, all_activities)
            schedule = scheduler.schedule_all()
    else:
        print(f"No existing schedule found at {schedule_file}. Running fresh scheduler...")
        scheduler = ConstrainedScheduler(troops, all_activities)
        schedule = scheduler.schedule_all()
    
    metrics = {}
    
    # 1. Excess Days for Clustered Activities
    # ---------------------------------------
    # Areas to check: Tower, Rifle, ODS, Handicrafts
    cluster_areas = ["Tower", "Rifle Range", "Outdoor Skills", "Handicrafts"]
    total_excess_days = 0
    area_details = {}
    
    for area in cluster_areas:
        acts = EXCLUSIVE_AREAS.get(area, [])
        area_entries = [e for e in schedule.entries if e.activity.name in acts]
        if not area_entries:
            continue
            
        days_used = set(e.time_slot.day for e in area_entries)
        num_activities = len(area_entries)
        
        # Calculate ideal min days (assuming 3 slots/day capacity is roughly usable)
        # Being generous: Min Days = ceil(Activities / 3)
        min_days = math.ceil(num_activities / 3.0)
        
        excess = max(0, len(days_used) - min_days)
        total_excess_days += excess
        area_details[area] = {"days": len(days_used), "min": min_days, "excess": excess}

    metrics["excess_cluster_days"] = total_excess_days
    
    # 2. Unnecessary Gaps (Slot 1 & 3 full, Slot 2 empty)
    # ---------------------------------------------------
    gap_1_3_count = 0
    
    # Define slots per day
    slots_per_day = {
        Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
        Day.THURSDAY: 2, Day.FRIDAY: 3
    }
    
    # Define cluster areas
    CLUSTER_AREAS = {
        "Tower": ["Climbing Tower"],
        "Rifle Range": ["Troop Rifle", "Troop Shotgun"],
        "Outdoor Skills": ["Knots and Lashings", "Orienteering", "GPS & Geocaching",
                          "Ultimate Survivor", "What's Cooking", "Chopped!"],
        "Handicrafts": ["Tie Dye", "Hemp Craft", "Woggle Neckerchief Slide", "Monkey's Fist"],
    }
    cluster_activity_names = set()
    for acts in CLUSTER_AREAS.values():
        cluster_activity_names.update(acts)
    
    # Cluster gaps: cluster area has slots 1&3 full but slot 2 empty (3-slot days only)
    cluster_gap_count = 0
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            day_slots = {e.time_slot.slot_number: e.activity.name for e in troop_entries if e.time_slot.day == day}
            for area_name, area_acts in CLUSTER_AREAS.items():
                has_1 = any(day_slots.get(1) == a for a in area_acts)
                has_2 = any(day_slots.get(2) == a for a in area_acts)
                has_3 = any(day_slots.get(3) == a for a in area_acts)
                if has_1 and has_3 and not has_2:
                    cluster_gap_count += 1
    
    # CRITICAL: Any gaps completely invalidate the schedule
    # Use schedule.is_troop_free() - same logic as scheduler (handles multi-slot correctly)
    all_time_slots = list(generate_time_slots())
    for troop in troops:
        for day in Day:
            max_slot = slots_per_day[day]
            for slot_num in range(1, max_slot + 1):
                slot = next((s for s in all_time_slots if s.day == day and s.slot_number == slot_num), None)
                if slot and schedule.is_troop_free(slot, troop):
                    gap_1_3_count += 1
                
    metrics["unnecessary_gaps"] = gap_1_3_count
    metrics["cluster_gaps"] = cluster_gap_count

    # 3. Staff Distribution (Variance)
    # --------------------------------
    slot_counts = defaultdict(int)
    for e in schedule.entries:
        if e.activity.name in ALL_STAFF_ACTIVITIES:
            slot_counts[(e.time_slot.day, e.time_slot.slot_number)] += 1
    
    # Ensure all 14 slots are counted (even if 0)
    counts_list = []
    slots_list = [] # For debugging
    for day in Day:
        max_slot = 2 if day == Day.THURSDAY else 3
        for s in range(1, max_slot + 1):
            c = slot_counts[(day, s)]
            counts_list.append(c)
            slots_list.append(f"{day.value[:3]}-{s}")
            
    avg_load = sum(counts_list) / len(counts_list)
    variance = sum((c - avg_load) ** 2 for c in counts_list) / len(counts_list)
    metrics["staff_variance"] = variance
    metrics["avg_staff_load"] = avg_load

    # 4. Underused & Excessive Staff Slots
    # ------------------------------------
    # Severe Underuse: Dynamic Threshold (Mean * 0.5, min floor based on troop count)
    # Excessive Staff: > 14
    
    # FIX 2026-01-30: Scale the severe underuse floor based on troop count
    # Small weeks (3-4 troops) naturally have lower slot utilization
    # and shouldn't be penalized for this structural limitation
    num_troops = len(troops)
    if num_troops <= 3:
        SEVERE_FLOOR = 1.5  # Very small weeks: expect ~1-2 per slot
    elif num_troops <= 5:
        SEVERE_FLOOR = 2.0  # Small weeks: expect ~2 per slot
    elif num_troops <= 7:
        SEVERE_FLOOR = 2.5  # Medium weeks
    else:
        SEVERE_FLOOR = 3.0  # Normal threshold for larger weeks
    
    severe_threshold = max(SEVERE_FLOOR, avg_load * 0.5)
    
    severe_underused = sum(1 for c in counts_list if c < severe_threshold)
    excessive_staff = sum(1 for c in counts_list if c > 14)
    
    metrics["severe_underused_slots"] = severe_underused
    metrics["excessive_staff_slots"] = excessive_staff
    
    # 5. Constraint Violations (HARD vs SOFT)
    # ----------------------------------------
    # HARD = Schedule Invalid (-1000): Empty slots, exclusive double-book, missing mandatory
    # SOFT = Deduct from budget: Wet patterns, same-day pairs, clustering issues
    hard_violations = 0
    soft_violations = 0
    hard_violation_details = []
    soft_violation_details = []
    
    # Beach Slot Rule - full list; Top 5 relaxation: slot 2 allowed when 1/3/Thu-2 full (AT: exclusive only)
    # Also track beach_slot_2_uses for score penalty (slot 2 is worse than 1/3 but better than missing Top 5)
    BEACH_SLOT_ACTS = {"Water Polo", "Greased Watermelon", "Aqua Trampoline", "Troop Swim",
                       "Underwater Obstacle Course", "Troop Canoe", "Troop Kayak", "Canoe Snorkel",
                       "Nature Canoe", "Float for Floats"}  # Sailing excluded - allowed slot 2
    beach_slot_2_uses = 0
    for e in schedule.entries:
        if e.activity.name in BEACH_SLOT_ACTS:
            if e.time_slot.day != Day.THURSDAY and e.time_slot.slot_number == 2:
                beach_slot_2_uses += 1  # Penalize every use of slot 2 for beach (worse than 1/3)
                troop = e.troop
                pref_rank = troop.get_priority(e.activity.name) if hasattr(troop, 'get_priority') else None
                is_top5 = pref_rank is not None and pref_rank < 5
                if is_top5:
                    if e.activity.name == "Aqua Trampoline":
                        if (troop.scouts + troop.adults) <= 16:
                            soft_violations += 1  # SOFT: AT slot 2 requires exclusive (17+)
                            soft_violation_details.append(f"{troop.name}: Aqua Trampoline in Slot 2 (small troop) on {e.time_slot.day.value}")
                    # else: Top 5 other beach - no violation (relaxation applies)
                else:
                    soft_violations += 1  # SOFT: Not Top 5 - penalize but not invalid
                    soft_violation_details.append(f"{troop.name}: Beach activity '{e.activity.name}' in Slot 2 (not Top 5) on {e.time_slot.day.value}")
    metrics["beach_slot_2_uses"] = beach_slot_2_uses
    
    # Delta vs Tower/ODS - Spine: "can be same day but not back to back" (adjacent slots only)
    TOWER_ODS_ACTS = set(EXCLUSIVE_AREAS.get("Tower", [])) | set(EXCLUSIVE_AREAS.get("Outdoor Skills", []))
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day_slot = defaultdict(dict)  # day -> {slot_num: activity_name}
        for e in troop_entries:
            by_day_slot[e.time_slot.day][e.time_slot.slot_number] = e.activity.name
        for day, slot_acts in by_day_slot.items():
            delta_slots = [s for s, a in slot_acts.items() if a == "Delta"]
            tower_slots = [s for s, a in slot_acts.items() if a in TOWER_ODS_ACTS]
            for ds in delta_slots:
                for ts in tower_slots:
                    if abs(ds - ts) <= 1:  # Adjacent
                        hard_violations += 1  # HARD: Geographic constraint
                        hard_violation_details.append(f"{troop.name}: Delta adjacent to Tower/ODS on {day.value}")
                        break
                else:
                    continue
                break

    # Friday Reflection Missing
    for t in troops:
        has_ref = any(e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY 
                     for e in schedule.entries if e.troop == t)
        if not has_ref:
            hard_violations += 1  # HARD: Mandatory spine activity
            hard_violation_details.append(f"{t.name}: Missing Friday Reflection")
    
    # Trading Post + Campsite Free Time / Shower House (Same Day)
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day = defaultdict(set)
        for e in troop_entries:
            by_day[e.time_slot.day].add(e.activity.name)
        
        for day, acts in by_day.items():
            has_trading = "Trading Post" in acts
            has_campsite = "Campsite Free Time" in acts
            has_shower = "Shower House" in acts
            if has_trading and (has_campsite or has_shower):
                soft_violations += 1  # SOFT: Same-day pair recommendation
                other = 'Campsite Free Time' if has_campsite else 'Shower House'
                soft_violation_details.append(f"{troop.name}: Trading Post + {other} on same day ({day.value})")
    
    # NEW: Canoe Pairing Conflicts (any 2 of these on same day)
    CANOE_ACTIVITIES = ["Troop Canoe", "Canoe Snorkel", "Nature Canoe", "Float for Floats"]
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day = defaultdict(set)
        for e in troop_entries:
            if e.activity.name in CANOE_ACTIVITIES:
                by_day[e.time_slot.day].add(e.activity.name)
        
        for day, acts in by_day.items():
            if len(acts) >= 2:
                soft_violations += 1  # SOFT: Same-day boat pair
                soft_violation_details.append(f"{troop.name}: Multiple canoe activities on {day.value} ({', '.join(acts)})")
    
    # NEW: Wet-Dry-Wet Pattern (Slot 1 wet, Slot 2 dry, Slot 3 wet)
    WET_ACTIVITIES = SchedulerConstants.WET_ACTIVITIES
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day_slot = defaultdict(dict)
        for e in troop_entries:
            by_day_slot[e.time_slot.day][e.time_slot.slot_number] = e.activity.name
        
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            slots = by_day_slot[day]
            if 1 in slots and 2 in slots and 3 in slots:
                s1_wet = slots[1] in WET_ACTIVITIES
                s2_wet = slots[2] in WET_ACTIVITIES
                s3_wet = slots[3] in WET_ACTIVITIES
                if s1_wet and not s2_wet and s3_wet:
                    soft_violations += 1  # SOFT: Wet pattern
                    soft_violation_details.append(f"{troop.name}: Wet-Dry-Wet pattern on {day.value}")
    
    # NEW: Tower/ODS after wet or wet after Tower/ODS
    TOWER_ODS_ALL = EXCLUSIVE_AREAS.get("Tower", []) + EXCLUSIVE_AREAS.get("Outdoor Skills", [])
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day_slot = defaultdict(dict)
        for e in troop_entries:
            by_day_slot[e.time_slot.day][e.time_slot.slot_number] = e.activity.name
        
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            slots = by_day_slot[day]
            for slot_num in [1, 2]:
                if slot_num in slots and (slot_num + 1) in slots:
                    curr_act = slots[slot_num]
                    next_act = slots[slot_num + 1]
                    # Wet then Tower/ODS
                    if curr_act in WET_ACTIVITIES and next_act in TOWER_ODS_ALL:
                        soft_violations += 1  # SOFT: Strenuous transition
                        soft_violation_details.append(f"{troop.name}: Wet->Tower/ODS transition on {day.value} (Slot {slot_num}->{slot_num+1})")
                    # Tower/ODS then Wet
                    if curr_act in TOWER_ODS_ALL and next_act in WET_ACTIVITIES:
                        soft_violations += 1  # SOFT: Strenuous transition
                        soft_violation_details.append(f"{troop.name}: Tower/ODS->Wet transition on {day.value} (Slot {slot_num}->{slot_num+1})")
    
    # NEW: Same Place Same Day - A troop should never do two activities from the same exclusive area on the same day
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day = defaultdict(set)
        for e in troop_entries:
            by_day[e.time_slot.day].add(e.activity.name)
        
        for day, acts in by_day.items():
            # Check each exclusive area
            for area_name, area_activities in EXCLUSIVE_AREAS.items():
                day_acts_in_area = [act for act in acts if act in area_activities]
                if len(day_acts_in_area) >= 2:
                    # SOFT: Troop has 2+ activities from same area on same day
                    soft_violations += 1
                    soft_violation_details.append(f"{troop.name}: Same area '{area_name}' twice on {day.value}")
                    break  # Count once per day per area
    
    # NEW: Showerhouse before Super Troop or wet activity (same day)
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day_slot = defaultdict(dict)
        for e in troop_entries:
            by_day_slot[e.time_slot.day][e.time_slot.slot_number] = e.activity.name
        
        for day, slots in by_day_slot.items():
            # Check if Showerhouse is in an earlier slot than Super Troop or wet activity
            for slot_num in sorted(slots.keys()):
                if slots[slot_num] == "Shower House":
                    # Check later slots on same day
                    for later_slot in sorted(slots.keys()):
                        if later_slot > slot_num:
                            later_act = slots[later_slot]
                            if later_act == "Super Troop" or later_act in WET_ACTIVITIES:
                                soft_violations += 1  # SOFT: Shower timing
                                soft_violation_details.append(f"{troop.name}: Shower House before {later_act} on {day.value}")
                                break  # Count once per violation
    
    # Accuracy limit: max 1 per day (Rifle, Shotgun, Archery) - includes Rifle+Shotgun
    ACCURACY_ACTIVITIES = ["Troop Rifle", "Troop Shotgun", "Archery"]
    for troop in troops:
        day_acc = defaultdict(set)
        for e in schedule.entries:
            if e.troop == troop and e.activity.name in ACCURACY_ACTIVITIES:
                day_acc[e.time_slot.day].add(e.activity.name)
        for d, acts in day_acc.items():
            if len(acts) >= 2:
                # SOFT: More than 1 accuracy activity on same day
                soft_violations += 1
                soft_violation_details.append(f"{troop.name}: Multiple accuracy activities on {d.value} ({', '.join(acts)})")

    # Exclusive double-book: only one troop per slot for Tower, Rifle, Shotgun, Archery, Delta, Super Troop, Sailing, Gaga Ball, 9 Square
    # This is a HARD constraint - schedule is invalid
    EXCLUSIVE_ONE_TROOP = {"Climbing Tower", "Troop Rifle", "Troop Shotgun", "Archery", "Delta", "Super Troop",
                           "Sailing", "Gaga Ball", "9 Square"}
    slot_activity_count = defaultdict(lambda: defaultdict(int))
    for e in schedule.entries:
        key = (e.time_slot.day, e.time_slot.slot_number)
        slot_activity_count[key][e.activity.name] += 1
    exclusive_double_book = 0
    for (day, slot_num), counts in slot_activity_count.items():
        for act_name, count in counts.items():
            if act_name in EXCLUSIVE_ONE_TROOP and count >= 2:
                exclusive_double_book += (count - 1)  # HARD: violation per extra troop
                hard_violation_details.append(f"Exclusive double-book: {act_name} on {day.value} Slot {slot_num} ({count} troops)")
    hard_violations += exclusive_double_book
    metrics["exclusive_double_book"] = exclusive_double_book
    
    # NEW: Max Beach Staff & Count
    # ----------------------------
    # Max 12 Beach Staff per Slot
    # Max 4 Staffed Beach Activities per Slot
    
    beach_staff_max = config_loader.get_constraints().get("beach_staff_per_slot", 12)
    beach_acts_max = config_loader.get_constraints().get("max_beach_staffed_activities", 4)
    
    beach_staff_violations = 0
    beach_acts_violations = 0
    
    # We need to calculate this per slot
    slot_beach_staff = defaultdict(int)
    slot_beach_acts = defaultdict(int)
    
    for e in schedule.entries:
        if e.activity.name in SchedulerConstants.BEACH_STAFFED_ACTIVITIES:
             # Add staff count
             staff_needed = config_loader.get_staff_need(e.activity.name)
             slot_beach_staff[(e.time_slot.day, e.time_slot.slot_number)] += staff_needed
             slot_beach_acts[(e.time_slot.day, e.time_slot.slot_number)] += 1

    for (day, slot_num), count in slot_beach_staff.items():
        if count > beach_staff_max:
             # HARD? Or Soft? BRAIN says "Capacity Safety" -> Hard?
             # "Capacity Safety" section in BRAIN is under "Hard Constraints" implies logic but let's check.
             # BRAIN: "Capacity Safety ... Global Staff ... Beach Staff". yes, HARD.
             hard_violations += 1
             hard_violation_details.append(f"Beach Staff Overload on {day.value} Slot {slot_num}: {count} > {beach_staff_max}")
             beach_staff_violations += 1

    for (day, slot_num), count in slot_beach_acts.items():
        if count > beach_acts_max:
             hard_violations += 1
             hard_violation_details.append(f"Beach Activity Saturation on {day.value} Slot {slot_num}: {count} > {beach_acts_max}")
             beach_acts_violations += 1

    metrics["beach_staff_violations"] = beach_staff_violations
    metrics["beach_acts_violations"] = beach_acts_violations
    
    # Store hard/soft violation counts and details
    metrics["hard_violations"] = hard_violations
    metrics["soft_violations"] = soft_violations
    metrics["hard_violation_details"] = hard_violation_details
    metrics["soft_violation_details"] = soft_violation_details
    metrics["constraint_violations"] = hard_violations + soft_violations  # Total for backward compat
    metrics["violation_details"] = hard_violation_details + soft_violation_details  # Combined for backward compat

    # 6. Top Preference Success (Innocent Until Proven Guilty Scoring)
    # -------------------------
    # Base Score: 450 (or whatever is in DEFAULT_WEIGHTS)
    # Deductions: For missing Top 14 items (if requested)
    # Bonuses: For hitting Top 15+ items
    
    preference_score = weights.get("preference_base_score", 450.0)
    current_preference_deductions = 0.0
    current_preference_bonuses = 0.0
    
    # Stats tracking
    missing_top5_count = 0
    missing_top10_count = 0
    missing_top14_count = 0
    missing_top15_count = 0
    
    # HC/DG exemption: if all 3 Tuesday slots are HC or DG, missed HC/DG counts as exempt
    tuesday_hc_dg_slots = set()
    for e in schedule.entries:
        if e.time_slot.day == Day.TUESDAY and e.activity.name in ("History Center", "Disc Golf"):
            tuesday_hc_dg_slots.add(e.time_slot.slot_number)
    hc_dg_tuesday_full = tuesday_hc_dg_slots >= {1, 2, 3}
    
    for troop in troops:
        troop_acts = set(e.activity.name for e in schedule.entries if e.troop == troop)
        
        # Check if troop has ANY 3-hour activity scheduled (exemption logic)
        has_3hr_scheduled = any(e.activity.name in ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"] 
                               for e in schedule.entries if e.troop == troop)
        
        # --- NEW: Multi-slot slot consumption calculation ---
        # Calculate how many EXTRA slots are consumed by scheduled activities
        # Standard activity = 1 slot. 
        # Sailing = 1.5 slots (consumes 2). Extra = 1.
        # 3-hour = 3 slots. Extra = 2.
        # Tower (Large) = 2 slots. Extra = 1.
        extra_slots_consumed = 0
        
        # Get all unique particular activity occurrences for this troop 
        # (to avoid counting multi-slot parts twice if schema differs)
        scheduled_activity_names = set(e.activity.name for e in schedule.entries if e.troop == troop)
        
        for act_name in scheduled_activity_names:
            activity = get_activity_by_name(act_name)
            if not activity: continue
            
            # Check for specific multi-slot types
            if activity.name == "Sailing":
                extra_slots_consumed += 1 # 1.5 rounded to 2, so 1 extra
            elif activity.slots == 3:
                extra_slots_consumed += 2 # 3 slots = 2 extra
            elif activity.name == "Climbing Tower" and troop.scouts > 15:
                 # Large troops use 2 slots for Tower
                 extra_slots_consumed += 1
        
        # Initialize exemption counter
        multi_slot_exemptions = extra_slots_consumed

        # Iterate through preferences
        for i, pref_name in enumerate(troop.preferences):
            rank = i + 1
            
            # --- RANKS 1-14: DEDUCTION IF MISSED ---
            if rank <= 14:
                # Determining weight
                weight = 0.0
                if rank <= 5:
                    weight = weights["preference_weights"]["top5"][i]
                elif rank <= 10:
                    weight = weights["preference_weights"]["top6_10"][i-5]
                elif rank <= 14:
                    weight = weights["preference_weights"]["top11_14"][i-10]
                
                if pref_name not in troop_acts:
                    # Check exemptions before deducting
                    is_exempt = False
                    
                    # 1. 3-Hour Mutually Exclusive Exemption (Generalized to all ranks)
                    if pref_name in ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"] and has_3hr_scheduled:
                         is_exempt = True
                         
                    # 2. Tuesday HC/DG Saturation Exemption (Generalized to all ranks)
                    elif pref_name in ("History Center", "Disc Golf") and hc_dg_tuesday_full:
                         is_exempt = True
                    
                    # 3. Multi-slot Consumption Exemption (NEW)
                    # If not already exempt by specific rules, check if pushed out by multi-slot activities
                    if not is_exempt and multi_slot_exemptions > 0:
                        is_exempt = True
                        multi_slot_exemptions -= 1
                        # print(f"DEBUG: Exempting {pref_name} for {troop.name} due to multi-slot consumption. Remaining exemptions: {multi_slot_exemptions}")
                    
                    if not is_exempt:
                        current_preference_deductions += weight
                        # Stats
                        if rank <= 5: missing_top5_count += 1
                        if rank <= 10: missing_top10_count += 1
                        if rank <= 14: missing_top14_count += 1
                        if rank <= 15: missing_top15_count += 1

            # --- RANKS 15-20: BONUS IF HIT ---
            elif rank <= 20:
                # Determining bonus weight
                weight = 0.0
                idx = i - 14
                if idx < len(weights["preference_weights"]["top15_20"]):
                    weight = weights["preference_weights"]["top15_20"][idx]
                
                if pref_name in troop_acts:
                    current_preference_bonuses += weight
                    # No stats for "missing" deep preferences

    # Final calculation
    total_preference_points_accumulated = max(0, preference_score - current_preference_deductions + current_preference_bonuses)

    metrics["preference_points_accumulated"] = total_preference_points_accumulated
    metrics["preference_deductions"] = current_preference_deductions
    metrics["preference_bonuses"] = current_preference_bonuses
    
    metrics["missing_top5"] = missing_top5_count
    metrics["missing_top10"] = missing_top10_count
    metrics["missing_top15"] = missing_top15_count
    
    # Success percentages (Calculated based on requested vs fulfilled)
    # Only count "requested" items in the denominator
    total_top5_requested = sum(min(5, len(t.preferences)) for t in troops)
    total_top10_requested = sum(min(10, len(t.preferences)) for t in troops)
    total_top15_requested = sum(min(15, len(t.preferences)) for t in troops)
    
    metrics["top5_pct"] = 100.0 * (total_top5_requested - missing_top5_count) / max(1, total_top5_requested)
    metrics["top10_pct"] = 100.0 * (total_top10_requested - missing_top10_count) / max(1, total_top10_requested)
    metrics["top15_pct"] = 100.0 * (total_top15_requested - missing_top15_count) / max(1, total_top15_requested)


    # 8. New Metrics: Early Week Bias & Batching
    # ------------------------------------------
    # Early Week: Super Troop / Delta on Mon/Tue
    early_week_count = 0
    TARGET_EARLY_ACTIVITIES = ["Super Troop", "Delta"]
    for e in schedule.entries:
        if e.activity.name in TARGET_EARLY_ACTIVITIES:
            if e.time_slot.day in [Day.MONDAY, Day.TUESDAY]:
                early_week_count += 1
    metrics["early_week_bias"] = early_week_count
    
    # 9. Promoted Pairings Reward (Commissioner/Easy Schedule Days)
    # -------------------------------------------------------------
    # Reward for:
    # - Sailing on same day as Delta (Mon/Tue/Wed)
    # - Rifle on same day as Super Troop (Mon/Tue/Wed)
    promoted_pairing_hits = 0
    
    # Check Delta + Sailing Pairing (Same Day)
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day = defaultdict(set)
        for e in troop_entries:
            by_day[e.time_slot.day].add(e.activity.name)
        
        for day, acts in by_day.items():
            # Pairing 1: Delta + Sailing
            if "Delta" in acts and "Sailing" in acts:
                promoted_pairing_hits += 1
            # Pairing 2: Super Troop + Rifle
            if "Super Troop" in acts and ("Troop Rifle" in acts or "Troop Shotgun" in acts):
                promoted_pairing_hits += 1
                
    metrics["promoted_pairings"] = promoted_pairing_hits

    # Batching: Back-to-back Tie Dye, Rifle, Shotgun (Global Schedule)
    # Check if slot N and N+1 have the same activity (any troop)
    BATCH_TARGETS = ["Tie Dye", "Troop Rifle", "Troop Shotgun"]
    batch_hits = 0
    
    # Organize by activity -> day -> slots
    day_order = {Day.MONDAY: 0, Day.TUESDAY: 1, Day.WEDNESDAY: 2, Day.THURSDAY: 3, Day.FRIDAY: 4}
    
    activity_slots = defaultdict(set)
    for e in schedule.entries:
        if e.activity.name in BATCH_TARGETS:
            activity_slots[e.activity.name].add((e.time_slot.day, e.time_slot.slot_number))
            
    for act_name, slots in activity_slots.items():
        # Sort by day, then slot using explicit order
        slots = sorted(slots, key=lambda x: (day_order.get(x[0], 99), x[1]))
        
        # Check consecutive slots
        for i in range(len(slots) - 1):
            d1, s1 = slots[i]
            d2, s2 = slots[i+1]
            if d1 == d2 and s2 == s1 + 1:
                batch_hits += 1
                
    metrics["activity_batching"] = batch_hits
    
    # Estimate possible batching opportunities based on per-day counts
    batch_possible = 0
    activity_day_slots = defaultdict(lambda: defaultdict(set))
    for e in schedule.entries:
        if e.activity.name in BATCH_TARGETS:
            activity_day_slots[e.activity.name][e.time_slot.day].add(e.time_slot.slot_number)
    for day_slots in activity_day_slots.values():
        for slots in day_slots.values():
            if len(slots) >= 2:
                batch_possible += len(slots) - 1
    metrics["activity_batching_possible"] = batch_possible
    
    # Sailing Full-Day or Empty-Day Bonus
    # Bonus if a troop's sailing day has no other staffed activities
    sailing_full_day = 0
    sailing_days = 0
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day = defaultdict(list)
        for e in troop_entries:
            by_day[e.time_slot.day].append(e)
        for day, entries in by_day.items():
            has_sailing = any(e.activity.name == "Sailing" for e in entries)
            if not has_sailing:
                continue
            sailing_days += 1
            other_staffed = any(
                e.activity.name != "Sailing" and e.activity.name in ALL_STAFF_ACTIVITIES
                for e in entries
            )
            if not other_staffed:
                sailing_full_day += 1
    metrics["sailing_full_day_hits"] = sailing_full_day
    metrics["sailing_full_day_total"] = sailing_days
    
    # Sailing Same-Day Pairing Bonus (2 sails on same day)
    sailing_day_counts = defaultdict(set)
    for e in schedule.entries:
        if e.activity.name == "Sailing":
            sailing_day_counts[e.time_slot.day].add(e.troop.name)
    sailing_days_total = len(sailing_day_counts)
    sailing_days_two = sum(1 for troops_set in sailing_day_counts.values() if len(troops_set) >= 2)
    metrics["sailing_same_day_hits"] = sailing_days_two
    metrics["sailing_same_day_total"] = sailing_days_total

    # 7. Calculate Score (Target: 1000 = perfect)
    # -------------------------------------------
    # Components: Preferences (450) + Cluster (250) + Soft Constraints (150) + Staff (100) + Bonuses (50)
    score_components = {}
    
    # === HARD CONSTRAINT CHECK: Any hard violation = INVALID (-1000) ===
    if metrics.get("hard_violations", 0) > 0:
        score = -1000
        metrics["schedule_invalid"] = True
        metrics["invalid_reason"] = "Hard constraint violation"
        score_components["hard_violation_penalty"] = -1000
        metrics["score_components"] = score_components
        metrics["final_score"] = int(round(score))
        return metrics
    
    # === EMPTY SLOT CHECK: Any gaps = INVALID (-1000) ===
    if metrics["unnecessary_gaps"] > 0:
        score = -1000
        metrics["schedule_invalid"] = True
        metrics["invalid_reason"] = "Empty slots in schedule"
        score_components["gap_penalty"] = -1000
        metrics["score_components"] = score_components
        metrics["final_score"] = int(round(score))
        return metrics
    
    # === Valid schedule - calculate component scores ===
    metrics["schedule_invalid"] = False
    
    # 1. Preferences: ~450 pts (already calculated with new deduction/bonus logic)
    pref_points = metrics.get("preference_points_accumulated", 0.0)
    score_components["preference_points"] = pref_points
    score_components["preference_deductions"] = metrics.get("preference_deductions", 0.0)
    score_components["preference_bonuses"] = metrics.get("preference_bonuses", 0.0)

    
    # 2. Cluster Efficiency: 250 pts (HIGH PRIORITY)
    cluster_points = (
        weights["cluster_efficiency_points"]
        - metrics["excess_cluster_days"] * weights["excess_cluster_day_penalty"]
        - metrics.get("cluster_gaps", 0) * weights["cluster_gap_penalty"]
    )
    score_components["cluster_efficiency_points"] = max(0, cluster_points)
    
    # 3. Soft Constraint Compliance: 150 pts (budget)
    soft_points = (
        weights["soft_constraint_points"]
        - metrics.get("soft_violations", 0) * weights["soft_violation_penalty"]
        - metrics.get("beach_slot_2_uses", 0) * weights["beach_slot_2_penalty"]
    )
    score_components["soft_constraint_points"] = max(0, soft_points)
    
    # 4. Staff Balance: 100 pts
    staff_balance_points = weights["staff_balance_points"]
    staff_balance_points -= metrics["staff_variance"] * weights["staff_variance_penalty"]
    staff_balance_points -= metrics["severe_underused_slots"] * weights["severe_underuse_penalty"]
    staff_balance_points -= metrics["excessive_staff_slots"] * weights["excessive_staff_penalty"]
    score_components["staff_balance_points"] = max(0, staff_balance_points)
    
    # 5. Bonuses: ~50 pts total
    # Early week bias (normalized)
    total_target_early = sum(1 for e in schedule.entries if e.activity.name in TARGET_EARLY_ACTIVITIES)
    metrics["early_week_total"] = total_target_early
    early_week_ratio = (metrics["early_week_bias"] / total_target_early) if total_target_early > 0 else 0
    score_components["early_week_points"] = early_week_ratio * weights["early_week_points"]
    
    # Promoted pairings (normalized)
    max_pairings = len(troops) * 2
    metrics["promoted_pairings_possible"] = max_pairings
    pairing_ratio = (metrics["promoted_pairings"] / max_pairings) if max_pairings > 0 else 0
    score_components["promoted_pairing_points"] = pairing_ratio * weights["promoted_pairing_points"]
    
    # Activity batching (normalized)
    batch_possible = metrics.get("activity_batching_possible", 0)
    batching_ratio = (metrics["activity_batching"] / batch_possible) if batch_possible > 0 else 0
    score_components["activity_batching_points"] = batching_ratio * weights["activity_batching_points"]
    
    # Sailing bonuses (normalized)
    sailing_total = metrics.get("sailing_full_day_total", 0)
    sailing_ratio = (metrics.get("sailing_full_day_hits", 0) / sailing_total) if sailing_total > 0 else 0
    score_components["sailing_full_day_points"] = sailing_ratio * weights["sailing_full_day_points"]
    
    same_day_total = metrics.get("sailing_same_day_total", 0)
    same_day_ratio = (metrics.get("sailing_same_day_hits", 0) / same_day_total) if same_day_total > 0 else 0
    score_components["sailing_same_day_points"] = same_day_ratio * weights["sailing_same_day_points"]
    
    # AT Sharing Bonus: +50 pts if 2 small troops share AT slot
    at_sharing_bonus = 0
    at_slot_troops = defaultdict(list)
    for e in schedule.entries:
        if e.activity.name == "Aqua Trampoline":
            key = (e.time_slot.day, e.time_slot.slot_number)
            troop_size = e.troop.scouts + e.troop.adults
            at_slot_troops[key].append(troop_size)
    for key, sizes in at_slot_troops.items():
        if len(sizes) >= 2 and all(s <= 16 for s in sizes):
            at_sharing_bonus += weights.get("at_sharing_bonus", 50.0)
    score_components["at_sharing_bonus"] = at_sharing_bonus
    metrics["at_sharing_bonus"] = at_sharing_bonus
    
    # Final score
    score = sum(score_components.values())
    metrics["score_components"] = score_components
    metrics["final_score"] = int(round(score))

    return metrics


class EnhancedRegressionChecker:
    """
    ENHANCED Automated regression checker for Summer Camp Scheduler.
    
    This version analyzes the 10 actual week files with comprehensive metrics:
    - Top 5 satisfaction (original)
    - Average week quality scores (NEW)
    - Constraint violations (NEW)
    - Staff efficiency (NEW)
    - Clustering quality (NEW)
    - Beach slot compliance (NEW)
    
    Target files:
    - tc_week1_troops through tc_week8_troops
    - voyageur_week1_troops, voyageur_week3_troops
    """
    
    def __init__(self):
        self.analyzer = UnscheduledAnalyzer()
        self.baseline_file = Path("baseline_metrics_10weeks.json")
        self.current_results = {}
        self.baseline_results = {}
        self.regressions_detected = []
        
        # Only the 10 actual week files
        self.target_weeks = [
            "tc_week1_troops",
            "tc_week2_troops", 
            "tc_week3_troops",
            "tc_week4_troops",
            "tc_week5_troops",
            "tc_week6_troops",
            "tc_week7_troops",
            "tc_week8_troops",
            "voyageur_week1_troops",
            "voyageur_week3_troops"
        ]
    
    def run_full_check(self, schedules_dir: str = "data/schedules") -> Dict[str, Any]:
        """
        Run comprehensive regression check on 10 actual weeks only.
        
        Args:
            schedules_dir: Directory containing schedule JSON files
            
        Returns:
            Complete regression report with comprehensive metrics
        """
        print("ENHANCED Regression Checker - Analyzing 10 Actual Weeks")
        print("=" * 60)
        
        # Analyze current state for target weeks only
        print("Analyzing current schedules...")
        self._analyze_target_weeks(schedules_dir)
        self.current_results = self.analyzer.get_season_summary()
        
        # Add comprehensive quality metrics
        if evaluate_week:
            print("Calculating comprehensive quality metrics...")
            self._add_quality_metrics(schedules_dir)
        
        # Load baseline if exists
        if self.baseline_file.exists():
            print("Loading baseline metrics...")
            with open(self.baseline_file, 'r') as f:
                self.baseline_results = json.load(f)
        
        # Check for regressions
        print("Checking for regressions...")
        self._check_top5_regressions()
        self._check_quality_regressions()
        self._check_multislot_activities(schedules_dir)
        self._check_data_consistency()
        
        # Generate report
        report = self._generate_regression_report()
        
        # Save current results as new baseline if no regressions
        if not self.regressions_detected:
            print("No regressions detected - updating baseline...")
            self._save_baseline()
        
        return report
    
    def _analyze_target_weeks(self, schedules_dir: str):
        """Analyze only the 10 target week files."""
        schedules_path = Path(schedules_dir)
        if not schedules_path.exists():
            raise FileNotFoundError(f"Schedules directory not found: {schedules_dir}")
        
        # Find the schedule files for target weeks
        target_schedule_files = []
        for week_name in self.target_weeks:
            # Look for the exact schedule file
            schedule_file = schedules_path / f"{week_name}_schedule.json"
            if schedule_file.exists():
                target_schedule_files.append(schedule_file)
            else:
                print(f"WARNING: Schedule file not found: {schedule_file}")
        
        print(f"Found {len(target_schedule_files)} target week files")
        
        # Analyze each target week
        for schedule_file in target_schedule_files:
            try:
                analysis = self.analyzer.analyze_week_from_schedule_json(schedule_file)
                self.analyzer.week_analyses[analysis.week_name] = analysis
            except Exception as e:
                print(f"Error analyzing {schedule_file}: {e}")
    
    def _check_top5_regressions(self):
        """Check for Top 5 satisfaction regressions."""
        if not self.baseline_results:
            print("No baseline found - will create new baseline")
            return
        
        current_success = self.current_results.get("season_success_rate", 0)
        baseline_success = self.baseline_results.get("season_success_rate", 0)
        
        # Check for significant drop in Top 5 success rate
        if current_success < baseline_success - 1.0:  # 1% tolerance
            self.regressions_detected.append({
                "type": "Top 5 Success Rate",
                "severity": "HIGH",
                "current": current_success,
                "baseline": baseline_success,
                "change": current_success - baseline_success,
                "description": f"Top 5 success rate dropped from {baseline_success:.1f}% to {current_success:.1f}%"
            })
        
        # Check for increase in counted misses
        current_misses = self.current_results.get("total_counted_misses", 0)
        baseline_misses = self.baseline_results.get("total_counted_misses", 0)
        
        if current_misses > baseline_misses:
            self.regressions_detected.append({
                "type": "Top 5 Missed Activities",
                "severity": "MEDIUM",
                "current": current_misses,
                "baseline": baseline_misses,
                "change": current_misses - baseline_misses,
                "description": f"Top 5 misses increased from {baseline_misses} to {current_misses}"
            })
        
        # Check for new problem weeks
        current_problem_weeks = self.current_results.get("weeks_with_issues", 0)
        baseline_problem_weeks = self.baseline_results.get("weeks_with_issues", 0)
        
        if current_problem_weeks > baseline_problem_weeks:
            self.regressions_detected.append({
                "type": "Problem Weeks",
                "severity": "MEDIUM",
                "current": current_problem_weeks,
                "baseline": baseline_problem_weeks,
                "change": current_problem_weeks - baseline_problem_weeks,
                "description": f"Weeks with Top 5 issues increased from {baseline_problem_weeks} to {current_problem_weeks}"
            })
    
    def _add_quality_metrics(self, schedules_dir: str):
        """Add comprehensive quality metrics using evaluate_week_success."""
        schedules_path = Path(schedules_dir)
        quality_metrics = []
        
        for week_name in self.target_weeks:
            # Find the corresponding troop file
            troop_file = schedules_path.parent / f"{week_name}.json"
            if not troop_file.exists():
                troop_file = schedules_path.parent / "troops" / f"{week_name}.json"
            
            if troop_file.exists():
                try:
                    # Evaluate the week
                    week_result = evaluate_week(str(troop_file))
                    
                    if week_result:
                        quality_metrics.append({
                            "week_name": week_name,
                            "total_score": week_result.get("final_score", 0),
                            "preference_score": week_result.get("score_components", {}).get("preference_points", 0),
                            "constraint_violations": week_result.get("constraint_violations", 0),
                            "staff_variance": week_result.get("staff_variance", 0),
                            "clustering_efficiency": week_result.get("excess_cluster_days", 0),
                            "beach_slot_2_violations": week_result.get("beach_slot_2_uses", 0),
                            "unnecessary_gaps": week_result.get("unnecessary_gaps", 0),
                            "grade": week_result.get("grade", "Unknown"),
                            "violation_details": week_result.get("violation_details", []),
                            "top5_pct": week_result.get("top5_pct", 0),
                            "top10_pct": week_result.get("top10_pct", 0)
                        })
                except Exception as e:
                    print(f"  Warning: Could not evaluate {week_name}: {e}")
        
        # Calculate averages
        if quality_metrics:
            avg_score = sum(m["total_score"] for m in quality_metrics) / len(quality_metrics)
            avg_violations = sum(m["constraint_violations"] for m in quality_metrics) / len(quality_metrics)
            avg_staff_variance = sum(m["staff_variance"] for m in quality_metrics) / len(quality_metrics)
            avg_clustering = sum(m["clustering_efficiency"] for m in quality_metrics) / len(quality_metrics)
            avg_beach_violations = sum(m["beach_slot_2_violations"] for m in quality_metrics) / len(quality_metrics)
            
            self.current_results.update({
                "quality_metrics": {
                    "average_week_score": avg_score,
                    "average_constraint_violations": avg_violations,
                    "average_staff_variance": avg_staff_variance,
                    "average_clustering_efficiency": avg_clustering,
                    "average_beach_slot_violations": avg_beach_violations,
                    "week_details": quality_metrics
                }
            })
            
            print(f"  Average Week Score: {avg_score:.1f}")
            print(f"  Average Constraint Violations: {avg_violations:.1f}")
            print(f"  Average Staff Variance: {avg_staff_variance:.2f}")
            print(f"  Average Clustering Efficiency: {avg_clustering:.2f}")
            print(f"  Average Beach Slot Violations: {avg_beach_violations:.1f}")
    
    def _check_quality_regressions(self):
        """Check for schedule quality regressions."""
        if not self.baseline_results or "quality_metrics" not in self.current_results:
            print("No quality baseline found - will create new baseline")
            return
        
        current_quality = self.current_results["quality_metrics"]
        baseline_quality = self.baseline_results.get("quality_metrics", {})
        
        # Check for significant drop in average week score
        current_score = current_quality.get("average_week_score", 0)
        baseline_score = baseline_quality.get("average_week_score", 0)
        
        if current_score < baseline_score - 5.0:  # 5 point tolerance
            self.regressions_detected.append({
                "type": "Average Week Score",
                "severity": "HIGH",
                "current": current_score,
                "baseline": baseline_score,
                "change": current_score - baseline_score,
                "description": f"Average week score dropped from {baseline_score:.1f} to {current_score:.1f}"
            })
        
        # Check for increase in constraint violations
        current_violations = current_quality.get("average_constraint_violations", 0)
        baseline_violations = baseline_quality.get("average_constraint_violations", 0)
        
        if current_violations > baseline_violations + 0.5:  # 0.5 violation tolerance
            self.regressions_detected.append({
                "type": "Constraint Violations",
                "severity": "HIGH",
                "current": current_violations,
                "baseline": baseline_violations,
                "change": current_violations - baseline_violations,
                "description": f"Constraint violations increased from {baseline_violations:.1f} to {current_violations:.1f}"
            })
        
        # Check for beach slot compliance regression
        current_beach = current_quality.get("average_beach_slot_violations", 0)
        baseline_beach = baseline_quality.get("average_beach_slot_violations", 0)
        
        if current_beach > baseline_beach + 0.5:  # 0.5 violation tolerance
            self.regressions_detected.append({
                "type": "Beach Slot Compliance",
                "severity": "MEDIUM",
                "current": current_beach,
                "baseline": baseline_beach,
                "change": current_beach - baseline_beach,
                "description": f"Beach slot violations increased from {baseline_beach:.1f} to {current_beach:.1f}"
            })
        
        # Check for staff efficiency regression
        current_staff = current_quality.get("average_staff_variance", 0)
        baseline_staff = baseline_quality.get("average_staff_variance", 0)
        
        if current_staff > baseline_staff + 0.2:  # 0.2 variance tolerance
            self.regressions_detected.append({
                "type": "Staff Balance",
                "severity": "MEDIUM",
                "current": current_staff,
                "baseline": baseline_staff,
                "change": current_staff - baseline_staff,
                "description": f"Staff variance increased from {baseline_staff:.2f} to {current_staff:.2f}"
            })
    
    def _check_multislot_activities(self, schedules_dir: str):
        """Check that multi-slot activities have the correct number of slots scheduled."""
        print("Checking multi-slot activities...")
        
        # Activities that should span multiple slots
        # 3 slots: Tamarac Wildlife Refuge, Itasca State Park, Back of the Moon
        # 2 slots: Sailing, Canoe Snorkel, Float for Floats
        THREE_HR = ['Tamarac Wildlife Refuge', 'Itasca State Park', 'Back of the Moon']
        TWO_HR = ['Sailing', 'Canoe Snorkel', 'Float for Floats']
        
        schedules_path = Path(schedules_dir)
        total_issues = 0
        weeks_with_issues = []
        
        for week_name in self.target_weeks:
            schedule_file = schedules_path / f"{week_name}_schedule.json"
            if not schedule_file.exists():
                continue
            
            try:
                with open(schedule_file) as f:
                    data = json.load(f)
            except Exception:
                continue
            
            # Group entries by troop and activity
            troop_activities = {}
            for entry in data.get('entries', []):
                key = (entry['troop_name'], entry['activity_name'])
                if key not in troop_activities:
                    troop_activities[key] = []
                troop_activities[key].append((entry['day'], entry['slot']))
            
            # Check multi-slot activities
            week_issues = 0
            for (troop, activity), slots in troop_activities.items():
                if activity in THREE_HR:
                    expected_slots = 3
                elif activity in TWO_HR:
                    expected_slots = 2
                else:
                    continue
                
                if len(slots) != expected_slots:
                    week_issues += 1
                    total_issues += 1
            
            if week_issues > 0:
                weeks_with_issues.append(week_name)
        
        if total_issues > 0:
            self.regressions_detected.append({
                "type": "Multi-Slot Activities",
                "severity": "HIGH",
                "current": total_issues,
                "baseline": 0,
                "change": total_issues,
                "description": f"Found {total_issues} multi-slot activity issues across {len(weeks_with_issues)} weeks",
                "details": weeks_with_issues
            })
    
    def _check_data_consistency(self):
        """Check for data consistency issues."""
        print("Checking data consistency...")
        
        # Validate unscheduled data against scheduled entries
        for week_name in self.analyzer.week_analyses.keys():
            schedule_path = Path("schedules") / f"{week_name}_schedule.json"
            if schedule_path.exists():
                validation = self.analyzer.validate_against_schedule_entries(week_name, schedule_path)
                discrepancies = validation.get("discrepancies", [])
                
                if discrepancies:
                    self.regressions_detected.append({
                        "type": "Data Consistency",
                        "severity": "HIGH",
                        "week": week_name,
                        "count": len(discrepancies),
                        "description": f"Found {len(discrepancies)} data discrepancies in {week_name}",
                        "details": discrepancies
                    })
    
    def _generate_regression_report(self) -> Dict[str, Any]:
        """Generate comprehensive regression report."""
        report = {
            "timestamp": str(Path().cwd()),
            "summary": {
                "regressions_detected": len(self.regressions_detected),
                "high_severity": len([r for r in self.regressions_detected if r.get("severity") == "HIGH"]),
                "medium_severity": len([r for r in self.regressions_detected if r.get("severity") == "MEDIUM"]),
                "status": "FAILED" if self.regressions_detected else "PASSED"
            },
            "current_metrics": self.current_results,
            "baseline_metrics": self.baseline_results,
            "regressions": self.regressions_detected,
            "detailed_analysis": self.analyzer.get_detailed_miss_report(),
            "target_weeks": self.target_weeks
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("ENHANCED REGRESSION CHECK SUMMARY")
        print("=" * 60)
        
        if self.regressions_detected:
            print(f"REGRESSIONS DETECTED: {len(self.regressions_detected)}")
            print(f"   High Severity: {report['summary']['high_severity']}")
            print(f"   Medium Severity: {report['summary']['medium_severity']}")
            print("\nREGRESSION DETAILS:")
            for i, regression in enumerate(self.regressions_detected, 1):
                severity_emoji = "HIGH" if regression.get("severity") == "HIGH" else "MEDIUM"
                print(f"   {i}. {severity_emoji} {regression['type']}: {regression['description']}")
                if 'details' in regression:
                    print(f"      Details: {regression['details']}")
        else:
            print("NO REGRESSIONS DETECTED")
            print(f"   Top 5 Success Rate: {self.current_results.get('season_success_rate', 0):.1f}%")
            print(f"   Total Top 5 Misses: {self.current_results.get('total_counted_misses', 0)}")
            
            # Show quality metrics if available
            if "quality_metrics" in self.current_results:
                quality = self.current_results["quality_metrics"]
                print(f"   Average Week Score: {quality.get('average_week_score', 0):.1f}")
                print(f"   Average Constraint Violations: {quality.get('average_constraint_violations', 0):.1f}")
                print(f"   Average Beach Slot Violations: {quality.get('average_beach_slot_violations', 0):.1f}")
                print(f"   Average Staff Variance: {quality.get('average_staff_variance', 0):.2f}")
        
        print("=" * 60)
        
        # Print per-week metrics table
        self._print_week_table()
        
        return report
    
    def _print_week_table(self):
        """Print a formatted table of per-week metrics."""
        quality = self.current_results.get("quality_metrics", {})
        week_details = quality.get("week_details", [])
        if not week_details:
            return
        
        print("\n" + "=" * 90)
        print("PER-WEEK EVALUATION SUMMARY")
        print("=" * 90)
        print(f"{'Week':<22} | {'Score':<6} | {'Top5%':<6} | {'Top10%':<6} | {'Viol':<5} | {'StVar':<5} | {'Clust':<5}")
        print("-" * 90)
        
        for w in sorted(week_details, key=lambda x: x['week_name']):
            print(f"{w['week_name']:<22} | {w.get('total_score',0):<6} | {w.get('top5_pct',0):<6.1f} | {w.get('top10_pct',0):<6.1f} | {w.get('constraint_violations',0):<5} | {w.get('staff_variance',0):<5.2f} | {w.get('clustering_efficiency',0):<5}")
        
        print("=" * 90)
    
    def print_violation_details(self, max_per_week: int = 10):
        """Print detailed violation messages for each week."""
        quality = self.current_results.get("quality_metrics", {})
        week_details = quality.get("week_details", [])
        if not week_details:
            print("No violation details available.")
            return
        
        print("\n" + "=" * 60)
        print("VIOLATION DETAILS BY WEEK")
        print("=" * 60)
        
        for w in sorted(week_details, key=lambda x: x['week_name']):
            violations = w.get('violation_details', [])
            if violations:
                print(f"\n--- {w['week_name']} ({len(violations)} violations) ---")
                for v in violations[:max_per_week]:
                    print(f"  - {v}")
                if len(violations) > max_per_week:
                    print(f"  ... and {len(violations) - max_per_week} more")
            else:
                print(f"\n--- {w['week_name']} (0 violations) ---")
    
    def _save_baseline(self):
        """Save current results as new baseline."""
        baseline_data = {
            "timestamp": str(Path().cwd()),
            "season_success_rate": self.current_results.get("season_success_rate", 0),
            "total_top5_slots": self.current_results.get("total_top5_slots", 0),
            "total_exempt_misses": self.current_results.get("total_exempt_misses", 0),
            "total_counted_misses": self.current_results.get("total_counted_misses", 0),
            "weeks_with_issues": self.current_results.get("weeks_with_issues", 0),
            "week_details": self.current_results.get("week_details", {}),
            "target_weeks": self.target_weeks,
            "quality_metrics": self.current_results.get("quality_metrics", {})
        }
        
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
    
    def get_top5_detailed_report(self) -> Dict[str, Any]:
        """Get detailed Top 5 analysis report."""
        return self.analyzer.get_detailed_miss_report()
    
    def set_baseline(self, force: bool = False):
        """
        Manually set current results as baseline.
        
        Args:
            force: Force overwrite existing baseline
        """
        if self.baseline_file.exists() and not force:
            print("Baseline already exists. Use force=True to overwrite.")
            return False
        
        if not self.current_results:
            print("No current results to set as baseline. Run check first.")
            return False
        
        self._save_baseline()
        print("Baseline updated successfully.")
        return True


def main():
    """Main entry point for enhanced regression checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ENHANCED Summer Camp Scheduler Regression Checker")
    parser.add_argument("--schedules-dir", default="data/schedules", help="Schedules directory")
    parser.add_argument("--set-baseline", action="store_true", help="Set current results as baseline")
    parser.add_argument("--force-baseline", action="store_true", help="Force overwrite baseline")
    parser.add_argument("--detailed", action="store_true", help="Show detailed Top 5 analysis")
    parser.add_argument("--show-violations", action="store_true", help="Show all constraint violation details")
    
    args = parser.parse_args()
    
    checker = EnhancedRegressionChecker()
    
    # Use absolute path from script directory parent
    project_root = Path(__file__).resolve().parent.parent
    schedules_dir = project_root / args.schedules_dir
    
    if args.set_baseline or args.force_baseline:
        # Run analysis first
        checker._analyze_target_weeks(str(schedules_dir))
        checker.current_results = checker.analyzer.get_season_summary()
        if evaluate_week:
            checker._add_quality_metrics(str(schedules_dir))
        checker.set_baseline(force=args.force_baseline)
        return 0
    
    # Run full regression check
    report = checker.run_full_check(str(schedules_dir))
    
    # Show detailed report if requested
    if args.detailed:
        print("\nDETAILED TOP 5 ANALYSIS:")
        detailed = checker.get_top5_detailed_report()
        for week_name, week_data in detailed.items():
            print(f"\n--- {week_name} ---")
            print(f"Success Rate: {week_data['week_success_rate']:.1f}%")
            print(f"Counted Misses: {week_data['counted_misses']}")
            if week_data['missed_activities']:
                print("Missed Activities:")
                for miss in week_data['missed_activities']:
                    print(f"  - {miss['troop']}: {miss['activity']} (Top #{miss['rank']})")
                    if miss['placement_suggestions']:
                        suggestions = ', '.join(miss['placement_suggestions'][:2])
                        # Replace unicode characters with ASCII
                        suggestions = suggestions.replace('≤', '<=').replace('≥', '>=')
                        print(f"    Suggestions: {suggestions}")
    
    # Show violation details if requested
    if args.show_violations:
        checker.print_violation_details()
    
    # Exit with error code if regressions detected
    return 1 if report["summary"]["regressions_detected"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
