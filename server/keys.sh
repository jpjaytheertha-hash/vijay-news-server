#!/bin/bash
# Type the secret keys yourself (they are saved only on this server, readable only by you).
umask 077
if [ ! -s "$HOME/.vijaynews_streamkey" ]; then
  echo "Paste the YouTube STREAM KEY (YouTube Studio > Go live > Stream > Stream key), then Enter (not shown):"
  read -r -s K; echo; [ -n "$K" ] && printf "%s" "$K" > "$HOME/.vijaynews_streamkey"
fi
if [ ! -s "$HOME/.vijaynews_gemini_key" ]; then
  echo "Paste the Google Gemini API key (the one used for the Puck voice), then Enter (not shown):"
  read -r -s K; echo; [ -n "$K" ] && printf "%s" "$K" > "$HOME/.vijaynews_gemini_key"
fi
ls -l "$HOME"/.vijaynews_streamkey "$HOME"/.vijaynews_gemini_key 2>/dev/null | awk '{print "saved:", $NF}'
