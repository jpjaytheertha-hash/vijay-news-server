#!/bin/bash
# Vijay News – one-time server setup on Oracle Cloud (Ubuntu 22.04/24.04, Arm or x86).
# Run from the cloned repo:  bash ~/vijay-news/server/setup.sh
set -e
cd "$(dirname "$0")/.."
APP="$PWD"; ME="$(whoami)"
echo "== 1/5 time zone (IST) and packages"
sudo timedatectl set-timezone Asia/Kolkata
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg python3-venv python3-pip git curl fonts-noto-core
echo "== 2/5 Python packages"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q numpy scipy pillow edge-tts
echo "== 3/5 local state"
mkdir -p shorts build build_promo broll
[ -f shorts/uploaded.txt ] || cp server/shorts_uploaded_seed.txt shorts/uploaded.txt
for j in specials/*.json; do [ -e "$j" ] && touch "${j%.json}.done"; done      # specials already published from the Mac
git config core.sshCommand "ssh -i $HOME/.ssh/vijaynews_deploy -o StrictHostKeyChecking=accept-new"
chmod +x server/*.sh
echo "== 4/5 background services"
sudo tee /etc/systemd/system/vijaynews-live.service >/dev/null <<UNIT
[Unit]
Description=Vijay News 24x7 live stream
After=network-online.target
Wants=network-online.target
[Service]
User=$ME
WorkingDirectory=$APP
Environment=VN_UPLOAD_SHORTS=1
ExecStart=/bin/bash $APP/server/live.sh
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
UNIT
sudo tee /etc/systemd/system/vijaynews-pull.service >/dev/null <<UNIT
[Unit]
Description=Vijay News – fetch new bulletin from GitHub
[Service]
Type=oneshot
User=$ME
WorkingDirectory=$APP
ExecStart=/bin/bash $APP/server/pull.sh
UNIT
sudo tee /etc/systemd/system/vijaynews-pull.timer >/dev/null <<UNIT
[Unit]
Description=Vijay News – check GitHub every 2 minutes
[Timer]
OnBootSec=1min
OnUnitActiveSec=2min
[Install]
WantedBy=timers.target
UNIT
sudo tee /etc/systemd/system/vijaynews-upload.service >/dev/null <<UNIT
[Unit]
Description=Vijay News – upload yesterday's bulletins and new Shorts
[Service]
Type=oneshot
User=$ME
WorkingDirectory=$APP
Environment=VN_UPLOAD_SHORTS=1
ExecStart=$APP/.venv/bin/python3 $APP/yt_upload.py daily
UNIT
sudo tee /etc/systemd/system/vijaynews-upload.timer >/dev/null <<UNIT
[Unit]
Description=Vijay News – uploads every 30 minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
[Install]
WantedBy=timers.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now vijaynews-pull.timer vijaynews-upload.timer
echo "== 5/5 keys"
bash server/keys.sh
sudo systemctl enable --now vijaynews-live.service
echo
echo "All set. Check with:  bash server/status.sh"
