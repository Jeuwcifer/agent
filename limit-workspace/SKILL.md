---
name: limit-workspace
description: Restricts the agent workspace to a defined folder. Denies operations outside it.
---

# Limit Workspace Skill

Restrict all file system and execution operations (read, write, edit, bash) to a specifically defined workspace directory.

## Rules
- Verify absolute paths before executing any tool.
- Reject operations outside the allowed directory.
- State the restriction clearly if an out-of-bounds access is requested.
- If the allowed workspace path is not defined, ask the user to specify it before proceeding.