---
name: roxtec-doc-gen
description: Automates the creation of support documentation and 1080p video guides for the Roxtec Transit Build web app. Triggers when the user asks to "create an instruction", "document how to", "make a video guide", or "generate a guide" for the Roxtec app or transit application.
---

# Roxtec Documentation Generator

When the user asks to generate documentation or a video guide for a process in the Roxtec Transit Build app (https://transitbuild.roxtec.com), follow these steps to create both a rich Markdown guide (with screenshots) and a 1080p video walkthrough (MP4/WebM) with animated click indicators.

## Prerequisites & Setup

1. **Authentication**: Use the `vidya_roxtec` or `roxtec` session to maintain state. If unauthenticated, use established test credentials (`rtdtest3@proton.me` or `rtdtest4@proton.me` / `Roxtec123!`).
2. **Tools**: Ensure `agent-browser` and `ffmpeg` are available. Helper scripts from `instruction-vidya` (`smart_effects.js`, `merge_video.py`) provide cursor animations and transcoding.

## Context: App Data Model

Roxtec Transit Build: Asset management system.
Hierarchy:
`Account` (Customer) → `Asset` → [`Floor Plan`, `Item`].
Notes:
- `Item` terminology changes based on selected product type (e.g. `Transit`).
- `Item`s are placed onto `Floor Plan`s.
- Draggable locations in the Place Item drawer: Primary locations (`span.rt-badge--primary[draggable="true"]`, `data-test="0"`) vs Reference locations (`span.rt-badge--tertiary[draggable="true"]`, `data-test="1"`).

## Key Locators & Disambiguation Rules

- **Startup Modals & Pre-flight Settling**: Asynchronous popups ("Download the mobile app", "Don't show at startup") render 1-3s after page transitions and intercept clicks. Always install a continuous background watcher (`setInterval`), AND wait 2.5-3s after navigating to an asset URL to trigger `dismiss_popups()` with `#showAtStartup` checkbox + `Close` BEFORE starting screen recording or capturing Step 0 screenshots.
- **Context Isolation on `record start`**:
  `agent-browser record start` launches a fresh browser context/page. Any DOM watchers (`_startupWatcher` interval) and `smart_effects.js` must be re-injected immediately *after* `record start` begins so asynchronous modals cannot mount during video capture.
- **Add Transit Modal Buttons & Commit Rules**:
  - Use exact match: `button[data-test="commit"]` (or `grep -E 'button "Add"'`) to click the final create button.
  - Do NOT use generic `grep -i "Add"`, which erroneously matches `button "Add and set status"` (`commit-and-set-status`) or background `Add transit` buttons.
  - **Product Selection vs Quick Commit**: Leaving Product Group as default ("Please select") allows immediate single-click transit commit via `button[data-test="commit"]`. If a specific Product Group (e.g. "Roxtec rectangular") is selected, Solution, Opening Size, Rows, and Columns cascade into mandatory fields before commit is enabled.
- **Collaborators Button Disambiguation**: The `data-test="manage-collaborators"` attribute is shared across 2 DOM nodes (an invisible 0-width element and the active menu item in the Manage dropdown). Always select the active node using `.rt-dropdown-item[data-test="manage-collaborators"]` or filter matches by `offsetParent !== null`.
- **Manage Buttons**: 
  - Asset-level (opens Collaborators, subsets, etc.): `button[data-test="manage-asset-detail-asset-button"]`
  - Row-level (transit specific): Usually scoped to table rows, avoid generic "Manage" text match.
- **Transit Wizard Progression**: Use `button[data-test="next"]` to navigate through the Identifier, Demand specification, and Product steps before the final `button[data-test="commit"]`.
- **Floor Plan Canvas Toolbar**:
  - Open Place Item drawer: `button[data-test="item-placement-action"]` (displays `+` / `add` icon).
  - Close Place Item drawer: `button[data-test="dialog-close"]`.
- **Canvas Drag & Drop**:
  - Dragging directly to target `"canvas"` via `agent-browser drag "span.rt-badge--primary[draggable='true']" "canvas"` reliably drops the item at canvas center coordinates.
- **Unique Naming Rule**: Always append a timestamp (e.g. `TR_$(date +%s)` or `FP_$(date +%s)`) to names when creating transits or floor plans to avoid duplicate name validation errors.
- **Geolocations View & Map Pinning**:
  - Nav tab: `a[data-test="geolocations"]`
  - Add location action: `button[data-test="geolocation-add-action"]`
  - Creation drawer: `div[data-test="add.geolocation"]`
  - Active draggable marker: `div[data-test="activeMarker"]` (spawns at map center)
  - Coordinate inputs: `input#latitude`, `input#longitude` (updating values dynamically positions pin on Leaflet map)
  - Commit button: `button[data-test="submit-geolocation-button"]`
  - Drawer close button: `button[data-test="dialog-close"]`
  - Location details drawer: Opened by clicking map pin `div[data-test="<location_name>"]` or `div.leaflet-marker-icon`. Contains `Transits` and `Floor plans` linkage tabs.
  - **Dynamic Marker IDs**: Newly created geolocations generate a Leaflet marker with `data-test="<Exact Name Given>"`. Ensure names are uniquely timestamped to easily click them later.
  - **Detail Drawer Tabs (Floor plans/Transits)**: Inner drawer tabs do not have reliable `data-test` attributes. Use text-based JS filtering: `Array.from(document.querySelectorAll('a.rt-tab')).find(a => a.textContent.includes('Floor plans') && a.getBoundingClientRect().x > 0)`
  - **List Filters**: The 'Associated' and 'All' buttons lack data-tests. Find them via `Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'All')`.
  - View selector: `select#view` (`asset-geo-locations` for Map View, `asset-geo-locations-detail` for List View)
  - **Editing Geolocations**:
    - **Map View Path**:
      1. Click pin: `div[data-test="<Location_Name>"]` or `div.leaflet-marker-icon` (opens left details drawer).
      2. Open menu: `button:has-text("Manage")` inside `.rt-geolocation-drawer`.
      3. Trigger edit: `button[data-test="edit-geolocation"]` (opens right Edit drawer).
      4. Submit: `button:has-text("Save")`.
    - **List View Path**:
      1. Switch view: `select#view` -> `asset-geo-locations-detail`.
      2. Trigger edit directly: `button[data-test="geolocation-edit-action"]` within row `.rt-list-item`.
      3. Submit: `button:has-text("Save")` or close via `button[data-test="dialog-close"]`.

- **Leaflet Map Marker Dragging (Fluid Batch Execution)**:
  Standard `agent-browser drag` and synthetic `MouseEvent` dispatching inside `eval` fail to update Leaflet's internal coordinates. Additionally, never execute `agent-browser mouse move` in a loop using individual CLI invocations (adds ~150ms per-step latency → choppy 3 FPS).
  Stream the entire waypoint trajectory in a single `agent-browser batch` call passing a JSON array of commands:
  ```python
  commands = [["mouse", "move", str(sx), str(sy)], ["mouse", "down"]]
  for px, py in interpolated_waypoints:
      commands.append(["mouse", "move", str(px), str(py)])
  commands.append(["mouse", "up"])
  subprocess.run(["agent-browser", "--session", session, "batch"], input=json.dumps(commands), text=True)
  ```
  This streams 50+ commands/sec with zero per-step process overhead, ensuring fluid 60 FPS marker drag.

## Process

1. **Query Knowledge Base**:
   - Check `wiki/roxtec-ui-map.md` for known selectors, view hierarchies, and action locators before writing scripts.

2. **Explore, Capture & Plan**:
   - Use `agent-browser` to verify target asset views and UI states.
   - Inject timestamps into payloads for transits and floor plans to satisfy uniqueness requirements.
   - Use `wait_for` and `wait_for_gone` instead of arbitrary sleeps.
   - Capture screenshots at key steps: `agent-browser --session vidya_roxtec screenshot step<N>_<desc>.png`.

3. **Generate Silent Video Guide**:
   - Use `record_template.sh` as the base.
   - **Silent Video Mandate**: Never include audio or sound tracks. Video output must be strictly silent (`-an`).
   - **Clean UI & No On-Screen Text Bars Mandate**: Never inject text bars, banner overlays, caption bars, or floating explanation windows onto the recording canvas. The application UI must remain 100% clean and unoccluded. Use only smooth SVG cursor gliding (`moveTo`) and click ripple animations (`clickRipple`). All high-level context, operational impact, and general information belong strictly in the companion Markdown documentation.
   - Maintain appropriate visual dwell times (`pace_step 1.5`-`2.5s`) so viewers can follow the actions.
   - Run the persistent startup modal watcher to guarantee uninterrupted click actions.
   - Animate pointer movements with SVG cursor gliding (`moveTo`) and click ripple animations (`clickRipple`).
   - Transcode raw recordings into high-compatibility silent 1080p MP4/WebM using `merge_video.py`.

4. **Deliverables**:
   - 1080p silent video file (`.mp4` / `.webm`) with visual cursor.
   - Companion Markdown guide containing general information only: executive summary & field impact, data model hierarchy, core capabilities overview, methods comparison matrix, and enterprise terminology compliance reference. Granular step-by-step instructions, click-by-click walkthroughs, video milestone timestamp tables, or action/result narrator scripts are unnecessary and strictly omitted from the .md documentation.

---

## Script Template

```bash
#!/usr/bin/env bash
set -e

SESSION="vidya_roxtec"
WORK_DIR="/home/user"
RAW_VIDEO="$WORK_DIR/raw_guide.webm"
FINAL_VIDEO="$WORK_DIR/final_guide.mp4"
TIMESTAMPS="$WORK_DIR/timestamps.txt"
EFFECTS_JS="/home/user/.agents/skills/instruction-vidya/scripts/smart_effects.js"
MERGE_SCRIPT="/home/user/.agents/skills/instruction-vidya/scripts/merge_video.py"

rm -f "$TIMESTAMPS" "$RAW_VIDEO"

function sync_step {
    local step="$1"
    local ts=$SECONDS
    echo "step${step}=${ts}" >> "$TIMESTAMPS"
    echo "$ts"
}

function pace_step {
    local duration="${1:-2.0}"
    sleep "$duration"
}

function dismiss_popups {
    cat << 'JS' | agent-browser --session "$SESSION" eval --stdin >/dev/null 2>&1 || true
    (() => {
        const cb = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(input => 
            (input.closest('label') && input.closest('label').textContent.includes("Don't show at startup")) ||
            (input.parentElement && input.parentElement.textContent.includes("Don't show at startup"))
        );
        if (cb && !cb.checked) cb.click();

        const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes("Close"));
        if (closeBtn) closeBtn.click();
    })();
JS
}

function ensure_authenticated {
    local snap
    snap=$(agent-browser --session "$SESSION" snapshot -i 2>&1 || true)
    if echo "$snap" | grep -qi "Welcome"; then
        agent-browser --session "$SESSION" fill 'input[type="email"], #username' 'rtdtest4@proton.me'
        agent-browser --session "$SESSION" click 'button:has-text("Continue")'
        agent-browser --session "$SESSION" wait --load networkidle
        agent-browser --session "$SESSION" fill 'input[type="password"], #password' 'Roxtec123!'
        agent-browser --session "$SESSION" click 'button:has-text("Continue")'
        agent-browser --session "$SESSION" wait --load networkidle
    fi
}

function ensure_effects {
    dismiss_popups
    if [ -f "$EFFECTS_JS" ]; then
        agent-browser --session "$SESSION" eval --stdin < "$EFFECTS_JS" >/dev/null 2>&1 || true
    fi
}

function get_ref {
    local text="$1"
    local type="$2"
    local file="$3"
    if [ -n "$type" ]; then
        grep -i "$text" "$file" | grep -i "$type" | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1
    else
        grep -i "$text" "$file" | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1
    fi
}

function wait_for {
    local text="$1"
    local type="$2"
    local max_attempts="${3:-25}"
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        dismiss_popups
        agent-browser --session "$SESSION" snapshot -i > /tmp/snap_wait 2>/dev/null || true
        local ref=$(get_ref "$text" "$type" "/tmp/snap_wait")
        if [ -n "$ref" ]; then
            return 0
        fi
        sleep 0.5
        ((attempt++))
    done
    echo "[Error] Timeout waiting for: '$text' ($type)" >&2
    return 1
}

function wait_for_gone {
    local text="$1"
    local type="$2"
    local max_attempts="${3:-25}"
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        dismiss_popups
        agent-browser --session "$SESSION" snapshot -i > /tmp/snap_wait 2>/dev/null || true
        local ref=$(get_ref "$text" "$type" "/tmp/snap_wait")
        if [ -z "$ref" ]; then
            return 0
        fi
        sleep 0.5
        ((attempt++))
    done
    echo "[Error] Timeout waiting for disappearance: '$text' ($type)" >&2
    return 1
}

function smart_click {
    local target="$1"
    if [ -z "$target" ]; then return; fi
    if [[ "$target" =~ ^e[0-9]+$ ]]; then target="@$target"; fi

    ensure_effects
    local box
    box=$(agent-browser --session "$SESSION" get box "$target" 2>/dev/null || true)
    
    if ! echo "$box" | grep -q "x:"; then
        agent-browser --session "$SESSION" click "$target"
        return
    fi

    local x=$(echo "$box" | grep "x:" | awk '{print $2}')
    local y=$(echo "$box" | grep "y:" | awk '{print $2}')
    local w=$(echo "$box" | grep "width:" | awk '{print $2}')
    local h=$(echo "$box" | grep "height:" | awk '{print $2}')

    local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')

    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.moveTo($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.5
    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.clickRipple($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.3
    agent-browser --session "$SESSION" click "$target"
    sleep 0.6
}

function smart_type {
    local target="$1"
    local text="$2"
    if [ -z "$target" ]; then return; fi
    if [[ "$target" =~ ^e[0-9]+$ ]]; then target="@$target"; fi

    ensure_effects
    local box
    box=$(agent-browser --session "$SESSION" get box "$target" 2>/dev/null || true)
    if echo "$box" | grep -q "x:"; then
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
    fi

    agent-browser --session "$SESSION" fill "$target" "$text"
    sleep 0.5
}

function smart_drag {
    local src="$1"
    local tx="$2"
    local ty="$3"

    ensure_effects
    local box
    box=$(agent-browser --session "$SESSION" get box "$src" 2>/dev/null || true)
    local x=$(echo "$box" | grep "x:" | awk '{print $2}')
    local y=$(echo "$box" | grep "y:" | awk '{print $2}')
    local w=$(echo "$box" | grep "width:" | awk '{print $2}')
    local h=$(echo "$box" | grep "height:" | awk '{print $2}')
    local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')

    cat << JS | agent-browser --session "$SESSION" eval --stdin >/dev/null 2>&1 || true
    if (window.__vidya) {
        window.__vidya.moveTo($cx, $cy);
        setTimeout(() => {
            let steps = 15; let i = 0;
            let intv = setInterval(() => { 
                i++; 
                let currX = $cx + ($tx - $cx) * (i / steps); 
                let currY = $cy + ($ty - $cy) * (i / steps); 
                window.__vidya.moveTo(currX, currY);
                if (i >= steps) {
                    clearInterval(intv);
                    window.__vidya.clickRipple($tx, $ty);
                }
            }, 35);
        }, 300);
    }
JS

    sleep 1.2
    agent-browser --session "$SESSION" drag "$src" "canvas" || true
    sleep 1.5
}

# 1. Initialize Browser
echo "Setting 1080p viewport..."
agent-browser --session "$SESSION" set viewport 1920 1080 1
agent-browser --session "$SESSION" open "https://transitbuild.roxtec.com"
agent-browser --session "$SESSION" wait --load networkidle

# 2. Continuous Startup Dialog Dismissal
cat << 'JS' | agent-browser --session "$SESSION" eval --stdin
(() => {
    function closeStartup() {
        const cb = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(input => 
            (input.closest('label') && input.closest('label').textContent.includes("Don't show at startup")) ||
            (input.parentElement && input.parentElement.textContent.includes("Don't show at startup"))
        );
        if (cb && !cb.checked) cb.click();
        const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes("Close"));
        if (closeBtn) closeBtn.click();
    }
    closeStartup();
    if (!window._startupWatcher) {
        window._startupWatcher = setInterval(closeStartup, 400);
    }
})();
JS

ensure_effects

# 3. Start Recording
echo "Starting screen recording..."
agent-browser --session "$SESSION" record stop >/dev/null 2>&1 || true
agent-browser --session "$SESSION" record start "$RAW_VIDEO"
SECONDS=0

# Workflow steps (using sync_step, smart_click, smart_type, pace_step)

# 4. Stop Recording & Post-Process
echo "Stopping recording..."
agent-browser --session "$SESSION" record stop
agent-browser --session "$SESSION" close

python3 "$MERGE_SCRIPT" \
    --video "$RAW_VIDEO" \
    --timestamps "$TIMESTAMPS" \
    --output "$FINAL_VIDEO" \
    --format mp4
```
