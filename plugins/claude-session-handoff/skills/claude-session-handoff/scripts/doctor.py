#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

from discover_sessions import candidate_projects_dirs, iter_session_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run basic environment checks for the claude-session-handoff skill."
    )
    parser.add_argument(
        "--cwd",
        help="Optional current working directory to use for repo-match context.",
    )
    parser.add_argument(
        "--claude-projects-dir",
        help="Explicit Claude projects directory override.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    skill_root = Path(__file__).resolve().parent.parent
    install_target = codex_home / "skills" / skill_root.name

    print("claude-session-handoff doctor")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Skill root: {skill_root}")
    print(f"Installed in Codex: {'yes' if install_target.exists() else 'no'}")
    print(f"Expected install target: {install_target}")
    if args.cwd:
        print(f"Current cwd: {Path(args.cwd).expanduser()}")

    print()
    print("Claude projects directories checked:")
    projects_dirs = candidate_projects_dirs(args.claude_projects_dir)
    checked, session_files = iter_session_files(projects_dirs)
    for path in checked:
        exists = "exists" if path.exists() else "missing"
        print(f"- {path} ({exists})")

    print()
    print(f"Discovered session transcripts: {len(session_files)}")
    if not session_files:
        print("No Claude session files were found. If Claude stores data elsewhere, rerun with --claude-projects-dir.")
        return 1

    print("Doctor check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
