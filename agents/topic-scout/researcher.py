"""Topic candidate sourcing + affiliate tool registry for Topic Scout.

SEO source priority (first one that returns data wins):
  1. Semrush API   (if SEMRUSH_API_KEY is set)
  2. pytrends      (if installed)
  3. YouTube autocomplete (suggestqueries)
  4. built-in seed list   (offline fallback, always available)

Each source yields candidate dicts:
  {keyword, topic, volume, kd, trend, tools, source}
"""

import json
import os
import urllib.parse
import urllib.request

# status: active (link live) | pending (applied, awaiting approval) | not_signed_up
TOOL_REGISTRY = {
    "elevenlabs": {"status": "active", "link": "https://try.elevenlabs.io/sfd8ezh0b45e"},
    "synthesia": {"status": "active", "link": "https://www.synthesia.io?via=zerick"},
    "murf": {"status": "pending"},
    "pictory": {"status": "pending"},
    "descript": {"status": "pending"},
    "invideo": {"status": "pending"},
    "opusclip": {"status": "pending"},
    "tubebuddy": {"status": "not_signed_up", "commission": "50% recurring",
                  "signup_url": "https://www.berush.com/"},
    "semrush": {"status": "not_signed_up", "commission": "$200/sale",
                "signup_url": "https://www.berush.com/"},
    "heygen": {"status": "not_signed_up", "signup_url": "TODO_find_heygen_affiliate"},
    "runway": {"status": "not_signed_up", "signup_url": "TODO_find_runway_affiliate"},
}

ALIASES = {
    "elevenlabs": ["elevenlabs", "eleven labs", "11labs"],
    "synthesia": ["synthesia"],
    "murf": ["murf"],
    "pictory": ["pictory"],
    "descript": ["descript"],
    "invideo": ["invideo", "in video"],
    "opusclip": ["opusclip", "opus clip"],
    "tubebuddy": ["tubebuddy", "tube buddy"],
    "semrush": ["semrush"],
    "heygen": ["heygen", "hey gen"],
    "runway": ["runway", "gen-3", "gen 3"],
}


def detect_tools(keyword):
    k = keyword.lower()
    return [tool for tool, names in ALIASES.items() if any(n in k for n in names)]


def _titleize(kw):
    return kw[:1].upper() + kw[1:]


def _candidate(kw, volume, kd, trend, source):
    return {
        "keyword": kw,
        "topic": _titleize(kw),
        "volume": volume,
        "kd": kd,
        "trend": trend,
        "tools": detect_tools(kw),
        "source": source,
    }


# (keyword, monthly_volume, keyword_difficulty, trend_0_1)
SEED = [
    ("best ai voice generator for youtube", 8100, 34, 0.8),
    ("synthesia vs heygen ai avatars", 4400, 41, 0.9),
    ("elevenlabs review 2026", 6600, 38, 0.7),
    ("runway gen-3 alternatives", 2900, 45, 0.85),
    ("descript vs opusclip for short form", 1900, 29, 0.75),
    ("is semrush pricing worth it", 3300, 52, 0.5),
    ("tubebuddy vs vidiq", 5400, 33, 0.6),
    ("how to start a faceless youtube channel", 12000, 60, 0.9),
    ("pictory ai review", 2400, 31, 0.65),
    ("invideo ai templates", 1600, 28, 0.7),
    ("best ai tools for solo creators 2026", 5900, 48, 0.95),
    ("murf ai pricing", 2700, 30, 0.55),
]


def _from_seed():
    return [_candidate(kw, v, kd, t, "seed") for kw, v, kd, t in SEED]


def _from_semrush():
    key = os.environ.get("SEMRUSH_API_KEY")
    if not key:
        return []
    out = []
    try:
        for s in ("ai voice generator", "ai video tool", "youtube seo tool"):
            params = urllib.parse.urlencode({
                "type": "phrase_related", "key": key, "phrase": s, "database": "us",
                "export_columns": "Ph,Nq,Kd", "display_limit": 10,
            })
            with urllib.request.urlopen("https://api.semrush.com/?" + params, timeout=20) as r:
                lines = r.read().decode().splitlines()
            for line in lines[1:]:
                parts = line.split(";")
                if len(parts) < 3:
                    continue
                out.append(_candidate(parts[0], int(float(parts[1])), int(float(parts[2])), None, "semrush"))
        return out
    except Exception:
        return []


def _from_pytrends():
    try:
        from pytrends.request import TrendReq
    except Exception:
        return []
    out = []
    try:
        py = TrendReq()
        for s in ("ai voice generator", "ai avatar", "youtube automation"):
            py.build_payload([s])
            rising = py.related_queries().get(s, {}).get("rising")
            if rising is None:
                continue
            for _, row in rising.iterrows():
                val = float(row["value"]) if row["value"] else 70
                out.append(_candidate(str(row["query"]), None, None, min(1.0, val / 100.0), "pytrends"))
        return out
    except Exception:
        return []


def _from_youtube_autocomplete():
    out = []
    try:
        for s in ("ai voice", "ai avatar", "ai video editing", "youtube seo"):
            url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
                {"client": "firefox", "ds": "yt", "q": s})
            with urllib.request.urlopen(url, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            for kw in data[1]:
                out.append(_candidate(kw, None, None, 0.6, "youtube"))
        return out
    except Exception:
        return []


def fetch_candidates():
    """Best available source, with the seed list as an always-available fallback."""
    for source in (_from_semrush, _from_pytrends, _from_youtube_autocomplete):
        cands = source()
        if cands:
            return cands
    return _from_seed()
