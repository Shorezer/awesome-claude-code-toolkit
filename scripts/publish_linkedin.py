#!/usr/bin/env python3
"""Publish a post to LinkedIn (UGC posts API). DRY-RUN by default."""

import argparse
import json
import os
import sys

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post", required=True, help="Path to linkedin-post.md")
    parser.add_argument(
        "--visibility",
        default="PUBLIC",
        choices=["PUBLIC", "CONNECTIONS"],
    )
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.post):
        print(f"ERROR: post not found: {args.post}", file=sys.stderr)
        sys.exit(1)

    with open(args.post) as f:
        text = f.read().strip()

    plan = {
        "action": "linkedin.post",
        "visibility": args.visibility,
        "length_chars": len(text),
        "preview": text[:200],
    }

    if not args.publish:
        print("[DRY RUN] " + json.dumps(plan, indent=2))
        return

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    author = os.environ.get("LINKEDIN_AUTHOR_URN")
    if not token or not author:
        print("ERROR: LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN required", file=sys.stderr)
        sys.exit(2)

    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": args.visibility},
    }
    r = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    print(json.dumps({"id": r.headers.get("x-restli-id")}))


if __name__ == "__main__":
    main()
