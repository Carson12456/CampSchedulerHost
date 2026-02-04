#!/usr/bin/env python3
"""
Comprehensive analysis of how scoring was affected by optimizations.
Compares actual evaluation results with our projections.
"""

# Actual evaluation results from latest run
ACTUAL_RESULTS = {
    "tc_week1": {"score": 677, "violations": 7, "excess_days": 3, "variance": 1.09, "missing_top5": 0},
    "tc_week2": {"score": 672, "violations": 4, "excess_days": 4, "variance": 0.67, "missing_top5": 0},
    "tc_week3": {"score": 466, "violations": 10, "excess_days": 3, "variance": 2.07, "missing_top5": 5},
    "tc_week4": {"score": 488, "violations": 10, "excess_days": 5, "variance": 2.09, "missing_top5": 4},
    "tc_week5": {"score": 385, "violations": 13, "excess_days": 5, "variance": 1.64, "missing_top5": 5},
    "tc_week6": {"score": 530, "violations": 12, "excess_days": 5, "variance": 2.27, "missing_top5": 1},
    "tc_week7": {"score": 583, "violations": 12, "excess_days": 4, "variance": 1.06, "missing_top5": 0},
    "tc_week8": {"score": 731, "violations": 3, "excess_days": 5, "variance": 0.82, "missing_top5": 0},
    "voyageur_week1": {"score": 545, "violations": 10, "excess_days": 3, "variance": 1.14, "missing_top5": 3},
    "voyageur_week3": {"score": 501, "violations": 10, "excess_days": 4, "variance": 2.06, "missing_top5": 3}
}

# Previous baseline results (before optimizations)
BASELINE_RESULTS = {
    "tc_week1": {"score": 744, "violations": 3, "excess_days": 5, "variance": 2.09, "missing_top5": 4},
    "tc_week5": {"score": 385, "violations": 13, "excess_days": 5, "variance": 1.64, "missing_top5": 5},
    "tc_week6": {"score": 530, "violations": 12, "excess_days": 5, "variance": 2.27, "missing_top5": 1},
    "tc_week7": {"score": 583, "violations": 12, "excess_days": 4, "variance": 1.06, "missing_top5": 0},
    "tc_week8": {"score": 731, "violations": 3, "excess_days": 5, "variance": 0.82, "missing_top5": 0},
    "voyageur_week1": {"score": 545, "violations": 10, "excess_days": 3, "variance": 1.14, "missing_top5": 3},
    "voyageur_week3": {"score": 501, "violations": 10, "excess_days": 4, "variance": 2.06, "missing_top5": 3}
}

# Scoring weights
SCORING_WEIGHTS = {
    "constraint_violations": -25,  # Points per violation
    "excess_cluster_days": -8,    # Points per excess day
    "staff_variance": -8,          # Points per variance point
    "missing_top5": -24            # Points per missing Top 5 (triple penalty)
}

def calculate_score_components(week_data):
    """Calculate individual score components from week data."""
    components = {}
    components["constraint_penalty"] = week_data["violations"] * SCORING_WEIGHTS["constraint_violations"]
    components["cluster_penalty"] = week_data["excess_days"] * SCORING_WEIGHTS["excess_cluster_days"]
    components["variance_penalty"] = week_data["variance"] * SCORING_WEIGHTS["staff_variance"]
    components["top5_penalty"] = week_data["missing_top5"] * SCORING_WEIGHTS["missing_top5"]
    
    total_penalty = sum(components.values())
    components["total_penalty"] = total_penalty
    components["estimated_base_score"] = week_data["score"] - total_penalty
    
    return components

def analyze_scoring_impact():
    """Analyze the impact of optimizations on scoring components."""
    print("SCORING IMPACT ANALYSIS")
    print("=" * 80)
    print()
    
    print("ACTUAL vs BASELINE COMPARISON")
    print("-" * 80)
    print("Week                    Actual    Baseline    Change    Violations    Top5 Missed")
    print("-" * 80)
    
    total_actual = 0
    total_baseline = 0
    total_violation_change = 0
    total_top5_change = 0
    
    for week_name in ACTUAL_RESULTS:
        if week_name in BASELINE_RESULTS:
            actual = ACTUAL_RESULTS[week_name]
            baseline = BASELINE_RESULTS[week_name]
            
            score_change = actual["score"] - baseline["score"]
            violation_change = actual["violations"] - baseline["violations"]
            top5_change = actual["missing_top5"] - baseline["missing_top5"]
            
            print(f"{week_name:<20} {actual['score']:>8}    {baseline['score']:>8}    {score_change:>+7}    {actual['violations']:>10}    {actual['missing_top5']:>11}")
            
            total_actual += actual["score"]
            total_baseline += baseline["score"]
            total_violation_change += violation_change
            total_top5_change += top5_change
    
    print("-" * 80)
    print(f"{'TOTAL':<20} {total_actual:>8}    {total_baseline:>8}    {total_actual - total_baseline:>+7}")
    print(f"{'AVERAGE':<20} {total_actual/len(ACTUAL_RESULTS):>8.1f}    {total_baseline/len(BASELINE_RESULTS):>8.1f}    {(total_actual - total_baseline)/len(ACTUAL_RESULTS):>+7.1f}")
    print()
    
    return total_actual, total_baseline

def detailed_score_breakdown():
    """Provide detailed breakdown of scoring components."""
    print("DETAILED SCORE COMPONENT ANALYSIS")
    print("-" * 80)
    print("Week                    Score    Constraint    Cluster    Variance    Top5")
    print("-" * 80)
    
    for week_name, week_data in ACTUAL_RESULTS.items():
        components = calculate_score_components(week_data)
        
        print(f"{week_name:<20} {week_data['score']:>6}    {components['constraint_penalty']:>+10}    {components['cluster_penalty']:>+8}    {components['variance_penalty']:>+9}    {components['top5_penalty']:>+4}")
    
    print()
    
    # Calculate averages
    avg_components = {}
    for key in ["constraint_penalty", "cluster_penalty", "variance_penalty", "top5_penalty"]:
        avg_components[key] = sum(calculate_score_components(w)[key] for w in ACTUAL_RESULTS.values()) / len(ACTUAL_RESULTS)
    
    print("AVERAGE COMPONENTS:")
    print(f"  Constraint Penalty: {avg_components['constraint_penalty']:+.1f} points")
    print(f"  Cluster Penalty: {avg_components['cluster_penalty']:+.1f} points")
    print(f"  Variance Penalty: {avg_components['variance_penalty']:+.1f} points")
    print(f"  Top 5 Penalty: {avg_components['top5_penalty']:+.1f} points")
    print(f"  Total Penalty: {sum(avg_components.values()):+.1f} points")
    print()

def identify_optimization_successes():
    """Identify where optimizations succeeded and where they failed."""
    print("OPTIMIZATION SUCCESS ANALYSIS")
    print("-" * 80)
    
    successes = []
    failures = []
    
    for week_name, week_data in ACTUAL_RESULTS.items():
        if week_name in BASELINE_RESULTS:
            baseline = BASELINE_RESULTS[week_name]
            
            # Check for improvements
            improvements = []
            regressions = []
            
            if week_data["violations"] < baseline["violations"]:
                improvements.append(f"Violations: {baseline['violations']} to {week_data['violations']}")
            elif week_data["violations"] > baseline["violations"]:
                regressions.append(f"Violations: {baseline['violations']} to {week_data['violations']}")
            
            if week_data["missing_top5"] < baseline["missing_top5"]:
                improvements.append(f"Top5: {baseline['missing_top5']} to {week_data['missing_top5']}")
            elif week_data["missing_top5"] > baseline["missing_top5"]:
                regressions.append(f"Top5: {baseline['missing_top5']} to {week_data['missing_top5']}")
            
            if week_data["excess_days"] < baseline["excess_days"]:
                improvements.append(f"Cluster: {baseline['excess_days']} to {week_data['excess_days']}")
            elif week_data["excess_days"] > baseline["excess_days"]:
                regressions.append(f"Cluster: {baseline['excess_days']} to {week_data['excess_days']}")
            
            score_change = week_data["score"] - baseline["score"]
            
            if improvements and score_change > 0:
                successes.append({
                    "week": week_name,
                    "score_change": score_change,
                    "improvements": improvements
                })
            elif regressions or score_change < -20:
                failures.append({
                    "week": week_name,
                    "score_change": score_change,
                    "regressions": regressions
                })
    
    print("OPTIMIZATION SUCCESSES:")
    for success in successes[:5]:  # Top 5 successes
        print(f"  {success['week']}: +{success['score_change']} points - {', '.join(success['improvements'])}")
    
    print("\nOPTIMIZATION CONCERNS:")
    for failure in failures[:5]:  # Top 5 concerns
        if failure['regressions']:
            print(f"  {failure['week']}: {failure['score_change']:+} points - {', '.join(failure['regressions'])}")
        else:
            print(f"  {failure['week']}: {failure['score_change']:+} points - No significant improvements")
    
    print()

def calculate_optimization_roi():
    """Calculate return on investment for each optimization type."""
    print("OPTIMIZATION ROI ANALYSIS")
    print("-" * 80)
    
    # Calculate total penalties by type
    total_constraint_penalty = sum(calculate_score_components(w)["constraint_penalty"] for w in ACTUAL_RESULTS.values())
    total_cluster_penalty = sum(calculate_score_components(w)["cluster_penalty"] for w in ACTUAL_RESULTS.values())
    total_variance_penalty = sum(calculate_score_components(w)["variance_penalty"] for w in ACTUAL_RESULTS.values())
    total_top5_penalty = sum(calculate_score_components(w)["top5_penalty"] for w in ACTUAL_RESULTS.values())
    
    total_penalty = total_constraint_penalty + total_cluster_penalty + total_variance_penalty + total_top5_penalty
    
    print("TOTAL PENALTY BREAKDOWN:")
    print(f"  Constraint Violations: {total_constraint_penalty:.0f} points ({abs(total_constraint_penalty/total_penalty*100):.1f}%)")
    print(f"  Excess Cluster Days: {total_cluster_penalty:.0f} points ({abs(total_cluster_penalty/total_penalty*100):.1f}%)")
    print(f"  Staff Variance: {total_variance_penalty:.0f} points ({abs(total_variance_penalty/total_penalty*100):.1f}%)")
    print(f"  Missing Top 5: {total_top5_penalty:.0f} points ({abs(total_top5_penalty/total_penalty*100):.1f}%)")
    print(f"  TOTAL PENALTY: {total_penalty:.0f} points")
    print()
    
    # Calculate optimization potential
    avg_violations = sum(w["violations"] for w in ACTUAL_RESULTS.values()) / len(ACTUAL_RESULTS)
    avg_excess_days = sum(w["excess_days"] for w in ACTUAL_RESULTS.values()) / len(ACTUAL_RESULTS)
    avg_missing_top5 = sum(w["missing_top5"] for w in ACTUAL_RESULTS.values()) / len(ACTUAL_RESULTS)
    
    print("OPTIMIZATION POTENTIAL:")
    print(f"  Fix 3 constraint violations: +{3 * 25} points")
    print(f"  Reduce 2 excess cluster days: +{2 * 8} points")
    print(f"  Recover 2 Top 5 preferences: +{2 * 24} points")
    print(f"  TOTAL POTENTIAL: +{(3 * 25) + (2 * 8) + (2 * 24)} points")
    print()

def main():
    """Main analysis function."""
    total_actual, total_baseline = analyze_scoring_impact()
    detailed_score_breakdown()
    identify_optimization_successes()
    calculate_optimization_roi()
    
    print("=" * 80)
    print("SCORING IMPACT SUMMARY")
    print("=" * 80)
    
    overall_change = total_actual - total_baseline
    avg_change = overall_change / len(ACTUAL_RESULTS)
    
    print(f"Overall Score Change: {overall_change:+.0f} points ({avg_change:+.1f} per week)")
    
    if overall_change > 0:
        print("OPTIMIZATIONS SHOWING POSITIVE IMPACT")
    elif overall_change < -50:
        print("OPTIMIZATIONS SHOWING NEGATIVE IMPACT - INVESTIGATION NEEDED")
    else:
        print("OPTIMIZATIONS SHOWING NEUTRAL IMPACT")
    
    print(f"Current Average: {total_actual/len(ACTUAL_RESULTS):.1f} points")
    print(f"Target Achievement: {total_actual/len(ACTUAL_RESULTS)/800*100:.1f}% of 800-point goal")
    
    print("\nKEY INSIGHTS:")
    print("1. Constraint violations remain the biggest scoring penalty")
    print("2. Top 5 recovery shows mixed results - some weeks improved, others regressed")
    print("3. Clustering optimization needs more aggressive implementation")
    print("4. Staff variance is generally well-controlled")
    print("5. Focus should remain on constraint violation reduction for highest ROI")

if __name__ == "__main__":
    main()
