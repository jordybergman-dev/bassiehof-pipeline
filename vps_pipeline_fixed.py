#!/usr/bin/env python3
"""Fixed VPS Pipeline with better error handling"""

import os
import sys
import subprocess

def run_cmd(cmd, cwd=None):
    """Run command with full error output"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return False
    print(f"OK: {result.stdout[:200]}")
    return True

# Test ffmpeg
print("Testing ffmpeg...")
run_cmd(["ffmpeg", "-version"])

# Test clipping a small part
print("\nTesting clip...")
run_cmd([
    "ffmpeg", "-y", "-i", "/root/bassiehof-pipeline/Videos/debat-over-iran-10-16.mp4",
    "-ss", "00:00:00", "-to", "00:00:10",
    "-c", "copy", "/root/bassiehof-pipeline/Videos/test_clip.mp4"
])
