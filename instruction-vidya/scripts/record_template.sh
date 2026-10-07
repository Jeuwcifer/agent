#!/usr/bin/env bash
# ==============================================================================
# record_template.sh - Automated, paced silent video recording template
# for instruction-vidya with clean, unoccluded application UI.
# NOTE: On-screen text bars and banners are strictly prohibited. All explanations
# belong in the companion Markdown guide.
# ==============================================================================
set -e

SESSION="${VIDYA_SESSION:-vidya_rec}"
RAW_VIDEO="${VIDYA_RAW:-raw_recording.webm}"
FINAL_VIDEO="${VIDYA_OUTPUT:-instructional_guide.mp4}"
TIMESTAMPS_FILE="${VIDYA_TIMESTAMPS:-timestamps.txt}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EFFECTS_JS="$SKILL_DIR/scripts/smart_effects.js"

# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------

function ensure_effects {
    if [ -f "$EFFECTS_JS" ]; then
        agent-browser --session "$SESSION" eval --stdin < "$EFFECTS_JS" >/dev/null 2>&1 || true
    fi
}

function ensure_authenticated {
    local snap
    snap=$(agent-browser --session "$SESSION" snapshot -i 2>&1 || true)
    if echo "$snap" | grep -qi "Welcome"; then
        agent-browser --session "$SESSION" fill 'input[type="email"], #username, input[name="username"]' "${VIDYA_USER:-rtdtest4@proton.me}"
        agent-browser --session "$SESSION" click 'button:has-text("Continue")'
        agent-browser --session "$SESSION" wait --load networkidle
        agent-browser --session "$SESSION" fill 'input[type="password"], #password, input[name="password"]' "${VIDYA_PASS:-Roxtec123!}"
        agent-browser --session "$SESSION" click 'button:has-text("Continue")'
        agent-browser --session "$SESSION" wait --load networkidle
    fi
}

# NOTE: On-screen textbars, banners, and windows are strictly disabled to
# maintain a clean, unoccluded application recording.
function show_banner { :; }
function hide_banner { :; }
function show_window { :; }
function hide_window { :; }

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
    local max_attempts="${3:-20}"
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        agent-browser --session "$SESSION" snapshot -i > /tmp/vidya_wait_snap 2>/dev/null || true
        local ref=$(get_ref "$text" "$type" "/tmp/vidya_wait_snap")
        if [ -n "$ref" ]; then
            return 0
        fi
        sleep 0.5
        ((attempt++))
    done
    echo "[Error] Timeout waiting for element: text='$text' type='$type'" >&2
    return 1
}

function wait_for_gone {
    local text="$1"
    local type="$2"
    local max_attempts="${3:-20}"
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        agent-browser --session "$SESSION" snapshot -i > /tmp/vidya_wait_snap 2>/dev/null || true
        local ref=$(get_ref "$text" "$type" "/tmp/vidya_wait_snap")
        if [ -z "$ref" ]; then
            return 0
        fi
        sleep 0.5
        ((attempt++))
    done
    echo "[Error] Timeout waiting for element to disappear: text='$text' type='$type'" >&2
    return 1
}

function smart_click {
    local target="$1"
    if [ -z "$target" ]; then
        echo "[smart_click] Target is empty, skipping" >&2
        return
    fi

    if [[ "$target" =~ ^e[0-9]+$ ]]; then
        target="@$target"
    fi

    ensure_effects

    local box_output
    box_output=$(agent-browser --session "$SESSION" get box "$target" 2>/dev/null || true)
    
    if ! echo "$box_output" | grep -q "x:"; then
        agent-browser --session "$SESSION" click "$target"
        return
    fi

    local x=$(echo "$box_output" | grep "x:" | awk '{print $2}')
    local y=$(echo "$box_output" | grep "y:" | awk '{print $2}')
    local w=$(echo "$box_output" | grep "width:" | awk '{print $2}')
    local h=$(echo "$box_output" | grep "height:" | awk '{print $2}')

    local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
    local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')

    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.moveTo($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.5

    agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.clickRipple($cx, $cy)" >/dev/null 2>&1 || true
    sleep 0.3

    agent-browser --session "$SESSION" click "$target"
    sleep 0.8
}

function smart_type {
    local target="$1"
    local text="$2"
    if [ -z "$target" ]; then
        echo "[smart_type] Target is empty, skipping" >&2
        return
    fi

    if [[ "$target" =~ ^e[0-9]+$ ]]; then
        target="@$target"
    fi

    ensure_effects

    local box_output
    box_output=$(agent-browser --session "$SESSION" get box "$target" 2>/dev/null || true)
    if echo "$box_output" | grep -q "x:"; then
        local x=$(echo "$box_output" | grep "x:" | awk '{print $2}')
        local y=$(echo "$box_output" | grep "y:" | awk '{print $2}')
        local w=$(echo "$box_output" | grep "width:" | awk '{print $2}')
        local h=$(echo "$box_output" | grep "height:" | awk '{print $2}')
        local cx=$(echo "$x $w" | awk '{printf "%d\n", $1 + ($2 / 2)}')
        local cy=$(echo "$y $h" | awk '{printf "%d\n", $1 + ($2 / 2)}')
        agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.moveTo($cx, $cy)" >/dev/null 2>&1 || true
        sleep 0.4
        agent-browser --session "$SESSION" eval "window.__vidya && window.__vidya.clickRipple($cx, $cy)" >/dev/null 2>&1 || true
        sleep 0.2
    fi

    agent-browser --session "$SESSION" fill "$target" "$text"
    sleep 0.8
}

function sync_step {
    local step="$1"
    local timestamp=$SECONDS
    echo "step${step}=${timestamp}" >> "$TIMESTAMPS_FILE"
    echo $timestamp
}

function pace_step {
    local duration="${1:-1.5}"
    sleep "$duration"
}

# ------------------------------------------------------------------------------
# Initialization & Setup
# ------------------------------------------------------------------------------

echo "[Vidya] Setting 1080p viewport..."
agent-browser --session "$SESSION" set viewport 1920 1080 1

# Start recording (silent webm)
echo "[Vidya] Starting screen recording to $RAW_VIDEO..."
rm -f "$TIMESTAMPS_FILE" "$RAW_VIDEO"
agent-browser --session "$SESSION" record start "$RAW_VIDEO"
SECONDS=0

# ==============================================================================
# WORKFLOW EXECUTION
# Insert workflow steps here using the pattern:
#
# TS=$(sync_step 0)
# pace_step 2.5
# # Visual actions (smart_click, smart_type, wait_for)
# ==============================================================================

# Example Step 0: Intro
# TS=$(sync_step 0)
# pace_step 3

# ==============================================================================
# Wrap Up & Post-Processing
# ==============================================================================

echo "[Vidya] Finishing recording..."
sleep 2
agent-browser --session "$SESSION" record stop
agent-browser --session "$SESSION" close

echo "[Vidya] Post-processing silent video..."
python3 "$SKILL_DIR/scripts/merge_video.py" \
    --video "$RAW_VIDEO" \
    --timestamps "$TIMESTAMPS_FILE" \
    --output "$FINAL_VIDEO"

echo "[Vidya] Silent video guide completed: $FINAL_VIDEO"
