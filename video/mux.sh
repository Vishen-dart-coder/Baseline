#!/usr/bin/env bash
# Join the rendered picture and the mix into the deliverable.
set -euo pipefail
cd "$(dirname "$0")/out"
ffmpeg -y -loglevel error -i video_only.mp4 -i mix.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 16 -profile:v high -pix_fmt yuv420p \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 320k -ar 48000 -movflags +faststart -shortest technomadenviro-film-2k60.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration,size -of compact technomadenviro-film-2k60.mp4
