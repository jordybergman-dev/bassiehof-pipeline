# subtitels.py - Bassiehof Subtitle Generator
# Zet SRT om naar gestylede ondertitels voor YouTube (16:9) of Shorts (9:16)
# Gebruik: py subtitels.py video.mp4 subtitels.srt [--stijl popup|karaoke] [--formaat youtube|shorts]

import sys, os, re, argparse, subprocess, textwrap

FFMPEG = r"C:\Users\jordy\Downloads\yt-dlp-gui-win64\yt-dlp-gui\_internal\bin\ffmpeg.exe"
VIDEOS = r"C:\Users\jordy\Documents\Bassiehof\Videos"

def parse_srt(pad):
    """Lees SRT bestand en retourneer lijst van {start, end, text}"""
    tekst = open(pad, encoding='utf-8', errors='ignore').read()
    blokken = re.split(r'\n\n+', tekst.strip())
    entries = []
    for b in blokken:
        regels = b.strip().split('\n')
        if len(regels) < 3: continue
        m = re.match(r'(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)', regels[1])
        if not m: continue
        entries.append({
            'start': regels[1].split('-->')[0].strip().replace(',','.'),
            'end':   regels[1].split('-->')[1].strip().replace(',','.'),
            'text':  ' '.join(regels[2:]).strip()
        })
    return entries

def tijd_naar_cs(t):
    """Zet HH:MM:SS.mmm om naar centiseconden voor ASS"""
    t = t.replace(',','.')
    parts = t.split(':')
    h,m = int(parts[0]), int(parts[1])
    s = float(parts[2])
    return int((h*3600 + m*60 + s) * 100)

def cs_naar_ass(cs):
    """Centiseconden naar ASS tijdformaat H:MM:SS.cc"""
    h = cs // 360000; cs %= 360000
    m = cs // 6000;   cs %= 6000
    s = cs // 100;    cs %= 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def maak_ass_popup(entries, formaat='youtube'):
    """Maak pop-up stijl ASS bestand"""
    # Instellingen per formaat
    if formaat == 'shorts':
        playresx, playresy = 1080, 1920
        fontsize  = 72
        marginl   = 80
        marginr   = 80
        marginv   = 160
        max_chars = 28  # smaller width for 9:16
    else:
        playresx, playresy = 1920, 1080
        fontsize  = 58
        marginl   = 120
        marginr   = 120
        marginv   = 80
        max_chars = 42

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {playresx}
PlayResY: {playresy}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,3,1,2,{marginl},{marginr},{marginv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for e in entries:
        # Splits lange tekst op meerdere regels
        tekst = e['text']
        regels = textwrap.wrap(tekst, width=max_chars)
        ass_tekst = r'\N'.join(regels)
        start = cs_naar_ass(tijd_naar_cs(e['start']))
        end   = cs_naar_ass(tijd_naar_cs(e['end']))
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{ass_tekst}")

    return header + '\n'.join(events)

def maak_ass_karaoke(entries, formaat='youtube'):
    """Karaoke stijl: woord voor woord oplichten (simulatie op basis van duur)"""
    if formaat == 'shorts':
        playresx, playresy = 1080, 1920
        fontsize  = 68
        marginl   = 80
        marginr   = 80
        marginv   = 160
        max_chars = 24
    else:
        playresx, playresy = 1920, 1080
        fontsize  = 56
        marginl   = 120
        marginr   = 120
        marginv   = 80
        max_chars = 38

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {playresx}
PlayResY: {playresy}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,{fontsize},&H0000FFFF,&H00FFFFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,3,1,2,{marginl},{marginr},{marginv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for e in entries:
        woorden = e['text'].split()
        if not woorden: continue
        start_cs = tijd_naar_cs(e['start'])
        end_cs   = tijd_naar_cs(e['end'])
        duur_cs  = max(end_cs - start_cs, 10)
        per_woord = duur_cs // len(woorden)

        # Bouw karaoke tags: {\k50}woord {\k50}woord ...
        # \k = duur in centiseconden voor dat woord (geel terwijl het gezegd wordt)
        regels_woorden = textwrap.wrap(' '.join(woorden), width=max_chars)
        
        # Herverdeel woorden over regels
        idx = 0
        ass_delen = []
        for regel in regels_woorden:
            regel_woorden = regel.split()
            for w in regel_woorden:
                ass_delen.append(f"{{\\k{per_woord}}}{w} ")
            ass_delen.append(r'{\k0}\N')

        ass_tekst = ''.join(ass_delen).rstrip(r'\N').strip()
        start = cs_naar_ass(start_cs)
        end   = cs_naar_ass(end_cs)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{ass_tekst}")

    return header + '\n'.join(events)

def brand_met_subs(video, ass_pad, uitvoer):
    """Burn subtitles in video met ffmpeg"""
    # ASS pad moet forward slashes hebben voor ffmpeg filter
    ass_escaped = ass_pad.replace('\\', '/').replace(':', '\\:')
    cmd = [
        FFMPEG, '-y', '-i', video,
        '-vf', f"ass='{ass_escaped}'",
        '-c:a', 'copy',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-pix_fmt', 'yuv420p',
        uitvoer
    ]
    print(f"\nRenderen: {os.path.basename(uitvoer)}")
    print(' '.join(f'"{c}"' if ' ' in c else c for c in cmd))
    subprocess.run(cmd)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Bassiehof Subtitle Generator')
    p.add_argument('video',           help='Invoer video (.mp4)')
    p.add_argument('srt',             help='SRT ondertitelbestand')
    p.add_argument('--stijl',         default='beide', choices=['popup','karaoke','beide'])
    p.add_argument('--formaat',       default='youtube', choices=['youtube','shorts'])
    p.add_argument('--alleen-ass',    action='store_true', help='Maak alleen ASS bestand, geen video')
    args = p.parse_args()

    entries = parse_srt(args.srt)
    print(f"Geladen: {len(entries)} ondertitels")

    basis = os.path.splitext(args.video)[0]
    stijlen = ['popup','karaoke'] if args.stijl == 'beide' else [args.stijl]

    for stijl in stijlen:
        print(f"\n=== Stijl: {stijl} ===")
        if stijl == 'popup':
            ass = maak_ass_popup(entries, args.formaat)
        else:
            ass = maak_ass_karaoke(entries, args.formaat)

        ass_pad = f"{basis}_{stijl}_{args.formaat}.ass"
        with open(ass_pad, 'w', encoding='utf-8') as f:
            f.write(ass)
        print(f"ASS opgeslagen: {ass_pad}")

        if not args.alleen_ass:
            uitvoer = f"{basis}_{stijl}_{args.formaat}.mp4"
            brand_met_subs(args.video, ass_pad, uitvoer)
            print(f"Video klaar: {uitvoer}")

    print("\nKlaar!")
