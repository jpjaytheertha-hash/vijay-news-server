#!/bin/bash
# Vijay News – 24x7 live loop on the Oracle Cloud server (same job as GO_LIVE.command on the Mac).
# - Streams the newest bulletin + promo to YouTube without re-encoding.
# - Renders a new video whenever bulletin.json changes (delivered through GitHub by the scheduled tasks;
#   server/pull.sh fetches it every 2 minutes).
# - Restarts the stream automatically if it drops. Run by systemd (vijaynews-live.service).
cd "$(dirname "$0")/.." || exit 1
KEYFILE="$HOME/.vijaynews_streamkey"
[ -s "$KEYFILE" ] || { echo "$(date) no stream key – run: bash server/keys.sh"; sleep 300; exit 1; }
URL="rtmp://a.rtmp.youtube.com/live2/$(cat "$KEYFILE")"
VOICE="${VN_VOICE:-kn-IN-GaganNeural}"
LOG="live.log"; exec > >(tee -a "$LOG") 2>&1
source .venv/bin/activate

render_if_needed() {
  [ -f .rendering ] && return
  local latest; latest="$(ls -t vijay_news_*.mp4 2>/dev/null | head -1)"
  if [ -z "$latest" ] || [ bulletin.json -nt "$latest" ]; then
    touch .rendering; echo "$(date '+%F %H:%M') new bulletin.json – rendering…"
    ( NAME="vijay_news_$(date +%Y%m%d_%H%M).mp4"
      if VN_TTS=auto VN_VOICE="$VOICE" nice -n 10 python3 make_bulletin.py bulletin.json render_tmp.mp4 > render.log 2>&1; then
        mv render_tmp.mp4 "$NAME"; echo "$(date '+%F %H:%M') ready: $NAME"
        find . -maxdepth 1 -name 'vijay_news_*.mp4' -mtime +3 -delete 2>/dev/null
      else echo "$(date '+%F %H:%M') render FAILED – see render.log"; fi
      rm -f .rendering ) &
  fi
}
promo_stamp() { cat promo.py promo_clips/*.mp4 presenter_promos/*.mp4 2>/dev/null | md5sum | cut -c1-12; }
render_promo_if_needed() {
  [ -f .rendering_promo ] && return
  local now; now="$(promo_stamp)"
  if [ ! -f promo.mp4 ] || [ "$now" != "$(cat .promo_stamp 2>/dev/null)" ]; then
    if [ ! -f .promo_stamp ] && [ -f promo.mp4 ]; then echo "$now" > .promo_stamp; return; fi   # first start: use promo.mp4 from the repo
    touch .rendering_promo
    ( if VN_TTS=auto VN_VOICE="$VOICE" nice -n 10 python3 promo.py promo_tmp.mp4 > promo.log 2>&1; then
        mv promo_tmp.mp4 promo.mp4; echo "$now" > .promo_stamp; echo "$(date '+%F %H:%M') promo ready"
      else echo "promo render failed – see promo.log"; fi
      rm -f .rendering_promo ) &
  fi
}

echo "=== Vijay News LIVE (server) $(date '+%F %H:%M') ==="
rm -f .rendering .rendering_promo
render_promo_if_needed; render_if_needed
while true; do
  LATEST="$(ls -t vijay_news_*.mp4 2>/dev/null | head -1)"
  if [ -z "$LATEST" ]; then echo "Waiting for the first bulletin…"; sleep 30; render_if_needed; continue; fi
  printf "file '%s'\n" "$PWD/$LATEST" > playlist.txt
  [ -f promo.mp4 ] && printf "file '%s'\n" "$PWD/promo.mp4" >> playlist.txt
  echo "$(date '+%F %H:%M') LIVE: $LATEST + promo"
  ffmpeg -hide_banner -loglevel error -re -stream_loop 1 -f concat -safe 0 -i playlist.txt -c copy -f flv "$URL"
  [ $? -ne 0 ] && { echo "$(date '+%F %H:%M') stream dropped – retrying in 5 s"; sleep 5; }
  render_if_needed; render_promo_if_needed
done
