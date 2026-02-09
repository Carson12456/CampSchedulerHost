
filename = "core/constrained_scheduler.py"
with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "def _balance_staff_distribution" in line:
            print(f"Line {i+1}: {line.strip()}")
