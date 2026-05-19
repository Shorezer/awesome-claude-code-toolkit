#!/usr/bin/env python3
"""Generate a 16:9 YouTube thumbnail from a prompt file.

Provider is selected by IMAGE_API env var: `stability` (default) or `openai`.
If the selected provider's API key is missing (or a TODO placeholder), the
script logs a skip and exits 0 so the pipeline isn't blocked on imagery.
"""

import argparse
import base64
import os
import sys

import requests
from PIL import Image


def _missing(val):
    return not val or val.startswith("TODO")


def via_stability(prompt, out):
    api_key = os.environ["STABILITY_API_KEY"]
    # SDXL v1. 1344x768 is a supported dimension and closest to 16:9.
    r = requests.post(
        "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "width": 1344,
            "height": 768,
            "samples": 1,
            "steps": 30,
        },
        timeout=120,
    )
    r.raise_for_status()
    artifacts = r.json().get("artifacts", [])
    if not artifacts:
        print("ERROR: Stability returned no image artifacts", file=sys.stderr)
        sys.exit(1)
    with open(out, "wb") as f:
        f.write(base64.b64decode(artifacts[0]["base64"]))


def via_openai(prompt, out):
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.images.generate(model="gpt-image-1", prompt=prompt, size="1792x1024")
    data = resp.data[0]
    if getattr(data, "b64_json", None):
        with open(out, "wb") as f:
            f.write(base64.b64decode(data.b64_json))
    else:
        r = requests.get(data.url, timeout=60)
        r.raise_for_status()
        with open(out, "wb") as f:
            f.write(r.content)


def downscale_to_youtube(path):
    """YouTube prefers 1280x720. Re-export whatever the provider produced."""
    img = Image.open(path)
    img.thumbnail((1280, 720), Image.LANCZOS)
    img.save(path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to thumbnail-prompt.txt")
    parser.add_argument("-o", "--output", help="Output png path")
    parser.add_argument(
        "--api",
        default=os.environ.get("IMAGE_API", "stability"),
        choices=["stability", "openai"],
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

    if args.api == "stability":
        if _missing(os.environ.get("STABILITY_API_KEY")):
            print("thumbnail skipped — no image API key", file=sys.stderr)
            sys.exit(0)
        via_stability(prompt, out)
    else:
        if _missing(os.environ.get("OPENAI_API_KEY")):
            print("thumbnail skipped — no image API key", file=sys.stderr)
            sys.exit(0)
        via_openai(prompt, out)

    downscale_to_youtube(out)
    print(out)


if __name__ == "__main__":
    main()
