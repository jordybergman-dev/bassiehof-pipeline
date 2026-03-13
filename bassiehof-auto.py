#!/usr/bin/env python3
"""
Bassiehof Auto Pipeline - met slimme clip detectie
"""
import os, subprocess, time, ssl, urllib.request, urllib.parse, json, pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# CONFIG
BASSIEHOF = "/root/bassiehof-pipeline"
VIDEOS = os.path.join(BASSIEHOF, "Videos")
BASE = BASSIEHOF
DEBATDIRECT_API = "https://cdn.debatdirect.tweedekamer.nl/api"
TELEGRAM_BOT = os.environ.get("TELEGRAM_BOT")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT")
CLIENT_SECRETS = os.path.join(BASE, "client_secret.json")
TOKEN_FILE = os.path.join(BASE, "youtube_token.pkl")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Viral keywords
VIRAL_KEYWORDS = {
    "woede":3,"boos":2,"schande":3,"belachelijk":2,"onacceptabel":3,"ramp":3,
    "migratie":2,"asiel":2,"discriminatie":2,"klimaat":2,"pensioen":2,
    "kabinet":1,"regering":1,"nooit":2,"niemand":2,"verraad":3,"klassejustitie":3
}

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

def telegram(m):
    if not TELEGRAM_BOT: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT, "text": m}).encode()
    try: urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
    except: pass

def run_cmd(cmd):
    log(f"CMD: {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"ERR: {r.stderr[:100]}")
        return False
    return True

def ts_to_sec(ts):
    ts = ts.replace(',','.').replace(' ','')
    p = ts.split(':')
    return int(p[0])*3600 + int(p[1])*60 + float(p[2])

def get_agenda(datum=None):
    if not datum: datum = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"{DEBATDIRECT_API}/agenda/{datum}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("debates", [])
    except: return []

def find_srt(vp):
    base = os.path.splitext(vp)[0]
    for ext in ['.nl.srt', '.srt']:
        srt = base + ext
        if os.path.exists(srt): return srt
    return None

def analyze_srt(srt_path):
    """Analyseer transcript voor viral clips - shorts EN longs"""
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
        
        # Bereken duration
        duration = ts_to_sec(end) - ts_to_sec(start)
        
        # Viral score
        score = 0
        tl = text.lower()
        for kw, w in VIRAL_KEYWORDS.items():
            if kw in tl: score += w
        
        # Lange speeches = interrupties = goed voor long video
        if duration > 60 and len(text) > 200:
            score += 2  # Bonus voor lange speeches
        
        # Korte impactvolle momenten = shorts
        if duration < 60 and score >= 2:
            score += 1
        
        if score >= 3:
            clips.append({
                'start': start, 'end': end, 'text': text[:100],
                'score': score, 'duration': duration,
                'type': 'short' if duration < 60 else 'long'
            })
    
    # Merge nearby clips
    clips = sorted(clips, key=lambda x: ts_to_sec(x['start']))
    merged = []
    for c in clips:
        if merged and ts_to_sec(c['start']) - ts_to_sec(merged[-1]['end']) < 10:
            merged[-1]['end'] = c['end']
            merged[-1]['text'] += " " + c['text']
            merged[-1]['duration'] = ts_to_sec(merged[-1]['end']) - ts_to_sec(merged[-1]['start'])
            merged[-1]['score'] = max(merged[-1]['score'], c['score'])
        else:
            merged.append(c)
    
    # Sort by score
    return sorted(merged, key=lambda x: x['score'], reverse=True)[:5]

def process_clip(video, clip, i):
    naam = f"clip_{i}"
    raw = os.path.join(VIDEOS, f"{naam}.mp4")
    start = clip['start'].replace(',','.')
    end = clip['end'].replace(',','.')
    
    cmd = f'ffmpeg -y -i "{video}" -ss {start} -to {end} -c copy "{raw}"'
    if run_cmd(cmd):
        return raw
    return None

def upload_youtube(video_path, title, is_short=False):
    import google.auth
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid: return False
    
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": title, "description": "#bassiehof #politiek #tweedekamer", "categoryId": "25"},
        "status": {"privacyStatus": "unlisted"}
    }
    media = MediaFileUpload(video_path, resumable=True)
    yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    log(f"Uploaded: {title}")
    return True

def upload_drive(filename):
    cmd = f'rclone copy "{VIDEOS}/{filename}" "gdrive videos:/videos/"'
    run_cmd(cmd)

# MAIN
def main():
    log("="*50)
    log("BASSIEHOF AUTO PIPELINE")
    log("="*50)
    
    telegram("🚀 Pipeline gestart!")
    
    # Check today
    today = datetime.now().strftime("%Y-%m-%d")
    debates = get_agenda(today)
    
    if not debates:
        log("Geen debatten vandaag")
        telegram("📅 Geen debatten vandaag")
        return
    
    for debat in debates:
        name = debat.get('name', 'Onbekend')
        log(f"Debat: {name}")
        
        # Download
        video_file = os.path.join(VIDEOS, f"debat_{today}.mp4")
        if not os.path.exists(video_file):
            stream = f"https://livestreaming.b67buv2.tweedekamer.nl/{today}/{debat.get('locationId','plenairezaal')}/stream_05/prog_index.m3u8"
            log(f"Downloading: {stream}")
            if run_cmd(f"ffmpeg -y -i {stream} -t 7200 -c copy {video_file}"):
                telegram("📥 Video gedownload!")
        
        # Analyze
        srt = find_srt(video_file)
        if not srt: continue
        
        clips = analyze_srt(srt)
        log(f"Gevonden: {len(clips)} clips")
        
        telegram(f"🤖 {len(clips)} clips gevonden!")
        
        for i, clip in enumerate(clips, 1):
            result = process_clip(video_file, clip, i)
            if result:
                is_short = clip['type'] == 'short'
                title = f"🔥 {clip['text'][:50]}"
                if is_short: title += " #Shorts"
                
                upload_youtube(result, title, is_short)
                upload_drive(os.path.basename(result))
                
                telegram(f"✅ Clip {i} ({clip['type']}): {title[:30]}...")
    
    telegram("✅ Pipeline klaar!")
    log("DONE!")

if __name__ == "__main__":
    main()
