#!/usr/bin/env python3
"""
Calculate the correct success rate from the detailed analysis
"""

def calculate_success_rate():
    """Calculate the correct Top 5 success rate."""
    print("CALCULATING CORRECT SUCCESS RATE")
    print("=" * 60)
    
    # From the detailed analysis:
    # tc_week1_troops: 0 misses, 6 troops = 30 Top 5 slots
    # tc_week2_troops: 0 misses, 3 troops = 15 Top 5 slots  
    # tc_week3_troops: 3 misses, 9 troops = 45 Top 5 slots
    # tc_week4_troops: 8 misses, 11 troops = 55 Top 5 slots
    # tc_week5_troops: 6 misses, 11 troops = 55 Top 5 slots
    # tc_week6_troops: 3 misses, 10 troops = 50 Top 5 slots
    # tc_week7_troops: 5 misses, 11 troops = 55 Top 5 slots
    # tc_week8_troops: 1 miss, 4 troops = 20 Top 5 slots
    # voyageur_week1_troops: 5 misses, 10 troops = 50 Top 5 slots
    # voyageur_week3_troops: 3 misses, 8 troops = 40 Top 5 slots
    
    week_data = [
        ("tc_week1_troops", 6, 0),
        ("tc_week2_troops", 3, 0),
        ("tc_week3_troops", 9, 3),
        ("tc_week4_troops", 11, 8),
        ("tc_week5_troops", 11, 6),
        ("tc_week6_troops", 10, 3),
        ("tc_week7_troops", 11, 5),
        ("tc_week8_troops", 4, 1),
        ("voyageur_week1_troops", 10, 5),
        ("voyageur_week3_troops", 8, 3)
    ]
    
    total_troops = 0
    total_top5_slots = 0
    total_misses = 0
    
    print("WEEK-BY-WEEK BREAKDOWN:")
    for week_name, troops, misses in week_data:
        top5_slots = troops * 5
        satisfied = top5_slots - misses
        success_rate = 100.0 * satisfied / top5_slots
        
        print(f"{week_name}:")
        print(f"  Troops: {troops}, Top5 slots: {top5_slots}")
        print(f"  Misses: {misses}, Satisfied: {satisfied}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print()
        
        total_troops += troops
        total_top5_slots += top5_slots
        total_misses += misses
    
    total_satisfied = total_top5_slots - total_misses
    overall_success_rate = 100.0 * total_satisfied / total_top5_slots
    
    print("=" * 60)
    print("OVERALL SUMMARY:")
    print(f"Total Weeks: {len(week_data)}")
    print(f"Total Troops: {total_troops}")
    print(f"Total Top 5 Slots: {total_top5_slots}")
    print(f"Total Misses: {total_misses}")
    print(f"Total Satisfied: {total_satisfied}")
    print(f"Overall Success Rate: {overall_success_rate:.1f}%")
    
    print()
    print("ISSUE IDENTIFIED:")
    print("The unscheduled analyzer is calculating success rate incorrectly.")
    print(f"It should be: {overall_success_rate:.1f}%")
    print("But it's reporting: 0.0%")
    
    return overall_success_rate

if __name__ == "__main__":
    calculate_success_rate()
