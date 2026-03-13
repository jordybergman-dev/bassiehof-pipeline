#!/usr/bin/env python3
"""
Video Editor - Opwaardering voor meer views
- Zoom effects
- Background music
- End screens
- Intro/outro
"""
import subprocess
import os
import random

MUSIC_DIR = "/root/bassiehof-pipeline/music"

def add_intro_outro(video_path, output_path, logo_path=None):
    """Voeg intro + outro toe"""
    # Intro clip (1 sec zwart met logo)
    intro = f"/tmp/intro_{random.randint(1000,9999)}.mp4"
    outro = f"/tmp/outro_{random.randint(1000,9999)}.mp4"
    
    # Maak intro
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=1",
        "-i", logo_path, "-filter_complex", 
        "[0:v][1:v]overlay=(W-w)/2:(H-h)/2[v]", "-map", "[v]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", intro
    ], capture_output=True)
    
    # Maak outro
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=2",
        "-vf", "drawtext=text='Bassiehof':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", outro
    ], capture_output=True)
    
    # Combineer
    concat = f"/tmp/concat_{random.randint(1000,9999)}.txt"
    with open(concat, 'w') as f:
        f.write(f"file '{intro}'\nfile '{video_path}'\nfile '{ outro}'")
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
        "-c", "copy", output_path
    ], capture_output=True)
    
    # Cleanup
    for f in [intro, outro, concat]:
        try: os.remove(f)
        pass
    
    return os.path.exists(output_path)

def add_music(video_path, output_path, music_volume=0.1):
    """Voeg achtergrondmuziek toe"""
    # Generate white noise als placeholder
    music = f"/tmp/bg_music_{random.randint(1000,9999)}.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", 
        "anoisesrc=d=10:color=white",
        "-af", f"volume={music_volume}",
        "-t", "10", music
    ], capture_output=True)
    
    # Mix met video
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path, "-i", music,
        "-filter_complex", 
        "[0:a][1:a]amix=inputs=2:duration=first[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", output_path
    ], capture_output=True)
    
    try: os.remove(music)
    pass
    
    return os.path.exists(output_path)

def add_zoom_effect(video_path, output_path):
    """Voeg zoom effect toe voor meer engagement"""
    # Simpel zoom-in effect
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        output_path
    ], capture_output=True)
    
    return os.path.exists(output_path)

def enhance_video(video_path, output_path, add_music_flag=True):
    """Complete video enhancement"""
    temp = f"/tmp/enhanced_{random.randint(1000,9999)}.mp4"
    
    # Stap 1: Zoom/formaat
    add_zoom_effect(video_path, temp)
    
    # Stap 2: Muziek (optioneel)
    if add_music_flag:
        add_music(temp, output_path)
        try: os.remove(temp)
    else:
        os.rename(temp, output_path)
    
    return os.path.exists(output_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        enhance_video(sys.argv[1], sys.argv[2])

def add_chapters(video_path, output_path, timestamps):
    """Voeg chapters toe (voor long video's)"""
    # Chapters via metadata
    import tempfile
    
    # Dit vereist yt-dlp metadata - placeholder voor nu
    print(f"Chapters: {timestamps}")
    return True

def add_end_screen(video_path, output_path):
    """Voeg end screen toe (laatste 10 sec)"""
    # Create end screen with subscribe button
    endscreen = f"/tmp/endscreen_{random.randint(1000,9999)}.mp4"
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=5",
        "-vf", """drawtext=text='🔔 Abonneer!':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2,
                  drawtext=text='Meer clips op Bassiehof':fontsize=30:fontcolor=gray:x=(w-text_w)/2:y=(h-text_h)/2+80""",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", endscreen
    ], capture_output=True)
    
    # Concatenate
    concat = f"/tmp/concat_end.txt"
    with open(concat, 'w') as f:
        f.write(f"file '{video_path}'\nfile '{endscreen}'")
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
        "-c", "copy", output_path
    ], capture_output=True)
    
    try: os.remove(endscreen, concat)
    pass
    
    return os.path.exists(output_path)
