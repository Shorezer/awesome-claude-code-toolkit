---
description: Fetch the next pending topic from the Sheets queue, scaffold its directory, and run the pipeline.
---

## Steps

1. Run `python scripts/fetch_next_topic.py`. The script returns a single JSON object on stdout.
2. If the output is `{}` (no pending rows), print "No pending topics in queue." and stop.
3. Parse the JSON. Required keys: `slug`, `topic`, `audience`, `affiliate_tool`.
4. Create `topics/<slug>/` and copy every file from `topics/_template/` into it:
   ```
   mkdir -p topics/<slug>
   cp -n topics/_template/* topics/<slug>/
   ```
5. Open `topics/<slug>/brief.md` and fill in only the top fields:
   - Working Title: a draft from the topic line (brief-writer will refine)
   - Audience: from JSON
   - Affiliate Tool(s) → Primary: from JSON
   Leave the rest as template placeholders.
6. Confirm the sheet status was set to `in-progress` (the fetch script does this). Otherwise call `python scripts/update_topic_status.py --slug <slug> --status pending` and report the failure.
7. Invoke `/run-pipeline <slug>`.

## Notes

- The fetch script picks the first row with `status=pending`. To prioritize topics, reorder the sheet.
- If `slug` is empty in the sheet, the fetch script generates one from the topic title and writes it back.
