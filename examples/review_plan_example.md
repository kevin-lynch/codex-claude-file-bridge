# Example Plan Review Prompt

Append this to a chat file when you want Claude to review a plan and Codex to apply required fixes.

```md
## YYYY-MM-DD HH:MM | from: human | to: claude | status: open
requested_action: final review

What do you think of this plan?

/absolute/path/to/project/docs/my_plan.md

Review the actual file from scratch. If you have required fixes, list them and address Codex with `status: open`. If you only have optional notes or no feedback, address the human with `status: closed`.

---
```

