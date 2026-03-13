#!/usr/bin/env python3
"""
Pipeline Orchestrator - Bassiehof Video Pipeline
Automates: download → AI analyze → process → upload
Verbeterd met beste features uit originele verwerk.py
"""

import os
import sys
import json
import argparse
import subprocess
import urllib.request
import ssl
import re
import time
from datetime import datetime

# Configuration
BASSIEHOF = os.environ.get("PIPELINE_BASSIEHOF", r"C:\Users\jordy\Documents\Bassiehof")
TOOLS = os.path.join(BASSIEHOF, "Tools")
VIDEOS = os.path.join(BASSIEHOF, "Videos")
YT_DLP = os.environ.get("PIPELINE_YT_DLP", "python")
FFMPEG = os.environ.get("PIPELINE_FFMPEG", "ffmpeg")

# Telegram config
TELEGRAM_BOT = os.environ.get("TELEGRAM_BOT")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# Viral keywords for Dutch political content
VIRAL_KEYWORDS = {
    "woede": 3, "boos": 2, "schande": 3, "belachelijk": 2, 
    "ondoordacht": 2, "ramp": 3, "fantastisch": 2, "onacceptabel": 3,
    "klassejustitie": 3, "gek": 2, "verraad": 3,
    "asiel": 2, "migratie": 2, "discriminatie": 2,
    "klimaat": 2, "pensioen": 2, "hypotheek": 2, "huur": 2,
    "kabinet": 1, "regering": 1, "minister": 1, "staatssecretaris": 1,
    "dit kabinet": 2, "volgende week": 2, "nooit": 2, "altijd": 2,
    "niemand": 2, "iedereen": 1, "allemaal": 1,
}

QUESTION_WORDS = ["waarom", "hoe", "wat", "wie", "wanneer", "?"]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def telegram_send(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "Markdown"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10, context=SSL_CTX):
            pass
    except Exception as e:
        log(f"Telegram error: {e}")


def telegram_send_file(filepath, caption=""):
    import uuid
    boundary = uuid.uuid4().hex
    with open(filepath, "rb") as f:
        file_data = f.read()
    filename = os.path.basename(filepath)
    parts = []
    for k, v in {"chat_id": TELEGRAM_CHAT, "caption": caption}.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
    parts.append(file_data)
    parts.append(f'\r\n--{boundary}--\r\n'.encode())
    body = b''.join(parts)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendDocument"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX):
            pass
    except Exception as e:
        log(f"Telegram upload error: {e}")


def wacht_op_goedkeuring(timeout_min=30):
    """Wacht op goedkeuring van gebruiker via Telegram"""
    log(f"Wachten op goedkeuring (max {timeout_min} min)...")
    
    last_update = 0
    deadline = time.time() + timeout_min * 60
    
    while time.time() < deadline:
        try:
            res = tg("getUpdates", offset=last_update+1, timeout=20)
            updates = res.get("result", [])
            for upd in updates:
                last_update = upd["update_id"]
                msg = upd.get("message", {})
                tekst = msg.get("text", "").lower().strip()
                
                if tekst == "upload":
                    log("✅ Goedkeuring ontvangen!")
                    return True
                elif tekst == "stop":
                    log("⏹ Pipeline gestopt door gebruiker")
                    return False
        except Exception as e:
            log(f"Poll fout: {e}")
        time.sleep(3)
    
    return False


def tg(method, **kwargs):
    """Telegram API helper"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/{method}"
    data = urllib.parse.urlencode(kwargs).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
        return json.loads(r.read())


def run_cmd(cmd, cwd=None, shell=False):
    log(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"Error: {result.stderr[:200]}")
        return False
    return True


def download_video(url, output_path=None):
    log(f"Downloading: {url}")
    if not output_path:
        output_path = os.path.join(VIDEOS, "%(title)s.%(ext)s")
    cmd = [YT_DLP, "--write-subs", "--write-auto-subs", "--sub-lang", "nl", "-o", output_path, url]
    if run_cmd(cmd):
        log("Download complete!")
        return True
    return False


def calculate_viral_score(text):
    score = 0
    text_lower = text.lower()
    for keyword, weight in VIRAL_KEYWORDS.items():
        if keyword in text_lower:
            score += weight
    if any(q in text_lower for q in QUESTION_WORDS):
        score += 1
    allcaps_words = [w for w in text.split() if w.isupper() and len(w) > 2]
    score += len(allcaps_words) * 0.5
    if len(text) > 100:
        score += 1
    if len(text) > 200:
        score += 1
    if any(text.rstrip().endswith(x) for x in '.!?'):
        score += 0.5
    return min(score, 10)


def timestamp_to_seconds(ts):
    ts = ts.replace(',', '.').replace(' ', '')
    parts = ts.split(':')
    return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])


def seconds_to_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')


def merge_nearby_clips(clips, merge_gap=10):
    if not clips:
        return []
    clips = sorted(clips, key=lambda x: timestamp_to_seconds(x['start']))
    merged = [clips[0]]
    for clip in clips[1:]:
        last = merged[-1]
        current_start = timestamp_to_seconds(clip['start'])
        last_end = timestamp_to_seconds(last['end'])
        if current_start - last_end < merge_gap:
            last['end'] = clip['end']
            last['text'] = last['text'] + " " + clip['text']
            last['viral_score'] = max(last['viral_score'], clip['viral_score'])
            last['duration'] = timestamp_to_seconds(last['end']) - timestamp_to_seconds(last['start'])
        else:
            merged.append(clip)
    return merged


def analyze_transcript_ai(srt_path):
    log("🤖 AI Analysis: Scoring clips for viral potential...")
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
        viral_score = calculate_viral_score(text)
        if viral_score >= 3:
            clips.append({'start': start, 'end': end, 'text': text[:100], 'viral_score': viral_score,
                         'duration': timestamp_to_seconds(end) - timestamp_to_seconds(start)})
    clips = merge_nearby_clips(clips, merge_gap=10)
    top_clips = sorted(clips, key=lambda x: x.get('viral_score', 0), reverse=True)[:5]
    log(f"🤖 AI found {len(top_clips)} high-potential clips:")
    log("=" * 50)
    for i, clip in enumerate(top_clips):
        duration = clip.get('duration', 0)
        log(f"📹 Clip #{i+1}")
        log(f"   Score: ⭐ {clip['viral_score']:.1f}/10")
        log(f"   Duration: {duration:.0f} seconds")
        log(f"   Time: {clip['start']} → {clip['end']}")
        log(f"   Text: {clip['text'][:80]}...")
        log("-" * 40)
    return top_clips


def generate_instructions(clips, video_title="Video", output_path=None):
    if not output_path:
        output_path = os.path.join(TOOLS, "instructies.json")
    instructions = {"clips": []}
    for i, clip in enumerate(clips):
        duration = clip.get('duration', 60)
        clip_format = "short" if duration < 90 else "youtube"
        title = generate_clip_title(clip['text'], clip['viral_score'], i+1)
        instructions["clips"].append({
            "naam": f"clip_{i+1}_{clip['text'][:20].replace(' ', '_')}",
            "start": clip['start'], "eind": clip['end'], "formaat": clip_format,
            "titel": title, "viral_score": round(clip['viral_score'], 1)
        })
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(instructions, f, indent=2)
    log(f"📋 Generated instructions: {output_path}")
    return output_path


def generate_clip_title(text, score, index):
    key_phrase = text[:60].strip() + ("..." if len(text) > 60 else "")
    emoji = "😤" if score >= 7 else ("🤔" if score >= 5 else "💡")
    title = f"{emoji} {key_phrase}"
    if len(text) < 50:
        title += " #Shorts"
    return title


# ===== VERWERK.PY FUNCTIONALITY =====

def snij_srt(srt_pad, start_str, eind_str, uitvoer):
    def ts(t):
        t = t.replace(',', '.').replace(' ', '')
        p = t.split(':')
        return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
    def fmt(s):
        s = max(0, s)
        h = int(s // 3600)
        s %= 3600
        m = int(s // 60)
        s %= 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')
    clip_s, clip_e = ts(start_str), ts(eind_str)
    tekst = open(srt_pad, encoding='utf-8', errors='ignore').read()
    blokken = re.split(r'\n\n+', tekst.strip())
    out, idx = [], 1
    for b in blokken:
        regels = b.strip().split('\n')
        if len(regels) < 3:
            continue
        m = re.match(r'(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)', regels[1])
        if not m:
            continue
        s = ts(regels[1].split('-->')[0].strip())
        e = ts(regels[1].split('-->')[1].strip())
        if e > clip_s and s < clip_e:
            out.append(f"{idx}\n{fmt(s - clip_s)} --> {fmt(e - clip_s)}\n{chr(10).join(regels[2:])}\n")
            idx += 1
    open(uitvoer, 'w', encoding='utf-8').write('\n'.join(out))


def snap_naar_srt_grens(srt_pad, eind_sec, marge_sec=8):
    if not srt_pad or not os.path.isfile(srt_pad):
        return eind_sec
    def ts(t):
        t = t.replace(",", ".").replace(' ', '')
        p = t.split(":")
        return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
    tekst = open(srt_pad, encoding="utf-8", errors="ignore").read()
    blokken = re.split(r"\n\n+", tekst.strip())
    eind_tijden = []
    for b in blokken:
        regels = b.strip().split("\n")
        if len(regels) < 3:
            continue
        m = re.match(r"(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)", regels[1])
        if not m:
            continue
        e = ts(regels[1].split("-->")[1].strip())
        zin = " ".join(regels[2:])
        is_afsluiting = zin.rstrip().endswith((".", "!", "?", "..."))
        eind_tijden.append((e, is_afsluiting))
    beste = None
    for (e, is_af) in eind_tijden:
        if abs(e - eind_sec) <= marge_sec:
            if beste is None:
                beste = (e, is_af)
            elif is_af and not beste[1]:
                beste = (e, is_af)
            elif is_af == beste[1] and abs(e - eind_sec) < abs(beste[0] - eind_sec):
                beste = (e, is_af)
    if beste:
        log(f"  Eindtijd aangepast: {eind_sec:.1f}s → {beste[0]:.1f}s (zin af: {beste[1]})")
        return beste[0]
    return eind_sec


def process_clip(video, srt, clip, index):
    naam = clip.get("naam", f"clip{index}").replace(" ", "_")
    start, eind = clip.get("start", "00:00:00"), clip.get("eind", "00:01:00")
    formaat = clip.get("formaat", "short")
    titel = clip.get("titel", f"Clip {index}")
    privacy = clip.get("privacy", "unlisted")
    os.makedirs(VIDEOS, exist_ok=True)
    raw, brand, final = os.path.join(VIDEOS, f"{naam}_raw.mp4"), os.path.join(VIDEOS, f"{naam}_branded.mp4"), os.path.join(VIDEOS, f"{naam}_final.mp4")
    telegram_send(f"⚙️ Clip {index}: {naam} ({start}→{eind}) [{formaat}]")
    
    # 1. Knippen met sentence snapping
    log(f"\n[{index}] Knippen: {start} -> {eind}")
    if srt and os.path.isfile(srt):
        clip_srt = os.path.join(VIDEOS, f"{naam}_clip.srt")
        snij_srt(srt, start, eind, clip_srt)
        eind_sec = snap_naar_srt_grens(clip_srt, timestamp_to_seconds(eind), marge_sec=10)
        eind = seconds_to_timestamp(eind_sec).replace('.', ',')
    if not run_cmd([FFMPEG, "-y", "-i", video, "-ss", start, "-to", eind, "-c", "copy", raw]):
        telegram_send(f"❌ Clip {index} knippen mislukt")
        return
    
    # 2. Branden (logo)
    log(f"[{index}] Branden ({formaat})...")
    logo = os.path.join(TOOLS, "bassiehof-logo-transparent.png")
    outro = os.path.join(BASSIEHOF, "Bassie_hof_Politiek.mp4")
    if formaat == "short":
        filt = "[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920[main];[1:v]scale=200:-1[logo];[main][logo]overlay=20:20[v]"
        ok = run_cmd([FFMPEG, "-y", "-i", raw, "-i", logo, "-filter_complex", filt, "-map", "[v]", "-map", "0:a?", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "18", brand])
    else:
        filt = "[1:v]scale=120:-1[logo];[0:v][logo]overlay=W-w-20:20[main];[2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[outro];[main][outro]concat=n=2:v=1[v]"
        ok = run_cmd([FFMPEG, "-y", "-i", raw, "-i", logo, "-i", outro, "-filter_complex", filt, "-map", "[v]", "-map", "0:a?", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "18", brand])
    if not ok:
        telegram_send(f"❌ Clip {index} branden mislukt")
        return
    
    # 3. Ondertitels
    final_pad = brand
    if srt and os.path.isfile(srt):
        log(f"[{index}] Ondertitels...")
        sub_format = "shorts" if formaat == "short" else "youtube"
        clip_srt = os.path.join(VIDEOS, f"{naam}.srt")
        snij_srt(srt, start, eind, clip_srt)
        ass_pad = os.path.join(VIDEOS, f"{naam}_karaoke_{sub_format}.ass")
        subprocess.run(["py", os.path.join(TOOLS, "subtitels.py"), brand, clip_srt, "--stijl", "karaoke", "--formaat", sub_format, "--alleen-ass"])
        if os.path.isfile(ass_pad):
            ass_esc = ass_pad.replace('\\', '/').replace(':', '\\:')
            if run_cmd([FFMPEG, "-y", "-i", brand, "-vf", f"ass='{ass_esc}'", "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", final]):
                final_pad = final
    
    # 4. Uploaden
    log(f"[{index}] Uploaden: {titel}")
    upload_args = ["py", os.path.join(TOOLS, "youtube_upload.py"), "--file", final_pad, "--title", titel, "--privacy", privacy]
    if formaat == "short":
        upload_args.append("--shorts")
    subprocess.run(upload_args)
    telegram_send(f"✅ Clip {index} klaar: {titel}")


def run_pipeline(video_url=None, actual_video=None, dry_run=False):
    log("=" * 50)
    log("🚀 BASSIEHOF PIPELINE STARTING")
    log("=" * 50)
    telegram_send("🚀 *Pipeline gestart!*")
    
    # Stage 1: Handle video (local or URL)
    actual_video = None
    
    # Check if video_url is actually a local file
    if video_url and os.path.isfile(video_url):
        actual_video = video_url
        log(f"📁 Local video: {actual_video}")
    elif video_url:
        # It's a URL, download it
        if not download_video(video_url):
            log("❌ Download failed!")
            telegram_send("❌ *Download mislukt!*")
            return False
        # Find the downloaded file
        for f in os.listdir(VIDEOS):
            if f.endswith(('.mp4', '.mkv', '.webm')):
                actual_video = os.path.join(VIDEOS, f)
                break
        if not actual_video:
            log("❌ No video specified!")
            return False
    
    # Stage 2: Find SRT
    srt_path = None
    if actual_video:
        base = os.path.splitext(actual_video)[0]
        for ext in ['.nl.srt', '.srt', '.vtt']:
            candidate = base + ext
            if os.path.exists(candidate):
                srt_path = candidate
                break
    if not srt_path:
        for f in os.listdir(VIDEOS):
            if f.endswith('.srt'):
                srt_path = os.path.join(VIDEOS, f)
                break
    
    # Stage 3: AI Analysis
    if srt_path and os.path.exists(srt_path):
        log(f"📄 Found SRT: {srt_path}")
        clips = analyze_transcript_ai(srt_path)
        
        if not dry_run:
            # Stuur analyse naar Telegram voor goedkeuring
            telegram_send(f"🤖 *AI Analyse voltooid!* {len(clips)} potentiële clips gevonden:\n")
            for i, clip in enumerate(clips, 1):
                telegram_send(f"{i}. {clip['text'][:80]}...\n📊 Score: {clip['viral_score']:.1f}")
            
            telegram_send("⏳ *Wacht op jouw goedkeuring...*\n\nStuur 'upload' om door te gaan of 'stop' om te annuleren.")
            
            # Wacht op goedkeuring via Telegram polling
            goedkeuring = wacht_op_goedkeuring(timeout_min=30)
            
            if not goedkeuring:
                telegram_send("❌ Geen goedkeuring. Pipeline gestopt.")
                return False
            
            # Generate instructions
            generate_instructions(clips, os.path.basename(actual_video) if actual_video else "Video")
            
            # Process clips
            if actual_video and os.path.exists(actual_video):
                for i, clip in enumerate(clips, 1):
                    process_clip(actual_video, srt_path, clip, i)
        else:
            log("🔍 Dry-run - skipping processing")
    else:
        log("⚠️ No SRT found - skipping AI analysis")
    
    log("=" * 50)
    log("✅ PIPELINE COMPLETE")
    log("=" * 50)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bassiehof Pipeline Orchestrator v2")
    parser.add_argument("--video", help="Video URL or path")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, don't process")
    parser.add_argument("--process-only", help="Process existing video")
    args = parser.parse_args()
    
    if args.process_only:
        srt_path = args.process_only.replace('.mp4', '.srt')
        clips = [{"start": "00:00:00", "eind": "00:01:00", "formaat": "short", "titel": "Test"}]
        process_clip(args.process_only, srt_path if os.path.exists(srt_path) else None, clips[0], 1)
    else:
        run_pipeline(video_url=args.video, dry_run=args.dry_run)
