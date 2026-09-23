#!/bin/bash
# Double-click launcher for macOS/Linux. Runs run.py using python3 on PATH.
cd "$(dirname "$0")"
python3 run.py
echo
read -p "Press Enter to close this window..."
