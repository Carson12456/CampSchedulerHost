import argparse
import io
import os
import sys
from pathlib import Path


# Fix encoding for Windows when output is redirected.
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.activities import get_all_activities
from core.constrained_scheduler import ConstrainedScheduler
from core.io_handler import load_troops_from_json
from core.scheduler.snapshot_recorder import ScheduleSnapshotRecorder


def _resolve_troop_file(week_or_path: str) -> Path:
    candidate = Path(week_or_path)
    if candidate.exists():
        return candidate

    troops_dir = Path("data/troops")
    by_stem = troops_dir / f"{week_or_path}.json"
    if by_stem.exists():
        return by_stem

    by_scheduleish_name = troops_dir / week_or_path
    if by_scheduleish_name.suffix != ".json":
        by_scheduleish_name = by_scheduleish_name.with_suffix(".json")
    if by_scheduleish_name.exists():
        return by_scheduleish_name

    raise FileNotFoundError(
        f"Could not find troop file for {week_or_path!r}. "
        "Pass a data/troops/*.json path or a week id like tc_week3_troops."
    )


def generate_snapshots(week_or_path: str, output_dir: str) -> tuple[Path, Path]:
    troop_file = _resolve_troop_file(week_or_path)
    week_id = troop_file.stem
    troops = load_troops_from_json(str(troop_file))
    voyageur_mode = "voyageur" in week_id.lower()
    recorder = ScheduleSnapshotRecorder(week_id=week_id, output_dir=output_dir)

    scheduler = ConstrainedScheduler(
        troops,
        get_all_activities(),
        voyageur_mode=voyageur_mode,
        snapshot_recorder=recorder,
    )
    scheduler.schedule_all()
    return recorder.write_bundle()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate semantic scheduler snapshot traces.")
    parser.add_argument(
        "week",
        help="Troop week id or JSON path, for example tc_week3_troops or data/troops/tc_week3_troops.json.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/snapshots",
        help="Directory where snapshot run folders are written.",
    )
    args = parser.parse_args()

    bundle_path, summary_path = generate_snapshots(args.week, args.output_dir)
    print(f"Snapshot JSON: {bundle_path}")
    print(f"Snapshot text: {summary_path}")


if __name__ == "__main__":
    main()
