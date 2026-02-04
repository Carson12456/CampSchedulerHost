#!/usr/bin/env python3
"""
Test ultra-safe scheduler on one week
"""

from ultra_safe_scheduler import UltraSafeEnhancedScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week

print('Testing Ultra-Safe Scheduler on tc_week1...')
troops = load_troops_from_json('tc_week1_troops.json')

scheduler = UltraSafeEnhancedScheduler(troops)
schedule = scheduler.schedule_all()

save_schedule_to_json(schedule, troops, 'schedules/tc_week1_ultra_safe_test.json')

metrics = evaluate_week('tc_week1_troops.json')
print(f'Results:')
print(f'  Score: {metrics["final_score"]}')
print(f'  Gaps: {metrics["unnecessary_gaps"]}')
print(f'  Operations: {scheduler.operations_successful} success, {scheduler.operations_blocked} blocked')
