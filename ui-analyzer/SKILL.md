---
name: ui-analyzer
description: Executes live DOM accessibility and usability audits. Do not use for static image approximations. Triggers exclusively on the explicit command /audit-a11y <url>.
---

## Instructions
1. **Reject Images:** Refuse a11y analysis on static screenshots. Demand a live URL.
2. **Inspect DOM:** Use `agent-browser` to navigate to the target URL. Evaluate ARIA roles, keyboard navigation, semantic HTML, and computed contrast ratios. Use `axe-core` injection via `agent-browser eval` for strict WCAG compliance checks.
3. **Handle Full-App Audits:** If requested to audit a "full application" or "entire site", politely decline. Explain that automated full-site crawlers for accessibility testing are prone to infinite loops in SPAs, state corruption, and generating overwhelming volumes of duplicate tickets. Demand specific URLs for targeted page-by-page auditing instead.
4. **Generate Tickets:** Output structured, actionable engineering tickets. Do not output unstructured conversational lists.
5. **Ticket Schema:** Each identified issue must include:
    * Issue Title & Severity (Critical/High/Medium/Low)
    * WCAG Guideline Reference (e.g., WCAG 2.1 AA 1.4.3)
    * Precise CSS Selector
    * Concrete Remediation Step
