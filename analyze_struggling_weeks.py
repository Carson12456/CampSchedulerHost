#!/usr/bin/env python3
"""
Analyze struggling weeks and identify specific issues
"""

from evaluate_week_success import evaluate_week
import glob

print('STRUGGLING WEEKS ANALYSIS')
print('=' * 50)

week_files = sorted(glob.glob('*_troops.json'))
struggling_weeks = []

for week_file in week_files:
    try:
        metrics = evaluate_week(week_file)
        if metrics['final_score'] <= 0:
            struggling_weeks.append({
                'file': week_file,
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
struggling_weeks.sort(key=lambda x: x['score'])

print('WORST PERFORMING WEEKS (Need Immediate Fix):')
for i, week in enumerate(struggling_weeks, 1):
    print(f'{i:2d}. {week["week"]:20}: {week["score"]:7.1f} (G:{week["gaps"]:2d} V:{week["violations"]:2d} T5:{week["top5_missed"]:2d})')

print(f'\nTOTAL STRUGGLING WEEKS: {len(struggling_weeks)}')

# Calculate total potential improvement
total_gaps = sum(w['gaps'] for w in struggling_weeks)
total_violations = sum(w['violations'] for w in struggling_weeks)
total_top5_missed = sum(w['top5_missed'] for w in struggling_weeks)

print(f'Total Issues to Fix:')
print(f'  Gaps: {total_gaps} (Potential: +{total_gaps * 1000} points)')
print(f'  Violations: {total_violations} (Potential: +{total_violations * 25} points)')
print(f'  Top 5 Missed: {total_top5_missed} (Potential: +{total_top5_missed * 24} points)')

total_potential = (total_gaps * 1000) + (total_violations * 25) + (total_top5_missed * 24)
print(f'Total Score Potential: +{total_potential} points')

# Save analysis for targeted fixing
with open('struggling_weeks_analysis.txt', 'w') as f:
    f.write('STRUGGLING WEEKS ANALYSIS\n')
    f.write('=' * 30 + '\n\n')
    for week in struggling_weeks:
        f.write(f'{week["week"]}: {week["score"]} (G:{week["gaps"]} V:{week["violations"]} T5:{week["top5_missed"]})\n')

print('\nAnalysis saved to struggling_weeks_analysis.txt')
