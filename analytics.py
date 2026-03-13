#!/usr/bin/env python3
"""
Analytics - Volg video prestaties
"""
import os
import json
from datetime import datetime

ANALYTICS_FILE = "/root/bassiehof-pipeline/analytics.json"

def track_upload(video_title, video_type, platform="youtube"):
    """Track upload"""
    data = load_analytics()
    data["uploads"].append({
        "date": datetime.now().isoformat(),
        "title": video_title[:50],
        "type": video_type,
        "platform": platform,
        "views": 0,
        "likes": 0
    })
    save_analytics(data)

def update_stats(video_title, views, likes):
    """Update stats"""
    data = load_analytics()
    for entry in data["uploads"]:
        if entry["title"] == video_title[:50]:
            entry["views"] = views
            entry["likes"] = likes
    save_analytics(data)

def get_top_performing():
    """Haal beste presterende video's"""
    data = load_analytics()
    sorted_videos = sorted(data["uploads"], key=lambda x: x["views"], reverse=True)
    return sorted_videos[:5]

def load_analytics():
    try:
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    except:
        return {"uploads": [], "stats": {}}

def save_analytics(data):
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    print("Analytics tracking ready!")
