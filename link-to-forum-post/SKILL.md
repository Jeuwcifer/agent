---
name: link-to-forum-post
description: >
  Converts web links into high-density, semantic Markdown articles suitable for forum discussions. Triggers when a user provides a URL and requests a forum post, article, summary, or discussion thread based on the link.
user-invocable: true
---

# Link to Forum Post

Converts web links into high-density, semantic Markdown articles suitable for forum discussions. 

## Triggers
Activate when user provides a URL and requests a forum post, article, summary, or discussion thread based on the link.

## Execution
1. Fetch: Extract pure text from the provided URL. Use `agent-browser` if dynamic rendering is required, otherwise use standard HTTP retrieval tools to pull the raw DOM.
2. Strip: Remove all navigation, ads, and boilerplate. Isolate the core content.
3. Synthesize: Do not just regurgitate. Add synthesis and critique to provide actual discussion value.
4. Format: Output strict, semantic Markdown. Use clear headers (`##`), bullet points, and exact quotes where relevant. 
5. Tone: Write conversationally, as a forum member sharing research. End with provocative questions to spark discussion. Do not sound like an academic paper or corporate summary.
