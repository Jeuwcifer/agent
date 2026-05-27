---
name: tdd-loop
description: Enforces strict Test-Driven Development (TDD) via test-time compute emulation. Requires writing and executing tests before implementing solutions.
---

# TDD Loop Validation Skill

Enforce a strict Test-Driven Development (TDD) execution loop for all code generation and bug fixes. Do not write implementation code until a failing test validates the issue.

## Protocol

1. **Write Test First:** Given a user request or bug report, immediately write an automated test script (`test_*.py`, `*.spec.ts`, etc.) that replicates the exact conditions.
2. **Execute Test:** Run the test using `bash`. It must fail, proving the bug or missing feature exists.
3. **Iterate Implementation:** Write the minimum code required to pass the test.
4. **Execute Test:** Run the test again.
5. **Verify:** If the test fails, use the output to revise the implementation. Repeat steps 3-5 until the test passes.
6. **Refactor:** Clean up the implementation while ensuring tests remain green.

## Constraints
- Never provide a solution without a paired, executable test.
- Do not skip the initial failure execution. Execution feedback is mandatory context.