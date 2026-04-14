#!/usr/bin/env bash
# Regenerate placeholder assets for pipeline / mock API proof-of-work.
# Requires: ffmpeg with libx264, libmp3lame, drawtext (libfreetype).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "Generating audio..."
ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t 25 -c:a libmp3lame -q:a 4 vo.mp3
ffmpeg -y -f lavfi -i "sine=frequency=220:sample_rate=44100" -t 45 -c:a libmp3lame -q:a 4 bgm_1.mp3
ffmpeg -y -f lavfi -i "sine=frequency=330:sample_rate=44100" -t 45 -c:a libmp3lame -q:a 4 bgm_2.mp3
ffmpeg -y -f lavfi -i "sine=frequency=440:sample_rate=44100" -t 45 -c:a libmp3lame -q:a 4 bgm_3.mp3
ffmpeg -y -f lavfi -i "sine=frequency=550:sample_rate=44100" -t 45 -c:a libmp3lame -q:a 4 bgm_4.mp3

echo "Generating scene PNGs (5)..."
for i in 1 2 3 4 5; do
  case $i in
    1) c=1a3a5c;; 2) c=3d2914;; 3) c=2d1f3d;; 4) c=1e2e1e;; 5) c=4a2c2a;;
  esac
  ffmpeg -y -f lavfi -i "color=c=0x${c}:s=1920x1080" -frames:v 1 \
    -vf "drawtext=text='SCENE ${i} MOCK':fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
    "scene_0${i}.png"
done

echo "Generating scene MP4s (6s each, test pattern + tone)..."
for i in 1 2 3 4 5; do
  ffmpeg -y -f lavfi -i "testsrc2=size=1920x1080:rate=30:duration=6" \
    -f lavfi -i "sine=frequency=$((200+i*50)):sample_rate=44100" -t 6 \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "scene_0${i}.mp4"
done

echo "Generating final.mp4 (20s)..."
ffmpeg -y -f lavfi -i "testsrc2=size=1920x1080:rate=30:duration=20" \
  -f lavfi -i "sine=frequency=300:sample_rate=44100" -t 20 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest final.mp4

echo "Done. Files in: $DIR"
ls -la
