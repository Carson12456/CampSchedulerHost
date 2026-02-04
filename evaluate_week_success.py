"""
Week Success Evaluator
Evaluates a week's schedule based on specific success criteria:
1. Excess days for clustered activities
2. Unnecessary gaps (Slot 1 & 3 full, Slot 2 empty)
3. Staff distribution consistency (Variance)
4. Underused slots (Excessive & Severe)
5. Constraint violations
6. Top 5/10/15 preference success
7. Weighted Scored System
"""

import sys
import math
from collections import defaultdict
import glob
import os
import json

from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities
from io_handler import load_troops_from_json, load_schedule_from_json
from models import Day, TimeSlot, EXCLUSIVE_AREAS, generate_time_slots

# --- Configuration for Scoring (0-1000 perfect, can go negative) ---
DEFAULT_WEIGHTS = {
    "max_score": 1000.0,

    # Points for desired outcomes (sum to ~1000 at perfection)
    # COMPRESSED: Scaled by ~0.135 to achieve ~450 max for preferences (11 troops)
    # Ratios preserved: Top 1 = 2x Top 5, gradual then steep decline
    "preference_points": {
        "top5": [5.4, 4.7, 4.1, 3.4, 2.7],       # Ranks 1-5 (Mandatory) - Sum: 20.3/troop
        "top6_10": [2.6, 2.4, 2.3, 2.2, 2.0],    # Ranks 6-10 (Gradual) - Sum: 11.5/troop
        "top11_15": [1.8, 1.6, 1.4, 1.2, 1.0],   # Ranks 11-15 - Sum: 7.0/troop
        "top16_20": [0.8, 0.6, 0.4, 0.2, 0.0]    # Ranks 16-20 - Sum: 2.0/troop
    },
    # Total per troop: 40.8 pts -> 11 troops = ~449 pts max
    
    "constraint_compliance_points": 200.0,
    "gap_points": 120.0,
    "staff_balance_points": 130.0,
    "cluster_efficiency_points": 40.0,
    "early_week_points": 10.0,
    "activity_batching_points": 10.0,
    "promoted_pairing_points": 10.0,
    "sailing_full_day_points": 10.0,
    "sailing_same_day_points": 20.0,
    # Bonus categories: 550 pts -> Total: 449 + 550 = ~999 pts

    # Penalties (scaled proportionally)
    "excess_cluster_day_penalty": 2.0,     # Scaled from 15
    "unnecessary_gap_penalty": 1.0,        # Scaled from 8
    "cluster_gap_penalty": 1.6,            # Scaled from 12
    "staff_variance_penalty": 1.0,         # Scaled from 8
    "severe_underuse_penalty": 1.3,        # Scaled from 10
    "excessive_staff_penalty": 0.7,        # Scaled from 5
    "constraint_violation_penalty": 3.4,   # Scaled from 25
    "top5_miss_penalty": 3.2,              # Scaled from 24
    "beach_slot_2_penalty": 5.0            # Per beach activity in slot 2 (non-Thu): worse than slot 1/3, better than missing Top 5
}


# Staffed Activity Definition
STAFF_MAP = {
    'Beach Staff': ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                   'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                   'Troop Swim', 'Water Polo', 'Sailing'], # Added Sailing
    'Tower Director': ['Climbing Tower'],
    'Rifle Director': ['Troop Rifle', 'Troop Shotgun'],
    'ODS Director': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                    'Ultimate Survivor', "What's Cooking", 'Chopped!'],
    'Handicrafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"],
    'Nature': ['Dr. DNA', 'Loon Lore', 'Nature Canoe'],
    'Archery': ['Archery']
}
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
    schedule_file = os.path.join("schedules", f"{week_basename}_schedule.json")
    
    if os.path.exists(schedule_file):
        print(f"Loading existing schedule from {schedule_file}...")
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
    
    # 5. Constraint Violations
    # ------------------------
    violations = 0
    
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
                            violations += 1  # AT slot 2 requires exclusive (17+)
                    # else: Top 5 other beach - no violation (relaxation applies)
                else:
                    violations += 1  # Not Top 5 - violation
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
                        violations += 1
                        break
                else:
                    continue
                break

    # Friday Reflection Missing
    for t in troops:
        has_ref = any(e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY 
                     for e in schedule.entries if e.troop == t)
        if not has_ref:
            violations += 1
    
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
                violations += 1
    
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
                violations += 1
    
    # NEW: Wet-Dry-Wet Pattern (Slot 1 wet, Slot 2 dry, Slot 3 wet)
    WET_ACTIVITIES = ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                      'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                      'Troop Swim', 'Water Polo', 'Sailing']
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
                    violations += 1
    
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
                        violations += 1
                    # Tower/ODS then Wet
                    if curr_act in TOWER_ODS_ALL and next_act in WET_ACTIVITIES:
                        violations += 1
    
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
                    # Troop has 2+ activities from same area on same day - violation
                    violations += 1
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
                                violations += 1
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
                # More than 1 accuracy activity on same day - violation
                violations += 1

    # Exclusive double-book: only one troop per slot for Tower, Rifle, Shotgun, Archery, Delta, Super Troop, Sailing, Gaga Ball, 9 Square
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
                exclusive_double_book += (count - 1)  # violation per extra troop
    violations += exclusive_double_book
    metrics["exclusive_double_book"] = exclusive_double_book
            
    metrics["constraint_violations"] = violations

    # 6. Top Preference Success (Exponential Decay Scoring)
    # -------------------------
    total_preference_points_accumulated = 0.0
    missing_top5_count = 0
    missing_top10_count = 0
    missing_top15_count = 0
    missing_top20_count = 0
    
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
        
        # Iterate through ALL top 20 preferences to assign points
        # Only check up to 20; if list is shorter, loop handles it
        for i, pref_name in enumerate(troop.preferences[:20]):
            rank = i + 1
            
            # Determine points for this rank
            points_for_hit = 0.0
            if rank <= 5:
                points_for_hit = weights["preference_points"]["top5"][i] # i=0 is rank 1
            elif rank <= 10:
                points_for_hit = weights["preference_points"]["top6_10"][i-5]
            elif rank <= 15:
                points_for_hit = weights["preference_points"]["top11_15"][i-10]
            elif rank <= 20:
                points_for_hit = weights["preference_points"]["top16_20"][i-15]
            
            if pref_name in troop_acts:
                total_preference_points_accumulated += points_for_hit
            else:
                # Count missing by tier
                if rank <= 5:
                    missing_top5_count += 1
                if rank <= 10:
                    missing_top10_count += 1
                if rank <= 15:
                    missing_top15_count += 1
                if rank <= 20:
                    missing_top20_count += 1
                # Handle Top 5 Penalties & Exemptions
                if rank <= 5:
                    is_exempt = False
                    if pref_name in ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"] and has_3hr_scheduled:
                        is_exempt = True
                    elif pref_name in ("History Center", "Disc Golf") and hc_dg_tuesday_full:
                        is_exempt = True
                    if is_exempt:
                        total_preference_points_accumulated += points_for_hit
                        missing_top5_count -= 1  # Exempt doesn't count as miss
                        missing_top10_count -= 1
                        missing_top15_count -= 1
                        missing_top20_count -= 1
    
    metrics["preference_points_accumulated"] = total_preference_points_accumulated
    metrics["missing_top5"] = missing_top5_count
    metrics["missing_top10"] = missing_top10_count
    metrics["missing_top15"] = missing_top15_count
    metrics["missing_top20"] = missing_top20_count
    
    # Success percentages
    total_top5 = sum(min(5, len(t.preferences)) for t in troops)
    total_top10 = sum(min(10, len(t.preferences)) for t in troops)
    total_top15 = sum(min(15, len(t.preferences)) for t in troops)
    total_top20 = sum(min(20, len(t.preferences)) for t in troops)
    metrics["top5_pct"] = 100.0 * (total_top5 - missing_top5_count) / max(1, total_top5)
    metrics["top10_pct"] = 100.0 * (total_top10 - missing_top10_count) / max(1, total_top10)
    metrics["top15_pct"] = 100.0 * (total_top15 - missing_top15_count) / max(1, total_top15)
    metrics["top20_pct"] = 100.0 * (total_top20 - missing_top20_count) / max(1, total_top20)


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

    # 7. Calculate Score (0-1000 perfect, can go negative)
    # ----------------------------------------------------
    score_components = {}
    
    # Preferences (summed points from exponential decay - penalty for missed Top 5)
    pref_points = (
        metrics.get("preference_points_accumulated", 0.0)
        - metrics["missing_top5"] * weights["top5_miss_penalty"]
    )
    score_components["preference_points"] = pref_points
    
    # Constraint compliance (includes exclusive double-book and beach slot 2 penalty)
    constraint_points = (
        weights["constraint_compliance_points"]
        - metrics["constraint_violations"] * weights["constraint_violation_penalty"]
        - metrics.get("beach_slot_2_uses", 0) * weights.get("beach_slot_2_penalty", 5.0)
    )
    score_components["constraint_points"] = constraint_points
    
    # Gaps - CRITICAL: Any gaps completely invalidate the schedule
    if metrics["unnecessary_gaps"] > 0 or metrics.get("cluster_gaps", 0) > 0:
        gap_points = -1000  # Complete invalidation for any gaps
    else:
        gap_points = (
            weights["gap_points"]
            - metrics["unnecessary_gaps"] * weights["unnecessary_gap_penalty"]
            - metrics.get("cluster_gaps", 0) * weights["cluster_gap_penalty"]
        )
    score_components["gap_points"] = gap_points
    
    # Staff balance
    staff_balance_points = weights["staff_balance_points"]
    staff_balance_points -= metrics["staff_variance"] * weights["staff_variance_penalty"]
    staff_balance_points -= metrics["severe_underused_slots"] * weights["severe_underuse_penalty"]
    staff_balance_points -= metrics["excessive_staff_slots"] * weights["excessive_staff_penalty"]
    score_components["staff_balance_points"] = staff_balance_points
    
    # Cluster efficiency
    cluster_points = (
        weights["cluster_efficiency_points"]
        - metrics["excess_cluster_days"] * weights["excess_cluster_day_penalty"]
    )
    score_components["cluster_efficiency_points"] = cluster_points
    
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
    
    # Sailing full-day/empty-day bonus (normalized)
    sailing_total = metrics.get("sailing_full_day_total", 0)
    sailing_ratio = (metrics.get("sailing_full_day_hits", 0) / sailing_total) if sailing_total > 0 else 0
    score_components["sailing_full_day_points"] = sailing_ratio * weights["sailing_full_day_points"]
    
    # Sailing same-day bonus (normalized)
    same_day_total = metrics.get("sailing_same_day_total", 0)
    same_day_ratio = (metrics.get("sailing_same_day_hits", 0) / same_day_total) if same_day_total > 0 else 0
    score_components["sailing_same_day_points"] = same_day_ratio * weights["sailing_same_day_points"]
    
    score = sum(score_components.values())
    # Invalidate schedule when exclusive double-book (e.g. two troops in Tower same slot)
    if metrics.get("exclusive_double_book", 0) > 0:
        score = min(score, -500)  # Force score to at most -500 so week is clearly invalid
        metrics["schedule_invalid"] = True
    else:
        metrics["schedule_invalid"] = False
    metrics["score_components"] = score_components
    metrics["final_score"] = int(round(score))

    return metrics

def print_metrics(week_name, metrics):
    print(f"\n--- EVALUATION: {week_name} ---")
    print(f"Final Score: {metrics['final_score']}")
    print("-" * 30)
    print(f"Excess Cluster Days:     {metrics['excess_cluster_days']}")
    print(f"Unnecessary Gaps (1-x-3):{metrics['unnecessary_gaps']}")
    print(f"Staff Variance:          {metrics['staff_variance']:.2f}")
    print(f"Slots Issues:            Severe Underuse (<5)={metrics['severe_underused_slots']}, Excessive Staff (>14)={metrics['excessive_staff_slots']}")
    print(f"Constraint Violations:   {metrics['constraint_violations']}")
    if metrics.get("exclusive_double_book", 0) > 0:
        print(f"  (Exclusive double-book: {metrics['exclusive_double_book']} - invalid)")
    if metrics.get("beach_slot_2_uses", 0) > 0:
        print(f"Beach Slot 2 Uses:       {metrics['beach_slot_2_uses']} (penalized)")
    print(f"Top 5 Missed (Total):    {metrics['missing_top5']}")
    print(f"Top 5 Success:           {metrics.get('top5_pct', 0):.1f}%")
    print(f"Cluster Gaps (1-3-2):    {metrics.get('cluster_gaps', 0)}")
    print(f"Top 10 Success:          {metrics.get('top10_pct', 0):.1f}%")
    print(f"Top 15 Success:          {metrics.get('top15_pct', 0):.1f}%")
    print(f"Top 20 Success:          {metrics.get('top20_pct', 0):.1f}%")
    print(f"Early Week Bonus:        {metrics['early_week_bias']} (Super Troop/Delta on Mon/Tue)")
    print(f"Batching Bonus:          {metrics['activity_batching']} (Back-to-back Rifle/Shotgun/Tie Dye)")
    print(f"Promoted Pairings:       {metrics['promoted_pairings']} (Delta+Sailing, ST+Rifle)")
    print(f"Sailing Full-Day Bonus:  {metrics.get('sailing_full_day_hits', 0)}/{metrics.get('sailing_full_day_total', 0)}")
    print(f"Sailing Same-Day Bonus:  {metrics.get('sailing_same_day_hits', 0)}/{metrics.get('sailing_same_day_total', 0)}")
    if "score_components" in metrics:
        sc = metrics["score_components"]
        print("-" * 30)
        print("Score Breakdown (max 1000):")
        print(f"Preferences:             {sc.get('preference_points', 0):.1f}")
        print(f"Constraint Compliance:   {sc.get('constraint_points', 0):.1f}")
        print(f"Schedule Gaps:           {sc.get('gap_points', 0):.1f}")
        print(f"Staff Balance:           {sc.get('staff_balance_points', 0):.1f}")
        print(f"Cluster Efficiency:      {sc.get('cluster_efficiency_points', 0):.1f}")
        print(f"Early Week Bias:          {sc.get('early_week_points', 0):.1f}")
        print(f"Activity Batching:       {sc.get('activity_batching_points', 0):.1f}")
        print(f"Promoted Pairings:       {sc.get('promoted_pairing_points', 0):.1f}")
        print(f"Sailing Full-Day:        {sc.get('sailing_full_day_points', 0):.1f}")
        print(f"Sailing Same-Day:        {sc.get('sailing_same_day_points', 0):.1f}")
    print("-" * 30)

if __name__ == "__main__":
    week_files = glob.glob("tc_week*.json") + glob.glob("voyageur_week*.json")
    
    all_metrics = []
    output_lines = []
    
    for w in sorted(week_files):
        m = evaluate_week(w)
        m['week'] = w
        all_metrics.append(m)
        
        # Capture output for file
        output_lines.append(f"\n--- EVALUATION: {w} ---")
        output_lines.append(f"Final Score: {m['final_score']}")
        output_lines.append("-" * 30)
        output_lines.append(f"Excess Cluster Days:     {m['excess_cluster_days']}")
        output_lines.append(f"Unnecessary Gaps (1-x-3):{m['unnecessary_gaps']}")
        output_lines.append(f"Staff Variance:          {m['staff_variance']:.2f}")
        output_lines.append(f"Slots Issues:            Severe Underuse (<5)={m['severe_underused_slots']}, Excessive Staff (>14)={m['excessive_staff_slots']}")
        output_lines.append(f"Constraint Violations:   {m['constraint_violations']}")
        if m.get("exclusive_double_book", 0) > 0:
            output_lines.append(f"  (Exclusive double-book: {m['exclusive_double_book']} - invalid)")
        if m.get("beach_slot_2_uses", 0) > 0:
            output_lines.append(f"Beach Slot 2 Uses:       {m['beach_slot_2_uses']} (penalized)")
        output_lines.append(f"Top 5 Missed (Total):    {m['missing_top5']}")
        output_lines.append(f"Top 5 Success:           {m.get('top5_pct', 0):.1f}%")
        output_lines.append(f"Cluster Gaps (1-3-2):    {m.get('cluster_gaps', 0)}")
        output_lines.append(f"Top 10 Success:          {m.get('top10_pct', 0):.1f}%")
        output_lines.append(f"Top 15 Success:          {m.get('top15_pct', 0):.1f}%")
        output_lines.append(f"Top 20 Success:          {m.get('top20_pct', 0):.1f}%")
        output_lines.append(f"Early Week Bonus:        {m['early_week_bias']}")
        output_lines.append(f"Batching Bonus:          {m['activity_batching']}")
        output_lines.append(f"Sailing Full-Day Bonus:  {m.get('sailing_full_day_hits', 0)}/{m.get('sailing_full_day_total', 0)}")
        output_lines.append(f"Sailing Same-Day Bonus:  {m.get('sailing_same_day_hits', 0)}/{m.get('sailing_same_day_total', 0)}")
        if "score_components" in m:
            sc = m["score_components"]
            output_lines.append("-" * 30)
            output_lines.append("Score Breakdown (max 1000):")
            output_lines.append(f"Preferences:             {sc.get('preference_points', 0):.1f}")
            output_lines.append(f"Constraint Compliance:   {sc.get('constraint_points', 0):.1f}")
            output_lines.append(f"Schedule Gaps:           {sc.get('gap_points', 0):.1f}")
            output_lines.append(f"Staff Balance:           {sc.get('staff_balance_points', 0):.1f}")
            output_lines.append(f"Cluster Efficiency:      {sc.get('cluster_efficiency_points', 0):.1f}")
            output_lines.append(f"Early Week Bias:          {sc.get('early_week_points', 0):.1f}")
            output_lines.append(f"Activity Batching:       {sc.get('activity_batching_points', 0):.1f}")
            output_lines.append(f"Promoted Pairings:       {sc.get('promoted_pairing_points', 0):.1f}")
            output_lines.append(f"Sailing Full-Day:        {sc.get('sailing_full_day_points', 0):.1f}")
            output_lines.append(f"Sailing Same-Day:        {sc.get('sailing_same_day_points', 0):.1f}")
        output_lines.append("-" * 30)
        
        # Print to console too
        print_metrics(w, m)
        
    avg_score = sum(m['final_score'] for m in all_metrics) / len(all_metrics) if all_metrics else 0
    summary_line = f"\nAverage Season Score: {avg_score:.1f}"
    output_lines.append(summary_line)
    print(summary_line)
    
    with open("evaluation_summary.txt", "w") as f:
        f.write("\n".join(output_lines))
    
    print("\nReport saved to evaluation_summary.txt")
