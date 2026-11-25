#!/bin/bash
# One-time sign-in for the YouTube uploads (yesterday's bulletins + Shorts).
# First copy the Google Cloud OAuth "Desktop app" client JSON here:  ~/.vijaynews_yt_client.json
cd "$(dirname "$0")/.." || exit 1
[ -s "$HOME/.vijaynews_yt_client.json" ] || { echo "Missing ~/.vijaynews_yt_client.json – paste it with:  nano ~/.vijaynews_yt_client.json"; exit 1; }
chmod 600 "$HOME/.vijaynews_yt_client.json"
.venv/bin/python3 yt_upload.py auth && .venv/bin/python3 yt_upload.py dry
