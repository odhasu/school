#!/bin/bash
set -e

echo "=== Focus Timer Build ==="

# Install deps
pip install customtkinter Pillow pyinstaller --quiet

# Build .exe (works on Windows) or app bundle on Mac
pyinstaller \
  --onefile \
  --windowed \
  --name "FocusTimer" \
  --clean \
  focus_timer.py

echo ""
echo "Done! Output is in dist/FocusTimer"
echo "On Windows this produces dist/FocusTimer.exe"
