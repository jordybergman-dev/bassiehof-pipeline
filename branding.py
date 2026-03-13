#!/usr/bin/env python3
"""
Video Branding - Bassiehof Logo toevoegen
- Long video: rechtsboven
- Shorts: linksboven
"""
import subprocess

def add_logo(video_input, video_output, logo_path, is_short=False):
    """
    Voeg Bassiehof logo toe
    is_short: True voor 9:16 (Shorts), False voor 16:9 (long)
    """
    if is_short:
        # Shorts: 9:16 formaat met logo linksboven
        filter_complex = (
            "[0:v]scale=1080:1920[main];"
            "[1:v]scale=150:-1[logo];"
            "[main][logo]overlay=20:20[v]"  # Linksboven
        )
    else:
        # Long: 16:9 formaat met logo rechtsboven
        filter_complex = (
            "[0:v][1:v]overlay=W-w-20:20[v]"  # Rechtsboven
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
