#!/bin/bash
# Fetch new bulletin.json / specials / code from GitHub (run every 2 minutes by vijaynews-pull.timer).
cd "$(dirname "$0")/.." || exit 1
before="$(git rev-parse HEAD)"
git fetch -q origin main && git reset -q --keep origin/main 2>>pull.log || git pull -q --ff-only origin main >>pull.log 2>&1
after="$(git rev-parse HEAD)"
[ "$before" != "$after" ] && echo "$(date '+%F %H:%M') updated $before -> $after: $(git diff --name-only "$before" "$after" | tr '\n' ' ')" >> pull.log
# Vijay: "ಶುಭೋದಯ" only in the morning, "ನಮಸ್ಕಾರ" from 11 AM – make_bulletin.py swaps the greeting by the clock,
# so at 11:00 just ask for a re-render once (touch keeps the file content unchanged).
if [ "$(date +%H)" -ge 11 ] && grep -q '"intro": *"ಶುಭೋದಯ' bulletin.json && [ ! -f ".greet_$(date +%F)" ]; then
  touch ".greet_$(date +%F)"; latest="$(ls -t vijay_news_*.mp4 2>/dev/null | head -1)"
  if [ -n "$latest" ] && [ "$(date -r "$latest" +%H)" -lt 11 ]; then touch bulletin.json; echo "$(date '+%F %H:%M') 11 AM greeting re-render" >> pull.log; fi
fi
