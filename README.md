# Affiliate Pipeline (Claude Code)

YouTube affiliate marketing pipeline run as a team of specialized Claude Code agents. Replaces the quality-and-iteration layer of a legacy n8n + Perplexity + single-Claude-call setup.

## What it does

For each topic in a Google Sheets queue, the pipeline produces:

- `research.md` — 5 cited facts, pain points, pricing, 3 hook angles, fit-check
- `brief.md` — title, outline, CTA, target keywords
- `script.md` and `script-edited.md` — long-form script with ElevenLabs v3 voice tags
- `editor-notes.md` — 8-check audit
- `voiceover.txt` and `voiceover.mp3` — TTS-ready text + audio
- `thumbnail-prompt.txt` and `thumbnail.png` — YouTube thumbnail
- `video.mp4` — final assembled file
- `blog-post.md` (1200–1800 w) and `linkedin-post.md` (150–250 w) — derivatives
- `broll-shotlist.md` — visual plan extracted from `// VISUAL:` notes

Auto-publish is **OFF** by default. See [Safety](#safety).

## Quickstart

```bash
git clone <this-repo>
cd <this-repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
$EDITOR .env          # fill API keys

# inside Claude Code
/next-topic           # fetches a row, scaffolds topics/<slug>/, runs pipeline
```

You'll need:

- A Google Sheet with columns `status | slug | topic | audience | affiliate_tool | notes` (rename the tab `Topics`). Rows with `status=pending` are picked up by `/next-topic`.
- A Google OAuth 2.0 **Desktop** client (`credentials/client_secret.json`) with the Sheets API and YouTube Data API v3 enabled. First run opens a browser for consent and caches a token in `credentials/`. The consenting account must have edit access to the sheet.
- An ElevenLabs voice ID (any v3-compatible voice).
- `ffmpeg` installed on the system PATH.

## Project layout

```
.claude/
  agents/        # 10 specialized agents
  commands/      # 8 slash commands
  settings.json  # default model + permissions
style/           # voice guide, banned words, ElevenLabs v3 reference, affiliate table, thumbnail rules
scripts/         # Python helpers (TTS, image, video, Sheets, YouTube, WordPress, LinkedIn)
topics/<slug>/   # one directory per topic, all artifacts
topics/_template # blanks copied into each new topic
```

## Commands

| Command | Purpose |
|---|---|
| `/next-topic` | Fetch next pending row from Sheets, scaffold topic dir, run full pipeline |
| `/run-pipeline <slug>` | Run pipeline on an existing topic dir, stops before publish |
| `/multi-take <slug> [--takes N]` | Generate N script variants, editor picks the best |
| `/produce-audio <slug>` | Run ElevenLabs TTS on `voiceover.txt` |
| `/produce-video <slug>` | Generate thumbnail + assemble final mp4 |
| `/adapt-blog <slug>` | Run the blog-adapter agent |
| `/adapt-linkedin <slug>` | Run the linkedin-adapter agent |
| `/publish <slug> [--target ...] [--publish]` | Publish (dry-run unless `--publish`) |

## Safety

Three layers of guardrail before anything goes live:

1. **Script default**: every `scripts/publish_*.py` runs in dry-run unless `--publish` is passed.
2. **Slash command**: `/publish` only forwards `--publish` when the user types it. Without it the command prints the plan only.
3. **Human review gate**: `/publish` refuses to publish unless `topics/<slug>/editor-notes.md` contains `Reviewed: yes`.

To go live: review `script-edited.md` and `editor-notes.md`, add `Reviewed: yes` to the top of `editor-notes.md`, then run `/publish <slug> --target all --publish`.

## See also

- `CLAUDE.md` — full project context loaded into every session
- `DECISIONS.md` — assumptions, TODOs, and first-run checklist
- `style/` — every voice and visual rule the agents follow
