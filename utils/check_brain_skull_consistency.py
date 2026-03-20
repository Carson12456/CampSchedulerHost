#!/usr/bin/env python3
"""
Check whether SKULL key constraints match BRAIN.

This is a consistency checker only (no auto-write).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAIN_PATH = PROJECT_ROOT / "config" / "BRAIN.md"
SKULL_PATH = PROJECT_ROOT / "config" / "SKULL.json"


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _extract_int(patterns: List[str], text: str, label: str) -> int:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))
    raise ValueError(f"Could not extract '{label}' from BRAIN")


def _contains_required_brain_clauses(brain: str) -> List[str]:
    required_groups = [
        ("non_exempt_top5_misses == 0", "non_exempt_top5_misses == 0"),
        ("100% non-exempt Top 5 success", "Zero Non-Exempt Top 5 Misses"),
        ("3-hour duplication rule", "3-Hour Duplication"),
        ("Tuesday HC/DG saturation rule", "Tuesday HC/DG Saturation"),
    ]
    missing = [
        label
        for label, clause in required_groups
        if clause not in brain
    ]
    return missing


def check_consistency() -> Tuple[List[str], List[str]]:
    brain = _read_text(BRAIN_PATH)
    skull = json.loads(_read_text(SKULL_PATH))

    errors: List[str] = []
    warnings: List[str] = []

    constraints: Dict[str, int] = skull.get("constraints", {})
    if not constraints:
        errors.append("SKULL missing constraints block")
        return errors, warnings

    expected_canoe = _extract_int(
        [
            r"Canoes max\s+(\d+)\s+people",
            r"Canoes:\s*Max\s+(\d+)\s+people",
        ],
        brain,
        "canoe capacity",
    )
    expected_global_staff = _extract_int(
        [
            r"Global staff max\s+(\d+)\s+per slot",
            r"Global Staff:\s*Base max\s+(\d+)\s+per slot",
        ],
        brain,
        "global staff",
    )
    expected_beach_staff = _extract_int(
        [
            r"Beach staff max\s+(\d+)\s+per slot",
            r"Beach Staff:\s*Max\s+(\d+)\s+per slot",
        ],
        brain,
        "beach staff",
    )
    expected_beach_sat = _extract_int(
        [
            r"Beach saturation max\s+(\d+)\s+staffed beach activities per slot",
            r"Beach Saturation:\s*Max\s+(\d+)\s+staffed beach activities per slot",
        ],
        brain,
        "beach saturation",
    )

    actual_canoe = int(constraints.get("max_canoe_capacity", -1))
    actual_global_staff = int(constraints.get("max_staff_global", -1))
    actual_beach_staff = int(constraints.get("beach_staff_per_slot", -1))
    actual_beach_sat = int(constraints.get("max_beach_staffed_activities", -1))

    if actual_canoe != expected_canoe:
        errors.append(f"Canoe capacity mismatch: BRAIN={expected_canoe}, SKULL={actual_canoe}")
    if actual_global_staff != expected_global_staff:
        errors.append(
            f"Global staff cap mismatch: BRAIN={expected_global_staff}, SKULL={actual_global_staff}"
        )
    if actual_beach_staff != expected_beach_staff:
        errors.append(
            f"Beach staff cap mismatch: BRAIN={expected_beach_staff}, SKULL={actual_beach_staff}"
        )
    if actual_beach_sat != expected_beach_sat:
        errors.append(
            f"Beach saturation mismatch: BRAIN={expected_beach_sat}, SKULL={actual_beach_sat}"
        )

    slot_rules = skull.get("slot_rules", {})
    allowed_beach = slot_rules.get("beach_allowed_slots", [])
    thursday_beach = slot_rules.get("beach_thursday_slots", [])
    if sorted(allowed_beach) != [1, 3]:
        errors.append(f"Beach allowed slots mismatch: expected [1,3], got {allowed_beach}")
    if sorted(thursday_beach) != [1, 2]:
        errors.append(f"Thursday beach slots mismatch: expected [1,2], got {thursday_beach}")

    missing_clauses = _contains_required_brain_clauses(brain)
    for clause in missing_clauses:
        warnings.append(f"BRAIN missing expected contract clause: '{clause}'")

    # NOTE: Top 5 acceptance gate is runtime logic and intentionally not stored in SKULL.
    warnings.append(
        "Runtime-only rule check: ensure non-exempt Top 5 acceptance gate is enforced in scheduler final validation."
    )

    return errors, warnings


def main() -> int:
    try:
        errors, warnings = check_consistency()
    except Exception as exc:  # pragma: no cover - utility script
        print(f"[ERROR] {exc}")
        return 2

    if errors:
        print("[FAIL] BRAIN/SKULL consistency check failed:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("[PASS] BRAIN/SKULL checked fields are aligned.")

    if warnings:
        print("[INFO] Additional checks:")
        for warn in warnings:
            print(f"  - {warn}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
