# Codex Claude File Bridge

A local file-based handoff, review, and discussion loop for Codex CLI and Claude CLI.

It lets two agents collaborate through append-only Markdown chat files instead of paid IDE orchestration. The default workflow is deliberately simple: one agent reviews, the other applies required fixes, then the reviewer performs a fresh full review of the artifact.

For early product, architecture, or planning work, the watcher also supports a discussion mode where Codex and Claude challenge each other, compare tradeoffs, and converge on a joint recommendation without editing files.

## What It Does

- Uses Markdown files as the shared message board.
- Invokes local `codex` and `claude` CLIs.
- Supports read-only review or writable review/fix loops.
- Supports read-only peer discussion loops for product/spec/architecture decisions.
- Can run from this bridge repo while targeting another repo with `--repo-root`.
- Stops when the latest message is `closed` or `blocked`.
- In review mode, keeps looping only for required fixes.
- In review mode, treats optional notes as non-blocking.

## Requirements

- Python 3
- Codex CLI installed and authenticated
- Claude CLI installed and authenticated
- Optional: `nvm`; the watcher prefers the nvm default Node binary when resolving `codex` or `claude`

## Quick Start

Create a local virtual environment and run the tests:

```bash
python3 -m venv .venv
.venv/bin/python -m unittest discover -s tests
```

Create or edit a chat file such as:

```text
docs/agent_chat_example.md
```

Dry-run routing:

```bash
.venv/bin/python scripts/agent_chat_watch.py docs/agent_chat_example.md --once --agents=codex,claude --dry-run
```

Run one read-only Codex turn:

```bash
.venv/bin/python scripts/agent_chat_watch.py docs/agent_chat_example.md --once --agents=codex
```

Run a writable Codex/Claude review loop:

```bash
.venv/bin/python scripts/agent_chat_watch.py docs/agent_chat_example.md --agents=codex,claude --poll=5 --max-turns=20 --codex-sandbox workspace-write --claude-write
```

Run a read-only product/spec discussion against another repo:

```bash
.venv/bin/python scripts/agent_chat_watch.py \
  /absolute/path/to/target-repo/docs/agent_discussion_product_spec.md \
  --repo-root /absolute/path/to/target-repo \
  --protocol docs/agent_discussion_protocol.md \
  --mode discussion \
  --agents=codex,claude \
  --poll=5 \
  --max-turns=20
```

## Review Mode Stop Rule

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

## Discussion Mode

Use discussion mode when you do not want a one-way review. It is intended for:

- product specs
- architecture choices
- roadmap/build-order decisions
- implementation strategy before code edits

Discussion mode changes the agent prompt:

- agents do not edit files
- agents read named artifacts and compare tradeoffs
- disagreements are kept open and sent to the other agent
- the thread closes only when there is a joint recommendation or a human-blocking question

Use the discussion protocol:

```text
docs/agent_discussion_protocol.md
```

Example starter chat:

```text
examples/spec_discussion_example.md
```

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
