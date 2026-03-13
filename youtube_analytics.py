#!/usr/bin/env python3
"""
YouTube Analytics Agent
Analyseert video prestaties en stelt verbeteringen voor
"""
import os
import json
import pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build

BASE = "/root/bassiehof-pipeline"
TOKEN_FILE = os.path.join(BASE, "youtube_token.pkl")
ANALYTICS_FILE = os.path.join(BASE, "analytics.json")

def get_yt():
    """YouTube API connectie"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if creds and creds.valid:
        return build("youtube", "v3", credentials=creds)
    return None

def get_channel_videos(yt, channel_id, max_results=50):
    """Haal alle video's van kanaal"""
    videos = []
    request = yt.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=max_results,
        order="date"
    )
    
    while request:
        response = request.execute()
        for item in response.get("items", []):
            if item["id"]["kind"] == "youtube#video":
                videos.append({
                    "id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published": item["snippet"]["publishedAt"]
                })
        request = yt.search().list_next(request, response)
    
    return videos

def get_video_stats(yt, video_ids):
    """Haal statistieken voor video's"""
    if not video_ids: return []
    
    request = yt.videos().list(
        part="statistics,snippet,contentDetails",
        id=",".join(video_ids)
    )
    response = request.execute()
    
    stats = []
    for item in response.get("items", []):
        stats.append({
            "id": item["id"],
            "title": item["snippet"]["title"],
            "views": int(item["statistics"].get("viewCount", 0)),
            "likes": int(item["statistics"].get("likeCount", 0)),
            "comments": int(item["statistics"].get("commentCount", 0)),
            "duration": item["contentDetails"]["duration"],
            "published": item["snippet"]["publishedAt"]
        })
    
    return stats

def analyze_performance(videos):
    """Analyseer video prestaties"""
    if not videos:
        return {"error": "Geen video's gevonden"}
    
    # Sorteer op views
    sorted_by_views = sorted(videos, key=lambda x: x["views"], reverse=True)
    sorted_by_likes = sorted(videos, key=lambda x: x["likes"], reverse=True)
    
    total_views = sum(v["views"] for v in videos)
    total_likes = sum(v["likes"] for v in videos)
    avg_views = total_views / len(videos) if videos else 0
    
    # Beste video's
    top_5 = sorted_by_views[:5]
    
    # Analyse
    analysis = {
        "total_videos": len(videos),
        "total_views": total_views,
        "total_likes": total_likes,
        "avg_views": int(avg_views),
        "top_performers": top_5,
        "recommendations": []
    }
    
    # Recommendations
    for video in top_5[:3]:
        analysis["recommendations"].append({
            "type": "reuse_format",
            "video": video["title"],
            "views": video["views"],
            "suggestion": "Gebruik zelfde formaat/titel stijl"
        })
    
    # Tags analyse
    titles = [v["title"] for v in videos]
    short_count = sum(1 for t in titles if "short" in t.lower())
    long_count = len(titles) - short_count
    
    if short_count > long_count * 2:
        analysis["recommendations"].append({
            "type": "more_long",
            "suggestion": "Meer long-form video's maken"
        })
    
    return analysis

def get_improvements(analysis):
    """Genereer specifieke verbeteringen"""
    improvements = []
    
    # Check top performer titles
    if analysis.get("top_performers"):
        best = analysis["top_performers"][0]
        improvements.append(f"Beste video: '{best['title']}' ({best['views']} views)")
    
    # Views compare
    if analysis.get("avg_views", 0) < 1000:
        improvements.append("💡 Tip:Probeer meer clickbait titels")
    
    return improvements

def run_analysis():
    """Main analysis"""
    print("📊 YouTube Analytics Agent")
    print("="*40)
    
    yt = get_yt()
    if not yt:
        print("❌ Geen YouTube connectie")
        return
    
    # Haal kanaal info
    channel_request = yt.channels().list(mine=True, part="snippet,statistics")
    channel_response = channel_request.execute()
    
    if not channel_response.get("items"):
        print("❌ Geen kanaal gevonden")
        return
    
    channel = channel_response["items"][0]
    channel_id = channel["id"]
    channel_name = channel["snippet"]["title"]
    
    print(f"📺 Kanaal: {channel_name}")
    print(f"👀 Abonnees: {channel['statistics']['itemCount']}")
    
    # Video's ophalen
    videos = get_channel_videos(yt, channel_id, max_results=50)
    print(f"📹 Video's: {len(videos)}")
    
    if not videos:
        print("❌ Geen video's gevonden")
        return
    
    # Stats ophalen
    video_ids = [v["id"] for v in videos]
    stats = get_video_stats(yt, video_ids)
    
    # Analyseren
    analysis = analyze_performance(stats)
    
    print(f"\n📈 Analyse:")
    print(f"   Totaal views: {analysis['total_views']:,}")
    print(f"   Gemiddeld: {analysis['avg_views']:,}")
    
    print(f"\n🏆 Top 3:")
    for i, v in enumerate(analysis["top_performers"][:3], 1):
        print(f"   {i}. {v['title'][:40]} - {v['views']:,} views")
    
    print(f"\n💡 Verbeteringen:")
    for imp in get_improvements(analysis):
        print(f"   • {imp}")
    
    # Save to file
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n✅ Analyse opgeslagen!")
    return analysis

if __name__ == "__main__":
    run_analysis()
