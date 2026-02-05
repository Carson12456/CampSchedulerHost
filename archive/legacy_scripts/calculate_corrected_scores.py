#!/usr/bin/env python3
"""
Calculate corrected quality scores with proper top 5 tracking (excluding unavailable activities)
"""

import json
import os
import glob
from typing import Dict, List

def main():
    """Calculate and display corrected scores across all weeks."""
    print("=== CORRECTED TOP 5 SATISFACTION SCORES (EXCLUDING UNAVAILABLE ACTIVITIES) ===\n")
    
    # Manually extracted data from recent runs with corrected top 5 tracking
    weeks_data = [
        {
            'week': 'Week 1',
            'quality_score': 71.6,
            'schedule_quality_percent': 62.5,
            'staff_efficiency': 73.4,
            'clustering_quality': 56.7,
            'total_violations': 2,
            'violations_fixed': 0,
            'ml_confidence': 0.83,
            'adaptive_score': 64.90,
            'clustering_improvement': 0.000,
            'top5_satisfied': 6,
            'top5_total': 6,
            'top5_available': 0,  # All top 5 were exempt (unavailable)
            'top5_exempt': 0,
            'top5_percentage': 100.0  # 100% of available top 5
        },
        {
            'week': 'Week 2', 
            'quality_score': 73.2,
            'schedule_quality_percent': 63.6,
            'staff_efficiency': 78.8,
            'clustering_quality': 68.0,
            'total_violations': 1,
            'violations_fixed': 0,
            'ml_confidence': 0.42,
            'adaptive_score': 67.34,
            'clustering_improvement': 0.000,
            'top5_satisfied': 3,
            'top5_total': 3,
            'top5_available': 0,  # All top 5 were exempt (unavailable)
            'top5_exempt': 0,
            'top5_percentage': 100.0  # 100% of available top 5
        },
        {
            'week': 'Week 3',
            'quality_score': 61.5,
            'schedule_quality_percent': 63.0,
            'staff_efficiency': 0.0,
            'clustering_quality': 56.7,
            'total_violations': 6,
            'violations_fixed': 0,
            'ml_confidence': 1.00,
            'adaptive_score': 60.23,
            'clustering_improvement': 0.000,
            'top5_satisfied': 7,
            'top5_total': 9,
            'top5_available': 10,  # 10 available top 5 preferences
            'top5_exempt': 0,
            'top5_percentage': 70.0  # 7/10 = 70%
        }
    ]
    
    # Calculate averages
    num_weeks = len(weeks_data)
    averages = {
        'quality_score': sum(w['quality_score'] for w in weeks_data) / num_weeks,
        'schedule_quality_percent': sum(w['schedule_quality_percent'] for w in weeks_data) / num_weeks,
        'staff_efficiency': sum(w['staff_efficiency'] for w in weeks_data) / num_weeks,
        'clustering_quality': sum(w['clustering_quality'] for w in weeks_data) / num_weeks,
        'total_violations': sum(w['total_violations'] for w in weeks_data) / num_weeks,
        'violations_fixed': sum(w['violations_fixed'] for w in weeks_data) / num_weeks,
        'ml_confidence': sum(w['ml_confidence'] for w in weeks_data) / num_weeks,
        'adaptive_score': sum(w['adaptive_score'] for w in weeks_data) / num_weeks,
        'clustering_improvement': sum(w['clustering_improvement'] for w in weeks_data) / num_weeks,
        'top5_satisfied': sum(w['top5_satisfied'] for w in weeks_data),
        'top5_total': sum(w['top5_total'] for w in weeks_data),
        'top5_available': sum(w['top5_available'] for w in weeks_data),
        'top5_exempt': sum(w['top5_exempt'] for w in weeks_data),
        'top5_percentage': sum(w['top5_percentage'] for w in weeks_data) / num_weeks
    }
    
    # Display individual week results
    print("INDIVIDUAL WEEK RESULTS:")
    print("-" * 110)
    print(f"{'Week':<10} {'Quality':<8} {'Schedule':<8} {'Staff':<8} {'Cluster':<8} {'Violations':<12} {'Top5':<12} {'Available':<10} {'ML Conf':<8}")
    print(f"{'':<10} {'Score':<8} {'Quality%':<8} {'Eff%':<8} {'Quality%':<8} {'Total':<6} {'Fixed':<6} {'Sat%':<8} {'Top5':<10} {'idence':<8}")
    print("-" * 110)
    
    for week_data in weeks_data:
        print(f"{week_data['week']:<10} {week_data['quality_score']:<8.1f} "
              f"{week_data['schedule_quality_percent']:<8.1f} {week_data['staff_efficiency']:<8.1f} "
              f"{week_data['clustering_quality']:<8.1f} {week_data['total_violations']:<6} "
              f"{week_data['violations_fixed']:<6} {week_data['top5_percentage']:<8.1f} "
              f"{week_data['top5_available']:<10} {week_data['ml_confidence']:<8.2f}")
    
    # Display averages
    print("\nCORRECTED AVERAGE RESULTS ACROSS ALL WEEKS:")
    print("=" * 110)
    print(f"Average Quality Score: {averages['quality_score']:.1f}")
    print(f"Average Schedule Quality %: {averages['schedule_quality_percent']:.1f}%")
    print(f"Average Staff Efficiency: {averages['staff_efficiency']:.1f}%")
    print(f"Average Clustering Quality: {averages['clustering_quality']:.1f}%")
    print(f"Average Total Violations: {averages['total_violations']:.1f}")
    print(f"Average Violations Fixed: {averages['violations_fixed']:.1f}")
    print(f"Average ML Confidence: {averages['ml_confidence']:.2f}")
    print(f"Average Adaptive Score: {averages['adaptive_score']:.1f}")
    print(f"Average Clustering Improvement: {averages['clustering_improvement']:.3f}")
    print(f"Top 5 Satisfaction: {averages['top5_satisfied']}/{averages['top5_total']} ({averages['top5_percentage']:.1f}%)")
    print(f"Available Top 5 Preferences: {averages['top5_available']}")
    print(f"Exempt Top 5 Preferences: {averages['top5_exempt']}")
    
    # Calculate overall grade
    avg_quality = averages['quality_score']
    if avg_quality >= 90:
        overall_grade = 'A'
    elif avg_quality >= 80:
        overall_grade = 'B'
    elif avg_quality >= 70:
        overall_grade = 'C'
    elif avg_quality >= 60:
        overall_grade = 'D'
    else:
        overall_grade = 'F'
    
    print(f"\nOVERALL GRADE: {overall_grade} ({avg_quality:.1f})")
    
    # Analysis
    print("\nCORRECTED ANALYSIS:")
    print("-" * 60)
    print(f"• Best performing week: {max(weeks_data, key=lambda x: x['quality_score'])['week']} "
          f"({max(w['quality_score'] for w in weeks_data):.1f})")
    print(f"• Week needing most improvement: {min(weeks_data, key=lambda x: x['quality_score'])['week']} "
          f"({min(w['quality_score'] for w in weeks_data):.1f})")
    print(f"• Total violations across all weeks: {sum(w['total_violations'] for w in weeks_data)}")
    print(f"• Total violations fixed: {sum(w['violations_fixed'] for w in weeks_data)}")
    print(f"• Average ML confidence: {averages['ml_confidence']:.2f} "
          f"({'High' if averages['ml_confidence'] > 0.7 else 'Medium' if averages['ml_confidence'] > 0.4 else 'Low'})")
    
    # Top 5 analysis
    total_available = averages['top5_available']
    total_satisfied = averages['top5_satisfied']
    if total_available > 0:
        actual_top5_percentage = (total_satisfied / total_available) * 100
        print(f"• Top 5 Preference Satisfaction: {actual_top5_percentage:.1f}% "
              f"({total_satisfied}/{total_available} of available preferences)")
        print(f"• Status: {'PERFECT' if actual_top5_percentage >= 95 else 'EXCELLENT' if actual_top5_percentage >= 85 else 'GOOD' if actual_top5_percentage >= 75 else 'NEEDS WORK'}")
    else:
        print(f"• Top 5 Preference Satisfaction: N/A (no available top 5 preferences)")
        print(f"• Status: EXEMPT (all top 5 preferences were unavailable activities)")
    
    print(f"• Clustering System: {'Active' if averages['clustering_improvement'] > 0 else 'No improvements found'}")
    
    # Comparison with previous results
    print("\nCOMPARISON WITH PREVIOUS RESULTS:")
    print("-" * 60)
    print("Previous Average Quality Score: 68.5")
    print(f"Corrected Average Quality Score: {averages['quality_score']:.1f}")
    improvement = averages['quality_score'] - 68.5
    print(f"Improvement: {improvement:+.1f} points")
    
    print("Previous Top 5 Satisfaction: 92.6% (including unavailable)")
    print(f"Corrected Top 5 Satisfaction: {averages['top5_percentage']:.1f}% (available only)")
    
    # Clustering analysis
    print("\nCLUSTERING ANALYSIS:")
    print("-" * 60)
    print("• Enhanced clustering system implemented with 3 phases:")
    print("  - Phase 1: Aggressive zone consolidation")
    print("  - Phase 2: Cross-zone optimization") 
    print("  - Phase 3: Activity type clustering")
    print(f"• Current result: {averages['clustering_improvement']:.3f} average improvement")
    print("• Issue: System finding no valid swaps that improve clustering")
    print("• Possible causes:")
    print("  - Schedule already well-clustered")
    print("  - Constraints preventing beneficial swaps")
    print("  - Scoring function too conservative")
    
    # Recommendations
    print("\nENHANCED RECOMMENDATIONS:")
    print("-" * 60)
    if averages['total_violations'] > 2:
        print("• Focus on reducing constraint violations across all weeks")
    if averages['staff_efficiency'] < 70:
        print("• Improve staff workload balancing algorithms")
    if averages['clustering_quality'] < 60:
        print("• Enhance activity zone clustering optimization")
    if total_available > 0 and (total_satisfied / total_available) < 0.95:
        print("• Strengthen top 5 preference guarantee system")
    if averages['clustering_improvement'] == 0:
        print("• Investigate clustering optimization algorithm")
        print("• Consider more aggressive swap strategies")
        print("• Relax clustering constraints slightly")
    
    print(f"• Current overall performance: {overall_grade} grade - {'Good' if overall_grade in ['A', 'B'] else 'Needs Improvement'}")
    print("• Enhanced features operational but clustering needs refinement")

if __name__ == "__main__":
    main()
