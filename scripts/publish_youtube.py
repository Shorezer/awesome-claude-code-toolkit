#!/usr/bin/env python3
"""Upload a video to YouTube. DRY-RUN by default; --publish to actually upload."""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--thumbnail", default=None)
    parser.add_argument(
        "--privacy",
        default="private",
        choices=["private", "unlisted", "public"],
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Actually upload. Without this flag, only prints the planned upload.",
    )
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    plan = {
        "action": "youtube.upload",
        "video": args.video,
        "title": args.title,
        "description_preview": args.description[:200],
        "tags": tags,
        "thumbnail": args.thumbnail,
        "privacy": args.privacy,
    }

    if not args.publish:
        print("[DRY RUN] " + json.dumps(plan, indent=2))
        return

    if not os.path.exists(args.video):
        print(f"ERROR: video not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    from google_oauth import load_credentials

    creds = load_credentials()  # shared Sheets+YouTube OAuth token
    yt = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": args.title,
            "description": args.description,
            "tags": tags,
            "categoryId": "28",  # Science & Technology
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(args.video, chunksize=-1, resumable=True)
    resp = yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    video_id = resp["id"]

    if args.thumbnail and os.path.exists(args.thumbnail):
        yt.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(args.thumbnail),
        ).execute()

    print(json.dumps({"id": video_id, "url": f"https://youtu.be/{video_id}"}))


if __name__ == "__main__":
    main()
