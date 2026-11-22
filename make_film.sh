#!/usr/bin/env bash
# Build the whole film: voices -> timeline -> score -> ambience -> mix -> picture + subtitles -> MP4
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build output
python3 audio/voices.py                               # Malayalam dialogue (neural voices) + lip-sync envelopes + word timings
python3 film/timeline.py                              # shot timing from voice durations
python3 audio/music.py                                # piano + strings score
python3 audio/ambience.py                             # birds, wind, footsteps, crickets, rain...
python3 audio/mix.py                                  # dialogue 100 %, background 75 %, ducked under speech
ffmpeg -hide_banner -loglevel error -y -i build/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 build/mix_norm.wav
python3 film/compose.py output/A_Home_Called_Grandma_and_Grandpa.mp4 --workers "${WORKERS:-4}"
python3 -m pytest -q tests
