#!/bin/bash
# One-time setup of the free STREAM-ONLY server (Oracle VM.Standard.E2.1.Micro, Ubuntu). Runs as cloud-init or by hand:
#   bash ~/vijay-news-server/server/stream_setup.sh english
set -e
CH="${1:-english}"; ME="${SUDO_USER:-$(whoami)}"; [ "$ME" = root ] && ME=ubuntu
HOMEDIR=$(getent passwd "$ME" | cut -d: -f6)
sudo timedatectl set-timezone Asia/Kolkata || true
# 1 GB RAM: add 2 GB swap so apt and ffmpeg never run out of memory
if ! swapon --show | grep -q /swapfile; then sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab; fi
sudo apt-get update -y && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg jq curl git
[ -d "$HOMEDIR/vijay-news-server" ] || sudo -u "$ME" git clone --depth 1 https://github.com/jpjaytheertha-hash/vijay-news-server "$HOMEDIR/vijay-news-server"
sudo tee /etc/systemd/system/vijaynews-stream@.service > /dev/null <<UNIT
[Unit]
Description=Vijay News %i – 24x7 YouTube stream (videos made on GitHub Actions)
After=network-online.target
Wants=network-online.target
[Service]
User=$ME
ExecStartPre=-/usr/bin/git -C $HOMEDIR/vijay-news-server pull -q --ff-only
ExecStart=/bin/bash $HOMEDIR/vijay-news-server/server/stream.sh %i
Restart=always
RestartSec=15
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable "vijaynews-stream@$CH"
sudo systemctl restart "vijaynews-stream@$CH"
echo "Set up ✓  Now type the stream key:  bash ~/vijay-news-server/server/stream_keys.sh $CH"
echo "Status:  tail -5 ~/vn-stream/$CH/stream.log"
