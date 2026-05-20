---
name: roxtec-crawler
description: Crawls Roxtec Transit Build web app to map UI elements, buttons, and workflows. Saves mapping as knowledge for roxtec-doc-gen. Triggers on "crawl roxtec", "map roxtec workflows", "explore roxtec ui".
---

# Roxtec UI Crawler

## Goal
Systematically explore the Roxtec Transit Build app, extract UI element locators (`snapshot -i`), and document workflows. Store the results via `knowledge-manager` so `roxtec-doc-gen` can reliably generate automation scripts without guessing locators.

## Execution Constraints
- **Read-Only**: Do not submit forms or delete assets during the crawl.
- **Depth Limit**: Limit BFS crawl to depth 2 (Main Nav -> Sub View -> Modal) to prevent token exhaustion and infinite loops.
- **Modal Purge**: Force close modals after snapshotting to avoid blocking navigation.

## Execution Steps
1. **Initialize**: Use `agent-browser --session roxtec set viewport 1920 1080 1`. Navigate to `https://transitbuild.roxtec.com`. Log in using standard test credentials if prompted.
2. **Crawl Strategy**: 
   - Capture current view: `agent-browser --session roxtec snapshot -i`.
   - Identify major navigation links (e.g., Dashboard, Transits, Asset documents, Floor plans).
   - Iterate through each major view.
   - In each view, identify primary action buttons (e.g., "Add transit", "Add document", "Manage").
   - Click to open dialogs/modals, capture their snapshot, then force close them (`agent-browser eval` to delete modal DOM nodes or click close).
3. **Data Formatting**:
   - Create a Markdown payload organizing the UI by view (e.g., `## Transits View`, `### Add Transit Modal`).
   - List exact text, roles, and typical state of key elements. 
   - Document observed data model hierarchies.
4. **Knowledge Storage**:
   - Save the generated Markdown to a local file, e.g., `/tmp/roxtec_ui_map.md`.
   - Invoke the `knowledge-manager` skill to ingest this file into the agent's persistent wiki with tags `#roxtec #ui-map #workflows`.
