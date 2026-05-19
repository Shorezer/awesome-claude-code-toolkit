#!/usr/bin/env python3
"""Update a topic's status column in the Sheets queue."""

import argparse
import os
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
VALID_STATUSES = [
    "pending", "in-progress",
    "researched", "briefed", "scripted", "edited",
    "voiced", "video-ready", "published", "failed", "skipped",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--status", required=True, choices=VALID_STATUSES)
    parser.add_argument("--sheet-id", default=os.environ.get("GOOGLE_SHEET_ID"))
    parser.add_argument("--creds", default=os.environ.get("GOOGLE_SHEETS_CREDS_PATH"))
    args = parser.parse_args()

    if not args.sheet_id:
        print("ERROR: GOOGLE_SHEET_ID is not set", file=sys.stderr)
        sys.exit(2)
    if not args.creds or not os.path.exists(args.creds):
        print(f"ERROR: GOOGLE_SHEETS_CREDS_PATH not found: {args.creds}", file=sys.stderr)
        sys.exit(2)

    creds = service_account.Credentials.from_service_account_file(args.creds, scopes=SCOPES)
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()

    rows = sheets.values().get(spreadsheetId=args.sheet_id, range="Topics!A:B").execute().get("values", [])
    for i, row in enumerate(rows, start=1):
        if i == 1:
            continue  # header
        slug = row[1] if len(row) > 1 else ""
        if slug == args.slug:
            sheets.values().update(
                spreadsheetId=args.sheet_id,
                range=f"Topics!A{i}",
                valueInputOption="RAW",
                body={"values": [[args.status]]},
            ).execute()
            print(f"{args.slug} → {args.status}")
            return

    print(f"ERROR: slug not found in sheet: {args.slug}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
