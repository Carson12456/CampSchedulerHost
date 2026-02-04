#!/usr/bin/env python3
"""
Performance benchmarking and testing tool for scheduler improvements.
Measures the impact of optimizations on scheduling speed and quality.
"""

import time
import statistics
from typing import Dict, List, Tuple
from constrained_scheduler import ConstrainedScheduler
from enhanced_scheduler import EnhancedScheduler
from evaluate_week_success import evaluate_week
from io_handler import load_troops_from_json
import glob


class SchedulerBenchmark:
    """Benchmark scheduler performance and quality."""
    
    def __init__(self):
        self.results = {}
        
    def run_comprehensive_benchmark(self, week_files: List[str]) -> Dict:
        """Run comprehensive benchmark comparing original vs enhanced scheduler."""
        print("Running comprehensive scheduler benchmark...")
        
        results = {
            'original': {},
            'enhanced': {},
            'comparison': {}
        }
        
        for week_file in week_files:
            print(f"\nBenchmarking {week_file}...")
            week_name = week_file.split('/')[-1].replace('_troops.json', '')
            
            # Benchmark original scheduler
            original_results = self._benchmark_scheduler(week_file, ConstrainedScheduler)
            results['original'][week_name] = original_results
            
            # Benchmark enhanced scheduler  
            enhanced_results = self._benchmark_scheduler(week_file, EnhancedScheduler)
            results['enhanced'][week_name] = enhanced_results
            
            # Calculate improvements
            comparison = self._compare_results(original_results, enhanced_results)
            results['comparison'][week_name] = comparison
            
            print(f"  Original: {original_results['final_score']:.1f} ({original_results['time']:.2f}s)")
            print(f"  Enhanced: {enhanced_results['final_score']:.1f} ({enhanced_results['time']:.2f}s)")
            print(f"  Improvement: {comparison['score_improvement']:+.1f} ({comparison['time_change']:+.1f}s)")
        
        # Calculate overall statistics
        results['summary'] = self._calculate_summary_stats(results['comparison'])
        
        return results
    
    def _benchmark_scheduler(self, week_file: str, scheduler_class) -> Dict:
        """Benchmark a single scheduler class."""
        troops = load_troops_from_json(week_file)
        
        # Time the scheduling process
        start_time = time.time()
        
        if scheduler_class == EnhancedScheduler:
            scheduler = EnhancedScheduler(troops)
        else:
            scheduler = ConstrainedScheduler(troops)
        
        schedule = scheduler.schedule_all()
        
        end_time = time.time()
        scheduling_time = end_time - start_time
        
        # Evaluate the schedule
        metrics = evaluate_week(week_file)
        
        return {
            'time': scheduling_time,
            'final_score': metrics['final_score'],
            'constraint_violations': metrics['constraint_violations'],
            'excess_cluster_days': metrics['excess_cluster_days'],
            'missing_top5': metrics['missing_top5'],
            'staff_variance': metrics['staff_variance'],
            'unnecessary_gaps': metrics['unnecessary_gaps']
        }
    
    def _compare_results(self, original: Dict, enhanced: Dict) -> Dict:
        """Compare original vs enhanced results."""
        return {
            'score_improvement': enhanced['final_score'] - original['final_score'],
            'time_change': enhanced['time'] - original['time'],
            'violations_change': enhanced['constraint_violations'] - original['constraint_violations'],
            'excess_days_change': enhanced['excess_cluster_days'] - original['excess_cluster_days'],
            'top5_change': enhanced['missing_top5'] - original['missing_top5'],
            'variance_change': enhanced['staff_variance'] - original['staff_variance'],
            'gaps_change': enhanced['unnecessary_gaps'] - original['unnecessary_gaps']
        }
    
    def _calculate_summary_stats(self, comparisons: Dict) -> Dict:
        """Calculate summary statistics across all weeks."""
        score_improvements = [c['score_improvement'] for c in comparisons.values()]
        time_changes = [c['time_change'] for c in comparisons.values()]
        violations_changes = [c['violations_change'] for c in comparisons.values()]
        
        return {
            'avg_score_improvement': statistics.mean(score_improvements),
            'median_score_improvement': statistics.median(score_improvements),
            'avg_time_change': statistics.mean(time_changes),
            'median_time_change': statistics.median(time_changes),
            'total_violations_fixed': sum(-v for v in violations_changes if v < 0),
            'weeks_improved': sum(1 for s in score_improvements if s > 0),
            'weeks_degraded': sum(1 for s in score_improvements if s < 0),
            'weeks_unchanged': sum(1 for s in score_improvements if s == 0)
        }
    
    def print_detailed_results(self, results: Dict):
        """Print detailed benchmark results."""
        print("\n" + "="*80)
        print("DETAILED BENCHMARK RESULTS")
        print("="*80)
        
        # Summary statistics
        summary = results['summary']
        print(f"\nSUMMARY STATISTICS:")
        print(f"  Average Score Improvement: {summary['avg_score_improvement']:+.1f} points")
        print(f"  Median Score Improvement: {summary['median_score_improvement']:+.1f} points")
        print(f"  Average Time Change: {summary['avg_time_change']:+.2f} seconds")
        print(f"  Median Time Change: {summary['median_time_change']:+.2f} seconds")
        print(f"  Total Violations Fixed: {summary['total_violations_fixed']}")
        print(f"  Weeks Improved: {summary['weeks_improved']}")
        print(f"  Weeks Degraded: {summary['weeks_degraded']}")
        print(f"  Weeks Unchanged: {summary['weeks_unchanged']}")
        
        # Week-by-week breakdown
        print(f"\nWEEK-BY-WEEK BREAKDOWN:")
        print("-" * 80)
        print(f"{'Week':<15} {'Original':<10} {'Enhanced':<10} {'Improvement':<12} {'Time Change':<12}")
        print("-" * 80)
        
        for week_name, comparison in results['comparison'].items():
            orig_score = results['original'][week_name]['final_score']
            enh_score = results['enhanced'][week_name]['final_score']
            improvement = comparison['score_improvement']
            time_change = comparison['time_change']
            
            print(f"{week_name:<15} {orig_score:<10.1f} {enh_score:<10.1f} {improvement:+<12.1f} {time_change:+<12.2f}s")
        
        # Quality improvements
        print(f"\nQUALITY IMPROVEMENTS:")
        print("-" * 40)
        total_violations_fixed = sum(results['comparison'][w]['violations_change'] for w in results['comparison'] if results['comparison'][w]['violations_change'] < 0)
        total_top5_improved = sum(results['comparison'][w]['top5_change'] for w in results['comparison'] if results['comparison'][w]['top5_change'] < 0)
        total_variance_improved = sum(1 for w in results['comparison'] if results['comparison'][w]['variance_change'] < 0)
        
        print(f"  Constraint violations fixed: {total_violations_fixed}")
        print(f"  Top 5 misses recovered: {total_top5_improved}")
        print(f"  Staff variance improved: {total_variance_improved} weeks")


def run_performance_test():
    """Run performance test on available week files."""
    week_files = glob.glob("*_troops.json")
    
    if not week_files:
        print("No troop files found for benchmarking")
        return
    
    benchmark = SchedulerBenchmark()
    results = benchmark.run_comprehensive_benchmark(week_files)
    benchmark.print_detailed_results(results)
    
    # Save results
    import json
    with open('benchmark_results.json', 'w') as f:
        # Convert non-serializable objects
        serializable_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                serializable_results[key] = {k: v for k, v in value.items() 
                                            if not callable(v) and not isinstance(v, type)}
            else:
                serializable_results[key] = value
        
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nDetailed results saved to benchmark_results.json")


if __name__ == "__main__":
    run_performance_test()
