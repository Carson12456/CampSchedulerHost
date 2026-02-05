#!/usr/bin/env python3
"""
Analyze ALL missed Top 5 preferences across schedules to find patterns.
Output: Which activities, ranks, troop sizes, etc. are most often missed.
"""
import json
import os
from collections import defaultdict
from pathlib import Path

THREE_HOUR = {"Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}
HC_DG = {"History Center", "Disc Golf"}

def analyze_week(week_id, schedule_path, troops_data):
    """Analyze one week, return list of (troop_name, activity, rank, troop_size, is_exempt)."""
    if not os.path.exists(schedule_path):
        return [], []
    
    with open(schedule_path) as f:
        sched = json.load(f)
    
    # Build troop lookup
    troops_by_name = {t['name']: t for t in troops_data}
    
    # Get scheduled activities per troop from entries
    troop_scheduled = defaultdict(set)
    for e in sched.get('entries', []):
        troop_scheduled[e['troop_name']].add(e['activity_name'])
    
    # HC/DG Tuesday exemption
    tuesday_hc_dg = set()
    for e in sched.get('entries', []):
        if e['day'] == 'TUESDAY' and e['activity_name'] in HC_DG:
            tuesday_hc_dg.add(e['slot'])
    hc_dg_full = tuesday_hc_dg >= {1, 2, 3}
    
    misses = []
    for troop_name, prefs in [(t['name'], t.get('preferences', [])[:5]) for t in troops_data]:
        scheduled = troop_scheduled[troop_name]
        troop_info = troops_by_name.get(troop_name, {})
        troop_size = troop_info.get('scouts', 0) + troop_info.get('adults', 0)
        has_3hr = bool(scheduled & THREE_HOUR)
        
        for i, pref in enumerate(prefs):
            if pref in scheduled:
                continue
            rank = i + 1
            is_exempt = False
            if pref in THREE_HOUR and has_3hr:
                is_exempt = True
            elif pref in HC_DG and hc_dg_full:
                is_exempt = True
            
            misses.append({
                'week': week_id,
                'troop': troop_name,
                'activity': pref,
                'rank': rank,
                'troop_size': troop_size,
                'is_exempt': is_exempt,
            })
    
    return misses

def main():
    # Week files (same as evaluate_week_success)
    week_files = [
        "tc_week1_troops.json", "tc_week2_troops.json", "tc_week3_troops.json",
        "tc_week4_troops.json", "tc_week5_troops.json", "tc_week6_troops.json",
        "tc_week7_troops.json", "tc_week8_troops.json",
        "voyageur_week1_troops.json", "voyageur_week3_troops.json",
    ]
    
    all_misses = []
    troops_dir = Path("troops")
    sched_dir = Path("schedules")
    
    for wf in week_files:
        week_id = wf.replace("_troops.json", "").replace(".json", "")
        troops_path = troops_dir / wf
        sched_path = sched_dir / f"{week_id}_troops_schedule.json"
        
        if not troops_path.exists():
            troops_path = Path(wf)
        if not troops_path.exists():
            continue
        
        with open(troops_path) as f:
            troops = json.load(f)['troops']
        
        misses = analyze_week(week_id, sched_path, troops)
        all_misses.extend(misses)
    
    # Filter to non-exempt only for pattern analysis
    non_exempt = [m for m in all_misses if not m['is_exempt']]
    
    print("=" * 80)
    print("TOP 5 MISSED ACTIVITIES - COMPREHENSIVE PATTERN ANALYSIS")
    print("=" * 80)
    print(f"\nTotal non-exempt misses: {len(non_exempt)}")
    print(f"Total including exempt: {len(all_misses)}")
    
    # PATTERN 1: By activity
    by_activity = defaultdict(list)
    for m in non_exempt:
        by_activity[m['activity']].append(m)
    print("\n--- BY ACTIVITY (most missed first) ---")
    for act, ms in sorted(by_activity.items(), key=lambda x: -len(x[1])):
        sizes = [m['troop_size'] for m in ms]
        ranks = [m['rank'] for m in ms]
        weeks = set(m['week'] for m in ms)
        print(f"  {act}: {len(ms)} misses | ranks: {sorted(ranks)} | sizes: {sizes} | weeks: {sorted(weeks)}")
    
    # PATTERN 2: By rank
    by_rank = defaultdict(list)
    for m in non_exempt:
        by_rank[m['rank']].append(m)
    print("\n--- BY RANK ---")
    for r in sorted(by_rank.keys()):
        ms = by_rank[r]
        acts = defaultdict(int)
        for m in ms:
            acts[m['activity']] += 1
        print(f"  Rank #{r}: {len(ms)} misses | activities: {dict(acts)}")
    
    # PATTERN 3: By troop size buckets
    def size_bucket(s):
        if s <= 12: return "small (<=12)"
        if s <= 16: return "medium (13-16)"
        if s <= 20: return "large (17-20)"
        return "xlarge (21+)"
    by_size = defaultdict(list)
    for m in non_exempt:
        by_size[size_bucket(m['troop_size'])].append(m)
    print("\n--- BY TROOP SIZE ---")
    for bucket in ["small (<=12)", "medium (13-16)", "large (17-20)", "xlarge (21+)"]:
        if bucket in by_size:
            ms = by_size[bucket]
            acts = defaultdict(int)
            for m in ms:
                acts[m['activity']] += 1
            print(f"  {bucket}: {len(ms)} misses | activities: {dict(acts)}")
    
    # PATTERN 4: Activity categories
    BEACH = {"Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim", "Troop Canoe", 
             "Troop Kayak", "Canoe Snorkel", "Float for Floats", "Sailing", "Underwater Obstacle Course", "Nature Canoe"}
    EXCLUSIVE = {"Climbing Tower", "Archery", "Troop Rifle", "Troop Shotgun", "Delta", "Sailing"}
    LIMITED = {"History Center", "Disc Golf"}  # Tuesday only
    by_category = defaultdict(list)
    for m in non_exempt:
        a = m['activity']
        if a in BEACH: cat = "Beach"
        elif a in EXCLUSIVE: cat = "Exclusive"
        elif a in LIMITED: cat = "Limited-day"
        elif a in THREE_HOUR: cat = "3-hour"
        else: cat = "Other"
        by_category[cat].append(m)
    print("\n--- BY ACTIVITY CATEGORY ---")
    for cat, ms in sorted(by_category.items(), key=lambda x: -len(x[1])):
        acts = defaultdict(int)
        for m in ms:
            acts[m['activity']] += 1
        print(f"  {cat}: {len(ms)} | {dict(acts)}")
    
    # PATTERN 5: Week distribution
    by_week = defaultdict(list)
    for m in non_exempt:
        by_week[m['week']].append(m)
    print("\n--- BY WEEK ---")
    for w in sorted(by_week.keys()):
        ms = by_week[w]
        acts = [m['activity'] for m in ms]
        print(f"  {w}: {len(ms)} | {acts}")
    
    # Raw detail for top missed activities
    print("\n--- RAW DETAIL: Top 3 most-missed activities ---")
    top_acts = sorted(by_activity.items(), key=lambda x: -len(x[1]))[:3]
    for act, ms in top_acts:
        print(f"\n  {act} ({len(ms)} misses):")
        for m in ms:
            print(f"    {m['week']} {m['troop']} (size {m['troop_size']}) rank #{m['rank']}")
    
    return non_exempt

if __name__ == "__main__":
    main()
