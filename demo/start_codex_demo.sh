#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO_PROJECTS_DIR="$REPO_ROOT/demo/claude-projects"
DEMO_WORKSPACE="${DEMO_WORKSPACE:-/tmp/claude-session-handoff-demo-workspace}"

mkdir -p "$DEMO_WORKSPACE"

echo "Starting Codex demo session"
echo "Workspace: $DEMO_WORKSPACE"
echo "Claude projects dir: $DEMO_PROJECTS_DIR"

cd "$DEMO_WORKSPACE"
CLAUDE_PROJECTS_DIR="$DEMO_PROJECTS_DIR" CLAUDE_SESSION_HANDOFF_DEMO_ONLY=1 codex
