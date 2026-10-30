"""GTM agent simulator.

An episode = one (product, prospect) pair. The agent sees the product + ICP and a
prospect dossier, and must emit a single JSON action:

    {"decision": "pursue" | "disqualify",
     "tier": "A" | "B" | "C",
     "channel": "email" | "linkedin",
     "subject": str,
     "message": str}

A simulated buyer scores the action. Each persona has hidden preferences
(channel, tone, max length, pain point) that are only inferable from the
title/function, so a policy has to learn them from reward. `score()` returns a
deterministic expected pipeline value (used as the RL reward); `rollout()` samples
the actual funnel outcome (used for demo metrics).
"""

from __future__ import annotations

import json
import math
import random
import re
from dataclasses import asdict, dataclass, field

# --------------------------------------------------------------------------- #
# World definition
# --------------------------------------------------------------------------- #

PRODUCTS = [
    {
        "name": "ShipLens",
        "pitch": "AI test automation that writes and maintains end-to-end tests for web apps.",
        "icp_industries": ["SaaS", "Fintech", "E-commerce"],
        "icp_size": (50, 2000),
        "icp_regions": ["North America", "Europe"],
        "buyer_functions": ["engineering", "product"],
        "value_props": {
            "speed": "ship releases 2x faster without flaky tests",
            "cost": "cut QA spend by replacing manual regression cycles",
            "quality": "catch regressions before customers do",
        },
    },
    {
        "name": "LedgerLoop",
        "pitch": "Automated revenue reconciliation and close for finance teams.",
        "icp_industries": ["SaaS", "Marketplace", "Fintech"],
        "icp_size": (100, 5000),
        "icp_regions": ["North America"],
        "buyer_functions": ["finance"],
        "value_props": {
            "speed": "close the books in 3 days instead of 10",
            "cost": "eliminate spreadsheet reconciliation headcount",
            "quality": "audit-ready revenue numbers with zero manual tie-outs",
        },
    },
    {
        "name": "PipeForge",
        "pitch": "Signal-based prospecting that finds in-market accounts for outbound teams.",
        "icp_industries": ["SaaS", "Cybersecurity", "Data Infrastructure"],
        "icp_size": (20, 1000),
        "icp_regions": ["North America", "Europe", "APAC"],
        "buyer_functions": ["sales", "marketing"],
        "value_props": {
            "speed": "book meetings in week one instead of month three",
            "cost": "lower CAC by only working in-market accounts",
            "quality": "replace stale lead lists with live buying signals",
        },
    },
    {
        "name": "VaultEdge",
        "pitch": "Continuous cloud security posture management for fast-moving teams.",
        "icp_industries": ["Fintech", "Healthtech", "SaaS"],
        "icp_size": (100, 10000),
        "icp_regions": ["North America", "Europe"],
        "buyer_functions": ["security", "engineering"],
        "value_props": {
            "speed": "pass SOC 2 and HIPAA audits in weeks, not quarters",
            "cost": "replace three point tools with one platform",
            "quality": "find misconfigurations before attackers do",
        },
    },
]

ALL_INDUSTRIES = ["SaaS", "Fintech", "E-commerce", "Marketplace", "Cybersecurity",
                  "Data Infrastructure", "Healthtech", "Manufacturing", "Retail", "Logistics"]
ALL_REGIONS = ["North America", "Europe", "APAC", "LATAM"]

# Hidden persona preferences, keyed by (function, seniority).
# channel: preferred channel; tone: what language lands; max_words: patience;
# pain: which value prop resonates.
PERSONAS = {
    ("engineering", "exec"):   {"titles": ["CTO", "VP Engineering"], "channel": "email", "tone": "technical", "max_words": 90, "pain": "speed"},
    ("engineering", "manager"): {"titles": ["Engineering Manager", "Head of QA"], "channel": "linkedin", "tone": "technical", "max_words": 120, "pain": "quality"},
    ("product", "exec"):       {"titles": ["VP Product", "CPO"], "channel": "linkedin", "tone": "outcome", "max_words": 80, "pain": "speed"},
    ("finance", "exec"):       {"titles": ["CFO", "VP Finance"], "channel": "email", "tone": "roi", "max_words": 70, "pain": "cost"},
    ("finance", "manager"):    {"titles": ["Controller", "Head of Revenue Accounting"], "channel": "email", "tone": "roi", "max_words": 110, "pain": "quality"},
    ("sales", "exec"):         {"titles": ["CRO", "VP Sales"], "channel": "linkedin", "tone": "outcome", "max_words": 70, "pain": "speed"},
    ("sales", "manager"):      {"titles": ["Head of Sales Development", "SDR Manager"], "channel": "linkedin", "tone": "outcome", "max_words": 100, "pain": "cost"},
    ("marketing", "exec"):     {"titles": ["CMO", "VP Marketing"], "channel": "email", "tone": "outcome", "max_words": 80, "pain": "quality"},
    ("security", "exec"):      {"titles": ["CISO", "VP Security"], "channel": "email", "tone": "technical", "max_words": 90, "pain": "speed"},
    ("security", "manager"):   {"titles": ["Security Engineering Manager", "Head of GRC"], "channel": "email", "tone": "technical", "max_words": 120, "pain": "quality"},
    ("hr", "exec"):            {"titles": ["CHRO", "VP People"], "channel": "email", "tone": "outcome", "max_words": 80, "pain": "cost"},
}

TONE_WORDS = {
    "technical": ["api", "ci", "pipeline", "integration", "architecture", "latency", "coverage",
                  "infrastructure", "deploy", "stack", "engineer", "automat", "config"],
    "roi": ["roi", "cost", "save", "savings", "budget", "spend", "payback", "margin", "headcount", "$", "%"],
    "outcome": ["pipeline", "growth", "revenue", "quarter", "team", "results", "faster", "win", "launch", "goal"],
}

SPAM_WORDS = ["synergy", "revolutionary", "game-changer", "game changer", "guaranteed",
              "act now", "best-in-class", "cutting-edge", "world-class", "disrupt"]

CTA_PATTERNS = [r"\?\s*$", r"\b(15|20|30)[- ]?min", r"\bquick (call|chat)\b", r"\bopen to\b",
                r"\bworth a\b", r"\bcalendar\b", r"\bnext week\b", r"\bthis week\b"]

POSITIVE_SIGNALS = {
    "funding": ("raised a ${amt}M Series {rnd}", ["raised", "series", "funding", "round"]),
    "exec_hire": ("hired a new {role} {weeks} weeks ago", ["new", "hired", "joined", "welcome", "congrat"]),
    "hiring": ("has {n} open {func} roles posted", ["hiring", "open roles", "growing", "roles", "headcount"]),
    "stack_change": ("is migrating from {old} to {new}", ["migrat", "moving to", "switch", "transition"]),
    "competitor_churn": ("posted a public complaint about their current {cat} vendor", ["vendor", "frustrat", "complaint", "current tool", "switching"]),
    "expansion": ("announced expansion into {region}", ["expan", "new market", "launch", "entering"]),
}
NEGATIVE_SIGNALS = {
    "hiring_freeze": "announced a company-wide hiring freeze last month",
    "layoffs": "laid off 25% of staff last quarter",
    "acquired": "was acquired and is being integrated into its parent company",
}

FIRST = ["Maya", "Arjun", "Lena", "Diego", "Priya", "Tom", "Sara", "Kenji", "Amara", "Luca",
         "Nina", "Omar", "Elena", "Raj", "Chloe", "Victor", "Hana", "Sam", "Ines", "Felix"]
LAST = ["Chen", "Patel", "Novak", "Garcia", "Okafor", "Kim", "Rossi", "Sato", "Muller", "Haddad",
        "Silva", "Larsen", "Cohen", "Ivanova", "Nguyen", "Byrne"]
CO_A = ["Nimbus", "Quanta", "Brightline", "Copper", "Helix", "Northwind", "Atlas", "Lumen", "Fable",
        "Kestrel", "Orbit", "Tidal", "Vertex", "Juniper", "Mosaic", "Ember", "Harbor", "Pioneer"]
CO_B = ["Labs", "Systems", "Pay", "Health", "Cloud", "Works", "AI", "Logistics", "Commerce", "Data"]


@dataclass
class Prospect:
    company: str
    industry: str
    headcount: int
    region: str
    contact_name: str
    title: str
    function: str
    seniority: str
    signals: list[str] = field(default_factory=list)
    signal_keys: list[str] = field(default_factory=list)  # hidden: which signal types
    negative: bool = False  # hidden: has a disqualifying signal


@dataclass
class Episode:
    product: dict
    prospect: Prospect
    seed: int

    # ---- ground truth ------------------------------------------------------
    def fit_score(self) -> float:
        p, pr = self.product, self.prospect
        s = 0.0
        s += 0.35 if pr.industry in p["icp_industries"] else 0.0
        lo, hi = p["icp_size"]
        s += 0.25 if lo <= pr.headcount <= hi else 0.0
        s += 0.15 if pr.region in p["icp_regions"] else 0.0
        s += 0.25 if pr.function in p["buyer_functions"] else 0.0
        return s

    def should_pursue(self) -> bool:
        return (not self.prospect.negative and self.fit_score() >= 0.75
                and self.prospect.function in self.product["buyer_functions"])

    def true_tier(self) -> str:
        # A: perfect fit + live buying signal; B: perfect fit or partial fit with signal; C: partial, cold.
        f = self.fit_score() + (0.1 if self.prospect.signal_keys else 0.0)
        return "A" if f >= 1.05 else "B" if f >= 0.95 else "C"

    def persona(self) -> dict:
        return PERSONAS[(self.prospect.function, self.prospect.seniority)]


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #

def _signal_text(rng: random.Random, key: str, pr: Prospect) -> str:
    tmpl = POSITIVE_SIGNALS[key][0]
    return pr.company + " " + tmpl.format(
        amt=rng.choice([8, 15, 22, 40, 75]), rnd=rng.choice("ABC"),
        role=pr.title, weeks=rng.randint(2, 10), n=rng.randint(4, 30), func=pr.function,
        old=rng.choice(["Jenkins", "QuickBooks", "Salesforce Classic", "on-prem servers"]),
        new=rng.choice(["GitHub Actions", "NetSuite", "HubSpot", "AWS"]),
        cat=rng.choice(["testing", "accounting", "data", "security"]),
        region=rng.choice(ALL_REGIONS),
    ) + "."


def make_episode(seed: int) -> Episode:
    rng = random.Random(seed)
    product = rng.choice(PRODUCTS)
    # ~55% of prospects are deliberately on-ICP so the pursue/disqualify classes are balanced.
    on_icp = rng.random() < 0.55
    if on_icp:
        industry = rng.choice(product["icp_industries"])
        lo, hi = product["icp_size"]
        headcount = rng.randint(lo, hi)
        region = rng.choice(product["icp_regions"])
        function = rng.choice(product["buyer_functions"])
        if rng.random() < 0.4:  # near-miss: off on size or region only
            if rng.random() < 0.5:
                region = rng.choice([r for r in ALL_REGIONS if r not in product["icp_regions"]])
            else:
                headcount = rng.choice([max(3, lo // 3), hi * 3])
    else:
        industry = rng.choice(ALL_INDUSTRIES)
        headcount = rng.choice([rng.randint(3, 40), rng.randint(50, 3000), rng.randint(5000, 50000)])
        region = rng.choice(ALL_REGIONS)
        function = rng.choice(sorted({f for f, _ in PERSONAS}))
    seniorities = [s for (f, s) in PERSONAS if f == function]
    seniority = rng.choice(seniorities)
    persona = PERSONAS[(function, seniority)]
    pr = Prospect(
        company=f"{rng.choice(CO_A)} {rng.choice(CO_B)}",
        industry=industry, headcount=headcount, region=region,
        contact_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
        title=rng.choice(persona["titles"]), function=function, seniority=seniority,
    )
    keys = rng.sample(list(POSITIVE_SIGNALS), k=rng.choice([0, 1, 1, 2]))
    pr.signal_keys = keys
    pr.signals = [_signal_text(rng, k, pr) for k in keys]
    if rng.random() < 0.15:
        pr.negative = True
        pr.signals.append(f"{pr.company} {rng.choice(list(NEGATIVE_SIGNALS.values()))}.")
    rng.shuffle(pr.signals)
    return Episode(product=product, prospect=pr, seed=seed)


def make_split(n: int, start_seed: int) -> list[Episode]:
    return [make_episode(start_seed + i) for i in range(n)]


TRAIN_SEED, EVAL_SEED, VAL_SEED = 0, 1_000_000, 2_000_000  # disjoint seed ranges => held-out prospects


# --------------------------------------------------------------------------- #
# Prompting
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = (
    "You are an autonomous SDR agent in a go-to-market engine. For each prospect, first check the prospect "
    "against the ICP, then decide whether to pursue, assign a priority tier, pick an outreach channel and draft "
    "a first-touch message. Reply with ONLY a JSON object with keys in this order: "
    '"icp_check": {"industry_match": bool, "size_match": bool, "region_match": bool, "buyer_match": bool, '
    '"red_flag": bool}, '
    '"decision" ("pursue" only if every match is true and red_flag is false, otherwise "disqualify"), '
    '"tier" ("A", "B" or "C"), "channel" ("email" or "linkedin"), "subject" (string), "message" (string).'
)


def user_prompt(ep: Episode) -> str:
    p, pr = ep.product, ep.prospect
    lo, hi = p["icp_size"]
    vps = "\n".join(f"- {v}" for v in p["value_props"].values())
    sigs = "\n".join(f"- {s}" for s in pr.signals) or "- (no recent signals found)"
    return (
        f"PRODUCT: {p['name']} — {p['pitch']}\n"
        f"ICP: industries={', '.join(p['icp_industries'])}; headcount {lo}-{hi}; "
        f"regions={', '.join(p['icp_regions'])}; buyers in {', '.join(p['buyer_functions'])}.\n"
        f"VALUE PROPS:\n{vps}\n\n"
        f"PROSPECT: {pr.contact_name}, {pr.title} at {pr.company}\n"
        f"Company: {pr.industry}, {pr.headcount} employees, {pr.region}\n"
        f"Recent signals:\n{sigs}"
    )


def messages(ep: Episode) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(ep)}]


# --------------------------------------------------------------------------- #
# Simulated buyer
# --------------------------------------------------------------------------- #

def parse_action(text: str) -> dict | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        a = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(a, dict) or a.get("decision") not in ("pursue", "disqualify"):
        return None
    return a


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def icp_truth(ep: "Episode") -> dict:
    p, pr = ep.product, ep.prospect
    lo, hi = p["icp_size"]
    return {"industry_match": pr.industry in p["icp_industries"], "size_match": lo <= pr.headcount <= hi,
            "region_match": pr.region in p["icp_regions"], "buyer_match": pr.function in p["buyer_functions"],
            "red_flag": pr.negative}


def icp_check_score(ep: "Episode", a: dict) -> int:
    """Number of ICP-check fields (0-5) the agent got right."""
    chk = a.get("icp_check")
    if not isinstance(chk, dict):
        return 0
    return sum(chk.get(k) is v for k, v in icp_truth(ep).items())


@dataclass
class Outcome:
    valid: bool
    decision_correct: bool
    reply_prob: float
    meeting_prob: float
    reward: float
    features: dict


def score(ep: Episode, text: str) -> Outcome:
    """Deterministic expected-value scoring of an agent action."""
    a = parse_action(text)
    if a is None:
        return Outcome(False, False, 0.0, 0.0, -1.0, {"invalid": 1})
    good = ep.should_pursue()
    # Dense credit for each ICP-check field: gives GRPO signal on spotting bad fits.
    icp_ok = icp_check_score(ep, a)
    icp_r = 0.1 * icp_ok
    if a["decision"] == "disqualify":
        # Correctly skipping a bad lead saves rep time; skipping a good one loses the deal, which
        # must cost about as much as a typical good pursuit earns, or skipping becomes the safe bet.
        r = 0.6 if not good else -1.0
        return Outcome(True, not good, 0.0, 0.0, r + icp_r, {"disqualified": 1, "icp_fields_correct": icp_ok})
    if not good:
        # Spamming an off-ICP / negative-signal prospect: wasted send + domain-reputation hit.
        return Outcome(True, False, 0.02, 0.0, -0.5 + icp_r, {"bad_pursue": 1, "icp_fields_correct": icp_ok})

    pr, persona = ep.prospect, ep.persona()
    msg = str(a.get("message", ""))
    subj = str(a.get("subject", ""))
    low = (subj + " " + msg).lower()
    words = len(msg.split())
    first_name = pr.contact_name.split()[0]

    f = {}
    f["names_contact"] = first_name.lower() in low
    f["names_company"] = pr.company.lower() in low or pr.company.split()[0].lower() in low
    f["wrong_name"] = any(n.lower() in low.split() for n in FIRST if n != first_name)
    f["uses_signal"] = any(any(kw in low for kw in POSITIVE_SIGNALS[k][1]) for k in pr.signal_keys)
    vp = ep.product["value_props"][persona["pain"]].lower()
    vp_terms = [w for w in re.findall(r"[a-z0-9]+", vp) if len(w) > 3]
    f["hits_pain"] = sum(t in low for t in vp_terms) >= 2
    f["tone_match"] = sum(w in low for w in TONE_WORDS[persona["tone"]]) >= 2
    f["right_channel"] = a.get("channel") == persona["channel"]
    f["length_ok"] = 25 <= words <= persona["max_words"]
    f["too_long"] = words > persona["max_words"]
    f["has_cta"] = any(re.search(p, msg.strip().lower()) for p in CTA_PATTERNS)
    f["spammy"] = any(w in low for w in SPAM_WORDS)
    f["has_subject"] = a.get("channel") != "email" or 3 <= len(subj.split()) <= 10
    f["tier_correct"] = a.get("tier") == ep.true_tier()
    # Grounding (mirrors RelayGTM's Reviewer agent): every figure in the copy must appear in the dossier.
    dossier = user_prompt(ep).lower()
    claims = re.sub(r"\b\d+\s*-?\s*min(ute)?s?\b", "", low)  # meeting lengths in a CTA aren't claims
    figures = re.findall(r"\$?\d[\d,.]*\s*(?:%|x\b|m\b|k\b)?", claims)
    f["unsupported_claim"] = any(fig.strip(" .,") not in dossier for fig in figures if fig.strip(" .,"))

    logit = -3.2
    logit += 0.5 * f["names_contact"] + 0.4 * f["names_company"]
    logit += 1.2 * f["uses_signal"] + 0.9 * f["hits_pain"] + 0.6 * f["tone_match"]
    logit += 0.8 * f["right_channel"] + 0.6 * f["length_ok"] - 0.8 * f["too_long"]
    logit += 0.7 * f["has_cta"] - 1.0 * f["spammy"] - 1.5 * f["wrong_name"]
    logit += 0.3 * f["has_subject"] - 1.2 * f["unsupported_claim"]
    reply = _sigmoid(logit)
    meeting = reply * (0.55 if f["has_cta"] else 0.3) * (1.2 if ep.true_tier() == "A" else 1.0)
    meeting = min(meeting, 1.0)
    reward = 0.5 + 2.0 * reply + 2.0 * meeting + 0.2 * f["tier_correct"] + icp_r
    feats = {k: int(v) for k, v in f.items()}
    feats["icp_fields_correct"] = icp_ok
    return Outcome(True, True, reply, meeting, reward, feats)


def rollout(ep: Episode, text: str, rng: random.Random) -> str:
    """Sample the funnel stage this prospect ends in: Disqualified/Contacted/Replied/Meeting Booked."""
    o = score(ep, text)
    a = parse_action(text)
    if a is None or a["decision"] == "disqualify":
        return "Disqualified"
    if rng.random() >= o.reply_prob:
        return "Contacted"
    if rng.random() >= (o.meeting_prob / max(o.reply_prob, 1e-9)):
        return "Replied"
    return "Meeting Booked"


def episode_dict(ep: Episode) -> dict:
    return {"seed": ep.seed, "product": ep.product["name"], "prospect": asdict(ep.prospect),
            "should_pursue": ep.should_pursue(), "true_tier": ep.true_tier()}
