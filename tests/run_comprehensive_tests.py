"""
Comprehensive Test Runner

Runs all unit tests and generates a detailed report of current system state.
This is the main entry point for regression detection after any changes.
"""
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_test_suite(test_name: str, test_path: str) -> dict:
    """Run a specific test suite and return results"""
    print(f"\n{'='*60}")
    print(f"Running {test_name}")
    print('='*60)
    
    start_time = time.time()
    
    try:
        # Run pytest with standard output
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            test_path, 
            '-v', 
            '--tb=short'
        ], 
        capture_output=True, 
        text=True, 
        cwd=project_root)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Parse results from pytest output
        if result.returncode == 0:
            status = "PASSED"
            failed_tests = 0
            total_tests = 0
        else:
            status = "FAILED"
            failed_tests = 0
            total_tests = 0
            
            # Parse pytest output to get test counts
            output_lines = result.stdout.split('\n') + result.stderr.split('\n')
            
            for line in output_lines:
                if 'passed' in line and 'failed' in line:
                    # Parse lines like "5 passed, 2 failed" or "5 passed, 2 failed, 1 error"
                    parts = line.replace(',', ' ').split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            next_part = parts[i + 1] if i + 1 < len(parts) else ''
                            if 'failed' in next_part:
                                failed_tests = int(part)
                            elif 'passed' in next_part:
                                total_tests = int(part)
                            elif 'error' in next_part:
                                failed_tests += int(part)
                elif '=== test session starts ===' in line:
                    # Look for test count summary
                    continue
                elif 'collected' in line and 'items' in line:
                    # Extract total tests from "collected X items"
                    try:
                        total_tests = int(line.split('collected')[1].split('items')[0].strip())
                    except:
                        pass
        
        return {
            'name': test_name,
            'status': status,
            'duration': duration,
            'failed_tests': failed_tests,
            'total_tests': total_tests,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            'name': test_name,
            'status': 'ERROR',
            'duration': end_time - start_time,
            'error': str(e),
            'failed_tests': -1,
            'total_tests': -1
        }


def generate_test_report(results: list) -> dict:
    """Generate comprehensive test report"""
    total_tests = sum(r.get('total_tests', 0) for r in results if r.get('total_tests', 0) > 0)
    total_failed = sum(r.get('failed_tests', 0) for r in results if r.get('failed_tests', 0) >= 0)
    total_passed = total_tests - total_failed
    total_duration = sum(r.get('duration', 0) for r in results)
    
    passed_suites = sum(1 for r in results if r['status'] == 'PASSED')
    failed_suites = sum(1 for r in results if r['status'] == 'FAILED')
    error_suites = sum(1 for r in results if r['status'] == 'ERROR')
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_test_suites': len(results),
            'passed_suites': passed_suites,
            'failed_suites': failed_suites,
            'error_suites': error_suites,
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration': total_duration
        },
        'test_suites': results,
        'recommendations': []
    }
    
    # Generate recommendations
    if failed_suites > 0:
        report['recommendations'].append("FAILED test suites indicate regressions - review failing tests immediately")
    
    if total_failed > 0:
        report['recommendations'].append(f"{total_failed} individual tests failed - check specific test failures")
    
    if total_duration > 60:
        report['recommendations'].append("Test execution is slow - consider optimizing test performance")
    
    if passed_suites == len(results):
        report['recommendations'].append("All tests passed - system is functioning correctly")
    
    return report


def save_report(report: dict, output_path: Path):
    """Save test report to file"""
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to: {output_path}")


def print_summary(report: dict):
    """Print test summary to console"""
    summary = report['summary']
    
    print(f"\n{'='*60}")
    print("COMPREHENSIVE TEST REPORT")
    print('='*60)
    
    print(f"Test Suites: {summary['passed_suites']} passed, {summary['failed_suites']} failed, {summary['error_suites']} errors")
    print(f"Individual Tests: {summary['total_passed']} passed, {summary['total_failed']} failed out of {summary['total_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Duration: {summary['total_duration']:.2f} seconds")
    print(f"Timestamp: {report['timestamp']}")
    
    if summary['failed_suites'] > 0 or summary['total_failed'] > 0:
        print(f"\n{'!'*60}")
        print("REGRESSIONS DETECTED!")
        print("{'!'*60}")
        
        # Show failed test suites
        for suite in report['test_suites']:
            if suite['status'] == 'FAILED':
                print(f"\nFAILED SUITE: {suite['name']}")
                print(f"  Failed Tests: {suite['failed_tests']}")
                if suite.get('stderr'):
                    print(f"  Error: {suite['stderr'][:200]}...")
    
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print('='*60)
    
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")


def main():
    """Main test runner"""
    print("Summer Camp Scheduler - Comprehensive Test Suite")
    print("=" * 60)
    print("Running all unit tests to detect regressions...")
    print("This will validate all success metrics and system behavior.")
    print()
    
    # Define test suites to run
    test_suites = [
        ("Core Entities", "tests/unit/test_core_entities.py"),
        ("Constraint System", "tests/unit/test_constraint_system.py"),
        ("Scheduling Algorithm", "tests/unit/test_scheduling_algorithm.py"),
        ("Performance Metrics", "tests/unit/test_performance_metrics.py"),
        ("Success Metrics", "tests/unit/test_success_metrics.py"),
        ("Regression Detection", "tests/unit/test_regression_detection.py"),
    ]
    
    # Run all test suites
    results = []
    overall_start_time = time.time()
    
    for test_name, test_path in test_suites:
        if Path(project_root / test_path).exists():
            result = run_test_suite(test_name, test_path)
            results.append(result)
        else:
            print(f"WARNING: Test file not found: {test_path}")
            results.append({
                'name': test_name,
                'status': 'SKIPPED',
                'duration': 0,
                'failed_tests': 0,
                'total_tests': 0,
                'error': 'Test file not found'
            })
    
    overall_end_time = time.time()
    
    # Generate and save report
    report = generate_test_report(results)
    report['summary']['total_duration'] = overall_end_time - overall_start_time
    
    # Save reports
    reports_dir = project_root / "tests" / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"test_report_{timestamp}.json"
    save_report(report, report_file)
    
    # Also save latest report
    latest_report_file = reports_dir / "latest_test_report.json"
    save_report(report, latest_report_file)
    
    # Print summary
    print_summary(report)
    
    # Return appropriate exit code
    if report['summary']['failed_suites'] > 0 or report['summary']['total_failed'] > 0:
        print(f"\n{'!'*60}")
        print("TESTS FAILED - REGRESSIONS DETECTED!")
        print("Review the failing tests and fix issues before proceeding.")
        print(f"{'!'*60}")
        return 1
    else:
        print(f"\n{'*'*60}")
        print("ALL TESTS PASSED - NO REGRESSIONS DETECTED!")
        print("System is functioning correctly.")
        print(f"{'*'*60}")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
