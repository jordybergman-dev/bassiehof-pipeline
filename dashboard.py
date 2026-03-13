#!/usr/bin/env python3
"""
WEEKELIJKS DASHBOARD - Bassiehof Agent Board
Combineert YouTube + X analytics en geeft aanbevelingen
"""
import os, json, requests
from datetime import datetime
from requests_oauthlib import OAuth1

BASE = "/root/bassiehof-pipeline"

# YouTube
YOUTUBE_API_KEY = open(os.path.join(BASE, "youtube_api_key.txt")).read().strip()
CHANNEL_ID = "UCkjmfFCmtLWuJz_SSwEvzjA"

# X
X_CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY", os.environ.get("X_CONSUMER_KEY", ""))
X_CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET", os.environ.get("X_CONSUMER_SECRET", ""))
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", os.environ.get("X_ACCESS_TOKEN", ""))
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", os.environ.get("X_ACCESS_SECRET", ""))
x_auth = OAuth1(X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)

# Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT", "8767320369:AAFwGKv5QIUH3t2jueTuTWSh5hGDTdu8CRM")
TELEGRAM_CHAT = "1523587806"

def telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}
    r = requests.post(url, json=data)
    return r.json()

def get_youtube_stats():
    """YouTube kanaal stats"""
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet&id={CHANNEL_ID}&key={YOUTUBE_API_KEY}"
    r = requests.get(url).json()
    if "items" in r:
        c = r["items"][0]
        return {
            "subscribers": int(c["statistics"]["subscriberCount"]),
            "views": int(c["statistics"]["viewCount"]),
            "videos": int(c["statistics"]["videoCount"]),
            "name": c["snippet"]["title"]
        }
    return {}

def get_youtube_top_videos():
    """Beste video's"""
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&maxResults=10&order=viewCount&type=video&key={YOUTUBE_API_KEY}"
    r = requests.get(url).json()
    videos = []
    if "items" in r:
        for item in r["items"]:
            videos.append({
                "title": item["snippet"]["title"],
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}"
            })
    return videos[:5]

def get_x_stats():
    """X stats"""
    url = "https://api.twitter.com/2/users/by/username/bassiehof?user.fields=public_metrics"
    r = requests.get(url, auth=x_auth)
    if r.status_code == 200:
        data = r.json().get("data", {})
        metrics = data.get("public_metrics", {})
        return {
            "followers": metrics.get("followers_count", 0),
            "following": metrics.get("following_count", 0),
            "tweets": metrics.get("tweet_count", 0)
        }
    return {}

def get_x_recent_posts():
    """Laatste X posts"""
    url = "https://api.twitter.com/2/users/me/tweets?max_results=5&tweet.fields=public_metrics"
    r = requests.get(url, auth=x_auth)
    posts = []
    if r.status_code == 200:
        for t in r.json().get("data", []):
            m = t.get("public_metrics", {})
            posts.append({
                "text": t.get("text", "")[:50],
                "likes": m.get("like_count", 0),
                "retweets": m.get("retweet_count", 0)
            })
    return posts

def generate_recommendations(yt_stats, x_stats):
    """Genereer aanbevelingen"""
    recs = []
    
    # YouTube
    if yt_stats.get("subscribers", 0) < 1000:
        recs.append("💡 Focus op shorts - algoritme belohnt volume")
    
    if x_stats.get("followers", 0) < 500:
        recs.append("💡 X: Vraag stellingen aan volgers voor meer interactie")
    
    return recs

def run_dashboard():
    print("="*50)
    print("📊 BASSIEHOF WEEK DASHBOARD")
    print("="*50)
    
    # YouTube
    print("\n📺 YouTube...")
    yt = get_youtube_stats()
    print(f"   Abonnees: {yt.get('subscribers', 0):,}")
    print(f"   Views: {yt.get('views', 0):,}")
    print(f"   Video's: {yt.get('videos', 0)}")
    
    # X
    print("\n🐦 X/Twitter...")
    x = get_x_stats()
    print(f"   Followers: {x.get('followers', 0)}")
    print(f"   Tweets: {x.get('tweets', 0)}")
    
    # Recommendations
    print("\n💡 Aanbevelingen:")
    recs = generate_recommendations(yt, x)
    for r in recs:
        print(f"   {r}")
    
    # Build report
    report = f"""
📊 <b>BASSIEHOF WEEK DASHBOARD</b>
📅 {datetime.now().strftime('%d-%m-%Y')}

📺 <b>YOUTUBE</b>
• Abonnees: {yt.get('subscribers', 0):,}
• Views: {yt.get('views', 0):,}
• Video's: {yt.get('videos', 0)}

🐦 <b>X/TWITTER</b>
• Followers: {x.get('followers', 0)}
• Tweets: {x.get('tweets', 0)}

💡 <b>AANBEVELINGEN</b>
{chr(10).join(recs)}

🎯 <b>VOLGENDE STAPPEN</b>
1. Test nieuwe titels
2. Post consistent
3. Focus op viral onderwerpen
"""
    
    # Send to Telegram
    print("\n📱 Verzenden naar Telegram...")
    telegram(report)
    print("✅ Verzonden!")
    
    # Save report
    with open(os.path.join(BASE, "dashboard_report.json"), "w") as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "youtube": yt,
            "twitter": x,
            "recommendations": recs
        }, f, indent=2)
    
    print("="*50)

if __name__ == "__main__":
    run_dashboard()
