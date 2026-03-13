import os
# verwerk.py - Bassiehof Auto-Clip Verwerker
# Wacht op Skordie's clip-instructies via Telegram en voert ze automatisch uit
# Gebruik: py verwerk.py "debat.mp4" "debat.srt"
# Dan stuurt Skordie via Telegram de clip-instructies en dit script voert ze uit

import sys, os, json, time, subprocess, re, ssl, urllib.request, urllib.parse, pickle, io

BOT_TOKEN = os.environ.get("TELEGRAM_BOT")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT")
FFMPEG    = r"C:\Users\jordy\Downloads\yt-dlp-gui-win64\yt-dlp-gui\_internal\bin\ffmpeg.exe"
LOGO      = r"C:\Users\jordy\Documents\Bassiehof\bassiehof-logo-transparent.png"
OUTRO     = r"C:\Users\jordy\Documents\Bassiehof\Bassie_hof_Politiek.mp4"
VIDEOS    = r"C:\Users\jordy\Documents\Bassiehof\Videos"
TOOLS     = os.path.dirname(os.path.abspath(__file__))
BASSIEHOF = r"C:\Users\jordy\Documents\Bassiehof"

CTX = ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE

def tg(method, **kwargs):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = urllib.parse.urlencode(kwargs).encode()
    req  = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        return json.loads(r.read())

def stuur(tekst):
    tg("sendMessage", chat_id=CHAT_ID, text=tekst)

def stuur_bestand(pad, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(pad,"rb") as f:
        body, boundary = encode_multipart({"chat_id": CHAT_ID, "caption": caption}, "document", os.path.basename(pad), f.read())
    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return json.loads(r.read())

def encode_multipart(fields, file_field, filename, file_data):
    import uuid
    boundary = uuid.uuid4().hex
    parts = []
    for k,v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
    parts.append(file_data)
    parts.append(f'\r\n--{boundary}--\r\n'.encode())
    return b''.join(parts), boundary

def wacht_op_instructies(timeout_min=30):
    """Poll Telegram voor JSON clip-instructies van Skordie"""
    print(f"Wachten op instructies van Skordie (max {timeout_min} min)...")
    stuur("📥 Bestanden ontvangen. Analyseer en stuur clip-instructies als JSON.")
    
    last_update = 0
    deadline = time.time() + timeout_min * 60
    
    while time.time() < deadline:
        try:
            res = tg("getUpdates", offset=last_update+1, timeout=20)
            updates = res.get("result", [])
            for upd in updates:
                last_update = upd["update_id"]
                msg = upd.get("message", {})
                tekst = msg.get("text", "")
                # Zoek JSON blok in bericht
                match = re.search(r'```json\s*(.*?)\s*```', tekst, re.DOTALL)
                if not match:
                    match = re.search(r'\{.*"clips".*\}', tekst, re.DOTALL)
                if match:
                    try:
                        instructies = json.loads(match.group(1) if '```' in tekst else match.group(0))
                        print(f"Instructies ontvangen!")
                        return instructies
                    except json.JSONDecodeError as e:
                        print(f"JSON fout: {e}")
        except Exception as e:
            print(f"Poll fout: {e}")
        time.sleep(3)
    return None

def run(cmd):
    print(f"\n$ {' '.join(cmd[:3])}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FOUT: {result.stderr[-200:]}")
    return result.returncode == 0

def verwerk_clip(video, srt, clip, index):
    """Verwerk één clip op basis van instructies"""
    naam     = clip.get("naam", f"clip{index}").replace(" ","_")
    start    = clip.get("start", "00:00:00")
    eind     = clip.get("eind",  "00:01:00")
    formaat  = clip.get("formaat", "short")   # "short" of "youtube"
    titel    = clip.get("titel", f"Clip {index}")
    privacy  = clip.get("privacy", "unlisted")

    os.makedirs(VIDEOS, exist_ok=True)
    raw    = os.path.join(VIDEOS, f"{naam}_raw.mp4")
    brand  = os.path.join(VIDEOS, f"{naam}_branded.mp4")
    final  = os.path.join(VIDEOS, f"{naam}_final.mp4")

    stuur(f"⚙️ Clip {index}: {naam} ({start}→{eind}) [{formaat}]")

    # 1. Knippen
    print(f"\n[{index}] Knippen: {start} -> {eind}")
    if not run([FFMPEG,"-y","-i",video,"-ss",start,"-to",eind,"-c","copy",raw]):
        stuur(f"❌ Clip {index} knippen mislukt"); return

    # 2. Branden
    print(f"[{index}] Branden ({formaat})...")
    if formaat == "short":
        filt = f"[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920[main];[1:v]scale=200:-1[logo];[main][logo]overlay=20:20[v]"
        if not run([FFMPEG,"-y","-i",raw,"-i",LOGO,"-filter_complex",filt,"-map","[v]","-map","0:a?","-pix_fmt","yuv420p","-c:v","libx264","-preset","fast","-crf","18",brand]):
            stuur(f"❌ Clip {index} branden mislukt"); return
    else:
        filt = f"[1:v]scale=120:-1[logo];[0:v][logo]overlay=W-w-20:20[main];[2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[outro];[main][outro]concat=n=2:v=1[v]"
        if not run([FFMPEG,"-y","-i",raw,"-i",LOGO,"-i",OUTRO,"-filter_complex",filt,"-map","[v]","-map","0:a?","-pix_fmt","yuv420p","-c:v","libx264","-preset","fast","-crf","18",brand]):
            stuur(f"❌ Clip {index} branden mislukt"); return

    # 3. Ondertitels
    if srt and os.path.isfile(srt):
        print(f"[{index}] Ondertitels...")
        sub_formaat = "shorts" if formaat=="short" else "youtube"
        
        # Maak clip-SRT (herberekende tijden)
        clip_srt = os.path.join(VIDEOS, f"{naam}.srt")
        snij_srt(srt, start, eind, clip_srt)
        
        # Genereer ASS
        ass_pad = os.path.join(VIDEOS, f"{naam}_karaoke_{sub_formaat}.ass")
        subprocess.run([
            "py", os.path.join(TOOLS,"subtitels.py"),
            brand, clip_srt,
            "--stijl","karaoke","--formaat",sub_formaat,"--alleen-ass"
        ])
        
        if os.path.isfile(ass_pad):
            ass_esc = ass_pad.replace('\\','/').replace(':','\\:')
            if not run([FFMPEG,"-y","-i",brand,"-vf",f"ass='{ass_esc}'","-c:a","copy","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",final]):
                print("Ondertitels mislukten, gebruik branded versie")
                final = brand
        else:
            final = brand
    else:
        final = brand

    # 4. Uploaden
    print(f"[{index}] Uploaden: {titel}")
    upload_args = [
        "py", os.path.join(TOOLS,"youtube_upload.py"),
        "--file", final,
        "--title", titel,
        "--privacy", privacy,
    ]
    if formaat == "short":
        upload_args.append("--shorts")
    subprocess.run(upload_args)
    stuur(f"✅ Clip {index} klaar: {titel}")

def snij_srt(srt_pad, start_str, eind_str, uitvoer):
    """Knip SRT op tijdrange en herbereken timestamps"""
    def ts(t):
        t=t.replace(',','.'); p=t.split(':')
        return int(p[0])*3600+int(p[1])*60+float(p[2])
    def fmt(s):
        s=max(0,s); h=int(s//3600); s%=3600; m=int(s//60); s%=60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.',',')
    
    clip_s = ts(start_str); clip_e = ts(eind_str)
    import re as _re
    tekst = open(srt_pad, encoding='utf-8', errors='ignore').read()
    blokken = _re.split(r'\n\n+', tekst.strip())
    out=[]; idx=1
    for b in blokken:
        regels=b.strip().split('\n')
        if len(regels)<3: continue
        m=_re.match(r'(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)',regels[1])
        if not m: continue
        s=ts(regels[1].split('-->')[0].strip()); e=ts(regels[1].split('-->')[1].strip())
        if e>clip_s and s<clip_e:
            out.append(f"{idx}\n{fmt(s-clip_s)} --> {fmt(e-clip_s)}\n{chr(10).join(regels[2:])}\n")
            idx+=1
    open(uitvoer,'w',encoding='utf-8').write('\n'.join(out))

def stuur_bestanden(video, srt):
    """Stuur video info + SRT naar Skordie voor analyse"""
    naam = os.path.basename(video)
    stuur(f"🎬 Nieuw debat klaar voor analyse: {naam}")
    if srt and os.path.isfile(srt):
        stuur_bestand(srt, caption="SRT transcript — analyseer en stuur clip-instructies als JSON")
    stuur("""📋 Stuur instructies in dit formaat:
```json
{
  "clips": [
    {
      "naam": "clip_naam",
      "start": "00:05:07",
      "eind": "00:06:28",
      "formaat": "short",
      "titel": "Titel voor YouTube",
      "privacy": "unlisted"
    }
  ]
}
```""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Gebruik: py verwerk.py video.mp4 [subtitels.srt]")
        sys.exit(1)
    
    video = sys.argv[1]
    srt   = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.isfile(video):
        print(f"Video niet gevonden: {video}"); sys.exit(1)
    
    print(f"Video: {video}")
    print(f"SRT  : {srt or 'geen'}")
    print()
    
    # Stuur naar Skordie voor analyse
    stuur_bestanden(video, srt)
    
    # Wacht op instructies
    instructies = wacht_op_instructies(timeout_min=60)
    
    if not instructies:
        print("Geen instructies ontvangen. Timeout.")
        stuur("⏰ Timeout — geen instructies ontvangen.")
        sys.exit(1)
    
    clips = instructies.get("clips", [])
    print(f"\n{len(clips)} clip(s) te verwerken...")
    stuur(f"🚀 Start verwerking van {len(clips)} clip(s)...")
    
    for i, clip in enumerate(clips, 1):
        verwerk_clip(video, srt, clip, i)
    
    stuur(f"🎉 Alle {len(clips)} clips klaar en geupload!")
    print("\nKlaar!")
