#!/usr/bin/env python3
"""
Social Media Agent - Politieke content generator
"""
import os, requests, random
from datetime import datetime
from requests_oauthlib import OAuth1
import json

# X Credentials
CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY", os.environ.get("X_CONSUMER_KEY", ""))
CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET", os.environ.get("X_CONSUMER_SECRET", ""))
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", os.environ.get("X_ACCESS_TOKEN", ""))
ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", os.environ.get("X_ACCESS_SECRET", ""))

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

# Engagement analysis - after posting
def analyze_engagement(tweet_id):
    """Analyseer hoe een post presteert"""
    url = f"https://api.twitter.com/2/tweets/{tweet_id}?tweet.fields=public_metrics"
    r = requests.get(url, auth=auth)
    
    if r.status_code == 200:
        data = r.json()
        metrics = data.get("data", {}).get("public_metrics", {})
        
        return {
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "impressions": metrics.get("impression_count", 0)
        }
    return None

def get_best_performing_posts():
    """Haal beste presterende posts op"""
    # Laatste 20 tweets
    url = "https://api.twitter.com/2/users/me/tweets?max_results=20&tweet.fields=public_metrics"
    r = requests.get(url, auth=auth)
    
    if r.status_code == 200:
        tweets = r.json().get("data", [])
        
        # Sorteer op engagement
        sorted_tweets = sorted(tweets, key=lambda t: 
            t.get("public_metrics", {}).get("like_count", 0) + 
            t.get("public_metrics", {}).get("retweet_count", 0) * 2,
            reverse=True
        )
        
        return sorted_tweets[:5]
    return []

# X Monetization - je kunt dit toevoegen
MONETIZATION_OPTIONS = [
    # Affiliate links in bio
    "affiliate_link": "Je kunt affiliate links toevoegen aan je X bio",
    # Promoties
    "sponsored": "Gesponsorde posts (requires setup)",
    # Tips
    "tips": "X Tips (beschikbaar in bepaalde regio's)"
]

import urllib.request, urllib.parse

# Telegram for notifications
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT", "8767320369:AAFwGKv5QIUH3t2jueTuTWSh5hGDTdu8CRM")
TELEGRAM_CHAT = "1523587806"

def telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT, "text": msg}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
    except:
        pass

def check_followers():
    """Check follower count"""
    url = "https://api.twitter.com/2/users/me?tweet.fields=public_metrics"
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        data = r.json()
        user = data.get("data", {})
        followers = user.get("public_metrics", {}).get("followers_count", 0)
        return followers
    return 0

def run_engagement_analysis():
    """Analyseer engagement en geef rapport"""
    print("\n📊 ENGAGEMENT ANALYSE")
    print("="*40)
    
    # Check followers
    followers = check_followers()
    print(f"👥 Followers: {followers}")
    
    if followers >= 500:
        msg = f"🎉 GEFELICITEERD! Je hebt 500 volgers bereikt op X! 🎉"
        print(msg)
        telegram(msg)
    elif followers >= 400:
        print(f"💪 Bijna! Nog {500 - followers} volgers tot 500!")
    
    # Get recent tweets
    url = "https://api.twitter.com/2/users/me/tweets?max_results=10&tweet.fields=public_metrics"
    r = requests.get(url, auth=auth)
    
    if r.status_code == 200:
        tweets = r.json().get("data", [])
        
        print(f"\n📝 Laatste {len(tweets)} posts:")
        
        for tweet in tweets[:5]:
            metrics = tweet.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            rts = metrics.get("retweet_count", 0)
            replies = metrics.get("reply_count", 0)
            engagement = likes + rts * 2 + replies
            
            print(f"   ❤️ {likes} | 🔁 {rts} | 💬 {replies} | 📊 {engagement}")
        
        # Beste type post
        print("\n💡 Inzichten:")
        if tweets:
            best = max(tweets, key=lambda t: 
                t.get("public_metrics", {}).get("like_count", 0))
            print(f"   Beste post: {best.get('text', '')[:50]}...")
    print("="*40)
