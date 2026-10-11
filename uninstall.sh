#!/usr/bin/env bash
# Remove the localbooks service (your ~/Books folder is left untouched).
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  exec sudo "$0" "$@"
fi

systemctl disable --now localbooks.service 2>/dev/null || true
rm -f /etc/systemd/system/localbooks.service /usr/local/bin/localbooks
systemctl daemon-reload
echo "localbooks removed."
