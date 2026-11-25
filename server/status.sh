#!/bin/bash
cd "$(dirname "$0")/.." || exit 1
systemctl is-active vijaynews-live.service vijaynews-pull.timer vijaynews-upload.timer | paste -sd' ' | sed 's/^/services: /'
echo "-- live.log";   tail -5 live.log 2>/dev/null
echo "-- render.log"; tail -2 render.log 2>/dev/null
echo "-- pull.log";   tail -3 pull.log 2>/dev/null
echo "-- upload.log"; tail -3 upload.log 2>/dev/null
df -h . | tail -1 | awk '{print "disk free:", $4}'
