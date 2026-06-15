# Claude/Codex File Bridge - How To Use

This is the canonical workflow for projects that use the local Claude/Codex
file bridge for blocking audits.

Project repos should reference this file instead of copying the full bridge
workflow into every `AGENTS.md`. Keep project-specific branch, deploy, product,
and domain rules in the target repo's own agent instructions.

## Bridge Repo

```text
/Users/kevinlynch/kplcode/my_repos/codex-claude-file-bridge
```

Before using the bridge, make sure the bridge repo is current:

```bash
cd /Users/kevinlynch/kplcode/my_repos/codex-claude-file-bridge
git pull --ff-only
```

## Core Rule

Codex implements. Claude audits through the local file bridge.

If Claude finds blocking issues, Codex fixes every required issue and reruns the
Claude audit. Repeat until Claude replies with `status: closed`.

Only after Claude closes should Codex treat the task as ready for commit, PR,
merge, deploy, or the next task, unless the user explicitly overrides that
project's agent instructions.

## Do Not Use Slack

- Do not use Slack for Claude/Codex audit handoffs.
- Do not ask the user to manually paste messages between agents.
- Do not commit bridge chat files.

## Target Repo Setup

Use the repository currently being edited as `<TARGET_REPO>`.

First determine it with:

```bash
pwd
```

Use that absolute path consistently in the audit file and watcher command.

Ensure `<TARGET_REPO>/.gitignore` ignores local bridge artifacts:

```gitignore
docs/agent_chat_*.md
docs/agent_discussion_*.md
```

Add those patterns if they are missing.

## Project AGENTS.md Snippet

Use this short snippet in project-level `AGENTS.md` files:

```md
## Claude/Codex Bridge

This repository uses the local Claude/Codex file bridge for blocking audits.

Before running a bridge audit, read and follow the canonical bridge workflow:

/Users/kevinlynch/kplcode/my_repos/codex-claude-file-bridge/docs/how_to_use.md

Bridge audit files are local coordination artifacts only. Do not commit files
matching `docs/agent_chat_*.md` or `docs/agent_discussion_*.md`.
```

Then keep any project-specific rules below that snippet, for example branch
policy, target PR base, deployment flow, product vocabulary, or domain-specific
implementation notes.

## Per Task Or PR

1. Follow the target repo's branch and merge policy.
2. Implement only the current task or section.
3. Run focused tests and appropriate validation.
4. Create a fresh bridge audit file:

   ```text
   <TARGET_REPO>/docs/agent_chat_<topic>_claude_audit.md
   ```

5. Write the audit request using this format:

   ```markdown
   ## YYYY-MM-DD HH:MM | from: codex | to: claude | status: open
   requested_action: blocking audit

   What do you think of this change?

   '<TARGET_REPO>'

   Changed files:
   - path/to/file1
   - path/to/file2

   Audit the actual current diff and files. Look for correctness, regressions, security, data safety, UX quality, code smell, missing tests, over-engineering, and anything that would not be acceptable in a greenfield production-grade product.

   Task intent:
   - Describe the exact task/section.
   - Describe all acceptance criteria.
   - Describe constraints such as env-only secrets, disabled-by-default providers, paid cap behavior, no legacy code, no technical debt, etc.

   Local validation already run:
   - list every command actually run
   - include focused tests
   - include full test suite where appropriate
   - include frontend build if frontend changed
   - include migration command if DB changed
   - include browser smoke checks if UI changed
   - include `git diff --check`

   If there are required fixes, reply to Codex with `status: open`.
   If there are no required fixes, reply to human with `status: closed`.
   ```

6. Run the watcher from the bridge repo:

   ```bash
   cd /Users/kevinlynch/kplcode/my_repos/codex-claude-file-bridge

   .venv/bin/python scripts/agent_chat_watch.py \
     <TARGET_REPO>/docs/agent_chat_<topic>_claude_audit.md \
     --repo-root <TARGET_REPO> \
     --protocol /Users/kevinlynch/kplcode/my_repos/codex-claude-file-bridge/docs/agent_chat_protocol.md \
     --agents=claude \
     --once \
     --timeout=1800
   ```

## Claude Runtime Isolation

Claude isolation is enabled by default in the bridge watcher.

By default, Claude runs with:

- no session persistence
- no Chrome integration
- strict empty MCP config
- disabled slash/plugin commands
- no user/project settings sources
- Claude Opus 4.8 (`--model claude-opus-4-8`)
- max effort (`--effort max`)
- explicit extended thinking
- read-only built-in tools unless `--claude-write` is explicitly set

This is intentional. It allows separate project audits to run in parallel
without sharing Claude session, MCP, Chrome, plugin, or project state.

Override the built-in Claude model and effort with `--claude-model` /
`--claude-effort` or `AGENT_CHAT_CLAUDE_MODEL` / `AGENT_CHAT_CLAUDE_EFFORT`.

Do not use `--no-claude-isolated`, `AGENT_CHAT_CLAUDE_ISOLATED=false`, or
`AGENT_CHAT_CLAUDE_CMD` unless explicitly debugging the bridge itself.

## After Claude Replies

If Claude replies with `status: open`:

1. Fix every required issue.
2. Rerun relevant validation.
3. Append a fresh audit request to the same bridge file.
4. Rerun the watcher.

Use this follow-up format:

```markdown
## YYYY-MM-DD HH:MM | from: codex | to: claude | status: open
requested_action: blocking audit

What do you think of this change?

'<TARGET_REPO>'

Changed files:
- path/to/file1
- path/to/file2

Audit the actual current diff and files.

Fixes since your previous review:
- list every required finding fixed
- list tests added or updated

Local validation rerun:
- list every command actually rerun

If there are required fixes, reply to Codex with `status: open`.
If there are no required fixes, reply to human with `status: closed`.
```

If Claude replies with `status: closed`:

1. Follow the target repo's git, PR, merge, and deploy policy.
2. Do not commit the bridge audit file.
3. Include Claude audit status and validation evidence in the final status.

## Testing Expectations

- Run focused tests for the touched area.
- Run broader tests only where the target repo's policy or change risk requires
  them.
- Run syntax/type checks for changed files.
- If frontend changed, run the project's frontend build.
- If DB changed, run migrations locally if safe.
- Always run `git diff --check`.
- If UI changed, run a browser smoke check and check console errors where
  practical.

## Security And Secrets

- API keys and secrets must come from environment variables unless the target
  repo explicitly says otherwise.
- Never expose secrets in API responses, UI, logs, docs, tests, or audit files.
- If a real key is missing and a live call is required, stop and ask the user.
- Mock third-party provider calls in tests unless the user explicitly asks for
  live verification.

## Quality Bar

- Production-grade from the start.
- No legacy, dead, or no-op code.
- No fake settings that appear to enable behavior but do nothing.
- No shortcuts or "fix later" debt unless the user explicitly accepts it.
- Prefer existing project patterns.
- Keep changes scoped.
- Add tests proportional to risk.

## Final Status To The User

Final status should include:

- Task or section completed.
- Branch name.
- PR number or link if created.
- Claude audit status.
- Tests and builds run.
- Merge or deploy state.
- Blockers, if any.
