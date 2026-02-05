"""
Schedule Quality Report Generator (Item 15)
Generates comprehensive analysis of schedule quality after generation.

Metrics:
- Preference Satisfaction (Raw + Adjusted + Weighted)
- Wet/Dry Constraint Violations
- Dry Days Tracking
- Staff Clustering (Smart evaluation + Non-consecutive)
- Staff Load Variance (Exponential)
- Commissioner Load Balance
"""
import sys
import math
from collections import defaultdict
from constrained_scheduler import ConstrainedScheduler
from activities import get_all_activities
from io_handler import load_troops_from_json
from models import Day


# Constants from ConstrainedScheduler
THREE_HOUR_ACTIVITIES = ["Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"]
WET_ACTIVITIES = [
    "Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", "Underwater Obstacle Course",
    "Troop Canoe", "Troop Kayak", "Canoe Snorkel", "Nature Canoe", "Float for Floats", "Sailing", "Sauna"
]
TOWER_ODS_ACTIVITIES = [
    "Climbing Tower", "Knots and Lashings", "Orienteering", "GPS & Geocaching",
    "Ultimate Survivor", "What's Cooking", "Chopped!"
]
MAJOR_WET_BEACH = ["Water Polo", "Aqua Trampoline", "Greased Watermelon"]

# Sailing capacity: 2 sessions/day × 4 days (Mon-Thu, Fri only 1 slot) = ~8 slots/week
SAILING_CAPACITY = 8


def generate_quality_report(week_file, output_file=None):
    """Generate a comprehensive schedule quality report."""
    troops = load_troops_from_json(week_file)
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    schedule = scheduler.schedule_all()
    
    report_lines = []
    
    # Header
    report_lines.append("="*70)
    report_lines.append(f"SCHEDULE QUALITY REPORT: {week_file}")
    report_lines.append("="*70)
    report_lines.append("")
    
    # =========================================================================
    # Section 1: PREFERENCE SATISFACTION (Raw + Adjusted + Weighted)
    # =========================================================================
    report_lines.append("PREFERENCE SATISFACTION")
    report_lines.append("-"*70)
    
    # Count how many troops want sailing (for capacity check)
    sailing_demand = sum(1 for t in troops if "Sailing" in t.preferences[:10])
    sailing_full = sailing_demand > SAILING_CAPACITY
    
    # Detect capacity-constrained activities (exclusive areas that are "full")
    # An activity is capacity-constrained if demand significantly exceeds scheduled instances
    from models import EXCLUSIVE_AREAS
    activity_demand = defaultdict(int)  # How many troops want each activity
    activity_scheduled = defaultdict(int)  # How many times each activity was scheduled
    
    for troop in troops:
        for pref in troop.preferences[:10]:  # Only consider Top 10
            activity_demand[pref] += 1
    
    for entry in schedule.entries:
        activity_scheduled[entry.activity.name] += 1
    
    # Identify capacity-constrained activities (demand > scheduled * 1.5 for exclusive activities)
    capacity_constrained = set()
    for activity_name in activity_demand:
        demand = activity_demand[activity_name]
        scheduled = activity_scheduled[activity_name]
        
        # Check if this activity is in an exclusive area
        is_exclusive = False
        for area_name, area_activities in EXCLUSIVE_AREAS.items():
            if activity_name in area_activities:
                is_exclusive = True
                break
        
        # If exclusive and demand significantly exceeds availability, mark as capacity-constrained
        if is_exclusive and demand > scheduled * 1.3 and scheduled < demand:
            capacity_constrained.add(activity_name)
    
    # Calculate raw and adjusted stats
    raw_stats = {'top5': [0, 0], 'top10': [0, 0]}
    adj_stats = {'top5': [0, 0], 'top10': [0, 0]}
    weighted_score = 0
    weighted_max = 0
    
    # Track missing activities for adjusted counts
    missing_top5 = []  # List of (troop, activity, rank) tuples
    missing_top10 = []  # List of (troop, activity, rank) tuples
    capacity_excluded_activities = defaultdict(int)  # Track how many exclusions per activity
    
    for troop in troops:
        activities = set(e.activity.name for e in schedule.entries if e.troop == troop)
        
        # Count 3-hour activities in preferences
        three_hour_in_prefs = [p for p in troop.preferences if p in THREE_HOUR_ACTIVITIES]
        
        for idx, tier in [(5, 'top5'), (10, 'top10')]:
            prefs = troop.preferences[:idx] if len(troop.preferences) >= idx else troop.preferences
            prefs_set = set(prefs)
            
            # Raw count
            achieved = len(prefs_set & activities)
            raw_stats[tier][0] += achieved
            raw_stats[tier][1] += len(prefs_set)
            
            # Adjusted count (exclude unfixable)
            unfixable_set = set()
            for i, p in enumerate(prefs):
                # Exclude 2nd+ three-hour activities
                if p in THREE_HOUR_ACTIVITIES:
                    earlier_3hr = [x for x in prefs[:i] if x in THREE_HOUR_ACTIVITIES]
                    if earlier_3hr:
                        unfixable_set.add(p)
                        continue
                # Exclude sailing when capacity exceeded (only for unscheduled)
                if p == "Sailing" and sailing_full and p not in activities:
                    unfixable_set.add(p)
                # Exclude Shotgun for large troops (>15) when NOT in Top 5
                if p == "Troop Shotgun" and (troop.scouts + troop.adults) > 15:
                    if "Troop Shotgun" not in troop.preferences[:5] and p not in activities:
                        unfixable_set.add(p)
                # NEW: Exclude capacity-constrained activities (didn't get it = truly full)
                if p in capacity_constrained and p not in activities:
                    unfixable_set.add(p)
                    capacity_excluded_activities[p] += 1
            
            # Track missing activities (adjusted - excludes unfixable)
            for p in prefs:
                if p not in activities and p not in unfixable_set:
                    if tier == 'top5':
                        missing_top5.append((troop.name, p, troop.preferences.index(p) + 1))
                    else:
                        missing_top10.append((troop.name, p, troop.preferences.index(p) + 1))
            
            adj_stats[tier][0] += achieved
            adj_stats[tier][1] += len(prefs_set) - len(unfixable_set)
        
        # Weighted preference score (Top 1=10, Top 2=9, ... Top 10=1)
        for i, pref in enumerate(troop.preferences[:10]):
            points = 10 - i  # Top 1=10, Top 10=1
            weighted_max += points
            if pref in activities:
                weighted_score += points
    
    # Print raw stats
    for tier, label in [('top5', 'Top 5'), ('top10', 'Top 10')]:
        achieved, total = raw_stats[tier]
        pct = (achieved / total * 100) if total > 0 else 0
        status = "[OK]" if (tier == 'top5' and pct >= 90) or (tier == 'top10' and pct >= 80) else "[WARN]"
        report_lines.append(f"  {label:10s} (Raw)     {pct:5.1f}% ({achieved:3d}/{total:3d}) {status}")
    
    # Print adjusted stats
    for tier, label in [('top5', 'Top 5'), ('top10', 'Top 10')]:
        achieved, total = adj_stats[tier]
        pct = (achieved / total * 100) if total > 0 else 0
        status = "[OK]" if (tier == 'top5' and pct >= 95) or (tier == 'top10' and pct >= 85) else "[WARN]"
        report_lines.append(f"  {label:10s} (Adj)     {pct:5.1f}% ({achieved:3d}/{total:3d}) {status}")
    
    # Print weighted score
    weighted_pct = (weighted_score / weighted_max * 100) if weighted_max > 0 else 0
    status = "[OK]" if weighted_pct >= 75 else "[WARN]"
    report_lines.append(f"  Weighted Score       {weighted_pct:5.1f}% ({weighted_score:3d}/{weighted_max:3d}) {status}")
    
    # Show capacity-excluded activities
    if capacity_excluded_activities:
        report_lines.append("")
        report_lines.append("  [NOTE] Capacity-Constrained Activities (excluded from adjusted %):")
        for activity, count in sorted(capacity_excluded_activities.items(), key=lambda x: -x[1]):
            demand = activity_demand[activity]
            scheduled = activity_scheduled[activity]
            report_lines.append(f"    {activity}: {count} troops excluded (demand={demand}, scheduled={scheduled})")

    if sailing_full:
        report_lines.append(f"  [NOTE] Sailing over-capacity: {sailing_demand} troops want it, {SAILING_CAPACITY} slots available")
    
    # Print missing activities from adjusted counts
    if missing_top5:
        report_lines.append("")
        report_lines.append("  Missing Top 5 Activities (Adjusted):")
        # Remove duplicates from Top 10 that are already in Top 5
        missing_top5_only = [m for m in missing_top5]
        for troop, activity, rank in sorted(missing_top5_only, key=lambda x: (x[2], x[0])):
            report_lines.append(f"    {troop}: {activity} (#{rank})")
    
    if missing_top10:
        report_lines.append("")
        report_lines.append("  Missing Top 6-10 Activities (Adjusted):")
        # Only show Top 6-10 missing (exclude Top 5 which were already shown)
        missing_top6_10 = [m for m in missing_top10 if m[2] > 5]
        for troop, activity, rank in sorted(missing_top6_10, key=lambda x: (x[2], x[0])):
            report_lines.append(f"    {troop}: {activity} (#{rank})")
    
    report_lines.append("")

    
    # =========================================================================
    # Section 2: CONSTRAINT COMPLIANCE (existing)
    # =========================================================================
    report_lines.append("CONSTRAINT COMPLIANCE")
    report_lines.append("-"*70)
    
    # Beach slot constraint
    beach_violations = 0
    BEACH_ACTS = ["Water Polo", "Greased Watermelon", "Aqua Trampoline"]
    for e in schedule.entries:
        if e.activity.name in BEACH_ACTS:
            slot = e.time_slot.slot_number
            # Per Spine: Slot 2 only allowed on Thursday (Sailing has separate exception)
            if e.time_slot.day != Day.THURSDAY and slot == 2:
                beach_violations += 1
    
    # Accuracy limit - ENHANCED to separate Rifle+Shotgun (CRITICAL) from general accuracy (WARNING)
    rifle_shotgun_violations = 0  # CRITICAL: Rifle + Shotgun same day
    accuracy_violations = 0  # WARNING: > 1 accuracy activity per day (Archery only now)
    ACCURACY = ["Troop Rifle", "Troop Shotgun", "Archery"]
    for troop in troops:
        day_acc = defaultdict(set)
        for e in schedule.entries:
            if e.troop == troop and e.activity.name in ACCURACY:
                day_acc[e.time_slot.day].add(e.activity.name)
        for day, acts in day_acc.items():
            # CRITICAL: Rifle + Shotgun on same day
            if "Troop Rifle" in acts and "Troop Shotgun" in acts:
                rifle_shotgun_violations += 1
            # WARNING: More than 1 accuracy activity (general)
            elif len(acts) > 1:
                accuracy_violations += 1
    
    # Friday Reflection
    reflection_violations = sum(1 for t in troops if not any(
        e.activity.name == "Reflection" and e.time_slot.day == Day.FRIDAY
        for e in schedule.entries if e.troop == t
    ))
    
    report_lines.append(f"  Beach Slot Rule:     {'[OK] All compliant' if beach_violations == 0 else f'[WARN] {beach_violations} violations'}")
    report_lines.append(f"  Rifle+Shotgun Day:   {'[OK] All compliant' if rifle_shotgun_violations == 0 else f'[CRITICAL] {rifle_shotgun_violations} violations'}")
    report_lines.append(f"  Accuracy Limit:      {'[OK] All compliant' if accuracy_violations == 0 else f'[WARN] {accuracy_violations} violations'}")
    report_lines.append(f"  Friday Reflection:   {'[OK] All troops' if reflection_violations == 0 else f'[FAIL] {reflection_violations} missing'}")
    
    report_lines.append("")
    
    # =========================================================================
    # Section 2.5: SCHEDULE GAPS (Empty Slots)
    # =========================================================================
    report_lines.append("SCHEDULE GAPS (Empty Slots)")
    report_lines.append("-"*70)
    
    # Check for gaps - each troop should have activities in all slots
    days_list = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
    slots_per_day = {
        Day.MONDAY: 3, Day.TUESDAY: 3, Day.WEDNESDAY: 3,
        Day.THURSDAY: 2, Day.FRIDAY: 3
    }
    
    total_gaps = 0
    troops_with_gaps = []
    
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        # Build filled_slots accounting for multi-slot activities
        filled_slots = set()
        for e in troop_entries:
            filled_slots.add((e.time_slot.day, e.time_slot.slot_number))
            # Add additional slots for multi-slot activities (e.g., Sailing, Float for Floats)
            if e.activity.slots > 1:
                for extra in range(1, math.ceil(e.activity.slots)):
                    filled_slots.add((e.time_slot.day, e.time_slot.slot_number + extra))
        
        
        gaps = []
        for day in days_list:
            for slot in range(1, slots_per_day[day] + 1):
                if (day, slot) not in filled_slots:
                    day_abbr = day.value[:3].upper()
                    gaps.append(f"{day_abbr}-{slot}")
        
        if gaps:
            total_gaps += len(gaps)
            troops_with_gaps.append((troop.name, len(gaps), gaps))
    
    if total_gaps == 0:
        report_lines.append("  [OK] No gaps - all troops have complete schedules")
    else:
        report_lines.append(f"  Total gaps: {total_gaps} [FAIL]")
        report_lines.append(f"  Troops with gaps ({len(troops_with_gaps)}):")
        for troop_name, gap_count, gap_list in sorted(troops_with_gaps, key=lambda x: -x[1]):
            gap_display = ', '.join(gap_list) if len(gap_list) <= 5 else ', '.join(gap_list[:5]) + '...'
            report_lines.append(f"    {troop_name}: {gap_count} gaps [{gap_display}]")
    
    report_lines.append("")
    
    
    # =========================================================================
    # Section 3: WET/DRY CONSTRAINT VIOLATIONS
    # =========================================================================
    report_lines.append("WET/DRY CONSTRAINT VIOLATIONS")
    report_lines.append("-"*70)
    
    wet_tower_violations = 0  # Wet -> Tower/ODS
    tower_wet_violations = 0  # Tower/ODS -> Wet
    major_wet_same_day = 0    # 2+ major wet beach same day
    wet_dry_wet_pattern = 0   # Wet-Dry-Wet slot pattern
    
    for troop in troops:
        troop_entries = sorted(
            [e for e in schedule.entries if e.troop == troop],
            key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
        )
        
        # Group by day
        by_day = defaultdict(list)
        for e in troop_entries:
            by_day[e.time_slot.day].append(e)
        
        for day, day_entries in by_day.items():
            day_entries.sort(key=lambda e: e.time_slot.slot_number)
            
            # Check for wet -> Tower/ODS and Tower/ODS -> wet
            for i in range(len(day_entries) - 1):
                curr = day_entries[i]
                next_e = day_entries[i + 1]
                
                if curr.activity.name in WET_ACTIVITIES and next_e.activity.name in TOWER_ODS_ACTIVITIES:
                    wet_tower_violations += 1
                if curr.activity.name in TOWER_ODS_ACTIVITIES and next_e.activity.name in WET_ACTIVITIES:
                    tower_wet_violations += 1
            
            # Check for 2+ major wet beach same day
            major_wet_count = sum(1 for e in day_entries if e.activity.name in MAJOR_WET_BEACH)
            if major_wet_count >= 2:
                major_wet_same_day += 1
            
            # Check for wet-dry-wet pattern (slots 1, 2, 3)
            if len(day_entries) >= 3:
                slot_map = {e.time_slot.slot_number: e for e in day_entries}
                if 1 in slot_map and 2 in slot_map and 3 in slot_map:
                    s1_wet = slot_map[1].activity.name in WET_ACTIVITIES
                    s2_wet = slot_map[2].activity.name in WET_ACTIVITIES
                    s3_wet = slot_map[3].activity.name in WET_ACTIVITIES
                    if s1_wet and not s2_wet and s3_wet:
                        wet_dry_wet_pattern += 1
    
    report_lines.append(f"  Wet -> Tower/ODS:    {wet_tower_violations} violations")
    report_lines.append(f"  Tower/ODS -> Wet:    {tower_wet_violations} violations")
    report_lines.append(f"  2+ Major Wet/Day:    {major_wet_same_day} violations")
    report_lines.append(f"  Wet-Dry-Wet Pattern: {wet_dry_wet_pattern} violations")
    
    total_wet_violations = wet_tower_violations + tower_wet_violations + major_wet_same_day + wet_dry_wet_pattern
    status = "[OK]" if total_wet_violations == 0 else "[WARN]"
    report_lines.append(f"  TOTAL:               {total_wet_violations} violations {status}")
    
    report_lines.append("")
    
    # =========================================================================
    # Section 3.5: DELTA WALKING CONSTRAINT
    # =========================================================================
    report_lines.append("DELTA WALKING CONSTRAINT")
    report_lines.append("-"*70)
    
    # Delta is far from Tower and Outdoor Skills areas
    # Before/after Delta, troops should only go to Beach, Campsite, or Delta zone
    # (not Tower, Outdoor Skills, or Off-Camp which require long walks)
    from models import Zone
    DELTA_COMPATIBLE_ZONES = {Zone.BEACH, Zone.CAMPSITE, Zone.DELTA}
    
    delta_walking_violations = 0
    delta_violation_details = []
    
    for troop in troops:
        troop_entries = sorted(
            [e for e in schedule.entries if e.troop == troop],
            key=lambda e: (e.time_slot.day.value, e.time_slot.slot_number)
        )
        
        by_day = defaultdict(list)
        for e in troop_entries:
            by_day[e.time_slot.day].append(e)
        
        for day, day_entries in by_day.items():
            day_entries.sort(key=lambda e: e.time_slot.slot_number)
            
            for i in range(len(day_entries) - 1):
                curr = day_entries[i]
                next_e = day_entries[i + 1]
                
                # Check Delta -> incompatible zone
                if curr.activity.name == "Delta" and next_e.activity.zone not in DELTA_COMPATIBLE_ZONES:
                    delta_walking_violations += 1
                    delta_violation_details.append(
                        f"{troop.name}: Delta -> {next_e.activity.name} ({day.value[:3]}-{next_e.time_slot.slot_number})"
                    )
                
                # Check incompatible zone -> Delta
                if next_e.activity.name == "Delta" and curr.activity.zone not in DELTA_COMPATIBLE_ZONES:
                    delta_walking_violations += 1
                    delta_violation_details.append(
                        f"{troop.name}: {curr.activity.name} -> Delta ({day.value[:3]}-{next_e.time_slot.slot_number})"
                    )
    
    if delta_walking_violations == 0:
        report_lines.append("  [OK] No Delta walking violations")
    else:
        report_lines.append(f"  Total violations: {delta_walking_violations} [WARN]")
        for detail in delta_violation_details[:5]:  # Show first 5
            report_lines.append(f"    {detail}")
        if len(delta_violation_details) > 5:
            report_lines.append(f"    ... and {len(delta_violation_details) - 5} more")
    
    report_lines.append("")
    
    # =========================================================================
    # Section 4: DRY DAYS TRACKING
    # =========================================================================
    report_lines.append("DRY DAYS TRACKING (excl. Thursday)")
    report_lines.append("-"*70)
    
    troops_with_dry_days = []
    total_dry_days = 0
    
    for troop in troops:
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        by_day = defaultdict(list)
        for e in troop_entries:
            by_day[e.time_slot.day].append(e)
        
        dry_day_count = 0
        for day in [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.FRIDAY]:
            day_entries = by_day.get(day, [])
            if not day_entries:
                continue  # No activities this day (shouldn't happen)
            
            # Check if ALL activities are dry
            all_dry = all(e.activity.name not in WET_ACTIVITIES for e in day_entries)
            if all_dry:
                dry_day_count += 1
        
        total_dry_days += dry_day_count
        if dry_day_count >= 2:
            troops_with_dry_days.append((troop.name, dry_day_count))
    
    avg_dry = total_dry_days / len(troops) if troops else 0
    report_lines.append(f"  Average dry days per troop: {avg_dry:.1f}")
    
    if troops_with_dry_days:
        report_lines.append(f"  Troops with 2+ dry days ({len(troops_with_dry_days)}):")
        for name, count in sorted(troops_with_dry_days, key=lambda x: -x[1]):
            report_lines.append(f"    {name}: {count} dry days")
    else:
        report_lines.append("  [OK] No troops with 2+ dry days")
    
    report_lines.append("")
    
    # =========================================================================
    # Section 5: STAFF CLUSTERING (Enhanced)
    # =========================================================================
    report_lines.append("STAFF CLUSTERING EFFICIENCY")
    report_lines.append("-"*70)
    
    AREAS = {
        'Tower': ['Climbing Tower'],
        'Rifle Range': ['Troop Rifle', 'Troop Shotgun'],
        'Outdoor Skills': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                          'Ultimate Survivor', "What's Cooking", 'Chopped!'],
        'Handicrafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', "Monkey's Fist"]
    }
    MAX_PER_DAY = 3  # 3 slots per day
    
    for area, acts in AREAS.items():
        area_entries = [e for e in schedule.entries if e.activity.name in acts]
        days_used = set(e.time_slot.day for e in area_entries)
        
        # Smart day evaluation
        activity_count = len(area_entries)
        min_needed = math.ceil(activity_count / MAX_PER_DAY) if activity_count > 0 else 0
        excess = len(days_used) - min_needed if min_needed > 0 else 0
        
        # Non-consecutive tracking
        day_order = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY]
        day_indices = sorted([day_order.index(d) for d in days_used])
        non_consecutive = 0
        for i in range(len(day_indices) - 1):
            if day_indices[i + 1] - day_indices[i] > 1:
                non_consecutive += 1
        
        status = "[OK]" if excess == 0 and non_consecutive == 0 else "[INFO]"
        report_lines.append(f"  {area:20s} {len(days_used)} days (min: {min_needed}, excess: {excess}, gaps: {non_consecutive}) {status}")
    
    report_lines.append("")
    
    # =========================================================================
    # Section 6: STAFF LOAD VARIANCE (Exponential)
    # =========================================================================
    report_lines.append("STAFF WORKLOAD DISTRIBUTION (Exponential)")
    report_lines.append("-"*70)
    
    STAFF_MAP = {
        'Beach Staff': ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                       'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                       'Troop Swim', 'Water Polo'],
        'Tower Director': ['Climbing Tower'],
        'Rifle Director': ['Troop Rifle', 'Troop Shotgun'],
        'ODS Director': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                        'Ultimate Survivor', "What's Cooking", 'Chopped!']
    }
    
    TOTAL_SLOTS = 14  # Mon=3, Tue=3, Wed=3, Thu=2, Fri=3
    
    for staff, acts in STAFF_MAP.items():
        # Count troops per slot
        slot_counts = defaultdict(int)
        for e in schedule.entries:
            if e.activity.name in acts:
                slot_counts[(e.time_slot.day, e.time_slot.slot_number)] += 1
        
        if slot_counts:
            total_troops = sum(slot_counts.values())
            # Average over ALL 14 slots (not just slots with activity)
            avg_per_slot = total_troops / TOTAL_SLOTS
            max_load = max(slot_counts.values())
            min_load = min(slot_counts.values())
            slots_used = len(slot_counts)
            
            # Calculate needed staff: if avg > 1, need more than 1 staff member
            staff_needed = math.ceil(avg_per_slot)
            
            # Exponential penalty on variance
            total_penalty = sum((c - avg_per_slot) ** 2 for c in slot_counts.values())
            balance_score = max(0, 100 - total_penalty * 5)
            
            status = "[OK]" if balance_score >= 70 else "[WARN]"
            report_lines.append(f"  {staff:20s} avg={avg_per_slot:.1f}/slot, max={max_load}, slots={slots_used}/14, need={staff_needed} staff {status}")
    
    # Calculate ALL-STAFF Distribution Score (aggregate metric)
    report_lines.append("")
    report_lines.append("  ALL-STAFF DISTRIBUTION SCORE:")
    
    # Combine all staff activities into one distribution analysis
    all_staff_slot_counts = defaultdict(int)
    all_staff_activities = []
    for acts in STAFF_MAP.values():
        all_staff_activities.extend(acts)
    
    for e in schedule.entries:
        if e.activity.name in all_staff_activities:
            all_staff_slot_counts[(e.time_slot.day, e.time_slot.slot_number)] += 1
    
    if all_staff_slot_counts:
        total_staff_needed = sum(all_staff_slot_counts.values())
        avg_per_slot = total_staff_needed / TOTAL_SLOTS
        max_in_slot = max(all_staff_slot_counts.values())
        min_in_slot = min(all_staff_slot_counts.values()) if all_staff_slot_counts else 0
        slots_with_staff = len(all_staff_slot_counts)
        empty_slots = TOTAL_SLOTS - slots_with_staff
        
        # Distribution variance (lower is better)
        variance = sum((c - avg_per_slot) ** 2 for c in all_staff_slot_counts.values()) / len(all_staff_slot_counts)
        
        # Score: 100 - (variance * 10) - (empty_slots * 5) - (peak penalty if max > avg*2)
        peak_penalty = max(0, (max_in_slot - avg_per_slot * 2) * 10) if avg_per_slot > 0 else 0
        distribution_score = max(0, 100 - variance * 10 - empty_slots * 2 - peak_penalty)
        
        status = "[EXCELLENT]" if distribution_score >= 85 else "[OK]" if distribution_score >= 70 else "[WARN]"
        report_lines.append(f"    Total staff-requiring activities: {total_staff_needed}")
        report_lines.append(f"    Average per slot: {avg_per_slot:.1f}, Peak: {max_in_slot}, Empty slots: {empty_slots}")
        report_lines.append(f"    Variance: {variance:.2f}")
        report_lines.append(f"    Distribution Score: {distribution_score:.0f}/100 {status}")
    else:
        report_lines.append("    No staff activities scheduled")
    
    report_lines.append("")

    
    # =========================================================================
    # Section 7: COMMISSIONER LOAD BALANCE
    # =========================================================================
    report_lines.append("COMMISSIONER LOAD BALANCE")
    report_lines.append("-"*70)
    
    # Build commissioner -> troops mapping dynamically from troop data
    commissioner_troops = defaultdict(list)
    for t in troops:
        if hasattr(t, 'commissioner') and t.commissioner:
            commissioner_troops[t.commissioner].append(t)
    
    for comm, week_troops in sorted(commissioner_troops.items()):
        if not week_troops:
            continue
        
        # Count days worked (all 5 days including Thursday)
        comm_entries = []
        for troop in week_troops:
            comm_entries.extend([e for e in schedule.entries 
                                if e.troop == troop and e.activity.name in ["Delta", "Super Troop", "Archery", "Reflection"]])
        
        days_worked = len(set(e.time_slot.day for e in comm_entries))
        
        # Count Reflection coverage (up to 3 troops)
        reflections_scheduled = sum(1 for t in week_troops 
                                   if any(e.activity.name == "Reflection" and e.troop == t 
                                         for e in schedule.entries))
        max_reflections = min(3, len(week_troops))
        
        status = "[OK]" if reflections_scheduled >= max_reflections else "[WARN]"
        report_lines.append(f"  {comm:15s} {len(week_troops)} troops, {days_worked} days worked, {reflections_scheduled}/{max_reflections} Reflections {status}")
    
    report_lines.append("")
    
    # =========================================================================
    # Footer
    # =========================================================================
    report_lines.append("="*70)
    report_lines.append(f"Total Activities Scheduled: {len(schedule.entries)}")
    report_lines.append("="*70)
    
    # Print report
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save to file if specified
    if output_file:
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"\nReport saved to: {output_file}")
    
    return report_text

if __name__ == "__main__":
    import glob
    
    week_files = glob.glob("tc_week*.json") + glob.glob("voyageur_week*.json")
    
    for week_file in sorted(week_files):
        output_file = f"reports/{week_file.replace('.json', '_quality_report.txt')}"
        generate_quality_report(week_file, output_file)
        print("\n")
