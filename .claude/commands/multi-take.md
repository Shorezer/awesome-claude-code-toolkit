---
description: Run the scriptwriter N times in parallel and have the editor pick the best take.
argument-hint: <topic-slug> [--takes N]
---

Topic slug: `$1`. Parse `--takes` from `$ARGUMENTS`; default to `3`.

## Pre-flight

- Verify `topics/$1/brief.md` and `topics/$1/research.md` exist. If either is missing, fail with a clear message pointing to `/run-pipeline $1`.

## Steps

1. In a single message, fire `--takes` parallel Task invocations to the `scriptwriter` agent. Instruct each one to write to:
   - take 1 → `topics/$1/script-take-1.md`
   - take 2 → `topics/$1/script-take-2.md`
   - take N → `topics/$1/script-take-N.md`
   Each take should explore a different hook/structure from research.md's three angles, plus one variant of the writer's choice if N > 3.

2. After all takes are written, invoke the `editor` agent with this instruction:
   > Read `topics/$1/script-take-*.md`. Pick the strongest take based on the 8-check criteria. Copy it to `topics/$1/script.md`. Then run your normal editing pass producing `script-edited.md` and `editor-notes.md`. In editor-notes, record which take was selected and why.

3. Report:
   - The N take files written
   - Which take the editor selected
   - The first three lines of `editor-notes.md`'s "Selected" justification

## Notes

- This does NOT advance the pipeline past `editor`. Run `/run-pipeline $1` after if you want the rest, or invoke later stages individually.
- Don't delete the unused takes — they're useful for retrospective analysis of which hook angles convert.
