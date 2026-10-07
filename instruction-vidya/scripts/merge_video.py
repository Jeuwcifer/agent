#!/usr/bin/env python3
"""
merge_video.py - Post-production processor for recorded walkthrough videos.
Transcodes raw browser screen recordings into clean, optimized MP4/WebM videos.
"""

import os
import sys
import argparse
import subprocess
import shutil

def process_video(video_in: str, output_path: str, output_format: str = "auto"):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed or not in PATH.")

    if not os.path.exists(video_in):
        raise FileNotFoundError(f"Input video file not found: {video_in}")

    if output_format == "auto":
        ext = os.path.splitext(output_path)[1].lower()
        output_format = "mp4" if ext == ".mp4" else "webm"

    cmd = ["ffmpeg", "-y", "-i", video_in]

    if output_format == "mp4":
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-an",
            "-movflags", "+faststart"
        ])
    else:  # webm
        cmd.extend([
            "-c:v", "libvpx-vp9",
            "-b:v", "2M",
            "-crf", "30",
            "-pix_fmt", "yuv420p",
            "-an"
        ])

    cmd.append(output_path)

    print(f"[Video] Transcoding {video_in} -> {output_path} ({output_format})...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[Video] FFmpeg failed with error:\n", res.stderr)
        raise RuntimeError("FFmpeg video post-processing failed.")

    print(f"[Video] Successfully generated final video: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Post-process recorded video walkthroughs.")
    parser.add_argument("--video", required=True, help="Input raw recorded video file (e.g. raw.webm)")
    parser.add_argument("--output", required=True, help="Output destination (e.g. guide.webm or guide.mp4)")
    parser.add_argument("--timestamps", help="Optional timestamps file (used for reference / companion guide)")
    parser.add_argument("--audiodir", help="Deprecated: kept for backward compatibility")
    parser.add_argument("--format", choices=["auto", "mp4", "webm"], default="auto", help="Output container format")

    args = parser.parse_args()
    process_video(args.video, args.output, args.format)

if __name__ == "__main__":
    main()
