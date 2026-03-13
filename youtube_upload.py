#!/usr/bin/env python3
"""
YouTube Upload met SEO optimalisatie
"""
import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta
import google.auth

BASE = "/root/bassiehof-pipeline"
TOKEN_FILE = os.path.join(BASE, "youtube_token.pkl")

# SEO Tags
SEO_TAGS = [
    "bassiehof", "politiek", "tweedekamer", "nederland", "nieuws",
    "wilders", "pvv", "debattle", "politiek debat", "kamerdebat",
    "actueel", "nederlands nieuws", "politieke momenten", "viral"
]

def get_youtube_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        return None
    return build("youtube", "v3", credentials=creds)

def upload(video_path, title, description="", is_short=False, schedule_hour=19):
    """Upload naar YouTube met SEO"""
    yt = get_youtube_service()
    if not yt:
        print("No YouTube credentials")
        return False
    
    # SEO description
    desc = f"""🔥 {title}

{description}

#bassiehof #politiek #tweedekamer #nederland #nieuws #debattle

📺 Meer politieke clips: Abonneer je op het kanaal!

🔔 Bel Aan! 🔔"""
    
    # Tags toevoegen
    tags = SEO_TAGS.copy()
    if is_short:
        tags.extend(["shorts", "ytshorts", "viral"])
    
    # Privacy + scheduling
    now = datetime.now()
    publish_at = now.replace(hour=schedule_hour, minute=0, second=0, microsecond=0)
    if publish_at <= now:
        publish_at += timedelta(days=1)
    
    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": tags,
            "categoryId": "25",  # News & Politics
        },
        "status": {
            "privacyStatus": "public",
            "publishAt": publish_at.isoformat() + "Z",
            "selfDeclaredMadeForKids": False,
        }
    }
    
    media = MediaFileUpload(video_path, resumable=True)
    response = yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    
    print(f"✅ Uploaded: {title}")
    print(f"🔗 https://youtube.com/watch?v={response['id']}")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        is_short = "short" in sys.argv[1].lower()
        upload(sys.argv[1], sys.argv[2], is_short=is_short)
