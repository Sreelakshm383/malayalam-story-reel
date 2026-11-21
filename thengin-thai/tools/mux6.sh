#!/bin/sh
# Mux picture + already-mastered audio (mix.py masters to −14 LUFS / −1.2 dBTP), add light film grain, AAC 256k. Works with ffmpeg 6.
# usage: sh tools/mux6.sh out/video.mp4 out/mix.wav thengin-thai.mp4
set -e
V=$1; A=$2; O=$3; TMP="$O.part.mp4"
ffmpeg -y -loglevel error -i "$V" -i "$A" -map 0:v -map 1:a -vf "noise=alls=2:allf=t" -c:v libx264 -preset slow -crf 25 -maxrate 9M -bufsize 18M -pix_fmt yuv420p -tune grain \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$TMP"
mv "$TMP" "$O"
ffmpeg -hide_banner -nostats -i "$O" -map 0:a -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary/,$p' | grep -E "I:|Peak:" | head -2
echo "$O"
