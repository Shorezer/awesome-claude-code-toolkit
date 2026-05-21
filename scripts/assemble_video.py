#!/usr/bin/env python3
"""Assemble an edited 1920x1080 video from a topic's script + voiceover.

Pipeline:
  1. Parse // VISUAL: cues (and the narration that follows each) from
     script-edited.md, in order.
  2. Get voiceover.mp3 duration via ffprobe; give each cue a time window
     proportional to its narration word count (visuals stay narration-synced).
  3. Classify each cue and build a visual for its window:
       - graphic : Pillow-rendered card/chart/text (real numbers from the cue)
       - broll   : Pexels stock video (keyword search), trimmed/looped to window
       - screen  : labeled placeholder card for a human screen-capture drop-in
  4. Composite the timed sequence with ffmpeg, mux voiceover.mp3, write video.mp4.

CLI is unchanged from the previous version (--audio, --image, -o); the script
path is derived from the audio file's directory.

PEXELS_API_KEY (loaded from .env) enables stock b-roll; if unset, broll cues
fall back to a generated placeholder so the pipeline is never blocked.
"""

import argparse
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
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30
BG = (10, 34, 51)          # dark teal
ACCENT = (255, 107, 26)    # orange
INK = (240, 244, 248)      # near-white
MUTE = (150, 168, 180)
PLACEHOLDER_BG = (28, 32, 38)

PEXELS_TIMEOUT = 600       # slow/flaky connections — be generous
PEXELS_RETRIES = 3

FONT_DIRS = ["/usr/share/fonts", "/Library/Fonts", "/System/Library/Fonts"]


# --------------------------------------------------------------------------- fonts
_font_cache = {}


def _find_font_file(bold):
    want = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for root in FONT_DIRS:
        if not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            if want in files:
                return os.path.join(dirpath, want)
    # any DejaVu / Arial as fallback
    for root in FONT_DIRS:
        if not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith(".ttf") and ("DejaVuSans" in f or "Arial" in f):
                    return os.path.join(dirpath, f)
    return None


def font(size, bold=True):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    path = _find_font_file(bold)
    fnt = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    _font_cache[key] = fnt
    return fnt


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_centered_block(draw, lines, fnt, color, top, line_gap=18):
    y = top
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=fnt)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((W - tw) / 2, y), ln, font=fnt, fill=color)
        y += th + line_gap
    return y


# --------------------------------------------------------------------------- renderers
def render_text_card(cue, headline, caption, out_path, label="GRAPHIC"):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=ACCENT)                 # top accent bar
    d.text((80, 70), label, font=font(34, bold=True), fill=ACCENT)

    head_font = font(96, bold=True)
    lines = wrap(d, headline, head_font, W - 320)
    if len(lines) > 4:                                      # shrink for long text
        head_font = font(64, bold=True)
        lines = wrap(d, headline, head_font, W - 280)
    block_h = sum(d.textbbox((0, 0), ln, font=head_font)[3] for ln in lines) + 18 * (len(lines) - 1)
    _draw_centered_block(d, lines, head_font, INK, (H - block_h) / 2 - 30)

    if caption:
        cap_font = font(40, bold=False)
        cap_lines = wrap(d, caption, cap_font, W - 360)
        _draw_centered_block(d, cap_lines, cap_font, MUTE, H - 80 - 50 * len(cap_lines))
    img.save(out_path)


def render_bar_chart(values, labels, title, caption, out_path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    d.text((80, 70), "BENCHMARK", font=font(34, bold=True), fill=ACCENT)

    tlines = wrap(d, title, font(64, bold=True), W - 320)
    _draw_centered_block(d, tlines, font(64, bold=True), INK, 150)

    base_y = H - 220
    max_h = 560
    vmax = max(values) if values else 1
    n = len(values)
    bar_w = 240
    gap = 200
    total_w = n * bar_w + (n - 1) * gap
    x = (W - total_w) / 2
    for i, (v, lab) in enumerate(zip(values, labels)):
        h = int(max_h * (v / vmax)) if vmax else 0
        color = ACCENT if v == vmax else (90, 120, 140)
        d.rectangle([x, base_y - h, x + bar_w, base_y], fill=color)
        vbbox = d.textbbox((0, 0), str(v), font=font(72, bold=True))
        d.text((x + (bar_w - (vbbox[2] - vbbox[0])) / 2, base_y - h - 90), str(v),
               font=font(72, bold=True), fill=INK)
        lbbox = d.textbbox((0, 0), lab, font=font(44, bold=True))
        d.text((x + (bar_w - (lbbox[2] - lbbox[0])) / 2, base_y + 24), lab,
               font=font(44, bold=True), fill=INK)
        x += bar_w + gap

    if caption:
        cap_font = font(34, bold=False)
        cl = wrap(d, caption, cap_font, W - 360)
        _draw_centered_block(d, cl, cap_font, MUTE, H - 70 - 44 * len(cl))
    img.save(out_path)


def render_placeholder(cue, out_path):
    img = Image.new("RGB", (W, H), PLACEHOLDER_BG)
    d = ImageDraw.Draw(img)
    # dashed-ish border
    for x in range(60, W - 60, 60):
        d.rectangle([x, 60, x + 30, 66], fill=MUTE)
        d.rectangle([x, H - 66, x + 30, H - 60], fill=MUTE)
    for y in range(60, H - 60, 60):
        d.rectangle([60, y, 66, y + 30], fill=MUTE)
        d.rectangle([W - 66, y, W - 60, y + 30], fill=MUTE)

    d.text((80, 80), "SCREEN CAPTURE — EDITOR TO DROP IN", font=font(40, bold=True), fill=ACCENT)
    head = wrap(d, cue, font(72, bold=True), W - 320)
    _draw_centered_block(d, head, font(72, bold=True), INK, (H - 72 * len(head)) / 2 - 40)
    note = "Record this product UI and replace this card."
    nb = d.textbbox((0, 0), note, font=font(40, bold=False))
    d.text(((W - (nb[2] - nb[0])) / 2, H - 160), note, font=font(40, bold=False), fill=MUTE)
    img.save(out_path)


# --------------------------------------------------------------------------- classify + parse
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
    """Return ordered list of {cue, narration} from // VISUAL: blocks."""
    cues = []
    cur = None
    with open(script_path) as f:
        for raw in f.splitlines():
            line = raw.strip()
            m = re.match(r"^//\s*VISUAL:\s*(.+)$", line, re.IGNORECASE)
            if m:
                cur = {"cue": m.group(1).strip(), "narration": ""}
                cues.append(cur)
                continue
            if line.startswith("//") or line.startswith("#") or not line:
                continue
            if cur is not None:
                clean = re.sub(r"\[[^\]]*\]", "", line)  # drop [v3 tags] for word count
                cur["narration"] += " " + clean
    for c in cues:
        c["narration"] = c["narration"].strip()
        c["words"] = max(1, len(c["narration"].split()))
    return cues


def extract_headline(cue):
    quotes = re.findall(r'"([^"]+)"', cue)
    if quotes:
        return " — ".join(quotes)
    # text after a leading "type:" descriptor
    head = cue.split(" — ")[0]
    if ":" in head:
        head = head.split(":", 1)[1]
    return head.strip()


def extract_caption(cue):
    m = re.search(r'caption[:\s]+"?([^"]+)"?', cue, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('"')
    return ""


# --------------------------------------------------------------------------- ffmpeg / ffprobe / pexels
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


def pexels_broll(keywords, window, workdir, idx):
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


def build_visual(cue, kind, dur, workdir, idx):
    """Return a segment mp4 path for this cue."""
    seg = os.path.join(workdir, f"seg_{idx:03d}.mp4")
    if kind == "broll":
        kws = [w for w in re.findall(r"[a-zA-Z]+", cue) if len(w) > 3][:5]
        clip = pexels_broll(kws, dur, workdir, idx)
        if clip:
            segment_from_video(clip, dur, seg)
            return seg
        # fall back to a generated placeholder card
        kind = "graphic"
        cue = f"B-roll: {cue}"

    img = os.path.join(workdir, f"img_{idx:03d}.png")
    if kind == "screen":
        render_placeholder(cue, img)
    elif "bar chart" in cue.lower():
        nums = [float(n) for n in re.findall(r"\d+\.\d+|\d+", cue.split("—")[0])]
        labels = [t for t in ("ElevenLabs", "Murf", "Pictory", "TubeBuddy") if t.lower() in cue.lower()]
        if len(nums) >= 2 and len(labels) >= 2:
            render_bar_chart(nums[:2], labels[:2], "Voice realism (out of 10)", extract_caption(cue), img)
        else:
            render_text_card(cue, extract_headline(cue), extract_caption(cue), img)
    else:
        render_text_card(cue, extract_headline(cue), extract_caption(cue), img)
    segment_from_image(img, dur, seg)
    return seg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--image", help="Thumbnail (accepted for compatibility; used as last-resort fallback)")
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
    # narration-proportional windows; assign rounding remainder to the last cue
    durations = [total * c["words"] / total_words for c in cues]

    print(f"Assembling {len(cues)} cues over {total:.1f}s of voiceover...")

    workdir = tempfile.mkdtemp(prefix="assemble_")
    segments = []
    try:
        for i, (cue, dur) in enumerate(zip(cues, durations)):
            kind = classify(cue["cue"])
            seg = build_visual(cue["cue"], kind, max(dur, 0.8), workdir, i)
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
        # leave images on failure for debugging only if env DEBUG set
        if not os.environ.get("ASSEMBLE_DEBUG"):
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"{args.output}  ({size_mb:.2f} MB, {total:.1f}s)")


if __name__ == "__main__":
    main()
