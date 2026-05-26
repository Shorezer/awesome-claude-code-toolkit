---
description: Generate the thumbnail image and assemble the final mp4.
argument-hint: <topic-slug>
---

Topic slug: `$1`.

## Pre-flight

- Verify `topics/$1/voiceover.mp3` exists. If not: "Run `/produce-audio $1` first."
- Verify `topics/$1/thumbnail-prompt.txt` exists. If not: "Run `/run-pipeline $1` first."
- Verify the image-gen API key for the configured provider is set: `OPENAI_API_KEY` (if `IMAGE_API=openai`) or `STABILITY_API_KEY` (if `IMAGE_API=stability`).
- Verify `ffmpeg` is on PATH.

## Run

1. Generate the thumbnail:
   ```
   python scripts/generate_thumbnail.py topics/$1/thumbnail-prompt.txt -o topics/$1/thumbnail.png
   ```
2. Assemble the video:
   ```
   python scripts/assemble_video.py --audio topics/$1/voiceover.mp3 --image topics/$1/thumbnail.png -o topics/$1/video.mp4
   ```

## Report

- Thumbnail path + dimensions
- Video path + duration + file size

Recommend `/publish $1 --target all` (dry-run) as the next step.
