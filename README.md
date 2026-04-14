# claude-session-handoff

Recover a previous Claude Code session into a Codex handoff from local transcript files, without calling Claude in the normal path.

This is for the common failure mode where Claude Code hit a token limit, lost context, or the session ended, and you want Codex to continue from the local artifacts already on disk.

## What it does

- Finds recent local Claude sessions
- Shows a short numbered picker instead of guessing
- Resolves your choice from a saved snapshot, so the picked number stays stable
- Summarizes the selected transcript into a compact Codex handoff
- Stops after the handoff so you can decide what happens next

## Why this exists

The default recovery pattern is usually manual and messy: find the right transcript, inspect it, reconstruct intent, then restate the open thread to another agent. This skill makes that path deterministic and cheap.

- No Claude token usage in the normal flow
- No dependency on the `claude` CLI
- Works from transcript artifacts already on your machine

## Requirements

- Python 3.10+
- Codex CLI
- Local Claude session transcripts on disk

## Install

From the repository root:

```bash
python3 scripts/install_skill.py
```

If you prefer a copy instead of a symlink:

```bash
python3 scripts/install_skill.py --mode copy
```

Then restart Codex.

Manual install targets:

- macOS/Linux: `~/.codex/skills/claude-session-handoff`
- Windows: `%USERPROFILE%\.codex\skills\claude-session-handoff`

## Use

After installation, prompts like these should trigger the skill:

- `Resume my last Claude session for this repo`
- `Recover a Claude Code session that ended and give me a handoff`
- `Find my last 5 Claude sessions and ask which one to resume`

Normal flow:

1. Discover recent local Claude sessions
2. Show a numbered picker
3. Summarize the selected session into a Codex handoff

## Verify your setup

macOS/Linux:

```bash
python3 scripts/doctor.py --cwd "$PWD"
```

Windows PowerShell:

```powershell
py -3 scripts/doctor.py --cwd (Get-Location)
```

The doctor reports:

- whether the skill is installed into Codex
- which Claude directories were checked
- how many transcript files were found

## Run the scripts directly

macOS/Linux:

```bash
python3 scripts/discover_sessions.py --cwd "$PWD" --limit 5 --picker
python3 scripts/discover_sessions.py --cwd "$PWD" --limit 5 --json --snapshot-out /tmp/claude-session-handoff-snapshot.json
python3 scripts/discover_sessions.py --snapshot-in /tmp/claude-session-handoff-snapshot.json --picker
python3 scripts/resolve_session_choice.py --snapshot /tmp/claude-session-handoff-snapshot.json --choice 1 --field file_path
python3 scripts/summarize_handoff.py --session /path/to/session.jsonl --json
```

Windows PowerShell:

```powershell
$snapshot = Join-Path $env:TEMP "claude-session-handoff-snapshot.json"
py -3 scripts/discover_sessions.py --cwd (Get-Location) --limit 5 --picker
py -3 scripts/discover_sessions.py --cwd (Get-Location) --limit 5 --json --snapshot-out $snapshot
py -3 scripts/discover_sessions.py --snapshot-in $snapshot --picker
py -3 scripts/resolve_session_choice.py --snapshot $snapshot --choice 1 --field file_path
py -3 scripts/summarize_handoff.py --session C:\path\to\session.jsonl --json
```

## How discovery works

Discovery checks these locations in order:

1. `--claude-projects-dir`
2. `CLAUDE_PROJECTS_DIR`
3. `CLAUDE_HOME/projects`
4. platform defaults in [references/storage-locations.md](references/storage-locations.md)

If your Claude data lives elsewhere, pass `--claude-projects-dir`.

## Privacy and limits

- The normal path reads local transcript files only.
- The skill recovers a handoff, not Claude's exact internal state.
- It is best-effort and depends on Claude transcript formats staying close to the JSONL structures covered by the tests.
- Session selection still happens through normal Codex chat replies because this is a plain skill, not a custom UI.

## Troubleshooting

If no sessions are found:

- run `scripts/doctor.py`
- confirm Claude transcript files exist locally
- pass `--claude-projects-dir` if Claude stores data outside the default path

If the wrong session is selected:

- run the discovery script directly and inspect the picker output
- invoke the skill from the repository you actually want to match

If a session file is missing or corrupted:

- malformed transcripts are skipped when possible
- direct `summarize_handoff.py` calls return a file-specific error

## Development

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

The repository includes:

- `scripts/doctor.py` for local diagnostics
- `.github/workflows/ci.yml` for cross-platform CI
- `agents/openai.yaml` for packaged skill metadata

## License

MIT
