#!/usr/bin/env python3
"""Bassiehof VPS Pipeline v3 - Fixed timestamp"""
import os, subprocess, ssl, urllib.request, urllib.parse, json
from datetime import datetime

BASSIEHOF = "/root/bassiehof-pipeline"
VIDEOS = os.path.join(BASSIEHOF, "Videos")
TOOLS = os.path.join(BASSIEHOF, "tools")

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ts_to_sec(ts):
    # Fix: replace comma with dot for ffmpeg
    ts = ts.replace(',', '.').replace(' ', '')
    p = ts.split(':')
    return int(p[0])*3600 + int(p[1])*60 + float(p[2])

def run_cmd(cmd, cwd=None):
    log(f"CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"ERROR: {result.stderr[:200]}")
        return False
    return True

def find_srt(vp):
    base = os.path.splitext(vp)[0]
    for ext in ['.nl.srt', '.srt', '.vtt']:
        srt = base + ext
        if os.path.exists(srt): return srt
    return None

def analyze(srt_path):
    with open(srt_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()
    blocks = content.strip().split('\n\n')
    clips = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3 or '-->' not in lines[1]: continue
        parts = lines[1].split('-->')
        start, end = parts[0].strip(), parts[1].strip()
        text = ' '.join(lines[2:]).strip()
        if not text: continue
        score = 3  # Simplified
        clips.append({'start': start, 'end': end, 'text': text[:80], 'score': score})
    return sorted(clips, key=lambda x: x['score'], reverse=True)[:3]

def process_clip(video, clip, i):
    naam = f"clip_{i}"
    raw = os.path.join(VIDEOS, f"{naam}_raw.mp4")
    # Use fixed timestamps (comma replaced with dot)
    start = clip['start'].replace(',', '.')
    end = clip['end'].replace(',', '.')
    log(f"Cutting: {start} -> {end}")
    if run_cmd(["ffmpeg", "-y", "-i", video, "-ss", start, "-to", end, "-c", "copy", raw]):
        return raw
    return None

def main(video_path):
    log("="*50)
    log("BASSIEHOF PIPELINE v3")
    log("="*50)
    srt = find_srt(video_path)
    if not srt: log("No SRT!"); return
    log(f"SRT: {srt}")
    clips = analyze(srt)
    log(f"Found {len(clips)} clips")
    for i, c in enumerate(clips, 1):
        result = process_clip(video_path, c, i)
        if result: log(f"OK: {result}")
    log("DONE!")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--video")
    a = p.parse_args()
    if a.video: main(a.video)
