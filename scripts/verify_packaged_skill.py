#!/usr/bin/env python3

from __future__ import annotations

import filecmp
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = ROOT / "plugins" / "claude-session-handoff" / "skills" / "claude-session-handoff"

SHARED_PATHS = (
    "agents/openai.yaml",
    "references/storage-locations.md",
    "scripts/discover_sessions.py",
    "scripts/doctor.py",
    "scripts/install_skill.py",
    "scripts/resolve_session_choice.py",
    "scripts/summarize_handoff.py",
)


def main() -> int:
    mismatches: list[str] = []
    for relative_path in SHARED_PATHS:
        source = ROOT / relative_path
        packaged = PACKAGE_ROOT / relative_path
        if not source.exists():
            mismatches.append(f"Missing source file: {source}")
            continue
        if not packaged.exists():
            mismatches.append(f"Missing packaged file: {packaged}")
            continue
        if not filecmp.cmp(source, packaged, shallow=False):
            mismatches.append(f"Packaged file is out of sync: {relative_path}")

    if mismatches:
        for mismatch in mismatches:
            print(mismatch)
        return 1

    print("Packaged skill files are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
