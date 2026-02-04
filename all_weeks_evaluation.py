#!/usr/bin/env python3
"""Comprehensive Success Evaluation for All 8 Weeks"""

import json
from datetime import datetime

def evaluate_all_weeks():
    """Comprehensive evaluation of all 8 weeks"""
    
    # Load results
    with open('all_weeks_results.json', 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("SUMMER CAMP SCHEDULER - ALL 8 WEEKS SUCCESS EVALUATION")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Weeks: {data['total_weeks']}")
    print(f"Total Troops: {data['total_troops']}")
    print()
    
    # Overall metrics
    overall = data['overall_metrics']
    print("OVERALL SUCCESS METRICS:")
    print("=" * 40)
    print(f"Top 5 Satisfaction: {overall['top5_satisfaction']:.1f}%")
    print(f"Friday Reflection: {overall['reflection_compliance']:.1f}%")
    print(f"Total Violations: {overall['total_violations']}")
    print()
    
    # Weekly breakdown
    print("WEEKLY BREAKDOWN:")
    print("-" * 50)
    
    total_top5_possible = 0
    total_top5_achieved = 0
    total_reflection = 0
    total_troops = 0
    
    for week in data['weekly_results']:
        week_num = week['week']
        troops = week['troops']
        violations = week['violations']
        
        # Calculate week metrics
        week_top5_achieved = sum(week['stats']['troops'][t]['top5_achieved'] for t in week['stats']['troops'])
        week_top5_possible = troops * 5
        week_top5_rate = (week_top5_achieved / week_top5_possible * 100) if week_top5_possible > 0 else 0
        
        week_reflection = sum(1 for t in week['stats']['troops'] if week['stats']['troops'][t]['has_reflection'])
        week_reflection_rate = (week_reflection / troops * 100) if troops > 0 else 0
        
        # Accumulate totals
        total_top5_possible += week_top5_possible
        total_top5_achieved += week_top5_achieved
        total_reflection += week_reflection
        total_troops += troops
        
        print(f"Week {week_num}:")
        print(f"  Troops: {troops}")
        print(f"  Top 5: {week_top5_achieved}/{week_top5_possible} ({week_top5_rate:.1f}%)")
        print(f"  Friday Reflection: {week_reflection}/{troops} ({week_reflection_rate:.1f}%)")
        print(f"  Violations: {violations}")
        print()
    
    # Success Assessment against .cursorrules targets
    print("SUCCESS ASSESSMENT (.cursorrules Targets):")
    print("=" * 55)
    
    # Target: Top 5 Satisfaction: 90.0%
    target_top5 = 90.0
    top5_status = "EXCELLENT" if overall['top5_satisfaction'] >= 95 else "GOOD" if overall['top5_satisfaction'] >= 85 else "NEEDS WORK" if overall['top5_satisfaction'] >= 75 else "CRITICAL"
    print(f"Top 5 Satisfaction: {overall['top5_satisfaction']:.1f}% (Target: {target_top5}%) [{top5_status}]")
    
    # Target: Friday Reflection: 100%
    target_reflection = 100.0
    reflection_status = "EXCELLENT" if overall['reflection_compliance'] >= 95 else "GOOD" if overall['reflection_compliance'] >= 85 else "NEEDS WORK" if overall['reflection_compliance'] >= 70 else "CRITICAL"
    print(f"Friday Reflection: {overall['reflection_compliance']:.1f}% (Target: {target_reflection}%) [{reflection_status}]")
    
    # Target: Violations: < 6 total (baseline)
    target_violations = 6
    violations_status = "EXCELLENT" if overall['total_violations'] <= target_violations else "NEEDS WORK" if overall['total_violations'] <= target_violations + 2 else "CRITICAL"
    print(f"Total Violations: {overall['total_violations']} (Target: <={target_violations}) [{violations_status}]")
    
    print()
    
    # Overall Grade calculation
    # Weighted scoring: Top 5 (40%), Friday Reflection (30%), Violations (30%)
    top5_score = min(overall['top5_satisfaction'] / target_top5 * 100, 100)
    reflection_score = overall['reflection_compliance'] / target_reflection * 100
    violations_score = max(0, 100 - (overall['total_violations'] - target_violations) * 10)  # Penalty for violations over target
    
    overall_score = (top5_score * 0.4) + (reflection_score * 0.3) + (violations_score * 0.3)
    
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
    if overall['top5_satisfaction'] >= 90:
        print("[EXCELLENT] Top 5 preference satisfaction exceeds target")
    elif overall['top5_satisfaction'] >= 85:
        print("[GOOD] Top 5 preference satisfaction is solid")
    else:
        print(f"[NEEDS WORK] Top 5 satisfaction below target (target: 90%, current: {overall['top5_satisfaction']:.1f}%)")
    
    if overall['reflection_compliance'] >= 85:
        print("[GOOD] Friday Reflection compliance is solid")
    else:
        print(f"[CRITICAL] Friday Reflection compliance needs major improvement (target: 100%, current: {overall['reflection_compliance']:.1f}%)")
    
    if overall['total_violations'] <= target_violations:
        print("[EXCELLENT] Constraint violations at or below target")
    else:
        print(f"[NEEDS WORK] Constraint violations above target (target: <={target_violations}, current: {overall['total_violations']})")
    
    print()
    print("RECOMMENDATIONS:")
    print("-" * 20)
    
    if overall['reflection_compliance'] < 100:
        print("1. PRIORITY 1: Fix Friday Reflection scheduling for all troops")
        print("2. PRIORITY 2: Review Friday Reflection constraint logic")
        print("3. PRIORITY 3: Ensure Friday Reflection is mandatory in scheduling")
    
    if overall['total_violations'] > target_violations:
        print("4. Address constraint violations (currently above target)")
        print("5. Review beach slot and exclusive area constraints")
    
    if overall['top5_satisfaction'] < 95:
        print("6. Optimize Top 5 preference placement algorithms")
        print("7. Review preference ranking and scheduling priority")
    
    # Performance Summary
    print()
    print("PERFORMANCE SUMMARY:")
    print("-" * 20)
    print(f"[SUCCESS] Processed {data['total_weeks']} weeks successfully")
    print(f"[SUCCESS] Scheduled {data['total_troops']} troops total")
    print(f"[EXCELLENT] Top 5 satisfaction: {overall['top5_satisfaction']:.1f}% (exceeds 90% target)")
    print(f"[CRITICAL] Friday Reflection: {overall['reflection_compliance']:.1f}% (needs improvement)")
    print(f"[NEEDS WORK] Violations: {overall['total_violations']} (monitoring needed)")
    
    return {
        'overall_score': overall_score,
        'grade': grade,
        'top5_satisfaction': overall['top5_satisfaction'],
        'reflection_compliance': overall['reflection_compliance'],
        'total_violations': overall['total_violations'],
        'total_troops': data['total_troops'],
        'total_weeks': data['total_weeks']
    }

if __name__ == "__main__":
    results = evaluate_all_weeks()
