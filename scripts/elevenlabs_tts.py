#!/usr/bin/env python3
"""Generate voiceover audio from voiceover.txt using ElevenLabs v3."""

import argparse
import os
import re
import sys

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

# ElevenLabs rejects requests over 5000 characters; chunk below that with margin.
MAX_CHARS = 4500


def chunk_text(text, max_chars=MAX_CHARS):
    """Split text into <=max_chars chunks at line/sentence boundaries only.

    The script is one-idea-per-line, so lines are the natural unit; an
    over-long line is further split at sentence enders. Never splits a
    sentence mid-way, which keeps inline [tags] attached to their text.
    """
    units = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) <= max_chars:
            units.append(line)
            continue
        buf = ""
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if buf and len(buf) + len(sentence) + 1 > max_chars:
                units.append(buf)
                buf = sentence
            else:
                buf = f"{buf} {sentence}".strip()
        if buf:
            units.append(buf)

    chunks = []
    buf = ""
    for unit in units:
        if buf and len(buf) + len(unit) + 1 > max_chars:
            chunks.append(buf)
            buf = unit
        else:
            buf = f"{buf}\n{unit}" if buf else unit
    if buf:
        chunks.append(buf)
    return chunks


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
    chunks = chunk_text(text)

    with open(out, "wb") as f:
        for chunk in chunks:
            audio_stream = client.text_to_speech.convert(
                voice_id=args.voice,
                model_id=args.model,
                text=chunk,
                output_format="mp3_44100_128",
            )
            for piece in audio_stream:
                if piece:
                    f.write(piece)

    size_mb = os.path.getsize(out) / (1024 * 1024)
    print(f"{out}  ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
