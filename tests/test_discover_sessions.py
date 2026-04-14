from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "discover_sessions.py"
FIXTURES = ROOT / "tests" / "fixtures"


class DiscoverSessionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="claude-session-handoff-test-"))
        self.projects_dir = self.temp_dir / "projects"
        (self.projects_dir / "demo-project").mkdir(parents=True)
        (self.projects_dir / "other-project").mkdir(parents=True)
        (self.projects_dir / "sibling-project").mkdir(parents=True)
        (self.projects_dir / "clear-project").mkdir(parents=True)
        (self.projects_dir / "command-project").mkdir(parents=True)
        (self.projects_dir / "clear-stale-project").mkdir(parents=True)
        (self.projects_dir / "cwd-clear-project").mkdir(parents=True)
        shutil.copy(FIXTURES / "session_alpha.jsonl", self.projects_dir / "demo-project" / "session-alpha.jsonl")
        shutil.copy(FIXTURES / "session_beta.jsonl", self.projects_dir / "other-project" / "session-beta.jsonl")
        shutil.copy(FIXTURES / "session_sibling.jsonl", self.projects_dir / "sibling-project" / "session-sibling.jsonl")
        shutil.copy(FIXTURES / "session_clear.jsonl", self.projects_dir / "clear-project" / "session-clear.jsonl")
        shutil.copy(
            FIXTURES / "session_command_markup.jsonl",
            self.projects_dir / "command-project" / "session-command-markup.jsonl",
        )
        shutil.copy(
            FIXTURES / "session_clear_stale_title.jsonl",
            self.projects_dir / "clear-stale-project" / "session-clear-stale-title.jsonl",
        )
        shutil.copy(
            FIXTURES / "session_cwd_clear.jsonl",
            self.projects_dir / "cwd-clear-project" / "session-cwd-clear.jsonl",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=True,
        )

    def test_json_output_returns_sessions(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/work/demo",
            "--limit",
            "5",
            "--json",
        )
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["sessions"]), 5)
        self.assertEqual(payload["sessions"][0]["session_id"], "session-alpha")
        self.assertEqual(payload["sessions"][0]["repo_match"], "strong")

    def test_clear_resets_picker_summary_to_latest_task_segment(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/repo/demo",
            "--limit",
            "10",
            "--json",
        )
        payload = json.loads(result.stdout)
        clear_session = next(session for session in payload["sessions"] if session["session_id"] == "session-clear")
        self.assertEqual(clear_session["title"], "Second task title")
        self.assertEqual(clear_session["preview"], "Second task")

    def test_clear_discards_stale_custom_title(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/repo/demo",
            "--limit",
            "10",
            "--json",
        )
        payload = json.loads(result.stdout)
        clear_session = next(
            session for session in payload["sessions"] if session["session_id"] == "session-clear-stale-title"
        )
        self.assertEqual(clear_session["title"], "new task after clear")
        self.assertEqual(clear_session["title_source"], "prompt")
        self.assertEqual(clear_session["preview"], "new task after clear")

    def test_picker_output_uses_multiline_format(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/work/demo",
            "--picker",
        )
        self.assertIn("1. Fix picker UX", result.stdout)
        self.assertIn("   Updated:", result.stdout)
        self.assertIn("   Repo match: strong", result.stdout)
        self.assertIn("   Session ID: session-alpha", result.stdout)
        self.assertNotIn("2. new task after clear\n   Updated: 2026-04-13 16:04\n   Repo match: different\n   Session ID: session-clear-stale-title\n   Preview:", result.stdout)

    def test_picker_shows_preview_only_for_non_prompt_title_sources(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/repo/demo",
            "--limit",
            "10",
            "--picker",
        )
        self.assertIn("1. Fix picker UX", result.stdout)
        self.assertIn("Preview: Resume this feature and clean up the picker output.", result.stdout)
        self.assertNotIn("Preview: Real task after command wrapper", result.stdout)

    def test_command_markup_is_not_used_as_picker_summary(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/repo/demo",
            "--json",
        )
        payload = json.loads(result.stdout)
        command_session = next(
            session for session in payload["sessions"] if session["session_id"] == "session-command-markup"
        )
        self.assertEqual(command_session["title"], "Real task after command wrapper")
        self.assertEqual(command_session["preview"], "Real task after command wrapper")

    def test_malformed_jsonl_is_skipped(self) -> None:
        broken_project = self.projects_dir / "broken-project"
        broken_project.mkdir(parents=True)
        broken_file = broken_project / "broken-session.jsonl"
        broken_file.write_text('{"broken": true\nnot-json\n', encoding="utf-8")

        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/work/demo",
            "--json",
        )
        payload = json.loads(result.stdout)
        session_ids = [session["session_id"] for session in payload["sessions"]]
        self.assertNotIn("broken-session", session_ids)
        self.assertTrue(any(item["file_path"].endswith("broken-session.jsonl") for item in payload["skipped_sessions"]))

    def test_sibling_directories_are_not_marked_related(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/repo/app",
            "--json",
        )
        payload = json.loads(result.stdout)
        sibling = next(session for session in payload["sessions"] if session["session_id"] == "session-sibling")
        self.assertEqual(sibling["repo_match"], "different")

    def test_clear_resets_cwd_to_latest_task_segment(self) -> None:
        result = self.run_script(
            "--claude-projects-dir",
            str(self.projects_dir),
            "--cwd",
            "/repo/new",
            "--limit",
            "10",
            "--json",
        )
        payload = json.loads(result.stdout)
        cwd_session = next(session for session in payload["sessions"] if session["session_id"] == "session-cwd-clear")
        self.assertEqual(cwd_session["cwd"], "/repo/new")
        self.assertEqual(cwd_session["repo_match"], "strong")


if __name__ == "__main__":
    unittest.main()
