#!/usr/bin/env bash
# Reboot the training machine after a short delay.
# Usage: reboot_machine.sh [delay_seconds]
set -euo pipefail

DELAY="${1:-5}"
sleep "$DELAY"

reboot_cmd() {
  if command -v systemctl >/dev/null 2>&1; then
    if [[ "$(id -u)" -eq 0 ]]; then
      systemctl reboot
    elif command -v sudo >/dev/null 2>&1; then
      sudo -n systemctl reboot
    else
      systemctl reboot
    fi
    return
  fi

  if [[ -x /sbin/reboot ]]; then
    /sbin/reboot
    return
  fi

  if [[ -x /usr/sbin/reboot ]]; then
    /usr/sbin/reboot
    return
  fi

  echo "No reboot command available" >&2
  exit 1
}

reboot_cmd
