---
name: self-reflection
description: Enforces a token-efficient plan-critique-output loop to improve reasoning before generating the final response.
---

# Self-Reflection Skill

References are relative to the directory containing this file.

## Instructions
Enforce an internal review loop before final output. To prevent token bloat and conflicts with brevity skills (e.g., `no-fluff`):

1. **Plan**: Outline the proposed solution in ultra-concise bullet points inside `<thinking>` tags. Do not write a full draft.
2. **Critique**: Identify edge cases, logical flaws, or inefficiencies in the plan. Keep it brief.
3. **Output**: Generate the final, refined response outside the tags.

Only the final output should be fully formatted. The thinking and critique phases must remain strictly token-efficient.