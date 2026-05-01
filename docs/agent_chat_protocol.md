# Agent Chat Protocol

Use this protocol when Codex and Claude need to collaborate through workspace files instead of IDE agent orchestration.

This protocol is for review/fix loops. For a peer strategy discussion where agents should challenge each other before choosing a direction, use `docs/agent_discussion_protocol.md` with `--mode discussion`.

## Files

- Use one chat file per topic.
- Put chat files in `docs/`.
- Name them clearly, for example:

```text
docs/agent_chat_feature_review.md
```

## Rules

- Append only. Do not edit, delete, or rewrite previous messages.
- One agent writes at a time.
- Reply only when directly addressed or when a message is marked `status: open`.
- Keep messages short and actionable.
- Include `from`, `to`, `status`, and `requested_action`.
- Do not include secrets, API keys, passwords, or private credentials.
- Prefer concrete findings, decisions, file references, and next actions over open-ended discussion.
- If a task is complete, set `status: closed`.

## Message Format

```md
## YYYY-MM-DD HH:MM | from: sender | to: recipient | status: open
requested_action: short action

Message body.

---
```

Allowed statuses:

- `open`: waiting for a response
- `answered`: response provided
- `closed`: no further response needed
- `blocked`: cannot proceed without user input

## Watcher Commands

Dry-run routing:

```bash
python3 scripts/agent_chat_watch.py docs/agent_chat_example.md --once --agents=codex,claude --dry-run
```

Read-only one-turn check:

```bash
python3 scripts/agent_chat_watch.py docs/agent_chat_example.md --once --agents=codex
```

Writable review/fix loop:

```bash
python3 scripts/agent_chat_watch.py docs/agent_chat_example.md --agents=codex,claude --poll=5 --max-turns=20 --codex-sandbox workspace-write --claude-write
```

Peer discussion loop:

```bash
python3 scripts/agent_chat_watch.py examples/spec_discussion_example.md --protocol docs/agent_discussion_protocol.md --mode discussion --agents=codex,claude --poll=5 --max-turns=20
```

## Completion Gate

A task is not complete just because an agent agrees with proposed edits. Completion requires a final artifact review.

For plans, docs, features, and code changes:

1. One agent applies the agreed edits to the target file.
2. The applying agent appends a plain final-review request to the reviewer.
3. If the reviewer finds required fixes, address them and repeat the review.
4. The thread may close when the reviewer has no required fixes. Optional notes, cosmetic wording, cautions, and future improvements do not keep the loop open.

Use `status: open` while any review, edit, or required fix remains. Use `status: closed` when the target artifact itself has been reviewed after the latest edits and the reviewer has no required fixes.

Required fixes include anything that affects correctness, implementation behavior, data safety, rollout risk, missing decisions, or ambiguity that could make two implementers build different things.

Optional notes include cosmetic wording, redundant phrasing, cautions, future improvements, preferences, and implementation awareness that does not change behavior.

## Final Review Request

Use this shape after every fix:

```text
What do you think of this <plan|feature|change>?

<absolute path to the target file, or absolute git/project root for a multi-file feature/change>
```

Do not ask:

- "does this address your feedback?"
- "are these changes OK?"

The reviewer must inspect the actual artifact again.

Use the most specific target:

- single plan/doc: the absolute file path
- single code file: the absolute file path
- multi-file feature/change: the absolute git/project root plus a short list of changed files
- ambiguous scope: ask the human before closing

## Reviewer Instructions

- Read the target itself, not only the chat thread.
- Treat every final-review request as a fresh full review of the current artifact.
- Review correctness, implementation behavior, data safety, rollout risk, missing decisions, ambiguity, and whether the artifact is ready to use.
- If you have required fixes, address the implementing agent with `status: open`.
- If you only have optional notes, address the human with `status: closed` and label the notes optional.
- If you have no fixes or notes, address the human with `status: closed`.

## Implementer Instructions

- Apply the requested fixes to the artifact before replying.
- Then address the reviewer with `status: open`.
- Repeat the exact final-review shape with the artifact path.
- Do not close the thread yourself after making fixes.

## Example

```md
## YYYY-MM-DD HH:MM | from: codex | to: claude | status: open
requested_action: final review

What do you think of this plan?

/absolute/path/to/project/docs/plan.md

Review the actual file. If you have required fixes, list them and address Codex. If you only have optional notes or no feedback, address the human and close.

---
```
