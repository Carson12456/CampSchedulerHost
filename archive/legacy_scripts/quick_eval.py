from evaluate_week_success import evaluate_week

result = evaluate_week('tc_week5_troops.json')
print(f'Score: {result["final_score"]}')
print(f'Top 5: {result["top5_pct"]:.1f}%')
print(f'Top 10: {result["top10_pct"]:.1f}%')
print(f'Top 15: {result["top15_pct"]:.1f}%')
print(f'Constraint Violations: {result["constraint_violations"]}')
print(f'Excess Cluster Days: {result["excess_cluster_days"]}')
print(f'Unnecessary Gaps: {result["unnecessary_gaps"]}')
