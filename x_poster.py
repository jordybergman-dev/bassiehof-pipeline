#!/usr/bin/env python3
"""
X/Twitter Poster - Automatisch posten naar @bassiehof
"""
import os
import requests
from requests_oauthlib import OAuth1

# Credentials from environment
CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY", os.environ.get("X_CONSUMER_KEY", ""))
CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET", os.environ.get("X_CONSUMER_SECRET", ""))
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", os.environ.get("X_ACCESS_TOKEN", ""))
ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", os.environ.get("X_ACCESS_SECRET", ""))

auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET)

def post_text(text):
    """Post tekst naar X"""
    url = "https://api.twitter.com/2/tweets"
    data = {"text": text}
    r = requests.post(url, auth=auth, json=data)
    return r.json()

def post_with_media(text, media_path=None):
    """Post met media"""
    if media_path:
        # Upload media first
        url = "https://upload.twitter.com/1.1/media/upload.json"
        with open(media_path, 'rb') as f:
            files = {'media': f}
            media = requests.post(url, auth=auth, files=files).json()
        
        media_id = media['media_id_string']
        
        # Post tweet with media
        url = "https://api.twitter.com/2/tweets"
        data = {"text": text, "media": {"media_ids": [media_id]}}
    else:
        url = "https://api.twitter.com/2/tweets"
        data = {"text": text}
    
    r = requests.post(url, auth=auth, json=data)
    return r.json()

def post_video_update(video_title, youtube_url):
    """Post video update voor Bassiehof"""
    hook = "🔥 Nieuwe video!"
    text = f"{hook}\n\n{video_title}\n\n👇 Kijk hier:\n{youtube_url}\n\n#Bassiehof #Politiek"
    
    return post_text(text)

# Test
if __name__ == "__main__":
    print("X Poster klaar!")
    # Test post
    # result = post_text("Test bericht van Bassiehof Pipeline! 🤖")
    # print(result)
