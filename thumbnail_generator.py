#!/usr/bin/env python3
"""
Thumbnail Generator voor Bassiehof
Haalt politicus foto's van Tweede Kamer API
"""
import os
import urllib.request
import json
from PIL import Image, ImageDraw, ImageFont

DEBATDIRECT_API = "https://cdn.debatdirect.tweedekamer.nl/api"

def get_politician_photo(name):
    """Haal foto URL op via naam"""
    # Probeer eerst via DebatDirect API
    try:
        req = urllib.request.Request(f"{DEBATDIRECT_API}/politicians")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            for p in data:
                if name.lower() in p.get('name', '').lower():
                    return p.get('photoUrl')
    except:
        pass
    return None

def create_thumbnail(title, politician_names, output_path):
    """Maak thumbnail met politicus foto"""
    # Download eerste politicus foto
    politicus_foto = None
    for name in politician_names:
        url = get_politician_photo(name)
        if url:
            try:
                urllib.request.urlretrieve(url, "/tmp/politicus.jpg")
                politicus_foto = "/tmp/politicus.jpg"
                break
            except:
                pass
    
    # Maak thumbnail (1280x720 voor YouTube)
    img = Image.new('RGB', (1280, 720), color=(20, 20, 20))
    d = ImageDraw.Draw(img)
    
    # Als we een foto hebben, plak die erin
    if politicus_foto:
        try:
            foto = Image.open(politicus_foto).resize((400, 400))
            img.paste(foto, (50, 160))
        except:
            pass
    
    # Titel tekst
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Teken tekst
    d.text((480, 200), title[:40], font=font, fill=(255, 255, 255))
    
    # Bassiehof logo/brand
    d.text((480, 600), "#Bassiehof #Politiek", font=font, fill=(200, 200, 200))
    
    img.save(output_path)
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        create_thumbnail(sys.argv[1], sys.argv[2].split(','), sys.argv[3])
    else:
        print("Usage: python3 thumbnail.py 'Titel' 'Naam1,Naam2' output.jpg")
