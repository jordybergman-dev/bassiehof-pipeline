#!/usr/bin/env python3
"""
Bassiehof VPS Pipeline
Volledig automatische pipeline voor de VPS:
- DebatDirect API check
- Video opname van streams
- AI viral analyse
- Video processing (logo, ondertitels)
- Thumbnail generatie
- YouTube upload
"""

import os
import sys
import json
import time
import ssl
import subprocess
import urllib.request
import urllib.parse
import re
from datetime import datetime, timedelta

# ============= CONFIG =============
BASSIEHOF = "/root/bassiehof"
VIDEOS = os.path.join(BASSIEHOF, "Videos")
TOOLS = os.path.join(BASSIEHOF, "tools")
LOGOS = os.path.join(BASSIEHOF, "logos")

# Telegram
TELEGRAM_BOT = os.environ.get("TELEGRAM_BOT")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT")

# YouTube
CLIENT_SECRETS = os.path.join(BASSIEHOF, "client_secret.json")

# DebatDirect API
DEBATDIRECT_API = "https://cdn.debatdirect.tweedekamer.nl/api"
STREAM_BASE = "https://livestreaming.b67buv2.tweedekamer.nl"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# Viral keywords
VIRAL_KEYWORDS = {
    "woede": 3, "boos": 2, "schande": 3, "belachelijk": 2, 
    "ondoordacht": 2, "ramp": 3, "onacceptabel": 3, "klassejustitie": 3,
    "asiel": 2, "migratie": 2, "discriminatie": 2, "klimaat": 2, 
    "pensioen": 2, "hypotheek": 2, "huur": 2, "kabinet": 1,
    "nooit": 2, "niemand": 2, "verraad": 3,
}

# ============= FUNCTIONS =============

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def telegram_send(msg):
    if not TELEGRAM_BOT:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "Markdown"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10, context=SSL_CTX):
            pass
    except Exception as e:
        log(f"Telegram error: {e}")


def get_agenda(datum=None):
    """Haal agenda op van DebatDirect API"""
    if not datum:
        datum = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    url = f"{DEBATDIRECT_API}/agenda/{datum}"
    log(f"📡 Agenda ophalen: {url}")
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
            data = json.loads(r.read())
            return data.get("debates", [])
    except Exception as e:
        log(f"Agenda error: {e}")
        return []


def download_stream(url, output_path, duration_sec=3600):
    """Download video van m3u8 stream met ffmpeg"""
    log(f"📹 Stream downloaden: {url}")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", url,
        "-t", str(duration_sec),
        "-c", "copy",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        log(f"✅ Download complete: {output_path}")
        return True
    else:
        log(f"❌ Download failed: {result.stderr[:200]}")
        return False


def find_subtitle(video_path):
    """Zoek bijbehorende SRT"""
    base = os.path.splitext(video_path)[0]
    for ext in ['.nl.srt', '.srt', '.vtt']:
        srt = base + ext
        if os.path.exists(srt):
            return srt
    return None


def calculate_viral_score(text):
    """Bereken viral score voor tekst"""
    score = 0
    text_lower = text.lower()
    
    for keyword, weight in VIRAL_KEYWORDS.items():
        if keyword in text_lower:
            score += weight
    
    if any(q in text_lower for q in ["waarom", "hoe", "wat", "wie", "?"]):
        score += 1
    
    if len(text) > 100:
        score += 1
    
    return min(score, 10)


def analyze_transcript(srt_path):
    """Analyseer transcript voor viral clips"""
    log("🤖 Transcript analyseren...")
    
    with open(srt_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    blocks = content.strip().split('\n\n')
    clips = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3 or '-->' not in lines[1]:
            continue
        
        parts = lines[1].split('-->')
        start, end = parts[0].strip(), parts[1].strip()
        text = ' '.join(lines[2:]).strip()
        
        if not text:
            continue
        
        score = calculate_viral_score(text)
        
        if score >= 3:
            clips.append({
                'start': start, 'end': end, 'text': text[:100],
                'score': score,
                'duration': timestamp_to_seconds(end) - timestamp_to_seconds(start)
            })
    
    # Merge nearby clips
    clips = merge_clips(clips)
    return sorted(clips, key=lambda x: x['score'], reverse=True)[:5]


def timestamp_to_seconds(ts):
    ts = ts.replace(',', '.').replace(' ', '')
    parts = ts.split(':')
    return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])


def merge_clips(clips, gap=10):
    if not clips:
        return []
    clips = sorted(clips, key=lambda x: timestamp_to_seconds(x['start']))
    merged = [clips[0]]
    for c in clips[1:]:
        last = merged[-1]
        if timestamp_to_seconds(c['start']) - timestamp_to_seconds(last['end']) < gap:
            last['end'] = c['end']
            last['text'] += " " + c['text']
            last['score'] = max(last['score'], c['score'])
        else:
            merged.append(c)
    return merged


def process_clip(video, srt, clip, index):
    """Verwerk 1 clip (knip, logo, ondertitels)"""
    naam = f"clip_{index}"
    start = clip['start']
    end = clip['end']
    
    raw = os.path.join(VIDEOS, f"{naam}_raw.mp4")
    branded = os.path.join(VIDEOS, f"{naam}_branded.mp4")
    
    # 1. Knippen
    log(f"✂️ Knippen: {start} → {end}")
    subprocess.run([
        "ffmpeg", "-y", "-i", video, "-ss", start, "-to", end,
        "-c", "copy", raw
    ], capture_output=True)
    
    # 2. Logo toevoegen
    log(f"🎨 Logo branden...")
    logo = os.path.join(TOOLS, "bassiehof-logo.png")
    
    # Bepaal formaat
    if clip.get('duration', 0) < 90:
        # Shorts formaat (9:16)
        filt = "[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920[main];[1:v]scale=200:-1[logo];[main][logo]overlay=20:20[v]"
    else:
        # YouTube formaat (16:9)
        filt = "[1:v]scale=120:-1[logo];[0:v][logo]overlay=W-w-20:20[v]"
    
    subprocess.run([
        "ffmpeg", "-y", "-i", raw, "-i", logo,
        "-filter_complex", filt, "-map", "[v]", "-map", "0:a?",
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        branded
    ], capture_output=True)
    
    # 3. Ondertitels
    if srt and os.path.exists(srt):
        log(f"📝 Ondertitels genereren...")
        ass_file = os.path.join(VIDEOS, f"{naam}.ass")
        # Hier subtitels.py aanroepen
        subprocess.run([
            "python3", os.path.join(TOOLS, "subtitels.py"),
            branded, srt, "--stijl", "karaoke"
        ], capture_output=True)
    
    return branded


def generate_thumbnail(title, politicians):
    """Genereer thumbnail met politicus foto's"""
    log(f"🖼️ Thumbnail genereren: {title}")
    
    # Haal foto's op via Tweede Kamer API
    for politicus in politicians[:3]:
        # Download foto van TK API
        foto_url = f"https://www.tweedekamer.nl/api/persoonsfoto?id={politicus['id']}"
        # ... download en verwerk
    
    return None


def upload_youtube(video_path, title, description, tags, privacy="unlisted", is_short=False):
    """Upload naar YouTube"""
    log(f"⬆️ YouTube uploaden: {title}")
    
    # YouTube upload logic hier
    # (gebruik google-api-python-client)
    
    return True


# ============= MAIN =============

def run_pipeline(video_path=None, video_url=None, dry_run=False):
    log("=" * 50)
    log("🚀 BASSIEHOF VPS PIPELINE START")
    log("=" * 50)
    
    telegram_send("🚀 *Pipeline gestart!*")
    
    # Stap 1: Video ophalen
    if video_url:
        # Download van stream
        output = os.path.join(VIDEOS, f"debat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        if download_stream(video_url, output):
            video_path = output
    elif not video_path:
        log("❌ Geen video of URL opgegeven!")
        return
    
    # Stap 2: SRT zoeken
    srt_path = find_subtitle(video_path)
    
    if srt_path and os.path.exists(srt_path):
        log(f"📄 SRT gevonden: {srt_path}")
        
        # Stap 3: AI Analyse
        clips = analyze_transcript(srt_path)
        
        if not clips:
            log("⚠️ Geen viral clips gevonden")
            return
        
        log(f"🤖 {len(clips)} clips gevonden:")
        for i, c in enumerate(clips):
            log(f"  #{i+1}: score={c['score']} | {c['text'][:50]}...")
        
        telegram_send(f"🤖 *Analyse compleet!* {len(clips)} clips gevonden.")
        
        if dry_run:
            log("🔍 Dry-run modus - geen processing")
            return
        
        # Stap 4: Verwerk clips
        for i, clip in enumerate(clips, 1):
            log(f"\n📹 Verwerken clip {i}/{len(clips)}")
            
            processed = process_clip(video_path, srt_path, clip, i)
            
            # Stap 5: Thumbnail
            thumbnail = generate_thumbnail(clip['text'][:50], [])
            
            # Stap 6: YouTube upload
            title = f"🔥 {clip['text'][:60]}..."
            if clip.get('duration', 0) < 60:
                title += " #Shorts"
            
            upload_youtube(processed, title, "Bassiehof", ["politiek", "nederland"], is_short=(clip.get('duration', 0) < 60))
            
            telegram_send(f"✅ Clip {i} uploaded: {title}")
    
    log("=" * 50)
    log("✅ PIPELINE COMPLETE")
    log("=" * 50)


def check_schedule():
    """CheckDebatDirect agenda en plan opnames"""
    log("📅 DebatDirect agenda check...")
    
    debates = get_agenda()
    
    if not debates:
        log("Geen debatten gevonden")
        telegram_send("📅 Geen debatten morgen")
        return
    
    bericht = "📅 Debatten morgen:\n"
    for debat in debates:
        start = datetime.fromisoformat(debat['startsAt'].replace('Z', '+00:00'))
        bericht += f"  ⏰ {start.strftime('%H:%M')} — {debat['title']}\n"
    
    telegram_send(bericht)
    return debates


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Bassiehof VPS Pipeline")
    parser.add_argument("--video", help="Lokale video")
    parser.add_argument("--url", help="Stream URL")
    parser.add_argument("--schedule", action="store_true", help="Check agenda")
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    if args.schedule:
        check_schedule()
    else:
        run_pipeline(video_path=args.video, video_url=args.url, dry_run=args.dry_run)
