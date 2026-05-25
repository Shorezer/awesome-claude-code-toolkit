# Affiliate Pipeline — Project Context

This Claude Code project runs a YouTube affiliate marketing pipeline as a team of specialized agents that hand off structured artifacts. The agent team is the whole operation — from SEO topic research through to publishing.

## Niche

AI tools for solo creators: writing, voice, video, workflow automation. Reviews are written the way a smart friend would — pros, cons, real tradeoffs, no hype.

## Current Phase

**Ship & Stabilize.** This agent pipeline is the operation — there is no parallel legacy system. The focus is getting the first video fully through the pipeline and published, closing the affiliate-monetization gap, and hardening pipeline reliability before scaling publishing cadence.

## Success Metrics

The business is pre-revenue, so progress is tracked by leading metrics, not a revenue target:

- **Publishing cadence** — videos shipped per week.
- **Active affiliate programs** — count of approved programs in rotation.
- **Pipeline reliability** — share of runs that finish without manual intervention.
- **Per-video performance** — views, affiliate clicks, CTR, and EPC.

Revenue follows once these are healthy. Do not push tools we wouldn't use ourselves.

## Affiliate Stack

| Program | Niche | Commission | Cookie |
|---|---|---|---|
| Jasper | AI writing | 30% recurring | 30 days |
| Pictory | AI video | 20% recurring | 60 days |
| TubeBuddy | YouTube tooling | 30–50% recurring | 30 days |
| ElevenLabs | AI voice | 20% of first payment | 30 days |
| Semrush | SEO | $200 flat + $10/trial | 120 days |
| ClickBank | Marketplace | Varies (10–75%) | 60 days |

Full reference: `style/affiliate-stack.md`.

## Tone Rules

- Direct, conversational, knowledgeable friend.
- One idea per sentence.
- No hype. Banned terms in `style/banned-words.md`.
- Every tool gets one honest tradeoff. If there's nothing critical to say, the topic isn't ready.
- Cite a fact only if it traces to `research.md`.

## Automation Boundary

**Auto-publish is OFF by default.** Every publisher script is dry-run unless invoked with `--publish`, and `/publish` requires both an explicit `--publish` flag and a human-reviewed `editor-notes.md` (must contain `Reviewed: yes`). No agent can publish autonomously. The `publisher` agent itself only runs publish scripts in dry-run mode.

## Pipeline State Machine

```
pending  ─►  researched  ─►  briefed  ─►  scripted  ─►  edited  ─►  voiced  ─►  video-ready  ─►  published
   │             │             │            │             │           │              │              │
   │         researcher    brief-writer  scriptwriter   editor    tts-prepper   produce-video   publisher
   │                                                                                                 │
   └──────────────────────────────────  fetch_next_topic.py  ─────────────────────────────────►  update_topic_status.py
```

A topic's current state is whatever artifacts exist in `topics/<slug>/`. The Sheets queue tracks status via `scripts/update_topic_status.py`.

## Artifact Contracts

| Stage | Artifact | Produced by |
|---|---|---|
| researched | `research.md` | researcher |
| briefed | `brief.md` | brief-writer |
| scripted | `script.md` | scriptwriter |
| edited | `script-edited.md`, `editor-notes.md` | editor |
| voiced (prep) | `voiceover.txt` | tts-prepper |
| voiced (audio) | `voiceover.mp3` | `scripts/elevenlabs_tts.py` |
| video-ready | `thumbnail.png`, `video.mp4` | `scripts/generate_thumbnail.py`, `scripts/assemble_video.py` |
| derivatives | `blog-post.md`, `linkedin-post.md`, `broll-shotlist.md`, `thumbnail-prompt.txt` | blog-adapter, linkedin-adapter, broll-planner, thumbnail-designer |
| published | sheet status flipped | `scripts/publish_*.py` + `update_topic_status.py` |

## Project Layout

- `.claude/agents/` — specialized agent definitions
- `.claude/commands/` — slash commands that orchestrate agents
- `.claude/settings.json` — permissions and default model
- `style/` — voice guide, banned words, ElevenLabs v3 reference, affiliate table, thumbnail rules
- `scripts/` — Python helpers (TTS, image, ffmpeg, Sheets, YouTube, WordPress, LinkedIn)
- `topics/<slug>/` — one directory per topic, holds every artifact
- `topics/_template/` — empty templates copied for each new topic

## Working Rules for Every Agent

1. Read the topic's `brief.md` and `research.md` before producing anything.
2. Never invent facts. If a claim isn't in `research.md`, don't write it.
3. `[brackets]` are reserved for ElevenLabs v3 voice tags ONLY.
4. Editor/visual annotations use `// VISUAL:` and `// SECTION` line prefixes.
5. Mention 2–4 affiliate tools per video. More is spam; fewer leaves money on the table.
6. Surface at least one honest tradeoff per tool.
7. Stop before publishing. Publishers are dry-run by default.
