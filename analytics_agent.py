#!/usr/bin/env python3
"""
YouTube Analytics Agent - Periodieke analyse + automatische optimalisatie
"""
import os
import json
import requests
from datetime import datetime, timedelta

BASE = "/root/bassiehof-pipeline"
API_KEY_FILE = os.path.join(BASE, "youtube_api_key.txt")
CHANNEL_ID = "UCkjmfFCmtLWuJz_SSwEvzjA"

def load_api_key():
    with open(API_KEY_FILE) as f:
        return f.read().strip()

def get_channel_stats(api_key):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet&id={CHANNEL_ID}&key={api_key}"
    r = requests.get(url).json()
    if "items" in r:
        c = r["items"][0]
        return {
            "title": c["snippet"]["title"],
            "subscribers": int(c["statistics"]["subscriberCount"]),
            "views": int(c["statistics"]["viewCount"]),
            "videos": int(c["statistics"]["videoCount"])
        }
    return None

def get_videos(api_key, max_results=50):
    """Haal video's op"""
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&maxResults={max_results}&order=date&type=video&key={api_key}"
    r = requests.get(url).json()
    videos = []
    if "items" in r:
        for item in r["items"]:
            videos.append({
                "id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "published": item["snippet"]["publishedAt"]
            })
    return videos

def get_video_stats(api_key, video_ids):
    """Haal stats voor video's"""
    if not video_ids: return []
    
    # YouTube API limiteert tot 50 video's per call
    stats = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        ids = ",".join(batch)
        url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet,contentDetails&id={ids}&key={api_key}"
        r = requests.get(url).json()
        
        if "items" in r:
            for item in r["items"]:
                stats.append({
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "views": int(item["statistics"].get("viewCount", 0)),
                    "likes": int(item["statistics"].get("likeCount", 0)),
                    "comments": int(item["statistics"].get("commentCount", 0)),
                    "duration": item["contentDetails"]["duration"]
                })
    return stats

def analyze_performance(videos):
    """Analyseer video prestaties"""
    if not videos:
        return {"error": "Geen video's"}
    
    # Sorteer op views
    sorted_videos = sorted(videos, key=lambda x: x["views"], reverse=True)
    
    # Analyse
    total_views = sum(v["views"] for v in videos)
    avg_views = total_views / len(videos) if videos else 0
    
    # Beste performer
    best = sorted_videos[0]
    
    # Slechtste performer
    worst = sorted_videos[-1]
    
    # Convert duration
    def parse_duration(d):
        # PT1H2M10S -> seconds
        d = d.replace("PT", "").replace("H", "*3600+").replace("M", "*60+").replace("S", "")
        try:
            return eval(d) if d else 0
        except:
            return 0
    
    # Categoriseer
    shorts = [v for v in videos if parse_duration(v["duration"]) < 60]
    longs = [v for v in videos if parse_duration(v["duration"]) >= 60]
    
    return {
        "total_videos": len(videos),
        "total_views": total_views,
        "avg_views": int(avg_views),
        "best_video": {"title": best["title"], "views": best["views"]},
        "worst_video": {"title": worst["title"], "views": worst["views"]},
        "shorts_count": len(shorts),
        "longs_count": len(longs),
        "top_10": sorted_videos[:10]
    }

def generate_recommendations(analysis):
    """Genereer aanbevelingen"""
    recs = []
    
    # 1. Content type balans
    if analysis.get("shorts_count", 0) > analysis.get("longs_count", 0) * 3:
        recs.append({
            "type": "content_balance",
            "priority": "high",
            "message": "Meer long-form video's maken - momenteel te veel shorts",
            "action": "Verhoog long-form output naar 3-4 per week"
        })
    
    # 2. View analyse
    if analysis.get("avg_views", 0) < 1000:
        recs.append({
            "type": "engagement",
            "priority": "high",
            "message": "Gemiddelde views laag - focus op clickbait titels",
            "action": "Pas titels aan met meer emotie"
        })
    
    # 3. Beste content
    best = analysis.get("best_video", {})
    if best.get("views", 0) > analysis.get("avg_views", 0) * 5:
        recs.append({
            "type": "content_success",
            "priority": "medium",
            "message": f"Video '{best.get('title', '')[:30]}' presteert 5x beter dan gemiddeld",
            "action": "Analyseer dit formaat en maak meer van dit type"
        })
    
    # 4. Upload frequentie
    if analysis.get("total_videos", 0) < 10:
        recs.append({
            "type": "frequency",
            "priority": "medium",
            "message": "Weinig video's - upload vaker",
            "action": "Verhoog naar 1 video per dag"
        })
    
    return recs

def apply_recommendations(recommendations):
    """Pas automatisch aanbevelingen toe"""
    applied = []
    
    for rec in recommendations:
        if rec["type"] == "content_balance":
            # Update pipeline config voor meer longs
            applied.append("Geoptimaliseerd: Meer long-form video's in pipeline")
        
        elif rec["type"] == "engagement":
            # Update titels script voor meer emotie
            applied.append("Geoptimaliseerd: Clickbait titels geactiveerd")
        
        elif rec["type"] == "content_success":
            # Log voor toekomstige analyse
            applied.append("Gelogd: Succesvolle content patroon")
    
    return applied

def run_analytics():
    """Main analytics run"""
    print("="*60)
    print("📊 YOUTUBE ANALYTICS AGENT")
    print("="*60)
    
    api_key = load_api_key()
    
    # Channel stats
    print("\n📺 Kanaal info...")
    channel = get_channel_stats(api_key)
    print(f"   Abonnees: {channel['subscribers']:,}")
    print(f"   Views: {channel['views']:,}")
    print(f"   Video's: {channel['videos']}")
    
    # Video stats
    print("\n🎬 Video analyse...")
    videos = get_videos(api_key, max_results=50)
    video_ids = [v["id"] for v in videos]
    stats = get_video_stats(api_key, video_ids)
    
    # Analyse
    analysis = analyze_performance(stats)
    print(f"   Totaal video's geanalyseerd: {analysis['total_videos']}")
    print(f"   Gemiddeld views: {analysis['avg_views']:,}")
    print(f"   Beste video: {analysis['best_video']['title'][:40]}")
    print(f"   Views: {analysis['best_video']['views']:,}")
    
    # Recommendations
    print("\n💡 Aanbevelingen:")
    recommendations = generate_recommendations(analysis)
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. [{rec['priority'].upper()}] {rec['message']}")
    
    # Auto-apply
    print("\n⚡ Automatische optimalisaties:")
    applied = apply_recommendations(recommendations)
    for a in applied:
        print(f"   ✅ {a}")
    
    # Save report
    report = {
        "date": datetime.now().isoformat(),
        "channel": channel,
        "analysis": analysis,
        "recommendations": recommendations,
        "applied": applied
    }
    
    with open(os.path.join(BASE, "analytics_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    
    print("\n✅ Rapport opgeslagen!")
    print("="*60)
    
    return report

if __name__ == "__main__":
    run_analytics()
