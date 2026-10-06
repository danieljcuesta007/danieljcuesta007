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
        "text": "#1f2328",
        "muted": "#59636e",
    },
    "dark": {
        "levels": ["#151b23", "#033a16", "#196c2e", "#2ea043", "#56d364"],
        "text": "#f0f6fc",
        "muted": "#9198a1",
    },
}

CELL, GAP = 11, 3
STEP = CELL + GAP
LEFT, TOP = 32, 44  # room for weekday labels and the title + month row
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
    return [nz[int(len(nz) * q) - 1 if int(len(nz) * q) else 0] for q in (0.25, 0.5, 0.75)]


def render(cal, theme):
    t = THEMES[theme]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    cuts = quartiles([d["contributionCount"] for d in days])
    width = LEFT + len(weeks) * STEP
    height = TOP + 7 * STEP + 22

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}" role="img" '
        f'aria-label="{cal["totalContributions"]:,} contributions in the last year">',
        f'<text x="0" y="14" font-size="14" font-weight="600" fill="{t["text"]}">'
        f'{cal["totalContributions"]:,} contributions in the last year</text>',
    ]

    # Month labels above the first column that starts a new month.
    last_month = None
    for i, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last_month and i < len(weeks) - 2:
            if last_month is not None or first.day <= 7:
                out.append(f'<text x="{LEFT + i * STEP}" y="{TOP - 8}" font-size="10" '
                           f'fill="{t["muted"]}">{first.strftime("%b")}</text>')
            last_month = first.month

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="0" y="{TOP + row * STEP + CELL - 2}" font-size="10" '
                   f'fill="{t["muted"]}">{name}</text>')

    for i, w in enumerate(weeks):
        for d in w["contributionDays"]:
            n = d["contributionCount"]
            out.append(
                f'<rect x="{LEFT + i * STEP}" y="{TOP + d["weekday"] * STEP}" '
                f'width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{t["levels"][level(n, cuts)]}">'
                f'<title>{n} on {d["date"]}</title></rect>')

    # Less → More legend, bottom right, like GitHub's.
    ly = TOP + 7 * STEP + 8
    lx = width - 5 * STEP - 30
    out.append(f'<text x="{lx - 28}" y="{ly + 9}" font-size="10" fill="{t["muted"]}">Less</text>')
    for k, c in enumerate(t["levels"]):
        out.append(f'<rect x="{lx + k * STEP}" y="{ly}" width="{CELL}" height="{CELL}" '
                   f'rx="2" fill="{c}"/>')
    out.append(f'<text x="{lx + 5 * STEP + 4}" y="{ly + 9}" font-size="10" '
               f'fill="{t["muted"]}">More</text>')
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
