---
name: skill-retrospective
description: Analyzes conversation sessions and execution traces to identify information gaps, tool friction, and trial-and-error loops. Formulates realistic, high-leverage improvements to add missing knowledge into skills, workflows, or wikis for faster future runs. Uses the get-good skill to log these suggestions.
---

# Skill Retrospective & Continuous Improvement

A meta-skill that audits chat sessions and tool execution traces to diagnose where missing context, trial-and-error loops, or tool missteps delayed the final outcome. It translates session friction into actionable, concrete additions for skills or knowledge bases, and uses the get-good skill to persist them.

---

## The Retrospective Mantra

> **"Go through the chat session and look for instances of where:**  
> **If certain information would have been available earlier, then it would have been possible to reach the end result that much sooner. And missteps avoided.**  
> **What are some realistic ways we can add this information so it's available for the next run?**  
>  
> **Generate unlimited suggestions and save them using the get-good skill."**

---

## When to Trigger This Skill

Trigger `skill-retrospective` when:
- The user requests a session audit: *"run a retrospective"*, *"analyze this session for skill improvements"*, *"what could we improve from this run"*, *"postmortem"*, or invoking `/skill:skill-retrospective`.
- A complex workflow concludes that involved multiple tool retries, selector hunting, file edit collisions, or user course-corrections.
- Developing, testing, or dogfooding new agent skills to compound learnings into persistent instructions.

---

## The 5-Phase Retrospective Protocol

```
┌────────────────────────────────────────────────────────┐
│ 1. Session Trace & Friction Audit                      │
│    Scan tool calls, errors, retries, exploratory burns │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Counterfactual Information Analysis                 │
│    What exact fact, if known at T=0, avoids this loop? │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Realistic Injection Vector Mapping                  │
│    SKILL.md rules, Wiki UI-maps, Pre-flight hooks      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Standardized Suggestion Generation                  │
│    Format proposals with clear impact blocks           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 5. Knowledge Base Ingestion                            │
│    Use get-good skill to log suggestions as articles   │
└────────────────────────────────────────────────────────┘
```

---

### Phase 1: Session Trace & Friction Audit

Review the current conversation context or execute the companion session analyzer:
```bash
python3 /home/user/.agents/skills/skill-retrospective/scripts/analyze_session.py
```

Audit the trace for four distinct categories of friction:
1. **Tool Failures & Exceptions**: Non-zero exits, element not found, pattern search failures, API error codes.
2. **Exploratory Burn**: Repeated commands searching for selectors, directory trees, API endpoints, or schemas that could have been documented upfront.
3. **Ambiguity Traps & Multi-Node Clashes**: Selectors or patterns matching multiple DOM elements (e.g., hidden duplicate buttons), causing failed interactions.
4. **User Course-Corrections**: Moments where the user had to interject to clarify credentials, UI locations, parameters, or intent.

---

### Phase 2: Counterfactual Information Analysis

For each friction event identified in Phase 1, ask the counterfactual question:
- *"If piece of information `X` had been available at Turn 0, would this misstep have been eliminated?"*
- *"How many turns, tool calls, and minutes would have been saved?"*
- *"Was the misstep caused by missing domain knowledge, an undocumented edge case, or lack of architectural guardrails?"*

---

### Phase 3: Realistic Injection Vectors

Identify the most realistic, sustainable location to persist the missing knowledge so that future runs succeed immediately:

| Vector | Where to Add It | Best For |
|:---|:---|:---|
| **Skill Instructions** | Target `SKILL.md` (`## Key Locators`, `## Disambiguation Rules`, `## Architectural Principles`) | High-priority behavioral constraints, exact selectors, element disambiguation rules, mandatory sequencing. |
| **Domain Knowledge Base** | `wiki/<domain>-ui-map.md` or `docs/` | Comprehensive component inventories, API payload schemas, route paths, product catalogs. |
| **Pre-Flight Hook / Guardrail** | Helper scripts (`ensure_effects`, `dismiss_popups`, settle intervals) | Asynchronous overlays, cookie banners, connection retries, environment preconditions. |
| **Skill Metadata & Triggers** | `SKILL.md` YAML frontmatter (`triggers`, `description`) | Ensuring the agent activates the skill with correct default parameters and scope. |

---

### Phase 4: Standardized Suggestion Generation

Formulate each proposal clearly, detailing the exact improvement and its impact. Generate as many suggestions as necessary to address all identified friction points (do not limit the count).

```markdown
### [SUGG-01] Title of Improvement

- **Observed Friction / Misstep**:
  [Describe the failure, retry loop, or wasted exploratory steps in this session.]

- **Root Information Gap**:
  [What specific knowledge was missing early on that caused this delay?]

- **Realistic Solution Vector**:
  [Skill Instructions / Knowledge Wiki / Pre-flight Script / Parameter Constraint]

- **Proposed Addition**:
  ```markdown
  [Exact text, selector rule, or code snippet to add]
  ```

- **Expected Savings**:
  [e.g., Eliminates 4 tool calls; cuts ~2 minutes of trial-and-error; prevents UI block.]
```

---

### Phase 5: Knowledge Base Ingestion

Do not automatically implement the suggestions by editing skill files directly, and do not ask the user for a grade. Instead, use the `get-good` skill to record the suggestions:

1. For each suggestion formulated in Phase 4, invoke the `get-good` skill.
2. Provide the suggestion details to `get-good` so it can ingest it as a distinct improvement article.
3. The `get-good` skill will handle creating the article, grouping similar suggestions, and increasing priority scores.
4. Conclude by informing the user that the suggestions have been successfully logged in the improvement wiki for future prioritization.
