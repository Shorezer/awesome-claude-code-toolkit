#!/usr/bin/env python3
"""Generate a 1792x1024 YouTube thumbnail from a prompt file.

Provider is selected by IMAGE_API env var: `openai` (default) or `stability`.
"""

import argparse
import base64
import os
import sys

import requests
from PIL import Image


def via_openai(prompt, out):
    from openai import OpenAI

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set", file=sys.stderr)
        sys.exit(2)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1792x1024",
    )
    data = resp.data[0]
    if getattr(data, "b64_json", None):
        with open(out, "wb") as f:
            f.write(base64.b64decode(data.b64_json))
    else:
        r = requests.get(data.url, timeout=60)
        r.raise_for_status()
        with open(out, "wb") as f:
            f.write(r.content)


def via_stability(prompt, out):
    api_key = os.environ.get("STABILITY_API_KEY")
    if not api_key:
        print("ERROR: STABILITY_API_KEY is not set", file=sys.stderr)
        sys.exit(2)

    r = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={"authorization": f"Bearer {api_key}", "accept": "image/*"},
        files={"none": ""},
        data={"prompt": prompt, "aspect_ratio": "16:9", "output_format": "png"},
        timeout=120,
    )
    r.raise_for_status()
    with open(out, "wb") as f:
        f.write(r.content)


def downscale_to_youtube(path):
    """YouTube prefers 1280x720. Source is 1792x1024 — re-export."""
    img = Image.open(path)
    img.thumbnail((1280, 720), Image.LANCZOS)
    img.save(path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to thumbnail-prompt.txt")
    parser.add_argument("-o", "--output", help="Output png path")
    parser.add_argument(
        "--api",
        default=os.environ.get("IMAGE_API", "openai"),
        choices=["openai", "stability"],
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        prompt = f.read().strip()
    if not prompt:
        print("ERROR: thumbnail prompt is empty", file=sys.stderr)
        sys.exit(1)

    out = args.output or args.input.replace("thumbnail-prompt.txt", "thumbnail.png")

    if args.api == "openai":
        via_openai(prompt, out)
    else:
        via_stability(prompt, out)

    downscale_to_youtube(out)
    print(out)


if __name__ == "__main__":
    main()
