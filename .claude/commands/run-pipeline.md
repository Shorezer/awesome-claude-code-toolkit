---
description: Run the full pipeline for a topic, stopping before publish.
argument-hint: <topic-slug>
---

Topic slug: `$1`. Topic directory: `topics/$1/`.

## Pre-flight

1. Verify `topics/$1/` exists. If not, fail with: "Topic dir not found. Run `/next-topic` or copy `topics/_template/` into `topics/$1/`."
2. Verify `topics/$1/brief.md` exists. If not, fail with the same message.

## Run agents in this order

For each step: invoke the named agent via the Task tool, wait for it to write its artifact, verify the file appeared, then move on. Do NOT run two agents in parallel — each depends on the previous artifact.

1. `researcher` → writes `topics/$1/research.md`
2. `brief-writer` → updates `topics/$1/brief.md` (uses research.md)
3. `scriptwriter` → writes `topics/$1/script.md`
4. `editor` → writes `topics/$1/script-edited.md` and `topics/$1/editor-notes.md`
5. `tts-prepper` → writes `topics/$1/voiceover.txt`
6. `blog-adapter` → writes `topics/$1/blog-post.md`
7. `linkedin-adapter` → writes `topics/$1/linkedin-post.md`
8. `thumbnail-designer` → writes `topics/$1/thumbnail-prompt.txt`
9. `broll-planner` → writes `topics/$1/broll-shotlist.md`

## Stop conditions

- If brief-writer writes a `## Skipped` brief, STOP after step 2. Report the skip reason. Do not run the rest.
- If the editor's notes file lists any unresolved item under `## Open Questions for Human Reviewer`, still complete steps 6–9, then surface those questions at the end of your summary.

## DO NOT

- DO NOT invoke the `publisher` agent.
- DO NOT run any `scripts/publish_*.py` command.
- DO NOT run `scripts/elevenlabs_tts.py`, `generate_thumbnail.py`, or `assemble_video.py` — those belong to `/produce-audio` and `/produce-video`.

## End-of-run report

Print a status summary listing each artifact that was written (with relative path) and any open questions from `editor-notes.md`. Recommend the next slash command — usually `/produce-audio $1`.
