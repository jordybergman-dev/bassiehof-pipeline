#!/usr/bin/env python3
"""
YouTube Token Refresh - Run locally om nieuwe token te krijgen
"""
import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "youtube_token.pkl"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",  # Voor analytics
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

def main():
    creds = None
    
    # Check bestaande token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    
    # Refresh of nieuw
    if creds and creds.expired and creds.refresh_token:
        print("Refreshing existing token...")
        creds.refresh(Request())
    else:
        print("Starting new OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=8080)
    
    # Save
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)
    
    print(f"✅ Token saved to {TOKEN_FILE}")
    print(f"Valid: {creds.valid}")

if __name__ == "__main__":
    main()
