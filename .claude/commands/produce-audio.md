---
description: Run ElevenLabs TTS on voiceover.txt and produce voiceover.mp3.
argument-hint: <topic-slug>
---

Topic slug: `$1`.

## Pre-flight

- Verify `topics/$1/voiceover.txt` exists. If not, fail with: "Run `/run-pipeline $1` first to produce voiceover.txt."
- Verify env vars `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` are set. If not, fail with the missing var names.

## Run

```
python scripts/elevenlabs_tts.py topics/$1/voiceover.txt -o topics/$1/voiceover.mp3
```

## Report

- Output path
- File size in MB
- Approximate duration (word count / 150) in mm:ss

Recommend `/produce-video $1` as the next step.
