#!/usr/bin/env bash
# Install ROS 2 Humble + Gazebo Fortress (Ignition) on Ubuntu 22.04 (Jammy).
#
# Matches what QuadRL Studio expects:
#   - spawn_gazebo_gui.sh sources /opt/ros/humble and calls `ign gazebo` / `ign service`
#   - the ros_gz_sim / ros_ign_gazebo bridge packages
#
# Usage:
#   ./install_ros2_gazebo.sh                 # desktop (GUI tools, rviz, demos)
#   ROS_PKG=ros-base ./install_ros2_gazebo.sh   # headless / training machines
#
# Re-runnable: apt skips already-installed packages.
set -euo pipefail

ROS_DISTRO="humble"
ROS_PKG="${ROS_PKG:-desktop}"   # desktop | ros-base

SUDO=""
[[ $EUID -ne 0 ]] && SUDO="sudo"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# --- 0. Sanity: Ubuntu 22.04 ---------------------------------------------
. /etc/os-release 2>/dev/null || true
if [[ "${VERSION_CODENAME:-}" != "jammy" ]]; then
  echo "WARNING: ROS 2 ${ROS_DISTRO} + Gazebo Fortress target Ubuntu 22.04 (jammy)."
  echo "         Detected: ${PRETTY_NAME:-unknown}. Continuing anyway in 5s (Ctrl+C to abort)."
  sleep 5
fi

# --- 1. Prerequisites + locale -------------------------------------------
log "Installing prerequisites and UTF-8 locale"
$SUDO apt-get update -y
$SUDO apt-get install -y curl gnupg lsb-release software-properties-common locales ca-certificates
$SUDO locale-gen en_US en_US.UTF-8
$SUDO update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Enable the "universe" repository (required for many ROS deps).
$SUDO add-apt-repository -y universe

# --- 2. ROS 2 apt repository ---------------------------------------------
log "Adding the ROS 2 apt repository"
$SUDO install -d -m 0755 /usr/share/keyrings
curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  | $SUDO gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg
ARCH="$(dpkg --print-architecture)"
echo "deb [arch=${ARCH} signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME}") main" \
  | $SUDO tee /etc/apt/sources.list.d/ros2.list >/dev/null

# --- 3. Gazebo (Ignition) apt repository ---------------------------------
log "Adding the OSRF (Gazebo/Ignition) apt repository"
curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
  | $SUDO gpg --dearmor -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=${ARCH} signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
  | $SUDO tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null

$SUDO apt-get update -y

# --- 4. ROS 2 Humble ------------------------------------------------------
log "Installing ROS 2 ${ROS_DISTRO} (${ROS_PKG}) + dev tools"
$SUDO apt-get install -y "ros-${ROS_DISTRO}-${ROS_PKG}" ros-dev-tools

# --- 5. Gazebo Fortress + the ROS<->Gazebo bridge -------------------------
log "Installing Gazebo Fortress (Ignition) and the ros_gz / ros_ign bridge"
$SUDO apt-get install -y \
  ignition-fortress \
  "ros-${ROS_DISTRO}-ros-gz" \
  "ros-${ROS_DISTRO}-ros-gz-sim" \
  "ros-${ROS_DISTRO}-ros-gz-bridge" \
  "ros-${ROS_DISTRO}-ros-ign-gazebo" \
  "ros-${ROS_DISTRO}-ros-ign-bridge"

# --- 6. rosdep ------------------------------------------------------------
log "Initialising rosdep"
$SUDO rosdep init 2>/dev/null || true
rosdep update || true

# --- 7. Auto-source in ~/.bashrc -----------------------------------------
SRC_LINE="source /opt/ros/${ROS_DISTRO}/setup.bash"
if ! grep -qxF "$SRC_LINE" "${HOME}/.bashrc" 2>/dev/null; then
  log "Adding '${SRC_LINE}' to ~/.bashrc"
  printf '\n# QuadRL Studio: ROS 2 environment\n%s\n' "$SRC_LINE" >> "${HOME}/.bashrc"
fi

cat <<EOF

$(printf '\033[1;32m')Done.$(printf '\033[0m') ROS 2 ${ROS_DISTRO} + Gazebo Fortress installed.

Activate in the current shell:
  source /opt/ros/${ROS_DISTRO}/setup.bash

Verify:
  ros2 --help
  ign gazebo --versions

New terminals pick up ROS automatically (added to ~/.bashrc).
EOF
