#!/bin/sh
# One command: voice → events → mix → picture → mux.  sh build.sh   (LIB = the Lemo-Opuscar library folder)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
LIB=${LIB:-/root/lemo-opuscar}
export LIB
[ -f "$LIB/core/render/video.mjs" ] || { echo "set LIB to the library folder"; exit 1; }
PY="$LIB/.venv/bin/python"
"$PY" "$HERE/tools/tts_ml.py" "$HERE/voice/lines.json" "$HERE/voice/out"          # Malayalam voices (edge-tts, online; cached)
cd "$LIB"
node core/render/events.mjs "$HERE"
"$PY" "$HERE/mix.py"
node core/render/video.mjs "$HERE" --fps 24 --workers 4 --size 1080x1920 --out "$HERE/out/video.mp4"
cd "$HERE"
"$PY" tools/subs.py
sh tools/mux6.sh out/video.mp4 out/mix.wav thengin-thai.mp4
