#!/usr/bin/env python3
"""
Thumbnail Generator - Slimme design
- 1 spreker: politicus foto + partij logo + virale tekst
- 2 sprekers: split screen met 2 politici + 2 partij logos  
- Altijd: Bassiehof logo rechtsboven
"""
import os
import urllib.request
import json
from PIL import Image, ImageDraw, ImageFont

# Politici data
POLITICIANS = {
    "Geert Wilders": {"party": "PVV", "photo": "https://www.tweedekamer.nl/static/img/politici/Geert_Wilders.jpg"},
    "Gidi Markuszower": {"party": "Groep Markuszower", "photo": "..."},
    "Lidewij de Vos": {"party": "FVD", "photo": "..."},
    # ... more can be added
}

# Partij logos (placeholder URLs)
PARTY_LOGOS = {
    "PVV": None,
    "FVD": None,
    "DENK": None,
    "BBB": None,
    "GroenLinks-PvdA": None,
    "D66": None,
    # ...
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def detect_speakers(text):
    """Detecteer hoeveel sprekers in de clip"""
    # Check voor aanhalingstekens = 2 sprekers
    quotes = text.count('"')
    if quotes >= 4:  # Minimaal 2 sprekers (ieder 2 aanhalingstekens)
        return 2
    return 1

def find_politician(name):
    """Zoek politicus in database"""
    for politician, data in POLITICIANS.items():
        if politician.lower() in name.lower():
            return politician, data
    return None, None

def create_thumbnail(title, text, output_path):
    """Maak thumbnail"""
    # Create canvas (YouTube: 1280x720)
    img = Image.new('RGB', (1280, 720), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    
    # Font
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    speakers = detect_speakers(text)
    
    if speakers == 1:
        # 1 spreker - links foto, rechts tekst
        # Zoek politicus
        politician, data = find_politician(title)
        
        # Teken tekst (rechterkant)
        draw.text((650, 200), title[:40], font=font_big, fill=(255, 255, 255))
        draw.text((650, 350), text[:100], font=font_small, fill=(200, 200, 200))
        
        # Partij info
        if data:
            draw.text((650, 500), data["party"], font=font_small, fill=(100, 150, 255))
        
        # Placeholder voor politicus foto (linkerkant)
        draw.ellipse([50, 150, 450, 550], fill=(50, 50, 50), outline=(100, 100, 100))
        draw.text((150, 330), " Politicus ", font=font_big, fill=(150, 150, 150))
        
    else:
        # 2 sprekers - split screen
        # Linker helft
        draw.ellipse([50, 150, 350, 450], fill=(50, 50, 50), outline=(100, 100, 100))
        draw.text((100, 280), " Spreker 1 ", font=font_small, fill=(150, 150, 150))
        
        # Rechter helft  
        draw.ellipse([930, 150, 1230, 450], fill=(50, 50, 50), outline=(100, 100, 100))
        draw.text((980, 280), " Spreker 2 ", font=font_small, fill=(150, 150, 150))
        
        # Titel in midden
        draw.text((400, 100), title[:30], font=font_big, fill=(255, 255, 255))
    
    # Bassiehof logo - rechtsboven ALTIJD
    draw.text((1050, 20), "#Bassiehof", font=font_small, fill=(100, 100, 255))
    
    # Save
    img.save(output_path)
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 3:
        create_thumbnail(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python3 thumbnail.py 'Titel' 'Virale tekst' output.jpg")
