#!/bin/bash
# Setup script for Raspberry Pi 4B (Debian/Ubuntu)
# - installs system deps (ffmpeg)
# - creates and activates a python venv
# - installs required python packages
# - optional: sets FLIGHTCALLNET_ROOT in /etc/profile.d for persistent env var

set -euo pipefail

# Variables (adjust if your SSD is mounted elsewhere)
PROJECT_DIR="/home/pi/FlightCallNet"
VENV_DIR="$PROJECT_DIR/.venv"

if [ -n "${1-}" ]; then
  PROJECT_DIR="$1"
  VENV_DIR="$PROJECT_DIR/.venv"
fi

echo "Running FlightCallNet RPi setup for project dir: $PROJECT_DIR"

# Update and install system packages
echo "Updating apt and installing ffmpeg, python3-venv, git..."
sudo apt update && sudo apt install -y ffmpeg python3-venv python3-pip git

# Create project dir if missing
if [ ! -d "$PROJECT_DIR" ]; then
  echo "Project directory $PROJECT_DIR does not exist; creating..."
  mkdir -p "$PROJECT_DIR"
fi

# Create venv and install python deps
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "Activating venv and installing Python packages from requirements.txt"
source "$VENV_DIR/bin/activate"

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
  pip install --upgrade pip
  pip install -r "$PROJECT_DIR/requirements.txt"
else
  echo "requirements.txt not found in $PROJECT_DIR; please copy the project to $PROJECT_DIR and rerun this script"
fi

# Run the Python helper to double-check deps (this will use the venv pip)
if [ -f "$PROJECT_DIR/scripts/check_and_install_deps.py" ]; then
  echo "Running dependency checker"
  python "$PROJECT_DIR/scripts/check_and_install_deps.py"
else
  echo "No dependency helper present at $PROJECT_DIR/scripts/check_and_install_deps.py"
fi

# Optional: persist FLIGHTCALLNET_ROOT for future shells (commented out by default)
# echo "export FLIGHTCALLNET_ROOT=$PROJECT_DIR" | sudo tee /etc/profile.d/flightcallnet.sh

echo "Setup finished. Activate venv with: source $VENV_DIR/bin/activate"

