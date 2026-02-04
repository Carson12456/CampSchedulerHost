#!/usr/bin/env python3
"""
Compare the improvements made to the scheduler.
"""

import json
from pathlib import Path

def compare_improvements():
    """Compare baseline vs improved metrics."""
    print("=== SCHEDULER IMPROVEMENTS COMPARISON ===\n")
    
    # Load current baseline
    baseline_file = Path("baseline_metrics.json")
    if not baseline_file.exists():
        print("Error: baseline_metrics.json not found. Run analyze_gaps.py first.")
        return
    
    with open(baseline_file, "r") as f:
        current = json.load(f)
    
    # Previous baseline (from earlier optimization work)
    previous = {
        "total_gaps": 13,
        "total_entries": 152,
        "satisfaction_rate": 61.2,
        "avg_staff": 11.2,
        "high_loads": 0,
        "underused": 0,
        "staff_variance": 2.14
    }
    
    print("=== METRICS COMPARISON ===")
    print(f"{'Metric':<20} {'Previous':<12} {'Current':<12} {'Change':<12}")
    print("-" * 56)
    
    metrics = [
        ("Total Gaps", "total_gaps", "lower"),
        ("Total Entries", "total_entries", "higher"),
        ("Satisfaction %", "satisfaction_rate", "higher"),
        ("Avg Staff/Slot", "avg_staff", "neutral"),
        ("High Load Slots", "high_loads", "lower"),
        ("Underused Slots", "underused", "lower"),
        ("Staff Variance", "staff_variance", "lower")
    ]
    
    for display_name, key, direction in metrics:
        prev_val = previous[key]
        curr_val = current[key]
        
        if key in ["satisfaction_rate", "avg_staff", "staff_variance"]:
            prev_display = f"{prev_val:.1f}"
            curr_display = f"{curr_val:.1f}"
        else:
            prev_display = str(prev_val)
            curr_display = str(curr_val)
        
        if direction == "lower":
            change = curr_val - prev_val
            change_display = f"{change:+d}" if isinstance(change, int) else f"{change:+.1f}"
            if change < 0:
                change_display = f"+ {change_display}"
            elif change > 0:
                change_display = f"- {change_display}"
            else:
                change_display = f"= {change_display}"
        elif direction == "higher":
            change = curr_val - prev_val
            change_display = f"{change:+d}" if isinstance(change, int) else f"{change:+.1f}"
            if change > 0:
                change_display = f"+ {change_display}"
            elif change < 0:
                change_display = f"- {change_display}"
            else:
                change_display = f"= {change_display}"
        else:  # neutral
            change_display = "="
        
        print(f"{display_name:<20} {prev_display:<12} {curr_display:<12} {change_display:<12}")
    
    print(f"\n=== GAP ANALYSIS ===")
    print(f"Current total gaps: {current['total_gaps']}")
    print(f"Troops with most gaps: ", end="")
    
    # Sort troops by gaps (most first)
    troop_gaps = current['troop_gaps']
    sorted_troops = sorted(troop_gaps.items(), key=lambda x: x[1], reverse=True)
    worst_troops = [f"{name}({gaps})" for name, gaps in sorted_troops[:3] if gaps > 0]
    print(", ".join(worst_troops) if worst_troops else "None")
    
    print(f"\nMost problematic slots: ", end="")
    # Sort slots by gaps (most first)
    slot_gaps = current['day_slot_gaps']
    sorted_slots = sorted(slot_gaps.items(), key=lambda x: x[1], reverse=True)
    worst_slots = [f"{slot}({gaps})" for slot, gaps in sorted_slots[:3] if gaps > 0]
    print(", ".join(worst_slots) if worst_slots else "None")
    
    print(f"\n=== IMPROVEMENTS MADE ===")
    print("+ Restored troop preferences display in web interface")
    print("+ Enhanced gap filling with priority-based targeting")
    print("+ Improved staff load consideration in activity moves")
    print("+ Fixed Thursday slot counting (2 slots, not 3)")
    print("+ Better clustering bonus calculations")
    
    print(f"\n=== RECOMMENDATIONS ===")
    if current['total_gaps'] > 15:
        print("• Consider more aggressive gap filling for critical slots")
    if current['satisfaction_rate'] < 60:
        print("• Focus on recovering more Top 5 preferences")
    if current['staff_variance'] > 2.5:
        print("• Continue optimizing staff balance")
    
    print(f"\nWeb interface running at: http://localhost:5000")
    print("Troop preferences should now display beneath each schedule.")

if __name__ == "__main__":
    compare_improvements()
