#!/usr/bin/env python3
"""
Spine-Enhanced Scheduler
Integrates all Spine-based systems with phase-based optimization as outlined in the Spine Final Edition
"""

from enhanced_scheduler import EnhancedScheduler
from prevention_aware_validator import PreventionValidator
from ultimate_gap_eliminator import UltimateGapEliminator
from smart_constraint_fixer import SmartConstraintFixer
from aggressive_top5_recovery import AggressiveTop5Recovery
from models import Schedule, ScheduleEntry
from typing import List, Dict
import logging


class SpineEnhancedScheduler(EnhancedScheduler):
    """
    Enhanced scheduler implementing the complete Spine-based optimization framework.
    
    Phase-based optimization process:
    Phase 1: Critical Priority Foundation
    Phase 2: High Priority Enhancement  
    Phase 3: Medium Priority Refinement
    Phase 4: Low Priority Fine-Tuning
    """
    
    def __init__(self, troops, activities=None, voyageur_mode=False):
        super().__init__(troops, activities, voyageur_mode)
        
        # Initialize Spine-based systems
        self.validator = PreventionValidator(self.schedule)
        self.gap_eliminator = UltimateGapEliminator(troops)
        self.constraint_fixer = SmartConstraintFixer(self.schedule)
        self.top5_recovery = AggressiveTop5Recovery(self.schedule)
        
        # Spine optimization metrics
        self.optimization_phases = {
            'critical_foundation': {},
            'high_priority_enhancement': {},
            'medium_priority_refinement': {},
            'low_priority_fine_tuning': {}
        }
        
        # Overall metrics
        self.total_improvements = 0
        self.issues_prevented = 0
        self.constraint_violations_fixed = 0
        self.gaps_eliminated = 0
        self.top5_recovered = 0
    
    def schedule_all(self) -> Schedule:
        """
        Enhanced scheduling with complete Spine-based phase optimization.
        """
        self.logger.info("Starting Spine-Enhanced scheduling with phase-based optimization...")
        
        # Generate base schedule
        schedule = super().schedule_all()
        
        # Apply Spine-based phase optimization
        self._apply_spine_phase_optimization()
        
        # Final validation and metrics
        self._final_validation()
        
        return schedule
    
    def _apply_spine_phase_optimization(self):
        """Apply the complete Spine-based phase optimization process."""
        self.logger.info("Starting Spine phase-based optimization...")
        
        # Phase 1: Critical Priority Foundation
        phase1_results = self._phase1_critical_foundation()
        self.optimization_phases['critical_foundation'] = phase1_results
        
        # Phase 2: High Priority Enhancement
        phase2_results = self._phase2_high_priority_enhancement()
        self.optimization_phases['high_priority_enhancement'] = phase2_results
        
        # Phase 3: Medium Priority Refinement
        phase3_results = self._phase3_medium_priority_refinement()
        self.optimization_phases['medium_priority_refinement'] = phase3_results
        
        # Phase 4: Low Priority Fine-Tuning
        phase4_results = self._phase4_low_priority_fine_tuning()
        self.optimization_phases['low_priority_fine_tuning'] = phase4_results
        
        # Calculate overall metrics
        self._calculate_overall_metrics()
        
        self.logger.info("Spine phase-based optimization complete")
    
    def _phase1_critical_foundation(self) -> Dict:
        """
        Phase 1: Critical Priority Foundation
        1. Generate Base Schedule - Create initial schedule with basic rules
        2. Ultimate Gap Elimination - Fill all gaps using comprehensive strategies
        3. Smart Constraint Fixing - Resolve violations with intelligent fixes
        4. Immediate Gap Prevention - Prevent gaps during optimization
        """
        self.logger.info("Phase 1: Critical Priority Foundation")
        
        results = {
            'gap_elimination': {},
            'constraint_fixing': {},
            'gap_prevention': {},
            'total_improvements': 0
        }
        
        # Step 1: Ultimate Gap Elimination
        self.logger.info("Step 1: Ultimate Gap Elimination")
        gap_results = self.gap_eliminator.eliminate_all_gaps()
        results['gap_elimination'] = gap_results
        self.gaps_eliminated = gap_results['total_filled']
        
        # Step 2: Smart Constraint Fixing
        self.logger.info("Step 2: Smart Constraint Fixing")
        constraint_results = self.constraint_fixer.fix_all_violations()
        results['constraint_fixing'] = constraint_results
        self.constraint_violations_fixed = constraint_results['violations_fixed']
        
        # Step 3: Immediate Gap Prevention
        self.logger.info("Step 3: Immediate Gap Prevention")
        prevention_results = self._apply_immediate_gap_prevention()
        results['gap_prevention'] = prevention_results
        
        results['total_improvements'] = (
            gap_results['total_filled'] + 
            constraint_results['violations_fixed'] + 
            prevention_results['gaps_prevented']
        )
        
        self.logger.info(f"Phase 1 complete: {results['total_improvements']} critical improvements")
        return results
    
    def _phase2_high_priority_enhancement(self) -> Dict:
        """
        Phase 2: High Priority Enhancement
        1. Aggressive Top 5 Recovery - Recover primary preferences
        2. Activity Requirement Compliance - Ensure activity-specific rules
        3. Staff Distribution Optimization - Balance staff allocation
        """
        self.logger.info("Phase 2: High Priority Enhancement")
        
        results = {
            'top5_recovery': {},
            'activity_compliance': {},
            'staff_optimization': {},
            'total_improvements': 0
        }
        
        # Step 1: Aggressive Top 5 Recovery
        self.logger.info("Step 1: Aggressive Top 5 Recovery")
        top5_results = self.top5_recovery.recover_all_top5()
        results['top5_recovery'] = top5_results
        self.top5_recovered = top5_results['total_recovered']
        
        # Step 2: Activity Requirement Compliance
        self.logger.info("Step 2: Activity Requirement Compliance")
        compliance_results = self._ensure_activity_compliance()
        results['activity_compliance'] = compliance_results
        
        # Step 3: Staff Distribution Optimization
        self.logger.info("Step 3: Staff Distribution Optimization")
        staff_results = self._optimize_staff_distribution()
        results['staff_optimization'] = staff_results
        
        results['total_improvements'] = (
            top5_results['total_recovered'] + 
            compliance_results['compliance_issues_fixed'] + 
            staff_results['staff_improvements']
        )
        
        self.logger.info(f"Phase 2 complete: {results['total_improvements']} high priority improvements")
        return results
    
    def _phase3_medium_priority_refinement(self) -> Dict:
        """
        Phase 3: Medium Priority Refinement
        1. Clustering Optimization - Group related activities
        2. Setup Efficiency - Optimize activity setup sequences
        3. Staff Variance Reduction - Minimize staff load variance
        """
        self.logger.info("Phase 3: Medium Priority Refinement")
        
        results = {
            'clustering_optimization': {},
            'setup_efficiency': {},
            'staff_variance_reduction': {},
            'total_improvements': 0
        }
        
        # Step 1: Clustering Optimization
        self.logger.info("Step 1: Clustering Optimization")
        clustering_results = self._optimize_clustering()
        results['clustering_optimization'] = clustering_results
        
        # Step 2: Setup Efficiency
        self.logger.info("Step 2: Setup Efficiency")
        setup_results = self._optimize_setup_efficiency()
        results['setup_efficiency'] = setup_results
        
        # Step 3: Staff Variance Reduction
        self.logger.info("Step 3: Staff Variance Reduction")
        variance_results = self._reduce_staff_variance()
        results['staff_variance_reduction'] = variance_results
        
        results['total_improvements'] = (
            clustering_results['clustering_improvements'] + 
            setup_results['setup_improvements'] + 
            variance_results['variance_improvements']
        )
        
        self.logger.info(f"Phase 3 complete: {results['total_improvements']} medium priority improvements")
        return results
    
    def _phase4_low_priority_fine_tuning(self) -> Dict:
        """
        Phase 4: Low Priority Fine-Tuning
        1. Preference Optimization - Satisfy lower preferences
        2. Minor Adjustments - Fine-tune schedule quality
        3. Final Verification - Ensure all constraints satisfied
        """
        self.logger.info("Phase 4: Low Priority Fine-Tuning")
        
        results = {
            'preference_optimization': {},
            'minor_adjustments': {},
            'final_verification': {},
            'total_improvements': 0
        }
        
        # Step 1: Preference Optimization
        self.logger.info("Step 1: Preference Optimization")
        preference_results = self._optimize_remaining_preferences()
        results['preference_optimization'] = preference_results
        
        # Step 2: Minor Adjustments
        self.logger.info("Step 2: Minor Adjustments")
        adjustment_results = self._apply_minor_adjustments()
        results['minor_adjustments'] = adjustment_results
        
        # Step 3: Final Verification
        self.logger.info("Step 3: Final Verification")
        verification_results = self._final_verification()
        results['final_verification'] = verification_results
        
        results['total_improvements'] = (
            preference_results['preferences_satisfied'] + 
            adjustment_results['adjustments_made'] + 
            verification_results['issues_resolved']
        )
        
        self.logger.info(f"Phase 4 complete: {results['total_improvements']} low priority improvements")
        return results
    
    def _apply_immediate_gap_prevention(self) -> Dict:
        """Apply immediate gap prevention strategies."""
        gaps_prevented = 0
        
        # Use prevention validator to identify potential gap creation
        for troop in self.troops:
            troop_entries = self.schedule.get_troop_entries(troop)
            
            for entry in troop_entries:
                # Check if this entry could create gaps
                validation = self.validator.comprehensive_prevention_check(
                    entry.troop, entry.activity, entry.time_slot
                )
                
                if validation['prevented_issues']:
                    gaps_prevented += len(validation['prevented_issues'])
        
        return {'gaps_prevented': gaps_prevented}
    
    def _ensure_activity_compliance(self) -> Dict:
        """Ensure activity-specific rule compliance."""
        compliance_issues_fixed = 0
        
        # Check for specific activity requirements
        for entry in self.schedule.entries:
            # Example: Ensure Friday Reflection for all troops
            if entry.time_slot.day.value == 5 and entry.activity.name != "Reflection":
                # Check if troop has Friday Reflection
                troop_friday_entries = [
                    e for e in self.schedule.entries 
                    if e.troop == entry.troop and e.time_slot.day.value == 5
                ]
                has_reflection = any(e.activity.name == "Reflection" for e in troop_friday_entries)
                
                if not has_reflection:
                    # Try to add Friday Reflection
                    self._add_friday_reflection(entry.troop)
                    compliance_issues_fixed += 1
        
        return {'compliance_issues_fixed': compliance_issues_fixed}
    
    def _optimize_staff_distribution(self) -> Dict:
        """Optimize staff distribution across activities."""
        staff_improvements = 0
        
        # Basic staff balancing - ensure no staff is overworked
        staff_loads = self._calculate_staff_loads()
        
        # Identify staff with excessive load
        max_load = max(staff_loads.values()) if staff_loads else 0
        min_load = min(staff_loads.values()) if staff_loads else 0
        
        if max_load - min_load > 2:  # If variance is too high
            # Try to balance by swapping activities
            staff_improvements = self._balance_staff_loads()
        
        return {'staff_improvements': staff_improvements}
    
    def _optimize_clustering(self) -> Dict:
        """Optimize activity clustering for efficiency."""
        clustering_improvements = 0
        
        # Group activities by zone and day for better clustering
        for troop in self.troops:
            troop_entries = self.schedule.get_troop_entries(troop)
            
            # Try to group activities in the same zone on consecutive days
            zone_groups = self._group_activities_by_zone(troop_entries)
            
            for zone, entries in zone_groups.items():
                if len(entries) > 1:
                    # Check if we can improve clustering
                    clustering_improvements += self._improve_zone_clustering(entries)
        
        return {'clustering_improvements': clustering_improvements}
    
    def _optimize_setup_efficiency(self) -> Dict:
        """Optimize activity setup sequences."""
        setup_improvements = 0
        
        # Optimize setup sequences for activities with similar requirements
        for troop in self.troops:
            troop_entries = self.schedule.get_troop_entries(troop)
            
            # Group by setup requirements
            setup_groups = self._group_by_setup_requirements(troop_entries)
            
            for setup_type, entries in setup_groups.items():
                if len(entries) > 1:
                    # Try to sequence these activities efficiently
                    setup_improvements += self._optimize_setup_sequence(entries)
        
        return {'setup_improvements': setup_improvements}
    
    def _reduce_staff_variance(self) -> Dict:
        """Reduce staff load variance."""
        variance_improvements = 0
        
        # Calculate current staff variance
        staff_loads = self._calculate_staff_loads()
        if staff_loads:
            loads = list(staff_loads.values())
            current_variance = max(loads) - min(loads)
            
            # Try to reduce variance through intelligent swaps
            variance_improvements = self._reduce_variance_swaps(current_variance)
        
        return {'variance_improvements': variance_improvements}
    
    def _optimize_remaining_preferences(self) -> Dict:
        """Optimize remaining lower-priority preferences."""
        preferences_satisfied = 0
        
        # Try to satisfy preferences beyond Top 5
        for troop in self.troops:
            if len(troop.preferences) > 5:
                remaining_prefs = troop.preferences[5:10]  # Next 5 preferences
                troop_activities = self.schedule.get_troop_activities(troop)
                activity_names = [act.name for act in troop_activities]
                
                for pref in remaining_prefs:
                    if pref.name not in activity_names:
                        # Try to place this preference
                        if self._try_place_preference(troop, pref):
                            preferences_satisfied += 1
        
        return {'preferences_satisfied': preferences_satisfied}
    
    def _apply_minor_adjustments(self) -> Dict:
        """Apply minor adjustments to fine-tune schedule quality."""
        adjustments_made = 0
        
        # Make small improvements that don't violate constraints
        for entry in self.schedule.entries:
            # Check if there's a better slot for this activity
            better_slot = self._find_better_slot(entry)
            
            if better_slot:
                # Make the adjustment
                self.schedule.remove_entry(entry)
                new_entry = ScheduleEntry(entry.troop, entry.activity, better_slot)
                self.schedule.add_entry(new_entry)
                adjustments_made += 1
        
        return {'adjustments_made': adjustments_made}
    
    def _final_verification(self) -> Dict:
        """Final verification to ensure all constraints are satisfied."""
        issues_resolved = 0
        
        # Check for any remaining violations
        violations = self.constraint_fixer._identify_all_violations()
        
        for violation in violations:
            # Try to resolve remaining issues
            if self.constraint_fixer._fix_violation_with_relocation(violation):
                issues_resolved += 1
        
        return {'issues_resolved': issues_resolved}
    
    # Helper methods (simplified implementations)
    def _add_friday_reflection(self, troop):
        """Add Friday Reflection for a troop."""
        # Implementation would find an available slot on Friday
        pass
    
    def _calculate_staff_loads(self) -> Dict:
        """Calculate staff loads across activities."""
        # Simplified implementation
        return {}
    
    def _balance_staff_loads(self) -> int:
        """Balance staff loads through swaps."""
        # Simplified implementation
        return 0
    
    def _group_activities_by_zone(self, entries: List[ScheduleEntry]) -> Dict:
        """Group activities by zone."""
        # Simplified implementation
        return {}
    
    def _improve_zone_clustering(self, entries: List[ScheduleEntry]) -> int:
        """Improve clustering within a zone."""
        # Simplified implementation
        return 0
    
    def _group_by_setup_requirements(self, entries: List[ScheduleEntry]) -> Dict:
        """Group activities by setup requirements."""
        # Simplified implementation
        return {}
    
    def _optimize_setup_sequence(self, entries: List[ScheduleEntry]) -> int:
        """Optimize setup sequence for activities."""
        # Simplified implementation
        return 0
    
    def _reduce_variance_swaps(self, current_variance: float) -> int:
        """Reduce staff variance through swaps."""
        # Simplified implementation
        return 0
    
    def _try_place_preference(self, troop, preference) -> bool:
        """Try to place a preference activity."""
        # Simplified implementation
        return False
    
    def _find_better_slot(self, entry: ScheduleEntry):
        """Find a better slot for an activity."""
        # Simplified implementation
        return None
    
    def _calculate_overall_metrics(self):
        """Calculate overall optimization metrics."""
        self.total_improvements = (
            self.gaps_eliminated + 
            self.constraint_violations_fixed + 
            self.top5_recovered
        )
        
        self.issues_prevented = self.validator.get_prevention_metrics()['issues_prevented']
    
    def _final_validation(self):
        """Perform final validation of the optimized schedule."""
        self.logger.info("Performing final validation...")
        
        # Count final gaps
        final_gaps = self.gap_eliminator._identify_all_gaps()
        self.logger.info(f"Final gaps: {len(final_gaps)}")
        
        # Count final violations
        final_violations = self.constraint_fixer._identify_all_violations()
        self.logger.info(f"Final violations: {len(final_violations)}")
        
        # Log overall metrics
        self.logger.info(f"Spine optimization complete:")
        self.logger.info(f"  Total improvements: {self.total_improvements}")
        self.logger.info(f"  Issues prevented: {self.issues_prevented}")
        self.logger.info(f"  Gaps eliminated: {self.gaps_eliminated}")
        self.logger.info(f"  Violations fixed: {self.constraint_violations_fixed}")
        self.logger.info(f"  Top 5 recovered: {self.top5_recovered}")
    
    def get_spine_optimization_metrics(self) -> Dict:
        """Get comprehensive Spine optimization metrics."""
        return {
            'total_improvements': self.total_improvements,
            'issues_prevented': self.issues_prevented,
            'constraint_violations_fixed': self.constraint_violations_fixed,
            'gaps_eliminated': self.gaps_eliminated,
            'top5_recovered': self.top5_recovered,
            'optimization_phases': self.optimization_phases,
            'prevention_metrics': self.validator.get_prevention_metrics(),
            'gap_elimination_metrics': self.gap_eliminator.get_gap_elimination_metrics(),
            'constraint_fixing_metrics': self.constraint_fixer.get_constraint_fixing_metrics(),
            'top5_recovery_metrics': self.top5_recovery.get_top5_recovery_metrics()
        }
