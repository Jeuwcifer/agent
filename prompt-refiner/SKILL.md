---
name: prompt-refiner
description: Suggests refined prompts based on Gemini core prompting principles (precision, consistent delimiters, constraint prioritization, anchor contexts).
---

# Prompt Refiner Skill

Refines user prompts according to Google's official Gemini Prompting Strategies. 

## Protocol
When a user provides a raw prompt or asks for prompt improvement:

1. **Analyze:** Check the input against these principles:
   - **Precision:** Is the goal clear, concise, and free of fluff?
   - **Structure:** Are delimiters (`<context>`, `<task>`) or Markdown headers used consistently?
   - **Parameters:** Are terms ambiguous? Is verbosity explicitly controlled?
   - **Priority:** Are critical constraints (persona, output format) at the very top (or in system instructions)?
   - **Long Contexts:** Is bulk data placed first, with specific instructions/questions placed at the *end*?
   - **Anchoring:** Is there a transition phrase (e.g., "Based on the information above...") after data blocks?

2. **Refine:** Rewrite the prompt to satisfy all missing principles. 
   - Apply XML tags for distinct sections.
   - Front-load constraints.
   - Ensure the final directive is explicit and at the bottom.

3. **Present:** Output the final optimized prompt in a copy-pasteable markdown code block, followed by a brief, bulleted explanation of what was changed and why.
