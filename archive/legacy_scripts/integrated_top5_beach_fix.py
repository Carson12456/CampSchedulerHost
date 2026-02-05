#!/usr/bin/env python3
"""
Integrated Top 5 Beach Activity Fix System
Combines Aqua Trampoline crisis fix with comprehensive beach activity optimization.
"""

from typing import Dict, List
import logging
from top5_beach_activity_fix import Top5BeachActivityFix
from beach_activity_optimizer import BeachActivityOptimizer


class IntegratedTop5BeachFix:
    """
    Integrated system that addresses Aqua Trampoline crisis and optimizes beach activities.
    """
    
    def __init__(self, schedule):
        self.schedule = schedule
        self.logger = logging.getLogger(__name__)
        
        # Initialize component systems
        self.top5_fixer = Top5BeachActivityFix(schedule)
        self.beach_optimizer = BeachActivityOptimizer(schedule)
        
        # Track overall results
        self.total_fixes_applied = 0
        self.total_violations_created = 0
        self.troops_helped = set()
    
    def apply_integrated_fix(self) -> Dict:
        """
        Apply the complete integrated Top 5 beach activity fix.
        """
        self.logger.info("Starting integrated Top 5 beach activity fix...")
        
        results = {
            'top5_beach_fixes': {},
            'beach_optimizations': {},
            'overall_impact': {},
            'recommendations': []
        }
        
        # Phase 1: Apply Top 5 beach activity constraint relaxation
        self.logger.info("Phase 1: Applying Top 5 beach constraint relaxation...")
        top5_results = self.top5_fixer.apply_top5_beach_fixes()
        results['top5_beach_fixes'] = top5_results
        
        # Update tracking
        self.total_fixes_applied += top5_results['fixes_applied']
        self.total_violations_created += top5_results['constraint_violations']
        self.troops_helped.update(top5_results['troops_helped'])
        
        # Phase 2: Apply comprehensive beach activity optimization
        self.logger.info("Phase 2: Applying beach activity optimization...")
        beach_results = self.beach_optimizer.optimize_beach_activities()
        results['beach_optimizations'] = beach_results
        
        # Phase 3: Calculate overall impact
        self.logger.info("Phase 3: Calculating overall impact...")
        overall_impact = self._calculate_overall_impact(top5_results, beach_results)
        results['overall_impact'] = overall_impact
        
        # Phase 4: Generate recommendations
        self.logger.info("Phase 4: Generating recommendations...")
        recommendations = self._generate_recommendations(top5_results, beach_results)
        results['recommendations'] = recommendations
        
        self.logger.info(f"Integrated fix complete: {self.total_fixes_applied} fixes applied")
        return results
    
    def _calculate_overall_impact(self, top5_results: Dict, beach_results: Dict) -> Dict:
        """
        Calculate the overall impact of the integrated fix.
        """
        # Count unique troops helped
        unique_troops = len(self.troops_helped)
        
        # Calculate Top 5 improvement
        top5_improvement = top5_results.get('fixes_applied', 0)
        
        # Calculate beach optimization impact
        beach_optimizations = (beach_results.get('capacity_optimizations', 0) +
                             beach_results.get('constraint_relaxations', 0) +
                             beach_results.get('scheduling_improvements', 0))
        
        # Calculate violation trade-off
        total_violations = self.total_violations_created
        violation_ratio = total_violations / max(1, self.total_fixes_applied)
        
        return {
            'total_fixes_applied': self.total_fixes_applied,
            'unique_troops_helped': unique_troops,
            'top5_improvements': top5_improvement,
            'beach_optimizations': beach_optimizations,
            'total_violations_created': total_violations,
            'violation_ratio': violation_ratio,
            'effectiveness_score': self._calculate_effectiveness_score(top5_results, beach_results)
        }
    
    def _calculate_effectiveness_score(self, top5_results: Dict, beach_results: Dict) -> float:
        """
        Calculate an effectiveness score for the integrated fix.
        """
        score = 0.0
        
        # Top 5 fixes weighted most heavily (40%)
        top5_score = (top5_results.get('fixes_applied', 0) * 10) / max(1, len(self.troops_helped))
        score += top5_score * 0.4
        
        # Beach optimizations (30%)
        beach_score = (beach_results.get('capacity_optimizations', 0) +
                      beach_results.get('constraint_relaxations', 0) +
                      beach_results.get('scheduling_improvements', 0)) * 5
        score += beach_score * 0.3
        
        # Constraint efficiency (20%) - lower violations is better
        if self.total_violations_created == 0:
            constraint_score = 10.0
        else:
            constraint_score = max(0, 10 - (self.total_violations_created * 2))
        score += constraint_score * 0.2
        
        # Coverage (10%) - percentage of troops helped
        coverage_score = (len(self.troops_helped) / max(1, len(self.schedule.troops))) * 10
        score += coverage_score * 0.1
        
        return round(score, 2)
    
    def _generate_recommendations(self, top5_results: Dict, beach_results: Dict) -> List[str]:
        """
        Generate recommendations based on the fix results.
        """
        recommendations = []
        
        # Aqua Trampoline specific recommendations
        at_fixes = [f for f in top5_results.get('details', []) 
                   if f.get('activity') == 'Aqua Trampoline']
        if len(at_fixes) > 5:
            recommendations.append(
                f"CRITICAL: Aqua Trampoline had {len(at_fixes)} fixes - consider permanent slot 2 allowance for Rank #1 preferences"
            )
        
        # Constraint violation recommendations
        if self.total_violations_created > 10:
            recommendations.append(
                f"WARNING: {self.total_violations_created} constraint violations created - monitor schedule quality"
            )
        
        # Beach capacity recommendations
        if beach_results.get('capacity_optimizations', 0) > 3:
            recommendations.append(
                "Consider increasing beach staff capacity during high-demand periods"
            )
        
        # Scheduling recommendations
        if beach_results.get('scheduling_improvements', 0) > 2:
            recommendations.append(
                "Review beach activity distribution patterns for better balance"
            )
        
        # Effectiveness recommendations
        effectiveness = self._calculate_effectiveness_score(top5_results, beach_results)
        if effectiveness < 5.0:
            recommendations.append(
                "Low effectiveness score - consider more aggressive constraint relaxation"
            )
        elif effectiveness > 8.0:
            recommendations.append(
                "High effectiveness - consider making these changes permanent"
            )
        
        return recommendations
    
    def get_detailed_analysis(self) -> Dict:
        """
        Get detailed analysis of the integrated fix.
        """
        return {
            'top5_beach_analysis': self.top5_fixer.get_fix_summary(),
            'beach_optimization_analysis': self.beach_optimizer.get_optimization_summary(),
            'impact_analysis': {
                'troops_helped': list(self.troops_helped),
                'total_fixes': self.total_fixes_applied,
                'violations_created': self.total_violations_created,
                'fix_success_rate': len(self.troops_helped) / max(1, len(self.schedule.troops))
            }
        }


def apply_integrated_top5_beach_fix(schedule) -> Dict:
    """
    Apply the complete integrated Top 5 beach activity fix to a schedule.
    """
    fixer = IntegratedTop5BeachFix(schedule)
    results = fixer.apply_integrated_fix()
    results['detailed_analysis'] = fixer.get_detailed_analysis()
    return results


if __name__ == "__main__":
    # Example usage
    import json
    from models import Schedule
    
    # Load a schedule (example)
    print("Integrated Top 5 Beach Activity Fix System")
    print("=" * 50)
    print("This system addresses the Aqua Trampoline crisis and optimizes beach activities.")
    print("Run through the main scheduler to see results.")
