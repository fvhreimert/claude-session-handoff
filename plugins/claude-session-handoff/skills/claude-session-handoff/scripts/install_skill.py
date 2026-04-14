#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import platform
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    default_mode = "copy" if platform.system() == "Windows" else "symlink"
    parser = argparse.ArgumentParser(
        description="Install the claude-session-handoff skill into a Codex skills directory."
    )
    parser.add_argument(
        "--source",
        default=Path(__file__).resolve().parent.parent,
        help="Path to the local skill directory. Default: this repository root.",
    )
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")),
        help="Codex home directory. Default: $CODEX_HOME or ~/.codex.",
    )
    parser.add_argument(
        "--mode",
        choices=["symlink", "copy"],
        default=default_mode,
        help="Install mode. Defaults to copy on Windows and symlink elsewhere.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing installed skill at the target path.",
    )
    return parser.parse_args()


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def ensure_valid_source(source: Path) -> None:
    skill_file = source / "SKILL.md"
    if not source.exists() or not source.is_dir():
        raise SystemExit(f"Skill source directory does not exist: {source}")
    if not skill_file.exists():
        raise SystemExit(f"Missing SKILL.md in skill source: {skill_file}")


def install(source: Path, target: Path, mode: str, force: bool) -> None:
    if target.exists() or target.is_symlink():
        if not force:
            raise SystemExit(
                f"Target already exists: {target}\nRe-run with --force to replace it."
            )
        remove_existing(target)

    target.parent.mkdir(parents=True, exist_ok=True)

    if mode == "symlink":
        target.symlink_to(source, target_is_directory=True)
    else:
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    codex_home = Path(args.codex_home).expanduser().resolve()
    target = codex_home / "skills" / source.name

    ensure_valid_source(source)
    install(source, target, args.mode, args.force)

    print(f"Installed: {target}")
    print("Restart Codex to pick up the new skill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
