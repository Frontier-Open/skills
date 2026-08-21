from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from init_desk_run import build_manifest  # noqa: E402


class DeskRunTests(unittest.TestCase):
    def test_manifest_is_bounded_and_has_no_outward_actions(self) -> None:
        manifest = build_manifest(
            now=datetime(2026, 8, 18, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
            window_hours=24,
            max_workers=3,
            max_candidates=5,
            max_retries=1,
        )
        self.assertEqual("20260818T090000+0800", manifest["run_id"])
        self.assertEqual([], manifest["outward_actions"])
        self.assertEqual(3, manifest["max_workers"])
        self.assertEqual(1, manifest["max_retries"])

    def test_manifest_rejects_unbounded_values(self) -> None:
        with self.assertRaises(ValueError):
            build_manifest(
                now=datetime.now(ZoneInfo("Asia/Shanghai")),
                window_hours=24,
                max_workers=4,
                max_candidates=5,
                max_retries=1,
            )


if __name__ == "__main__":
    unittest.main()
