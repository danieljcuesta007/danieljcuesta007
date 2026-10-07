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
import json
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
STATS = 74        # stat columns below the grid
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


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


def render(cal, theme):
    t = THEMES[theme]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    cuts = quartiles([d["contributionCount"] for d in days])
    longest, current, best, active = stats(days)

    gx, gy = PAD + AXIS, PAD + HEAD           # grid origin
    width = gx + len(weeks) * STEP - GAP + PAD
    grid_bottom = gy + 7 * STEP - GAP
    height = grid_bottom + 28 + STATS + PAD

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

    # Stat columns, divided by hairlines.
    sy = grid_bottom + 28
    out.append(f'<line x1="{PAD}" y1="{sy}" x2="{width - PAD}" y2="{sy}" stroke="{t["rule"]}"/>')
    best_day = dt.date.fromisoformat(best["date"]).strftime("%b %-d")
    cols = [
        (f'{cal["totalContributions"]:,}', "contributions"),
        (f"{current}", "day streak, current"),
        (f"{longest}", "day streak, longest"),
        (f"{active}", "active days"),
        (f'{best["contributionCount"]}', f"busiest day, {best_day}"),
    ]
    colw = (width - 2 * PAD) / len(cols)
    for k, (num, label) in enumerate(cols):
        cx = PAD + k * colw
        if k:
            out.append(f'<line x1="{cx:.1f}" y1="{sy + 16}" x2="{cx:.1f}" y2="{sy + STATS - 6}" '
                       f'stroke="{t["rule"]}"/>')
        mid = cx + colw / 2
        out.append(text(f"{mid:.1f}", sy + 42, num, 24, t["accent"], 600, "middle"))
        out.append(text(f"{mid:.1f}", sy + 62, label, 11, anchor="middle"))

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("login", nargs="?",
                    default=os.environ.get("GITHUB_REPOSITORY_OWNER", "danieljcuesta007"))
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    cal = fetch(args.login)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (out / f"contributions-{theme}.svg").write_text(render(cal, theme))
    print(f"{cal['totalContributions']:,} contributions → {out}/contributions-{{light,dark}}.svg")


if __name__ == "__main__":
    main()
