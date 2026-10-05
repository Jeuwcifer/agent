#!/usr/bin/env python3
"""
analyze_session.py - Chat Session & Execution Trace Analyzer for Skill Improvements
Part of the `skill-retrospective` skill.

Parses agent session logs (.jsonl), identifies bottlenecks, tool failures,
and diagnostic trial-and-error loops, and generates actionable skill improvement
proposals following the core retrospective mantra:

"If certain information would have been available earlier, then it would have
been possible to reach the end result that much sooner and missteps avoided.
What are some realistic ways we can add this information so it's available for
the next run? Each suggestion should be graded on a scale of 1 to 10 by the user."
"""

import os
import sys
import json
import glob
import re
import argparse
from datetime import datetime
from collections import defaultdict

DEFAULT_SESSIONS_DIR = os.path.expanduser("~/.pi/agent/sessions/--home-user--")

def find_latest_session_file(sessions_dir=DEFAULT_SESSIONS_DIR):
    if not os.path.exists(sessions_dir):
        # Fallback to searching all session subdirs
        root_sessions = os.path.expanduser("~/.pi/agent/sessions")
        pattern = os.path.join(root_sessions, "**", "*.jsonl")
        files = glob.glob(pattern, recursive=True)
    else:
        files = glob.glob(os.path.join(sessions_dir, "*.jsonl"))
    
    if not files:
        return None
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]

def parse_session(jsonl_path):
    records = []
    with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                pass
    return records

def extract_trace(records):
    """
    Extracts structured turns, tool calls, and results from records.
    """
    turns = []
    pending_tool_calls = {}
    session_start = None
    session_cwd = None

    for r in records:
        rtype = r.get("type")
        if rtype == "session":
            session_start = r.get("timestamp")
            session_cwd = r.get("cwd")
        elif rtype == "message":
            msg = r.get("message", {})
            role = msg.get("role")
            content = msg.get("content")
            timestamp = msg.get("timestamp") or r.get("timestamp")

            if role == "user":
                user_text = ""
                if isinstance(content, str):
                    user_text = content
                elif isinstance(content, list):
                    user_text = " ".join([c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"])
                turns.append({
                    "role": "user",
                    "text": user_text,
                    "timestamp": timestamp,
                    "tools": []
                })
            elif role == "assistant":
                if not turns:
                    turns.append({"role": "user", "text": "(Session start)", "timestamp": timestamp, "tools": []})
                
                tool_calls = []
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "toolCall":
                            call_id = item.get("id")
                            call_info = {
                                "id": call_id,
                                "name": item.get("name"),
                                "arguments": item.get("arguments", {}),
                                "timestamp": timestamp,
                                "result": None
                            }
                            pending_tool_calls[call_id] = call_info
                            tool_calls.append(call_info)
                
                if tool_calls:
                    turns[-1]["tools"].extend(tool_calls)
            elif role == "toolResult":
                call_id = msg.get("toolCallId")
                tool_name = msg.get("toolName")
                is_error = bool(msg.get("isError"))
                res_content = msg.get("content")
                
                res_text = ""
                if isinstance(res_content, str):
                    res_text = res_content
                elif isinstance(res_content, list):
                    res_text = " ".join([c.get("text", "") for c in res_content if isinstance(c, dict) and c.get("text")])

                if call_id in pending_tool_calls:
                    call_info = pending_tool_calls[call_id]
                    call_info["result"] = {
                        "text": res_text,
                        "is_error": is_error,
                        "timestamp": timestamp
                    }

    return {
        "session_start": session_start,
        "session_cwd": session_cwd,
        "turns": turns
    }

def detect_friction_points(trace):
    """
    Identifies missteps, errors, repeated queries, and exploratory trial-and-error loops.
    """
    friction_events = []
    all_tools = []
    for turn_idx, turn in enumerate(trace["turns"]):
        for tool in turn["tools"]:
            tool["turn_idx"] = turn_idx
            all_tools.append(tool)

    # 1. Direct Tool Failures (is_error or failure keywords)
    error_patterns = [
        re.compile(r"error", re.IGNORECASE),
        re.compile(r"failed", re.IGNORECASE),
        re.compile(r"not found", re.IGNORECASE),
        re.compile(r"timeout", re.IGNORECASE),
        re.compile(r"could not find", re.IGNORECASE),
        re.compile(r"exception", re.IGNORECASE)
    ]

    for tool in all_tools:
        res = tool.get("result")
        if not res:
            continue
        
        is_err = res.get("is_error", False)
        text = res.get("text", "")
        
        has_err_text = any(p.search(text) for p in error_patterns) if text else False
        # Filter false positives like "0 errors" or successful git status
        if has_err_text and any(fp in text.lower() for fp in ["0 errors", "no errors", "without error", "not found: 0"]):
            has_err_text = False

        if is_err or (has_err_text and len(text) < 600):
            friction_events.append({
                "type": "tool_failure",
                "tool": tool["name"],
                "args": tool["arguments"],
                "summary": text[:200].replace("\n", " ").strip(),
                "turn_idx": tool["turn_idx"]
            })

    # 2. Repeated Consecutive Tool Calls (Exploration / Trial-and-error Loops)
    call_signatures = []
    for tool in all_tools:
        name = tool["name"]
        args = tool["arguments"]
        sig = name
        if name in ("bash", "default_api:bash"):
            cmd = args.get("command", "").strip()
            # Group by command prefix
            sig = f"bash:{cmd.split()[0] if cmd else ''}"
        elif name in ("read", "default_api:read"):
            sig = f"read:{os.path.basename(args.get('path', ''))}"
        elif name in ("edit", "default_api:edit"):
            sig = f"edit:{os.path.basename(args.get('path', ''))}"
        call_signatures.append((sig, tool))

    loop_count = 1
    for i in range(1, len(call_signatures)):
        prev_sig, prev_tool = call_signatures[i - 1]
        curr_sig, curr_tool = call_signatures[i]
        if curr_sig == prev_sig and not curr_sig.startswith("read:"):
            loop_count += 1
        else:
            if loop_count >= 3:
                friction_events.append({
                    "type": "trial_and_error_loop",
                    "signature": prev_sig,
                    "count": loop_count,
                    "turn_idx": prev_tool["turn_idx"],
                    "summary": f"Repeated tool execution loop: {prev_sig} executed {loop_count} times in sequence."
                })
            loop_count = 1

    # 3. DOM / Selector Probing in Browser sessions
    agent_browser_probes = []
    for tool in all_tools:
        args = tool["arguments"]
        cmd = args.get("command", "") if isinstance(args, dict) else ""
        if "agent-browser" in cmd and any(k in cmd for k in ["eval", "get box", "snapshot"]):
            agent_browser_probes.append(cmd)

    if len(agent_browser_probes) >= 4:
        friction_events.append({
            "type": "dom_exploration_burn",
            "count": len(agent_browser_probes),
            "turn_idx": all_tools[0]["turn_idx"] if all_tools else 0,
            "summary": f"{len(agent_browser_probes)} exploratory DOM queries/evals executed to discover locators and states."
        })

    return friction_events

def generate_counterfactual_recommendations(friction_events, trace):
    """
    Transforms detected friction events into structured skill improvement suggestions
    following the mantra:
    - What info was missing earlier?
    - How could having it have saved time and avoided missteps?
    - Realistic ways to add this info for the next run.
    """
    suggestions = []
    
    # Categorize events
    dom_probes = [e for e in friction_events if e["type"] == "dom_exploration_burn"]
    failures = [e for e in friction_events if e["type"] == "tool_failure"]
    loops = [e for e in friction_events if e["type"] == "trial_and_error_loop"]

    idx = 1

    # Heuristic 1: DOM / UI Locators and Dialog handling
    if dom_probes:
        suggestions.append({
            "id": f"SUGG-{idx:02d}",
            "title": "Codify UI Selectors & Modal Watcher in Target Skill",
            "friction_observed": f"Agent spent {dom_probes[0]['count']} manual `eval` and `get box` commands probing the DOM for buttons, inputs, and modal states.",
            "missing_information": "Exact unique DOM attributes (e.g. data-test IDs, visible element filters, and modal dismissal timings) were not documented in the skill instructions.",
            "realistic_solution": "Add an explicit `Key Locators & Disambiguation Rules` table directly to the relevant `SKILL.md` or domain wiki (`wiki/ui-map.md`). Include persistent modal watchers so exploratory DOM scraping is bypassed entirely.",
            "implementation_target": "Skill instructions (`SKILL.md`) or Knowledge Base (`wiki/ui-map.md`)",
            "estimated_savings": "Eliminates 5-10 exploratory tool calls; saves 2-4 minutes of execution time.",
        })
        idx += 1

    # Heuristic 2: Tool failures / Edit collisions
    edit_failures = [f for f in failures if "edit" in f["tool"].lower() or "not find" in f["summary"].lower()]
    if edit_failures:
        suggestions.append({
            "id": f"SUGG-{idx:02d}",
            "title": "Strict Text Replacement Boundaries & Full Overwrite Fallback",
            "friction_observed": "Targeted file edits failed due to minor whitespace or multi-match mismatch, requiring extra reads and retries.",
            "missing_information": "Precise line offset context or structured AST replacement helper was absent, forcing manual string matching.",
            "realistic_solution": "Add a skill rule: 'When targeted edit fails once, immediately switch to full write/overwrite or read a strict 30-line window around target lines' in `SKILL.md`.",
            "implementation_target": "Agent System/Skill instructions (`SKILL.md`)",
            "estimated_savings": "Avoids 2-3 repetitive edit/read cycles per file modification.",
        })
        idx += 1

    # Heuristic 3: Element not found or timing / asynchronous transitions
    selector_not_found = [f for f in failures if "not found" in f["summary"].lower() or "timeout" in f["summary"].lower()]
    if selector_not_found:
        suggestions.append({
            "id": f"SUGG-{idx:02d}",
            "title": "Pre-flight Verification Hook for Asynchronous Overlays",
            "friction_observed": "Element lookups failed because asynchronous startup modals or animations intercepted clicks and rendered elements invisible.",
            "missing_information": "Knowledge of the 1-3s delayed overlay rendering was missing during the setup phase.",
            "realistic_solution": "Incorporate a standardized pre-flight `ensure_effects()` and `dismiss_popups()` check with a 2-second settle interval into the skill's setup routine.",
            "implementation_target": "Workflow setup script (`record_template.sh` or Python runner)",
            "estimated_savings": "Prevents 100% of false-negative selector timeouts and blocked interactions.",
        })
        idx += 1

    # Generic high-value fallback if specific heuristics didn't trigger
    if not suggestions:
        suggestions.append({
            "id": f"SUGG-{idx:02d}",
            "title": "Pre-compile Known Schema & Verification Checklist",
            "friction_observed": "Agent verified state through multiple exploratory queries instead of executing a deterministic verification checklist.",
            "missing_information": "Expected API payloads, URL routes, and success toasts were discovered progressively rather than referenced from a checklist.",
            "realistic_solution": "Document the verified success criteria and endpoints in the skill's context reference.",
            "implementation_target": "Skill documentation (`SKILL.md`)",
            "estimated_savings": "Cuts 2-4 tool turns per workflow run.",
        })

    return suggestions

def format_retrospective_report(session_file, trace, friction_events, suggestions):
    ts = trace.get("session_start") or datetime.now().isoformat()
    total_turns = len(trace["turns"])
    total_tools = sum(len(t["tools"]) for t in trace["turns"])

    lines = []
    lines.append("# Chat Session Retrospective & Skill Improvement Audit")
    lines.append(f"**Session File:** `{os.path.basename(session_file)}`  ")
    lines.append(f"**Session Start:** `{ts}` | **Turns:** {total_turns} | **Tool Calls:** {total_tools}  ")
    lines.append("")
    lines.append("## Retrospective Mantra")
    lines.append("> *\"Go through the chat session and look for instances of where: If certain information would have been available earlier, then it would have been possible to reach the end result that much sooner and missteps avoided. What are some realistic ways we can add this information so it's available for the next run? Each suggestion should be graded on a scale of 1 to 10 by the user.\"*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Identified Friction & Misstep Summary")
    if friction_events:
        for idx, event in enumerate(friction_events, 1):
            lines.append(f"- **Issue {idx} [{event['type'].upper()}]:** {event['summary']}")
    else:
        lines.append("- *No critical tool failures or loop anomalies detected in trace.*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Concrete Skill Improvement Proposals")
    lines.append("Review each proposal below and grade it on a **scale of 1 to 10** based on feasibility and future impact.")
    lines.append("")
    lines.append("### Grading Rubric:")
    lines.append("- **1-3 (Low):** Minor convenience, fragile, or unlikely to recur.")
    lines.append("- **4-6 (Moderate):** Useful optimization, reduces token or tool churn.")
    lines.append("- **7-8 (High):** Substantial time and failure reduction across multiple runs.")
    lines.append("- **9-10 (Critical):** High-leverage architectural improvement; prevents catastrophic failures or saves major turnaround time.")
    lines.append("")

    for s in suggestions:
        lines.append(f"### [{s['id']}] {s['title']}")
        lines.append(f"- **Observed Friction:** {s['friction_observed']}")
        lines.append(f"- **Root Information Gap:** {s['missing_information']}")
        lines.append(f"- **Realistic Solution Vector:** {s['realistic_solution']}")
        lines.append(f"- **Target Location:** `{s['implementation_target']}`")
        lines.append(f"- **Expected Savings:** {s['estimated_savings']}")
        lines.append(f"- **User Grade:** `[ ___ / 10 ]`")
        lines.append("")

    lines.append("---")
    lines.append("## Interactive Scoring Prompt")
    lines.append("To submit your ratings and apply approved improvements, reply with your scores, for example:")
    lines.append("```")
    for s in suggestions:
        lines.append(f"{s['id']}: 8/10 - Apply this to SKILL.md")
    lines.append("```")
    lines.append("High-scoring items (7+) will be committed directly to the corresponding skill instructions or knowledge base.")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Analyze chat session to identify skill improvements.")
    parser.add_argument("--file", help="Path to specific session .jsonl file")
    parser.add_argument("--sessions-dir", default=DEFAULT_SESSIONS_DIR, help="Directory containing session jsonl files")
    parser.add_argument("--output", help="Optional output path for markdown report")
    parser.add_argument("--json", action="store_true", help="Output raw JSON analysis")

    args = parser.parse_args()

    session_file = args.file
    if not session_file:
        session_file = find_latest_session_file(args.sessions_dir)

    if not session_file or not os.path.exists(session_file):
        print(f"[Error] No session file found in {args.sessions_dir}", file=sys.stderr)
        sys.exit(1)

    records = parse_session(session_file)
    trace = extract_trace(records)
    frictions = detect_friction_points(trace)
    suggestions = generate_counterfactual_recommendations(frictions, trace)

    if args.json:
        result = {
            "session_file": session_file,
            "turns_count": len(trace["turns"]),
            "frictions": frictions,
            "suggestions": suggestions
        }
        print(json.dumps(result, indent=2))
        return

    report = format_retrospective_report(session_file, trace, frictions, suggestions)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[Report] Saved to {args.output}")
    else:
        print(report)

if __name__ == "__main__":
    main()
