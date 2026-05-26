# Decisions & Assumptions

Every assumption I made while building this scaffold. Review each one and flip it if it doesn't match your setup.

## Architecture change — Google auth (OAuth 2.0, not service account)

The original scaffold assumed a Google **service account** key for Sheets. The `zandpai.com` Workspace org blocks service-account key creation, so we pivoted to an **OAuth 2.0 Desktop client**.

What changed:

- New shared helper `scripts/google_oauth.py` runs the OAuth Desktop flow and caches/refreshes the token. It requests both Sheets and YouTube scopes in one consent, so a single token file works for the whole pipeline.
- `fetch_next_topic.py`, `update_topic_status.py`, and `publish_youtube.py` now call `load_credentials()` from that helper instead of `service_account.Credentials.from_service_account_file(...)`. The `--creds` CLI arg was dropped; paths come from env vars.
- Env var meanings (reused the existing names):
  - `YOUTUBE_CLIENT_SECRET_PATH` → the downloaded Desktop client secret JSON (`credentials/client_secret.json`).
  - `GOOGLE_SHEETS_CREDS_PATH` → the authorized-user **token cache** written after first consent (`credentials/google_oauth_token.json`), NOT a service-account key.
  - `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` → optional fallback; the helper builds a client config from these if the JSON file is absent.
- OAuth client: project `concise-crane-495108-d3`, Desktop app type. Google Sheets API and YouTube Data API v3 are both enabled on the project.
- `credentials/` is gitignored. `client_secret.json` is present locally; the token JSON is generated on first run.

First-run consent caveat: `run_local_server(port=0)` opens a browser. **It must run on a machine with a browser** — not this headless container. Run any Sheets/YouTube command once locally to mint `credentials/google_oauth_token.json`, then copy that token into the container's `credentials/` if you want to run there.

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

### WordPress.com (blog) — REST API needs a paid plan

`theai4ge.wordpress.com` is a WordPress.com-hosted site, and its plan does not support REST API posting:

- WordPress.com REST API posting (`public-api.wordpress.com/rest/v1.1/sites/<site>/posts/new`) requires a **paid plan (Personal or above)** or a self-hosted site running **Jetpack**, plus an OAuth2 bearer token (`WORDPRESS_COM_TOKEN`). Free WordPress.com sites cannot publish via the API at all.
- `publish_blog.py` detects a wordpress.com host and routes to the REST v1.1 path. When `WORDPRESS_COM_TOKEN` is missing/empty/`TODO`, it now logs a `[SKIP]` message and exits 0 — it does NOT crash the pipeline. This keeps `/publish --target all` working even while WordPress is unconfigured.
- Self-hosted WordPress still works via the `/wp-json/wp/v2/posts` path with `WORDPRESS_USER` + `WORDPRESS_APP_PASSWORD` (basic auth).

To enable WordPress publishing, either upgrade the wordpress.com site to Personal+ and mint an OAuth2 token at https://developer.wordpress.com/apps/, or move the blog to self-hosted WordPress with Jetpack. Until then, blog output (`blog-post.md`) is produced but not auto-published.

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
5. Put your Desktop OAuth `client_secret.json` in `credentials/`. On first run of a Sheets/YouTube command, a browser opens for consent and `credentials/google_oauth_token.json` is written. Do this on a machine with a browser.
6. Create your Google Sheet with the `Topics` tab and required headers. The Google account you consent with must have edit access to the sheet.
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
