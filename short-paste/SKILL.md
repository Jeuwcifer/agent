---
name: short-paste
description: Keeps commands and requested outputs to one line of 54 characters or fewer so they survive copy-paste into a terminal with broken bracketed paste (^[[200~ markers, merged lines) or a narrow TTY. Always active.
---

# short-paste

Every command given to the user must fit one line, 54 characters or fewer, including `sudo`. Reason: the user's terminal mangles multi-line pastes and long lines.

## Rules

1. One command per line. Never bundle commands on one line.
2. 54 chars max per command line. Long command: split into separate short steps, or write a script file with the write tool and give one short run command.
3. No multi-line paste blocks for the user. No heredocs, no `&&` chains, no `for` loops to paste.
4. When requesting command output, keep it short: append `| head -N` or `| grep PATTERN`, or redirect to a file and grep the file.
5. Paths, command names, numbers, error strings stay verbatim. Never truncate one to fit 54; split or rename output file instead.

## Boundaries

- Never shorten a payload by dropping characters: shorten by filtering or splitting.
- Does not apply to file contents written via tools, only to text the user must copy or retype.
