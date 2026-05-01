import shlex
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import agent_chat_watch  # noqa: E402


class AgentChatWatchTests(unittest.TestCase):
    def test_parse_agent_output_preserves_preamble_before_metadata(self) -> None:
        output = """I reviewed merged.md from scratch and found one required fix.

to: codex
status: open
requested_action: apply fix

The response body after the routing fields.
"""

        recipient, status, requested_action, body = agent_chat_watch.parse_agent_output(
            output,
            default_recipient="kevin",
        )

        self.assertEqual(recipient, "codex")
        self.assertEqual(status, "open")
        self.assertEqual(requested_action, "apply fix")
        self.assertEqual(
            body,
            "I reviewed merged.md from scratch and found one required fix.\n\n"
            "The response body after the routing fields.",
        )

    def test_run_agent_passes_prompt_on_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_agent = Path(tmpdir) / "fake_agent.py"
            fake_agent.write_text(
                "\n".join(
                    [
                        "import sys",
                        "prompt = sys.stdin.read()",
                        "print('to: codex')",
                        "print('status: answered')",
                        "print('requested_action: none')",
                        "print()",
                        "print(prompt)",
                    ]
                ),
                encoding="utf-8",
            )

            output = agent_chat_watch.run_agent(
                "claude",
                "prompt sent through stdin",
                REPO_ROOT,
                command_override=f"{shlex.quote(sys.executable)} {shlex.quote(str(fake_agent))}",
                timeout_seconds=5,
                codex_sandbox="read-only",
                claude_write=False,
            )

        self.assertIn("prompt sent through stdin", output)

    def test_discussion_prompt_uses_peer_discussion_rules(self) -> None:
        latest = agent_chat_watch.MessageBlock(
            raw="raw",
            timestamp="2026-01-01 09:00",
            sender="kevin",
            recipient="codex",
            status="open",
            requested_action="compare specs",
            body="What do you think of these specs? Compare them before deciding what to build.",
        )

        prompt = agent_chat_watch.build_prompt(
            "codex",
            "protocol",
            "chat text",
            latest,
            REPO_ROOT,
            can_edit=True,
            mode="discussion",
        )

        self.assertIn("Discussion mode:", prompt)
        self.assertIn("Treat this as a peer strategy discussion", prompt)
        self.assertIn("Do not edit the target artifact in discussion mode", prompt)
        self.assertIn("Keep the discussion open to the other agent", prompt)
        self.assertNotIn("Fix loop rule:", prompt)
        self.assertNotIn("Final artifact review rule:", prompt)

    def test_review_prompt_keeps_fix_loop_rules(self) -> None:
        latest = agent_chat_watch.MessageBlock(
            raw="raw",
            timestamp="2026-01-01 09:00",
            sender="claude",
            recipient="codex",
            status="open",
            requested_action="apply fix",
            body="Apply the required fix.",
        )

        prompt = agent_chat_watch.build_prompt(
            "codex",
            "protocol",
            "chat text",
            latest,
            REPO_ROOT,
            can_edit=True,
            mode="review",
        )

        self.assertIn("Fix loop rule:", prompt)
        self.assertIn("You may edit files directly", prompt)
        self.assertNotIn("Discussion mode:", prompt)

    def test_resolve_path_uses_fallback_root_when_primary_missing(self) -> None:
        with tempfile.TemporaryDirectory() as primary_dir, tempfile.TemporaryDirectory() as fallback_dir:
            primary_root = Path(primary_dir)
            fallback_root = Path(fallback_dir)
            fallback_file = fallback_root / "docs" / "protocol.md"
            fallback_file.parent.mkdir()
            fallback_file.write_text("protocol", encoding="utf-8")

            resolved = agent_chat_watch.resolve_path(
                "docs/protocol.md",
                primary_root,
                fallback_root=fallback_root,
            )

        self.assertEqual(resolved, fallback_file)

    def test_resolve_path_prefers_primary_root_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as primary_dir, tempfile.TemporaryDirectory() as fallback_dir:
            primary_root = Path(primary_dir)
            fallback_root = Path(fallback_dir)
            primary_file = primary_root / "docs" / "protocol.md"
            fallback_file = fallback_root / "docs" / "protocol.md"
            primary_file.parent.mkdir()
            fallback_file.parent.mkdir()
            primary_file.write_text("primary", encoding="utf-8")
            fallback_file.write_text("fallback", encoding="utf-8")

            resolved = agent_chat_watch.resolve_path(
                "docs/protocol.md",
                primary_root,
                fallback_root=fallback_root,
            )

        self.assertEqual(resolved, primary_file)


if __name__ == "__main__":
    unittest.main()
