---
name: skill-retrospective
description: Analyzes conversation sessions and execution traces to identify information gaps, tool friction, and trial-and-error loops. Formulates realistic, high-leverage improvements to add missing knowledge into skills, workflows, or wikis for faster future runs. Prompts the user to grade each suggestion on a 1-10 scale.
---

# Skill Retrospective & Continuous Improvement

A meta-skill that audits chat sessions and tool execution traces to diagnose where missing context, trial-and-error loops, or tool missteps delayed the final outcome. It translates session friction into actionable, concrete additions for skills or knowledge bases, and prompts the user to grade every recommendation on a 1 to 10 scale.

---

## The Retrospective Mantra

> **"Go through the chat session and look for instances of where:**  
> **If certain information would have been available earlier, then it would have been possible to reach the end result that much sooner. And missteps avoided.**  
> **What are some realistic ways we can add this information so it's available for the next run?**  
>  
> **Each suggestion should be graded on a scale of 1 to 10 by the user."**

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
│ 4. Structured Suggestion Cards with User Grading (1-10)│
│    Format proposals with clear impact & scoring blocks │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 5. Closed-Loop Implementation                          │
│    User grades proposals; agent applies high-ranked    │
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

### Phase 4: Standardized Suggestion Cards for User Grading

Present each proposal using the standardized suggestion card. Every card **must** feature a user grading block:

```markdown
### [SUGG-01] Title of Improvement

- **Observed Friction / Misstep**:
  [Describe the failure, retry loop, or wasted exploratory steps in this session.]

- **Root Information Gap**:
  [What specific knowledge was missing early on that caused this delay?]

- **Realistic Solution Vector**:
  [Skill Instructions / Knowledge Wiki / Pre-flight Script / Parameter Constraint]

- **Target Location**:
  `[path/to/target/file.md]` (Section: `[Section Header]`)

- **Proposed Addition**:
  ```markdown
  [Exact text, selector rule, or code snippet to add]
  ```

- **Expected Savings**:
  [e.g., Eliminates 4 tool calls; cuts ~2 minutes of trial-and-error; prevents UI block.]

- **User Grade**: `[ ___ / 10 ]`
```

#### User Grading Rubric (1 to 10 Scale):
- **1 – 3 (Low):** Trivial, fragile, or too specific to a one-off scenario. Not worth codifying.
- **4 – 6 (Moderate):** Helpful optimization. Reduces token churn or slightly speeds up execution.
- **7 – 8 (High):** Substantial time and failure reduction across multiple workflows. Clean, realistic addition.
- **9 – 10 (Critical):** High-leverage architectural fix. Prevents recurring hard failures or eliminates major diagnostic loops.

---

### Phase 5: Closed-Loop Application

Conclude the retrospective report by asking the user to provide their ratings:

```markdown
## Interactive Scoring Prompt

Please rate each proposal above on a scale of **1 to 10** (e.g., `SUGG-01: 9/10, SUGG-02: 6/10`).
For any suggestions you score **7 or higher** (or explicitly approve), I will immediately commit the changes to the corresponding skill files and knowledge bases.
```

When the user responds with their scores:
1. Filter suggestions scoring **7 or higher** (or user-approved items).
2. Use the `edit` or `write` tools to update the target `SKILL.md`, `wiki/`, or script files.
3. Show the committed diff and confirm that the skill is upgraded for subsequent runs.
