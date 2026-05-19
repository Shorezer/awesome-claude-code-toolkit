#!/usr/bin/env python3
"""Publish a blog post to WordPress via REST API. DRY-RUN by default."""

import argparse
import json
import os
import re
import sys
import urllib.parse

import requests


def is_wpcom(url):
    """WordPress.com-hosted sites need the public REST API, not the local one."""
    return "wordpress.com" in urllib.parse.urlparse(url).netloc


def publish_wpcom(url, title, body, status):
    # WordPress.com REST v1.1. Auth is an OAuth2 bearer token (NOT an app password).
    # TODO: WORDPRESS_COM_TOKEN must be a WordPress.com OAuth2 token. Create an app
    # at https://developer.wordpress.com/apps/ and run its OAuth2 flow to mint one.
    token = os.environ.get("WORDPRESS_COM_TOKEN")
    if not token or token.startswith("TODO"):
        print(
            "ERROR: this is a WordPress.com-hosted site. It needs a WordPress.com "
            "OAuth2 token in WORDPRESS_COM_TOKEN (separate from an application "
            "password). Create an app at https://developer.wordpress.com/apps/ and "
            "complete its OAuth2 flow to get a token.",
            file=sys.stderr,
        )
        sys.exit(2)
    site = urllib.parse.urlparse(url).netloc
    endpoint = f"https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/new"
    r = requests.post(
        endpoint,
        json={"title": title, "content": body, "status": status},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return {"id": data.get("ID"), "link": data.get("URL")}


def publish_selfhosted(url, title, body, status, meta):
    user = os.environ.get("WORDPRESS_USER")
    pw = os.environ.get("WORDPRESS_APP_PASSWORD")
    if not user or not pw or pw.startswith("TODO"):
        print("ERROR: WORDPRESS_USER / WORDPRESS_APP_PASSWORD required", file=sys.stderr)
        sys.exit(2)
    endpoint = url.rstrip("/") + "/wp-json/wp/v2/posts"
    r = requests.post(
        endpoint,
        json={
            "title": title,
            "content": body,
            "status": status,
            "slug": meta.get("slug"),
            "meta": {"description": meta.get("meta_description", "")},
        },
        auth=(user, pw),
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return {"id": data.get("id"), "link": data.get("link")}


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

    url = os.environ.get("WORDPRESS_URL")
    if not url:
        print("ERROR: WORDPRESS_URL required", file=sys.stderr)
        sys.exit(2)

    title = meta.get("title", args.title)
    api = "wordpress.com" if is_wpcom(url) else "self-hosted"

    plan = {
        "action": "wordpress.post",
        "api": api,
        "title": title,
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

    if api == "wordpress.com":
        result = publish_wpcom(url, title, body, args.status)
    else:
        result = publish_selfhosted(url, title, body, args.status, meta)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
