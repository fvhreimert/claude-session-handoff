from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "resolve_session_choice.py"
FIXTURES = ROOT / "tests" / "fixtures"


class ResolveSessionChoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="claude-session-handoff-choice-"))
        self.projects_dir = self.temp_dir / "projects"
        (self.projects_dir / "demo-project").mkdir(parents=True)
        (self.projects_dir / "other-project").mkdir(parents=True)
        shutil.copy(FIXTURES / "session_alpha.jsonl", self.projects_dir / "demo-project" / "session-alpha.jsonl")
        shutil.copy(FIXTURES / "session_beta.jsonl", self.projects_dir / "other-project" / "session-beta.jsonl")
        self.snapshot_path = self.temp_dir / "snapshot.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_field_output_returns_exact_path(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "discover_sessions.py"),
                "--claude-projects-dir",
                str(self.projects_dir),
                "--cwd",
                "/work/demo",
                "--limit",
                "5",
                "--json",
                "--snapshot-out",
                str(self.snapshot_path),
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--snapshot",
                str(self.snapshot_path),
                "--choice",
                "1",
                "--field",
                "file_path",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertTrue(result.stdout.strip().endswith("session-alpha.jsonl"))

    def test_snapshot_keeps_choice_stable_when_newer_file_appears(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "discover_sessions.py"),
                "--claude-projects-dir",
                str(self.projects_dir),
                "--cwd",
                "/work/demo",
                "--limit",
                "5",
                "--json",
                "--snapshot-out",
                str(self.snapshot_path),
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        newest_project = self.projects_dir / "newest-project"
        newest_project.mkdir(parents=True)
        shutil.copy(FIXTURES / "session_alpha.jsonl", newest_project / "session-newest.jsonl")
        session_text = (newest_project / "session-newest.jsonl").read_text(encoding="utf-8")
        session_text = session_text.replace("session-alpha", "session-newest").replace("2026-04-13T19:53:00Z", "2026-04-13T23:53:00Z").replace("2026-04-13T19:54:00Z", "2026-04-13T23:54:00Z").replace("2026-04-13T19:55:00Z", "2026-04-13T23:55:00Z")
        (newest_project / "session-newest.jsonl").write_text(session_text, encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--snapshot",
                str(self.snapshot_path),
                "--choice",
                "1",
                "--field",
                "session_id",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "session-alpha")

    def test_snapshot_picker_and_resolution_stay_aligned_end_to_end(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "discover_sessions.py"),
                "--claude-projects-dir",
                str(self.projects_dir),
                "--cwd",
                "/work/demo",
                "--limit",
                "5",
                "--json",
                "--snapshot-out",
                str(self.snapshot_path),
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        newest_project = self.projects_dir / "newest-project"
        newest_project.mkdir(parents=True)
        shutil.copy(FIXTURES / "session_alpha.jsonl", newest_project / "session-newest.jsonl")
        session_text = (newest_project / "session-newest.jsonl").read_text(encoding="utf-8")
        session_text = session_text.replace("session-alpha", "session-newest").replace("2026-04-13T19:53:00Z", "2026-04-13T23:53:00Z").replace("2026-04-13T19:54:00Z", "2026-04-13T23:54:00Z").replace("2026-04-13T19:55:00Z", "2026-04-13T23:55:00Z")
        (newest_project / "session-newest.jsonl").write_text(session_text, encoding="utf-8")

        picker_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "discover_sessions.py"),
                "--snapshot-in",
                str(self.snapshot_path),
                "--picker",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("1. Fix picker UX", picker_result.stdout)
        self.assertNotIn("session-newest", picker_result.stdout)

        resolve_result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--snapshot",
                str(self.snapshot_path),
                "--choice",
                "1",
                "--field",
                "file_path",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        selected_path = resolve_result.stdout.strip()
        self.assertTrue(selected_path.endswith("session-alpha.jsonl"))

        summarize_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "summarize_handoff.py"),
                "--session",
                selected_path,
                "--json",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(summarize_result.stdout)
        self.assertEqual(payload["session_id"], "session-alpha")


if __name__ == "__main__":
    unittest.main()
