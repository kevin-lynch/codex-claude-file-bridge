# Agent Discussion Protocol

Use this protocol when Codex and Claude need a real peer discussion before a plan, spec, architecture, or implementation direction is chosen.

This is not the review/fix protocol. The goal is not for one agent to submit an artifact and the other to approve it. The goal is to make both agents examine the same evidence, challenge each other, converge on a recommendation, and make unresolved tradeoffs visible to the human.

## Files

- Use one chat file per discussion.
- Put chat files in the target repo, usually under `docs/`.
- Name them clearly, for example:

```text
docs/agent_discussion_product_spec.md
```

## Message Format

```md
## YYYY-MM-DD HH:MM | from: sender | to: recipient | status: open
requested_action: short action

Message body.

---
```

Allowed statuses:

- `open`: waiting for a response
- `answered`: response provided, but no automated turn is pending
- `closed`: no further response needed
- `blocked`: human input is required before the discussion can continue

## Discussion Rules

- Append only. Do not edit, delete, or rewrite previous messages.
- One agent writes at a time.
- Reply only when directly addressed by the latest `open` message.
- Read the named artifacts before giving an opinion.
- Compare options and tradeoffs, not just wording.
- Challenge weak assumptions directly and explain the practical consequence.
- Distinguish facts found in files from inferences and recommendations.
- Keep the thread open while material disagreements or missing decisions remain.
- Close to the human only when the agents have a concrete joint recommendation, or block if human input is needed.
- Do not edit the target artifact during discussion mode. Propose a synthesis, decision, or next edit instead.
- Do not put secrets, API keys, passwords, tokens, or private credentials in chat files.

## Recommended Flow

1. Human or Codex opens the discussion with the artifacts and decision needed.
2. First agent evaluates the artifacts and sends a position to the second agent.
3. Second agent evaluates both artifacts and the first position, then either agrees with refinements or challenges it.
4. Agents continue until the remaining disagreements are either resolved or explicitly framed for the human.
5. Final agent sends the human a concise synthesis with:
   - recommended direction
   - decisions both agents agree on
   - open questions requiring human input
   - suggested next implementation slice

## Useful Requested Actions

- `evaluate and respond`
- `challenge assumptions`
- `compare specs`
- `propose synthesis`
- `resolve disagreements`
- `final synthesis`

## Starting Prompt Template

```md
## YYYY-MM-DD HH:MM | from: kevin | to: codex | status: open
requested_action: compare specs

Please evaluate these artifacts, then discuss with Claude before closing:

- /absolute/path/to/docs/product_spec.md
- /absolute/path/to/docs/product_spec_codex.md
- /absolute/path/to/docs/product_spec_claude.md

Goal:

Decide what should actually be built into the application and in what order.

Instructions:

- Do not edit files during this discussion.
- Start by giving Claude your view of the strongest product direction, biggest gaps, and highest-risk assumptions.
- Ask Claude to challenge your view and propose a synthesis.
- Keep the thread open until there is a shared recommendation or a clearly blocked human decision.

---
```

## Watcher Command

Run from the bridge repo while targeting another repo:

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
