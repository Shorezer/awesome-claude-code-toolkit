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
- PRICING NOT FROM OFFICIAL SOURCES. research.md flags that elevenlabs.io/pricing, murf.ai/pricing, and pictory.ai/pricing all returned HTTP 403 on direct fetch; every price in this script came from third-party summaries dated 2026-05-20. Spot-check the following on the official pages before publishing: ElevenLabs free/$5/$22/$99 tiers and Instant Voice Cloning on the $5 Starter plan; Murf Creator at $29/mo ($19 annual) and the ~$3,000/yr enterprise cloning add-on; Pictory Professional at $35/mo annual with 600 video min and 120 ElevenLabs premium-voice min, plus Starter at 200 video min.
- The "2.8x advertised rate" figure (line: tracked user) traces to a single third-party source (qcall.ai/elevenlabs-review), not a controlled benchmark. It is load-bearing for the entire hook and title. Confirm you are comfortable presenting one tracked user's result as the framing claim.
- Internal characters-per-minute inconsistency carried over from research: the problem section states a 10-minute narration ≈ 15,000 characters, while the walkthrough states Multilingual v2's 10,000-char cap ≈ 10 minutes of audio. Both numbers individually trace to research.md (pain points vs. fact 4), but they imply different chars/minute rates. A sharp viewer could notice. I did not reconcile this by inventing a number — flagging for you to decide whether to align the framing.
- The 9.4 vs 7.8 realism scores are described as "independent 2026 testing" but research fact 5 sources them to two named comparison-review sites (aitools-directory, startwithsam), one benchmark among several. The phrasing is defensible; confirm the on-screen benchmark chart credits the source rather than implying a first-party test.
