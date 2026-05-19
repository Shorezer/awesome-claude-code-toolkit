#!/usr/bin/env python3
"""Publish a blog post to WordPress via REST API. DRY-RUN by default."""

import argparse
import json
import os
import re
import sys

import requests


def parse_frontmatter(text):
    """Pull out optional YAML frontmatter. Returns (meta_dict, body)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    body = text[end + 5:]
    meta = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, body


def substitute_affiliate_links(body):
    """Replace AFFILIATE_LINK_TOOL placeholders with env-supplied URLs.

    Reads AFFILIATE_LINK_<TOOL> env vars. If unset, leaves the placeholder
    in place and flags it in the dry-run output.
    """
    missing = []

    def repl(match):
        token = match.group(0)
        url = os.environ.get(token)
        if url:
            return url
        missing.append(token)
        return token

    new = re.sub(r"AFFILIATE_LINK_[A-Z_]+", repl, body)
    return new, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post", required=True, help="Path to blog-post.md")
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--status",
        default="draft",
        choices=["draft", "publish", "future", "private"],
    )
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.post):
        print(f"ERROR: post not found: {args.post}", file=sys.stderr)
        sys.exit(1)

    with open(args.post) as f:
        raw = f.read()

    meta, body = parse_frontmatter(raw)
    body, missing_links = substitute_affiliate_links(body)

    plan = {
        "action": "wordpress.post",
        "title": meta.get("title", args.title),
        "slug": meta.get("slug"),
        "status": args.status,
        "length_chars": len(body),
        "missing_affiliate_links": missing_links,
    }

    if not args.publish:
        print("[DRY RUN] " + json.dumps(plan, indent=2))
        return

    if missing_links:
        print(f"ERROR: missing affiliate link env vars: {missing_links}", file=sys.stderr)
        sys.exit(1)

    url = os.environ.get("WORDPRESS_URL")
    user = os.environ.get("WORDPRESS_USER")
    pw = os.environ.get("WORDPRESS_APP_PASSWORD")
    if not (url and user and pw):
        print("ERROR: WORDPRESS_URL / WORDPRESS_USER / WORDPRESS_APP_PASSWORD required", file=sys.stderr)
        sys.exit(2)

    endpoint = url.rstrip("/") + "/wp-json/wp/v2/posts"
    payload = {
        "title": meta.get("title", args.title),
        "content": body,
        "status": args.status,
        "slug": meta.get("slug"),
        "meta": {"description": meta.get("meta_description", "")},
    }
    r = requests.post(endpoint, json=payload, auth=(user, pw), timeout=60)
    r.raise_for_status()
    data = r.json()
    print(json.dumps({"id": data.get("id"), "link": data.get("link")}))


if __name__ == "__main__":
    main()
