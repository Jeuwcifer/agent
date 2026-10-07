#!/usr/bin/env python3
"""
instruction_vidya.py - Unified CLI pipeline orchestrator for instruction-vidya.
Coordinates crawling, video recording with smart effects,
and FFmpeg post-processing.
"""

import os
import sys
import argparse
import subprocess
import shutil

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")

def check_env():
    for cmd in ["agent-browser", "ffmpeg", "ffprobe"]:
        if not shutil.which(cmd):
            raise RuntimeError(f"Missing required tool: {cmd}")

def run_crawler(url, email, password, outdir, session="vidya_crawl", depth=2, max_views=10):
    cmd = [
        sys.executable,
        os.path.join(SCRIPTS_DIR, "crawler.py"),
        "--url", url,
        "--email", email,
        "--password", password,
        "--session", session,
        "--depth", str(depth),
        "--max-views", str(max_views),
        "--outdir", outdir
    ]
    print(f"\n[Vidya] Starting application crawler on {url}...")
    subprocess.run(cmd, check=True)

def process_output(raw_video, output_video, timestamps_file=None, output_format="auto"):
    cmd = [
        sys.executable,
        os.path.join(SCRIPTS_DIR, "merge_video.py"),
        "--video", raw_video,
        "--output", output_video,
        "--format", output_format
    ]
    if timestamps_file and os.path.exists(timestamps_file):
        cmd.extend(["--timestamps", timestamps_file])
    print(f"\n[Vidya] Post-processing video...")
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description="instruction-vidya orchestrator")
    parser.add_argument("--url", help="Target web application URL")
    parser.add_argument("--email", default="", help="Login username or email")
    parser.add_argument("--password", default="", help="Login password")
    parser.add_argument("--crawl", action="store_true", help="Perform autonomous exploration crawl")
    parser.add_argument("--record-script", help="Path to custom bash recording script")
    parser.add_argument("--output", default="final_guide.mp4", help="Output video file name")
    parser.add_argument("--workdir", default="./vidya_output", help="Working directory for artifacts")

    args = parser.parse_args()
    check_env()
    os.makedirs(args.workdir, exist_ok=True)

    # 1. Crawl phase if requested
    if args.crawl:
        if not args.url:
            print("[Error] --url is required when --crawl is specified.")
            sys.exit(1)
        run_crawler(args.url, args.email, args.password, args.workdir)

    # 2. Execution of recording script if provided
    if args.record_script:
        print(f"\n[Vidya] Executing recording script: {args.record_script}...")
        env = os.environ.copy()
        env["VIDYA_RAW"] = os.path.join(args.workdir, "raw_recording.webm")
        env["VIDYA_TIMESTAMPS"] = os.path.join(args.workdir, "timestamps.txt")
        env["VIDYA_OUTPUT"] = os.path.join(args.workdir, args.output)
        subprocess.run(["bash", args.record_script], cwd=args.workdir, env=env, check=True)

        # 3. Post-process if raw video exists
        raw_webm = os.path.join(args.workdir, "raw_recording.webm")
        ts_file = os.path.join(args.workdir, "timestamps.txt")
        out_dest = os.path.join(args.workdir, args.output)
        if os.path.exists(raw_webm):
            process_output(raw_webm, out_dest, timestamps_file=ts_file)
            print(f"\n[Vidya] Done! Instructional video generated at: {out_dest}")

if __name__ == "__main__":
    main()
