#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import platform
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover recent local Claude session transcripts."
    )
    parser.add_argument("--cwd", help="Current working directory for repo-match scoring.")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of sessions to return. Default: 5.",
    )
    parser.add_argument(
        "--claude-projects-dir",
        help="Explicit Claude projects directory override.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a human-readable list.",
    )
    parser.add_argument(
        "--picker",
        action="store_true",
        help="Emit only the numbered picker entries for user selection.",
    )
    parser.add_argument(
        "--snapshot-out",
        help="Write the discovered session payload to this JSON file for deterministic later resolution.",
    )
    parser.add_argument(
        "--snapshot-in",
        help="Read a previously saved session payload instead of discovering sessions live.",
    )
    return parser.parse_args()


def candidate_projects_dirs(explicit: str | None) -> list[Path]:
    candidates: list[Path] = []
    demo_only = os.environ.get("CLAUDE_SESSION_HANDOFF_DEMO_ONLY") == "1"

    def add(path_str: str | None) -> None:
        if not path_str:
            return
        expanded = Path(path_str).expanduser()
        if expanded not in candidates:
            candidates.append(expanded)

    if explicit:
        add(explicit)
        return candidates

    explicit_env = os.environ.get("CLAUDE_PROJECTS_DIR")
    add(explicit_env)
    if demo_only and explicit_env:
        return candidates

    claude_home = os.environ.get("CLAUDE_HOME")
    if claude_home:
        add(str(Path(claude_home).expanduser() / "projects"))

    home = Path.home()
    system = platform.system()

    common = [
        home / ".claude" / "projects",
    ]
    if system == "Darwin":
        common.append(home / "Library" / "Application Support" / "Claude" / "projects")
    elif system == "Linux":
        common.extend(
            [
                home / ".config" / "claude" / "projects",
                home / ".local" / "share" / "claude" / "projects",
            ]
        )
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        localappdata = os.environ.get("LOCALAPPDATA")
        common.extend(
            [
                home / ".claude" / "projects",
                Path(appdata) / "Claude" / "projects" if appdata else None,
                Path(localappdata) / "Claude" / "projects" if localappdata else None,
            ]
        )

    for path in common:
        if path is not None:
            add(str(path))

    return candidates


def iter_session_files(projects_dirs: Iterable[Path]) -> tuple[list[Path], list[Path]]:
    checked: list[Path] = []
    session_files: list[Path] = []
    seen: set[Path] = set()
    for projects_dir in projects_dirs:
        checked.append(projects_dir)
        if not projects_dir.exists():
            continue
        for session_file in projects_dir.glob("*/*.jsonl"):
            if session_file not in seen and session_file.is_file():
                session_files.append(session_file)
                seen.add(session_file)
    return checked, session_files


def parse_iso(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = " ".join(value.replace("\n", " ").split())
    return text.strip()


def is_substantive_user_text(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "<local-command-caveat>" in lowered:
        return False
    if lowered.startswith("<command-name>"):
        return False
    if text in {"clear", "/clear", "clear clear", "/clear clear", "usage"}:
        return False
    return True


def has_local_command_markup(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return "<command-name>" in lowered or "<local-command-caveat>" in lowered


def is_clear_command(text: str) -> bool:
    return text.strip().lower() in {"clear", "/clear", "clear clear", "/clear clear"}


def truncate(text: str, limit: int = 110) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def parse_message_content(message: object, include_tool_results: bool = False) -> str:
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return clean_text(content)
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if item_type == "text":
                        raw_text = item.get("text")
                        if has_local_command_markup(raw_text):
                            continue
                        parts.append(clean_text(raw_text))
                    elif include_tool_results and item_type == "tool_result":
                        parts.append(clean_text(item.get("content")))
            return clean_text(" ".join(part for part in parts if part))
    return ""


@dataclass
class SessionSummary:
    session_id: str
    file_path: str
    project_path: str | None
    cwd: str | None
    updated_at: str | None
    updated_epoch: float
    title: str
    title_source: str
    preview: str
    repo_match: str
    checked_projects_dir: str | None


@dataclass
class SkippedSession:
    file_path: str
    error: str


def repo_match_label(current_cwd: Path | None, session_cwd: str | None) -> str:
    if current_cwd is None or not session_cwd:
        return "unknown"
    try:
        session_path = Path(session_cwd).expanduser().resolve()
        current_path = current_cwd.resolve()
    except OSError:
        return "unknown"

    if normalized_parts(current_path) == normalized_parts(session_path):
        return "strong"
    if path_contains(current_path, session_path) or path_contains(session_path, current_path):
        return "related"
    return "different"


def normalized_parts(path: Path) -> tuple[str, ...]:
    parts = path.parts
    if platform.system() == "Windows":
        return tuple(part.casefold() for part in parts)
    return tuple(parts)


def path_contains(parent: Path, child: Path) -> bool:
    parent_parts = normalized_parts(parent)
    child_parts = normalized_parts(child)
    if len(parent_parts) > len(child_parts):
        return False
    return child_parts[: len(parent_parts)] == parent_parts


def summarize_session(session_file: Path, current_cwd: Path | None) -> tuple[SessionSummary | None, str | None]:
    current_segment_first_user_text = ""
    current_segment_custom_title = ""
    current_segment_cwd = ""
    latest_timestamp: datetime | None = None
    latest_slug = ""
    session_id = session_file.stem
    parsed_entries = 0
    parse_errors = 0

    try:
        with session_file.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    parse_errors += 1
                    continue
                parsed_entries += 1

                if entry.get("sessionId"):
                    session_id = entry["sessionId"]
                if entry.get("cwd"):
                    current_segment_cwd = entry["cwd"]
                if entry.get("customTitle"):
                    current_segment_custom_title = clean_text(entry["customTitle"])
                if entry.get("slug"):
                    latest_slug = clean_text(entry["slug"])
                dt = parse_iso(entry.get("timestamp"))
                if dt and (latest_timestamp is None or dt > latest_timestamp):
                    latest_timestamp = dt

                if entry.get("type") == "user":
                    text = parse_message_content(entry.get("message"))
                    if is_clear_command(text):
                        current_segment_first_user_text = ""
                        current_segment_custom_title = ""
                        current_segment_cwd = entry.get("cwd") or ""
                    elif not current_segment_first_user_text and is_substantive_user_text(text):
                        current_segment_first_user_text = text
    except OSError as exc:
        return None, str(exc)

    if parsed_entries == 0:
        reason = "No parseable JSONL entries were found."
        if parse_errors:
            reason += f" Encountered {parse_errors} JSON decode error(s)."
        return None, reason

    updated_at = latest_timestamp.isoformat() if latest_timestamp else None
    updated_epoch = latest_timestamp.timestamp() if latest_timestamp else session_file.stat().st_mtime

    if current_segment_custom_title:
        title = current_segment_custom_title
        title_source = "custom_title"
    elif current_segment_first_user_text:
        title = truncate(current_segment_first_user_text, 80)
        title_source = "prompt"
    elif latest_slug:
        title = latest_slug.replace("-", " ")
        title_source = "slug"
    elif latest_timestamp:
        title = f"Session from {latest_timestamp.astimezone().strftime('%Y-%m-%d %H:%M')}"
        title_source = "timestamp"
    else:
        title = f"Session {session_id}"
        title_source = "session_id"

    preview = truncate(current_segment_first_user_text, 140) if current_segment_first_user_text else title
    return SessionSummary(
        session_id=session_id,
        file_path=str(session_file),
        project_path=str(session_file.parent),
        cwd=current_segment_cwd or None,
        updated_at=updated_at,
        updated_epoch=updated_epoch,
        title=title,
        title_source=title_source,
        preview=preview,
        repo_match=repo_match_label(current_cwd, current_segment_cwd or None),
        checked_projects_dir=str(session_file.parent.parent),
    ), None


def discover_payload(current_cwd: Path | None, projects_dirs: Iterable[Path], limit: int) -> dict[str, object]:
    checked, session_files = iter_session_files(projects_dirs)

    sessions: list[SessionSummary] = []
    skipped_sessions: list[SkippedSession] = []
    for session_file in session_files:
        summary, error = summarize_session(session_file, current_cwd)
        if summary:
            sessions.append(summary)
        elif error:
            skipped_sessions.append(SkippedSession(file_path=str(session_file), error=error))

    sessions.sort(key=lambda item: item.updated_epoch, reverse=True)
    sessions = sessions[: max(limit, 0)]

    return {
        "platform": platform.system(),
        "current_cwd": str(current_cwd) if current_cwd else None,
        "checked_projects_dirs": [str(path) for path in checked],
        "sessions": [asdict(session) for session in sessions],
        "skipped_sessions": [asdict(item) for item in skipped_sessions],
    }


def write_snapshot(snapshot_path: Path, payload: dict[str, object]) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_snapshot(snapshot_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Unable to read snapshot file {snapshot_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Snapshot file is not valid JSON: {snapshot_path}: {exc}") from exc

    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        raise SystemExit(f"Snapshot file does not contain a valid sessions list: {snapshot_path}")
    return payload


def human_time(iso_value: str | None) -> str:
    if not iso_value:
        return "unknown time"
    dt = parse_iso(iso_value)
    if not dt:
        return iso_value
    local = dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M")


def picker_title(title: str) -> str:
    return truncate(title, 78)


def should_show_picker_preview(session: dict[str, object]) -> bool:
    title = str(session.get("title") or "")
    preview = str(session.get("preview") or "")
    title_source = str(session.get("title_source") or "")
    if not preview or preview == title:
        return False
    return title_source != "prompt"


def main() -> int:
    args = parse_args()
    current_cwd = Path(args.cwd).expanduser() if args.cwd else None
    if args.snapshot_in:
        payload = load_snapshot(Path(args.snapshot_in).expanduser())
    else:
        projects_dirs = candidate_projects_dirs(args.claude_projects_dir)
        payload = discover_payload(current_cwd, projects_dirs, args.limit)

    if args.snapshot_out:
        write_snapshot(Path(args.snapshot_out).expanduser(), payload)

    sessions = payload["sessions"]

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    if args.picker:
        if not sessions:
            print("No Claude sessions found.")
            return 0
        for index, session in enumerate(sessions, start=1):
            print(f"{index}. {picker_title(session['title'])}")
            print(f"   Updated: {human_time(session['updated_at'])}")
            print(f"   Repo match: {session['repo_match']}")
            print(f"   Session ID: {session['session_id']}")
            if should_show_picker_preview(session):
                print(f"   Preview: {truncate(session['preview'], 110)}")
        return 0

    if not sessions:
        print("No Claude sessions found.")
        print(f"Platform: {payload['platform']}")
        print("Checked:")
        for path in payload["checked_projects_dirs"]:
            print(f"- {path}")
        skipped = payload.get("skipped_sessions") or []
        if skipped:
            print("Skipped malformed session files:")
            for item in skipped:
                print(f"- {item['file_path']}: {item['error']}")
        return 0

    print("Recent Claude sessions:")
    for index, session in enumerate(sessions, start=1):
        print(f"{index}. {picker_title(session['title'])}")
        print(f"   Updated: {human_time(session['updated_at'])}")
        print(f"   Repo match: {session['repo_match']}")
        print(f"   Session ID: {session['session_id']}")
        print(f"   Preview: {session['preview']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
