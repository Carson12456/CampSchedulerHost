"""
Master test runner - runs all test suites.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_test_file(test_file):
    """Run a test file and return True if passed."""
    print(f"\n{'='*70}")
    print(f"Running: {test_file}")
    print('='*70)
    
    # Set up environment to include parent directory in PYTHONPATH
    env = os.environ.copy()
    parent_dir = str(Path(__file__).parent.parent)
    current_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = f"{parent_dir}{os.pathsep}{current_pythonpath}" if current_pythonpath else parent_dir
    
    result = subprocess.run([sys.executable, test_file], capture_output=False, env=env)
    return result.returncode == 0

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SUMMER CAMP SCHEDULER - TEST SUITE")
    print("="*70)
    
    # Determine the tests directory
    script_dir = Path(__file__).parent
    tests_dir = script_dir if script_dir.name == "tests" else script_dir / "tests"
    
    test_files = [
        "test_constraints.py",
        "test_capacity.py",
        "test_preferences.py"
    ]
    
    # Resolve full paths to test files
    test_paths = [str(tests_dir / test_file) for test_file in test_files]
    
    results = {}
    for test_file, test_path in zip(test_files, test_paths):
        if not os.path.exists(test_path):
            print(f"\nWARNING: Test file not found: {test_path}")
            results[test_file] = False
        else:
            results[test_file] = run_test_file(test_path)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_file, passed in results.items():
        status = "[OK] PASSED" if passed else "[FAIL] FAILED"
        print(f"{test_file:30s} {status}")
    
    all_passed = all(results.values())
    
    print("="*70)
    if all_passed:
        print("[OK] ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("[FAIL] SOME TESTS FAILED")
        sys.exit(1)
