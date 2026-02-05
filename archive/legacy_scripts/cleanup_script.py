import os
import glob

# Files to definitely keep
KEEP_FILES = {
    "main.py",
    "gui_web.py",
    "models.py",
    "activities.py",
    "constrained_scheduler.py",
    "evaluate_week_success.py",
    "scheduler_config.py",
    "scheduler_logging.py",
    "scheduler_cache.py",
    "schedule_cache.py",
    "io_handler.py",
    "config_loader.py",
    "README.md",
    "requirements.txt",
    "top5_misses_analysis_report.md",
    "CampScheduler.code-workspace"
}

# Patterns for deletion
DELETE_PATTERNS = [
    "*_REPORT.md", "*_ANALYSIS.md", "*_COMPARISON.md", "*_SUMMARY.md", "*_GUIDE.md",
    "*_PLANNING.md", "*_RESULTS.md", "*_FIXES.md", "*_LOG.md", "*_TEMPLATE.md",
    "*_PATTERNS.md", "BEFORE_AFTER_COMPARISON.md", "CONSTRAINT_FIXES.md", "CRITICAL_FIX_COMPLETE.md",
    "EVALUATION_SYSTEM.md", "RESTRUCTURING.md", "STRUCTURAL_AT_INSIGHTS.md",
    "*.txt", # requirements.txt is in KEEP_FILES which overrides this
    "debug_*.py",
    "analyze_*.py",
    "check_*.py",
    "calculate_*.py",
    "fix_*.py",
    "apply_fixes_*.py",
    "compare_*.py",
    "evaluate_*.py", # evaluate_week_success.py is in KEEP_FILES
    "export_schedule.py",
    "generate_*.py",
    "get_*.py", # if any
    "import_week.py",
    "list_methods*.py",
    "find_method.py", 
    "migrate_activity_names.py",
    "multislot_*.py",
    "optimization_results_analysis.py",
    "print_*.py",
    "quick_*.py",
    "real_time_monitor.py",
    "reflection_fix_patch.py",
    "regenerate_all.py",
    "reproduce_slow_loading.py",
    "restore_original_schedules.py",
    "reverse_beach_optimizations.py",
    "score_optimizer.py",
    "simple_*.py",
    "smart_safe_scheduler.py",
    "target_beach_fix.py",
    "test_*.py", # Only in root
    "ultra_*.py",
    "update_web_schedules.py",
    "verify_*.py",
    "webpage_update.py",
    "final_*.py",
    "adaptive_constraint_system.py",
    "activity_placement_analyzer.py",
    "advanced_preference_optimizer.py",
    "advanced_top5_fix.py",
    "aggressive_optimizer.py",
    "aggressive_test_enhancer.py",
    "aggressive_top5_recovery.py",
    "beach_activity_enhancer.py",
    "beach_activity_optimizer.py",
    "breakthrough_analysis.py",
    "comprehensive_*.py",
    "constrained_scheduler_*.py", # if exists
    "day_aware_fill_snippet.py",
    "detect_broken_multislot.py",
    "direct_fix_struggling_weeks.py",
    "double_check_analysis.py",
    "enhanced_clustering_optimizer.py",
    "enhanced_scheduler.py",
    "gui_enhancements.py",
    "integrated_top5_beach_fix.py",
    "ml_activity_predictor.py",
    "performance_analytics.py",
    "performance_benchmark.py",
    "prevention_aware_validator.py",
    "regression_checker.py",
    "regression_checker_fixed.py",
    "regression_test_enhancer.py",
    "safe_constraint_fixer.py",
    "safe_optimizer.py",
    "safe_scheduling_validator.py",
    "schedule_quality_predictor.py",
    "scheduler.py", # If unused
    "scoring_impact_analysis.py",
    "smart_beach_optimizer.py",
    "smart_constraint_fixer.py",
    "specialized_constraint_fixer.py",
    "staff_balance_optimizer.py",
    "success_evaluation.py",
    "top5_beach_activity_fix.py",
    "top5_guarantee_system.py",
    "ultimate_gap_eliminator.py",
    "validate_schedule.py",
    "validate_troop_data.py",
    "zero_gap_scheduler.py"
]

def main():
    files_to_delete = set()
    
    # Gather files matching patterns
    for pattern in DELETE_PATTERNS:
        matches = glob.glob(pattern)
        for match in matches:
            if match not in KEEP_FILES:
                # Don't delete directories this way
                if os.path.isfile(match):
                    files_to_delete.add(match)

    print(f"Found {len(files_to_delete)} files to delete.")
    
    deleted_count = 0
    for file_path in sorted(list(files_to_delete)):
        try:
            os.remove(file_path)
            print(f"Deleted: {file_path}")
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
            
    print(f"\nTotal files deleted: {deleted_count}")

if __name__ == "__main__":
    main()
