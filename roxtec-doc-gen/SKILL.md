---
name: roxtec-doc-gen
description: Automates the creation of support documentation and 1080p video guides for the Roxtec Transit Build web app. Triggers when the user asks to "create an instruction", "document how to", "make a video guide", or "generate a guide" for the Roxtec app or transit application.
---

# Roxtec Documentation Generator

When the user asks to generate documentation or a video guide for a process in the Roxtec Transit Build app (https://transitbuild.roxtec.com), follow these steps to create both a rich Markdown guide (with screenshots) and a 1080p WebM video with animated click indicators.

## Prerequisites & Setup

1. **Authentication**: Use the `roxtec` session to maintain state. If the user doesn't specify credentials and we are not logged in, use the previously established test credentials if permitted (`rtdtest4@proton.me` / `Roxtec123!`).
2. **Tools**: Ensure `agent-browser` is available, `ffmpeg` is installed, and `edge-tts` is available (install via `pip install --break-system-packages edge-tts` if missing).

## Context: App Data Model

Roxtec Transit Build: Asset management system.
Hierarchy:
`Account` (Customer) → `Asset` → [`Floor Plan`, `Item`].
Notes:
- `Item` terminology changes based on selected product type.
- `Item`s are placed onto `Floor Plan`s.
Use this mental model when navigating UI or writing guides.

## Process

1. **Query Knowledge Base**:
   - Before taking any action or writing any script, use the `read` tool to check `wiki/index.md` or invoke the `knowledge-manager` skill to search for pre-existing UI maps, locators, or workflow documentation related to the request (e.g., `#roxtec #ui-map`).
   - If UI mapping exists in the wiki, use those known locators and navigation steps to skip the exploration phase entirely or significantly reduce it.

2. **Explore, Capture & Plan**: 
   - If knowledge is missing or incomplete, silently use `agent-browser` to walk through the requested workflow. Use `agent-browser --session roxtec open ...` and take snapshots (`snapshot -i`) to understand the UI elements and the required steps.
   - When creating items that require unique names (like transits and floor plans), ensure your script dynamically injects a timestamp (e.g., `$(date +%s)`) into the payload to strictly adhere to the application's unique naming rules and avoid save failures.
   - Instead of using arbitrary hardcoded sleeps like `agent-browser wait 3000`, use the provided `wait_for` function to poll the DOM until the target element appears. This ensures deterministic execution and prevents audio desync from slow network or render times.
   - For generic matching, beware of similarly named UI elements. Use strict typing in your `get_ref` calls (e.g., specifying "button" or "textbox") or use precise Javascript evaluation to prevent false positives.
   - Audio generation and syncing: The script uses a unified Python script to directly execute the `ffmpeg` merge, eliminating fragile bash-string hacks. Ensure the `sync_step` is called *only when the UI is fully ready* for the next action. Do not call `sync_step` while waiting for previous transitions to finish.
   - **CRITICAL ARCHITECTURAL RULE FOR SYNC**: NEVER execute visual transitions (e.g., `agent-browser open`, `agent-browser click`, `agent-browser fill`) outside of a narrated step block. If you perform a forced URL navigation or a click *before* `sync_step` and `wait_audio`, the video will capture the action silently, and all subsequent audio will be permanently desynced from the visuals. All actions that change the screen must occur strictly *after* the `wait_audio` command for that step.
   - At key steps, capture screenshots using `agent-browser --session roxtec screenshot step<N>.png`.
   - Document the steps in a Markdown file (`roxtec_guide_<workflow>.md`). Outline exactly what to click, fill, and select. Embed the `step<N>.png` screenshots you captured into the Markdown to make it a high-quality visual guide. Explicitly instruct the user to use unique names when creating items like floor plans or transits.

3. **Generate Narrated Video**:
   - Write a python script using `edge-tts` to generate high-quality text-to-speech audio segments for each step of the video (e.g., `step0.mp3`, `step1.mp3`, etc.). Use the voice model `en-US-AriaNeural`.
   - Create a bash script (e.g., `record_<workflow>.sh`) based on the template below.
   - Insert the interaction steps you discovered into the script. Use the `sync_step` and `wait_audio` functions from the template. Call `TS=$(sync_step <N>)` followed immediately by `wait_audio <N> $TS` *before* the UI action. This guarantees the narration preempts the action, keeping the screen still while the voice describes the upcoming event.
   - To interact with dynamic modals like "Don't show at startup", do not just hide them with CSS as they can still interfere with recording or reappear. Instead, inject JavaScript to actively find and click the checkbox and the Close button, using an interval to ensure the element is captured when it renders. Example:
     ```javascript
     let attempts = 0;
     let inv = setInterval(() => {
         const cb = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(input => 
             (input.closest('label') && input.closest('label').textContent.includes("Don't show at startup")) ||
             (input.parentElement && input.parentElement.textContent.includes("Don't show at startup"))
         );
         if (cb && !cb.checked) cb.click();
         const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes("Close"));
         if (closeBtn) {
             closeBtn.click();
             clearInterval(inv);
         }
         if (++attempts > 10) clearInterval(inv);
     }, 500);
     ```
   - For file uploads, the `<input type="file">` is often unselectable or dynamic. Inject an ID first: `agent-browser --session roxtec eval "document.querySelector('input[type=\"file\"]').id = 'file-upload';"` then run `upload "#file-upload" <path>`. Wait fully for the DOM to update.
   - Drag and drop actions on interactive canvases (like Floor Plans) *must* be constructed using sequential `PointerEvent` objects (`pointerdown`, `pointermove`, `pointerup`) dispatched to the DOM. Regular `MouseEvent`s or `.click()` will fail the drag interaction.
   - To drag transits onto a floor plan canvas, the exact locator format is often CSS-based rather than text-based due to icon spans masking the draggable area. Use `span.rt-badge--primary[draggable='true']` as the source and `.konvajs-content` (or the visual center of the viewport) as the target.
   - Execute the recording script.
   - Use a python script to generate a `merge.sh` FFmpeg command that maps the video stream, applies `adelay` to each audio segment based on the timestamps outputted to `/tmp/timestamps.txt` (note: wait 1 second or ensure accurate matching to avoid overlapping), mixes them into a single track, and encodes the final video using `libopus`. Ensure timestamps are properly transformed into milliseconds for `adelay` and that negative timestamps are clamped to `0`.

## Script Template

Always use this template as the base for the recording script. Modify the "WORKFLOW STEPS" section with the specific actions needed. Use `smart_click` instead of `agent-browser click` for all clicking actions so the cursor movement and click delay are properly animated.

```bash
#!/bin/bash
set -e

export PATH="$HOME/bin:$PATH"

function get_ref {
    local text="$1"
    local type="$2"
    local file="$3"
    # Extracts ref=eXX refs from agent-browser snapshot -i
    # Matches case-insensitive text and optional type
    if [ -n "$type" ]; then
        grep -i "$text" "$file" | grep -i "$type" | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1
    else
        grep -i "$text" "$file" | grep -oE 'ref=e[0-9]+' | cut -d= -f2 | head -1
    fi
}

function wait_for {
    local text="$1"
    local type="$2"
    local max_attempts=15
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        agent-browser --session roxtec snapshot -i > /tmp/snap_wait
        local ref=$(get_ref "$text" "$type" "/tmp/snap_wait")
        if [ -n "$ref" ]; then
            return 0
        fi
        sleep 1
        ((attempt++))
    done
    echo "Timeout waiting for '$text'"
    return 1
}

function wait_for_gone {
    local text="$1"
    local type="$2"
    local max_attempts=15
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        agent-browser --session roxtec snapshot -i > /tmp/snap_wait
        local ref=$(get_ref "$text" "$type" "/tmp/snap_wait")
        if [ -z "$ref" ]; then
            return 0
        fi
        sleep 1
        ((attempt++))
    done
    echo "Timeout waiting for '$text' to disappear"
    return 1
}

function smart_click {
    local ref="$1"
    
    if [ -z "$ref" ]; then
        echo "Ref is empty, skipping click"
        return
    fi
    
    local box_output=$(agent-browser --session roxtec get box "$ref")
    if ! echo "$box_output" | grep -q "x:"; then
        # Fallback if bounding box isn't found
        agent-browser --session roxtec click "$ref"
        return
    fi
    
    local x=$(echo "$box_output" | grep "x:" | awk '{print $2}')
    local y=$(echo "$box_output" | grep "y:" | awk '{print $2}')
    local w=$(echo "$box_output" | grep "width:" | awk '{print $2}')
    local h=$(echo "$box_output" | grep "height:" | awk '{print $2}')
    
    # Calculate center coordinates purely with awk (no bc required)
    local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')

    cat << JS | agent-browser --session roxtec eval --stdin >/dev/null 2>&1
    if (!window._fakeCursor) {
        const cursor = document.createElement('div');
        cursor.id = 'fake-cursor';
        cursor.style.position = 'fixed';
        cursor.style.left = (window.innerWidth / 2) + 'px';
        cursor.style.top = (window.innerHeight / 2) + 'px';
        cursor.style.width = '24px';
        cursor.style.height = '24px';
        cursor.style.backgroundImage = 'url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2224%22 height=%2224%22 viewBox=%220 0 24 24%22 fill=%22white%22 stroke=%22black%22 stroke-width=%221%22%3E%3Cpath d=%22M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z%22/%3E%3C/svg%3E")';
        cursor.style.backgroundSize = 'contain';
        cursor.style.backgroundRepeat = 'no-repeat';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '9999999';
        cursor.style.transition = 'left 0.5s ease-out, top 0.5s ease-out';
        document.body.appendChild(cursor);
        window._fakeCursor = cursor;
    }
    
    window._fakeCursor.style.left = $cx + 'px';
    window._fakeCursor.style.top = $cy + 'px';
    
    setTimeout(() => {
        const dot = document.createElement('div');
        dot.style.position = 'fixed';
        dot.style.left = ($cx - 15) + 'px';
        dot.style.top = ($cy - 15) + 'px';
        dot.style.width = '30px';
        dot.style.height = '30px';
        dot.style.borderRadius = '50%';
        dot.style.backgroundColor = 'rgba(255, 0, 0, 0.5)';
        dot.style.border = '2px solid red';
        dot.style.pointerEvents = 'none';
        dot.style.zIndex = '9999998';
        dot.style.transition = 'all 0.5s ease-out';
        dot.style.transform = 'scale(1)';
        document.body.appendChild(dot);
        
        setTimeout(() => { dot.style.transform = 'scale(2)'; dot.style.opacity = '0'; }, 10);
        setTimeout(() => { dot.remove(); }, 500);
    }, 500);
JS

    # Wait 0.5s for mouse to move, then 1.0s delay = 1.5s total before real click
    sleep 1.5
    agent-browser --session roxtec click "$ref"
}

function smart_drag {
    local ref="$1"
    local tx="$2"
    local ty="$3"
    
    if [ -z "$ref" ]; then
        echo "Ref is empty, skipping drag"
        return
    fi
    
    local box_output=$(agent-browser --session roxtec get box "$ref")
    if ! echo "$box_output" | grep -q "x:"; then
        echo "Cannot find source box"
        return
    fi
    
    local x=$(echo "$box_output" | grep "x:" | awk '{print $2}')
    local y=$(echo "$box_output" | grep "y:" | awk '{print $2}')
    local w=$(echo "$box_output" | grep "width:" | awk '{print $2}')
    local h=$(echo "$box_output" | grep "height:" | awk '{print $2}')
    
    local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')

    cat << JS | agent-browser --session roxtec eval --stdin >/dev/null 2>&1
    if (!window._fakeCursor) {
        const cursor = document.createElement('div');
        cursor.id = 'fake-cursor';
        cursor.style.position = 'fixed';
        cursor.style.left = (window.innerWidth / 2) + 'px';
        cursor.style.top = (window.innerHeight / 2) + 'px';
        cursor.style.width = '24px';
        cursor.style.height = '24px';
        cursor.style.backgroundImage = 'url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2224%22 height=%2224%22 viewBox=%220 0 24 24%22 fill=%22white%22 stroke=%22black%22 stroke-width=%221%22%3E%3Cpath d=%22M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z%22/%3E%3C/svg%3E")';
        cursor.style.backgroundSize = 'contain';
        cursor.style.backgroundRepeat = 'no-repeat';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '9999999';
        cursor.style.transition = 'left 0.5s ease-out, top 0.5s ease-out';
        document.body.appendChild(cursor);
        window._fakeCursor = cursor;
    }
    
    // Move to source
    window._fakeCursor.style.left = $cx + 'px';
    window._fakeCursor.style.top = $cy + 'px';
    
    setTimeout(() => {
        let steps = 10; let i = 0;
        let intv = setInterval(() => { 
            i++; 
            let currX = $cx + ($tx - $cx) * (i / steps); 
            let currY = $cy + ($ty - $cy) * (i / steps); 
            window._fakeCursor.style.left = currX + 'px';
            window._fakeCursor.style.top = currY + 'px';
            if (i >= steps) clearInterval(intv); 
        }, 50);
    }, 500);
JS

    # Wait for the visual animation to finish, then trigger the actual underlying CDP drag
    sleep 1.5
    agent-browser --session roxtec drag "$ref" "canvas" || true
    sleep 1
}

function sync_step {
    local step="$1"
    local timestamp=$SECONDS
    echo "step${step}=${timestamp}" >> /tmp/timestamps.txt
    echo $timestamp
}

function wait_audio {
    local step="$1"
    local start_time="$2"
    local file="step${step}.mp3"
    if [ -f "$file" ]; then
        local dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")
        local dur_int=$(echo "$dur" | awk '{print int($1)+1}')
        local elapsed=$((SECONDS - start_time))
        local remaining=$((dur_int - elapsed))
        if [ $remaining -gt 0 ]; then
            echo "Waiting ${remaining}s for audio step${step}.mp3 to finish..."
            sleep $remaining
        fi
    fi
    # Add a small pad between steps
    sleep 1
}

echo "Setting viewport..."
agent-browser --session roxtec set viewport 1920 1080 1

agent-browser --session roxtec open https://transitbuild.roxtec.com
agent-browser --session roxtec wait --load networkidle || true
agent-browser --session roxtec wait 1000

# Handle Login if needed
URL=$(agent-browser --session roxtec get url)
if [[ "$URL" == *"login"* ]]; then
    echo "Logging in..."
    agent-browser --session roxtec snapshot -i > /tmp/snap_login
    E_EMAIL=$(get_ref "Email" "textbox" "/tmp/snap_login")
    
    if [ -n "$E_EMAIL" ]; then
        agent-browser --session roxtec fill "$E_EMAIL" "rtdtest4@proton.me"
        agent-browser --session roxtec wait 500
        
        wait_for "Continue" "button"
        agent-browser --session roxtec snapshot -i > /tmp/snap_login
        E_CONT=$(get_ref "Continue" "button" "/tmp/snap_login")
        smart_click "$E_CONT"
        agent-browser --session roxtec wait --load networkidle || true

        wait_for "Password" "textbox"
        agent-browser --session roxtec snapshot -i > /tmp/snap_pass
        E_PASS=$(get_ref "Password" "textbox" "/tmp/snap_pass")
        agent-browser --session roxtec fill "$E_PASS" "Roxtec123!"
        agent-browser --session roxtec wait 500
        
        wait_for "Continue" "button"
        agent-browser --session roxtec snapshot -i > /tmp/snap_pass
        E_CONT2=$(get_ref "Continue" "button" "/tmp/snap_pass")
        smart_click "$E_CONT2"
        agent-browser --session roxtec wait --load networkidle || true
    else
        echo "Could not find email field. Snapshot output:"
        cat /tmp/snap_login
    fi
fi

# Dismiss startup modal properly before recording
cat << 'JS' | agent-browser --session roxtec eval --stdin >/dev/null 2>&1 || true
let attempts = 0;
let inv = setInterval(() => {
    const cb = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(input => 
        (input.closest('label') && input.closest('label').textContent.includes("Don't show at startup")) ||
        (input.parentElement && input.parentElement.textContent.includes("Don't show at startup"))
    );
    if (cb && !cb.checked) cb.click();

    const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes("Close"));
    if (closeBtn) {
        closeBtn.click();
        clearInterval(inv);
    }
    if (++attempts > 10) clearInterval(inv);
}, 500);
JS
agent-browser --session roxtec wait 2000

echo "Starting recording..."
agent-browser --session roxtec record start ./workflow_video_guide.webm
SECONDS=0
rm -f /tmp/timestamps.txt

TS=$(sync_step 0)
wait_audio 0 $TS

# ==========================================
# WORKFLOW STEPS GO HERE
# Remember to:
# 1. Use `wait_for "Text" "type"` to ensure the UI is ready.
# 2. Start the step with: TS=$(sync_step <N>)
# 3. Wait for audio: wait_audio <N> $TS
# 4. Get the ref and click (smart_click)
#
# (Drag & Drop Template snippet):
# E_SRC="span.rt-badge--primary[draggable='true']"
# smart_drag "$E_SRC" 960 540
# ==========================================

echo "Stopping recording..."
agent-browser --session roxtec wait 5000
agent-browser --session roxtec record stop
agent-browser --session roxtec close

echo "Merging audio..."
cat << 'PY' > /tmp/build_audio_merge.py
import os, subprocess
timestamps = []
with open('/tmp/timestamps.txt', 'r') as f:
    for line in f:
        if not line.strip(): continue
        key, val = line.strip().split('=')
        timestamps.append((int(key.replace('step', '')), int(val)))

valid_steps = [(idx, t_sec, f"step{idx}.mp3") for idx, t_sec in timestamps if os.path.exists(f"step{idx}.mp3")]
if valid_steps:
    cmd = ["ffmpeg", "-y", "-i", "workflow_video_guide.webm"]
    for _, _, mp3 in valid_steps:
        cmd.extend(["-i", mp3])
    
    filter_parts = [f"[{i+1}:a]adelay={max(0, t_sec * 1000)}|{max(0, t_sec * 1000)}[a{i}]" for i, (_, t_sec, _) in enumerate(valid_steps)]
    filter_complex = "; ".join(filter_parts) + f"; {''.join(f'[a{i}]' for i in range(len(valid_steps)))}amix=inputs={len(valid_steps)}:normalize=0[aout]"
    
    cmd.extend(["-filter_complex", filter_complex, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "libopus", "final_guide.webm"])
    print("Running FFmpeg merge...")
    subprocess.run(cmd, check=True)
PY
python3 /tmp/build_audio_merge.py
if [ -f final_guide.webm ]; then
    mv final_guide.webm workflow_video_guide.webm
fi

echo "Done!"
```

4. **Deliverable**:
   - Output the finalized Markdown guide (with embedded screenshots where appropriate).
   - Run the bash script to produce the video.
   - Provide the user with the filenames.
