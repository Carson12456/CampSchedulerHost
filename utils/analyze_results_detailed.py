
import sys
import os
import glob
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.regression_checker import evaluate_week

def analyze_all():
    troops_dir = os.path.join("data", "troops")
    troop_files = glob.glob(os.path.join(troops_dir, "*.json"))
    
    # Sort for consistent output
    troop_files.sort()
    
    print(f"\n{'Week':<25} | {'Score':<6} | {'Top5%':<6} | {'Top10%':<6} | {'Top15%':<6} | {'ExcDays':<7} | {'Gap':<3} | {'BeachWarn':<9}")
    print("-" * 105)
    
    avgs = {'score': 0, 't5': 0, 't10': 0, 't15': 0, 'exc': 0, 'gaps': 0, 'warn': 0}
    count = 0
    
    for troop_file in troop_files:
        week_name = os.path.splitext(os.path.basename(troop_file))[0]
        schedule_file = os.path.join("data", "schedules", f"{week_name}_schedule.json")
        
        # We need to make sure we are checking the relative path that evaluate_week expects or pass absolute
        # evaluate_week uses "data/schedules/{week}_schedule.json" relative to CWD
        
        if not os.path.exists(schedule_file):
            continue
            
        try:
            m = evaluate_week(troop_file)
            
            # Format
            score = m.get('final_score', 0)
            t5 = m.get('top5_pct', 0)
            t10 = m.get('top10_pct', 0)
            t15 = m.get('top15_pct', 0)
            exc = m.get('excess_cluster_days', 0)
            gap = m.get('cluster_gaps', 0)
            warn = m.get('soft_violations', 0)
            
            invalid = ""
            if score == -1000:
                invalid = m.get('invalid_reason', 'Unknown Invalid')
                
            print(f"{week_name:<25} | {score:<6} | {t5:5.1f}% | {t10:5.1f}% | {t15:5.1f}% | {exc:<7} | {gap:<3} | {warn:<9} | {invalid}")
            
            avgs['score'] += score
            avgs['t5'] += t5
            avgs['t10'] += t10
            avgs['t15'] += t15
            avgs['exc'] += exc
            avgs['gaps'] += gap
            avgs['warn'] += warn
            count += 1
        except Exception as e:
            print(f"Error {week_name}: {e}")

    if count > 0:
        print("-" * 105)
        print(f"{'AVERAGE':<25} | {avgs['score']/count:6.1f} | {avgs['t5']/count:5.1f}% | {avgs['t10']/count:5.1f}% | {avgs['t15']/count:5.1f}% | {avgs['exc']/count:<7.1f} | {avgs['gaps']/count:<3.1f} | {avgs['warn']/count:<9.1f}")
    else:
        print("No schedules found to analyze.")

if __name__ == "__main__":
    analyze_all()
