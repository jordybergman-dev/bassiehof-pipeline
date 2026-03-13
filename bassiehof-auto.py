#!/usr/bin/env python3
"""
Bassiehof Auto Pipeline - Slimme distributie
Max 3 long + 5 short per dag
Rest bewaren voor droge dagen
"""
import os, subprocess, time, ssl, urllib.request, json, pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# CONFIG
MAX_LONG = 3
MAX_SHORT = 5
BASSIEHOF = "/root/bassiehof-pipeline"
VIDEOS = os.path.join(BASSIEHOF, "Videos")
QUEUE_FILE = os.path.join(BASE, "upload_queue.json")
BASE = BASSIEHOF
DEBATDIRECT_API = "https://cdn.debatdirect.tweedekamer.nl/api"

# Viral keywords
VIRAL_KEYWORDS = {
    "woede":3,"boos":2,"schande":3,"belachelijk":2,"onacceptabel":3,"ramp":3,
    "migratie":2,"asiel":2,"discriminatie":2,"klimaat":2,"pensioen":2,
    "kabinet":1,"regering":1,"nooit":2,"niemand":2,"verraad":3,"klassejustitie":3
}

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

def get_agenda(datum=None):
    if not datum: datum = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"{DEBATDIRECT_API}/agenda/{datum}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("debates", [])
    except: return []

def ts_to_sec(ts):
    ts = ts.replace(',','.').replace(' ','')
    p = ts.split(':')
    return int(p[0])*3600 + int(p[1])*60 + float(p[2])

def find_srt(vp):
    base = os.path.splitext(vp)[0]
    for ext in ['.nl.srt', '.srt']:
        srt = base + ext
        if os.path.exists(srt): return srt
    return None

def analyze_srt(srt_path):
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
        
        duration = ts_to_sec(end) - ts_to_sec(start)
        score = 0
        tl = text.lower()
        for kw, w in VIRAL_KEYWORDS.items():
            if kw in tl: score += w
        
        if duration > 60 and len(text) > 200: score += 2
        if duration < 60 and score >= 2: score += 1
        
        if score >= 3:
            clips.append({
                'start': start, 'end': end, 'text': text[:100],
                'score': score, 'duration': duration,
                'type': 'short' if duration < 60 else 'long'
            })
    
    clips = sorted(clips, key=lambda x: x['score'], reverse=True)
    return clips[:15]  # Max 15 clips per debat

def load_queue():
    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except: return {"long": [], "short": []}

def save_queue(q):
    with open(QUEUE_FILE, 'w') as f:
        json.dump(q, f)

def create_clickbait_title(clip, is_short=False):
    """Maak pakkende titel"""
    text = clip['text'][:50]
    emotes = ["😱", "🔥", "💯", "👀", "⚡", "🚨"]
    emote = emotes[clip['score'] % len(emotes)]
    
    if is_short:
        return f"{emote} {text} #Shorts #Politiek"
    return f"{emote} {text} #Bassiehof #Politiek"

def process_clip(video, clip, i):
    naam = f"clip_{i}"
    raw = os.path.join(VIDEOS, f"{naam}.mp4")
    start = clip['start'].replace(',','.')
    end = clip['end'].replace(',','.')
    
    cmd = f'ffmpeg -y -i "{video}" -ss {start} -to {end} -c copy "{raw}"'
    subprocess.run(cmd, shell=True, capture_output=True)
    
    if os.path.exists(raw):
        return raw
    return None

# MAIN
def main():
    log("="*50)
    log("BASSIEHOF AUTO PIPELINE v2")
    log("="*50)
    
    today = datetime.now()
    weekday = today.weekday()
    
    # Check of het een debate dag is (di, wo, do)
    is_debat_dag = weekday in [1, 2, 3]
    
    queue = load_queue()
    
    if is_debat_dag:
        log("Debat dag! Nieuwe clips verwerken...")
        
        today_str = today.strftime("%Y-%m-%d")
        debates = get_agenda(today_str)
        
        long_count = 0
        short_count = 0
        
        for debat in debates:
            video_file = os.path.join(VIDEOS, f"debat_{today_str}.mp4")
            srt = find_srt(video_file)
            if not srt: continue
            
            clips = analyze_srt(srt)
            
            for i, clip in enumerate(clips, 1):
                if clip['type'] == 'long' and long_count >= MAX_LONG:
                    queue['long'].append(clip)  # Bewaren
                    continue
                if clip['type'] == 'short' and short_count >= MAX_SHORT:
                    queue['short'].append(clip)  # Bewaren
                    continue
                
                result = process_clip(video_file, clip, i)
                if result:
                    title = create_clickbait_title(clip, clip['type'] == 'short')
                    log(f"✅ {clip['type']}: {title[:40]}")
                    
                    if clip['type'] == 'long':
                        long_count += 1
                    else:
                        short_count += 1
        
        save_queue(queue)
        log(f"Dagelijks limiet: {long_count}/{MAX_LONG} long, {short_count}/{MAX_SHORT} short")
        log(f"Opgeslagen voor later: {len(queue['long'])} long, {len(queue['short'])} short")
    
    else:
        log("Geen debat dag - controleer queue...")
        
        # Upload 1 long en 2 short vanuit queue
        if queue['long']:
            clip = queue['long'].pop(0)
            log(f"📤 Upload long from queue: {clip['text'][:30]}")
        
        if len(queue['short']) >= 2:
            for _ in range(2):
                clip = queue['short'].pop(0)
                log(f"📤 Upload short from queue: {clip['text'][:30]}")
        
        save_queue(queue)
    
    log("DONE!")

if __name__ == "__main__":
    main()
