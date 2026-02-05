#!/usr/bin/env python3
"""
Calculate average quality scores across all weeks
"""

import json
import os
import glob
from typing import Dict, List

def extract_quality_score_from_output(output_file: str) -> float:
    """Extract quality score from scheduler output file."""
    try:
        with open(output_file, 'r') as f:
            content = f.read()
        
        # Look for the quality score line
        for line in content.split('\n'):
            if 'Overall quality score:' in line:
                # Extract the score (e.g., "Overall quality score: 71.6 (Grade: C)")
                parts = line.split('Overall quality score:')[1].strip()
                score = float(parts.split()[0])
                return score
    except Exception as e:
        print(f"Error extracting score from {output_file}: {e}")
    
    return 0.0

def extract_all_metrics_from_output(output_file: str) -> Dict[str, float]:
    """Extract all performance metrics from scheduler output file."""
    metrics = {
        'quality_score': 0.0,
        'schedule_quality_percent': 0.0,
        'staff_efficiency': 0.0,
        'clustering_quality': 0.0,
        'total_violations': 0,
        'violations_fixed': 0,
        'ml_confidence': 0.0,
        'adaptive_score': 0.0
    }
    
    try:
        with open(output_file, 'r') as f:
            content = f.read()
        
        for line in content.split('\n'):
            if 'Overall quality score:' in line:
                parts = line.split('Overall quality score:')[1].strip()
                metrics['quality_score'] = float(parts.split()[0])
            elif 'Schedule Quality Score:' in line:
                parts = line.split('Schedule Quality Score:')[1].strip()
                metrics['schedule_quality_percent'] = float(parts.split('%')[0])
            elif 'Staff Efficiency:' in line:
                parts = line.split('Staff Efficiency:')[1].strip()
                metrics['staff_efficiency'] = float(parts.split('%')[0])
            elif 'Clustering Quality:' in line:
                parts = line.split('Clustering Quality:')[1].strip()
                metrics['clustering_quality'] = float(parts.split('%')[0])
            elif 'Total Violations:' in line:
                parts = line.split('Total Violations:')[1].strip()
                metrics['total_violations'] = int(parts.split()[0])
            elif 'Violations Fixed:' in line:
                parts = line.split('Violations Fixed:')[1].strip()
                metrics['violations_fixed'] = int(parts.split()[0])
            elif 'Model confidence level:' in line:
                parts = line.split('Model confidence level:')[1].strip()
                metrics['ml_confidence'] = float(parts)
            elif 'Adaptive system score:' in line:
                parts = line.split('Adaptive system score:')[1].strip()
                metrics['adaptive_score'] = float(parts)
                
    except Exception as e:
        print(f"Error extracting metrics from {output_file}: {e}")
    
    return metrics

def main():
    """Calculate and display average scores across all weeks."""
    print("=== AVERAGE QUALITY SCORES ACROSS ALL WEEKS ===\n")
    
    # Find all output files (we'll need to run the scheduler and capture output)
    # For now, let's manually extract from the recent runs
    
    # Manually extracted data from recent runs
    weeks_data = [
        {
            'week': 'Week 1',
            'quality_score': 69.2,
            'schedule_quality_percent': 60.6,
            'staff_efficiency': 62.6,
            'clustering_quality': 56.7,
            'total_violations': 2,
            'violations_fixed': 0,
            'ml_confidence': 0.82,
            'adaptive_score': 64.33
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
            'adaptive_score': 67.34
        },
        {
            'week': 'Week 3',
            'quality_score': 66.5,
            'schedule_quality_percent': 62.3,
            'staff_efficiency': 26.1,
            'clustering_quality': 53.3,
            'total_violations': 3,
            'violations_fixed': 0,
            'ml_confidence': 1.00,
            'adaptive_score': 63.78
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
        'adaptive_score': sum(w['adaptive_score'] for w in weeks_data) / num_weeks
    }
    
    # Display individual week results
    print("INDIVIDUAL WEEK RESULTS:")
    print("-" * 80)
    print(f"{'Week':<10} {'Quality':<8} {'Schedule':<8} {'Staff':<8} {'Cluster':<8} {'Violations':<12} {'ML Conf':<8} {'Adaptive':<8}")
    print(f"{'':<10} {'Score':<8} {'Quality%':<8} {'Eff%':<8} {'Quality%':<8} {'Total':<6} {'Fixed':<6} {'idence':<8} {'Score':<8}")
    print("-" * 80)
    
    for week_data in weeks_data:
        print(f"{week_data['week']:<10} {week_data['quality_score']:<8.1f} "
              f"{week_data['schedule_quality_percent']:<8.1f} {week_data['staff_efficiency']:<8.1f} "
              f"{week_data['clustering_quality']:<8.1f} {week_data['total_violations']:<6} "
              f"{week_data['violations_fixed']:<6} {week_data['ml_confidence']:<8.2f} "
              f"{week_data['adaptive_score']:<8.1f}")
    
    # Display averages
    print("\nAVERAGE RESULTS ACROSS ALL WEEKS:")
    print("=" * 80)
    print(f"Average Quality Score: {averages['quality_score']:.1f}")
    print(f"Average Schedule Quality %: {averages['schedule_quality_percent']:.1f}%")
    print(f"Average Staff Efficiency: {averages['staff_efficiency']:.1f}%")
    print(f"Average Clustering Quality: {averages['clustering_quality']:.1f}%")
    print(f"Average Total Violations: {averages['total_violations']:.1f}")
    print(f"Average Violations Fixed: {averages['violations_fixed']:.1f}")
    print(f"Average ML Confidence: {averages['ml_confidence']:.2f}")
    print(f"Average Adaptive Score: {averages['adaptive_score']:.1f}")
    
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
    print("\nANALYSIS:")
    print("-" * 40)
    print(f"• Best performing week: {max(weeks_data, key=lambda x: x['quality_score'])['week']} "
          f"({max(w['quality_score'] for w in weeks_data):.1f})")
    print(f"• Week needing most improvement: {min(weeks_data, key=lambda x: x['quality_score'])['week']} "
          f"({min(w['quality_score'] for w in weeks_data):.1f})")
    print(f"• Total violations across all weeks: {sum(w['total_violations'] for w in weeks_data)}")
    print(f"• Average ML confidence: {averages['ml_confidence']:.2f} "
          f"({'High' if averages['ml_confidence'] > 0.7 else 'Medium' if averages['ml_confidence'] > 0.4 else 'Low'})")
    
    # Recommendations
    print("\nRECOMMENDATIONS:")
    print("-" * 40)
    if averages['total_violations'] > 2:
        print("• Focus on reducing constraint violations across all weeks")
    if averages['staff_efficiency'] < 70:
        print("• Improve staff workload balancing algorithms")
    if averages['clustering_quality'] < 60:
        print("• Enhance activity zone clustering optimization")
    if averages['ml_confidence'] < 0.7:
        print("• Collect more historical data to improve ML prediction accuracy")
    
    print(f"• Current overall performance: {overall_grade} grade - {'Good' if overall_grade in ['A', 'B'] else 'Needs Improvement'}")

if __name__ == "__main__":
    main()
