#!/usr/bin/env python3
"""Builds every SVG in assets/ for the profile README, in a dark and a light version.

Standard library only. Edit PROFILE below, then run:

    python3 scripts/build.py

With GITHUB_TOKEN (or GH_TOKEN) set, the activity panel is filled from the
GitHub API. Without it, an existing activity panel is left alone, or a
"waiting for first sync" panel is written if there is none yet.
"""
import datetime
import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
BOOK = ROOT / "data" / "book.json"

# --------------------------------------------------------------------------
# Content. Everything a visitor reads comes from here.
# --------------------------------------------------------------------------
PROFILE = {
    "login": "AkashChavan54",
    "name": "Akash Chavan",
    "intro": [
        "I build the low-latency C++ systems that carry",
        "an order from signal to exchange.",
    ],
    "where": "Quant and infra developer in Mumbai. IIT Kanpur, 2023.",
    # since, order, side, status, state (filled | working | partial | rejected)
    "blotter": [
        ("2023", "B.Tech in Computer Science, IIT Kanpur", "buy", "filled", "filled"),
        ("Jul 2023", "Quant developer, trading infrastructure", "buy", "working", "working"),
        ("daily", "C++17 on Linux, with MySQL underneath", "buy", "working", "working"),
        ("always", "Markets, and trading them", "buy", "partly filled", "partial"),
        ("tonight", "Eight hours of sleep", "buy", "rejected by risk check", "rejected"),
    ],
    # slug (file name), title, description, footer note, colour key
    "focus": [
        ("orders", "Order management",
         "Taking an order from a strategy's decision to a working order "
         "on the exchange, and tracking every state in between.",
         "C++17, state machines", "bid"),
        ("risk", "Pre-trade risk",
         "The checks every order has to clear before it leaves the box: "
         "limits, positions and sanity, all in the hot path.",
         "C++17", "ask"),
        ("routing", "Exchange connectivity",
         "Per-exchange order adapters and routing, including orders "
         "that cross servers and venues.",
         "C++17, Linux networking", "accent"),
        ("threads", "Threading and latency",
         "Deciding which thread owns which step, and keeping the "
         "path from signal to wire short.",
         "C++17, Linux", "bid"),
        ("storage", "Persistence and replication",
         "Every order written down, then consolidated from many "
         "servers into one view.",
         "MySQL, multi-source replication", "ask"),
        ("recovery", "Crash recovery",
         "What the system does after a restart: rebuild state, "
         "reconcile with the exchange, carry on.",
         "C++17, MySQL", "accent"),
    ],
    "pipeline": ["signal", "risk check", "route", "exchange", "fill"],
}

THEMES = {
    "dark": {
        "text": "#E9E4D8", "muted": "#8D96A5", "rule": "#2A313C",
        "bid": "#2FBF9F", "ask": "#F0668A", "accent": "#F4D35E",
        "cell": "#1B222C",
    },
    "light": {
        "text": "#1B2330", "muted": "#5E6875", "rule": "#D5DAE1",
        "bid": "#0E8F78", "ask": "#C93A63", "accent": "#A87B00",
        "cell": "#E9ECF0",
    },
}

SERIF = "'Iowan Old Style','Palatino Linotype',Palatino,'Book Antiqua',Georgia,serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

LANG_KEYS = ["bid", "ask", "accent", "muted", "text"]


def svg(width, height, t, body, css="", label=""):
    base = f"""
    .serif{{font-family:{SERIF}}} .sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}
    .t{{fill:{t['text']}}} .m{{fill:{t['muted']}}}
    .bid{{fill:{t['bid']}}} .ask{{fill:{t['ask']}}} .acc{{fill:{t['accent']}}}
    .rule{{stroke:{t['rule']};stroke-width:1}}
    """
    motion = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{escape(label)}">\n'
        f"<style>{base}{css}{motion}</style>\n{body}\n</svg>\n"
    )


def wrap(text, limit):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > limit:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# Hero: name on the left, a breathing order-book ladder on the right.
# --------------------------------------------------------------------------
def hero(t, book):
    p = PROFILE
    last = book["last"]
    out = [f'<text x="6" y="128" class="serif t" font-size="92" letter-spacing="-1.5">{escape(p["name"])}</text>']
    for i, line in enumerate(p["intro"]):
        out.append(f'<text x="8" y="{200 + i * 38}" class="sans t" font-size="27">{escape(line)}</text>')
    out.append(f'<text x="8" y="304" class="sans m" font-size="21">{escape(p["where"])}</text>')

    # Ladder geometry
    px, row, top = 946, 30, 24          # price column centre, row pitch, first row
    # Prices follow the live book in data/book.json; visitors move it with their orders.
    asks = [(last + 0.05 * k, size) for k, size in zip((5, 4, 3, 2, 1), (182, 150, 112, 78, 44))]
    bids = [(last - 0.05 * k, size) for k, size in zip((1, 2, 3, 4, 5), (50, 86, 120, 152, 186))]
    for i, (price, size) in enumerate(asks):
        y = top + i * row
        out.append(
            f'<rect class="ask bar a" x="{px + 56}" y="{y}" width="{size}" height="20" rx="2" '
            f'style="--s:{0.62 + (i * 7 % 5) * 0.07:.2f};animation-duration:{4.2 + i * 0.9:.1f}s;'
            f'animation-delay:-{i * 1.3:.1f}s"/>'
            f'<text x="{px}" y="{y + 16}" text-anchor="middle" class="mono m" font-size="17">{price:.2f}</text>'
        )
    sy = top + 5 * row + 8
    out.append(f'<line class="rule" x1="700" y1="{sy + 10}" x2="{px - 52}" y2="{sy + 10}"/>')
    out.append(f'<line class="rule" x1="{px + 52}" y1="{sy + 10}" x2="1192" y2="{sy + 10}"/>')
    out.append(
        f'<text x="{px}" y="{sy + 17}" text-anchor="middle" class="mono acc last" '
        f'font-size="20" font-weight="600">{last:.2f}</text>'
    )
    btop = sy + 36
    for i, (price, size) in enumerate(bids):
        y = btop + i * row
        out.append(
            f'<rect class="bid bar b" x="{px - 56 - size}" y="{y}" width="{size}" height="20" rx="2" '
            f'style="--s:{0.66 + (i * 3 % 5) * 0.06:.2f};animation-duration:{5.1 + i * 0.7:.1f}s;'
            f'animation-delay:-{i * 1.7:.1f}s"/>'
            f'<text x="{px}" y="{y + 16}" text-anchor="middle" class="mono m" font-size="17">{price:.2f}</text>'
        )
    css = """
    .bar{transform-box:fill-box;animation:breathe 5s ease-in-out infinite}
    .a{transform-origin:left center} .b{transform-origin:right center}
    @keyframes breathe{0%,100%{transform:scaleX(1)}50%{transform:scaleX(var(--s))}}
    .last{animation:print 3.2s ease-in-out infinite}
    @keyframes print{0%,100%{opacity:1}50%{opacity:.55}}
    """
    label = f'{p["name"]}. {" ".join(p["intro"])} {p["where"]}'
    return svg(1200, 372, t, "\n".join(out), css, label)


# --------------------------------------------------------------------------
# The live market: a tape of visitor orders and a P&L table.
# Orders arrive as GitHub issues; scripts/order.py fills them.
# --------------------------------------------------------------------------
def short(login, limit=18):
    return login if len(login) <= limit else login[: limit - 1] + "…"


def market(t, book):
    last = book["last"]
    out = [
        '<text x="8" y="40" class="serif t" font-size="34">Trade against my book</text>',
        f'<text x="1192" y="38" text-anchor="end" class="mono m" font-size="17">'
        f'last {last:.2f}, {book["orders"]:,} orders so far</text>',
        '<line class="rule" x1="0" y1="60" x2="1200" y2="60"/>',
    ]
    cols = {"time": 8, "trader": 170, "side": 410, "price": 480, "status": 560}
    for name, x in cols.items():
        out.append(f'<text x="{x}" y="90" class="mono m" font-size="16">{name}</text>')
    tape = book["tape"][:6]
    for i, e in enumerate(tape):
        y = 128 + i * 36
        when = datetime.datetime.fromisoformat(e["time"])
        filled = e["status"] == "filled"
        side_cls = {"buy": "bid", "sell": "ask"}.get(e["side"], "m")
        status = "filled" if filled else f'rejected: {e["reason"].split(",")[0]}'
        price = f'{e["price"]:.2f}' if filled else "-"
        fresh = " fresh" if i == 0 else ""
        out.append(
            f'<g class="row{fresh}">'
            f'<text x="{cols["time"]}" y="{y}" class="mono m" font-size="17">{when:%d %b %H:%M}</text>'
            f'<text x="{cols["trader"]}" y="{y}" class="sans t" font-size="19">@{escape(short(e["user"]))}</text>'
            f'<text x="{cols["side"]}" y="{y}" class="mono {side_cls}" font-size="17">{escape(e["side"])}</text>'
            f'<text x="{cols["price"]}" y="{y}" class="mono t" font-size="17">{price}</text>'
            f'<circle class="{"bid" if filled else "ask"}" cx="{cols["status"] + 5}" cy="{y - 6}" r="4.5"/>'
            f'<text x="{cols["status"] + 18}" y="{y}" class="mono {"t" if filled else "m"}" font-size="17">{escape(status)}</text>'
            "</g>"
        )
    if not tape:
        out.append('<text x="8" y="140" class="sans t" font-size="22">No orders yet. Yours can be the first print on the tape.</text>')

    # P&L table, marked to the last price
    lx = 900
    out.append(f'<line class="rule" x1="{lx - 30}" y1="76" x2="{lx - 30}" y2="320"/>')
    out.append(f'<text x="{lx}" y="90" class="mono m" font-size="16">top traders</text>')
    out.append('<text x="1100" y="90" text-anchor="end" class="mono m" font-size="16">lots</text>')
    out.append('<text x="1192" y="90" text-anchor="end" class="mono m" font-size="16">p&amp;l</text>')
    ranked = sorted(
        ((u, tr["pos"], round(tr["cash"] + tr["pos"] * last, 2))
         for u, tr in book["traders"].items() if tr["times"] or tr["pos"] or tr["cash"]),
        key=lambda r: -r[2],
    )[:6]
    for i, (user, pos, pnl) in enumerate(ranked):
        y = 128 + i * 36
        cls = "bid" if pnl > 0 else "ask" if pnl < 0 else "m"
        out.append(
            f'<text x="{lx}" y="{y}" class="sans t" font-size="19">@{escape(short(user, 14))}</text>'
            f'<text x="1100" y="{y}" text-anchor="end" class="mono m" font-size="17">{pos:+d}</text>'
            f'<text x="1192" y="{y}" text-anchor="end" class="mono {cls}" font-size="17">{pnl:+.2f}</text>'
        )
    if not ranked:
        out.append(f'<text x="{lx}" y="128" class="sans m" font-size="19">Nobody has a position yet.</text>')
    out.append(
        '<text x="8" y="356" class="sans m" font-size="18">'
        "Risk checks: 10 orders a day, 5 lots either way, prices between 90 and 110. Times are UTC.</text>"
    )
    css = """
    .fresh{animation:fresh 2.6s ease-out infinite}
    @keyframes fresh{0%{opacity:.35}30%,100%{opacity:1}}
    """
    return svg(1200, 372, t, "\n".join(out), css,
               f'Live tape of visitor orders. Last price {last:.2f}, {book["orders"]} orders so far.')


def button(t, side, book):
    buy = side == "buy"
    colour = t["bid"] if buy else t["ask"]
    price = book["last"] + (0.05 if buy else -0.05)
    title = "Buy 1 lot" if buy else "Sell 1 lot"
    note = f"lifts the offer at {price:.2f}" if buy else f"hits the bid at {price:.2f}"
    body = (
        f'<rect class="btn" x="4" y="4" width="592" height="112" rx="10" fill="{colour}" fill-opacity=".14" '
        f'stroke="{colour}" stroke-width="2"/>'
        f'<text x="300" y="58" text-anchor="middle" class="serif" font-size="36" fill="{colour}">{title}</text>'
        f'<text x="300" y="92" text-anchor="middle" class="mono m" font-size="17">{note}</text>'
    )
    css = """
    .btn{animation:glow 3s ease-in-out infinite}
    @keyframes glow{0%,100%{fill-opacity:.14}50%{fill-opacity:.26}}
    """
    return svg(600, 120, t, body, css, f"{title}: {note}")


# --------------------------------------------------------------------------
# Blotter: the about-me, written as rows on an order blotter.
# --------------------------------------------------------------------------
def blotter(t):
    cols = {"since": 8, "order": 170, "side": 800, "status": 910}
    out = []
    for name, x in cols.items():
        out.append(f'<text x="{x}" y="26" class="mono m" font-size="17">{name}</text>')
    out.append('<line class="rule" x1="0" y1="42" x2="1200" y2="42"/>')
    dot = {"filled": "bid", "working": "acc", "partial": "acc", "rejected": "ask"}
    for i, (since, order, side, status, state) in enumerate(PROFILE["blotter"]):
        y = 80 + i * 50
        pulse = " pulse" if state == "working" else ""
        out.append(
            f'<text x="{cols["since"]}" y="{y}" class="mono m" font-size="19">{escape(since)}</text>'
            f'<text x="{cols["order"]}" y="{y}" class="sans t" font-size="23">{escape(order)}</text>'
            f'<text x="{cols["side"]}" y="{y}" class="mono {"bid" if side == "buy" else "ask"}" font-size="19">{side}</text>'
            f'<circle class="{dot[state]}{pulse}" cx="{cols["status"] + 6}" cy="{y - 7}" r="5"/>'
            f'<text x="{cols["status"] + 22}" y="{y}" class="mono t" font-size="19">{escape(status)}</text>'
        )
        if i < len(PROFILE["blotter"]) - 1:
            out.append(f'<line class="rule" x1="0" y1="{y + 19}" x2="1200" y2="{y + 19}"/>')
    css = """
    .pulse{animation:pulse 2.4s ease-in-out infinite}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
    """
    h = 80 + (len(PROFILE["blotter"]) - 1) * 50 + 24
    label = "Order blotter: " + "; ".join(f"{o}, {s}" for _, o, _, s, _ in PROFILE["blotter"])
    return svg(1200, h, t, "\n".join(out), css, label)


# --------------------------------------------------------------------------
# Focus cards: what the work covers (shown two across in the README).
# --------------------------------------------------------------------------
def card(t, name, desc, note, key):
    out = [
        '<line class="rule" x1="8" y1="14" x2="592" y2="14"/>',
        f'<rect x="8" y="12" width="72" height="5" fill="{t[key]}"/>',
        f'<text x="8" y="66" class="serif t" font-size="34">{escape(name)}</text>',
    ]
    for i, line in enumerate(wrap(desc, 56)[:3]):
        out.append(f'<text x="8" y="{104 + i * 28}" class="sans m" font-size="20">{escape(line)}</text>')
    out.append(f'<text x="8" y="206" class="mono t" font-size="16">{escape(note)}</text>')
    return svg(600, 224, t, "\n".join(out), "", f"{name}: {desc}")


# --------------------------------------------------------------------------
# Activity panel: a year of contributions and a language split.
# --------------------------------------------------------------------------
QUERY = """
query($login:String!){ user(login:$login){
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount } } } }
  repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
    nodes{ languages(first:10, orderBy:{field:SIZE,direction:DESC}){
      edges{ size node{ name } } } } }
} }
"""


def fetch_stats(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": PROFILE["login"]}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-build"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    user = payload["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    langs = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            langs[edge["node"]["name"]] = langs.get(edge["node"]["name"], 0) + edge["size"]
    return {"total": cal["totalContributions"], "weeks": weeks, "languages": langs}


def stats(t, data):
    out = []
    pitch, cell, x0, y0 = 22.3, 17, 8, 74
    weeks = data["weeks"][-53:] if data else [[0] * 7] * 53
    days = [c for w in weeks for c in w]
    peak = max(days) if days else 0

    def level(count):
        if count == 0 or peak == 0:
            return None
        return min(4, 1 + int(3.999 * (count - 1) / max(1, peak - 1))) if peak > 1 else 4

    for wi, week in enumerate(weeks):
        for di, count in enumerate(week):
            lv = level(count)
            fill = t["cell"] if lv is None else t["bid"]
            op = "" if lv is None else f' fill-opacity="{0.25 + 0.25 * (lv - 1):.2f}"'
            out.append(
                f'<rect x="{x0 + wi * pitch:.1f}" y="{y0 + di * pitch:.1f}" width="{cell}" '
                f'height="{cell}" rx="3" fill="{fill}"{op}/>'
            )
    bottom = y0 + 7 * pitch

    if not data:
        out.append('<text x="8" y="40" class="serif t" font-size="32">Activity appears here after the first sync</text>')
        out.append(f'<text x="8" y="{bottom + 34:.0f}" class="mono m" font-size="17">'
                   "The Profile workflow fills this in on its next run.</text>")
        return svg(1200, int(bottom + 52), t, "\n".join(out), "", "Activity panel, waiting for first sync.")

    active = sum(1 for c in days if c)
    streak = best = 0
    for c in days:
        streak = streak + 1 if c else 0
        best = max(best, streak)
    out.append(f'<text x="8" y="40" class="serif t" font-size="32">{data["total"]:,} contributions in the last year</text>')
    out.append(f'<text x="1192" y="38" text-anchor="end" class="mono m" font-size="17">'
               f"{active} active days, longest run {best}</text>")

    langs = sorted(data["languages"].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in langs)
    label = f'{data["total"]} contributions in the last year, {active} active days.'
    if total:
        top = langs[:4]
        rest = total - sum(v for _, v in top)
        if rest:
            top.append(("other", rest))
        by, x = bottom + 22, 8.0
        legend_x = 8
        for i, (name, size) in enumerate(top):
            share = size / total
            w = max(2.0, 1184 * share)
            colour = t[LANG_KEYS[i % len(LANG_KEYS)]]
            out.append(f'<rect x="{x:.1f}" y="{by:.0f}" width="{max(0.5, w - 3):.1f}" height="10" rx="2" fill="{colour}"/>')
            x += w
            text = f"{name} {share * 100:.0f}%"
            out.append(f'<circle cx="{legend_x + 6}" cy="{by + 37:.0f}" r="5" fill="{colour}"/>')
            out.append(f'<text x="{legend_x + 20}" y="{by + 43:.0f}" class="mono t" font-size="17">{escape(text)}</text>')
            legend_x += 20 + int(len(text) * 10.4) + 34
        label += " Languages: " + ", ".join(n for n, _ in top) + "."
        height = by + 62
    else:
        height = bottom + 20
    return svg(1200, int(height), t, "\n".join(out), "", label)


# --------------------------------------------------------------------------
# Footer: the path an order takes, with one pulse travelling along it.
# --------------------------------------------------------------------------
def footer(t):
    stages = PROFILE["pipeline"]
    x0, x1, y = 60, 1140, 30
    step = (x1 - x0) / (len(stages) - 1)
    dur = 7.0
    out = [f'<line class="rule" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>']
    for i, name in enumerate(stages):
        x = x0 + i * step
        delay = dur * 0.8 * i / (len(stages) - 1)
        out.append(
            f'<circle cx="{x:.0f}" cy="{y}" r="6" fill="{t["rule"]}"/>'
            f'<circle class="acc node" cx="{x:.0f}" cy="{y}" r="6" style="animation-delay:{delay:.2f}s"/>'
            f'<text x="{x:.0f}" y="{y + 36}" text-anchor="middle" class="mono m" font-size="17">{escape(name)}</text>'
        )
    out.append(f'<circle class="acc run" cx="{x0}" cy="{y}" r="4"/>')
    css = f"""
    .node{{opacity:0;animation:hit {dur}s linear infinite}}
    @keyframes hit{{0%{{opacity:0}}2%{{opacity:1}}22%{{opacity:0}}100%{{opacity:0}}}}
    .run{{opacity:0;animation:run {dur}s linear infinite}}
    @keyframes run{{0%{{transform:translateX(0);opacity:1}}80%{{transform:translateX({x1 - x0}px);opacity:1}}
      81%,100%{{transform:translateX({x1 - x0}px);opacity:0}}}}
    """
    return svg(1200, 86, t, "\n".join(out), css, "An order's path: " + ", ".join(stages) + ".")


def main():
    ASSETS.mkdir(exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    data = None
    if token:
        try:
            data = fetch_stats(token)
        except Exception as exc:  # keep the last good panel rather than break the page
            print(f"stats fetch failed, keeping existing panel: {exc}", file=sys.stderr)
    book = json.loads(BOOK.read_text())
    for theme, t in THEMES.items():
        files = {
            "hero": hero(t, book), "blotter": blotter(t), "footer": footer(t),
            "market": market(t, book),
            "buy": button(t, "buy", book), "sell": button(t, "sell", book),
        }
        for slug, name, desc, note, key in PROFILE["focus"]:
            files[f"card-{slug}"] = card(t, name, desc, note, key)
        stats_path = ASSETS / f"stats-{theme}.svg"
        if data or not stats_path.exists():
            files["stats"] = stats(t, data)
        for stem, content in files.items():
            (ASSETS / f"{stem}-{theme}.svg").write_text(content, encoding="utf-8")
    print(f"built {len(list(ASSETS.glob('*.svg')))} files in {ASSETS}"
          f" at {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC")


if __name__ == "__main__":
    main()
