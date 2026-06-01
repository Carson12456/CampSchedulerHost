"""Opt-in schedule snapshot tracing for scheduler debugging."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


class ScheduleSnapshotRecorder:
    """Collect semantic snapshots without participating in scheduling decisions."""

    def __init__(
        self,
        *,
        week_id: str | None = None,
        run_id: str | None = None,
        output_dir: str | Path = "artifacts/snapshots",
        enabled: bool = True,
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.week_id = week_id or "unknown_week"
        self.run_id = run_id or f"{self.week_id}_{timestamp}"
        self.output_dir = Path(output_dir)
        self.enabled = enabled
        self.snapshots: list[dict[str, Any]] = []
        self.troops: list[dict[str, Any]] = []
        self._last_signature: tuple[tuple[str, str, str, int], ...] | None = None

    def record(
        self,
        scheduler: Any,
        label: str,
        *,
        reason: str = "checkpoint",
        metadata: dict[str, Any] | None = None,
        force: bool = False,
    ) -> bool:
        """Capture the current schedule if it changed since the previous snapshot."""
        if not self.enabled:
            return False

        if not self.troops:
            self.troops = self._serialize_troops(getattr(scheduler, "troops", []))

        entries = self._serialize_entries(getattr(scheduler.schedule, "entries", []))
        signature = tuple(
            (e["troop_name"], e["activity_name"], e["day"], e["slot"])
            for e in entries
        )
        if not force and signature == self._last_signature:
            return False

        diff = self._diff_signatures(self._last_signature, signature)
        snapshot = {
            "step_index": len(self.snapshots),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "week_id": self.week_id,
            "phase": getattr(scheduler, "current_pipeline_phase", "unknown"),
            "label": label,
            "reason": reason,
            "metadata": metadata or {},
            "metrics": self._collect_metrics(scheduler, len(entries)),
            "diff": diff,
            "entries": entries,
            "sailing_half_fills": getattr(scheduler, "sailing_balls_fills", {}) or {},
        }
        self.snapshots.append(snapshot)
        self._last_signature = signature
        return True

    def write_bundle(self, output_dir: str | Path | None = None) -> tuple[Path, Path]:
        """Write machine-readable JSON and a concise text review file."""
        target_dir = Path(output_dir) if output_dir is not None else self.output_dir
        run_dir = target_dir / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        bundle_path = run_dir / f"{self.week_id}.json"
        summary_path = run_dir / f"{self.week_id}.txt"
        bundle = {
            "run_id": self.run_id,
            "week_id": self.week_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "snapshot_count": len(self.snapshots),
            "troops": self.troops,
            "snapshots": self.snapshots,
        }

        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, separators=(",", ":"))

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(self._build_summary_text())

        return bundle_path, summary_path

    def _serialize_entries(self, entries: Iterable[Any]) -> list[dict[str, Any]]:
        rows = []
        for entry in entries:
            rows.append(
                {
                    "troop_name": entry.troop.name,
                    "activity_name": entry.activity.name,
                    "day": entry.time_slot.day.name,
                    "slot": entry.time_slot.slot_number,
                }
            )
        return sorted(rows, key=lambda e: (e["day"], e["slot"], e["troop_name"], e["activity_name"]))

    def _serialize_troops(self, troops: Iterable[Any]) -> list[dict[str, Any]]:
        rows = []
        for troop in troops:
            rows.append(
                {
                    "name": troop.name,
                    "scouts": troop.scouts,
                    "adults": troop.adults,
                    "campsite": troop.campsite,
                    "commissioner": troop.commissioner,
                    "preferences": list(troop.preferences or []),
                    "day_requests": troop.day_requests or {},
                }
            )
        return rows

    def _collect_metrics(self, scheduler: Any, entry_count: int) -> dict[str, Any]:
        metrics: dict[str, Any] = {"entry_count": entry_count}
        probes = {
            "troop_empty_slots": "_count_troop_empty_slots",
            "top10_scheduled": "_count_top10_in_schedule",
            "excess_cluster_days": "_count_excess_cluster_days",
            "cluster_gaps": "_count_area_cluster_gaps",
        }
        for key, method_name in probes.items():
            method = getattr(scheduler, method_name, None)
            if not callable(method):
                continue
            try:
                metrics[key] = method()
            except Exception as exc:
                metrics[f"{key}_error"] = str(exc)

        top5_method = getattr(scheduler, "_count_non_exempt_top5_misses", None)
        if callable(top5_method):
            try:
                top5_count, details = top5_method()
                metrics["non_exempt_top5_misses"] = top5_count
                metrics["non_exempt_top5_preview"] = [
                    {"troop": troop, "activity": activity, "rank": rank}
                    for troop, activity, rank in details[:10]
                ]
            except Exception as exc:
                metrics["non_exempt_top5_misses_error"] = str(exc)
        return metrics

    def _diff_signatures(
        self,
        before: tuple[tuple[str, str, str, int], ...] | None,
        after: tuple[tuple[str, str, str, int], ...],
    ) -> dict[str, Any]:
        if before is None:
            return {
                "added_count": len(after),
                "removed_count": 0,
                "added": [],
                "removed": [],
            }

        before_counts = Counter(before)
        after_counts = Counter(after)
        added = list((after_counts - before_counts).elements())
        removed = list((before_counts - after_counts).elements())
        return {
            "added_count": len(added),
            "removed_count": len(removed),
            "added": [self._signature_to_dict(item) for item in added[:25]],
            "removed": [self._signature_to_dict(item) for item in removed[:25]],
        }

    def _signature_to_dict(self, item: tuple[str, str, str, int]) -> dict[str, Any]:
        troop_name, activity_name, day, slot = item
        return {
            "troop_name": troop_name,
            "activity_name": activity_name,
            "day": day,
            "slot": slot,
        }

    def _build_summary_text(self) -> str:
        lines = [
            f"Schedule Snapshot Trace: {self.week_id}",
            f"Run ID: {self.run_id}",
            f"Snapshots: {len(self.snapshots)}",
            "",
        ]
        for snapshot in self.snapshots:
            metrics = snapshot.get("metrics", {})
            diff = snapshot.get("diff", {})
            metadata = snapshot.get("metadata", {})
            status = metadata.get("status")
            status_label = f"; status={status}" if status else ""
            lines.append(
                f"{snapshot['step_index']:04d} [{snapshot.get('phase', 'unknown')}] "
                f"{snapshot.get('label', '')}"
            )
            lines.append(
                "  "
                f"reason={snapshot.get('reason', '')}; "
                f"entries={metrics.get('entry_count', '?')}; "
                f"empty_slots={metrics.get('troop_empty_slots', '?')}; "
                f"top5_misses={metrics.get('non_exempt_top5_misses', '?')}; "
                f"top10={metrics.get('top10_scheduled', '?')}; "
                f"+{diff.get('added_count', 0)} -{diff.get('removed_count', 0)}"
                f"{status_label}"
            )
            for key in ("added", "removed"):
                items = diff.get(key, [])
                if not items:
                    continue
                rendered = ", ".join(
                    f"{i['troop_name']}:{i['activity_name']}@{i['day']}-{i['slot']}"
                    for i in items[:5]
                )
                lines.append(f"  {key}: {rendered}")
            lines.append("")
        return "\n".join(lines)
