---
description: Run the linkedin-adapter agent on an existing topic.
argument-hint: <topic-slug>
---

Topic slug: `$1`.

## Pre-flight

Verify `topics/$1/script-edited.md` exists. If not: "Run `/run-pipeline $1` first."

## Run

Invoke the `linkedin-adapter` agent and instruct it to produce `topics/$1/linkedin-post.md`.

## Verify

After the agent finishes:

```
wc -w topics/$1/linkedin-post.md
grep -E 'https?://' topics/$1/linkedin-post.md && echo "URL FOUND — must be removed"
```

Confirm word count falls in 150–250. Confirm no URL in body. If either fails, ask the agent to revise once. Report final word count.
