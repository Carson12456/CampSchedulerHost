#!/usr/bin/env python3
"""Comprehensive Success Evaluation Report"""

import json
from datetime import datetime

def calculate_success_metrics():
    """Calculate comprehensive success metrics from current schedules"""
    
    # Load current schedule data
    with open('current_schedules.json', 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("SUMMER CAMP SCHEDULER - SUCCESS EVALUATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Calculate overall metrics
    total_troops = sum(week['troops'] for week in data)
    total_entries = sum(week['stats']['total_entries'] for week in data)
    
    # Top 5 Satisfaction Analysis
    total_top5_possible = 0
    total_top5_achieved = 0
    troops_with_reflection = 0
    
    for week in data:
        for troop_name, stats in week['stats']['troops'].items():
            total_top5_possible += 5  # Each troop has 5 Top 5 preferences
            total_top5_achieved += stats['top5_achieved']
            if stats['has_reflection']:
                troops_with_reflection += 1
    
    top5_satisfaction_rate = (total_top5_achieved / total_top5_possible * 100) if total_top5_possible > 0 else 0
    
    # Top 10 Satisfaction Analysis
    total_top10_possible = 0
    total_top10_achieved = 0
    
    for week in data:
        for troop_name, stats in week['stats']['troops'].items():
            total_top10_possible += 10  # Each troop has 10 Top 10 preferences
            total_top10_achieved += stats['top10_achieved']
    
    top10_satisfaction_rate = (total_top10_achieved / total_top10_possible * 100) if total_top10_possible > 0 else 0
    
    # Friday Reflection Compliance
    reflection_compliance = (troops_with_reflection / total_troops * 100) if total_troops > 0 else 0
    
    # Week-by-week breakdown
    print("WEEKLY BREAKDOWN:")
    print("-" * 40)
    for week in data:
        week_num = week['week']
        troops_count = week['troops']
        entries = week['stats']['total_entries']
        
        week_top5_achieved = sum(stats['top5_achieved'] for stats in week['stats']['troops'].values())
        week_top5_possible = troops_count * 5
        week_top5_rate = (week_top5_achieved / week_top5_possible * 100) if week_top5_possible > 0 else 0
        
        week_reflection = sum(1 for stats in week['stats']['troops'].values() if stats['has_reflection'])
        week_reflection_rate = (week_reflection / troops_count * 100) if troops_count > 0 else 0
        
        print(f"Week {week_num}:")
        print(f"  Troops: {troops_count}")
        print(f"  Total Activities: {entries}")
        print(f"  Top 5 Satisfaction: {week_top5_achieved}/{week_top5_possible} ({week_top5_rate:.1f}%)")
        print(f"  Friday Reflection: {week_reflection}/{troops_count} ({week_reflection_rate:.1f}%)")
        print()
    
    # Overall Success Metrics
    print("OVERALL SUCCESS METRICS:")
    print("=" * 40)
    print(f"Total Troops Scheduled: {total_troops}")
    print(f"Total Activities Scheduled: {total_entries}")
    print(f"Average Activities per Troop: {total_entries/total_troops:.1f}")
    print()
    print(f"Top 5 Satisfaction: {total_top5_achieved}/{total_top5_possible} ({top5_satisfaction_rate:.1f}%)")
    print(f"Top 10 Satisfaction: {total_top10_achieved}/{total_top10_possible} ({top10_satisfaction_rate:.1f}%)")
    print(f"Friday Reflection Compliance: {troops_with_reflection}/{total_troops} ({reflection_compliance:.1f}%)")
    print()
    
    # Success Assessment against .cursorrules targets
    print("SUCCESS ASSESSMENT (.cursorrules Targets):")
    print("=" * 50)
    
    # Target: Top 5 Satisfaction: 90.0% (16/18 available preferences)
    target_top5 = 90.0
    top5_status = "EXCELLENT" if top5_satisfaction_rate >= 85 else "NEEDS WORK" if top5_satisfaction_rate >= 75 else "CRITICAL"
    print(f"Top 5 Satisfaction: {top5_satisfaction_rate:.1f}% (Target: {target_top5}%) [{top5_status}]")
    
    # Target: Friday Reflection: 100%
    target_reflection = 100.0
    reflection_status = "EXCELLENT" if reflection_compliance >= 95 else "NEEDS WORK" if reflection_compliance >= 85 else "CRITICAL"
    print(f"Friday Reflection: {reflection_compliance:.1f}% (Target: {target_reflection}%) [{reflection_status}]")
    
    # Target: Schedule Completeness (no gaps)
    # Based on average 14 activities per troop (should be 15 for full schedule)
    avg_activities = total_entries / total_troops
    completeness_status = "EXCELLENT" if avg_activities >= 14 else "NEEDS WORK" if avg_activities >= 12 else "CRITICAL"
    print(f"Schedule Completeness: {avg_activities:.1f}/troop (Target: 15) [{completeness_status}]")
    
    print()
    
    # Overall Grade
    overall_score = (top5_satisfaction_rate + reflection_compliance + (avg_activities/15*100)) / 3
    
    if overall_score >= 90:
        grade = "A"
        status = "EXCELLENT"
    elif overall_score >= 80:
        grade = "B"
        status = "GOOD"
    elif overall_score >= 70:
        grade = "C"
        status = "ACCEPTABLE"
    elif overall_score >= 60:
        grade = "D"
        status = "NEEDS IMPROVEMENT"
    else:
        grade = "F"
        status = "CRITICAL"
    
    print(f"OVERALL GRADE: {grade} ({overall_score:.1f}%) [{status}]")
    print()
    
    # Key Findings
    print("KEY FINDINGS:")
    print("-" * 20)
    if top5_satisfaction_rate >= 85:
        print("[EXCELLENT] Top 5 preference satisfaction is excellent")
    else:
        print(f"[NEEDS WORK] Top 5 satisfaction needs improvement (target: 90%, current: {top5_satisfaction_rate:.1f}%)")
    
    if reflection_compliance >= 95:
        print("[EXCELLENT] Friday Reflection compliance is excellent")
    else:
        print(f"[NEEDS WORK] Friday Reflection compliance needs work (target: 100%, current: {reflection_compliance:.1f}%)")
    
    if avg_activities >= 14:
        print("[GOOD] Schedule completeness is good")
    else:
        print(f"[NEEDS WORK] Schedule completeness has gaps (target: 15/troop, current: {avg_activities:.1f}/troop)")
    
    print()
    print("RECOMMENDATIONS:")
    print("-" * 20)
    if top5_satisfaction_rate < 90:
        print("1. Focus on improving Top 5 preference placement")
        print("2. Review preference ranking algorithms")
    
    if reflection_compliance < 100:
        print("3. Ensure Friday Reflection is scheduled for all troops")
        print("4. Check Friday Reflection scheduling logic")
    
    if avg_activities < 15:
        print("5. Address gap elimination algorithms")
        print("6. Review activity availability constraints")
    
    return {
        'overall_score': overall_score,
        'grade': grade,
        'top5_satisfaction': top5_satisfaction_rate,
        'reflection_compliance': reflection_compliance,
        'avg_activities': avg_activities,
        'total_troops': total_troops,
        'total_entries': total_entries
    }

if __name__ == "__main__":
    calculate_success_metrics()
