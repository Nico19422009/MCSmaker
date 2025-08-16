#!/bin/bash
set -e

echo "=== MCSmaker Installer ==="
echo "Updating package list..."
sudo apt update -y

echo "Installing Python3..."
sudo apt install -y python3 python3-pip

echo "Installing OpenJDK 17 (headless)..."
sudo apt install -y openjdk-17-jre-headless

echo "=== Installation complete! ==="
echo "Python version: $(python3 --version)"
echo "Java version: $(java -version 2>&1 | head -n 1)"
echo
echo "You can now run: python3 manager.py"
