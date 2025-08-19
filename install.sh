#!/bin/bash
set -e

echo "=== MCSmaker Installer ==="

# --- Update system ---
echo "[*] Updating package list..."
sudo apt-get update -y

# --- Install Python3 ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "[*] Installing Python3..."
  sudo apt-get install -y python3 python3-pip
else
  echo "[OK] Python3 already installed: $(python3 --version)"
fi

# --- Install Java (default-jdk) ---
if ! command -v java >/dev/null 2>&1; then
  echo "[*] Installing latest OpenJDK (default-jdk)..."
  sudo apt-get install -y default-jdk
else
  echo "[OK] Java already installed: $(java -version 2>&1 | head -n 1)"
fi

# --- Install screen ---
if ! command -v screen >/dev/null 2>&1; then
  echo "[*] Installing screen..."
  sudo apt-get install -y screen
else
  echo "[OK] screen already installed: $(screen --version | head -n 1)"
fi

echo
echo "=== Installation complete! ==="
echo "Python version: $(python3 --version)"
echo "Java version: $(java -version 2>&1 | head -n 1)"
echo "Screen version: $(screen --version | head -n 1)"
echo
echo "You can now run: python3 manager.py"
