#!/usr/bin/env python3
"""Draw the GitHub contribution graph, laid out like the profile one, in GitHub's Halloween colours.

Usage: GITHUB_TOKEN=... python3 scripts/graph.py <login> <out_dir> [<snake_dir>]
Writes <out_dir>/halloween-graph.svg (light) and <out_dir>/halloween-graph-dark.svg (dark).
With <snake_dir> holding Platane/snk SVGs of the same names, the snake and its grid replace the static cells.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        months { name firstDay totalWeeks }
        weeks { contributionDays { date weekday contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

THEMES = {
    "halloween-graph.svg": {
        "cells": ["#ebedf0", "#ffee4a", "#ffc501", "#fe9600", "#03001c"],
        "cell_border": "rgba(31,35,40,0.05)",
        "text": "#1f2328",
        "muted": "#59636e",
        "border": "#d1d9e0",
    },
    "halloween-graph-dark.svg": {
        "cells": ["#151b23", "#631c03", "#bd561d", "#fa7a18", "#fddf68"],
        "cell_border": "rgba(240,246,252,0.05)",
        "text": "#f0f6fc",
        "muted": "#9198a1",
        "border": "#3d444d",
    },
}

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
CELL, GAP = 10, 3
STEP = CELL + GAP
PAD = 16          # inside the bordered box
DAY_LABEL_W = 32  # room for Mon / Wed / Fri
HEADER_H = 32     # "N contributions in the last year"
MONTH_H = 20
SNK_STEP, SNK_OFFSET = 16, 2  # snk draws cell i at 2 + 16 * i


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise SystemExit(f"GraphQL errors: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def tooltip(day):
    d = date.fromisoformat(day["date"])
    n = day["contributionCount"]
    what = "No contributions" if n == 0 else plural(n, "contribution")
    return f"{what} on {d.strftime('%B')} {d.day}"


def snake_layer(svg, x, y):
    """snk's grid and snake, scaled so its cells land exactly on ours; its progress bar is dropped."""
    body = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", svg, flags=re.S)
    body = re.sub(r"<desc>.*?</desc>|<rect class=\"u[^>]*/>", "", body, flags=re.S)
    k = STEP / SNK_STEP
    return f'<g transform="translate({x - SNK_OFFSET * k} {y - SNK_OFFSET * k}) scale({k})">{body}</g>'


def render(cal, theme, snake=None):
    weeks = cal["weeks"]
    grid_x = PAD + DAY_LABEL_W
    grid_y = HEADER_H + PAD + MONTH_H
    grid_w = len(weeks) * STEP - GAP
    box_w = DAY_LABEL_W + grid_w + 2 * PAD
    legend_y = grid_y + 7 * STEP - GAP + 14
    box_h = legend_y + 10 + PAD - HEADER_H
    width, height = box_w + 2, HEADER_H + box_h + 1

    week_of = {d["date"]: i for i, w in enumerate(weeks) for d in w["contributionDays"]}
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{FONT}">',
        f'<text x="1" y="18" font-size="16" fill="{theme["text"]}">{plural(cal["totalContributions"], "contribution")} in the last year</text>',
        f'<rect x="0.5" y="{HEADER_H + 0.5}" width="{box_w}" height="{box_h}" rx="6" fill="none" stroke="{theme["border"]}"/>',
    ]

    # Month labels sit over the week holding the 1st; GitHub drops a month with under two weeks on the graph.
    for m in cal["months"]:
        if m["totalWeeks"] < 2 or m["firstDay"] not in week_of:
            continue
        x = grid_x + week_of[m["firstDay"]] * STEP
        out.append(f'<text x="{x}" y="{grid_y - 7}" font-size="12" fill="{theme["text"]}">{m["name"]}</text>')

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = grid_y + row * STEP + CELL - 1
        out.append(f'<text x="{PAD}" y="{y}" font-size="12" fill="{theme["text"]}">{name}</text>')

    def cell(x, y, level, title=None):
        t = f"<title>{title}</title>" if title else ""
        return (f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{theme["cells"][level]}" '
                f'stroke="{theme["cell_border"]}">{t}</rect>')

    if snake:
        out.append(snake_layer(snake, grid_x, grid_y))
    else:
        for i, w in enumerate(weeks):
            for d in w["contributionDays"]:
                out.append(cell(grid_x + i * STEP, grid_y + d["weekday"] * STEP, LEVELS[d["contributionLevel"]], tooltip(d)))

    out.append(f'<text x="{PAD}" y="{legend_y + 9}" font-size="12" fill="{theme["muted"]}">Learn how we count contributions</text>')
    right = grid_x + grid_w
    lx = right - 30 - 5 * STEP
    out.append(f'<text x="{lx - 4}" y="{legend_y + 9}" font-size="12" text-anchor="end" fill="{theme["muted"]}">Less</text>')
    for level in range(5):
        out.append(cell(lx + level * STEP, legend_y, level))
    out.append(f'<text x="{right}" y="{legend_y + 9}" font-size="12" text-anchor="end" fill="{theme["muted"]}">More</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    login, out_dir = sys.argv[1], sys.argv[2]
    snake_dir = sys.argv[3] if len(sys.argv) > 3 else None
    cal = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(out_dir, exist_ok=True)
    for name, theme in THEMES.items():
        snake = None
        if snake_dir and os.path.exists(os.path.join(snake_dir, name)):
            snake = open(os.path.join(snake_dir, name)).read()
        with open(os.path.join(out_dir, name), "w") as f:
            f.write(render(cal, theme, snake))
    print(f"{login}: {cal['totalContributions']} contributions, {len(cal['weeks'])} weeks")


if __name__ == "__main__":
    main()
