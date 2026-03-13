#!/usr/bin/env python3
"""
Thumbnail Generator - Clean News Style
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
POLITICIANS_DIR = os.path.join(BASE, "politici")

def find_photo(name):
    for ext in ['.jpg', '.png', '.jpeg']:
        local = os.path.join(POLITICIANS_DIR, f"{name}{ext}")
        if os.path.exists(local):
            return local
    return None

def create_thumbnail(title, text, output_path):
    """Clean News Style - Geen emoji"""
    img = Image.new('RGB', (1280, 720), color=(10, 10, 15))
    draw = ImageDraw.Draw(img)
    
    # Font
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 25)
    except:
        font_huge = font_big = font_small = ImageFont.load_default()
    
    # Rood balk boven
    draw.rectangle([0, 0, 1280, 12], fill=(200, 30, 30))
    
    # Links: Grote tekst (quote)
    draw.text((30, 50), text[:50], font=font_huge, fill=(255, 255, 255))
    
    # Naam
    name = title.split()[0] if title else "Politicus"
    draw.text((30, 200), f"— {name}", font=font_big, fill=(180, 180, 180))
    
    # Rechts: Foto
    photo = find_photo(name)
    if photo:
        try:
            foto = Image.open(photo).resize((500, 500))
            img.paste(foto, (700, 110), foto)
        except:
            draw.rectangle([700, 110, 1200, 610], fill=(30, 30, 40), outline=(80, 80, 120), width=2)
    else:
        draw.rectangle([700, 110, 1200, 610], fill=(30, 30, 40), outline=(80, 80, 120), width=2)
    
    # Bassiehof - linksonder
    draw.text((30, 645), "#Bassiehof", font=font_small, fill=(80, 130, 220))
    
    # POLITIEK - rechtsonder
    draw.text((1050, 645), "POLITIEK", font=font_small, fill=(200, 50, 50))
    
    img.save(output_path)
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 3:
        create_thumbnail(sys.argv[1], sys.argv[2], sys.argv[3])
