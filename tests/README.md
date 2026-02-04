# Comprehensive Unit Test Suite

This directory contains a comprehensive unit test suite designed to detect any regressions in the Summer Camp Scheduler after changes. The tests validate every metric of success defined in `.cursorrules` and ensure the current 'correct' behavior is maintained.

## Test Structure

### Core Test Files

1. **`test_success_metrics.py`** - Tests all success metrics from `.cursorrules`
   - Average Season Score target (730.7)
   - Top 5 Satisfaction target (90.0%)
   - Multi-Slot Activities success rate (100%)
   - Schedule Empty Slots target (0)
   - Schedule Validity target (100%)

2. **`test_core_entities.py`** - Tests fundamental data models
   - Activity, Troop, Schedule, ScheduleEntry, TimeSlot entities
   - Immutability and hashability properties
   - Business logic methods

3. **`test_constraint_system.py`** - Tests all constraint validation rules
   - Exclusive area enforcement
   - Beach slot rules
   - Activity conflict constraints
   - Capacity limits
   - Multi-slot activity handling

4. **`test_scheduling_algorithm.py`** - Tests scheduling algorithm phases
   - Phase A: Foundation & Core Priorities
   - Phase B: Core Requests
   - Phase C: Integrated Optimization
   - Phase D: Cleanup & Recovery
   - Prevention-based framework
   - Batch processing by priority

5. **`test_performance_metrics.py`** - Tests performance metrics and scoring
   - Scoring system calculations
   - Preference satisfaction metrics
   - Staff efficiency metrics
   - Clustering quality metrics
   - Performance analytics

6. **`test_regression_detection.py`** - Regression detection tests
   - Baseline metric comparisons
   - Performance boundary tests
   - Functional regression tests
   - Memory and performance monitoring

## Running Tests

### Quick Test Run
```bash
# Run all tests with comprehensive report
python tests/run_comprehensive_tests.py

# Run specific test file
python -m pytest tests/unit/test_success_metrics.py -v

# Run tests with coverage
python -m pytest tests/unit/ --cov=. --cov-report=html
```

### Individual Test Categories

#### Success Metrics Validation
```bash
python -m pytest tests/unit/test_success_metrics.py::TestSuccessMetrics::test_average_season_score_target -v
python -m pytest tests/unit/test_success_metrics.py::TestSuccessMetrics::test_top5_satisfaction_rate -v
python -m pytest tests/unit/test_success_metrics.py::TestSuccessMetrics::test_multislot_activity_success_rate -v
```

#### Regression Detection
```bash
python -m pytest tests/unit/test_regression_detection.py -v
```

#### Core Functionality
```bash
python -m pytest tests/unit/test_core_entities.py -v
python -m pytest tests/unit/test_constraint_system.py -v
python -m pytest tests/unit/test_scheduling_algorithm.py -v
```

## Test Reports

### Comprehensive Test Report
The main test runner generates detailed reports:

- **Location**: `tests/reports/test_report_YYYYMMDD_HHMMSS.json`
- **Latest**: `tests/reports/latest_test_report.json`

### Report Contents
- Test suite results (passed/failed/error)
- Individual test counts
- Success rates
- Execution times
- Regression detection results
- Recommendations for action

## Success Metrics Validation

### Target Metrics (from .cursorrules)
- **Average Season Score**: 730.7
- **Top 5 Satisfaction**: 90.0% (16/18 available preferences)
- **Multi-Slot Activities**: 100% success rate
- **Schedule Empty Slots**: 0 across ALL weeks
- **Schedule Validity**: 100% (no invalid schedules)

### Regression Detection Thresholds
- **Top 5 Satisfaction**: Minimum 75% (15% tolerance from target)
- **Staff Efficiency**: Minimum 35.8% (20% tolerance from baseline 55.8%)
- **Clustering Quality**: Minimum 49.3% (10% tolerance from baseline 59.3%)
- **Constraint Violations**: Maximum 6 (baseline level)
- **Success Rate**: Minimum 30% (current working minimum)

## Integration with Development Workflow

### Before Making Changes
1. Run baseline tests to ensure current state is passing
2. Save baseline report for comparison

### After Making Changes
1. Run comprehensive test suite
2. Review any failures or regressions
3. Fix issues before proceeding

### Continuous Integration
The test suite is designed for CI/CD integration:
- Fast execution (under 30 seconds target)
- Clear pass/fail indicators
- Detailed reporting for debugging
- Regression detection alerts

## Test Data

### Sample Troops
Tests use both real troop data (when available) and comprehensive test data:
- Real data: `tc_week1_troops.json` (when exists)
- Fallback: Comprehensive test troops with varied preferences

### Activities
Tests use the complete activity set from `activities.py` to ensure realistic testing.

## Extending the Test Suite

### Adding New Tests
1. Follow existing naming conventions
2. Use descriptive test method names
3. Include proper fixtures and setup
4. Add assertions for both positive and negative cases
5. Document the purpose of each test

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Regression Tests**: Baseline comparison testing
- **Performance Tests**: Speed and resource usage testing

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure project root is in Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/project/root"
```

#### Missing Test Data
```bash
# Ensure test data files exist
ls tests/fixtures/
ls tc_week1_troops.json
```

#### Performance Issues
```bash
# Run with verbose output to identify slow tests
python -m pytest tests/unit/ --durations=10
```

### Debugging Failed Tests

1. **Run specific test with verbose output**:
   ```bash
   python -m pytest tests/unit/test_success_metrics.py::TestSuccessMetrics::test_top5_satisfaction_rate -v -s
   ```

2. **Run with debugging**:
   ```bash
   python -m pytest tests/unit/test_success_metrics.py::TestSuccessMetrics::test_top5_satisfaction_rate --pdb
   ```

3. **Check test report**:
   ```bash
   cat tests/reports/latest_test_report.json | python -m json.tool
   ```

## Best Practices

### Test Design
- **Independent**: Tests should not depend on each other
- **Repeatable**: Same results every time
- **Fast**: Quick execution for rapid feedback
- **Clear**: Descriptive names and documentation

### Assertions
- **Specific**: Test exactly what you expect
- **Comprehensive**: Cover edge cases
- **Meaningful**: Clear failure messages

### Fixtures
- **Reusable**: Share setup code across tests
- **Isolated**: Each test gets fresh data
- **Efficient**: Minimize setup overhead

## Maintenance

### Regular Updates
1. Update baseline metrics when system improves
2. Add new tests for new features
3. Review and update test data
4. Monitor test execution times

### Performance Monitoring
- Track test execution times
- Identify slow tests
- Optimize where needed
- Maintain under 30 seconds total execution

This comprehensive test suite ensures that any changes to the Summer Camp Scheduler are thoroughly validated and regressions are immediately detected.
