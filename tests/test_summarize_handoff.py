from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_handoff.py"
FIXTURES = ROOT / "tests" / "fixtures"


class SummarizeHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="claude-session-handoff-summary-"))
        self.session_path = self.temp_dir / "session-alpha.jsonl"
        shutil.copy(FIXTURES / "session_alpha.jsonl", self.session_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_json_handoff_is_structured(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(self.session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["session_id"], "session-alpha")
        self.assertEqual(payload["session_title"], "Fix picker UX")
        self.assertIn("Resume this feature", payload["original_objective"])
        self.assertIn("multiline format", payload["recent_context"])
        self.assertEqual(payload["open_thread"], "Most recent user ask: Resume this feature and clean up the picker output.")

    def test_likely_files_keeps_extensionless_and_missing_paths(self) -> None:
        session_path = self.temp_dir / "session-paths.jsonl"
        shutil.copy(FIXTURES / "session_paths.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("/repo/project/Dockerfile", payload["likely_files"])
        self.assertIn("/repo/project/Makefile", payload["likely_files"])
        self.assertIn("/repo/project/README", payload["likely_files"])
        self.assertIn("/repo/project/src/old_name", payload["likely_files"])

    def test_clear_resets_original_objective_to_latest_task_segment(self) -> None:
        session_path = self.temp_dir / "session-clear.jsonl"
        shutil.copy(FIXTURES / "session_clear.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["session_title"], "Second task title")
        self.assertEqual(payload["original_objective"], "Second task")

    def test_clear_discards_stale_custom_title_in_handoff(self) -> None:
        session_path = self.temp_dir / "session-clear-stale-title.jsonl"
        shutil.copy(FIXTURES / "session_clear_stale_title.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["session_title"], "new task after clear")
        self.assertEqual(payload["original_objective"], "new task after clear")

    def test_recent_user_ignores_tool_result_only_user_entries(self) -> None:
        session_path = self.temp_dir / "session-tool-result-user.jsonl"
        shutil.copy(FIXTURES / "session_tool_result_user.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("Latest user context: Check the config", payload["recent_context"])
        self.assertNotIn("name: demo", payload["recent_context"])

    def test_recent_context_prefers_latest_tool_activity_over_older_assistant_text(self) -> None:
        session_path = self.temp_dir / "session-latest-tool-only.jsonl"
        shutil.copy(FIXTURES / "session_latest_tool_only.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("Latest assistant activity: prepared tool calls to Read.", payload["recent_context"])
        self.assertNotIn("Earlier assistant reply", payload["recent_context"])
        self.assertEqual(payload["open_thread"], "Claude ended while preparing or awaiting a tool-driven step.")

    def test_latest_assistant_without_stop_reason_remains_latest(self) -> None:
        session_path = self.temp_dir / "session-empty-stop-reason-latest.jsonl"
        shutil.copy(FIXTURES / "session_empty_stop_reason_latest.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("Latest assistant output: Actual latest assistant reply", payload["recent_context"])
        self.assertNotIn("Read", payload["recent_context"])
        self.assertEqual(payload["open_thread"], "Most recent user ask: Continue the task")

    def test_likely_files_includes_filenames_lists(self) -> None:
        session_path = self.temp_dir / "session-filenames.jsonl"
        shutil.copy(FIXTURES / "session_filenames.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("/repo/demo/README", payload["likely_files"])
        self.assertIn("/repo/demo/Dockerfile", payload["likely_files"])
        self.assertIn("/repo/demo/src/main", payload["likely_files"])

    def test_windows_claude_internal_paths_are_filtered_from_likely_files(self) -> None:
        session_path = self.temp_dir / "session-windows-paths.jsonl"
        shutil.copy(FIXTURES / "session_windows_paths.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("C:\\repo\\src\\app.ts", payload["likely_files"])
        self.assertNotIn("C:\\Users\\tester\\.claude\\projects\\demo\\session.jsonl", payload["likely_files"])
        self.assertNotIn("C:\\Users\\tester\\.claude\\plans\\plan.md", payload["likely_files"])

    def test_partial_transcript_reports_partial_confidence(self) -> None:
        session_path = self.temp_dir / "session-partial.jsonl"
        shutil.copy(FIXTURES / "session_partial.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("partial local transcript", payload["confidence"])
        self.assertIn("skipped 1 malformed JSONL entry", payload["confidence"])

    def test_last_updated_uses_max_timestamp_not_last_line(self) -> None:
        session_path = self.temp_dir / "session-out-of-order-timestamps.jsonl"
        shutil.copy(FIXTURES / "session_out_of_order_timestamps.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["last_updated"], "2026-04-14T12:00:00Z")

    def test_command_markup_is_not_used_as_objective(self) -> None:
        session_path = self.temp_dir / "session-command-markup.jsonl"
        shutil.copy(FIXTURES / "session_command_markup.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["original_objective"], "Real task after command wrapper")
        self.assertEqual(payload["session_title"], "Real task after command wrapper")
        self.assertNotIn("npm test", payload["recent_context"])

    def test_human_readable_likely_files_resolve_against_repo_cwd(self) -> None:
        session_path = self.temp_dir / "session-relative-paths.jsonl"
        shutil.copy(FIXTURES / "session_relative_paths.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path)],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("/repo/project/src/app.py", result.stdout)
        self.assertNotIn(str(self.temp_dir / "src" / "app.py"), result.stdout)

    def test_generic_path_field_outside_repo_is_not_reported_as_likely_file(self) -> None:
        repo_dir = self.temp_dir / "repo"
        repo_dir.mkdir()
        session_path = self.temp_dir / "session-generic-path.jsonl"
        entries = [
            {
                "sessionId": "session-generic-path",
                "cwd": str(repo_dir),
                "timestamp": "2026-04-14T12:00:00Z",
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Inspect the API response"}]},
            },
            {
                "sessionId": "session-generic-path",
                "cwd": str(repo_dir),
                "timestamp": "2026-04-14T12:01:00Z",
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Checking response data"}]},
                "toolUseResult": {"path": "/v1/responses"},
            },
        ]
        session_path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertNotIn("/v1/responses", payload["likely_files"])

    def test_relative_directory_path_is_filtered_against_session_repo_not_process_cwd(self) -> None:
        repo_dir = self.temp_dir / "repo"
        src_dir = repo_dir / "src"
        src_dir.mkdir(parents=True)
        session_path = self.temp_dir / "session-relative-dir.jsonl"
        entries = [
            {
                "sessionId": "session-relative-dir",
                "cwd": str(repo_dir),
                "timestamp": "2026-04-14T12:00:00Z",
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Inspect the src directory"}]},
            },
            {
                "sessionId": "session-relative-dir",
                "cwd": str(repo_dir),
                "timestamp": "2026-04-14T12:01:00Z",
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Looking at src"}]},
                "toolUseResult": {"path": "src"},
            },
        ]
        session_path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertNotIn(str(src_dir), payload["likely_files"])
        self.assertNotIn("src", payload["likely_files"])

    def test_missing_session_path_returns_clean_error(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(self.temp_dir / "missing.jsonl")],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not read Claude session file", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_clear_resets_repo_to_latest_task_segment(self) -> None:
        session_path = self.temp_dir / "session-cwd-clear.jsonl"
        shutil.copy(FIXTURES / "session_cwd_clear.jsonl", session_path)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--session", str(session_path), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["repo"], "/repo/new")
        self.assertEqual(payload["session_title"], "New repo task")


if __name__ == "__main__":
    unittest.main()
