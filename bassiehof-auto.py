#!/usr/bin/env python3
"""
Bassiehof Auto Pipeline - Analytics Optimized
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

# Load viral keywords
VIRAL_KEYWORDS = {
    "woede":5,"boos":4,"schande":5,"belachelijk":3,"onacceptabel":5,"ramp":4,
    "migratie":3,"asiel":3,"discriminatie":4,"klimaat":3,"pensioen":3,
    "kabinet":2,"regering":2,"nooit":3,"niemand":3,"verraad":5,"klassejustitie":5,
    "hakken":5,"sodemieter":5,"weg":3,"wegvaagd":4,"af":3,"kapot":4,
    "corruptie":5,"schandaal":5,"leugens":4,"bedrog":5,"fake":4,
    "politie":3,"justitie":3,"rechtsstaat":4,"democratie":3
}

# Priority politicans - based on analytics
PRIORITY_POLITICIANS = [
    "Geert Wilders", "Florian", "Agema", "Gidi Markuszower",
    "Dion Graus", "Martin Bosma", "Marjolein Faber", "Mona Keijzer",
    "Caroline van der Plas", "Kati Piri", "Jan Paternotte", "Jesse Klaver",
    "Stephan van Baarle", "Gideon van Meijeren", "Esther Ouwehand", "Lidewij de Vos"
]
POLITICIAN_BONUS = 5

# SEO
SEO_TAGS = ["bassiehof", "politiek", "tweedekamer", "nederland", "nieuws",
            "wilders", "pvv", "bbb", "debattle", "kamerdebat", "actueel", "viral"]

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

def get_agenda_with_meta(datum=None):
    if not datum: datum = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"{DEBATDIRECT_API}/agenda/{datum}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("debates", [])
    except: return []

def create_seo_description(debat_meta, clip_text):
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
    """Analytics-optimized clip detection"""
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
        
        # Viral keywords (analytics-based)
        for kw, w in VIRAL_KEYWORDS.items():
            if kw in tl: score += w
        
        # Priority politicians (PVV dominates)
        for p in PRIORITY_POLITICIANS:
            if p.lower() in tl: score += POLITICIAN_BONUS
        
        # Duration bonuses (short clips work best)
        if duration < 60 and duration > 30: score += 3  # Optimal shorts
        if duration > 60 and duration < 300: score += 2  # Good long
        
        if score >= 10:  # Higher threshold for quality
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
    text = clip['text'][:50]
    if is_short:
        return f"🔥 {text} #Shorts"
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

# MAIN
def main():
    log("="*50)
    log_event("agenda_checked", {})
    log("BASSIEHOF PIPELINE v4 - ANALYTICS OPTIMIZED")
    log("="*50)
    log_event("agenda_checked", {})
    
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

# Telegram notifications
import os

TELEGRAM_BOT = "8767320369:AAFwGKv5QIUH3t2jueTuTWSh5hGDTdu8CRM"
TELEGRAM_CHAT = "1523587806"

def telegram(msg):
    """Stuur Telegram bericht"""
    import urllib.request, urllib.parse
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT, "text": msg}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
    except:
        pass

def log_event(event_type, details):
    """Log event en stuur Telegram"""
    events = {
        "agenda_checked": "📅 DebatDirect agenda gechecked",
        "debate_started": "🎬 Debat gestart met opnemen",
        "clips_created": "✂️ {count} clips gemaakt",
        "uploaded": "📤 Video geüpload naar YouTube",
        "error": "❌ Fout: {error}"
    }
    
    msg = events.get(event_type, event_type).format(**details)
    log(msg)
    telegram(msg)
