
filename = "constrained_scheduler.py"
with open(filename, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if "_can_schedule" in line and "def " in line:
            print(f"Found at line {i+1}: {line.strip()}")
