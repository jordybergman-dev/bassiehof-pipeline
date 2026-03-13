#!/usr/bin/env python3
"""
YouTube + Analytics Token Refresh
"""
import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "youtube_token.pkl"

# ALLE SCRAPES - YouTube Data + Analytics
SCOPES = [
    # YouTube Data API
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload", 
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    # YouTube Analytics API
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
    # Cloud
    "https://www.googleapis.com/auth/cloud-platform"
]

def main():
    print("="*50)
    print("YouTube + Analytics Token Refresh")
    print("="*50)
    print("Kies Bassiehof kanaal!")
    print("Accepteer ALLE permissies die gevraagd worden!")
    print("="*50)
    
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    
    if creds and hasattr(creds, 'expired') and creds.expired and creds.refresh_token:
        print("Refreshing...")
        creds.refresh(Request())
    else:
        print("Starting OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=8080)
    
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)
    
    print("✅ Token opgeslagen!")
    print(f"Scopes: {creds.scopes}")

if __name__ == "__main__":
    main()
