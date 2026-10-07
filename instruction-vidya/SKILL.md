---
name: instruction-vidya
description: Creates professional instructional videos and documentation for web applications. Connects, logs in, crawls the app to learn its structure and workflows, plans an instructional sequence from user prompts, and records 1080p video with smooth animated cursor movements and click ripples. Triggers on requests like "create an instructional video", "generate video guide", "make a video tutorial", "record a video guide for my web app", "crawl my app and make a video", "how-to video", or "instruction-vidya".
---

# instruction-vidya

An end-to-end skill for automatically generating professional 1080p instructional video walkthroughs and companion Markdown guides for any web application. The skill connects and logs in to the application, crawls it to learn its UI structure and workflows, plans an instructional storyboard based on the user's prompt, records the browser screen with smooth animated cursor movements and click ripples, and produces an optimized instructional video (MP4/WebM) along with companion documentation.

---

## Architectural Principles & Core Laws

1. **The Clean UI & Silent Video Law**:
   Instructional videos must present a clean, unoccluded application UI without on-screen text bars, banner overlays, caption bars, or floating explanation windows. Never inject text bars or banners into the video canvas. All operational context, high-level feature explanations, and general information are delivered strictly through the companion Markdown manual (`guide.md`). Post-production strictly enforces silent audio (`-an`). Granular step-by-step instructions or click-by-click scripts are unnecessary and omitted from the markdown documentation.
2. **The Deliberate Visual Pacing Law**:
   Visual state transitions (navigating, clicking, filling forms, inspecting dialogs) must be executed with intentional pacing and clear dwell times (2-3 seconds per action). Rushing actions confuses viewers. Each step must allow viewers ample time to observe the gliding SVG cursor, see the animated click ripple, and verify the resulting UI change.
3. **Deterministic DOM Polling Over Sleeps**:
   Never use hardcoded sleeps like `sleep 5` to wait for pages or dialogs. Use `wait_for` and `wait_for_gone` to poll DOM snapshots for target elements. This ensures reliable execution across varied server latencies.
4. **High-Fidelity Visual Cues (Cursor & Ripples Only)**:
   Automated agent interactions lack visible user input cues. This skill injects `smart_effects.js` into the DOM to render a smooth SVG cursor pointer and glowing click ripple rings. Never inject on-screen text bars, floating windows, or caption overlays.
5. **Non-Destructive Exploration**:
   During the initial crawl phase, exploration is read-only. Modals and drawers are inspected for inputs and form structures, then dismissed with Escape or Cancel without submitting mutations.
5. **Asynchronous Dialog Interception**:
   Web applications frequently render asynchronous onboarding, cookie, or startup dialogs 1-3 seconds after navigation. Automation scripts must run an active background watcher or pre-flight dismissal check within `smart_click` / `ensure_effects` to prevent clicks from being intercepted by transparent modal backdrops.
6. **Strict Selector Disambiguation**:
   Never rely on greedy substring searches for common verbs (e.g. `Add` matching `Add and set status` or `Add transit`). Use exact regex (`grep -E 'button "Add"'`) or explicit `data-test` attributes to prevent false click targets.
7. **DOM vs CLI Selector Separation**:
   Never pass Playwright pseudo-selectors (e.g. `:has-text()`, `:visible`, `:text()`) into `document.querySelector()` inside `eval`. Use valid W3C CSS selectors or filter elements via JavaScript (`Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('...'))`).

---

## Tooling & Environment Prerequisites

All necessary tools are pre-configured:
- `agent-browser`: Web automation, snapshot extraction, and screen recording CLI.
- `ffmpeg` & `ffprobe`: Video recording, duration calculation, and post-production transcoding.
- `python3`: Pipeline automation and helper scripts.

### Browser Evaluation Pattern (Avoid Inline Shell Escapes)
Never pass multi-line JavaScript containing internal quotes as inline CLI arguments to `agent-browser eval`. Always pipe via stdin to eliminate shell syntax escaping errors:
```bash
cat << 'JS' | agent-browser --session "$SESSION" eval --stdin
(() => {
    // DOM operations
})();
JS
```

Helper utilities located in the skill directory (`scripts/`):
- `crawler.py`: Autonomous web application crawler and knowledge mapper.
- `merge_video.py`: FFmpeg video post-production and transcoding engine.
- `smart_effects.js`: DOM-injected smooth SVG cursor and animated click ripple.
- `record_template.sh`: Ready-to-use recording script template.

---

## Step-by-Step Workflow

```
┌────────────────────────┐
│ 1. Connect & Auth      │  -> Launch session, set 1920x1080, log in with credentials
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│ 2. App Crawl & Mapping │  -> Discover routes, buttons, forms, modals; save app_knowledge.md
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│ 3. Storyboard Planning │  -> Parse user prompt into Step 0..N action sequence
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│ 4. Screen Recording    │  -> Record 1080p, animate cursor/ripples with deliberate pacing
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│ 5. FFmpeg Post-Prod    │  -> Transcode raw recording into optimized final MP4/WebM
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│ 6. Companion Guide     │  -> Output Markdown manual with step screenshots and timestamps
└────────────────────────┘
```

---

### Phase 1: Connection & Authentication

1. **Initialize Browser**:
   Set standard Full HD 1080p viewport (16:9 aspect ratio):
   ```bash
   agent-browser --session vidya_<app> set viewport 1920 1080 1
   agent-browser --session vidya_<app> open <app_url>
   ```

2. **Handle Login**:
   If the target application requires authentication:
   - Check URL or interactive snapshot (`agent-browser --session vidya_<app> snapshot -i`).
   - Identify email/username input, password input, and submit button refs.
   - Fill credentials and submit:
     ```bash
     agent-browser --session vidya_<app> fill @<email_ref> "user@example.com"
     agent-browser --session vidya_<app> fill @<password_ref> "password123"
     agent-browser --session vidya_<app> click @<submit_ref>
     ```
   - Wait for navigation: `agent-browser --session vidya_<app> wait --load networkidle`

---

### Phase 2: Autonomous App Crawling & Exploration

To understand the app's features and locate elements before producing the video, execute the crawler:

```bash
python3 /home/user/.agents/skills/instruction-vidya/scripts/crawler.py \
    --url "https://app.example.com" \
    --email "user@example.com" \
    --password "secret" \
    --depth 2 \
    --max-views 10 \
    --outdir "./app_knowledge"
```

The crawler performs:
- **Navigation Discovery**: Traverses links, tabs, and menus within the same domain.
- **Action Extraction**: Catalogs all buttons, inputs, dropdowns, and checkboxes per view.
- **Safe Modal Probing**: Temporarily clicks creation/filter buttons, snapshots dialog inputs, and closes them via Escape/Cancel.
- **Knowledge Synthesis**: Generates `app_knowledge.json` and human-readable `app_knowledge.md`.

*Tip*: If `knowledge-manager` skill is present, you can index `app_knowledge.md` into the wiki under `#app-knowledge #ui-map`.

---

### Phase 3: Storyboard & Action Planning

Given the user prompt (e.g. *"Show how to invite a collaborator to a team project"*), craft a structured storyboard and action plan:

1. **Step 0 (Intro)**: Overview of what the tutorial demonstrates.
2. **Step 1 (Navigation)**: Navigating to the relevant screen or tab.
3. **Step 2 (Action)**: Clicking the trigger button (e.g. "+ Invite Member").
4. **Step 3 (Data Entry)**: Typing inputs, selecting dropdown options.
5. **Step 4 (Submission)**: Clicking confirmation or submit button.
6. **Step 5 (Outro)**: Highlighting the final outcome and concluding.

Create a `storyboard.json` file:
```json
[
  {
    "step": 0,
    "title": "Introduction",
    "description": "Welcome to this guide. Today we will show you how to invite a new team member to your project."
  },
  {
    "step": 1,
    "title": "Navigate to Settings",
    "description": "From your dashboard, click on the Settings tab in the left navigation sidebar."
  },
  {
    "step": 2,
    "title": "Open Invite Dialog",
    "description": "Click the Invite Member button in the upper right corner."
  },
  {
    "step": 3,
    "title": "Enter Collaborator Details",
    "description": "Enter the colleague's email address and assign their project role."
  },
  {
    "step": 4,
    "title": "Confirm and Submit",
    "description": "Click Send Invitation to complete the process."
  },
  {
    "step": 5,
    "title": "Wrap-up",
    "description": "The team member has been successfully invited."
  }
]
```

---

### Phase 4: High-Fidelity Screen Recording

Create and run a workflow recording script (`record_guide.sh`) using deliberate visual pacing:

```bash
#!/usr/bin/env bash
set -e

SESSION="vidya_guide"
RAW_VIDEO="raw_walkthrough.webm"
TIMESTAMPS="timestamps.txt"
EFFECTS_JS="/home/user/.agents/skills/instruction-vidya/scripts/smart_effects.js"

rm -f "$TIMESTAMPS" "$RAW_VIDEO"

function sync_step {
    local step="$1"
    local ts=$SECONDS
    echo "step${step}=${ts}" >> "$TIMESTAMPS"
    echo "$ts"
}

function pace_step {
    local duration="${1:-1.5}"
    sleep "$duration"
}

function ensure_effects {
    agent-browser --session "$SESSION" eval --stdin < "$EFFECTS_JS" >/dev/null 2>&1 || true
}

function smart_click {
    local target="$1"
    if [[ "$target" =~ ^e[0-9]+$ ]]; then target="@$target"; fi
    ensure_effects
    local box=$(agent-browser --session "$SESSION" get box "$target" 2>/dev/null || true)
    local x=$(echo "$box" | grep "x:" | awk '{print $2}')
    local y=$(echo "$box" | grep "y:" | awk '{print $2}')
    local w=$(echo "$box" | grep "width:" | awk '{print $2}')
    local h=$(echo "$box" | grep "height:" | awk '{print $2}')
    local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    
    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.moveTo($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.5
    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.clickRipple($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.2
    agent-browser --session "$SESSION" click "$target"
    sleep 0.8
}

function smart_type {
    local target="$1"
    local text="$2"
    if [[ "$target" =~ ^e[0-9]+$ ]]; then target="@$target"; fi
    ensure_effects
    local box=$(agent-browser --session "$SESSION" get box "$target" 2>/dev/null || true)
    local x=$(echo "$box" | grep "x:" | awk '{print $2}')
    local y=$(echo "$box" | grep "y:" | awk '{print $2}')
    local w=$(echo "$box" | grep "width:" | awk '{print $2}')
    local h=$(echo "$box" | grep "height:" | awk '{print $2}')
    local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    
    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.moveTo($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.4
    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.clickRipple($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.2
    agent-browser --session "$SESSION" fill "$target" "$text"
    sleep 0.8
}

# 1. Setup Browser
agent-browser --session "$SESSION" set viewport 1920 1080 1
agent-browser --session "$SESSION" open "<app_starting_url>"
ensure_effects

# 2. Start Recording
echo "[Vidya] Starting screen recording..."
agent-browser --session "$SESSION" record start "$RAW_VIDEO"
SECONDS=0

# Step 0: Intro
TS=$(sync_step 0)
pace_step 2

# Step 1: Navigate
TS=$(sync_step 1)
agent-browser --session "$SESSION" snapshot -i > /tmp/snap1
REF_NAV=$(grep -i "Settings" /tmp/snap1 | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1)
smart_click "$REF_NAV"
agent-browser --session "$SESSION" screenshot step1.png
pace_step 1.5

# Step 2: Trigger Action
TS=$(sync_step 2)
agent-browser --session "$SESSION" snapshot -i > /tmp/snap2
REF_BTN=$(grep -i "Invite Member" /tmp/snap2 | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1)
smart_click "$REF_BTN"
agent-browser --session "$SESSION" screenshot step2.png
pace_step 1.5

# Step 3: Input Form Fields
TS=$(sync_step 3)
agent-browser --session "$SESSION" snapshot -i > /tmp/snap3
REF_EMAIL=$(grep -i "Email" /tmp/snap3 | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1)
smart_type "$REF_EMAIL" "colleague@example.com"
agent-browser --session "$SESSION" screenshot step3.png
pace_step 1.5

# Step 4: Submit
TS=$(sync_step 4)
agent-browser --session "$SESSION" snapshot -i > /tmp/snap4
REF_SUBMIT=$(grep -i "Send" /tmp/snap4 | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1)
smart_click "$REF_SUBMIT"
agent-browser --session "$SESSION" screenshot step4.png
pace_step 2

# Step 5: Outro
TS=$(sync_step 5)
pace_step 2

# 3. Stop Recording
echo "[Vidya] Finalizing recording..."
sleep 1
agent-browser --session "$SESSION" record stop
agent-browser --session "$SESSION" close
```

Execute the recording:
```bash
bash record_guide.sh
```

---

### Phase 5: Post-Production & Video Optimization

Transcode and optimize the raw screen recording into the final distribution video:

```bash
python3 /home/user/.agents/skills/instruction-vidya/scripts/merge_video.py \
    --video "raw_walkthrough.webm" \
    --timestamps "timestamps.txt" \
    --output "final_instructional_guide.mp4"
```

Features of the post-production engine:
- Transcodes raw WebM recordings into high-compatibility MP4 (`libx264` + `yuv420p` + `+faststart`) or WebM (`libvpx-vp9`).
- Removes unneeded audio streams (`-an`) for clean, silent instructional walkthroughs.
- Optimizes compression CRF and framerate settings.
- Preserves timestamps from `timestamps.txt` for companion documentation timecodes.

---

### Phase 6: Companion Documentation Manual

Generate a companion Markdown guide (`guide_<workflow>.md` or `final_<workflow>_guide.md`) containing general information, operational architecture, workflow video milestones, methods comparison, and domain terminology. Granular step-by-step instructions, click-by-click walkthroughs, or detailed action/result narrator scripts are unnecessary and strictly omitted; documentation should focus exclusively on high-level general information. All generated guides must adhere strictly to the following enterprise documentation structure:

#### Mandatory Document Structure & Sections:

1. **Header & Video Metadata Specification**:
   - Primary Title: `# <Application Name> — <Workflow / Feature Overview Title>`
   - Metadata Block:
     ```markdown
     **Video Walkthrough**: `<video_filename>.mp4`  
     **Video Specifications**: 1080p Full HD (1920×1080) | Strictly Silent (`-an`) | Clean UI (No on-screen text overlays)
     ```
2. **Executive Summary & Field Impact**:
   - Enterprise Operational Context: High-level purpose, operational value, and data model hierarchy formula:
     $$\text{Level 1} \longrightarrow \text{Level 2} \longrightarrow \text{Level 3} \dots$$
   - Subheading: `### Operational Benefits for Field Teams` (or relevant operational personas such as Quality Inspectors, Project Managers, Installation Technicians).
   - Concrete bullet points with bold thematic titles (e.g. Rapid Identification, Accurate Spatial Routing, Audit-Ready Traceability) describing exact field benefits on massive industrial sites.
3. **Core Capabilities Overview**:
   - High-level functional breakdown of key platform features, operational modes, schematic links, and data associations without granular step-by-step clicks or video milestones.
4. **Comparison Matrix (Methods Evaluation)**:
   - A structured side-by-side evaluation table comparing primary vs alternative interaction patterns (e.g., Interactive Map Drag vs Tabular List View, Direct Action vs Wizard):
     | Capability | Method 1: <Name> (Recommended) | Method 2: <Name> |
     Rows include: **Primary Entry**, **Coordinate Setting / Input Mode**, **Best Scenario**, **Target Role**.
5. **Terminology Compliance Reference**:
   - Canonical enterprise domain dictionary standardizing authoritative vocabulary and explicitly prohibiting informal, colloquial, or generic phrasing:
     | Term | Context & Definition | Prohibited Synonyms |

#### Canonical Guide Template Example:

```markdown
# Roxtec Transit Build™ — Geolocation Feature Overview

**Video Walkthrough**: `final_geolocation_guide.mp4`  
**Video Specifications**: 1080p Full HD (1920×1080) | Strictly Silent (`-an`) | Clean UI (No on-screen text overlays)

---

## Executive Summary & Field Impact

In **Roxtec Transit Build™**, **Geolocations** link geographical spatial coordinates directly to structural floor plans and transit frames. By anchoring **Floor Plans** and **Cable Penetrations** to physical GPS coordinates, project stakeholders establish an unambiguous operational hierarchy:

$$\text{Customer / Account} \longrightarrow \text{Asset} \longrightarrow \text{Geolocation} \longrightarrow \text{Floor Plans} \longrightarrow \text{Transit Seals & Cable Penetrations}$$

### Operational Benefits for Field Teams
For **Quality Inspectors**, **Project Managers**, and **Installation Technicians**, spatial pinning directly eliminates guesswork on massive industrial job sites (shipyards, offshore substations, energy storage facilities, and processing plants):
- **Rapid Transit Identification**: Field inspectors locate penetration frames instantly on interactive maps without cross-referencing paper blueprints or outdated spreadsheets.
- **Accurate Spatial Routing**: Technicians navigate directly to the correct deck, module, or substation quadrant before starting cable pulling and packing seal installations.
- **Audit-Ready Traceability**: Inspectors record transit seal compliance statuses directly against geographically verified locations, ensuring complete regulatory and quality traceability.

---

## Core Capabilities Overview

### 1. Interactive Cartographic Pinning & Dynamic GPS Mapping
- **Fluid Map Dragging**: Active site markers can be dragged directly across the Leaflet cartographic map.
- **Real-Time Coordinate Synchronization**: Latitude and Longitude values calculate and synchronize dynamically as the marker is moved, eliminating error-prone manual coordinate data entry.

### 2. Operational Metadata Management
- **Identifiable Tagging**: Each geolocation receives a unique naming identifier and operational scope description.
- **Persistent Marker Data**: Saved geolocations populate the cartographic map with persistent interactive markers and accessible inspection details.

### 3. Structural Floor Plan & Penetration Linkage
- **Schematic Association**: Structural deck layouts and 2D floor plans are linked directly to corresponding geolocations.
- **Bidirectional Filtering**: The Location Details drawer provides quick filtering between all available floor plans and those currently associated with the selected location.

### 4. Dual Operational Views (Map View vs. List View)
- **Map View (`asset-geo-locations`)**: Best suited for visual spatial validation, regional platform layouts, and interactive geographic exploration.
- **List View (`asset-geo-locations-detail`)**: Best suited for administrative audits, alphanumeric search, bulk reviews, and fast row-level editing across large transit datasets.

---

## Comparison: Editing Geolocations in Roxtec Transit Build™

| Capability | Method 1: Interactive Map Drag (Recommended) | Method 2: Tabular List View |
|---|---|---|
| **Primary Entry** | Pin details drawer &rarr; `Manage` &rarr; `Edit Location` &rarr; **Free-hand Drag on Map** | View dropdown &rarr; Row edit icon (`[data-test="geolocation-edit-action"]`) |
| **Coordinate Setting** | **Direct visual pin dragging** across cartography; lat/long dynamically update | Manual coordinate entry or field verification |
| **Best Scenario** | Spatial validation, offshore platform layout, repositioning relative to site geography | Rapid coordinate audits, alphanumeric search, sorting across hundreds of transits |
| **Target Role** | Field Installation Technicians & Quality Inspectors | Project Managers & Engineering Coordinators |

---

## Terminology Compliance Reference

| Term | Context & Definition | Prohibited Synonyms |
|---|---|---|
| **Cable Penetrations** | Physical openings in fire walls, bulkheads, or decks through which electrical cables pass. | Do not refer to as generic "holes" or "pipes". |
| **Transit Seals** | Elastomeric sealing modules, compression wedges, and stayplates that seal penetrations against fire, water, and gas. | Do not use generic "rubber blocks". |
| **Floor Plans** | Two-dimensional CAD or image schematics representing structural decks, levels, or architectural layouts. | Do not use "blueprints" or "sketches". |
| **Geolocations** | Geospatial reference points tying assets and floor plans to real-world GPS coordinates (Latitude/Longitude). | **Never call pins "dots" or "marks".** Refer exclusively to "pins", "site markers", or "geolocations". |
```

---

## Deliverables Summary

When requested by the user, produce:
1. `final_instructional_guide.mp4` (1080p instructional video walkthrough with smooth animated cursor and click ripple effects).
2. `guide_<topic>.md` (Companion Markdown manual containing general information only: Executive Summary & Field Impact, Core Capabilities Overview, Comparison Matrix, and Terminology Compliance Reference).
3. `app_knowledge.md` (If app crawling was performed).
