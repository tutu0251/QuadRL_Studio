#!/usr/bin/env bash
# Install QuadRL Studio as a systemd service that starts on boot.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_NAME="quadrl-studio.service"
SRC="$ROOT/deploy/$UNIT_NAME"
DEST="/etc/systemd/system/$UNIT_NAME"
USER_NAME="${SUDO_USER:-$(whoami)}"

if [[ ! -f "$SRC" ]]; then
  echo "Missing unit file: $SRC" >&2
  exit 1
fi

chmod +x "$ROOT/scripts/start_all_background.sh"
chmod +x "$ROOT/scripts/restart_services.sh"
chmod +x "$ROOT/scripts/reboot_machine.sh"

TMP="$(mktemp)"
sed "s|User=gazebo|User=$USER_NAME|g; s|/home/gazebo/QuadRL_Studio|$ROOT|g" "$SRC" >"$TMP"

echo "Installing $DEST (user=$USER_NAME, root=$ROOT)"
sudo cp "$TMP" "$DEST"
rm -f "$TMP"

sudo systemctl daemon-reload
sudo systemctl enable "$UNIT_NAME"
sudo systemctl restart "$UNIT_NAME" || sudo systemctl start "$UNIT_NAME"

echo ""
echo "QuadRL Studio is enabled on boot."
echo "  Status:  sudo systemctl status $UNIT_NAME"
echo "  Logs:    journalctl -u $UNIT_NAME -f"
echo "  Stop:    sudo systemctl stop $UNIT_NAME"
echo ""
echo "Optional — allow reboot from the Train Monitor UI without a password:"
echo "  echo '$USER_NAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl reboot' | sudo tee /etc/sudoers.d/quadrl-reboot"
echo "  sudo chmod 440 /etc/sudoers.d/quadrl-reboot"
