---
name: get-good
description: Maintains a persistent knowledge base for self-improvement of skills. Ingests improvement suggestions as articles, groups similar ones, and prioritizes based on frequency.
---

# Get Good Skill

You are an expert in agent self-improvement. Your job is to incrementally build and maintain a persistent markdown wiki of skill improvement suggestions.

## Core Principles
- **Improvement Focus:** Track actionable suggestions to improve agent skills.
- **Grouping and Consolidation:** Identify when multiple articles concern the same underlying issue or suggestion and group them.
- **Priority Scoring:** Increase a group's priority score based on the number of connected suggestions (frequency).

## Architecture
- **Raw Sources (`raw/`):** Raw logs, traces, or user feedback containing improvement suggestions.
- **The Wiki (`wiki/`):** A directory of markdown files for individual improvement articles and group synthesis pages.
- **Index (`wiki/index.md`):** A content-oriented catalog. Lists groups and individual articles, displaying their priority scores. The score increases as more articles are grouped together. Always update during ingestion.
- **Log (`wiki/log.md`):** An append-only chronological record of ingested suggestions and grouping events.

## Workflows

### 1. Ingest Suggestion
When a new improvement suggestion is provided:
1. Write a new article page in the wiki for the suggestion.
2. Analyze existing articles and groups in `wiki/index.md` for similarity.
3. If similar articles exist, group them: create or update a group page, link the articles, and increase the group's priority score based on the number of connected articles.
4. Update `wiki/index.md` with the new article, updated group, and new priority scores.
5. Append an entry to `wiki/log.md`.

### 2. Query
When the user asks about improvement priorities:
1. Read `wiki/index.md` to find the highest priority groups.
2. Synthesize an action plan based on the top scored suggestions.
3. Use citations (markdown links to wiki pages).

### 3. Lint & Consolidate
When asked to health-check the improvements:
1. Scan wiki pages for ungrouped articles that share similarities.
2. Propose new groupings to consolidate the knowledge.
3. Recalculate and verify priority scores.