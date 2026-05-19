---
description: Run the blog-adapter agent on an existing topic.
argument-hint: <topic-slug>
---

Topic slug: `$1`.

## Pre-flight

Verify `topics/$1/script-edited.md` and `topics/$1/research.md` exist. If either is missing, fail with: "Run `/run-pipeline $1` first."

## Run

Invoke the `blog-adapter` agent and instruct it to produce `topics/$1/blog-post.md`.

## Verify

After the agent finishes:

```
wc -w topics/$1/blog-post.md
```

Confirm word count falls in 1200–1800. If under or over by more than 10%, ask the agent to revise once. Report final word count and the first H2 in the post.
