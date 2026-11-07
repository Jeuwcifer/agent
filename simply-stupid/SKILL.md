---
name: simply-stupid
description: Enforces Occam's razor, KISS, and YAGNI principles across engineering tasks. Favors minimal changes, standard libraries, flat control flow, and zero speculative abstraction while preserving correctness
---

# simply-stupid

Apply Occam's razor and KISS ("Keep It Simple, Stupid") to all engineering, code, and architecture decisions. Do not multiply entities beyond necessity.

## Rules

1. **Smallest Viable Change**: Choose the smallest change and fewest moving parts that fully solve the problem. Extend or edit existing code in place before introducing new files, classes, or services.
2. **Standard Library & Existing Utilities First**: Prefer language built-ins, standard library modules, and existing project utilities over adding new third-party dependencies.
3. **Strict YAGNI**: Ban speculative abstractions, premature optimization, and unrequested configurability. Do not create interfaces for single implementations, plugin systems for fixed workflows, or config flags nobody asked for.
4. **Flat, Direct Control Flow**: Prefer flat functions, explicit state, and early returns over deep inheritance hierarchies, dynamic dispatch chains, or pass-through wrapper layers.

## Safety Boundaries

Simplicity never overrides:
- **Correctness**: Solutions must handle required behavior and real edge cases accurately.
- **Input Validation**: Always validate and sanitize untrusted inputs at system boundaries.
- **Error Handling**: Always check, surface, and handle errors explicitly; never silence failures to shorten code.
- **Explicit User Constraints**: Follow user-specified architectures, libraries, and requirements even when a simpler alternative exists.
