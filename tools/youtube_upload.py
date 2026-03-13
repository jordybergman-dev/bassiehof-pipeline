#!/usr/bin/env python3
# Bassiehof YouTube Uploader v2.0
# Gebruik: py youtube_upload.py --file "clip.mp4" --title "Titel"
# Optioneel: --thumbnail "thumb.jpg" --description "..." --privacy private/unlisted/public

import os, sys, argparse, pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# youtube scope nodig voor thumbnail upload (youtube.upload is te beperkt)
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
BASSIEHOF      = r"C:\Users\jordy\Documents\Bassiehof"
CLIENT_SECRETS = os.path.join(BASSIEHOF, "client_secret.json")
TOKEN_FILE     = os.path.join(BASSIEHOF, "youtube_token.pkl")
VIDEOS_MAP     = os.path.join(BASSIEHOF, "Videos")

def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Scope uitgebreid -> token moet opnieuw aangemaakt worden
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload(file, title, description, privacy, thumbnail=None, is_shorts=False):
    yt = get_service()

    body = {
        "snippet": {
            "title": title,
            "description": description + "\n\n#bassiehof #politiek #tweedekamer #nederland",
            "tags": ["bassiehof","politiek","tweedekamer","nederland","tweede kamer"] + (["Shorts"] if is_shorts else []),
            "categoryId": "25",
            "defaultLanguage": "nl",
        },
        "status": {"privacyStatus": privacy}
    }

    media = MediaFileUpload(file, chunksize=-1, resumable=True)
    print(f"\nUploaden naar YouTube...")
    print(f"Titel   : {title}")
    print(f"Bestand : {file}")
    print(f"Privacy : {privacy}")
    if thumbnail:
        print(f"Thumb   : {thumbnail}")
    print()

    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"Voortgang: {int(status.progress() * 100)}%")

    vid = response["id"]
    print(f"\nVideo geupload! https://www.youtube.com/watch?v={vid}")

    # Thumbnail uploaden
    if thumbnail and os.path.isfile(thumbnail):
        print(f"\nThumbnail uploaden...")
        try:
            yt.thumbnails().set(
                videoId=vid,
                media_body=MediaFileUpload(thumbnail, mimetype="image/jpeg")
            ).execute()
            print(f"Thumbnail OK!")
        except Exception as e:
            print(f"Thumbnail fout: {e}")
            print(f"(Tip: stel thumbnail handmatig in op YouTube Studio)")
    elif thumbnail:
        print(f"Thumbnail niet gevonden: {thumbnail}")

    return vid

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file",        required=True,  help="Pad naar video bestand")
    p.add_argument("--title",       required=True,  help="Videotitel")
    p.add_argument("--thumbnail",   default=None,   help="Pad naar thumbnail (JPG)")
    p.add_argument("--description", default="Clip van het Nederlandse parlement | Bassiehof Politiek")
    p.add_argument("--privacy",     default="private", choices=["private","unlisted","public"])
    p.add_argument("--shorts",      action="store_true", help="Upload als YouTube Short (#Shorts)")
    args = p.parse_args()

    if not os.path.exists(args.file):
        print(f"Bestand niet gevonden: {args.file}")
        sys.exit(1)

    # Thumbnail: altijd automatisch - pakt de meest recente thumb uit Videos\
    thumb = args.thumbnail
    if not thumb:
        import glob, re as _re
        # Zoek meest recente thumb_*.jpg in Videos map
        thumbs = glob.glob(os.path.join(VIDEOS_MAP, "thumb_*.jpg"))
        default = os.path.join(VIDEOS_MAP, "thumbnail.jpg")
        if thumbs:
            thumb = max(thumbs, key=os.path.getmtime)
            print(f"Thumbnail automatisch (meest recent): {os.path.basename(thumb)}")
        elif os.path.isfile(default):
            thumb = default
            print(f"Thumbnail automatisch: thumbnail.jpg")
        else:
            print(f"Geen thumbnail gevonden in {VIDEOS_MAP}")

    desc = args.description
    title = args.title
    if args.shorts:
        # #Shorts in titel + beschrijving zorgt dat YouTube het als Short herkent
        if "#Shorts" not in title:
            title = title + " #Shorts"
        desc = desc + "\n\n#Shorts"
        print("Short modus: #Shorts toegevoegd aan titel + beschrijving")

    upload(args.file, title, desc, args.privacy, thumbnail=thumb, is_shorts=args.shorts)
