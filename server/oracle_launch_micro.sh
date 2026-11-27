#!/bin/bash
# Run in Oracle Cloud Shell:  curl -fsSL https://raw.githubusercontent.com/jpjaytheertha-hash/vijay-news-server/main/server/oracle_launch_micro.sh | bash
# Creates the ALWAYS FREE stream server (VM.Standard.E2.1.Micro, Ubuntu 24.04) "vijay-news-stream" and sets it up
# automatically (server/stream_setup.sh english). Only Always-Free-eligible resources are used – ₹0.
set -e
C="${OCI_TENANCY:?run this in Oracle Cloud Shell}"
NAME=vijay-news-stream
EXIST=$(oci compute instance list -c "$C" --display-name "$NAME" --lifecycle-state RUNNING --query 'data[0].id' --raw-output 2>/dev/null || true)
if [ -n "$EXIST" ] && [ "$EXIST" != "null" ]; then echo "already exists: $EXIST"; else
AD=$(oci iam availability-domain list -c "$C" --query 'data[0].name' --raw-output)
SUB=$(oci network subnet list -c "$C" --query 'data[?"prohibit-public-ip-on-vnic"==`false`] | [0].id' --raw-output)
if [ -z "$SUB" ] || [ "$SUB" = "null" ]; then echo "no public subnet found"; exit 1; fi
IMG=$(oci compute image list -c "$C" --operating-system "Canonical Ubuntu" --operating-system-version "24.04" \
      --shape VM.Standard.E2.1.Micro --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output)
[ -f ~/.ssh/vn_micro ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/vn_micro -q
cat > ~/vn_cloudinit.sh <<'CI'
#!/bin/bash
for i in 1 2 3 4 5; do sudo -u ubuntu git clone --depth 1 https://github.com/jpjaytheertha-hash/vijay-news-server /home/ubuntu/vijay-news-server && break; sleep 20; done
bash /home/ubuntu/vijay-news-server/server/stream_setup.sh english > /var/log/vn_setup.log 2>&1
CI
echo "AD=$AD"; echo "creating $NAME (VM.Standard.E2.1.Micro, Always Free)..."
for try in $(seq 1 20); do
  if oci compute instance launch -c "$C" --availability-domain "$AD" --shape VM.Standard.E2.1.Micro --image-id "$IMG" \
       --subnet-id "$SUB" --assign-public-ip true --display-name "$NAME" --ssh-authorized-keys-file ~/.ssh/vn_micro.pub \
       --user-data-file ~/vn_cloudinit.sh --wait-for-state RUNNING --query 'data.id' --raw-output > ~/vn_id.txt 2> ~/vn_err.txt; then break; fi
  if grep -qi "capacity" ~/vn_err.txt; then echo "out of capacity, retry $try in 60 s"; sleep 60; continue; fi
  cat ~/vn_err.txt; exit 1
done
EXIST=$(tail -1 ~/vn_id.txt)
fi
IP=$(oci compute instance list-vnics --instance-id "$EXIST" --query 'data[0]."public-ip"' --raw-output)
echo "SERVER READY: $NAME  IP=$IP"
echo "In ~3 minutes the setup finishes by itself. Then type the English stream key with:"
echo "  ssh -t -i ~/.ssh/vn_micro ubuntu@$IP 'bash ~/vijay-news-server/server/stream_keys.sh english'"
