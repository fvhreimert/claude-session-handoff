#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from discover_sessions import (
    candidate_projects_dirs,
    discover_payload,
    load_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a numbered Claude session choice to an exact session file."
    )
    parser.add_argument("--choice", type=int, required=True, help="1-based choice from the displayed session list.")
    parser.add_argument("--cwd", help="Current working directory used during discovery.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of sessions considered. Default: 5.")
    parser.add_argument("--claude-projects-dir", help="Explicit Claude projects directory override.")
    parser.add_argument(
        "--snapshot",
        help="Path to a previously saved discover_sessions snapshot. Use this for deterministic choice resolution.",
    )
    parser.add_argument(
        "--field",
        choices=["file_path", "session_id", "title", "cwd"],
        help="Return only one field instead of the full JSON object.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.snapshot:
        payload = load_snapshot(Path(args.snapshot).expanduser())
    else:
        current_cwd = Path(args.cwd).expanduser() if args.cwd else None
        projects_dirs = candidate_projects_dirs(args.claude_projects_dir)
        payload = discover_payload(current_cwd, projects_dirs, args.limit)

    sessions = payload["sessions"]

    if not sessions:
        raise SystemExit("No Claude sessions were found.")

    if args.choice < 1 or args.choice > len(sessions):
        raise SystemExit(f"Choice {args.choice} is out of range. Valid range: 1-{len(sessions)}.")

    selected = sessions[args.choice - 1]
    if args.field:
        print(selected[args.field])
    else:
        print(json.dumps(selected, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
