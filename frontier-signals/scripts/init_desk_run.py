#!/usr/bin/env python3
"""Create one bounded Frontier Signals Agent Desk run manifest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("Asia/Shanghai")


def build_manifest(
    *,
    now: datetime,
    window_hours: int,
    max_workers: int,
    max_candidates: int,
    max_retries: int,
) -> dict:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not 1 <= window_hours <= 72:
        raise ValueError("window_hours must be between 1 and 72")
    if not 1 <= max_workers <= 3:
        raise ValueError("max_workers must be between 1 and 3")
    if not 1 <= max_candidates <= 5:
        raise ValueError("max_candidates must be between 1 and 5")
    if not 0 <= max_retries <= 1:
        raise ValueError("max_retries must be 0 or 1")
    current = now.astimezone(TIMEZONE)
    return {
        "schema_version": 1,
        "run_id": current.strftime("%Y%m%dT%H%M%S%z"),
        "timezone": "Asia/Shanghai",
        "started_at": current.isoformat(timespec="seconds"),
        "window_start": (current - timedelta(hours=window_hours)).isoformat(timespec="seconds"),
        "window_end": current.isoformat(timespec="seconds"),
        "max_workers": max_workers,
        "max_candidates": max_candidates,
        "max_retries": max_retries,
        "status": "scouting",
        "scout_tasks": [],
        "candidates": [],
        "selected_candidate_id": None,
        "research_tasks": [],
        "reviewer": None,
        "failures": [],
        "outward_actions": [],
        "finished_at": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a bounded Frontier Signals desk-run.json")
    parser.add_argument("output", type=Path)
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--max-retries", type=int, default=1)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error(f"refusing to overwrite existing file: {args.output}")
    try:
        manifest = build_manifest(
            now=datetime.now(TIMEZONE),
            window_hours=args.window_hours,
            max_workers=args.max_workers,
            max_candidates=args.max_candidates,
            max_retries=args.max_retries,
        )
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "file": str(args.output), "run_id": manifest["run_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
