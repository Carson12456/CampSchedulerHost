#!/usr/bin/env python3
"""
Test enhanced scheduler improvements
"""

from enhanced_scheduler import EnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week
import time

print('Testing Enhanced Scheduler vs Original')
print('=' * 50)

# Test on tc_week3
week_file = 'tc_week3_troops.json'
troops = load_troops_from_json(week_file)

# Test enhanced scheduler
print('\nEnhanced Scheduler:')
start_time = time.time()
enhanced_scheduler = EnhancedScheduler(troops)
enhanced_schedule = enhanced_scheduler.schedule_all()
enhanced_time = time.time() - start_time

# Save enhanced schedule
save_schedule_to_json(enhanced_schedule, troops, 'schedules/tc_week3_enhanced_schedule.json')

# Evaluate enhanced
enhanced_metrics = evaluate_week(week_file)

print(f'  Time: {enhanced_time:.2f}s')
print(f'  Final Score: {enhanced_metrics["final_score"]}')
print(f'  Gaps: {enhanced_metrics["unnecessary_gaps"]}')
print(f'  Constraint Violations: {enhanced_metrics["constraint_violations"]}')
print(f'  Top 5 Missed: {enhanced_metrics["missing_top5"]}')
print(f'  Staff Variance: {enhanced_metrics["staff_variance"]:.2f}')

# Quick gap verification
total_gaps = 0
for troop in troops:
    gaps = len(enhanced_scheduler._find_troop_gaps(troop))
    total_gaps += gaps

print(f'  Verified Gaps: {total_gaps}')
