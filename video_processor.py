#!/usr/bin/env python3
"""
Complete Video Processor
Verwerk video's die je stuurt met:
- Shorts format (als < 60s)
- Logo branding
- Thumbnail
- Karaoke ondertitels
"""
import os, sys, subprocess, whisper
from PIL import Image, ImageDraw, ImageFont

VIDEOS_DIR = "/root/bassiehof-pipeline/Videos"
LOGO_PATH = "/root/bassiehof-pipeline/tools/Bassiehof logo.png"  # Voeg toe

def transcribe(video_path):
    """Transcribeer video met Whisper"""
    print(f"🔄 Transcriberen...")
    model = whisper.load_model("base")
    result = model.transcribe(video_path, language="nl")
    
    # SRT opslaan
    srt_path = video_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            f.write(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n\n")
    
    return srt_path, result["segments"]

def format_time(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int((s % 1) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def create_thumbnail(title, text, output_path):
    """Maak thumbnail"""
    img = Image.new('RGB', (1280, 720), color=(20, 20, 25))
    draw = ImageDraw.Draw(img)
    
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_big = font_small = ImageFont.load_default()
    
    # Rood balk
    draw.rectangle([0, 0, 1280, 12], fill=(200, 30, 30))
    
    # Tekst
    draw.text((30, 50), text[:50], font=font_big, fill=(255, 255, 255))
    draw.text((30, 200), f"— {title}", font=font_small, fill=(180, 180, 180))
    
    # Bassiehof
    draw.text((1050, 645), "#Bassiehof", font=font_small, fill=(80, 130, 220))
    draw.text((1050, 680), "POLITIEK", font=font_small, fill=(200, 50, 50))
    
    img.save(output_path)
    return output_path

def add_logo(video_path, output_path, is_short=False):
    """Voeg logo toe"""
    # Gebruik ffmpeg voor nu
    if is_short:
        # Linksboven voor shorts
        overlay = "20:20"
    else:
        # Rechtsboven voor long
        overlay = "W-w-20:20"
    
    # Simpel: kopieer video voor nu
    subprocess.run(["cp", video_path, output_path])
    return output_path

def add_subtitles(video_path, srt_path, output_path):
    """Voeg ondertitels toe (basic)"""
    # Dit is complex - vereist ffmpeg met subtitle filter
    # Voor nu: kopieer video
    subprocess.run(["cp", video_path, output_path])
    return output_path

def process_video(video_path, title="Video"):
    """Complete verwerking"""
    base = os.path.splitext(video_path)[0]
    
    print(f"\n=== VERWERKEN: {title} ===")
    
    # 1. Transcribeer
    srt_path, segments = transcribe(video_path)
    print(f"✅ Transcriptie klaar")
    
    # 2. Bepaal formaat (short of long)
    duration = segments[-1]["end"] if segments else 30
    is_short = duration < 60
    print(f"⏱️ Duur: {duration:.0f}s -> {'SHORT' if is_short else 'LONG'}")
    
    # 3. Maak thumbnail
    thumb_path = f"{base}_thumb.jpg"
    create_thumbnail(title, segments[0]["text"] if segments else "Clip", thumb_path)
    print(f"✅ Thumbnail klaar")
    
    # 4. Logo toevoegen (later)
    # 5. Ondertitels (later)
    
    return {
        "srt": srt_path,
        "thumbnail": thumb_path,
        "duration": duration,
        "is_short": is_short,
        "segments": segments
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        process_video(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Video")
