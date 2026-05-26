#!/usr/bin/env python3
"""Topic Scout — source, score, dedup, and queue new video topics.

KEY RULE: affiliate match is an OPPORTUNITY signal, never a filter. Topics
featuring tools we haven't signed up for still rank and are flagged with
affiliate_action_needed + a signup URL.

Usage:
  python3 agents/topic-scout/scout.py --dry-run --top 5
  python3 agents/topic-scout/scout.py --top 10            # writes to the sheet
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import researcher
import scorer
import sheet_writer

DEFAULT_AUDIENCE = "Solo creators using AI for writing, voice, and video"


def build_notes(s):
    sub = s["subscores"]
    parts = [
        f"score={s['score']}",
        f"(intent={sub['intent']} aff={sub['affiliate']} vol={sub['volume']} "
        f"kd={sub['kd']} fresh={sub['freshness']})",
        f"src={s['source']}",
    ]
    if s["affiliate_action_needed"]:
        parts.append("AFFILIATE_ACTION_NEEDED")
        if s["signup_urls"]:
            parts.append("signup=" + ",".join(s["signup_urls"]))
    return " ".join(parts)


def claude_select(shortlist):
    """Optional final ranking by Claude using prompt.md. Falls back to score
    order if there's no API key or anything goes wrong."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or key.startswith("TODO"):
        return shortlist
    try:
        import anthropic

        prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt.md")
        with open(prompt_path) as f:
            system = f.read()
        payload = [
            {"slug": s["slug"], "topic": s["topic"], "score": s["score"],
             "primary_tool": s["primary_tool"], "affiliate_action_needed": s["affiliate_action_needed"]}
            for s in shortlist
        ]
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        order = json.loads(msg.content[0].text)
        by_slug = {s["slug"]: s for s in shortlist}
        reordered = [by_slug[sl] for sl in order if sl in by_slug]
        return reordered or shortlist
    except Exception as e:
        print(f"WARN: Claude selection skipped ({e}); using score order.", file=sys.stderr)
        return shortlist


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Score and print; do not write the sheet")
    ap.add_argument("--top", type=int, default=10, help="How many top topics to queue")
    ap.add_argument("--status", default="ready", help="Sheet status for new rows (default: ready)")
    args = ap.parse_args()

    candidates = researcher.fetch_candidates()
    source = candidates[0]["source"] if candidates else "none"
    scored = sorted(
        (scorer.score(c, researcher.TOOL_REGISTRY) for c in candidates),
        key=lambda s: s["score"],
        reverse=True,
    )

    # Dedup against local topic dirs (and the sheet when live).
    seen = sheet_writer.existing_slugs_local()
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not args.dry_run and sheet_id:
        try:
            seen |= sheet_writer.existing_slugs_sheet(sheet_id)
        except Exception as e:
            print(f"WARN: could not read sheet for dedup: {e}", file=sys.stderr)

    pool = []
    for s in scored:
        slug = sheet_writer.slugify(s["topic"])
        if slug in seen:
            continue
        s["slug"] = slug
        seen.add(slug)
        pool.append(s)
        if len(pool) >= max(args.top * 2, args.top):
            break

    if not args.dry_run:
        pool = claude_select(pool)
    selected = pool[: args.top]

    print(f"\nTopic Scout — {len(selected)} topic(s) | source={source} | "
          f"{'DRY RUN' if args.dry_run else 'LIVE'}\n")
    print(f"{'#':>2}  {'score':>5}  {'tool':<11} act  slug")
    for i, s in enumerate(selected, 1):
        flag = "!" if s["affiliate_action_needed"] else " "
        print(f"{i:>2}  {s['score']:>5}  {str(s['primary_tool'] or '-'):<11} {flag:>3}  {s['slug']}")
        if s["affiliate_action_needed"] and s["signup_urls"]:
            print(f"      signup needed: {', '.join(s['signup_urls'])}")

    if args.dry_run:
        print(f"\n[DRY RUN] No rows written. Planned rows (status={args.status}):")
        for s in selected:
            print(f"  - {s['slug']} | {s['topic']} | {s['primary_tool'] or '-'} | {build_notes(s)}")
        return

    if not sheet_id:
        print("ERROR: GOOGLE_SHEET_ID not set; cannot write rows.", file=sys.stderr)
        sys.exit(2)

    for s in selected:
        sheet_writer.append_row(
            sheet_id, args.status, s["slug"], s["topic"],
            DEFAULT_AUDIENCE, s["primary_tool"] or "", build_notes(s),
        )
        print(f"queued: {s['slug']} ({args.status})")


if __name__ == "__main__":
    main()
