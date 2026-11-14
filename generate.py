#!/usr/bin/env python3
"""
OUTER SURVEY OFFICE: Daily Planetary Bulletin.

Generates one procedural planet per day, seeded by the date, so everyone sees
the same world on the same day. Stdlib only.

    python3 generate.py                     # today's survey -> planets/, README.md
    python3 generate.py --date 2026-10-31   # a specific day
    python3 generate.py --date 2026-01-01 --out /tmp/x --no-readme
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import math
import random
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIRST_BULLETIN = dt.date(2026, 11, 14)  # bulletin No. 1
SEED_SALT = "outer-survey-office"       # change this to get a different universe

# ─── Planet classes: name, riso palette, surface style ─────────────────────────
CLASSES = [
    dict(name="Fungal Ocean",   base="#2a6f6b", tones=["#3fa38f", "#1f4e5f", "#8fd6b4"], glow="#8fffd0", style="bands"),
    dict(name="Glass Desert",   base="#e0b48a", tones=["#f3dcc0", "#c98f63", "#fff2e0"], glow="#ffe9c7", style="dunes"),
    dict(name="Gas Giant",      base="#c46a3a", tones=["#e9a368", "#8c3b2a", "#f2d4a0", "#b5523b"], glow="#ffc48a", style="bands", rings=0.6),
    dict(name="Iron Swamp",     base="#4b3b2f", tones=["#6b4f3a", "#2f2620", "#8a6b45"], glow="#d9a86c", style="spots"),
    dict(name="Ice Cathedral",  base="#bcdcf0", tones=["#ffffff", "#8fbbe0", "#e6f2ff"], glow="#d8f1ff", style="craters"),
    dict(name="Lava Garden",    base="#2b1416", tones=["#ff5a36", "#ffb347", "#5a1f1f"], glow="#ff7a4a", style="spots"),
    dict(name="Violet Archive", base="#5b3f8c", tones=["#7d5fb8", "#3e2a66", "#c7a6ff"], glow="#cdb3ff", style="bands", rings=0.4),
    dict(name="Moss World",     base="#4f7a3a", tones=["#7fae4f", "#2f4f2a", "#c9e08a"], glow="#d6ffa8", style="spots", clouds=True),
    dict(name="Cloud Kingdom",  base="#8aa6cc", tones=["#dfe9f7", "#6f8fbf", "#ffffff"], glow="#e4efff", style="bands", clouds=True),
    dict(name="Rust Belt",      base="#a2482c", tones=["#c9673f", "#6e2a1c", "#e39a6b"], glow="#ffb08a", style="craters"),
    dict(name="Chrome Sea",     base="#7f8b98", tones=["#c9d1d9", "#55606c", "#eef2f5"], glow="#f2f6fa", style="bands"),
    dict(name="Coral Shelf",    base="#e2716b", tones=["#f4a49a", "#b84a52", "#ffd6c9"], glow="#ffc2b8", style="spots", clouds=True),
    dict(name="Ink Planet",     base="#1d2240", tones=["#2f3768", "#141830", "#5a66b0"], glow="#8a9bff", style="bands", rings=0.5),
]

HALLOWEEN = dict(name="Haunted World", base="#2a1838", tones=["#ff8c2a", "#4a2a5e", "#1a0f24"], glow="#ffa64d", style="spots")
CHEESE    = dict(name="Cheese (Provisional)", base="#f2c94c", tones=["#e0a93a", "#fff0a8", "#d49a2a"], glow="#fff3b0", style="craters")

# ─── Grammar (Tracery-style: #key# expands to a random entry) ──────────────────
G = {
    "inhabitants": [
        "#count# #creature# who #habit#",
        "#count# #creature# who #habit#",
        "#count# #creature# who #habit#",
        "a single enormous #giant# that #habit_s#",
        "none, officially",
        "#count# #creature#, presumed friendly",
    ],
    "count": ["approximately 40 billion", "three (3)", "an unknown number of", "a small family of",
              "several hundred", "a disputed number of", "roughly a dozen", "too many",
              "eleven", "a quiet majority of"],
    "creature": ["moth-priests", "sentient umbrellas", "very polite crabs", "lichen accountants",
                 "glass herons", "retired satellites", "low-voltage ghosts", "jellyfish with opinions",
                 "lantern-eyed goats", "beetles in small hats", "stone choirs", "migratory furniture",
                 "clouds that have learned to sit", "hermit snails the size of cathedrals",
                 "former astronauts", "librarian eels", "tax inspectors", "foxes made of static",
                 "monks who are also weather", "small, damp dragons"],
    "habit": ["hum in B-flat", "communicate exclusively through weather",
              "worship a lost sock from probe #probe_no#", "are still waiting for a reply",
              "have unionised", "file formal complaints about the sun",
              "build cathedrals out of their own echoes", "migrate north once per century, then apologise",
              "collect the word 'perhaps'", "have mistaken our probe for a god of mild inconvenience",
              "sleep for 900 years at a time", "only exist on Thursdays", "keep a very detailed diary",
              "trade exclusively in compliments", "are mostly bones but remain upbeat",
              "have already surveyed us", "are building a probe of their own, out of spite",
              "know what you did"],
    "habit_s": ["hums in B-flat", "is waiting for a reply", "keeps a very detailed diary",
                "has asked not to be catalogued", "is dreaming the rest of the planet",
                "sneezes once per decade, rearranging the continents", "is, we think, a landlord"],
    "giant": ["mushroom", "eel", "librarian", "tortoise", "hand", "eye that is politely looking away",
              "moth", "accordion", "sleeping dog"],
    "probe_no": ["4471", "12", "9", "300-B", "77"],

    "feature": [
        "a #adj# #landmark# visible from orbit",
        "the oceans are #liquid#",
        "it rains #rain# every #interval#",
        "a lighthouse nobody built",
        "a 900 km crater in the shape of a question mark",
        "a mountain that is slightly taller on Mondays",
        "the planet is hollow, and the inside is nicer",
        "an equator lined with abandoned vending machines",
        "a single road that goes all the way around",
        "the north pole is warm and smells of toast",
        "a #adj# #landmark# that appears in all our photographs, facing the camera",
        "a continent shaped exactly like the previous survey team",
    ],
    "adj": ["singing", "perfectly square", "upside-down", "warm", "apologetic", "unfinished",
            "slowly rotating", "brass", "suspiciously tidy", "very old"],
    "landmark": ["staircase", "canyon", "forest of antennas", "lake", "cathedral", "door",
                 "glacier", "chair", "radio tower"],
    "liquid": ["lukewarm tea", "carbonated", "about 4% soup", "very shallow, everywhere",
               "mirror-still and reflect a different sky", "slightly sticky", "on a timer"],
    "rain": ["small brass keys", "warm static", "glass beads", "the sound of applause",
             "tiny fish", "letters addressed to no one", "buttons"],
    "interval": ["eleven minutes", "leap year", "time someone lies", "seventh sunrise", "Tuesday"],

    "advisory": [
        "Do not answer the humming.", "Do not make eye contact with the moon.",
        "Bring a jacket. And a second, smaller jacket.",
        "The locals will try to give you a hat. Accept the hat.",
        "Landing is permitted. Leaving is under review.",
        "Avoid the southern continent; it is listening.",
        "Do not mention the previous survey team.",
        "Time passes differently here. Set your watch to 'vaguely'.",
        "If you hear your name, it is not for you.",
        "Safe for tourism, unsafe for sincerity.",
        "The gravity is fine. The vibes are not.",
        "Do not feed the weather.",
        "No advisory issued. That is what worries us.",
        "Wipe your boots before leaving. Something will try to come with you.",
        "Approach from the left. It prefers the left.",
    ],
    "note": [
        "Probe returned #probe_state#.",
        "I would like to request a transfer.",
        "Survey team reports feeling 'seen'.",
        "Lovely place. Would not live there.",
        "Recommend we leave it alone and stop thinking about it.",
        "This is the fourth time this planet has been discovered. It keeps getting lost.",
        "The planet appears to be surveying us back.",
        "Several crew members have asked to stay. They seem happy. We are not sure.",
        "Filed in triplicate. One copy has since gone missing.",
        "Took a sample. The sample took one of us.",
        "Nothing to report, which is itself worth reporting.",
    ],
    "probe_state": ["intact but humming", "with a postcard", "two days before it was launched",
                    "covered in a fine blue dust that smells like Sunday",
                    "and politely declined to elaborate", "slightly taller"],
}

ATMOSPHERE = ["nitrogen", "oxygen", "argon", "methane", "helium", "ammonia", "static", "nostalgia",
              "birdsong", "fine glitter", "unidentified", "regret", "pollen", "old radio",
              "petrichor", "chlorine", "warm breath", "lavender"]
STAMPS = ["APPROVED", "DO NOT LAND", "UNDER REVIEW", "CLASSIFIED", "LOST AGAIN",
          "PENDING VIBES CHECK", "HABITABLE (TECHNICALLY)", "QUARANTINED", "FILED", "DENIED"]
SURVEYORS = ["Okonkwo", "Halvorsen", "Petrakis", "Moreau", "Tanaka", "Vale", "Quist", "Abernathy",
             "Lindqvist", "Osei", "Marchetti", "Ferreira", "Nakamura", "Brannigan", "Ilunga"]
SECTORS = ["Outer Drift", "The Long Quiet", "Sector 7G", "Lantern Reach", "Unmapped (Mostly)",
           "The Shelf", "Far Margin", "Hollow Arm", "Sector Nine-ish"]


def expand(rule, rng):
    out = re.sub(r"#(\w+)#", lambda m: expand(rng.choice(G[m.group(1)]), rng), rule)
    return re.sub(r"\b([Aa]) ([aeiou])", r"\1n \2", out)  # a -> an


def roman(n):
    return ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][n - 1]


def make_name(rng):
    onset = ["k", "v", "th", "s", "m", "dr", "z", "l", "qu", "t", "n", "br", "h", "x", "pr", "gl", "or", "a"]
    vowel = ["a", "e", "i", "o", "u", "ae", "io", "au", "y", "ee"]
    coda = ["", "", "", "n", "r", "s", "th", "l", "x", "m"]
    name = "".join(rng.choice(onset) + rng.choice(vowel) + rng.choice(coda) for _ in range(rng.choice([2, 2, 3])))
    suffix = rng.choice([f"-{roman(rng.randint(1, 9))}", f"-{roman(rng.randint(1, 9))}",
                         f" {rng.randint(2, 999)}b", " PRIME", " MINOR", ""])
    return (name + suffix).upper()


# ─── Planet data ──────────────────────────────────────────────────────────────
def survey(date):
    seed = int(hashlib.sha256(f"{SEED_SALT}:{date.isoformat()}".encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    cls = dict(rng.choice(CLASSES))

    p = dict(date=date, rng=rng, anomaly=None)
    p["name"] = make_name(rng)
    p["bulletin"] = (date - FIRST_BULLETIN).days + 1
    p["sector"] = rng.choice(SECTORS)

    roll = rng.random()
    if roll < 0.02:
        p["anomaly"] = "missing"
    elif roll < 0.04:
        p["anomaly"] = "pebble"

    if date.month == 10 and date.day == 31:
        cls, p["anomaly"] = dict(HALLOWEEN), None
    if date.month == 4 and date.day == 1:
        cls, p["anomaly"] = dict(CHEESE), None
    p["cls"] = cls

    p["gravity"] = f"{rng.uniform(0.08, 3.9):.2f} g"
    p["day"] = rng.choice([f"{rng.uniform(3, 300):.1f} h"] * 6 + ["indeterminate", "contested", "just the one"])
    p["temp"] = rng.choice([f"{rng.randint(-240, 460)} °C"] * 5 + ["pleasant", "lukewarm"])
    gases = rng.sample(ATMOSPHERE, 3)
    a = sorted([rng.random() + 0.2 for _ in range(3)], reverse=True)
    pct = [round(x / sum(a) * 100) for x in a]
    pct[0] += 100 - sum(pct)
    p["atmosphere"] = ", ".join(f"{n}% {g}" for n, g in zip(pct, gases))

    p["inhabitants"] = expand("#inhabitants#", rng) + "."
    p["feature"] = expand("#feature#", rng) + "."
    p["advisory"] = expand("#advisory#", rng)
    p["note"] = expand("#note#", rng)
    p["surveyor"] = f"{rng.choice('ABCDEFGHJKLMNOPRSTVW')}. {rng.choice(SURVEYORS)}"
    p["stamp"] = rng.choice(STAMPS)

    # visual parameters
    p["rings"] = rng.random() < cls.get("rings", 0.15)
    p["r"] = rng.uniform(68, 92) if p["rings"] else rng.uniform(95, 132)
    p["moons"] = rng.choice([0, 0, 1, 1, 1, 2, 2, 3])

    if p["anomaly"] == "pebble":
        p["r"], p["rings"], p["moons"] = 9, False, 0
        p["cls"]["name"] = "Pebble (Disputed)"
        p["feature"] = "it is a pebble. The committee maintains it is a planet."
    if p["anomaly"] == "missing":
        p["rings"], p["moons"] = False, 0
        p["cls"]["name"] = "Unconfirmed"
        p["inhabitants"] = "unknown."
        p["feature"] = "it was here yesterday."
        p["stamp"] = "LOST AGAIN"
        p["note"] = "Please check behind the sofa."

    # calendar easter eggs
    if cls is HALLOWEEN or cls["name"] == "Haunted World":
        p["inhabitants"] = expand("#count# ghosts who #habit#", rng) + "."
        p["stamp"] = "DO NOT LAND"
    if date.month == 4 and date.day == 1:
        p["stamp"] = "RETRACTED"
        p["note"] = "Staff are reminded that this bulletin was printed on April 1st."
    if date.month == 1 and date.day == 1:
        p["note"] = "New year. Same void."
    if date.day == 13 and date.weekday() == 4:
        p["advisory"] = "It is Friday the 13th here too. Proceed accordingly."
    return p


# ─── SVG rendering ────────────────────────────────────────────────────────────
INK, MUTED, PAPER, RED = "#2b2a33", "#7a7264", "#efe6d2", "#c8412f"
FONT = "'Courier New', Courier, 'Nimbus Mono PS', 'DejaVu Sans Mono', monospace"
W = 840


def esc(s):
    return html.escape(str(s), quote=True)


def f(x):
    return f"{x:.1f}"


def wave_band(x0, r, yc, h, amp, k, ph1, ph2):
    """A wavy horizontal band, periodic over 2r so it can scroll seamlessly."""
    span, step = 4 * r, 6
    xs = [i * step for i in range(int(span / step) + 2)]
    top = [(x0 + x, yc - h / 2 + amp * math.sin(2 * math.pi * k * x / (2 * r) + ph1)) for x in xs]
    bot = [(x0 + x, yc + h / 2 + amp * math.sin(2 * math.pi * k * x / (2 * r) + ph2)) for x in reversed(xs)]
    pts = top + bot
    return "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts) + " Z"


def render(p):
    rng, cls, r = p["rng"], p["cls"], p["r"]
    tones, glow = cls["tones"], cls["glow"]

    # ── right panel layout first, so we know the card height
    tx, wrap = 442, 47
    out_text, y = [], 52

    def text(x, yy, s, size=13, fill=INK, weight="normal", spacing=0, style="normal"):
        out_text.append(
            f'<text x="{x}" y="{f(yy)}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'letter-spacing="{spacing}" font-style="{style}">{esc(s)}</text>')

    def rule(yy):
        out_text.append(f'<line x1="{tx}" y1="{f(yy)}" x2="{W - 24}" y2="{f(yy)}" stroke="{INK}" stroke-opacity=".35" stroke-dasharray="2 3"/>')

    text(tx, y, "OUTER SURVEY OFFICE", 11, MUTED, "bold", 3); y += 17
    text(tx, y, f"FORM PS-7 · DAILY PLANETARY BULLETIN · No. {p['bulletin']}", 10.5, MUTED); y += 12
    rule(y); y += 36
    name_size = 30 if len(p["name"]) <= 18 else 24
    text(tx, y, p["name"], name_size, INK, "bold", 1); y += 20
    text(tx, y, f"Catalogued {p['date'].strftime('%d %b %Y').upper()} · {p['sector']}", 11.5, MUTED); y += 14
    rule(y); y += 22

    moons_txt = str(p["moons"]) if p["moons"] != 1 else "1"
    if p["moons"] >= 2 and rng.random() < 0.4:
        moons_txt += " (one is shy)"
    grid = [("CLASS", cls["name"]), ("GRAVITY", p["gravity"]),
            ("DAY LENGTH", p["day"]), ("MEAN TEMP", p["temp"]),
            ("MOONS", moons_txt), ("RINGS", "yes" if p["rings"] else "no")]
    for i in range(0, len(grid), 2):
        for j, (k, v) in enumerate(grid[i:i + 2]):
            cx_ = tx + j * 190
            text(cx_, y, k, 9.5, MUTED, "bold", 1.5)
            text(cx_, y + 16, v, 13)
        y += 38

    def para(label, body, style="normal"):
        nonlocal y
        text(tx, y, label, 9.5, MUTED, "bold", 1.5); y += 17
        for line in textwrap.wrap(body, wrap):
            text(tx, y, line, 13, INK, style=style); y += 17
        y += 9

    para("ATMOSPHERE", p["atmosphere"])
    para("INHABITANTS", p["inhabitants"][0].upper() + p["inhabitants"][1:])
    para("NOTABLE FEATURE", p["feature"][0].upper() + p["feature"][1:])
    para("TRAVEL ADVISORY", "⚠ " + p["advisory"])
    para("SURVEYOR'S NOTE", f"“{p['note']}” — Field Surveyor {p['surveyor']}", "italic")

    H = max(460, int(y + 62))

    # ── stamp
    st = p["stamp"]
    sw = len(st) * 11.5 + 28
    sx, sy = W - 40 - sw, H - 70
    stamp = (f'<g transform="rotate({f(rng.uniform(-14, -6))} {f(sx + sw / 2)} {f(sy + 22)})" '
             f'filter="url(#rough)" opacity=".78">'
             f'<rect x="{f(sx)}" y="{f(sy)}" width="{f(sw)}" height="44" rx="5" fill="none" stroke="{RED}" stroke-width="3"/>'
             f'<rect x="{f(sx + 5)}" y="{f(sy + 5)}" width="{f(sw - 10)}" height="34" rx="3" fill="none" stroke="{RED}" stroke-width="1"/>'
             f'<text x="{f(sx + sw / 2)}" y="{f(sy + 29)}" text-anchor="middle" font-size="17" font-weight="bold" '
             f'letter-spacing="2" fill="{RED}">{esc(st)}</text></g>')

    # ── viewport + planet
    vx, vy, vw, vh = 20, 20, 400, H - 40
    cx, cy = vx + vw / 2, vy + vh / 2
    x0 = cx - r
    v = []

    # stars
    for i in range(110):
        sxx, syy = rng.uniform(vx, vx + vw), rng.uniform(vy, vy + vh)
        sr, so = rng.uniform(0.3, 1.3), rng.uniform(0.25, 0.9)
        tw = ""
        if i % 9 == 0:
            tw = (f'<animate attributeName="opacity" values="{so:.2f};.1;{so:.2f}" '
                  f'dur="{rng.uniform(2, 6):.1f}s" begin="-{rng.uniform(0, 6):.1f}s" repeatCount="indefinite"/>')
        v.append(f'<circle cx="{f(sxx)}" cy="{f(syy)}" r="{sr:.2f}" fill="#fff" opacity="{so:.2f}">{tw}</circle>')

    ring_els = []
    if p["rings"]:
        tilt = rng.uniform(-28, 28)
        squash = rng.uniform(0.16, 0.32)
        for _ in range(rng.randint(2, 4)):
            rx = r * rng.uniform(1.3, 1.95)
            ring_els.append(
                f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(rx * squash)}" fill="none" '
                f'stroke="{rng.choice(tones)}" stroke-width="{rng.uniform(2, 9):.1f}" stroke-opacity="{rng.uniform(.45, .85):.2f}"/>')
        rings_back = f'<g transform="rotate({f(tilt)} {f(cx)} {f(cy)})">{"".join(ring_els)}</g>'
        rings_front = (f'<g transform="rotate({f(tilt)} {f(cx)} {f(cy)})" clip-path="url(#ringfront)">{"".join(ring_els)}</g>')
    else:
        rings_back = rings_front = ""

    moons_back, moons_front = [], []
    for _ in range(p["moons"]):
        orx = min(r * rng.uniform(1.3, 1.75), 182)
        ory = orx * rng.uniform(0.12, 0.35)
        mt = rng.uniform(-25, 25)
        mr = rng.uniform(4, 11)
        dur, beg = rng.uniform(16, 45), rng.uniform(0, 45)
        path = (f"M{f(cx + orx)},{f(cy)} A{f(orx)},{f(ory)} 0 0 1 {f(cx - orx)},{f(cy)} "
                f"A{f(orx)},{f(ory)} 0 0 1 {f(cx + orx)},{f(cy)}")
        motion = f'<animateMotion dur="{dur:.1f}s" begin="-{beg:.1f}s" repeatCount="indefinite" path="{path}"/>'
        moon = f'<circle cx="0" cy="0" r="{mr:.1f}" fill="url(#moonshade)">{motion}'
        moons_back.append(f'<g transform="rotate({f(mt)} {f(cx)} {f(cy)})">{moon}</circle></g>')
        moons_front.append(
            f'<g transform="rotate({f(mt)} {f(cx)} {f(cy)})">{moon}'
            f'<animate attributeName="opacity" values="1;0" keyTimes="0;0.5" calcMode="discrete" '
            f'dur="{dur:.1f}s" begin="-{beg:.1f}s" repeatCount="indefinite"/></circle></g>')

    # surface (scrolls left to fake rotation)
    surf = []
    style = cls["style"]
    if style in ("bands", "dunes"):
        n = rng.randint(6, 11)
        for i in range(n):
            yc = cy - r + (i + rng.uniform(0.2, 0.8)) * (2 * r / n)
            h = rng.uniform(0.25, 0.9) * (2 * r / n)
            amp = rng.uniform(1, 7) if style == "bands" else rng.uniform(4, 12)
            k = rng.choice([1, 2, 3]) if style == "bands" else rng.choice([3, 4, 5])
            surf.append(f'<path d="{wave_band(x0, r, yc, h, amp, k, rng.uniform(0, 6.3), rng.uniform(0, 6.3))}" '
                        f'fill="{rng.choice(tones)}" opacity="{rng.uniform(.55, 1):.2f}"/>')
        if style == "bands" and rng.random() < 0.5:  # a great storm
            sxp, syp = rng.uniform(0, 2 * r), cy + rng.uniform(-0.5, 0.5) * r
            srx = r * rng.uniform(0.12, 0.22)
            for off in (-2 * r, 0, 2 * r):
                surf.append(f'<ellipse cx="{f(x0 + sxp + off)}" cy="{f(syp)}" rx="{f(srx)}" ry="{f(srx * .55)}" '
                            f'fill="{tones[1]}" stroke="{tones[-1]}" stroke-width="2" opacity=".9"/>')
    else:
        spots = []
        for _ in range(rng.randint(14, 30)):
            sxp, syp = rng.uniform(0, 2 * r), rng.uniform(cy - r, cy + r)
            sr_ = r * rng.uniform(0.04, 0.2)
            spots.append((sxp, syp, sr_, rng.choice(tones), rng.uniform(.5, .95)))
        for off in (-2 * r, 0, 2 * r):
            for sxp, syp, sr_, col, op in spots:
                X = x0 + sxp + off
                if style == "craters":
                    surf.append(f'<circle cx="{f(X)}" cy="{f(syp)}" r="{f(sr_)}" fill="{tones[1]}" opacity="{op:.2f}"/>'
                                f'<circle cx="{f(X - sr_ * .15)}" cy="{f(syp - sr_ * .15)}" r="{f(sr_ * .8)}" fill="none" '
                                f'stroke="{tones[0]}" stroke-width="{f(max(1, sr_ * .18))}" opacity=".7"/>')
                else:
                    surf.append(f'<ellipse cx="{f(X)}" cy="{f(syp)}" rx="{f(sr_ * 1.5)}" ry="{f(sr_)}" fill="{col}" opacity="{op:.2f}"/>')

    spin = rng.uniform(70, 180)
    surface = (f'<g>{"".join(surf)}<animateTransform attributeName="transform" type="translate" '
               f'from="0 0" to="{f(-2 * r)} 0" dur="{spin:.0f}s" repeatCount="indefinite"/></g>')

    clouds = ""
    if cls.get("clouds"):
        cl = [f'<path d="{wave_band(x0, r, cy - r + rng.uniform(.1, 1.9) * r, rng.uniform(4, 14), rng.uniform(3, 9), rng.choice([2, 3, 4]), rng.uniform(0, 6.3), rng.uniform(0, 6.3))}" fill="#fff" opacity="{rng.uniform(.25, .5):.2f}"/>'
              for _ in range(rng.randint(4, 7))]
        clouds = (f'<g>{"".join(cl)}<animateTransform attributeName="transform" type="translate" '
                  f'from="0 0" to="{f(-2 * r)} 0" dur="{spin * .55:.0f}s" repeatCount="indefinite"/></g>')

    if p["anomaly"] == "missing":
        planet = (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="none" stroke="{glow}" stroke-opacity=".5" stroke-dasharray="6 8"/>'
                  f'<text x="{f(cx)}" y="{f(cy + 5)}" text-anchor="middle" font-size="14" fill="{glow}" letter-spacing="4">NO SIGNAL'
                  f'<animate attributeName="opacity" values="1;.2;1" dur="2s" repeatCount="indefinite"/></text>')
    else:
        planet = (
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r + 5)}" fill="none" stroke="{glow}" stroke-width="10" opacity=".35" filter="url(#blur)"/>'
            f'<g clip-path="url(#pc)">'
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{cls["base"]}"/>'
            f'{surface}{clouds}'
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="url(#shade)"/>'
            f'<rect x="{f(cx - r)}" y="{f(cy - r)}" width="{f(2 * r)}" height="{f(2 * r)}" fill="url(#dots)" mask="url(#shadowmask)" opacity=".5"/>'
            f'</g>'
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="none" stroke="{glow}" stroke-opacity=".45" stroke-width="1.5"/>')

    # viewport chrome: brackets, labels, scanlines
    b, L = 10, 22
    chrome = []
    for (bx, by, dx, dy) in [(vx + b, vy + b, 1, 1), (vx + vw - b, vy + b, -1, 1),
                             (vx + b, vy + vh - b, 1, -1), (vx + vw - b, vy + vh - b, -1, -1)]:
        chrome.append(f'<path d="M{bx},{by + dy * L} L{bx},{by} L{bx + dx * L},{by}" stroke="#e8e1cf" stroke-opacity=".6" fill="none" stroke-width="1.5"/>')
    chrome.append(f'<circle cx="{vx + 26}" cy="{vy + 30}" r="3.5" fill="{RED}"><animate attributeName="opacity" values="1;.15;1" dur="1.6s" repeatCount="indefinite"/></circle>')
    chrome.append(f'<text x="{vx + 36}" y="{vy + 34}" font-size="10" fill="#e8e1cf" fill-opacity=".75" letter-spacing="2">VIEWPORT · LIVE</text>')
    chrome.append(f'<text x="{vx + vw - 26}" y="{vy + vh - 22}" text-anchor="end" font-size="9.5" fill="#e8e1cf" fill-opacity=".55" letter-spacing="1">'
                  f'λ {rng.randint(380, 780)}nm · EXP 1/{rng.choice([30, 60, 125, 250])}s · RA {rng.randint(0, 23):02d}h{rng.randint(0, 59):02d}m</text>')

    defs = f'''<defs>
  <clipPath id="pc"><circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"/></clipPath>
  <clipPath id="vp"><rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="10"/></clipPath>
  <clipPath id="ringfront"><rect x="{f(cx - 400)}" y="{f(cy)}" width="800" height="400"/></clipPath>
  <radialGradient id="shade" cx=".36" cy=".34" r=".78">
    <stop offset="0" stop-color="#fff" stop-opacity=".28"/><stop offset=".42" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".78" stop-color="#000" stop-opacity=".45"/><stop offset="1" stop-color="#000" stop-opacity=".82"/>
  </radialGradient>
  <radialGradient id="shadowgrad" cx=".36" cy=".34" r=".8">
    <stop offset=".45" stop-color="#000"/><stop offset="1" stop-color="#fff"/>
  </radialGradient>
  <mask id="shadowmask"><rect x="{f(cx - r)}" y="{f(cy - r)}" width="{f(2 * r)}" height="{f(2 * r)}" fill="url(#shadowgrad)"/></mask>
  <radialGradient id="moonshade" cx=".35" cy=".35" r=".8">
    <stop offset="0" stop-color="#f4efe4"/><stop offset=".6" stop-color="#b9b2a4"/><stop offset="1" stop-color="#3d3a36"/>
  </radialGradient>
  <radialGradient id="space" cx=".5" cy=".5" r=".75">
    <stop offset="0" stop-color="#1a1f3a"/><stop offset="1" stop-color="#0a0c18"/>
  </radialGradient>
  <pattern id="dots" width="4.5" height="4.5" patternUnits="userSpaceOnUse"><circle cx="2.25" cy="2.25" r="1.1" fill="#000"/></pattern>
  <pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse"><rect width="3" height="1" fill="#fff"/></pattern>
  <filter id="blur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5"/></filter>
  <filter id="rough"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="{rng.randint(1, 99)}"/>
    <feDisplacementMap in="SourceGraphic" scale="3"/></filter>
  <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="3" seed="7"/>
    <feColorMatrix values="0 0 0 0 .35  0 0 0 0 .3  0 0 0 0 .22  0 0 0 .22 0"/></filter>
</defs>'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" aria-label="{esc(alt_text(p))}">
<title>{esc(p["name"])} — Outer Survey Office bulletin No. {p["bulletin"]}</title>
{defs}
<rect width="{W}" height="{H}" rx="14" fill="{PAPER}"/>
<rect width="{W}" height="{H}" rx="14" filter="url(#paper)"/>
<g clip-path="url(#vp)">
  <rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="url(#space)"/>
  {"".join(v)}
  {rings_back}{"".join(moons_back)}{planet}{rings_front}{"".join(moons_front)}
  <rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="url(#scan)" opacity=".035"/>
  {"".join(chrome)}
</g>
<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="10" fill="none" stroke="{INK}" stroke-width="2"/>
{"".join(out_text)}
{stamp}
</svg>
'''


def alt_text(p):
    return (f"Survey bulletin: {p['name']}, class: {p['cls']['name']}. "
            f"Inhabitants: {p['inhabitants']} Advisory: {p['advisory']}")


# ─── README + archive ─────────────────────────────────────────────────────────
START, END = "<!-- PLANET:START -->", "<!-- PLANET:END -->"


def update_readme(readme, p, rel_svg):
    block = f'''{START}
<p align="center">
  <img src="{rel_svg}" width="840" alt="{esc(alt_text(p))}">
</p>
<p align="center"><sub>
  🛰️ The <b>Outer Survey Office</b> catalogues one new world every day at 00:07 UTC ·
  <a href="planets/ARCHIVE.md">past bulletins</a>
</sub></p>
{END}'''
    text = readme.read_text() if readme.exists() else ""
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    readme.write_text(text)


def write_archive(out, log):
    lines = ["# 🛰️ Outer Survey Office: Archive", "",
             "Every world catalogued so far, newest first.", "",
             "| No. | Date | Designation | Class | Status |", "|---:|---|---|---|---|"]
    for e in sorted(log, key=lambda e: e["date"], reverse=True):
        lines.append(f"| {e['bulletin']} | {e['date']} | [**{e['name']}**](archive/{e['date']}.svg) | {e['class']} | `{e['stamp']}` |")
    (out / "ARCHIVE.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date())
    ap.add_argument("--out", type=Path, default=ROOT / "planets")
    ap.add_argument("--readme", type=Path, default=ROOT / "README.md")
    ap.add_argument("--no-readme", action="store_true")
    a = ap.parse_args()

    p = survey(a.date)
    svg = render(p)
    (a.out / "archive").mkdir(parents=True, exist_ok=True)
    (a.out / "archive" / f"{a.date}.svg").write_text(svg)

    log_path = a.out / "log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else []
    log = [e for e in log if e["date"] != str(a.date)]
    log.append(dict(date=str(a.date), bulletin=p["bulletin"], name=p["name"],
                    **{"class": p["cls"]["name"]}, stamp=p["stamp"]))
    log_path.write_text(json.dumps(log, indent=1))
    write_archive(a.out, log)

    if not a.no_readme:
        rel = (a.out / "archive" / f"{a.date}.svg").resolve().relative_to(a.readme.resolve().parent)
        update_readme(a.readme, p, rel.as_posix())
    print(f"No. {p['bulletin']}  {a.date}  {p['name']}  [{p['cls']['name']}]  {p['stamp']}")


if __name__ == "__main__":
    main()
