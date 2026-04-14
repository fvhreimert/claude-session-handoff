#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any


DEFAULT_MARKETPLACE_NAME = "personal-plugins"
DEFAULT_MARKETPLACE_DISPLAY_NAME = "Personal Plugins"
PLUGIN_INSTALL_POLICY = "AVAILABLE"
PLUGIN_AUTH_POLICY = "ON_INSTALL"
PLUGIN_CATEGORY = "Productivity"


def parse_args() -> argparse.Namespace:
    default_mode = "copy" if platform.system() == "Windows" else "symlink"
    parser = argparse.ArgumentParser(
        description="Install the claude-session-handoff Codex plugin into your personal marketplace."
    )
    parser.add_argument(
        "--source",
        default=Path(__file__).resolve().parent.parent / "plugins" / "claude-session-handoff",
        help="Path to the local plugin directory. Default: repository plugin package.",
    )
    parser.add_argument(
        "--plugins-dir",
        default=Path.home() / "plugins",
        help="Directory where personal Codex plugins live. Default: ~/plugins.",
    )
    parser.add_argument(
        "--marketplace-path",
        default=Path.home() / ".agents" / "plugins" / "marketplace.json",
        help="Path to the personal Codex marketplace file. Default: ~/.agents/plugins/marketplace.json.",
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
        help="Replace an existing installed plugin directory and marketplace entry.",
    )
    return parser.parse_args()


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def ensure_valid_source(source: Path) -> str:
    manifest = source / ".codex-plugin" / "plugin.json"
    if not source.exists() or not source.is_dir():
        raise SystemExit(f"Plugin source directory does not exist: {source}")
    if not manifest.exists():
        raise SystemExit(f"Missing plugin manifest: {manifest}")
    with manifest.open() as handle:
        payload = json.load(handle)
    plugin_name = payload.get("name")
    if not isinstance(plugin_name, str) or not plugin_name:
        raise SystemExit(f"Plugin manifest is missing a valid name: {manifest}")
    return plugin_name


def install_plugin(source: Path, target: Path, mode: str, force: bool) -> None:
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
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def load_marketplace(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "name": DEFAULT_MARKETPLACE_NAME,
            "interface": {"displayName": DEFAULT_MARKETPLACE_DISPLAY_NAME},
            "plugins": [],
        }
    with path.open() as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"Marketplace file must contain a JSON object: {path}")
    return payload


def update_marketplace(path: Path, plugin_name: str, force: bool) -> None:
    payload = load_marketplace(path)
    plugins = payload.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise SystemExit(f"Marketplace 'plugins' field must be an array: {path}")

    payload.setdefault("name", DEFAULT_MARKETPLACE_NAME)
    interface = payload.setdefault("interface", {})
    if isinstance(interface, dict):
        interface.setdefault("displayName", DEFAULT_MARKETPLACE_DISPLAY_NAME)
    else:
        raise SystemExit(f"Marketplace 'interface' field must be an object: {path}")

    entry = {
        "name": plugin_name,
        "source": {
            "source": "local",
            "path": f"./plugins/{plugin_name}",
        },
        "policy": {
            "installation": PLUGIN_INSTALL_POLICY,
            "authentication": PLUGIN_AUTH_POLICY,
        },
        "category": PLUGIN_CATEGORY,
    }

    for index, existing in enumerate(plugins):
        if isinstance(existing, dict) and existing.get("name") == plugin_name:
            if not force:
                raise SystemExit(
                    f"Marketplace entry already exists for {plugin_name}: {path}\n"
                    "Re-run with --force to replace it."
                )
            plugins[index] = entry
            break
    else:
        plugins.append(entry)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    plugins_dir = Path(args.plugins_dir).expanduser().resolve()
    marketplace_path = Path(args.marketplace_path).expanduser().resolve()

    plugin_name = ensure_valid_source(source)
    target = plugins_dir / plugin_name

    install_plugin(source, target, args.mode, args.force)
    update_marketplace(marketplace_path, plugin_name, args.force)

    print(f"Installed plugin: {target}")
    print(f"Updated marketplace: {marketplace_path}")
    print("Restart Codex, then open /plugins to install or verify the plugin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
