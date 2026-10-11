#!/usr/bin/env bash
# Install localbooks as a systemd service that starts at boot and serves ~/Books.
set -euo pipefail

USER_NAME="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-80}"

if [ "$(id -u)" -ne 0 ]; then
  exec sudo PORT="$PORT" "$0" "$@"
fi

systemctl stop localbooks.service 2>/dev/null || true
if ss -ltnH "sport = :$PORT" | grep -q .; then
  echo "Port $PORT is already in use by another program:" >&2
  ss -ltnpH "sport = :$PORT" >&2
  echo "Choose another port, e.g.: PORT=8088 ./install.sh" >&2
  exit 1
fi

apt-get install -y avahi-daemon avahi-utils python3 >/dev/null

install -m 755 "$SRC_DIR/localbooks.py" /usr/local/bin/localbooks
install -d -o "$USER_NAME" -g "$USER_NAME" "$USER_HOME/Books"

cat > /etc/systemd/system/localbooks.service <<UNIT
[Unit]
Description=localbooks - ebook server for Kobo
After=network-online.target avahi-daemon.service
Wants=network-online.target avahi-daemon.service

[Service]
User=$USER_NAME
Environment=LOCALBOOKS_DIR=$USER_HOME/Books
Environment=LOCALBOOKS_PORT=$PORT
Environment=LOCALBOOKS_NAME=books.local
ExecStart=/usr/bin/python3 /usr/local/bin/localbooks
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now localbooks.service

if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow "$PORT/tcp" >/dev/null
  ufw allow 5353/udp >/dev/null
fi

URL="http://books.local/"
[ "$PORT" = 80 ] || URL="http://books.local:$PORT/"
echo "localbooks installed. Put your books in $USER_HOME/Books and open $URL"
systemctl --no-pager status localbooks.service | head -n 15
