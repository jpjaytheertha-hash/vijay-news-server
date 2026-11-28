#!/bin/bash
# Vijay News – STREAM-ONLY 24x7 loop for a tiny free Oracle server (VM.Standard.E2.1.Micro, Always Free).
# The videos are made in the cloud by GitHub Actions and published as release assets; this script only
# downloads the newest bulletin.mp4 + promo.mp4 and relays them to YouTube WITHOUT re-encoding (almost no CPU).
#   usage: stream.sh english   (release "english-live", key ~/.vijaynews_en_streamkey)
#          stream.sh kannada   (release "kannada-live", key ~/.vijaynews_streamkey) – for later
# Keeps only the current files on disk (old ones are removed after each switch) → a few hundred MB per channel.
CH="${1:-english}"
REPO="${VN_REPO:-jpjaytheertha-hash/vijay-news-server}"
case "$CH" in
  english) KEYFILE="$HOME/.vijaynews_en_streamkey" ;;
  kannada) KEYFILE="$HOME/.vijaynews_streamkey" ;;
  *) echo "unknown channel $CH"; exit 1 ;;
esac
DIR="$HOME/vn-stream/$CH"; mkdir -p "$DIR"; cd "$DIR" || exit 1
exec >> stream.log 2>&1
API="https://api.github.com/repos/$REPO/releases/tags/$CH-live"
[ -s "$KEYFILE" ] || { echo "$(date '+%F %H:%M') no stream key for $CH – run: bash ~/vijay-news-server/server/stream_keys.sh $CH"; sleep 300; exit 1; }
URL="rtmp://a.rtmp.youtube.com/live2/$(cat "$KEYFILE")"
PROG="$DIR/progress.txt"; PID=""; CUR=""

# fetch(): download a release asset if its id changed → file <name>_<id>.mp4 ; prints the local file name
fetch() {   # $1 = asset name (bulletin.mp4 | promo.mp4)
  local id url f
  id=$(jq -r --arg n "$1" '.assets[] | select(.name==$n) | .id' release.json 2>/dev/null)
  [ -z "$id" ] || [ "$id" = "null" ] && { ls -t "${1%.mp4}"_*.mp4 2>/dev/null | head -1; return; }
  f="${1%.mp4}_$id.mp4"
  if [ ! -s "$f" ]; then
    url=$(jq -r --arg n "$1" '.assets[] | select(.name==$n) | .browser_download_url' release.json)
    if curl -fsSL --http1.1 --retry 5 --retry-all-errors --retry-delay 5 -m 1800 -o "$f.part" "$url" && ffprobe -v error -show_entries format=duration -of csv=p=0 "$f.part" > /dev/null; then
      mv "$f.part" "$f"; echo "$(date '+%F %H:%M') downloaded $f ($(du -h "$f" | cut -f1))" >&2
    else rm -f "$f.part"; ls -t "${1%.mp4}"_*.mp4 2>/dev/null | grep -v "$f" | head -1; return; fi
  fi
  echo "$f"
}
refresh() {
  curl -fsS --http1.1 --retry 3 -m 30 -H "Accept: application/vnd.github+json" "$API" -o release.json.new && mv release.json.new release.json
  B=$(fetch bulletin.mp4); P=$(fetch promo.mp4)
}
start_stream() {
  : > playlist.txt
  [ -n "$B" ] && printf "file '%s'\n" "$DIR/$B" >> playlist.txt
  [ -n "$P" ] && printf "file '%s'\n" "$DIR/$P" >> playlist.txt
  CUR="$B|$P"; : > "$PROG"
  echo "$(date '+%F %H:%M') LIVE ($CH): $B + $P"
  ffmpeg -hide_banner -loglevel error -re -stream_loop -1 -f concat -safe 0 -i playlist.txt -c copy \
    -progress "$PROG" -stats_period 5 -f flv "$URL" &
  PID=$!
}
stop_stream() { [ -n "$PID" ] && kill "$PID" 2>/dev/null; sleep 2; [ -n "$PID" ] && kill -9 "$PID" 2>/dev/null; wait "$PID" 2>/dev/null; PID=""; }
cleanup_old() {   # keep only the files in use (saves disk on the 47 GB free server)
  for f in bulletin_*.mp4 promo_*.mp4; do [ -e "$f" ] || continue; case "$CUR" in *"$f"*) ;; *) rm -f "$f";; esac; done
}
trap 'stop_stream; exit 0' INT TERM
echo "=== Vijay News $CH stream server $(date '+%F %H:%M') ==="
sleep 15   # let YouTube close any previous connection first
T=0
while true; do
  if [ $T -le 0 ]; then refresh; T=9; fi     # check GitHub every ~3 minutes (well inside the free API limit)
  T=$((T-1))
  # no bulletin yet → stream the promo alone (it is replaced by bulletin + promo as soon as a bulletin is published)
  if [ -z "$B" ] && [ -z "$P" ]; then echo "$(date '+%F %H:%M') waiting for the first video from GitHub…"; sleep 60; T=0; continue; fi
  if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
    [ -n "$PID" ] && { echo "$(date '+%F %H:%M') stream dropped – restarting in 20 s"; sleep 20; }
    start_stream; cleanup_old
  elif [ "$B|$P" != "$CUR" ]; then
    echo "$(date '+%F %H:%M') new video – switching"; stop_stream; sleep 20; start_stream; cleanup_old
  elif [ -f "$PROG" ] && [ $(( $(date +%s) - $(stat -c %Y "$PROG") )) -gt 60 ]; then
    echo "$(date '+%F %H:%M') stream stalled – reconnecting"; stop_stream; sleep 20; start_stream
  fi
  sleep 20
done
