# Codex Claude File Bridge

A local file-based handoff and review loop for Codex CLI and Claude CLI.

It lets two agents collaborate through append-only Markdown chat files instead of paid IDE orchestration. The workflow is deliberately simple: one agent reviews, the other applies required fixes, then the reviewer performs a fresh full review of the artifact.

## What It Does

- Uses Markdown files as the shared message board.
- Invokes local `codex` and `claude` CLIs.
- Supports read-only review or writable review/fix loops.
- Stops when the latest message is `closed` or `blocked`.
- Keeps looping only for required fixes.
- Treats optional notes as non-blocking.

## Requirements

- Python 3
- Codex CLI installed and authenticated
- Claude CLI installed and authenticated
- Optional: `nvm`; the watcher prefers the nvm default Node binary when resolving `codex` or `claude`

## Quick Start

Create or edit a chat file such as:

```text
docs/agent_chat_example.md
```

Dry-run routing:

```bash
python3 scripts/agent_chat_watch.py docs/agent_chat_example.md --once --agents=codex,claude --dry-run
```

Run one read-only Codex turn:

```bash
python3 scripts/agent_chat_watch.py docs/agent_chat_example.md --once --agents=codex
```

Run a writable Codex/Claude review loop:

```bash
python3 scripts/agent_chat_watch.py docs/agent_chat_example.md --agents=codex,claude --poll=5 --max-turns=20 --codex-sandbox workspace-write --claude-write
```

## Stop Rule

The loop continues for required fixes only.

Required fixes are issues that affect:

- correctness
- implementation behavior
- data safety
- rollout risk
- missing decisions
- ambiguity that could make two implementers build different things

Optional notes do not keep the loop open:

- cosmetic wording
- redundant phrasing
- cautions
- future improvements
- preferences
- implementation awareness that does not change behavior

## Fresh Review Rule

After every fix, the implementing agent must ask for a fresh artifact review:

```text
What do you think of this <plan|feature|change>?

<absolute path to target file, or absolute project root plus changed files for multi-file work>
```

Do not ask only whether the latest edits are OK. The reviewer should inspect the actual artifact again.

## Chat Format

```md
## YYYY-MM-DD HH:MM | from: sender | to: recipient | status: open
requested_action: short action

Message body.

---
```

Allowed statuses:

- `open`
- `answered`
- `closed`
- `blocked`

## Environment Overrides

The watcher supports:

```text
AGENT_CHAT_CODEX_CMD
AGENT_CHAT_CLAUDE_CMD
AGENT_CHAT_CODEX_SANDBOX
AGENT_CHAT_CLAUDE_WRITE
```

## Safety Notes

- Do not commit real agent chats that contain private project details.
- Do not put secrets, API keys, passwords, tokens, or client data in chat files.
- Start with `--dry-run` to confirm routing.
- Use writable mode only when you want agents to edit files.

## License

MIT

