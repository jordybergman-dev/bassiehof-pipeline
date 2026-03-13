#!/usr/bin/env python3
"""Bassiehof VPS Pipeline v4 - met Google Drive upload"""
import os, subprocess, sys
from datetime import datetime

BASSIEHOF = "/root/bassiehof-pipeline"
VIDEOS = os.path.join(BASSIEHOF, "Videos")
TOOLS = os.path.join(BASSIEHOF, "tools")

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ts_to_sec(ts):
    ts = ts.replace(',', '.').replace(' ', '')
    p = ts.split(':')
    return int(p[0])*3600 + int(p[1])*60 + float(p[2])

def run_cmd(cmd):
    log(f"CMD: {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"ERR: {r.stderr[:150]}")
        return False
    return True

def upload_to_drive(filename):
    """Upload naar Google Drive"""
    local = os.path.join(VIDEOS, filename)
    remote = "gdrive videos:videos"
    cmd = f'rclone copy "{local}" "{remote}"'
    log(f"Upload: {filename}")
    return run_cmd(cmd)

def main():
    log("="*50)
    log("BASSIEHOF PIPELINE v4")
    log("="*50)
    
    # Check voor nieuwe clips
    clips = [f for f in os.listdir(VIDEOS) if f.startswith('clip_') and f.endswith('.mp4')]
    log(f"Gevonden: {clips}")
    
    if not clips:
        log("Geen clips gevonden!")
        return
    
    for clip in clips:
        upload_to_drive(clip)
        log(f"✅ {clip} naar Drive")
    
    log("Klaar!")

if __name__ == "__main__":
    main()
