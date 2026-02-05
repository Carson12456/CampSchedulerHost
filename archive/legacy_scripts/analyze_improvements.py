#!/usr/bin/env python3
"""
Analyze current results and identify improvement opportunities
"""

from evaluate_week_success import evaluate_week
import glob

print('ANALYZING CURRENT RESULTS FOR IMPROVEMENT OPPORTUNITIES')
print('=' * 60)

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
            'staff_variance': metrics['staff_variance']
        })
    except:
        continue

# Sort by score (worst first)
results.sort(key=lambda x: x['score'])

print('WORST PERFORMING WEEKS (Biggest Improvement Potential):')
for i, r in enumerate(results[:5]):
    print(f'{i+1}. {r["week"]}: Score {r["score"]} (Gaps: {r["gaps"]}, Violations: {r["violations"]}, Top5 Missed: {r["top5_missed"]})')

print('\nBIGGEST ISSUES ACROSS ALL WEEKS:')
total_gaps = sum(r['gaps'] for r in results)
total_violations = sum(r['violations'] for r in results)
total_top5_missed = sum(r['top5_missed'] for r in results)

print(f'Total Gaps: {total_gaps} (Avg: {total_gaps/len(results):.1f})')
print(f'Total Violations: {total_violations} (Avg: {total_violations/len(results):.1f})')
print(f'Total Top 5 Missed: {total_top5_missed} (Avg: {total_top5_missed/len(results):.1f})')

# Identify primary improvement targets
if total_gaps > 0:
    print('\nPRIMARY TARGET: Eliminate remaining gaps (-1000 points each)')
if total_violations > 0:
    print('SECONDARY TARGET: Fix constraint violations (-25 points each)')
if total_top5_missed > 0:
    print('TERTIARY TARGET: Recover Top 5 activities (-24 points each)')

# Save analysis for targeted improvements
with open('improvement_targets.txt', 'w') as f:
    f.write('IMPROVEMENT TARGETS\n')
    f.write('=' * 40 + '\n')
    for r in results:
        f.write(f'{r["week"]}: Score {r["score"]}, Gaps {r["gaps"]}, Violations {r["violations"]}, Top5 {r["top5_missed"]}\n')

print('\nAnalysis saved to improvement_targets.txt')
