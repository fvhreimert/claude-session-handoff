# Demo Recording Guide

This branch exists only to make clean recordings of `claude-session-handoff`.

It does not change the product behavior in `main`. Instead, it provides a fake
Claude projects directory and a small launcher so Codex discovers sanitized demo
sessions instead of real local Claude history.

## What this gives you

- fake project names
- fake session IDs
- deterministic picker ordering
- no accidental leaks from your real Claude history

## Quick start

1. Install the plugin from this repository if you have not already:

```bash
python3 scripts/install_plugin.py --force
```

2. Start a clean throwaway workspace for the recording:

```bash
mkdir -p /tmp/claude-session-handoff-demo-workspace
```

3. Launch Codex with demo transcripts enabled:

```bash
./demo/start_codex_demo.sh
```

This opens Codex with:

- `CLAUDE_PROJECTS_DIR` pointed at `demo/claude-projects`
- `CLAUDE_SESSION_HANDOFF_DEMO_ONLY=1` so real Claude history is excluded
- current working directory set to `/tmp/claude-session-handoff-demo-workspace`

That makes the fake demo sessions show up as `Repo match: strong`.

## Recommended recording flow

Type exactly this:

```text
Resume my last Claude session
```

Wait for the picker, then type:

```text
1
```

Stop recording after the handoff appears.

Keep the take short so Codex does not emit the `/compact` reminder.

## Asciinema steps

1. Open a clean terminal window with a larger font.
2. Start recording:

```bash
asciinema rec claude-session-handoff-demo.cast
```

3. Run:

```bash
cd /Users/frederikreimert/Documents/Skills/claude-session-handoff
./demo/start_codex_demo.sh
```

4. In Codex, type:

```text
Resume my last Claude session
```

5. Type `1` when the picker appears.
6. Stop the recording as soon as the handoff is rendered.
7. Convert/crop the cast into GIF with your preferred toolchain.

## Trim and speed up an existing cast

If the cast already starts at the right place and you only want to cut the tail
and speed it up slightly, run:

```bash
python3 demo/trim_cast.py \
  claude-session-handoff-demo.cast \
  claude-session-handoff-demo-trimmed.cast \
  --trim-end 2 \
  --speed 1.25
```

Preview the result:

```bash
asciinema play claude-session-handoff-demo-trimmed.cast
```

Then render that trimmed cast to GIF with your preferred renderer.

## Notes

- The demo fixtures are intentionally fake and safe to publish.
- If you want a different picker order or nicer titles, edit the JSONL files in `demo/claude-projects/`.
- This branch is only for recordings. Do not merge it into `main` unless you decide demo fixtures should ship.
