#!/usr/bin/env python3
"""Fetch the next pending topic from the Google Sheets queue and mark it in-progress.

Sheet must have a tab named `Topics` with header row:
    status | slug | topic | audience | affiliate_tool | notes

Prints a single JSON object on stdout, or `{}` if no pending rows.
"""

import argparse
import json
import os
import re
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_RANGE = "Topics!A:F"
COLS = ["status", "slug", "topic", "audience", "affiliate_tool", "notes"]


def slugify(s):
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:80] or "untitled"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
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

    rows = sheets.values().get(spreadsheetId=args.sheet_id, range=SHEET_RANGE).execute().get("values", [])
    if not rows:
        print("{}")
        return

    data = rows[1:]  # skip header

    for i, row in enumerate(data, start=2):  # row 2 is first data row
        record = dict(zip(COLS, row + [""] * (len(COLS) - len(row))))
        if record["status"].strip().lower() != "pending":
            continue

        if not record["slug"]:
            record["slug"] = slugify(record["topic"])

        sheets.values().update(
            spreadsheetId=args.sheet_id,
            range=f"Topics!A{i}:B{i}",
            valueInputOption="RAW",
            body={"values": [["in-progress", record["slug"]]]},
        ).execute()

        print(json.dumps(record))
        return

    print("{}")


if __name__ == "__main__":
    main()
