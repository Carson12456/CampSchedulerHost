import sys
import os
import json
from pprint import pprint

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from utils.regression_checker import evaluate_week

def debug_week1():
    week_file = "data/troops/tc_week1_troops.json"
    print(f"Analyzing {week_file}...")
    
    metrics = evaluate_week(week_file)
    
    print("\n--- Score Components ---")
    pprint(metrics.get("score_components", {}))
    
    print("\n--- Key Metrics ---")
    print(f"Final Score: {metrics.get('final_score')}")
    print(f"Top 5 Pct: {metrics.get('top5_pct')}")
    print(f"Excess Cluster Days: {metrics.get('excess_cluster_days')}")
    print(f"Staff Variance: {metrics.get('staff_variance')}")
    print(f"Soft Violations: {metrics.get('soft_violations')}")
    
    print("\n--- Preference Breakdown ---")
    print(f"Preference Points Accumulated: {metrics.get('preference_points_accumulated')}")
    print(f"Missing Top 5: {metrics.get('missing_top5')}")
    print(f"Missing Top 10: {metrics.get('missing_top10')}")
    
    print("\n--- Violation Details ---")
    pprint(metrics.get("violation_details", []))

if __name__ == "__main__":
    debug_week1()
