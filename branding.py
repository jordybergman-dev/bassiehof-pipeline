#!/usr/bin/env python3
"""
Video Branding - Logo toevoegen aan video's
"""
import subprocess
import os

def add_logo(video_input, video_output, logo_path, is_short=False):
    """
    Voeg logo toe aan video
    is_short: True voor 9:16, False voor 16:9
    """
    if is_short:
        # 9:16 formaat (Shorts/Reels)
        # Crop naar 9:16 en voeg logo toe
        filter_complex = (
            "[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920[main];"
            "[1:v]scale=200:-1[logo];"
            "[main][logo]overlay=20:20[v]"
        )
    else:
        # 16:9 formaat (YouTube long)
        filter_complex = (
            "[1:v]scale=120:-1[logo];"
            "[0:v][logo]overlay=W-w-20:20[v]"
        )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_input,
        "-i", logo_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        video_output
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 3:
        is_short = sys.argv[3].lower() == "short"
        add_logo(sys.argv[1], sys.argv[2], sys.argv[3], is_short)
    else:
        print("Usage: python3 branding.py input.mp4 output.mp4 logo.png [short|long]")
