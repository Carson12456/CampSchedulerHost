
import re

filename = "constrained_scheduler.py"
print(f"Scanning {filename}...")
with open(filename, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if line.strip().startswith("def "):
            print(f"{i+1}: {line.strip()}")
        if "class " in line:
            print(f"{i+1}: {line.strip()}")
