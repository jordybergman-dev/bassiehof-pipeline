#!/usr/bin/env python3
"""
YouTube Token Refresh - Volledige toegang
"""
import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "youtube_token.pkl"

# ALLE SCRAPES - dit is belangrijk!
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",  
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

def main():
    print("YouTube Token Refresh")
    print("="*40)
    print("Let op: Accepteer ALLE permissies in de browser!")
    
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    
    if creds and creds.expired and creds.refresh_token:
        print("Refreshing...")
        creds.refresh(Request())
    else:
        print("Starting OAuth flow...")
        print("Kies je YouTube kanaal en accepteer ALLE permissies!")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=8080)
    
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)
    
    print("✅ Token opgeslagen!")
    print(f"Scopes: {creds.scopes}")

if __name__ == "__main__":
    main()
