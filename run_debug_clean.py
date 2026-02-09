import subprocess
import sys

with open('debug_output_week1_clean.txt', 'w', encoding='utf-8') as f:
    # Run the debug script and capture output
    result = subprocess.run(
        [sys.executable, 'debug_week1_score.py'], 
        text=True, 
        capture_output=True, 
        encoding='utf-8'
    )
    
    # Write stdout
    f.write(result.stdout)
    
    # Write stderr if any
    if result.stderr:
        f.write("\nSTDERR:\n")
        f.write(result.stderr)

    print(f"Finished with return code {result.returncode}")
