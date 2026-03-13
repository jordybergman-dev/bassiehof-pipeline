#!/usr/bin/env python3
"""
Bassiehof VPS Pipeline v2 - Fixed
"""
import os, subprocess, ssl, urllib.request, urllib.parse, json
from datetime import datetime

BASSIEHOF = "/root/bassiehof-pipeline"
VIDEOS = os.path.join(BASSIEHOF, "Videos")
TOOLS = os.path.join(BASSIEHOF, "tools")
TELEGRAM_BOT = os.environ.get("TELEGRAM_BOT")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT")

VIRAL_KEYWORDS = {"woede":3,"boos":2,"schande":3,"belachelijk":2,"onacceptabel":3,"ramp":3,"migratie":2,"pensioen":2,"klimaat":2,"kabinet":1,"nooit":2,"niemand":2}

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def telegram_send(msg):
    if not TELEGRAM_BOT: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT, "text": msg}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
    except: pass

def run_cmd(cmd, cwd=None):
    """Run command with output"""
    log(f"CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"ERROR: {result.stderr[:300]}")
        return False
    if result.stdout:
        log(f"OK: {result.stdout[:200]}")
    return True

def find_srt(video_path):
    base = os.path.splitext(video_path)[0]
    for ext in ['.nl.srt', '.srt', '.vtt']:
        srt = base + ext
        if os.path.exists(srt):
            return srt
    return None

def ts_to_sec(ts):
    ts = ts.replace(',','.').replace(' ','')
    p = ts.split(':')
    return int(p[0])*3600 + int(p[1])*60 + float(p[2])

def analyze_srt(srt_path):
    log("Analyzing transcript...")
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
        
        score = 0
        text_lower = text.lower()
        for kw, w in VIRAL_KEYWORDS.items():
            if kw in text_lower: score += w
        
        if score >= 3:
            clips.append({
                'start': start, 'end': end, 'text': text[:80],
                'score': score, 'duration': ts_to_sec(end) - ts_to_sec(start)
            })
    
    # Sort and take top 5
    clips = sorted(clips, key=lambda x: x['score'], reverse=True)[:5]
    log(f"Found {len(clips)} clips")
    for i, c in enumerate(clips):
        log(f"  #{i+1}: score={c['score']} | {c['text'][:50]}...")
    return clips

def process_clip(video, srt, clip, i):
    log(f"Processing clip {i}...")
    naam = f"clip_{i}"
    
    # Cut
    raw = os.path.join(VIDEOS, f"{naam}_raw.mp4")
    log(f"Cutting: {clip['start']} -> {clip['end']}")
    if not run_cmd(["ffmpeg", "-y", "-i", video, "-ss", clip['start'], "-to", clip['end'], "-c", "copy", raw]):
        return None
    
    # Logo
    logo = os.path.join(TOOLS, "bassiehof-logo-transparent.png")
    branded = os.path.join(VIDEOS, f"{naam}_branded.mp4")
    
    if clip.get('duration', 0) < 90:
        filt = "[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920[main];[1:v]scale=200:-1[logo];[main][logo]overlay=20:20[v]"
    else:
        filt = "[1:v]scale=120:-1[logo];[0:v][logo]overlay=W-w-20:20[v]"
    
    if os.path.exists(logo):
        run_cmd(["ffmpeg", "-y", "-i", raw, "-i", logo, "-filter_complex", filt, "-map", "[v]", "-map", "0:a?", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "18", branded])
        return branded
    return raw

def main(video_path):
    log("="*50)
    log("BASSIEHOF PIPELINE v2")
    log("="*50)
    
    telegram_send("🚀 Pipeline gestart!")
    
    # Find SRT
    srt = find_srt(video_path)
    if not srt or not os.path.exists(srt):
        log("No SRT found!")
        telegram_send("❌ Geen SRT gevonden!")
        return
    
    log(f"Found SRT: {srt}")
    
    # Analyze
    clips = analyze_srt(srt)
    
    if not clips:
        log("No clips found!")
        return
    
    # Process
    for i, clip in enumerate(clips, 1):
        result = process_clip(video_path, srt, clip, i)
        if result:
            log(f"✅ Clip {i} done: {result}")
            telegram_send(f"✅ Clip {i} klaar!")
    
    log("DONE!")
    telegram_send("✅ Pipeline klaar!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video")
    args = parser.parse_args()
    if args.video:
        main(args.video)
    else:
        print("Usage: python3 vps_pipeline.py --video <path>")
