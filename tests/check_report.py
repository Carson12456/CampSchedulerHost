import json

# Load and display test report summary
try:
    with open('tests/reports/latest_test_report.json', 'r') as f:
        report = json.load(f)
    
    summary = report['summary']
    print(f"Test Suites: {summary['passed_suites']} passed, {summary['failed_suites']} failed")
    print(f"Individual Tests: {summary['total_passed']} passed, {summary['total_failed']} failed out of {summary['total_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Duration: {summary['total_duration']:.2f} seconds")
    
    # Show failed test suites
    failed_suites = [suite for suite in report['test_suites'] if suite['status'] == 'FAILED']
    if failed_suites:
        print("\nFailed Test Suites:")
        for suite in failed_suites:
            print(f"  - {suite['name']}: {suite['failed_tests']} failed tests")
    
except FileNotFoundError:
    print("No test report found. Run tests first.")
except Exception as e:
    print(f"Error reading report: {e}")
