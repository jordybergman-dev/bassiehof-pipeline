#!/usr/bin/env python3
"""
YouTube + Analytics Token Refresh - Force new consent
"""
import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "youtube_token.pkl"

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload", 
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"
]

def main():
    print("="*50)
    print("YouTube + Analytics - Force New Consent")
    print("="*50)
    
    # Verwijder oude token
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print("Oude token verwijderd")
    
    print("Starting NEW OAuth flow...")
    print("Kies Bassiehof kanaal!")
    print("Accepteer ALLE permissies!")
    print("="*50)
    
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(port=8080, prompt='consent')
    
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)
    
    print("✅ Token opgeslagen!")
    print(f"Scopes: {creds.scopes}")

if __name__ == "__main__":
    main()
