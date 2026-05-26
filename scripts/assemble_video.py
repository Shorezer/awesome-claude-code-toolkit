#!/usr/bin/env python3
"""Assemble an edited 1920x1080 video from a topic's script + voiceover.

Pipeline (unchanged from prior version except the per-cue VISUAL rendering):
  1. Parse // VISUAL: cues + the narration that follows each, in order.
  2. Time each cue proportionally to its narration word count, against the
     ffprobe-measured voiceover.mp3 duration.
  3. Build a visual per cue:
       - graphic : an HTML/CSS slide rendered to PNG via a headless browser
                   (Playwright/Chromium) — polished, on-brand templates.
       - broll   : Pexels stock video, trimmed/looped to the window.
       - screen  : an HTML/CSS screen-capture placeholder slide.
  4. Composite with ffmpeg and mux voiceover.mp3 -> video.mp4.

Graphics rebuild: graphic-type and screen-placeholder cues are now rendered as
designed HTML/CSS slides (not Pillow), screenshotted at 1920x1080 by Chromium.

One-time setup on the target machine:
    pip install -r requirements.txt
    playwright install chromium          # downloads the browser
    playwright install-deps              # (Linux) system libs, may need sudo
Optionally install the Inter font system-wide for the intended typography;
otherwise a clean system-ui fallback is used.

CLI unchanged: --audio, --image (compat), -o. The script path is derived from
the audio file's directory. PEXELS_API_KEY (from .env) enables stock b-roll;
empty key makes broll cues fall back to a generated placeholder slide.
"""

import argparse
import html as _html
import os
import re
import subprocess
import sys
import tempfile
import time

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

import requests

W, H = 1920, 1080
FPS = 30
PEXELS_TIMEOUT = 600       # slow/flaky connections — be generous
PEXELS_RETRIES = 3


# ===================================================================== brand slides
BRAND_CSS = """
:root{--bg:#0F1115;--card:#1A1D24;--accent:#FF8A3D;--accent2:#4DA6FF;--head:#F2F4F7;--muted:#9AA4B2;}
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:1920px;height:1080px;background:var(--bg);color:var(--head);
 font-family:'Inter','Inter UI',system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased;letter-spacing:-.01em;}
.stage{width:1920px;height:1080px;display:flex;padding:120px;}
.card{background:var(--card);border-radius:32px;padding:120px;flex:1;display:flex;flex-direction:column;
 justify-content:center;box-shadow:0 40px 120px rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.05);}
.kicker{color:var(--accent);font-size:36px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;margin-bottom:52px;}
.accent{color:var(--accent);} .accent2{color:var(--accent2);} .muted{color:var(--muted);}
.center{text-align:center;align-items:center;justify-content:center;}
.big{font-size:132px;font-weight:800;line-height:1.05;max-width:1500px;letter-spacing:-.025em;}
.cap{font-size:46px;color:var(--muted);margin-top:60px;max-width:1400px;line-height:1.3;}
.row{display:flex;gap:64px;width:100%;align-items:stretch;}
.col{flex:1;background:rgba(255,255,255,.035);border-radius:24px;padding:80px;display:flex;
 flex-direction:column;justify-content:center;}
.col h3{font-size:46px;font-weight:600;color:var(--muted);margin-bottom:32px;letter-spacing:0;}
.col .v{font-size:72px;font-weight:800;line-height:1.08;}
.vs{display:flex;align-items:center;font-size:60px;font-weight:800;color:var(--accent);}
table{width:100%;border-collapse:collapse;font-size:54px;table-layout:fixed;}
th{text-align:left;color:var(--muted);font-weight:600;font-size:42px;text-transform:uppercase;
 letter-spacing:.08em;padding-bottom:40px;}
th.l{color:var(--accent2);}
td{padding:32px 0;border-top:1px solid rgba(255,255,255,.08);font-weight:700;}
.bars{display:flex;gap:180px;align-items:flex-end;justify-content:center;margin:0;}
.bar{width:260px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;}
.bar .val{font-size:64px;font-weight:800;margin-bottom:14px;}
.bar .fill{width:100%;border-radius:20px 20px 0 0;background:var(--accent2);}
.bar.win .fill{background:var(--accent);}
.bar.win .val{color:var(--accent);}
.bar .lab{font-size:48px;font-weight:700;margin-top:34px;color:var(--head);}
.pills{display:flex;gap:52px;justify-content:center;flex-wrap:wrap;}
.pill{background:rgba(255,138,61,.12);border:2px solid var(--accent);color:var(--head);
 font-size:66px;font-weight:700;padding:40px 72px;border-radius:999px;}
.ph{border:4px dashed rgba(154,164,178,.45);}
.title{font-size:72px;font-weight:800;margin-bottom:28px;line-height:1.1;}
.note{font-size:44px;color:var(--muted);margin-top:40px;}
"""

_NUM_RE = re.compile(r'(\$\d[\d,\.]*(?:\s?\([^)]*\))?|\d+(?:\.\d+)?\s?[×x]\b|\d+(?:\.\d+)?%|\b\d[\d,\.]{2,}\b)')


def _esc(s):
    return _html.escape(s or "")


def _hl(s):
    """Reserve the warm accent for numeric emphasis."""
    return _NUM_RE.sub(lambda m: f'<span class="accent">{m.group(0)}</span>', _esc(s))


def _doc(body):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{BRAND_CSS}</style></head><body>{body}</body></html>"


def tpl_callout(headline, caption=""):
    cap = f'<div class="cap">{_esc(caption)}</div>' if caption else ""
    return _doc(f'<div class="stage"><div class="card center"><div class="big">{_hl(headline)}</div>{cap}</div></div>')


def tpl_twoup(title, left, right):
    ll, lv = left
    rl, rv = right
    kick = f'<div class="kicker">{_esc(title)}</div>' if title else ""
    return _doc(
        f'<div class="stage"><div class="card">{kick}<div class="row">'
        f'<div class="col"><h3>{_esc(ll)}</h3><div class="v">{_hl(lv)}</div></div>'
        f'<div class="vs">VS</div>'
        f'<div class="col"><h3>{_esc(rl)}</h3><div class="v">{_hl(rv)}</div></div>'
        f'</div></div></div>'
    )


def tpl_pricingtable(left_label, left_tiers, right_label, right_tiers):
    n = max(len(left_tiers), len(right_tiers))
    rows = ""
    for i in range(n):
        l = left_tiers[i] if i < len(left_tiers) else ""
        r = right_tiers[i] if i < len(right_tiers) else ""
        rows += f'<tr><td class="accent2">{_esc(l)}</td><td>{_esc(r)}</td></tr>'
    return _doc(
        f'<div class="stage"><div class="card"><div class="kicker">Pricing</div>'
        f'<div style="width:100%"><table><thead><tr><th class="l">{_esc(left_label)}</th><th>{_esc(right_label)}</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div></div></div>'
    )


def tpl_barchart(labels, values, title="", caption=""):
    vmax = max(values) if values else 1
    bars = ""
    for v, lab in zip(values, labels):
        h = int(240 * (v / vmax)) if vmax else 0
        win = "win" if v == vmax else ""
        bars += (f'<div class="bar {win}"><div class="val">{v}</div>'
                 f'<div class="fill" style="height:{h}px"></div>'
                 f'<div class="lab">{_esc(lab)}</div></div>')
    kick = f'<div class="kicker">{_esc(title)}</div>' if title else ""
    cap = f'<div class="cap">{_esc(caption)}</div>' if caption else ""
    return _doc(f'<div class="stage"><div class="card center">{kick}<div class="bars">{bars}</div>{cap}</div></div>')


def tpl_sectionheader(parts):
    pills = "".join(f'<div class="pill">{_esc(p)}</div>' for p in parts)
    return _doc(f'<div class="stage"><div class="card center"><div class="pills">{pills}</div></div></div>')


def tpl_placeholder(text):
    return _doc(
        f'<div class="stage"><div class="card ph center">'
        f'<div class="kicker">Screen capture — editor to drop in</div>'
        f'<div class="title">{_esc(text)}</div>'
        f'<div class="note">Record this product UI and replace this slide.</div></div></div>'
    )


class SlideRenderer:
    """Render HTML slides to 1920x1080 PNGs with one shared Chromium instance."""

    def __enter__(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print(
                "ERROR: playwright is required for slide rendering.\n"
                "  pip install -r requirements.txt\n"
                "  playwright install chromium\n"
                "  playwright install-deps   # Linux system libs (may need sudo)",
                file=sys.stderr,
            )
            sys.exit(2)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(args=["--no-sandbox"])
        self._page = self._browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        return self

    def render(self, html, out_path):
        self._page.set_content(html, wait_until="load")
        self._page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": W, "height": H})

    def __exit__(self, *exc):
        try:
            self._browser.close()
        finally:
            self._pw.stop()


# ===================================================================== classify + parse (unchanged)
SCREEN_KW = ["signup", "sign-up", "dashboard", "editor", "interface", "timeline",
             "panel", "credit meter", "regenerate button", "screen record",
             "screen-record", "screen capture", " ui ", "clip", "app "]
GRAPHIC_KW = ["on-screen text", "text overlay", "card", "chart", "bar chart", "table",
              "comparison header", "stat", "quote", "pricing", "$", "credits",
              "benchmark", "callout", "overlay", "header", "languages", "≈", "×", "cheaper"]
BROLL_KW = ["waveform", "microphone", "split screen", "abstract", "desk", "b-roll",
            "footage", "stock"]


def classify(cue):
    c = f" {cue.lower()} "
    if any(k in c for k in SCREEN_KW):
        return "screen"
    if any(k in c for k in GRAPHIC_KW):
        return "graphic"
    if any(k in c for k in BROLL_KW):
        return "broll"
    return "graphic"


def parse_cues(script_path):
    cues = []
    cur = None
    with open(script_path) as f:
        for raw in f.read().splitlines():
            line = raw.strip()
            m = re.match(r"^//\s*VISUAL:\s*(.+)$", line, re.IGNORECASE)
            if m:
                cur = {"cue": m.group(1).strip(), "narration": ""}
                cues.append(cur)
                continue
            if line.startswith("//") or line.startswith("#") or not line:
                continue
            if cur is not None:
                cur["narration"] += " " + re.sub(r"\[[^\]]*\]", "", line)
    for c in cues:
        c["narration"] = c["narration"].strip()
        c["words"] = max(1, len(c["narration"].split()))
    return cues


def extract_headline(cue):
    quotes = re.findall(r'"([^"]+)"', cue)
    if quotes:
        return " — ".join(quotes)
    head = cue.split(" — ")[0]
    if ":" in head:
        head = head.split(":", 1)[1]
    return head.strip()


def extract_caption(cue):
    m = re.search(r'caption[:\s]+"?([^"]+)"?', cue, re.IGNORECASE)
    return m.group(1).strip().rstrip('"') if m else ""


# ===================================================================== graphic routing
def _data_part(cue):
    """Cue text with the trailing caption clause removed."""
    return cue.split("—")[0].strip()


def _side(s):
    s = s.strip().strip(",")
    q = re.search(r'"([^"]+)"', s)
    if q:
        label = s[: q.start()].strip().strip(",")
        return label, q.group(1)
    toks = s.split()
    return (toks[0], " ".join(toks[1:])) if len(toks) > 1 else ("", s)


def graphic_html(cue):
    cl = cue.lower()
    core = _data_part(cue)
    caption = extract_caption(cue)

    if "bar chart" in cl:
        nums = [float(n) for n in re.findall(r"\d+\.\d+|\d+", core)]
        labels = [t for t in ("ElevenLabs", "Murf", "Pictory", "TubeBuddy") if t.lower() in cl]
        if len(nums) >= 2 and len(labels) >= 2:
            return tpl_barchart(labels[:2], nums[:2], "Voice realism (out of 10)", caption)
        return tpl_callout(extract_headline(cue), caption)

    if "comparison header" in cl or "three-column" in cl:
        body = core.split(":", 1)[1] if ":" in core else core
        parts = [p.strip().strip('"') for p in body.split("/") if p.strip()]
        if len(parts) >= 2:
            return tpl_sectionheader(parts)

    if "pricing table" in cl:
        body = core.split(":", 1)[1] if ":" in core else core
        sides = re.split(r"\s+vs\.?\s+", body, flags=re.IGNORECASE)
        if len(sides) >= 2:
            def side_table(s):
                t = s.strip().split()
                return t[0], [x.strip() for x in " ".join(t[1:]).split("/") if x.strip()]
            ll, lt = side_table(sides[0])
            rl, rt = side_table(sides[1])
            return tpl_pricingtable(ll, lt, rl, rt)

    if re.search(r"\svs\.?\s", core, re.IGNORECASE):
        body = core.split(":", 1)[1] if ":" in core.split(" vs ")[0].lower() or ": " in core else core
        sides = re.split(r"\s+vs\.?\s+", body, flags=re.IGNORECASE)
        if len(sides) >= 2:
            return tpl_twoup("", _side(sides[0]), _side(sides[1]))

    return tpl_callout(extract_headline(cue), caption)


# ===================================================================== ffmpeg / ffprobe / pexels (unchanged)
def run(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        raise RuntimeError(f"command failed: {' '.join(cmd[:3])}...")
    return proc.stdout


def audio_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", path])
    return float(out.decode().strip())


def pexels_broll(keywords, workdir, idx):
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key or api_key.startswith("TODO"):
        return None
    query = " ".join(keywords[:4]) or "abstract technology"
    for attempt in range(1, PEXELS_RETRIES + 1):
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": api_key},
                params={"query": query, "orientation": "landscape", "per_page": 1, "size": "medium"},
                timeout=PEXELS_TIMEOUT,
            )
            r.raise_for_status()
            vids = r.json().get("videos", [])
            if not vids:
                return None
            files = [f for f in vids[0].get("video_files", []) if f.get("width", 0) >= 1280]
            files.sort(key=lambda f: f.get("width", 0))
            link = (files[0] if files else vids[0]["video_files"][0])["link"]
            dest = os.path.join(workdir, f"broll_{idx}.mp4")
            with requests.get(link, stream=True, timeout=PEXELS_TIMEOUT) as dl:
                dl.raise_for_status()
                with open(dest, "wb") as fh:
                    for block in dl.iter_content(1 << 16):
                        fh.write(block)
            return dest
        except Exception as e:
            if attempt == PEXELS_RETRIES:
                sys.stderr.write(f"WARN: Pexels failed for '{query}' ({e}); using placeholder.\n")
                return None
            time.sleep(2 ** attempt)
    return None


def segment_from_image(img_path, dur, seg_path):
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}",
         "-i", img_path,
         "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p",
         "-r", str(FPS), "-c:v", "libx264", "-an", seg_path])


def segment_from_video(clip_path, dur, seg_path):
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", clip_path, "-t", f"{dur:.3f}",
         "-an",
         "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,"
                "crop=1920:1080,setsar=1,fps=30,format=yuv420p",
         "-r", str(FPS), "-c:v", "libx264", seg_path])


# ===================================================================== per-cue visual
def build_visual(cue, kind, dur, workdir, idx, slides):
    seg = os.path.join(workdir, f"seg_{idx:03d}.mp4")
    if kind == "broll":
        kws = [w for w in re.findall(r"[a-zA-Z]+", cue) if len(w) > 3][:5]
        clip = pexels_broll(kws, workdir, idx)
        if clip:
            segment_from_video(clip, dur, seg)
            return seg
        kind = "graphic"
        cue = f"B-roll: {cue}"

    img = os.path.join(workdir, f"img_{idx:03d}.png")
    html = tpl_placeholder(cue) if kind == "screen" else graphic_html(cue)
    slides.render(html, img)
    segment_from_image(img, dur, seg)
    return seg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--image", help="Thumbnail (accepted for compatibility; unused)")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"ERROR: audio not found: {args.audio}", file=sys.stderr)
        sys.exit(1)

    topic_dir = os.path.dirname(os.path.abspath(args.audio))
    script_path = os.path.join(topic_dir, "script-edited.md")
    if not os.path.exists(script_path):
        print(f"ERROR: script-edited.md not found beside audio: {script_path}", file=sys.stderr)
        sys.exit(1)

    try:
        total = audio_duration(args.audio)
    except FileNotFoundError:
        print("ERROR: ffprobe/ffmpeg not on PATH", file=sys.stderr)
        sys.exit(2)

    cues = parse_cues(script_path)
    if not cues:
        print("ERROR: no // VISUAL: cues found in script-edited.md", file=sys.stderr)
        sys.exit(1)

    total_words = sum(c["words"] for c in cues)
    durations = [total * c["words"] / total_words for c in cues]

    print(f"Assembling {len(cues)} cues over {total:.1f}s of voiceover...")

    workdir = tempfile.mkdtemp(prefix="assemble_")
    segments = []
    try:
        with SlideRenderer() as slides:
            for i, (cue, dur) in enumerate(zip(cues, durations)):
                kind = classify(cue["cue"])
                seg = build_visual(cue["cue"], kind, max(dur, 0.8), workdir, i, slides)
                segments.append(seg)
                print(f"  [{i+1:02d}/{len(cues)}] {kind:7s} {dur:5.1f}s  {cue['cue'][:70]}")

        listfile = os.path.join(workdir, "segments.txt")
        with open(listfile, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        silent = os.path.join(workdir, "silent.mp4")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
             "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", silent])

        run(["ffmpeg", "-y", "-i", silent, "-i", args.audio,
             "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", args.output])
    finally:
        if not os.environ.get("ASSEMBLE_DEBUG"):
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"{args.output}  ({size_mb:.2f} MB, {total:.1f}s)")


if __name__ == "__main__":
    main()
