#!/usr/bin/env python3
"""
Final score analysis and targeted improvements
"""

from evaluate_week_success import evaluate_week
import glob

def final_score_analysis():
    """Comprehensive analysis of current scores and improvement targets"""
    print("FINAL SCORE ANALYSIS & TARGETED IMPROVEMENTS")
    print("=" * 60)
    
    week_files = sorted(glob.glob('*_troops.json'))
    results = []
    
    for week_file in week_files:
        try:
            metrics = evaluate_week(week_file)
            results.append({
                'week': week_file.replace('_troops.json', ''),
                'score': metrics['final_score'],
                'gaps': metrics['unnecessary_gaps'],
                'violations': metrics['constraint_violations'],
                'top5_missed': metrics['missing_top5'],
                'excess_days': metrics['excess_cluster_days'],
                'staff_variance': metrics['staff_variance'],
                'preferences': metrics.get('preference_points', 0),
                'constraint_compliance': metrics.get('constraint_compliance_points', 0)
            })
        except Exception as e:
            print(f"Error with {week_file}: {e}")
            continue
    
    # Sort by score (best first)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("CURRENT SCORE RANKINGS:")
    for i, r in enumerate(results, 1):
        if r['score'] > 500:
            status = "EXCELLENT"
        elif r['score'] > 0:
            status = "GOOD"
        elif r['score'] > -200:
            status = "FAIR"
        else:
            status = "POOR"
        print(f"{i:2d}. {status:12} {r['week']:15}: {r['score']:6.1f} (G:{r['gaps']:2d} V:{r['violations']:2d} T5:{r['top5_missed']:2d})")
    
    # Calculate statistics
    avg_score = sum(r['score'] for r in results) / len(results)
    total_gaps = sum(r['gaps'] for r in results)
    total_violations = sum(r['violations'] for r in results)
    total_top5_missed = sum(r['top5_missed'] for r in results)
    
    print(f"\nOVERALL STATISTICS:")
    print(f"Average Score: {avg_score:.1f}")
    print(f"Total Gaps: {total_gaps} (Potential: +{total_gaps * 1000} points)")
    print(f"Total Violations: {total_violations} (Potential: +{total_violations * 25} points)")
    print(f"Total Top 5 Missed: {total_top5_missed} (Potential: +{total_top5_missed * 24} points)")
    
    # Identify improvement opportunities
    print(f"\nIMPROVEMENT OPPORTUNITIES:")
    
    # Perfect weeks (no gaps, no violations, no top5 missed)
    perfect_weeks = [r for r in results if r['gaps'] == 0 and r['violations'] == 0 and r['top5_missed'] == 0]
    print(f"Perfect Weeks: {len(perfect_weeks)}")
    for r in perfect_weeks:
        print(f"  PERFECT {r['week']}: {r['score']}")
    
    # High potential weeks (few issues)
    high_potential = [r for r in results if r['gaps'] <= 2 and r['violations'] <= 2 and r['top5_missed'] <= 2]
    print(f"\nHigh Potential Weeks (<2 issues each): {len(high_potential)}")
    for r in high_potential:
        issues = r['gaps'] + r['violations'] + r['top5_missed']
        print(f"  HIGH {r['week']}: {r['score']} ({issues} total issues)")
    
    # Critical weeks (many issues)
    critical_weeks = [r for r in results if r['gaps'] > 5 or r['violations'] > 5 or r['top5_missed'] > 5]
    print(f"\nCritical Weeks (Need Major Help): {len(critical_weeks)}")
    for r in critical_weeks:
        print(f"  CRITICAL {r['week']}: {r['score']} (G:{r['gaps']} V:{r['violations']} T5:{r['top5_missed']})")
    
    # Calculate theoretical maximum
    potential_improvement = (total_gaps * 1000) + (total_violations * 25) + (total_top5_missed * 24)
    theoretical_max = avg_score + (potential_improvement / len(results))
    
    print(f"\nTHEORETICAL IMPROVEMENT POTENTIAL:")
    print(f"Current Average: {avg_score:.1f}")
    print(f"Theoretical Maximum: {theoretical_max:.1f}")
    print(f"Total Potential: +{potential_improvement} points")
    print(f"Per Week Average: +{potential_improvement/len(results):.1f} points")
    
    # Save detailed analysis
    with open('final_score_analysis.txt', 'w') as f:
        f.write("FINAL SCORE ANALYSIS\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Average Score: {avg_score:.1f}\n")
        f.write(f"Total Gaps: {total_gaps}\n")
        f.write(f"Total Violations: {total_violations}\n")
        f.write(f"Total Top 5 Missed: {total_top5_missed}\n")
        f.write(f"Theoretical Maximum: {theoretical_max:.1f}\n\n")
        
        f.write("WEEKLY BREAKDOWN:\n")
        for r in results:
            f.write(f"{r['week']}: {r['score']} (G:{r['gaps']} V:{r['violations']} T5:{r['top5_missed']})\n")
    
    print(f"\nDetailed analysis saved to final_score_analysis.txt")
    return results

if __name__ == "__main__":
    final_score_analysis()
