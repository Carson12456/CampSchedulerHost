#!/usr/bin/env python3
"""
Deprecated compatibility wrapper.

Use utils/regression_checker.py directly.
This wrapper preserves old entrypoints while delegating to the canonical tool.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    checker = project_root / "utils" / "regression_checker.py"
    print("[DEPRECATED] analyze_results_detailed.py -> forwarding to regression_checker.py")
    cmd = [sys.executable, str(checker)]
    completed = subprocess.run(cmd, cwd=str(project_root))
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
