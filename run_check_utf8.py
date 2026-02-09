import subprocess
import sys

with open('regression_log_utf8.txt', 'w', encoding='utf-8') as f:
    # Run the regression checker and capture output
    result = subprocess.run(
        [sys.executable, 'utils/regression_checker.py', '--detailed', '--show-violations'], 
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
