# Decisions & Assumptions

Every assumption I made while building this scaffold. Review each one and flip it if it doesn't match your setup.

## Assumptions (default behavior you may want to change)

### Pipeline
- **Sequential, not parallel.** `/run-pipeline` runs agents one at a time and each one writes its artifact before the next runs. Faster parallel handoff is possible (e.g. blog-adapter and linkedin-adapter could run in parallel after editor), but for v1 I kept it linear so artifact-state and debugging stay simple.
- **`/multi-take` parallelizes only the scriptwriter.** Three takes run concurrently, then editor picks the best. Editor itself is single-call.
- **Pipeline stops before audio/video.** `/run-pipeline` does NOT call `produce-audio` or `produce-video` even after all writing agents finish. Those are explicit because they cost real money (ElevenLabs + image API).

### Models
- `scriptwriter` and `editor` use `claude-opus-4-7` per your spec.
- Every other agent uses `claude-sonnet-4-6`. `settings.json` sets that as the default.

### Tools per agent
- `researcher` gets WebSearch + WebFetch + Read + Write. No Bash — no reason to give it shell access.
- `brief-writer`, `scriptwriter`, `editor`, `blog-adapter`, `linkedin-adapter`, `thumbnail-designer` are file-only (Read/Write/Edit). No Bash, no web.
- `tts-prepper` gets Bash but only to run `strip_visual_tags.py` and `wc`/`grep`.
- `broll-planner` gets Grep added so it can pull `// VISUAL:` lines fast.
- `publisher` gets Read + Bash. No Write — it never edits artifacts, only runs scripts.

### Safety
- **Three-layer publish gate** (see README): script default + slash-command flag + `Reviewed: yes` in editor-notes.
- `settings.json` denies `Bash(git push:*)` and `rm -rf` outright.
- `.env` and `secrets/` are denied from reading. Scripts read env vars from the process environment, not by reading `.env` directly.

### Sheets schema
I assumed columns `status | slug | topic | audience | affiliate_tool | notes` on a tab named `Topics`. If your sheet differs, edit `scripts/fetch_next_topic.py` (COLS list and SHEET_RANGE constant) and `scripts/update_topic_status.py`.

Valid statuses: `pending`, `in-progress`, `researched`, `briefed`, `scripted`, `edited`, `voiced`, `video-ready`, `published`, `failed`, `skipped`. Only `pending` is picked up by `/next-topic`.

### YouTube category
`publish_youtube.py` defaults `categoryId=28` (Science & Technology). If you target a different category, change it.

### YouTube privacy
Defaults to `private` on first upload. You probably want to leave it private and flip to `unlisted` or `public` manually after eyeballing the live page.

### Image API
Defaults to OpenAI's `gpt-image-1` at 1792×1024, then downscales to 1280×720 with Pillow. Switch to Stability by setting `IMAGE_API=stability` in `.env`.

### Affiliate link substitution
Blog publisher substitutes `AFFILIATE_LINK_<TOOL>` placeholders from env vars (`AFFILIATE_LINK_ELEVENLABS`, `AFFILIATE_LINK_JASPER`, etc.). Those env vars are NOT in `.env.example` because the names depend on which tools you actually link from each post — add them as needed. If any placeholder is unresolved, the script refuses to publish.

### LinkedIn
LinkedIn dings external links in post body, so the linkedin-adapter writes posts without URLs and the publisher posts the body alone. **The first-comment-with-link pattern is NOT automated** — the LinkedIn API doesn't support comment-with-link reliably for personal profiles. You'll have to drop the link in a first comment manually for now.

### B-roll
`broll-planner` produces a shot list; `assemble_video.py` currently does the simple thing (static thumbnail + audio). Once you have a stock-footage pipeline (Storyblocks API or local clips), extend `assemble_video.py` to consume `broll-shotlist.md` and ffmpeg-concat the timeline.

### ElevenLabs model
TTS calls `eleven_v3`. If you have access to a different production model ID, override with `--model` on `elevenlabs_tts.py`.

### Python deps
`requirements.txt` is pinned to versions that were current early 2026. If install fails because a pinned version was yanked, loosen the pin and re-pin once it installs cleanly.

## TODOs that need your input

1. **`AFFILIATE_LINK_*` env vars.** Add a line for each affiliate link you'll use, e.g. `AFFILIATE_LINK_ELEVENLABS=https://elevenlabs.io/?via=yourcode`.
2. **YouTube OAuth.** First run will pop a browser for OAuth. Run it from a workstation, not a headless server.
3. **Google Sheet ID + tab.** Create the Sheets queue with the schema above and put its ID in `.env`.
4. **ElevenLabs voice ID.** Pick a v3 voice in the ElevenLabs dashboard and put its ID in `.env`.
5. **Disclosure copy.** The disclosure line in `style/affiliate-stack.md` is a draft. Replace with whatever your FTC counsel approves.
6. **Banned-words list.** I included your spec plus a few common offenders I notice on similar channels. Trim or expand to your taste.
7. **n8n parity gate.** Define what "parity" means for the migration off n8n — output cadence per week, average watch-time, click-through on link in description, etc. Bake those numbers in here so you have a clean handoff criterion.

## First-run checklist

1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Install ffmpeg on PATH: `apt install ffmpeg` / `brew install ffmpeg`.
4. `cp .env.example .env` and fill all required keys.
5. Create `secrets/` directory and drop in `google-service-account.json` + `youtube-client-secret.json`.
6. Create your Google Sheet with the `Topics` tab and required headers. Share it with the service account email (Editor).
7. Add one row with `status=pending` and an interesting topic.
8. Open Claude Code in this repo.
9. Verify agents and commands are loaded: try `/help` and look for `/next-topic`, `/run-pipeline`, etc.
10. Run `/next-topic`. Watch the pipeline complete through `broll-planner`.
11. Read `topics/<slug>/editor-notes.md`. If it looks good, add `Reviewed: yes` at the top.
12. Run `/produce-audio <slug>`, then `/produce-video <slug>`.
13. Run `/publish <slug> --target all` (dry-run — no `--publish` flag). Confirm the plans look right.
14. When ready: `/publish <slug> --target all --publish`.
15. Check that the Sheet's status flipped to `published`.

## Things I did NOT build (yet)

- Hooks (SessionStart, PostToolUse). The current flow doesn't need them — every guardrail is in agent frontmatter, settings.json permissions, or script-level dry-run defaults. Add hooks if you find a class of error that should be machine-enforced rather than reviewer-caught.
- A web UI / Streamlit dashboard for monitoring the queue. Sheet is the dashboard.
- Automatic retry on TTS or image-gen failures. Failures bubble up; rerun the slash command. Add retry if it becomes a real cost.
- Caching of research between topics. Each topic gets fresh research because hot AI-tool facts (pricing, features) shift fast.
- A `/skip` slash command for marking a topic skipped. For now, edit the sheet directly or use `update_topic_status.py --status skipped`.

## Things to verify after first run

- ElevenLabs reads `[curious]` etc correctly with your chosen voice. Some voices ignore tags.
- The 1792→1280 thumbnail downscale isn't blurring your text. If it is, generate at 1280×720 directly (Stability supports this natively; OpenAI doesn't at the time of writing).
- The `// VISUAL:` strip regex doesn't eat something it shouldn't. If you ever write a line with literal `// VISUAL:` content that should be spoken, the regex will swallow it — but you wouldn't have a reason to write that.
