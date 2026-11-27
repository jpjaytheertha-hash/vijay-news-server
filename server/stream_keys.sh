#!/bin/bash
# Type the YouTube stream key yourself (saved only on this server, readable only by you).
#   bash stream_keys.sh english   → Vijay News English (YouTube Studio of @VijayNewsEnglish > Go live > Stream > Stream key)
#   bash stream_keys.sh kannada   → Vijay News Kannada
CH="${1:-english}"; umask 077
case "$CH" in english) F="$HOME/.vijaynews_en_streamkey"; N="Vijay News ENGLISH";; kannada) F="$HOME/.vijaynews_streamkey"; N="Vijay News (Kannada)";; *) echo "english or kannada"; exit 1;; esac
echo "Paste the STREAM KEY of $N, then Enter (not shown):"; read -r -s K; echo
[ -n "$K" ] && printf "%s" "$K" > "$F" && echo "saved ✓" && sudo systemctl restart "vijaynews-stream@$CH" 2>/dev/null; true
