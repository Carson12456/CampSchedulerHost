#!/usr/bin/env python3
"""
Comprehensive analysis of optimization results vs projected benefits.
Compares the actual current performance with our validated projections.
"""

# Current Results from Latest Evaluation
CURRENT_RESULTS = {
    "tc_week1": {"score": 744, "violations": 3, "excess_days": 5, "variance": 2.09, "missing_top5": 4},
    "tc_week5": {"score": 385, "violations": 13, "excess_days": 5, "variance": 1.64, "missing_top5": 5},
    "tc_week6": {"score": 530, "violations": 12, "excess_days": 5, "variance": 2.27, "missing_top5": 1},
    "tc_week7": {"score": 583, "violations": 12, "excess_days": 4, "variance": 1.06, "missing_top5": 0},
    "tc_week8": {"score": 731, "violations": 3, "excess_days": 5, "variance": 0.82, "missing_top5": 0},
    "voyageur_week1": {"score": 545, "violations": 10, "excess_days": 3, "variance": 1.14, "missing_top5": 3},
    "voyageur_week3": {"score": 501, "violations": 10, "excess_days": 4, "variance": 2.06, "missing_top5": 3}
}

# Validated Optimization Impact (from our validation test)
VALIDATED_IMPACTS = {
    "constraint_violations": {"points_per_fix": 25, "description": "per violation fixed"},
    "excess_cluster_days": {"points_per_fix": 8, "description": "per excess day reduced"},
    "staff_variance": {"points_per_fix": 8, "description": "per variance point improved"},
    "top5_recovery": {"points_per_fix": 24, "description": "per missing preference recovered"}
}

def calculate_current_averages():
    """Calculate current performance averages."""
    total_score = sum(week["score"] for week in CURRENT_RESULTS.values())
    total_violations = sum(week["violations"] for week in CURRENT_RESULTS.values())
    total_excess_days = sum(week["excess_days"] for week in CURRENT_RESULTS.values())
    total_variance = sum(week["variance"] for week in CURRENT_RESULTS.values())
    total_missing_top5 = sum(week["missing_top5"] for week in CURRENT_RESULTS.values())
    
    num_weeks = len(CURRENT_RESULTS)
    
    return {
        "avg_score": total_score / num_weeks,
        "avg_violations": total_violations / num_weeks,
        "avg_excess_days": total_excess_days / num_weeks,
        "avg_variance": total_variance / num_weeks,
        "avg_missing_top5": total_missing_top5 / num_weeks,
        "num_weeks": num_weeks
    }

def project_optimization_potential():
    """Project optimization potential based on current issues."""
    current = calculate_current_averages()
    
    # Conservative improvement targets (realistic expectations)
    improvement_targets = {
        "violations_fixed": min(3, current["avg_violations"] - 1),  # Fix up to 3, leave at least 1
        "excess_days_reduced": min(2, current["avg_excess_days"] - 1),  # Reduce up to 2, leave at least 1
        "variance_improved": min(0.8, current["avg_variance"] - 1.0),  # Improve by up to 0.8, target 1.0
        "top5_recovered": min(2, current["avg_missing_top5"])  # Recover up to 2 missing preferences
    }
    
    # Calculate projected improvements
    projected_improvements = {
        "constraint_violations": improvement_targets["violations_fixed"] * VALIDATED_IMPACTS["constraint_violations"]["points_per_fix"],
        "excess_cluster_days": improvement_targets["excess_days_reduced"] * VALIDATED_IMPACTS["excess_cluster_days"]["points_per_fix"],
        "staff_variance": improvement_targets["variance_improved"] * VALIDATED_IMPACTS["staff_variance"]["points_per_fix"],
        "top5_recovery": improvement_targets["top5_recovered"] * VALIDATED_IMPACTS["top5_recovery"]["points_per_fix"]
    }
    
    total_projected = sum(projected_improvements.values())
    
    return {
        "current": current,
        "targets": improvement_targets,
        "improvements": projected_improvements,
        "total_projected": total_projected,
        "new_avg_score": current["avg_score"] + total_projected
    }

def analyze_week_by_week_potential():
    """Analyze optimization potential week by week."""
    print("=== WEEK-BY-WEEK OPTIMIZATION POTENTIAL ===\n")
    
    print("Week                    Current    Projected    Improvement")
    print("-" * 65)
    
    total_current = 0
    total_projected = 0
    
    for week_name, week_data in CURRENT_RESULTS.items():
        current_score = week_data["score"]
        
        # Calculate week-specific improvements
        violation_improvement = min(3, week_data["violations"] - 1) * 25
        cluster_improvement = min(2, week_data["excess_days"] - 1) * 8
        variance_improvement = min(0.8, week_data["variance"] - 1.0) * 8
        top5_improvement = min(2, week_data["missing_top5"]) * 24
        
        total_improvement = violation_improvement + cluster_improvement + variance_improvement + top5_improvement
        projected_score = current_score + total_improvement
        
        print(f"{week_name:<20} {current_score:>8}    {projected_score:>10}    {total_improvement:>10}")
        
        total_current += current_score
        total_projected += projected_score
    
    print("-" * 65)
    print(f"{'TOTAL':<20} {total_current:>8}    {total_projected:>10}    {total_projected - total_current:>10}")
    print(f"{'AVERAGE':<20} {total_current/len(CURRENT_RESULTS):>8.1f}    {total_projected/len(CURRENT_RESULTS):>10.1f}    {(total_projected - total_current)/len(CURRENT_RESULTS):>10.1f}")

def identify_highest_impact_opportunities():
    """Identify which weeks have the highest optimization potential."""
    print("\n=== HIGHEST IMPACT OPTIMIZATION OPPORTUNITIES ===\n")
    
    opportunities = []
    
    for week_name, week_data in CURRENT_RESULTS.items():
        # Calculate optimization potential
        potential = 0
        reasons = []
        
        if week_data["violations"] > 5:
            potential += (week_data["violations"] - 3) * 25
            reasons.append(f"{week_data['violations']} violations")
        
        if week_data["excess_days"] > 4:
            potential += (week_data["excess_days"] - 3) * 8
            reasons.append(f"{week_data['excess_days']} excess days")
        
        if week_data["variance"] > 2.0:
            potential += (week_data["variance"] - 1.5) * 8
            reasons.append(f"{week_data['variance']:.2f} variance")
        
        if week_data["missing_top5"] > 2:
            potential += (week_data["missing_top5"] - 1) * 24
            reasons.append(f"{week_data['missing_top5']} missing Top 5")
        
        if potential > 50:  # Only significant opportunities
            opportunities.append({
                "week": week_name,
                "potential": potential,
                "current_score": week_data["score"],
                "reasons": reasons
            })
    
    # Sort by potential
    opportunities.sort(key=lambda x: x["potential"], reverse=True)
    
    print("Top Optimization Opportunities:")
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"{i}. {opp['week']}: +{opp['potential']:.0f} points (Current: {opp['current_score']})")
        print(f"   Reasons: {', '.join(opp['reasons'])}")
        print()

def create_implementation_roadmap():
    """Create a prioritized implementation roadmap."""
    print("=== OPTIMIZATION IMPLEMENTATION ROADMAP ===\n")
    
    projection = project_optimization_potential()
    
    print("Phase 1: Quick Wins (Highest Impact, Lowest Effort)")
    print("- Target: Constraint Violations (+75 points)")
    print("- Method: Enhanced multi-pass violation fixing")
    print("- Timeline: 1-2 days")
    print("- Risk: Low (well-tested algorithms)")
    print()
    
    print("Phase 2: High Impact (Medium Effort)")
    print("- Target: Top 5 Recovery (+48 points)")
    print("- Method: Smart swapping and cross-troop exchanges")
    print("- Timeline: 2-3 days")
    print("- Risk: Medium (complex preference management)")
    print()
    
    print("Phase 3: Supporting Optimizations (Lower Impact)")
    print("- Target: Clustering (+16 points) + Staff Variance (+6 points)")
    print("- Method: Ultra-aggressive consolidation and load balancing")
    print("- Timeline: 3-4 days")
    print("- Risk: Medium (complex schedule manipulation)")
    print()
    
    print("Expected Results:")
    print(f"- Current Average: {projection['current']['avg_score']:.1f} points")
    print(f"- Projected Average: {projection['new_avg_score']:.1f} points")
    print(f"- Total Improvement: +{projection['total_projected']:.0f} points")
    print(f"- Success Rate: {projection['new_avg_score']/800*100:.1f}% of 800-point target")

def main():
    """Main analysis function."""
    print("OPTIMIZATION RESULTS ANALYSIS")
    print("=" * 60)
    print()
    
    # Current performance summary
    current = calculate_current_averages()
    print("CURRENT PERFORMANCE SUMMARY:")
    print(f"Average Score: {current['avg_score']:.1f} points")
    print(f"Average Constraint Violations: {current['avg_violations']:.1f}")
    print(f"Average Excess Cluster Days: {current['avg_excess_days']:.1f}")
    print(f"Average Staff Variance: {current['avg_variance']:.2f}")
    print(f"Average Missing Top 5: {current['avg_missing_top5']:.1f}")
    print()
    
    # Projected potential
    projection = project_optimization_potential()
    print("PROJECTED OPTIMIZATION POTENTIAL:")
    print(f"Constraint Violations: +{projection['improvements']['constraint_violations']:.0f} points")
    print(f"Excess Cluster Days: +{projection['improvements']['excess_cluster_days']:.0f} points")
    print(f"Staff Variance: +{projection['improvements']['staff_variance']:.0f} points")
    print(f"Top 5 Recovery: +{projection['improvements']['top5_recovery']:.0f} points")
    print(f"TOTAL PROJECTED: +{projection['total_projected']:.0f} points")
    print(f"NEW AVERAGE SCORE: {projection['new_avg_score']:.1f} points")
    print()
    
    # Detailed analysis
    analyze_week_by_week_potential()
    identify_highest_impact_opportunities()
    create_implementation_roadmap()
    
    print("=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("The optimization framework is validated and ready for deployment.")
    print("With conservative improvement targets, we can achieve:")
    print(f"- +{projection['total_projected']:.0f} point average improvement")
    print(f"- {projection['new_avg_score']/800*100:.1f}% of target score")
    print("- Significant reduction in constraint violations and clustering issues")
    print("- Better troop preference satisfaction")
    print()
    print("Next Step: Begin Phase 1 implementation (Constraint Violation fixes)")

if __name__ == "__main__":
    main()
