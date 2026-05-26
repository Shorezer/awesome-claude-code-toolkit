---
description: Publish a topic's artifacts. DRY RUN by default. Requires --publish flag AND human review to actually post.
argument-hint: <topic-slug> [--target youtube|blog|linkedin|all] [--publish]
---

Parse `$ARGUMENTS`:
- `$1` = topic slug
- `--target` = `youtube` | `blog` | `linkedin` | `all` (default: `all`)
- `--publish` = present or absent (default: absent → dry-run)

## Safety gate — read first

This command refuses to forward `--publish` unless BOTH conditions are true:

1. `--publish` appears in `$ARGUMENTS`.
2. `topics/$1/editor-notes.md` contains the line `Reviewed: yes` (must be the literal string, anywhere in the file).

If either fails, run every script WITHOUT `--publish` and clearly tell the user which condition failed and how to fix it.

## Pre-flight

Required artifacts depending on target:

| Target | Required files |
|---|---|
| youtube | `topics/$1/video.mp4`, `topics/$1/thumbnail.png`, `topics/$1/brief.md`, `topics/$1/blog-post.md` (description source) |
| blog | `topics/$1/blog-post.md`, `topics/$1/brief.md` |
| linkedin | `topics/$1/linkedin-post.md` |

If any required file is missing, fail with the missing path.

## Delegate

Invoke the `publisher` agent. Pass it the slug, the resolved `--target`, and whether `--publish` is authorized (per the safety gate). The publisher prints the plan first, then runs the scripts.

## Targets

The publisher runs these (each with or without `--publish` per the gate):

- `youtube`:
  ```
  python scripts/publish_youtube.py --video topics/$1/video.mp4 --thumbnail topics/$1/thumbnail.png --title "<from brief>" --description "<derived>" [--publish]
  ```
- `blog`:
  ```
  python scripts/publish_blog.py --post topics/$1/blog-post.md --title "<from brief>" [--publish]
  ```
- `linkedin`:
  ```
  python scripts/publish_linkedin.py --post topics/$1/linkedin-post.md [--publish]
  ```

## After a real publish

If `--publish` was authorized and any target succeeded:

```
python scripts/update_topic_status.py --slug $1 --status published
```

## Final report

For each target: dry-run plan or real result (ID/URL). Status update result. Open items to verify on the live page.
