#!/bin/bash
set -e

APP_NAME="MCSmaker"
REPO_URL="https://github.com/Nico19422009/MCSmaker"
RAW_BASE="https://raw.githubusercontent.com/Nico19422009/MCSmaker/main"

# ===== Self-update install.sh =====
echo "[*] Updating install.sh from repo..."
curl -fsSL "$RAW_BASE/install.sh" -o install.sh
chmod +x install.sh

# ===== Normal setup =====
echo "=== $APP_NAME Installer ==="
echo "Updating package list..."
sudo apt update -y

# Python
sudo apt install -y python3 python3-pip

# Java (latest stable from repos)
echo "Installing OpenJDK..."
sudo apt install -y default-jdk

# Screen
sudo apt install -y screen

# Fetch latest manager.py
echo "Downloading latest manager.py..."
curl -fsSL "$RAW_BASE/manager.py" -o manager.py

# Create symlink for easy access
sudo ln -sf $(pwd)/manager.py /usr/local/bin/mcsmaker

# Version info
echo "=== Installation complete! ==="
echo "Python version: $(python3 --version)"
echo "Java version: $(java -version 2>&1 | head -n 1)"
echo "Screen version: $(screen --version)"
echo

echo "You can now run: mcsmaker"
echo "Repo: $REPO_URL"
