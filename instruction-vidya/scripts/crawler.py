#!/usr/bin/env python3
"""
crawler.py - Autonomous web application crawler for instruction_vidya.
Connects, logs in (if credentials provided), maps routes, interactive elements,
dialogs, and workflows, producing an Application Knowledge Map (JSON + Markdown).
"""

import os
import sys
import json
import time
import re
import argparse
import subprocess
import urllib.parse

def run_agent_browser(args, session="vidya_crawl", timeout=45):
    cmd = ["agent-browser", "--session", session] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res.stdout.strip(), res.stderr.strip(), res.returncode

def get_snapshot(session="vidya_crawl", interactive=True):
    args = ["snapshot", "-i"] if interactive else ["snapshot"]
    out, _, _ = run_agent_browser(args, session=session)
    return out

def get_current_url(session="vidya_crawl"):
    out, _, _ = run_agent_browser(["get", "url"], session=session)
    return out.strip()

def get_current_title(session="vidya_crawl"):
    out, _, _ = run_agent_browser(["get", "title"], session=session)
    return out.strip()

def parse_snapshot_elements(snapshot_text):
    """
    Parses agent-browser snapshot text into structured element descriptors.
    Handles varied bracket metadata like [level=2, ref=e1] or [disabled, ref=e5].
    """
    elements = []
    lines = snapshot_text.splitlines()
    pattern = re.compile(r'^\s*-\s*([a-zA-Z0-9_\-]+)\s*(?:\"([^\"]*)\")?\s*\[(.*ref=([^,\s\]]+).*)\]')
    
    for line in lines:
        match = pattern.match(line)
        if match:
            role = match.group(1).lower()
            name = match.group(2) or ""
            ref = match.group(4)
            elements.append({
                "role": role,
                "name": name.strip(),
                "ref": ref.strip(),
                "raw": line.strip()
            })
    return elements

def attempt_login(url, email, password, session="vidya_crawl"):
    print(f"[Auth] Initializing session viewport 1920x1080 and opening {url}...")
    run_agent_browser(["set", "viewport", "1920", "1080", "1"], session=session)
    run_agent_browser(["open", url], session=session)
    time.sleep(2)
    
    current_url = get_current_url(session)
    snap = get_snapshot(session)
    elements = parse_snapshot_elements(snap)
    
    login_keywords = ["login", "signin", "sign-in", "log in", "sign in", "auth"]
    is_login_page = any(k in current_url.lower() for k in login_keywords) or any(
        e["role"] == "button" and any(k in e["name"].lower() for k in login_keywords) for e in elements
    ) or any("password" in e["role"] or "pass" in e["name"].lower() for e in elements)

    if not is_login_page:
        print("[Auth] No login form detected; proceeding as already authenticated or public app.")
        return True

    print(f"[Auth] Login form detected on {current_url}. Locating inputs...")
    email_ref = None
    pass_ref = None
    submit_ref = None

    textboxes = [e for e in elements if e["role"] == "textbox"]
    buttons = [e for e in elements if e["role"] == "button"]

    for tb in textboxes:
        n = tb["name"].lower()
        if "pass" in n:
            pass_ref = tb["ref"]
        elif any(k in n for k in ["email", "user", "login", "account", "id"]):
            email_ref = tb["ref"]

    # Fallback to order if not identified by name
    if not email_ref and len(textboxes) >= 1:
        email_ref = textboxes[0]["ref"]
    if not pass_ref and len(textboxes) >= 2:
        pass_ref = textboxes[1]["ref"]

    for btn in buttons:
        n = btn["name"].lower()
        if any(k in n for k in ["sign in", "log in", "continue", "submit", "next", "enter"]):
            submit_ref = btn["ref"]
            break

    if not submit_ref and buttons:
        submit_ref = buttons[0]["ref"]

    if email_ref and email:
        print(f"[Auth] Filling username/email (ref=@{email_ref})...")
        run_agent_browser(["fill", f"@{email_ref}", email], session=session)
        time.sleep(0.5)

    if pass_ref and password:
        print(f"[Auth] Filling password (ref=@{pass_ref})...")
        run_agent_browser(["fill", f"@{pass_ref}", password], session=session)
        time.sleep(0.5)

    if submit_ref:
        print(f"[Auth] Clicking submit (ref=@{submit_ref})...")
        run_agent_browser(["click", f"@{submit_ref}"], session=session)
        time.sleep(3)

    post_url = get_current_url(session)
    print(f"[Auth] Authentication attempt completed. Current URL: {post_url}")
    return post_url or url

def crawl_application(start_url, max_depth=2, max_views=15, session="vidya_crawl"):
    base_domain = urllib.parse.urlparse(start_url).netloc
    visited_urls = set()
    queue = [(start_url, 0, "Root Landing")]
    views_mapped = []

    print(f"[Crawler] Starting exploration from {start_url} (depth={max_depth}, limit={max_views} views)...")

    while queue and len(views_mapped) < max_views:
        url, depth, origin_label = queue.pop(0)
        norm_url = url.split("#")[0].rstrip("/")
        if norm_url in visited_urls:
            continue
        visited_urls.add(norm_url)

        print(f"\n[Crawler] [{len(views_mapped)+1}/{max_views}] Exploring view: {url} (Depth: {depth})")
        run_agent_browser(["open", url], session=session)
        time.sleep(1.5)

        title = get_current_title(session)
        snap = get_snapshot(session)
        elements = parse_snapshot_elements(snap)

        view_info = {
            "url": url,
            "title": title,
            "depth": depth,
            "origin": origin_label,
            "navigation_links": [],
            "actions": [],
            "form_fields": [],
            "modals_detected": []
        }

        for el in elements:
            role = el["role"]
            name = el["name"]
            ref = el["ref"]

            if not name and role not in ["textbox", "combobox"]:
                continue

            if role in ["link", "tab"] or (role == "button" and any(k in name.lower() for k in ["view", "page", "tab", "go to"])):
                view_info["navigation_links"].append({"name": name, "role": role, "ref": ref})
                
            elif role == "button":
                is_dangerous = any(d in name.lower() for d in ["delete", "remove", "logout", "sign out", "purge", "destroy", "cancel subscription"])
                view_info["actions"].append({
                    "name": name,
                    "ref": ref,
                    "dangerous": is_dangerous
                })

            elif role in ["textbox", "combobox", "checkbox", "radio", "slider", "spinbutton"]:
                view_info["form_fields"].append({
                    "name": name or role,
                    "role": role,
                    "ref": ref
                })

        # Safe probing of modal/drawer buttons
        candidate_modal_buttons = [
            a for a in view_info["actions"]
            if any(k in a["name"].lower() for k in ["new", "create", "add", "invite", "filter", "settings", "configure"])
            and not a["dangerous"]
        ]

        for mba in candidate_modal_buttons[:2]:
            try:
                print(f"[Crawler] Probing modal trigger: '{mba['name']}' (ref=@{mba['ref']})...")
                run_agent_browser(["click", f"@{mba['ref']}"], session=session)
                time.sleep(1.2)
                modal_snap = get_snapshot(session)
                modal_elements = parse_snapshot_elements(modal_snap)
                
                modal_inputs = [m for m in modal_elements if m["role"] in ["textbox", "combobox", "checkbox", "button"]]
                if len(modal_inputs) > len(view_info["form_fields"]):
                    modal_fields = [m["name"] for m in modal_inputs if m["role"] != "button" and m["name"]]
                    view_info["modals_detected"].append({
                        "trigger_button": mba["name"],
                        "fields": modal_fields
                    })
                    print(f"[Crawler] -> Discovered workflow for '{mba['name']}' with fields: {modal_fields}")

                close_btn = next((m for m in modal_elements if m["role"] == "button" and any(c in m["name"].lower() for c in ["close", "cancel", "dismiss", "esc"])), None)
                if close_btn:
                    run_agent_browser(["click", f"@{close_btn['ref']}"], session=session)
                else:
                    run_agent_browser(["press", "Escape"], session=session)
                time.sleep(0.8)
            except Exception as e:
                print(f"[Crawler] Probing '{mba['name']}' finished: {e}")
                run_agent_browser(["press", "Escape"], session=session)

        views_mapped.append(view_info)

        # Enqueue new navigation links if within depth limit
        if depth < max_depth:
            js_get_links = """
            Array.from(document.querySelectorAll('a[href]'))
                 .map(a => ({ text: a.textContent.trim(), href: a.href }))
                 .filter(a => a.href && a.href.startsWith('http'))
            """
            out_links, _, _ = run_agent_browser(["eval", js_get_links], session=session)
            try:
                found_links = json.loads(out_links) if out_links and out_links.startswith("[") else []
                for lnk in found_links:
                    l_url = lnk.get("href", "")
                    l_text = lnk.get("text", "")
                    parsed = urllib.parse.urlparse(l_url)
                    if parsed.netloc == base_domain:
                        norm_l = l_url.split("#")[0].rstrip("/")
                        if norm_l not in visited_urls and not any(q[0].rstrip("/") == norm_l for q in queue):
                            if not any(k in l_url.lower() or k in l_text.lower() for k in ["logout", "signout", "sign-out"]):
                                queue.append((l_url, depth + 1, l_text or "Link"))
            except Exception:
                pass

    return views_mapped

def generate_knowledge_markdown(start_url, views_mapped):
    md = [
        f"# Application Knowledge Map",
        f"",
        f"- **Base URL**: {start_url}",
        f"- **Views Discovered**: {len(views_mapped)}",
        f"- **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"",
        f"## Navigation & Feature Overview",
        f""
    ]

    for idx, v in enumerate(views_mapped, 1):
        md.append(f"### {idx}. {v['title'] or 'View'} (`{v['url']}`)")
        md.append(f"- **Discovery Origin**: {v['origin']} (Depth: {v['depth']})")
        
        if v["actions"]:
            action_names = [f"`{a['name']}`" for a in v["actions"] if not a["dangerous"]]
            md.append(f"- **Primary Actions**: {', '.join(action_names) if action_names else 'None'}")

        if v["form_fields"]:
            fields = [f"`{f['name']}` ({f['role']})" for f in v["form_fields"]]
            md.append(f"- **Form Controls**: {', '.join(fields)}")

        if v["modals_detected"]:
            md.append(f"- **Discovered Dialogs / Workflows**:")
            for m in v["modals_detected"]:
                md.append(f"  - Trigger: `{m['trigger_button']}` -> Inputs: {', '.join(f'`{f}`' for f in m['fields'])}")
                
        md.append("")

    md.append("## Inferred Workflows for Video Instructions")
    md.append("")
    for v in views_mapped:
        for m in v["modals_detected"]:
            md.append(f"- **How to {m['trigger_button']}**:")
            md.append(f"  1. Navigate to {v['title']} (`{v['url']}`).")
            md.append(f"  2. Click `{m['trigger_button']}`.")
            md.append(f"  3. Fill the form fields: {', '.join(m['fields'])}.")
            md.append(f"  4. Submit to complete.")
            md.append("")

    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Crawl and map a web application for instruction_vidya.")
    parser.add_argument("--url", required=True, help="Web application URL to crawl")
    parser.add_argument("--email", default="", help="Login email/username")
    parser.add_argument("--password", default="", help="Login password")
    parser.add_argument("--session", default="vidya_crawl", help="agent-browser session name")
    parser.add_argument("--depth", type=int, default=2, help="Crawl depth limit (default: 2)")
    parser.add_argument("--max-views", type=int, default=10, help="Maximum views to explore (default: 10)")
    parser.add_argument("--outdir", default=".", help="Directory to save knowledge artifacts")

    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    try:
        active_url = attempt_login(args.url, args.email, args.password, session=args.session)
        views = crawl_application(active_url, max_depth=args.depth, max_views=args.max_views, session=args.session)

        json_path = os.path.join(args.outdir, "app_knowledge.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "app_url": args.url,
                "crawled_at": time.time(),
                "views": views
            }, f, indent=2)
        print(f"[Crawler] Knowledge JSON saved to: {json_path}")

        md_content = generate_knowledge_markdown(args.url, views)
        md_path = os.path.join(args.outdir, "app_knowledge.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[Crawler] Knowledge Markdown saved to: {md_path}")

    finally:
        print("[Crawler] Closing browser crawl session...")
        run_agent_browser(["close"], session=args.session)

if __name__ == "__main__":
    main()
