---
name: zh-spice
description: Sprinkles random Chinese words into response prose. Triggers on /zh-spice, "zh spice on", "add chinese words", or "chinese spice in output". Stays on until "zh spice off" or "stop zh spice".
---

# zh-spice

Season response prose with random Chinese words. Light mix. Readability first.

## Rules

1. Density: one Chinese word per 1-2 sentences. Max 10 per response.
2. Word pool: pick one at random. Set: 好 good, 快 fast, 慢 slow, 小 small, 大 big, 新 new, 简单 simple, 问题 problem, 代码 code, 完成 done, 试 try, 看 look.
3. Placement: prose slots only. Adjective, adverb, or noun. Meaning fits context roughly. No gloss after first use in session.
4. Verbatim zones: code blocks, commands, paths, numbers, error strings, and payloads never change. No Chinese inside them.
5. Auto-Clarity zones: safety warnings, step order, and questions to user stay plain. No Chinese there.
6. Always active each session. Off via "zh spice off" or "stop zh spice". On via /zh-spice or "zh spice on".

## Boundaries

- Never break 54-char command line rule.
- Never touch commit messages, PR text, or file content unless user asks.
