#!/usr/bin/env python3
"""
Bassiehof Auto Pipeline - Complete
"""
import os, subprocess, urllib.request, json, pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# CONFIG
MAX_LONG = 3
MAX_SHORT = 5
BASSIEHOF = "/root/bassiehof-pipeline"
VIDEOS = os.path.join(BASSIEHOF, "Videos")
QUEUE_FILE = os.path.join(BASSIEHOF, "upload_queue.json")
BASE = BASSIEHOF
DEBATDIRECT_API = "https://cdn.debatdirect.tweedekamer.nl/api"

# SEO
SEO_TAGS = ["bassiehof", "politiek", "tweedekamer", "nederland", "nieuws",
            "wilders", "pvv", "debattle", "kamerdebat", "actueel"]

VIRAL_KEYWORDS = {
    "woede":3,"boos":2,"schande":3,"belachelijk":2,"onacceptabel":3,"ramp":3,
    "migratie":2,"asiel":2,"discriminatie":2,"klimaat":2,"pensioen":2,
    "kabinet":1,"regering":1,"nooit":2,"niemand":2,"verraad":3,"klassejustitie":3
}

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

def get_agenda_with_meta(datum=None):
    """Haal agenda MET metadata"""
    if not datum: datum = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"{DEBATDIRECT_API}/agenda/{datum}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("debates", [])
    except: return []

def create_seo_description(debat_meta, clip_text):
    """Maak SEO beschrijving voor long video"""
    title = debat_meta.get("name", "Debat")
    category = debat_meta.get("categoryNames", ["Politiek"])[0]
    debate_type = debat_meta.get("debateType", "Debat")
    location = debat_meta.get("locationName", "Tweede Kamer")
    
    desc = f"""🔥 {title}

📌 Over dit debat:
• Type: {debate_type}
• Categorie: {category}
• Locatie: {location}

💬 In deze clip:
{clip_text[:200]}

🔔 Abonneer voor meer politieke clips!

#bassiehof #{category.lower().replace(' ','')} #politiek #tweedekamer #nederland #nieuws"""
    
    return desc

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
    return clips[:15]

def load_queue():
    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except: return {"long": [], "short": []}

def save_queue(q):
    with open(QUEUE_FILE, 'w') as f:
        json.dump(q, f)

def create_title(clip, is_short=False):
    emotes = ["😱", "🔥", "💯", "👀", "⚡", "🚨"]
    emote = emotes[clip['score'] % len(emotes)]
    text = clip['text'][:50]
    
    if is_short:
        return f"{emote} {text} #Shorts"
    return f"🔥 {text}"

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

# YouTube upload
TOKEN_FILE = os.path.join(BASE, "youtube_token.pkl")

def get_yt():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if creds and creds.valid:
        return build("youtube", "v3", credentials=creds)
    return None

def upload_youtube(video_path, title, description, is_short=False):
    yt = get_yt()
    if not yt: return False
    
    tags = SEO_TAGS.copy()
    if is_short: tags.extend(["shorts", "ytshorts"])
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "25"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    
    media = MediaFileUpload(video_path, resumable=True)
    yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    return True

# MAIN
def main():
    log("="*50)
    log("BASSIEHOF PIPELINE v3")
    log("="*50)
    
    today = datetime.now()
    is_debat_dag = today.weekday() in [1, 2, 3]
    queue = load_queue()
    
    if is_debat_dag:
        today_str = today.strftime("%Y-%m-%d")
        debates = get_agenda_with_meta(today_str)
        
        long_count = 0
        short_count = 0
        
        for debat in debates:
            video_file = os.path.join(VIDEOS, f"debat_{today_str}.mp4")
            srt = find_srt(video_file)
            if not srt: continue
            
            clips = analyze_srt(srt)
            
            for i, clip in enumerate(clips, 1):
                if clip['type'] == 'long' and long_count >= MAX_LONG:
                    queue['long'].append({'clip': clip, 'meta': debat})
                    continue
                if clip['type'] == 'short' and short_count >= MAX_SHORT:
                    queue['short'].append({'clip': clip, 'meta': debat})
                    continue
                
                result = process_clip(video_file, clip, i)
                if result:
                    title = create_title(clip, clip['type'] == 'short')
                    
                    # Beschrijving voor long videos
                    if clip['type'] == 'long':
                        desc = create_seo_description(debat, clip['text'])
                    else:
                        desc = f"#{clip['text'][:50]} #Shorts #Bassiehof"
                    
                    log(f"✅ {clip['type']}: {title[:40]}")
                    
                    if clip['type'] == 'long':
                        long_count += 1
                    else:
                        short_count += 1
        
        save_queue(queue)
        log(f"Long: {long_count}/{MAX_LONG}, Short: {short_count}/{MAX_SHORT}")
    
    log("DONE!")

if __name__ == "__main__":
    main()
