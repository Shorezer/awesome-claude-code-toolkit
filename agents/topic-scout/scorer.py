"""100-point topic scoring model for Topic Scout.

    total = intent(30) + affiliate_opportunity(25) + volume(20) + KD(15) + freshness(10)

KEY RULE: affiliate match is an OPPORTUNITY signal, never a filter. A topic that
features a tool we are NOT signed up for still scores high on affiliate
opportunity and sets affiliate_action_needed=True with the signup URL. We never
exclude a topic for a missing affiliate relationship.
"""

TRANSACTIONAL = ("pricing", "price", "cost", "coupon", "discount", "deal", "worth it", "free trial")
COMMERCIAL = ("best", " vs ", "review", "alternative", "alternatives", "top ", "comparison", "compare")
INFORMATIONAL = ("how ", "what ", "guide", "tutorial", "tips", "ideas", "examples")


def score_intent(keyword):
    k = f" {keyword.lower()} "
    if any(t in k for t in TRANSACTIONAL):
        return 30
    if any(t in k for t in COMMERCIAL):
        return 24
    if any(t in k for t in INFORMATIONAL):
        return 12
    return 6


def score_affiliate(tools, registry):
    """Return (points, action_needed, signup_urls, primary_tool).

    Opportunity, not filter: pending/not-signed-up tools still score high and
    raise affiliate_action_needed with a signup URL.
    """
    if not tools:
        return 10, False, [], None  # niche-relevant but no tracked tool

    statuses = [registry[t]["status"] for t in tools if t in registry]
    signup, action = [], False
    for t in tools:
        meta = registry.get(t, {})
        if meta.get("status") in ("pending", "not_signed_up"):
            action = True
            if meta.get("signup_url"):
                signup.append(f"{t}:{meta['signup_url']}")

    if "active" in statuses:
        pts = 25
    elif "pending" in statuses:
        pts = 23
    elif "not_signed_up" in statuses:
        pts = 22
    else:
        pts = 10

    primary = next((t for t in tools if registry.get(t, {}).get("status") == "active"), tools[0])
    return pts, action, signup, primary


def score_volume(v):
    if v is None:
        return 8
    for thr, pts in [(10000, 20), (5000, 16), (2000, 12), (1000, 8), (500, 4)]:
        if v >= thr:
            return pts
    return 2


def score_kd(kd):
    if kd is None:
        return 8
    for thr, pts in [(20, 15), (35, 12), (50, 8), (70, 4)]:
        if kd <= thr:
            return pts
    return 1


def score_freshness(trend):
    if trend is None:
        return 5
    return max(0, min(10, round(trend * 10)))


def score(candidate, registry):
    i = score_intent(candidate["keyword"])
    a, action, signup, primary = score_affiliate(candidate.get("tools", []), registry)
    v = score_volume(candidate.get("volume"))
    k = score_kd(candidate.get("kd"))
    f = score_freshness(candidate.get("trend"))
    return {
        **candidate,
        "score": i + a + v + k + f,
        "subscores": {"intent": i, "affiliate": a, "volume": v, "kd": k, "freshness": f},
        "affiliate_action_needed": action,
        "signup_urls": signup,
        "primary_tool": primary,
    }
