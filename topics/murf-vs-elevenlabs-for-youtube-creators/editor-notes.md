# Editor Notes — Murf vs ElevenLabs: The Credit Math Nobody Shows You

Reviewed: no

## Checks
- [x] Fact trace — 16 distinct claims, 16 traced, 0 rewritten as opinion
- [x] Banned words — 0 found, 0 replaced
- [x] Hype check — pass (no unsupported superlatives; "costs way more," "cheaper at every comparable tier," and the 9.4/7.8 gap all trace to research)
- [x] Affiliate mentions: 3 (target 2–4) — tools: ElevenLabs (primary), Pictory, TubeBuddy. Murf is the comparison subject, not an affiliate.
- [x] Tradeoff present per tool: pass — ElevenLabs (credit burn / forced Pro tier), Pictory (hard video-minute cap), TubeBuddy (upkeep / data you must act on), Murf (robotic artifacts, clipping, manual pronunciation fixes)
- [x] V3 tag validation: 7 tags, 7 valid, 0 rewritten — [curious] x1, [pause] x5, [excited] x1. None stacked, none contain editor notes, all placed immediately before their line.
- [x] Rhythm: short-line count ~12, long-line count ~6 across ~7 min — pass
- [x] CTA fidelity: match — final cta line is verbatim to brief.md (only addition is the valid [excited] tag prefix)

## Changes Made
- None substantive. The script passed all 8 checks on the first pass. script-edited.md is a faithful copy of script.md with all `// VISUAL:`, `// SECTION`, and `[bracket]` tags preserved.

## Open Questions for Human Reviewer

All four original open questions have been addressed (commits as of 2026-05-20):

- [RESOLVED] Pricing now verified from the official ElevenLabs and Murf pages; research.md Pricing table + cost model rebuilt. ElevenLabs Starter is $6 (not $5). (Pictory still third-party — official page 403s.)
- [RESOLVED] The single-sourced "2.8x advertised rate" figure was removed and replaced with an auditable cost model: ElevenLabs ~3x cheaper at ~4 videos/month (~32 min), narrowing to ~1.3x — and flipping to Murf on annual billing — at the comparable Creator tier. The on-screen volume caveat prevents overclaiming.
- [RESOLVED] chars/min reconciled to ElevenLabs' official ~1,000/min (10K credits ≈ 10 min); the third-party "15,000 per 10-min" figure was dropped.
- [RESOLVED] The 9.4/7.8 realism scores are now attributed on-screen to aitools-directory and StartWithSam — no first-party-testing implication.
- [RESOLVED] Murf cloning ~$3,000/yr figure removed as unverified (Murf lists Enterprise as Custom / Contact Sales). Script and research now say enterprise-only, contact sales, no public price.
- [ADDED] An affiliate-disclosure line was added to the CTA section.

Remaining for Zerick's final pass: confirm the overall framing, then flip `Reviewed: no` → `yes`.
