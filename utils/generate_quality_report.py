#!/usr/bin/env python3
"""
Deprecated compatibility wrapper.

Use utils/regression_checker.py directly.
This wrapper forwards to the canonical report path.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    checker = project_root / "utils" / "regression_checker.py"
    print("[DEPRECATED] generate_quality_report.py -> forwarding to regression_checker.py")
    cmd = [sys.executable, str(checker), "--show-violations"]
    completed = subprocess.run(cmd, cwd=str(project_root))
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
