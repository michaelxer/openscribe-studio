#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt pyinstaller

.venv/bin/python -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --windowed \
  --name "OpenScribeStudio" \
  --collect-all faster_whisper \
  --collect-all ctranslate2 \
  --collect-all av \
  --collect-all tokenizers \
  --collect-all huggingface_hub \
  --collect-all imageio_ffmpeg \
  --collect-all yt_dlp \
  transcript_app.py

DIST_APP="$ROOT/dist/OpenScribeStudio.app"
if [ -d "$DIST_APP" ]; then
  mkdir -p "$DIST_APP/Contents/Resources"
  cp "$ROOT/README.md" "$DIST_APP/Contents/Resources/README.md"
  cp "$ROOT/USER_GUIDE.md" "$DIST_APP/Contents/Resources/USER_GUIDE.md"
  cp "$ROOT/urls.example.txt" "$DIST_APP/Contents/Resources/urls.example.txt"
fi

echo ""
echo "macOS app created:"
echo "  $DIST_APP"
echo ""
echo "For public distribution, sign and notarize the app/DMG with an Apple Developer account."
