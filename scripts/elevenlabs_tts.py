#!/usr/bin/env python3
"""Generate voiceover audio from voiceover.txt using ElevenLabs v3."""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to voiceover.txt")
    parser.add_argument("-o", "--output", help="Output mp3 path (default: alongside input)")
    parser.add_argument("--voice", default=os.environ.get("ELEVENLABS_VOICE_ID"))
    parser.add_argument("--model", default="eleven_v3")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY is not set", file=sys.stderr)
        sys.exit(2)
    if not args.voice:
        print("ERROR: ELEVENLABS_VOICE_ID is not set (or pass --voice)", file=sys.stderr)
        sys.exit(2)
    if not os.path.exists(args.input):
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    out = args.output or args.input.replace("voiceover.txt", "voiceover.mp3")
    if out == args.input:
        out = args.input + ".mp3"

    with open(args.input) as f:
        text = f.read()

    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    audio_stream = client.text_to_speech.convert(
        voice_id=args.voice,
        model_id=args.model,
        text=text,
        output_format="mp3_44100_128",
    )

    with open(out, "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)

    size_mb = os.path.getsize(out) / (1024 * 1024)
    print(f"{out}  ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
