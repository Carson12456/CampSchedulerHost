import subprocess
import sys

with open("top5_misses_clean.txt", "w", encoding="utf-8") as f:
    subprocess.run([sys.executable, "print_all_weeks_missed_top5.py"], stdout=f, text=True)
