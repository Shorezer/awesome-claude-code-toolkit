#!/usr/bin/env python3
"""Strip // VISUAL: and // SECTION comments from a script.

Preserves ElevenLabs [bracket] voice tags untouched. Drops blank lines
and markdown headings (lines starting with #).
"""

import argparse
import re
import sys


VISUAL_LINE = re.compile(r"^\s*//\s*(VISUAL|SECTION)\b.*$", re.IGNORECASE)
TRAILING_COMMENT = re.compile(r"\s*//\s*(VISUAL|SECTION)\b.*$", re.IGNORECASE)
HEADING = re.compile(r"^\s*#")


def strip(text):
    out = []
    for raw in text.splitlines():
        if VISUAL_LINE.match(raw):
            continue
        if HEADING.match(raw):
            continue
        line = TRAILING_COMMENT.sub("", raw).rstrip()
        if line.strip():
            out.append(line)
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("-o", "--output", help="Output path; defaults to stdout")
    args = parser.parse_args()

    with open(args.input) as f:
        cleaned = strip(f.read())

    if args.output:
        with open(args.output, "w") as f:
            f.write(cleaned)
        print(args.output)
    else:
        sys.stdout.write(cleaned)


if __name__ == "__main__":
    main()
