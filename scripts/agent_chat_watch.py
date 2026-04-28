#!/usr/bin/env python3
"""
File-based agent chat watcher.

Polls an agent chat markdown file and invokes a local agent CLI when the latest
open message is addressed to that agent. The agent returns response metadata and
body; this script appends the formatted block.

This intentionally uses a plain file as the message store so it works without
Cursor orchestration.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from shutil import which
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


HEADER_RE = re.compile(
    r"^##\s+(?P<ts>[^|]+)\|\s*from:\s*(?P<sender>[^|]+)\|\s*to:\s*(?P<to>[^|]+)\|\s*status:\s*(?P<status>\S+)\s*$",
    re.MULTILINE,
)

ALLOWED_STATUSES = {"open", "answered", "closed", "blocked"}


@dataclass
class MessageBlock:
    raw: str
    timestamp: str
    sender: str
    recipient: str
    status: str
    requested_action: str
    body: str


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_latest_message(chat_text: str) -> Optional[MessageBlock]:
    matches = list(HEADER_RE.finditer(chat_text))
    if not matches:
        return None

    match = matches[-1]
    start = match.start()
    next_match_start = len(chat_text)
    raw = chat_text[start:next_match_start].strip()

    body_text = chat_text[match.end() : next_match_start].strip()
    if body_text.endswith("---"):
        body_text = body_text[:-3].strip()

    requested_action = "none"
    body_lines = body_text.splitlines()
    if body_lines:
        first = body_lines[0].strip()
        if first.lower().startswith("requested_action:"):
            requested_action = first.split(":", 1)[1].strip() or "none"
            body_text = "\n".join(body_lines[1:]).strip()

    return MessageBlock(
        raw=raw,
        timestamp=match.group("ts").strip(),
        sender=match.group("sender").strip(),
        recipient=match.group("to").strip(),
        status=match.group("status").strip(),
        requested_action=requested_action,
        body=body_text,
    )


def is_final_artifact_review(latest: MessageBlock) -> bool:
    marker = "what do you think of this"
    return (
        "final" in latest.requested_action.lower()
        or marker in latest.body.lower()
    )


def build_prompt(
    agent_name: str,
    protocol_text: str,
    chat_text: str,
    latest: MessageBlock,
    repo_root: Path,
    can_edit: bool,
) -> str:
    edit_rule = (
        "- You may edit files directly when the latest message asks you to apply fixes.\n"
        if can_edit
        else "- Do not edit files directly in this run. If edits are required, describe them and address Codex.\n"
    )
    review_rule = ""
    if is_final_artifact_review(latest):
        review_rule = """
Final artifact review rule:
- Treat this as a fresh full review of the target artifact, not a review of only the latest changes.
- Read the target path named after "What do you think of this ...?" before answering.
- If you have required fixes, address Codex with status: open and list them.
- Required fixes affect correctness, implementation behavior, data safety, rollout risk, missing decisions, or ambiguity that could make two implementers build different things.
- Optional notes include cosmetic wording, redundant phrasing, cautions, future improvements, preferences, and implementation awareness that does not change behavior.
- If you only have optional notes or no feedback, address Kevin with status: closed.
"""

    fix_loop_rule = """
Fix loop rule:
- If you are Codex and the reviewer listed required fixes, apply the fixes when file editing is allowed.
- After applying fixes, address the reviewer with status: open and requested_action: final review.
- Your response body must include a fresh review request in this exact shape, using the current artifact type and absolute target path:

What do you think of this <plan|feature|change>?

<absolute target path, or absolute project root plus changed files for multi-file work>

- Do not ask whether the changes are okay. Ask for a fresh review of the artifact.
"""

    return f"""You are {agent_name} participating in a file-based agent chat.

Repository root:
{repo_root}

Protocol:
{protocol_text}

Current chat file:
{chat_text}

Latest message addressed to you:
from: {latest.sender}
to: {latest.recipient}
status: {latest.status}
requested_action: {latest.requested_action}

{latest.body}

Return only this response format, with no surrounding markdown fence:

to: claude|codex|kevin
status: answered|open|closed|blocked
requested_action: short action or none

Your response body.

Rules:
{edit_rule.rstrip()}
- Do not include the markdown header; this watcher will add it.
- The first non-empty lines of your response must be `to:`, `status:`, and `requested_action:` in that order.
- If you need the other agent to respond, set `to:` to that agent, use status: open, and set requested_action.
- If the plan is ready for Kevin, set `to: kevin` and status: closed.
- If no response is needed, use status: answered or closed.
- Keep the response concise and concrete.
{review_rule}
{fix_loop_rule}
"""


def parse_agent_output(output: str, default_recipient: str) -> tuple[str, str, str, str]:
    text = output.strip()
    recipient = default_recipient
    status = "answered"
    requested_action = "none"

    lines = text.splitlines()

    # Be tolerant of agents that put the routing metadata after an explanation.
    # Prefer the last complete metadata triplet and remove it from the body.
    for index in range(len(lines) - 3, -1, -1):
        if not lines[index].lower().startswith("to:"):
            continue
        if not lines[index + 1].lower().startswith("status:"):
            continue
        if not lines[index + 2].lower().startswith("requested_action:"):
            continue

        candidate_recipient = lines[index].split(":", 1)[1].strip().lower()
        candidate_status = lines[index + 1].split(":", 1)[1].strip().lower()
        candidate_action = lines[index + 2].split(":", 1)[1].strip() or "none"
        if candidate_recipient and candidate_status in ALLOWED_STATUSES:
            recipient = candidate_recipient
            status = candidate_status
            requested_action = candidate_action
            before = "\n".join(lines[:index]).strip()
            after = "\n".join(lines[index + 3 :]).strip()
            body = "\n\n".join(part for part in (before, after) if part)
            if not body:
                body = "(No response body returned.)"
            return recipient, status, requested_action, body

    body_start = 0
    if lines and lines[0].lower().startswith("to:"):
        candidate = lines[0].split(":", 1)[1].strip().lower()
        if candidate:
            recipient = candidate
        body_start = 1

    if len(lines) > body_start and lines[body_start].lower().startswith("status:"):
        candidate = lines[body_start].split(":", 1)[1].strip().lower()
        if candidate in ALLOWED_STATUSES:
            status = candidate
        body_start += 1

    if len(lines) > body_start and lines[body_start].lower().startswith("requested_action:"):
        requested_action = lines[body_start].split(":", 1)[1].strip() or "none"
        body_start += 1

    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    body = "\n".join(lines[body_start:]).strip()
    if not body:
        body = "(No response body returned.)"

    return recipient, status, requested_action, body


def default_command(agent_name: str, repo_root: Path, output_file: Path, codex_sandbox: str) -> list[str]:
    executable = resolve_agent_executable(agent_name)
    if agent_name == "codex":
        return [
            executable,
            "exec",
            "-C",
            str(repo_root),
            "-s",
            codex_sandbox,
            "--skip-git-repo-check",
            "-o",
            str(output_file),
            "-",
        ]
    if agent_name == "claude":
        # Claude Code commonly supports `claude -p` for non-interactive print mode.
        # If this local installation is broken, pass --claude-cmd to override after fixing it.
        return [executable, "-p"]
    raise ValueError(f"No default command for agent: {agent_name}")


def resolve_agent_executable(agent_name: str) -> str:
    """
    Prefer the nvm default install so the watcher still works if an older shell
    has a stale Node version earlier in PATH.
    """
    nvm_bin = resolve_nvm_default_bin()
    if nvm_bin:
        candidate = Path(nvm_bin) / agent_name
        if candidate.exists():
            return str(candidate)

    found = which(agent_name)
    return found or agent_name


def resolve_nvm_default_bin() -> Optional[str]:
    nvm_default = Path.home() / ".nvm" / "alias" / "default"
    if not nvm_default.exists():
        return None

    version = nvm_default.read_text(encoding="utf-8").strip()
    if not version:
        return None

    candidate = Path.home() / ".nvm" / "versions" / "node" / version / "bin"
    if candidate.exists():
        return str(candidate)
    return None


def run_agent(
    agent_name: str,
    prompt: str,
    repo_root: Path,
    command_override: Optional[str],
    timeout_seconds: int,
    codex_sandbox: str,
    claude_write: bool,
) -> str:
    with tempfile.TemporaryDirectory(prefix="agent-chat-") as tmpdir:
        output_file = Path(tmpdir) / f"{agent_name}-last-message.txt"
        if command_override:
            cmd = shlex.split(command_override)
        else:
            cmd = default_command(agent_name, repo_root, output_file, codex_sandbox)
            if agent_name == "claude" and claude_write:
                cmd.extend(["--permission-mode", "acceptEdits", "--tools", "default"])

        env = os.environ.copy()
        nvm_bin = resolve_nvm_default_bin()
        if nvm_bin:
            env["PATH"] = f"{nvm_bin}{os.pathsep}{env.get('PATH', '')}"

        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=timeout_seconds,
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"{agent_name} command failed with exit code {proc.returncode}\n"
                f"command: {' '.join(shlex.quote(part) for part in cmd)}\n"
                f"stderr:\n{proc.stderr.strip()}"
            )

        if output_file.exists() and output_file.read_text(encoding="utf-8").strip():
            return output_file.read_text(encoding="utf-8")

        if proc.stdout.strip():
            return proc.stdout

        return "(Agent command succeeded but returned no output.)"


def append_response(
    chat_file: Path,
    sender: str,
    recipient: str,
    status: str,
    requested_action: str,
    body: str,
) -> None:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    block = (
        f"\n## {now} | from: {sender} | to: {recipient} | status: {status}\n"
        f"requested_action: {requested_action or 'none'}\n\n"
        f"{body.strip()}\n\n"
        f"---\n"
    )
    with chat_file.open("a", encoding="utf-8") as handle:
        handle.write(block)


def should_handle(latest: MessageBlock, agents: set[str]) -> bool:
    return latest.status == "open" and latest.recipient.lower() in agents


def main() -> int:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description="Watch an agent chat file and invoke local agent CLIs.")
    parser.add_argument(
        "chat_file",
        nargs="?",
        default="docs/agent_chat_example.md",
        help="Path to chat markdown file, relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--protocol",
        default="docs/agent_chat_protocol.md",
        help="Path to protocol markdown file, relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--agents",
        default="codex",
        help="Comma-separated agents this watcher may invoke. Example: codex or codex,claude.",
    )
    parser.add_argument("--poll", type=float, default=5.0, help="Polling interval in seconds.")
    parser.add_argument("--once", action="store_true", help="Check once and exit.")
    parser.add_argument("--max-turns", type=int, default=1, help="Maximum agent turns before exit.")
    parser.add_argument("--timeout", type=int, default=900, help="Per-agent command timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without invoking agents.")
    parser.add_argument(
        "--codex-sandbox",
        default=os.getenv("AGENT_CHAT_CODEX_SANDBOX", "read-only"),
        choices=("read-only", "workspace-write", "danger-full-access"),
        help="Codex sandbox mode. Use workspace-write for auto-fix review loops.",
    )
    parser.add_argument(
        "--claude-write",
        action="store_true",
        default=os.getenv("AGENT_CHAT_CLAUDE_WRITE", "").lower() in {"1", "true", "yes"},
        help="Allow Claude to use edit-capable tools where the local Claude CLI supports them.",
    )
    parser.add_argument("--codex-cmd", default=os.getenv("AGENT_CHAT_CODEX_CMD"), help="Override Codex command.")
    parser.add_argument("--claude-cmd", default=os.getenv("AGENT_CHAT_CLAUDE_CMD"), help="Override Claude command.")

    args = parser.parse_args()

    chat_file = Path(args.chat_file)
    if not chat_file.is_absolute():
        chat_file = repo_root / chat_file
    protocol_file = Path(args.protocol)
    if not protocol_file.is_absolute():
        protocol_file = repo_root / protocol_file

    agents = {agent.strip().lower() for agent in args.agents.split(",") if agent.strip()}
    turns_taken = 0
    last_handled_raw = None

    print(f"Watching {chat_file}")
    print(f"Agents enabled: {', '.join(sorted(agents))}")
    if args.dry_run:
        print("Dry run: no agent commands will be invoked.")

    while turns_taken < args.max_turns:
        chat_text = read_text(chat_file)
        latest = parse_latest_message(chat_text)
        if latest and latest.status in {"closed", "blocked"}:
            print(
                f"Stopping. Latest message is to={latest.recipient}, status={latest.status}; "
                f"no automated agent turn is pending."
            )
            return 0

        if latest and should_handle(latest, agents) and latest.raw != last_handled_raw:
            agent = latest.recipient.lower()
            print(f"Turn {turns_taken + 1}: {latest.sender} -> {agent} ({latest.requested_action})")

            if args.dry_run:
                print(f"Would invoke {agent} and append response.")
                return 0 if args.once else 0

            protocol_text = read_text(protocol_file)
            can_edit = (
                (agent == "codex" and args.codex_sandbox != "read-only")
                or (agent == "claude" and args.claude_write)
            )
            prompt = build_prompt(agent, protocol_text, chat_text, latest, repo_root, can_edit=can_edit)
            command_override = args.codex_cmd if agent == "codex" else args.claude_cmd

            try:
                raw_output = run_agent(
                    agent,
                    prompt,
                    repo_root,
                    command_override=command_override,
                    timeout_seconds=args.timeout,
                    codex_sandbox=args.codex_sandbox,
                    claude_write=args.claude_write,
                )
                recipient, status, requested_action, body = parse_agent_output(
                    raw_output, default_recipient=latest.sender
                )
                append_response(
                    chat_file=chat_file,
                    sender=agent,
                    recipient=recipient,
                    status=status,
                    requested_action=requested_action,
                    body=body,
                )
                turns_taken += 1
                last_handled_raw = latest.raw
                print(f"Appended {agent} response with status: {status}")
            except Exception as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1

            if args.once:
                return 0
        elif args.once:
            if latest:
                print(
                    f"No action. Latest message is to={latest.recipient}, status={latest.status}; "
                    f"enabled agents={','.join(sorted(agents))}."
                )
            else:
                print("No parseable message found.")
            return 0

        time.sleep(args.poll)

    print(f"Stopped after {turns_taken} turn(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
