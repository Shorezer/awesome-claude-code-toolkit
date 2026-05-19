#!/usr/bin/env python3
"""Assemble final mp4 from voiceover.mp3 + thumbnail.png.

Produces a static-image-with-audio video suitable for upload. Replace this
with a b-roll-aware assembler once broll-shotlist.md drives a real editor.
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    for path in (args.audio, args.image):
        if not os.path.exists(path):
            print(f"ERROR: missing input: {path}", file=sys.stderr)
            sys.exit(1)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", args.image,
        "-i", args.audio,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-shortest",
        args.output,
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("ERROR: ffmpeg not on PATH", file=sys.stderr)
        sys.exit(2)

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"{args.output}  ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
