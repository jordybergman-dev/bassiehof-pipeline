#!/usr/bin/env python3
"""
Social Media Agent - Politieke content generator
Post 1-2x per dag naar X/Twitter
"""
import os
import requests
from requests_oauthlib import OAuth1
from datetime import datetime
import json
import random

# X Credentials
CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY", "4DHzgY5szwxKGg1XMG6L84emn")
CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET", "b8czGuw3CVXXo6q7JLNjFyBrGGZg0abDGnIItbNzY6AhdiyCG2")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "1701510127746965504-60tQ6PdnNfAnmvq8kjyGfSKqwRYnlm")
ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "zfDe9DwaRM0L89kP90WyurSo26XhgOqMUaMeQuxelFieK")

auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET)

# API Key for YouTube
YOUTUBE_API_KEY = open("/root/bassiehof-pipeline/youtube_api_key.txt").read().strip()
CHANNEL_ID = "UCkjmfFCmtLWuJz_SSwEvzjA"

# Content templates
POST_TEMPLATES = [
    # Week samenvatting
    "📊 Deze week in de politiek:\n\n{topics}\n\n👇 Beste video: {video_title}\n{video_url}\n\n#Bassiehof #Politiek",
    
    # Hot topic
    "🔥 {topic} barst los in de Tweede Kamer!\n\n{summary}\n\n👉 Kijk de reacties: {video_title}\n{video_url}\n\n#Bassiehof #{hashtag}",
    
    # Vraag aan volgers
    "🤔 Vraag aan jullie:\n\n{question}\n\nLaat weten in de reacties! 👇\n\n#Bassiehof #Discussie",
    
    # Politicus spotlight
    "🎯 {politician} vandaag in het nieuws:\n\n{news}\n\nKijk de clip: {video_title}\n{video_url}\n\n#Bassiehof #{party}",
    
    # Weekend samenvatting
    "📅 Week-end samenvatting:\n\n{highlights}\n\n💡 Binnenkort meer debate clips!\n\n#Bassiehof #Politiek"
]

# Politieke onderwerpen om te tracken
TOPICS = {
    "asiel": {"hashtag": "Asiel", "party": "PVV"},
    "migratie": {"hashtag": "Migratie", "party": "PVV"},
    "klimaat": {"hashtag": "Klimaat", "party": "GroenLinks"},
    "zorg": {"hashtag": "Zorg", "party": "BBB"},
    "pensioen": {"hashtag": "Pensioen", "party": "SP"},
    "stikstof": {"hashtag": "Stikstof", "party": "BBB"},
    "economie": {"hashtag": "Economie", "party": "VVD"},
    "onderwijs": {"hashtag": "Onderwijs", "party": "D66"},
    "veiligheid": {"hashtag": "Veiligheid", "party": "PVV"},
    "europa": {"hashtag": "Europa", "party": "GL"}
}

def get_top_videos():
    """Haal top viral video's op"""
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

def generate_post(post_type="random"):
    """Genereer een post"""
    videos = get_top_videos()
    
    if not videos:
        return None
    
    video = random.choice(videos)
    
    if post_type == "week_summary":
        topics = "• Asieldebat was trending\n• Klimaatbeleid sorgt voor chaos\n• Zorg nog steeds hoofdonderwerp"
        template = POST_TEMPLATES[0]
        return template.format(
            topics=topics,
            video_title=video["title"][:50],
            video_url=video["url"]
        )
    
    elif post_type == "hot_topic":
        topic = random.choice(list(TOPICS.keys()))
        template = POST_TEMPLATES[1]
        return template.format(
            topic=topic.capitalize(),
            summary=f"De discussie over {topic} wordt steeds intensiever in de Kamer.",
            video_title=video["title"][:50],
            video_url=video["url"],
            hashtag=TOPICS[topic]["hashtag"]
        )
    
    elif post_type == "question":
        questions = [
            "Wie heeft deze week het beste debat geleverd?",
            "Welk onderwerp zou jij willen bespreken?",
            "Welke politicus verraste je deze week?"
        ]
        template = POST_TEMPLATES[2]
        return template.format(question=random.choice(questions))
    
    elif post_type == "politician":
        politicians = ["Wilders", "Van der Plas", "Klaver", "Piri", "Keijzer"]
        politician = random.choice(politicians)
        parties = {"Wilders": "PVV", "Van der Plas": "BBB", "Klaver": "GroenLinks", "Piri": "GL-PvdA", "Keijzer": "BBB"}
        template = POST_TEMPLATES[3]
        return template.format(
            politician=politician,
            news=f"{politician} stond vandaag in de spotlight.",
            video_title=video["title"][:50],
            video_url=video["url"],
            party=parties.get(politician, "Politiek")
        )
    
    else:  # random
        template = random.choice(POST_TEMPLATES[1:4])
        topic = random.choice(list(TOPICS.keys()))
        return template.format(
            topic=topic.capitalize(),
            summary=f"Nieuws over {topic} uit de Tweede Kamer.",
            video_title=video["title"][:50],
            video_url=video["url"],
            hashtag=TOPICS[topic]["hashtag"],
            question=random.choice(["Wat vind jij?", "Jouw mening?", "Laat het weten!"]),
            politician=random.choice(["Wilders", "Van der Plas", "Klaver"]),
            news="最新的政治新闻",
            party="PVV"
        )

def post_to_x(text):
    """Post naar X"""
    url = "https://api.twitter.com/2/tweets"
    data = {"text": text[:280]}  # Max 280 chars
    
    r = requests.post(url, auth=auth, json=data)
    return r.json()

def run_social_agent():
    """Main agent"""
    print("="*50)
    print("📱 SOCIAL MEDIA AGENT")
    print("="*50)
    
    # Kies post type
    today = datetime.now().weekday()
    
    if today == 0:  # Maandag: vooruitkijken
        post_type = "week_summary"
    elif today == 0  # Maandag
        post_type = "week_ahead"
    elif today == 4:  # Vrijdag: terugkijken
        post_type = "hot_topic"
    elif today == 6:  # Zondag
        post_type = "weekend"
    else:
        post_type = random.choice(["hot_topic", "question", "politician"])
    
    # Genereer post
    post = generate_post(post_type)
    
    if post:
        print(f"📝 Post: {post[:100]}...")
        
        # Post
        result = post_to_x(post)
        
        if "data" in result:
            print(f"✅ Gepost! ID: {result['data']['id']}")
            return True
        else:
            print(f"❌ Error: {result}")
            return False
    else:
        print("❌ Geen video's gevonden")
        return False

if __name__ == "__main__":
    run_social_agent()
