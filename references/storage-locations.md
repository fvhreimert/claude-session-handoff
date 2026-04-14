# Claude Storage Locations

This skill is designed to work without calling the `claude` CLI.

It looks for Claude project transcripts in these places, in order:

1. `--claude-projects-dir`
2. `CLAUDE_PROJECTS_DIR`
3. `CLAUDE_HOME/projects`
4. macOS:
   - `~/.claude/projects`
   - `~/Library/Application Support/Claude/projects`
5. Linux:
   - `~/.claude/projects`
   - `~/.config/claude/projects`
   - `~/.local/share/claude/projects`
6. Windows:
   - `%USERPROFILE%\.claude\projects`
   - `%APPDATA%\Claude\projects`
   - `%LOCALAPPDATA%\Claude\projects`

Observed Claude Code transcripts on this machine live under:

- `~/.claude/projects/<project-slug>/<session-id>.jsonl`

Useful fields seen in those JSONL entries:

- `sessionId`
- `timestamp`
- `cwd`
- `slug`
- `customTitle`
- `message`
- `toolUseResult`

Session summaries should prefer:

1. `customTitle`
2. first substantive user prompt
3. timestamp label

The transcript format may change between Claude versions, so scripts should degrade cleanly and report what was missing.
