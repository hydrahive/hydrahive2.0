#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "install.sh must run as root" >&2
    exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if ! getent group hydrahive-node >/dev/null 2>&1; then
    groupadd --system hydrahive-node
fi
if ! id hydrahive-node >/dev/null 2>&1; then
    useradd --system --gid hydrahive-node --home-dir /var/lib/hydrahive-node --shell /usr/sbin/nologin hydrahive-node
fi
install -d -m 0700 -o hydrahive-node -g hydrahive-node /var/lib/hydrahive-node
python3 -m pip install --disable-pip-version-check "$SCRIPT_DIR"
install -m 0644 "$SCRIPT_DIR/systemd/hydrahive-node.service" /etc/systemd/system/hydrahive-node.service
systemctl daemon-reload
systemctl enable hydrahive-node.service

echo "Installed. Enroll interactively with: hydrahive-node enroll --server https://HOST --name NODE"
