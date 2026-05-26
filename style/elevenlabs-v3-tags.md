# ElevenLabs v3 Tag Reference

## CRITICAL

`[brackets]` are reserved for ElevenLabs v3 voice tags ONLY. Any non-tag content inside brackets will be spoken aloud by the TTS engine. Editor and visual notes use `// VISUAL:` and `// SECTION` line prefixes — never brackets.

## Allowed tags

| Tag | Effect | When to use |
|---|---|---|
| `[excited]` | Higher energy, lifted pitch | Hooks, payoff moments |
| `[curious]` | Inquisitive lilt | Questions, hypotheticals |
| `[sarcastic]` | Dry tone | One per script max — overuse kills it |
| `[whispers]` | Soft volume | Asides, "between you and me" |
| `[shouts]` | Volume bump | Reserve for impact, max once per video |
| `[laughs]` | Light chuckle | After a joke, never in front of facts |
| `[sighs]` | Audible sigh | When acknowledging frustration |
| `[pause]` | ~500 ms pause | Mid-sentence breath |
| `[long pause]` | ~1500 ms pause | Section transitions, dramatic effect |

## Usage rules

- Place the tag **immediately before** the line it modifies. Tag affects the line, not the whole paragraph.
- One tag at a time. Do not stack (`[excited][whispers]` is invalid — pick one).
- Use sparingly. A tag every line reads as theater-kid acting. Aim for one tag per 30–60 seconds of audio.
- Tag the emotion, not the word. `[excited] This actually works.` — not `This [excited] actually works.`

## Examples

Correct:

```
[curious] So what happens when you feed it a 20-minute voiceover?
[long pause]
The answer is annoying.
```

Wrong:

```
[excited and curious] This is great           ← stacked, invalid
The [whispers] hard part is pricing.          ← mid-line, behaves unpredictably
[Note: cut this in post] sometimes it fails   ← not a tag, will be spoken aloud
```

## Non-tag annotations

For everything that is NOT spoken:

- `// SECTION <name>` on its own line marks a structural beat (`cold-open`, `problem`, `walkthrough`, `tradeoff`, `alt-picks`, `cta`).
- `// VISUAL: <description>` on its own line describes what should be on screen during the next spoken line(s). The broll-planner reads these.

The `tts-prepper` strips every `// VISUAL:` and `// SECTION` line before sending to ElevenLabs, and preserves every `[bracket]` tag.
