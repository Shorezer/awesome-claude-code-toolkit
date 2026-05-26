"""Dedup against existing topics and append new rows to the Sheets queue.

Existing slugs are read from both topics/<slug>/ directories and (when live)
the sheet itself, so the same topic isn't queued twice. New rows are appended
with a configurable status (default "ready"). Reuses the project's shared
OAuth helper in scripts/google_oauth.py — same auth as the rest of the pipeline.
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOPICS_DIR = os.path.join(REPO_ROOT, "topics")
SHEET_RANGE = "Topics!A:F"  # status | slug | topic | audience | affiliate_tool | notes


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().strip())
    return s.strip("-")[:80] or "untitled"


def existing_slugs_local():
    if not os.path.isdir(TOPICS_DIR):
        return set()
    return {
        d for d in os.listdir(TOPICS_DIR)
        if os.path.isdir(os.path.join(TOPICS_DIR, d)) and not d.startswith("_")
    }


def _sheets_client():
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    from google_oauth import load_credentials
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=load_credentials()).spreadsheets()


def existing_slugs_sheet(sheet_id):
    sheets = _sheets_client()
    rows = sheets.values().get(spreadsheetId=sheet_id, range=SHEET_RANGE).execute().get("values", [])
    return {row[1] for row in rows[1:] if len(row) > 1 and row[1]}


def append_row(sheet_id, status, slug, topic, audience, affiliate_tool, notes):
    sheets = _sheets_client()
    sheets.values().append(
        spreadsheetId=sheet_id,
        range=SHEET_RANGE,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [[status, slug, topic, audience, affiliate_tool, notes]]},
    ).execute()
