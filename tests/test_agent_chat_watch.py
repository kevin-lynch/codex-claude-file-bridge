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


if __name__ == "__main__":
    unittest.main()
