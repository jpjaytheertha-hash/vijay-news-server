#!/bin/bash
# Vijay News – one-time setup for the daily upload of yesterday's bulletins (YouTube Data API).
# 1. Put the OAuth "Desktop app" client file from Google Cloud (client_secret_....json) in Downloads.
# 2. Double-click this file. Chrome opens: sign in, choose the "Vijay News" channel, allow.
cd "$(dirname "$0")" || exit 1
CLIENT="$HOME/.vijaynews_yt_client.json"
if [ ! -s "$CLIENT" ]; then
  F="$(ls -t "$HOME"/Downloads/client_secret*.json 2>/dev/null | head -1)"
  [ -z "$F" ] && { echo "No client_secret_....json found in Downloads. Download it from Google Cloud first."; read -r -p "Press Enter to close"; exit 1; }
  cp "$F" "$CLIENT" && chmod 600 "$CLIENT" && echo "Using $F"
fi
[ -f .venv/bin/activate ] && source .venv/bin/activate
python3 yt_upload.py auth && python3 yt_upload.py dry && echo && echo "Uploading any finished days now (runs in the background)…" \
  && (nohup python3 yt_upload.py daily >/dev/null 2>&1 &)
read -r -p "Done. Press Enter to close"
