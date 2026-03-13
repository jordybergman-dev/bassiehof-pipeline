# thumbnail.py - Bassiehof Politiek Thumbnail Generator v5
import sys, os, re, json, io, ssl, urllib.request, urllib.parse

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installeer Pillow: py -m pip install Pillow")
    input("Enter..."); sys.exit(1)

BASSIEHOF = r"C:\Users\jordy\Documents\Bassiehof"
POLITICI  = os.path.join(BASSIEHOF, "Politici")
LOGOS     = os.path.join(BASSIEHOF, "Partij logos")
VIDEOS    = os.path.join(BASSIEHOF, "Videos")
TOOLS     = os.path.dirname(os.path.abspath(__file__))
BLOGO     = os.path.join(TOOLS, "bassiehof-logo-transparent.png")

W, H    = 1280, 720
BORDER  = 18
DIVIDER = 10

GEEL = (255,220,0); ROOD = (200,0,0); WIT = (255,255,255); ZWART = (0,0,0)

KLEUREN = {
    "PVV":(0,100,180),"VVD":(230,120,0),"D66":(0,160,200),
    "PvdA":(200,30,30),"GL":(0,150,50),"SP":(180,30,30),
    "CDA":(0,100,50),"NSC":(50,50,180),"BBB":(90,150,30),
    "DENK":(0,150,150),"JA21":(160,0,70),"FVD":(90,0,110),
    "CU":(30,120,190),"SGP":(160,90,0),"Volt":(70,0,180),"PvdD":(30,140,50),
}

# Bekende politici (fallback als API traag is)
BEKEND = {
    "wilders":"PVV","rutte":"VVD","omtzigt":"NSC","klever":"PVV",
    "castricum":"Volt","jetten":"D66","kaag":"D66","yesilgoz":"VVD",
    "ploumen":"PvdA","klaver":"GL","marijnissen":"SP","segers":"CU",
    "van baarle":"DENK","kuzu":"DENK","azarkan":"DENK",
    "baudet":"FVD","heerma":"CDA","bontenbal":"CDA",
}

TK  = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"
HDR = {"Accept":"application/json","User-Agent":"BassiehofBot/1.0"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

def GET(url):
    try:
        print(f"  GET: {url[:80]}...")
        req = urllib.request.Request(url, headers=HDR)
        with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
            data = r.read()
            print(f"  -> {len(data)} bytes")
            return data
    except Exception as e:
        print(f"  [GET FOUT] {e}")
        return None

def haal_info(naam):
    info = {"foto": None, "afk": None, "logo": None, "logo_transparant": False}
    
    # Lokale foto?
    veilig = re.sub(r"[^\w\s-]","",naam).strip()
    if os.path.isdir(POLITICI):
        for ext in [".jpg",".jpeg",".png"]:
            pad = os.path.join(POLITICI, f"{veilig}{ext}")
            if os.path.isfile(pad):
                info["foto"] = open(pad,"rb").read()
                print(f"  [FOTO] Lokaal: {pad}")
                break

    # Bekende partij (snelle fallback)
    naam_l = naam.lower()
    for key,afk in BEKEND.items():
        if key in naam_l:
            info["afk"] = afk
            print(f"  [PARTIJ] Bekende fallback: {afk}")
            break

    # Lokaal logo (als partij bekend)
    if info["afk"] and os.path.isdir(LOGOS):
        for ext in [".png",".jpg",".jpeg"]:
            pad = os.path.join(LOGOS, f"{info['afk']}{ext}")
            if os.path.isfile(pad):
                info["logo"] = open(pad,"rb").read()
                info["logo_transparant"] = ext.lower() == ".png"
                print(f"  [LOGO] Lokaal: {pad} (transparant={info['logo_transparant']})")
                break

    # API ophalen
    delen = naam.strip().split()
    if not delen: return info
    
    print(f"\n  === API voor {naam} ===")
    
    # Persoon zoeken
    filt = urllib.parse.quote("Achternaam eq '" + delen[-1] + "'")
    data = GET(f"{TK}/Persoon?$filter={filt}&$top=5")
    if not data:
        print(f"  [PERSOON] Geen response")
        return info
    
    try:
        items = json.loads(data).get("value",[])
        print(f"  [PERSOON] {len(items)} resultaten")
        vn = delen[0].lower()
        match = next((p for p in items if p.get("Roepnaam","").lower()==vn), items[0] if items else None)
        if not match:
            print(f"  [PERSOON] Geen match gevonden")
            return info
        pid = match["Id"]
        print(f"  [PERSOON] {match.get('Roepnaam')} {match.get('Achternaam')} -> {pid}")
    except Exception as e:
        print(f"  [PERSOON FOUT] {e}")
        return info

    # Foto downloaden
    if not info["foto"]:
        fb = GET(f"{TK}/Persoon({pid})/Resource")
        if fb:
            info["foto"] = fb
            print(f"  [FOTO] API: {len(fb)} bytes")
        else:
            print(f"  [FOTO] Niet beschikbaar")

    # Partij - stap 1: FractieZetel_Id
    filt2 = urllib.parse.quote("Persoon_Id eq " + pid)
    d1 = GET(f"{TK}/FractieZetelPersoon?$filter={filt2}&$top=1&$select=FractieZetel_Id")
    if not d1:
        print(f"  [PARTIJ] FractieZetelPersoon geen response")
        return info
    
    try:
        fz_items = json.loads(d1).get("value",[])
        print(f"  [PARTIJ] FractieZetel items: {len(fz_items)}")
        if not fz_items: return info
        fz_id = fz_items[0].get("FractieZetel_Id")
        print(f"  [PARTIJ] FractieZetel_Id: {fz_id}")
        if not fz_id: return info
    except Exception as e:
        print(f"  [PARTIJ STAP1 FOUT] {e}")
        return info

    # Partij - stap 2: Fractie info
    d2 = GET(f"{TK}/FractieZetel({fz_id})?$expand=Fractie")
    if not d2:
        print(f"  [PARTIJ] FractieZetel geen response")
        return info
    
    try:
        frac = json.loads(d2).get("Fractie",{})
        afk  = frac.get("Afkorting")
        fid  = frac.get("Id")
        print(f"  [PARTIJ] Afkorting: {afk}, ID: {fid}")
        if afk:
            info["afk"] = afk
    except Exception as e:
        print(f"  [PARTIJ STAP2 FOUT] {e}")
        return info

    # Logo downloaden
    if not info["logo"]:
        if info["afk"] and os.path.isdir(LOGOS):
            for ext in [".png",".jpg",".jpeg"]:
                pad = os.path.join(LOGOS, f"{info['afk']}{ext}")
                if os.path.isfile(pad):
                    info["logo"] = open(pad,"rb").read()
                    print(f"  [LOGO] Lokaal: {pad}")
                    break
        
        if not info["logo"] and fid:
            lb = GET(f"{TK}/Fractie({fid})/Resource")
            if lb:
                info["logo"] = lb
                info["logo_transparant"] = False
                print(f"  [LOGO] API: {len(lb)} bytes")
            else:
                print(f"  [LOGO] Niet beschikbaar via API")

    print(f"  === Resultaat {naam}: foto={bool(info['foto'])}, afk={info['afk']}, logo={bool(info['logo'])} ===\n")
    return info

def font(sz):
    for p in [r"C:\Windows\Fonts\ariblk.ttf",r"C:\Windows\Fonts\arialbd.ttf",
              r"C:\Windows\Fonts\impact.ttf",r"C:\Windows\Fonts\verdanab.ttf",
              r"C:\Windows\Fonts\calibrib.ttf",r"C:\Windows\Fonts\arial.ttf"]:
        if os.path.isfile(p):
            try: return ImageFont.truetype(p,sz)
            except: pass
    return ImageFont.load_default()

def tekst(draw, cx, cy, t, f, kleur, outline, d=4):
    try: bb=f.getbbox(t); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    except:
        try: tw,th=f.getsize(t)
        except: tw,th=len(t)*9,14
    x,y = int(cx-tw/2), int(cy-th/2)
    for dx in range(-d,d+1):
        for dy in range(-d,d+1):
            if dx or dy: draw.text((x+dx,y+dy),t,font=f,fill=outline)
    draw.text((x,y),t,font=f,fill=kleur)

def bouw_paneel(breedte, hoogte, naam, info):
    afk = info.get("afk")

    if info.get("foto"):
        try:
            img = Image.open(io.BytesIO(info["foto"])).convert("RGB")
            r = max(breedte/img.width, hoogte/img.height)
            nw,nh = int(img.width*r),int(img.height*r)
            img = img.resize((nw,nh),Image.LANCZOS)
            xo = (nw-breedte)//2
            yo = max(0, int((nh-hoogte)*0.12))
            p = img.crop((xo,yo,xo+breedte,yo+hoogte))
            print(f"  [PANEEL] Foto geplaatst voor {naam}")
        except Exception as e:
            print(f"  [PANEEL] Foto fout: {e}")
            p = Image.new("RGB",(breedte,hoogte),KLEUREN.get(afk,(45,45,60)))
    else:
        p = Image.new("RGB",(breedte,hoogte),KLEUREN.get(afk,(45,45,60)))
        dr = ImageDraw.Draw(p)
        ini = "".join(w[0].upper() for w in naam.split() if w)
        tekst(dr,breedte//2,hoogte//2,ini,font(min(int(hoogte*0.28),180)),WIT,ZWART,3)

    # Gradient
    g = Image.new("RGBA",(breedte,hoogte//2),(0,0,0,0))
    gd = ImageDraw.Draw(g)
    for i in range(hoogte//2):
        gd.rectangle([(0,i),(breedte,i+1)],fill=(0,0,0,int(175*i/(hoogte//2))))
    p2 = p.convert("RGBA"); p2.paste(g,(0,hoogte//2),g); p=p2.convert("RGB")

    # Partijlogo
    # Partijlogo — transparant of opaque
    logo_bytes = info.get("logo")
    print(f"  [LOGO CHECK] afk={afk}, logo bytes={len(logo_bytes) if logo_bytes else None}")
    if logo_bytes:
        try:
            lg = Image.open(io.BytesIO(logo_bytes))
            print(f"  [LOGO] Geopend: {lg.size} mode={lg.mode}")
            # Eerst naar RGBA converteren voor resize (behoudt transparantie correct)
            lg = lg.convert("RGBA")
            lh = 65; lw = max(1,int(lg.width*lh/lg.height))
            lg2 = lg.resize((lw,lh),Image.LANCZOS)
            # Verwijder achtergrondkleur (wit of zwart) als PNG
            if info.get("logo_transparant", False):
                pixels = lg2.load()
                w2, h2 = lg2.size
                # Detecteer achtergrondkleur via hoekpixels
                corners = [pixels[0,0], pixels[w2-1,0], pixels[0,h2-1], pixels[w2-1,h2-1]]
                avg_r = sum(c[0] for c in corners)//4
                avg_g = sum(c[1] for c in corners)//4
                avg_b = sum(c[2] for c in corners)//4
                avg_a = sum(c[3] for c in corners)//4
                is_white_bg = avg_r > 200 and avg_g > 200 and avg_b > 200 and avg_a > 200
                is_dark_bg  = avg_r < 60  and avg_g < 60  and avg_b < 60  and avg_a > 200
                print(f"  [LOGO] Hoekkleur avg: r={avg_r} g={avg_g} b={avg_b} a={avg_a} (wit={is_white_bg}, donker={is_dark_bg})")
                if is_white_bg or is_dark_bg:
                    # Maak achtergrondpixels transparant (tolerantie 40)
                    new_pixels = []
                    for y in range(h2):
                        for x in range(w2):
                            r,g,b,a = pixels[x,y]
                            if is_white_bg and r > 200 and g > 200 and b > 200:
                                pixels[x,y] = (r,g,b,0)
                            elif is_dark_bg and r < 60 and g < 60 and b < 60:
                                pixels[x,y] = (r,g,b,0)
                    print(f"  [LOGO] Achtergrond verwijderd")
            p3 = p.convert("RGBA")
            # Logo plakken met alpha mask (geen vakje erachter voor PNG)
            if not info.get("logo_transparant", False):
                bx = Image.new("RGBA",(lw+16,lh+16),(0,0,0,180))
                p3.paste(bx,(12,12),bx)
            p3.paste(lg2,(20,20),lg2)
            p = p3.convert("RGB")
            print(f"  [LOGO] Geplakt!")
        except Exception as e:
            print(f"  [LOGO FOUT] {e}")
            import traceback; traceback.print_exc()
    elif afk:
        # Fallback: gekleurde balk met tekst
        print(f"  [LOGO] Geen bytes, teken tekst voor {afk}")
        p3 = p.convert("RGBA")
        kleur = KLEUREN.get(afk,(60,60,60))
        bx = Image.new("RGBA",(80,34),(kleur[0],kleur[1],kleur[2],220))
        p3.paste(bx,(12,12),bx)
        dr = ImageDraw.Draw(p3)
        try:
            f2 = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf",18)
        except:
            f2 = ImageFont.load_default()
        bb = f2.getbbox(afk) if hasattr(f2,'getbbox') else (0,0,len(afk)*10,18)
        tw = bb[2]-bb[0]; th = bb[3]-bb[1]
        dr.text((12+(80-tw)//2, 12+(34-th)//2), afk, font=f2, fill=WIT)
        p = p3.convert("RGB")

    return p

def maak(titel, namen):
    print(f"\n{'='*50}")
    print(f"Titel : {titel}")
    print(f"Namen : {namen}")
    print(f"{'='*50}\n")

    c = Image.new("RGB",(W,H),ZWART)
    ix,iy = BORDER,BORDER
    iw,ih = W-2*BORDER, H-2*BORDER

    if len(namen)==1:
        info = haal_info(namen[0])
        c.paste(bouw_paneel(iw,ih,namen[0],info),(ix,iy))
    else:
        pb = (iw-DIVIDER)//2
        for i,naam in enumerate(namen[:2]):
            info = haal_info(naam)
            c.paste(bouw_paneel(pb,ih,naam,info),(ix+i*(pb+DIVIDER),iy))
        d=ImageDraw.Draw(c)
        d.rectangle([(ix+pb,iy),(ix+pb+DIVIDER,iy+ih)],fill=GEEL)

    d=ImageDraw.Draw(c)
    d.rectangle([(0,0),(W-1,H-1)],outline=GEEL,width=BORDER)

    delen = [x.strip() for x in titel.upper().split("/")]
    ty = H-110
    if len(delen)>=2:
        tekst(d,W//2,ty-55,delen[0],font(44),WIT,ROOD,3)
        tekst(d,W//2,ty+10,delen[1],font(72),GEEL,ROOD,5)
    else:
        ww=titel.upper().split(); h=len(ww)//2
        tekst(d,W//2,ty-40," ".join(ww[:h]),font(68),GEEL,ROOD,5)
        tekst(d,W//2,ty+32," ".join(ww[h:]),font(68),GEEL,ROOD,5)

    if os.path.isfile(BLOGO):
        try:
            bl=Image.open(BLOGO).convert("RGBA")
            bl=bl.resize((150,150),Image.LANCZOS)
            c2=c.convert("RGBA"); c2.paste(bl,(W-150-BORDER-10,BORDER+10),bl)
            c=c2.convert("RGB"); print("[BLOGO] Bassiehof logo OK")
        except Exception as e: print(f"[BLOGO] Fout: {e}")
    else:
        print(f"[BLOGO] Niet gevonden: {BLOGO}")

    os.makedirs(VIDEOS,exist_ok=True)
    # Sla op als thumbnail.jpg (standaard) + unieke versie op basis van titel
    import re as _re, datetime as _dt
    veilig = _re.sub(r"[^\w\s-]","",titel).strip().replace(" ","_")[:40]
    uit_uniek = os.path.join(VIDEOS, f"thumb_{veilig}.jpg")
    uit       = os.path.join(VIDEOS, "thumbnail.jpg")
    c.save(uit,      "JPEG", quality=95)
    c.save(uit_uniek,"JPEG", quality=95)
    print(f"\n>>> KLAAR:")
    print(f"    Standaard : {uit}")
    print(f"    Uniek     : {uit_uniek}")
    print(f"\nGebruik bij upload: --title \"{titel}\"")
    print(f"Dan vindt de uploader automatisch de thumbnail.\n")

if __name__=="__main__":
    if len(sys.argv)>=3:
        maak(sys.argv[1],sys.argv[2:])
    else:
        print("\n  Bassiehof Thumbnail Generator v5\n  " + "="*34 + "\n")
        titel = input("Debattitel (bijv. FEL DEBAT / WILDERS VS CASTRICUM): ").strip()
        pol1  = input("Politicus 1 (bijv. Geert Wilders): ").strip()
        pol2  = input("Politicus 2 (optioneel - Enter overslaan): ").strip()
        if titel and pol1:
            maak(titel, [pol1] if not pol2 else [pol1,pol2])
        else:
            print("Geen titel of naam ingevuld!")
    input("\nDruk Enter om te sluiten...")
