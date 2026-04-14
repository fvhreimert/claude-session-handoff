---
name: claude-session-handoff
description: Recover a prior Claude Code session into a Codex handoff without spending Claude tokens. Use when the user wants Codex to resume, recover, continue, import, or finish work from an ended Claude Code session, especially after Claude hit token limits. This skill discovers recent local Claude sessions, shows a short numbered picker, asks the user which session to use, then summarizes the selected session into a compact Codex handoff and stops.
---

# Resume Claude Session

Use this skill when the user wants Codex to pick up work that started in Claude Code.

Default behavior:
- Discover local Claude session transcripts without calling Claude.
- Show the 5 most recent sessions as a numbered list.
- Ask the user which session to resume.
- Summarize the selected session into a Codex handoff.
- Stop after the handoff unless the user explicitly asks Codex to continue the task.

Do not spend Claude tokens unless the user explicitly asks for a CLI fallback.
Keep internal tool output quiet. Use machine-readable script output for internal steps, and only show the user:
- one short picker
- one final handoff
- a short failure message when needed

Do not paste raw JSON or full script stdout into the user-facing response.
Do not repeat the session list after the user has already picked a number.
Do not narrate command names unless a failure requires it.

## Workflow

1. Run `scripts/discover_sessions.py --json --snapshot-out <temp_snapshot>` to get structured session data internally and save the exact displayed ordering.
2. If the current repository is known, pass `--cwd <current_repo_path>` so repo matches are labeled.
3. For the visible picker, render from the same saved snapshot instead of doing a second live discovery:

```bash
python3 scripts/discover_sessions.py --snapshot-in <temp_snapshot> --picker
```

4. Keep the picker in this multiline format:
   - title or task summary
   - `Updated`
   - `Repo match`
   - `Session ID`
   Do not collapse it into a one-line summary.
5. Ask the user which session to resume. Keep the prompt short, for example:

```text
I found these Claude sessions. Which one should I resume? Reply with the number.
```

6. After the user chooses, do not reconstruct the path from the printed list and do not re-discover the live filesystem. Resolve the numeric choice from the saved snapshot with:

```bash
python3 scripts/resolve_session_choice.py --snapshot <temp_snapshot> --choice <n> --field file_path
```

7. Pass the returned file path to:

```bash
python3 scripts/summarize_handoff.py --session <file_path> --json
```

8. Parse the JSON internally and return one concise handoff summary. Stop there unless the user explicitly asks Codex to continue the work.

## Discovery Rules

- Prefer local Claude artifacts over the `claude` CLI.
- Show only the 5 most recent sessions by default.
- Prefer a saved title if present.
- Otherwise use the first substantive user request as the task summary.
- If no useful summary exists, fall back to a timestamp label.
- Label repo match as:
  - `strong` when the session `cwd` exactly matches the current working directory
  - `related` when one path is inside the other
  - `different` otherwise

## Commands

Discover recent sessions:

```bash
python3 scripts/discover_sessions.py --cwd "$PWD" --limit 5 --json --snapshot-out /tmp/claude-session-handoff-snapshot.json
```

Render the user-facing picker:

```bash
python3 scripts/discover_sessions.py --snapshot-in /tmp/claude-session-handoff-snapshot.json --picker
```

Resolve the user's numeric choice to the exact transcript path:

```bash
python3 scripts/resolve_session_choice.py --snapshot /tmp/claude-session-handoff-snapshot.json --choice 2 --field file_path
```

Summarize a selected session:

```bash
python3 scripts/summarize_handoff.py --session /path/to/session.jsonl --json
```

If Claude data is not under the default location, allow overrides:

```bash
python3 scripts/discover_sessions.py --cwd "$PWD" --claude-projects-dir /custom/path/to/projects
```

## Output Contract

The handoff should be concise and structured for Codex. Include:
- `Session`: title and session id
- `Repo`: detected cwd and repo match
- `Original objective`: first substantive user request
- `Recent context`: tail-first summary of the latest user and assistant activity
- `Likely files`: touched file paths if they can be inferred
- `Open thread`: best-effort statement of what still looked unresolved
- `Confidence`: whether the summary came from a complete local transcript or from partial metadata

Do not claim the session is fully resumed. State that Codex has recovered a local handoff from Claude session artifacts.
Default to short prose, not a large dump of fields. Use a compact list only when it improves readability.

## Failure Handling

If no sessions are found:
- explain which Claude directories were checked
- mention the current platform
- suggest `--claude-projects-dir`
- ask the user for the Claude data path or a specific session file

If parsing fails for a session:
- skip the broken file if other sessions are available
- otherwise report the parse error and the exact file path

If the user already provided a transcript file path:
- skip the picker
- summarize that session directly

## Resources

- Storage locations and path assumptions: `references/storage-locations.md`
- Session discovery script: `scripts/discover_sessions.py`
- Session choice resolver: `scripts/resolve_session_choice.py`
- Handoff summarizer: `scripts/summarize_handoff.py`
