#!/usr/bin/env python3
"""
Test smart safe scheduler
"""

from smart_safe_scheduler import SmartSafeScheduler
from io_handler import load_troops_from_json, save_schedule_to_json
from evaluate_week_success import evaluate_week

print('Testing Smart Safe Scheduler on tc_week1...')
troops = load_troops_from_json('tc_week1_troops.json')

scheduler = SmartSafeScheduler(troops)
schedule = scheduler.schedule_all()

save_schedule_to_json(schedule, troops, 'schedules/tc_week1_smart_safe_test.json')

metrics = evaluate_week('tc_week1_troops.json')
print(f'Results:')
print(f'  Score: {metrics["final_score"]}')
print(f'  Gaps: {metrics["unnecessary_gaps"]}')
print(f'  Operations: {scheduler.operations_safe} safe, {scheduler.operations_blocked} blocked, {scheduler.operations_warned} warned')
