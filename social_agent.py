#!/usr/bin/env python3
"""
Social Media Agent - Politieke content generator
"""
import os, requests, random
from datetime import datetime
from requests_oauthlib import OAuth1
import json

# X Credentials
CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY", "4DHzgY5szwxKGg1XMG6L84emn")
CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET", "b8czGuw3CVXXo6q7JLNjFyBrGGZg0abDGnIItbNzY6AhdiyCG2")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "1701510127746965504-60tQ6PdnNfAnmvq8kjyGfSKqwRYnlm")
ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "zfDe9DwaRM0L89kP90WyurSo26XhgOqMUaMeQuxelFieK")

auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
YOUTUBE_API_KEY = open("/root/bassiehof-pipeline/youtube_api_key.txt").read().strip()
CHANNEL_ID = "UCkjmfFCmtLWuJz_SSwEvzjA"

TOPICS = {
    "asiel": "Asiel", "migratie": "Migratie", "klimaat": "Klimaat",
    "zorg": "Zorg", "pensioen": "Pensioen", "stikstof": "Stikstof",
    "economie": "Economie", "onderwijs": "Onderwijs"
}

def get_top_videos():
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&maxResults=5&order=date&type=video&key={YOUTUBE_API_KEY}"
    r = requests.get(url).json()
    videos = []
    if "items" in r:
        for item in r["items"]:
            videos.append({
                "title": item["snippet"]["title"],
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}"
            })
    return videos

def post_to_x(text):
    url = "https://api.twitter.com/2/tweets"
    data = {"text": text[:280]}
    r = requests.post(url, auth=auth, json=data)
    return r.json()

def generate_post(post_type):
    videos = get_top_videos()
    if not videos:
        return None
    video = random.choice(videos)
    
    if post_type == "week_back":
        return f"📊 Afgelopen week in de politiek:\n\n• Asieldebatten trending\n• Klimaat zorgt voor verdeeldheid\n• Zorg blijft hot topic\n\n👇 Beste video: {video['title'][:50]}\n{video['url']}\n\n#Bassiehof #Politiek"
    
    elif post_type == "week_ahead":
        return f"🔮 Aankomende week in de Tweede Kamer:\n\n• Vragenuur dinsdag\n• Debatten over migratie\n• Stikstofdiscussie\n\n📺 Blijf kijken voor de beste clips!\n\n#Bassiehof #Politiek"
    
    elif post_type == "hot_topic":
        topic = random.choice(list(TOPICS.keys()))
        return f"🔥 {TOPICS[topic]} barst los!\n\nDe discussieover {TOPICS[topic].lower()} wordt steeds intensiever.\n\n👉 {video['title'][:50]}\n{video['url']}\n\n#Bassiehof #{TOPICS[topic]}"
    
    elif post_type == "question":
        q = random.choice([
            "Wie had deze week het beste argument?",
            "Welk debat wilt u volgende week?",
            "Welke politicus verraste u?"
        ])
        return f"🤔 {q}\n\nReageer hieronder! 👇\n\n#Bassiehof #Discussie"
    
    else:
        return f"📺 Nieuwe debate clip!\n\n{video['title'][:80]}\n{video['url']}\n\n#Bassiehof #Politiek"

def run():
    print("="*50)
    print("📱 SOCIAL MEDIA AGENT")
    print("="*50)
    
    today = datetime.now().weekday()
    
    if today == 4:  # Vrijdag - terugkijken
        post_type = "week_back"
    elif today == 0:  # Maandag - vooruitkijken
        post_type = "week_ahead"
    else:
        post_type = random.choice(["hot_topic", "question"])
    
    post = generate_post(post_type)
    
    if post:
        print(f"📝 Post: {post[:80]}...")
        result = post_to_x(post)
        if "data" in result:
            print(f"✅ Gepost! ID: {result['data']['id']}")
        else:
            print(f"❌ Error: {result}")

if __name__ == "__main__":
    run()
