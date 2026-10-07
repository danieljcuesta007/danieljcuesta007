#!/usr/bin/env python3
"""Draw the last year of GitHub contributions as SVGs for the profile README.

GitHub always renders its own contribution graph below the README, so this
script redraws it as an image that can sit anywhere in the README. It writes a
light and a dark variant; the README picks one with <picture>.

Stdlib only. Needs a GitHub token: $GITHUB_TOKEN, else `gh auth token`.

    python3 scripts/contributions.py [login] [--out dist]
"""

import argparse
import datetime as dt
import html
import json
import re
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""

# GitHub's own palettes, so the image reads as the familiar graph.
THEMES = {
    "light": {
        "levels": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "text": "#1f2328", "muted": "#59636e", "accent": "#1a7f37",
        "card": "#ffffff", "border": "#d1d9e0", "rule": "#e6eaef",
    },
    "dark": {
        "levels": ["#151b23", "#033a16", "#196c2e", "#2ea043", "#56d364"],
        "text": "#f0f6fc", "muted": "#9198a1", "accent": "#3fb950",
        "card": "#0d1117", "border": "#3d444d", "rule": "#262c36",
    },
}

CELL, GAP = 11, 3
STEP = CELL + GAP
PAD = 24          # card padding
AXIS = 32         # weekday label column
HEAD = 56         # title + month row above the grid
STATS = 74        # stat columns below the grid (no activity chart)
BAND = 200        # stats grid + activity chart below the grid
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def activity(login):
    """GitHub's own Commits / PRs / Issues / Code review split for the last year.

    The API only breaks down public work by type, so this reads the percentages
    from the fragment the profile page lazy-loads. It isn't a documented API,
    so on any failure the card simply leaves the chart out.
    """
    url = (f"https://github.com/{login}?action=show&controller=profiles"
           f"&tab=contributions&user_id={login}")
    req = urllib.request.Request(url, headers={"X-Requested-With": "XMLHttpRequest",
                                               "User-Agent": "profile-contributions"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = resp.read().decode("utf-8", "replace")
        m = re.search(r'data-percentages="([^"]+)"', page)
        pct = json.loads(html.unescape(m.group(1)))
        return {k: int(pct.get(k, 0)) for k in
                ("Commits", "Pull requests", "Issues", "Code review")}
    except Exception as err:  # noqa: BLE001 - degrade, never fail the run
        print(f"activity overview unavailable ({err}); drawing without it")
        return None


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sys.exit("No token: set GITHUB_TOKEN or log in with `gh auth login`.")


def fetch(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token()}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors") or not body.get("data", {}).get("user"):
        sys.exit(f"GitHub API error: {body.get('errors') or 'user not found'}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(count, cuts):
    if count == 0:
        return 0
    return 1 + sum(count > c for c in cuts)


def quartiles(counts):
    """Bucket edges from the non-zero days, the way GitHub scales its colours."""
    nz = sorted(c for c in counts if c > 0)
    if not nz:
        return [0, 0, 0]
    return [nz[max(int(len(nz) * q) - 1, 0)] for q in (0.25, 0.5, 0.75)]


def stats(days):
    """Longest and current streak, busiest day, and active days."""
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    # Today may not have a contribution yet; don't let that break the streak.
    tail = days[:-1] if days and not days[-1]["contributionCount"] else days
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1
    best = max(days, key=lambda d: d["contributionCount"])
    active = sum(1 for d in days if d["contributionCount"])
    return longest, current, best, active


def radar(out, text, t, cx, cy, arm, pct):
    """GitHub's activity cross: four arms, filled shape at each share."""
    k = arm / 100
    pts = [(cx - pct["Commits"] * k, cy), (cx, cy - pct["Code review"] * k),
           (cx + pct["Issues"] * k, cy), (cx, cy + pct["Pull requests"] * k)]
    for x1, y1, x2, y2 in ((cx - arm, cy, cx + arm, cy), (cx, cy - arm, cx, cy + arm)):
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                   f'stroke="{t["levels"][4]}" stroke-width="2" stroke-linecap="round"/>')
    out.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
               f'" fill="{t["levels"][2]}" fill-opacity="0.45" stroke="{t["levels"][3]}" '
               'stroke-width="1.5" stroke-linejoin="round"/>')
    for x, y in pts:
        if (x, y) != (cx, cy):
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{t["card"]}" '
                       f'stroke="{t["levels"][4]}" stroke-width="2"/>')
    pc = lambda n: f'<tspan font-weight="600" fill="{t["text"]}">{n}%</tspan>'
    out.append(text(cx - arm - 10, cy + 4, f'{pc(pct["Commits"])} Commits', 11, anchor="end"))
    out.append(text(cx + arm + 10, cy + 4, f'{pc(pct["Issues"])} Issues', 11))
    out.append(text(cx, cy - arm - 10, f'{pc(pct["Code review"])} Code review', 11, anchor="middle"))
    out.append(text(cx, cy + arm + 20, f'{pc(pct["Pull requests"])} Pull requests', 11,
                    anchor="middle"))


def render(cal, theme, pct=None):
    t = THEMES[theme]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    cuts = quartiles([d["contributionCount"] for d in days])
    longest, current, best, active = stats(days)

    gx, gy = PAD + AXIS, PAD + HEAD           # grid origin
    width = gx + len(weeks) * STEP - GAP + PAD
    grid_bottom = gy + 7 * STEP - GAP
    height = grid_bottom + 28 + (BAND if pct else STATS) + PAD

    def text(x, y, body, size=10, fill=t["muted"], weight=400, anchor="start"):
        return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                f'fill="{fill}" text-anchor="{anchor}">{body}</text>')

    first = dt.date.fromisoformat(days[0]["date"])
    last = dt.date.fromisoformat(days[-1]["date"])
    span = f'{first.strftime("%b %Y")} – {last.strftime("%b %Y")}'

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}" role="img" '
        f'aria-label="{cal["totalContributions"]:,} contributions in the last year">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="{t["card"]}" stroke="{t["border"]}"/>',
        text(PAD, PAD + 14, "Contributions", 15, t["text"], 600),
        text(width - PAD, PAD + 14, span, 11, anchor="end"),
    ]

    # Month labels above the first column that starts a new month.
    last_month = None
    for i, w in enumerate(weeks):
        d0 = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if d0.month != last_month and i < len(weeks) - 2:
            if last_month is not None or d0.day <= 7:
                out.append(text(gx + i * STEP, gy - 9, d0.strftime("%b")))
            last_month = d0.month

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(text(PAD, gy + row * STEP + CELL - 2, name))

    for i, w in enumerate(weeks):
        for d in w["contributionDays"]:
            n = d["contributionCount"]
            out.append(
                f'<rect x="{gx + i * STEP}" y="{gy + d["weekday"] * STEP}" '
                f'width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{t["levels"][level(n, cuts)]}">'
                f'<title>{n} on {d["date"]}</title></rect>')

    # Less → More legend under the grid, right-aligned like GitHub's.
    ly = grid_bottom + 10
    lx = width - PAD - 5 * STEP - 26
    out.append(text(lx - 6, ly + 9, "Less", anchor="end"))
    for k, c in enumerate(t["levels"]):
        out.append(f'<rect x="{lx + k * STEP}" y="{ly}" width="{CELL}" height="{CELL}" '
                   f'rx="2" fill="{c}"/>')
    out.append(text(lx + 5 * STEP + 2, ly + 9, "More"))

    # Stats, divided by hairlines; with the activity chart beside them when known.
    sy = grid_bottom + 28
    out.append(f'<line x1="{PAD}" y1="{sy}" x2="{width - PAD}" y2="{sy}" stroke="{t["rule"]}"/>')
    best_day = dt.date.fromisoformat(best["date"]).strftime("%b %-d")
    best_week = max(sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks)
    cols = [
        (f'{cal["totalContributions"]:,}', "contributions"),
        (f"{current}", "day streak, current"),
        (f"{longest}", "day streak, longest"),
        (f"{active}", "active days"),
        (f'{best["contributionCount"]}', f"busiest day, {best_day}"),
    ]
    inner = width - 2 * PAD

    def stat(mid, top, num, label):
        out.append(text(f"{mid:.1f}", top + 26, num, 24, t["accent"], 600, "middle"))
        out.append(text(f"{mid:.1f}", top + 46, label, 11, anchor="middle"))

    if not pct:
        colw = inner / len(cols)
        for k, (num, label) in enumerate(cols):
            cx = PAD + k * colw
            if k:
                out.append(f'<line x1="{cx:.1f}" y1="{sy + 16}" x2="{cx:.1f}" '
                           f'y2="{sy + STATS - 6}" stroke="{t["rule"]}"/>')
            stat(cx + colw / 2, sy + 16, num, label)
    else:
        cols.append((f"{best_week}", "busiest week"))
        left = inner * 0.58
        colw, rowh = left / 3, (BAND - 16) / 2
        for k, (num, label) in enumerate(cols):
            r, c = divmod(k, 3)
            top = sy + 8 + r * rowh
            if c:
                x = PAD + c * colw
                out.append(f'<line x1="{x:.1f}" y1="{top + 18:.1f}" x2="{x:.1f}" '
                           f'y2="{top + rowh - 12:.1f}" stroke="{t["rule"]}"/>')
            stat(PAD + c * colw + colw / 2, top + 22, num, label)
        out.append(f'<line x1="{PAD}" y1="{sy + 8 + rowh:.1f}" x2="{PAD + left:.1f}" '
                   f'y2="{sy + 8 + rowh:.1f}" stroke="{t["rule"]}"/>')
        dx = PAD + left
        out.append(f'<line x1="{dx:.1f}" y1="{sy + 16}" x2="{dx:.1f}" y2="{sy + BAND - 8}" '
                   f'stroke="{t["rule"]}"/>')
        out.append(text(dx + 20, sy + 30, "Activity overview", 12, t["text"], 600))
        radar(out, text, t, dx + (inner - left) / 2 + 8, sy + BAND / 2 + 12, 60, pct)

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("login", nargs="?",
                    default=os.environ.get("GITHUB_REPOSITORY_OWNER", "danieljcuesta007"))
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    cal = fetch(args.login)
    pct = activity(args.login)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (out / f"contributions-{theme}.svg").write_text(render(cal, theme, pct))
    print(f"{cal['totalContributions']:,} contributions → {out}/contributions-{{light,dark}}.svg")


if __name__ == "__main__":
    main()
