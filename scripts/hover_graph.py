#!/usr/bin/env python3
"""The contribution graph as README HTML: one image per day, so hovering a day shows its count like on GitHub.

Usage: GITHUB_TOKEN=... python3 scripts/hover_graph.py <login> <assets_dir> <readme> [<readme_tail.md>]
Writes <readme> and, into <assets_dir>, the label and cell images it references (served from the output branch).

GitHub keeps only `title`, `align` and links on README images, and strips inline SVG and image maps, so every day
is its own <img title="...">. The grid sits in a <kbd>: its 10px line-height and `align="top"` images make each
row exactly one cell step tall; in a plain paragraph the 24px line-height would pull the rows apart.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph import FONT, LEVELS, fetch, plural  # noqa: E402

CELL, STEP = 10, 13
PAD = 8           # inside the box, on top of the kbd's own 4px
DAY_LABEL_W = 32 + PAD
MONTH_ROW_H = 18 + PAD
LEGEND_ROW_H = 24 + PAD
LEARN_W, LESS_W, MORE_W = 230, 34, 34

THEMES = {
    "l": {"cells": ["#ebedf0", "#ffee4a", "#ffc501", "#fe9600", "#03001c"], "cell_border": "rgba(31,35,40,0.05)",
          "text": "#1f2328", "muted": "#59636e"},
    "d": {"cells": ["#2a313c", "#631c03", "#bd561d", "#fa7a18", "#fddf68"], "cell_border": "rgba(240,246,252,0.05)",
          "text": "#f0f6fc", "muted": "#9198a1"},
}

LEGEND_TITLES = ["No contributions.", "Low contributions.", "Medium-low contributions.", "Medium-high contributions.",
                 "High contributions."]
LEARN_URL = "https://docs.github.com/articles/why-are-my-contributions-not-showing-up-on-my-profile"


def svg(w, h, body=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}" font-size="12">{body}</svg>\n')


def text(x, y, s, fill, anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{fill}" text-anchor="{anchor}">{s}</text>'


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def day_title(day):
    d = date.fromisoformat(day["date"])
    n = day["contributionCount"]
    what = "No contributions" if n == 0 else plural(n, "contribution")
    return f"{what} on {d.strftime('%B')} {ordinal(d.day)}."


def images(cal, grid_w):
    """name -> svg text, for both themes."""
    weeks = cal["weeks"]
    week_of = {d["date"]: i for i, w in enumerate(weeks) for d in w["contributionDays"]}
    out = {}
    for t, th in THEMES.items():
        for level, colour in enumerate(th["cells"]):
            out[f"{t}c{level}.svg"] = svg(STEP, STEP, f'<rect x="0.5" y="0.5" width="{CELL - 1}" height="{CELL - 1}" '
                                                     f'rx="2" fill="{colour}" stroke="{th["cell_border"]}"/>')
        months = "".join(
            text(DAY_LABEL_W + week_of[m["firstDay"]] * STEP, PAD + 11, m["name"], th["text"])
            for m in cal["months"] if m["totalWeeks"] >= 2 and m["firstDay"] in week_of)
        out[f"{t}months.svg"] = svg(DAY_LABEL_W + grid_w + PAD, MONTH_ROW_H, months)
        for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
            out[f"{t}{name.lower()}.svg"] = svg(DAY_LABEL_W, STEP, text(PAD, 9, name, th["text"]))
        out[f"{t}learn.svg"] = svg(LEARN_W, LEGEND_ROW_H, text(PAD, 20, "Learn how we count contributions", th["muted"]))
        out[f"{t}less.svg"] = svg(LESS_W, LEGEND_ROW_H, text(LESS_W - 4, 20, "Less", th["muted"], "end"))
        out[f"{t}more.svg"] = svg(MORE_W, LEGEND_ROW_H, text(4, 20, "More", th["muted"]))
        # Legend cells sit at the bottom of the legend row, level with the text.
        for level, colour in enumerate(th["cells"]):
            out[f"{t}lc{level}.svg"] = svg(STEP, LEGEND_ROW_H, f'<rect x="0.5" y="{LEGEND_ROW_H - PAD - 12.5}" width="{CELL - 1}" '
                                                             f'height="{CELL - 1}" rx="2" fill="{colour}" stroke="{th["cell_border"]}"/>')
    out["blank.svg"] = svg(STEP, STEP)
    out["blank-label.svg"] = svg(DAY_LABEL_W, STEP)
    out["spacer.svg"] = svg(max(grid_w + DAY_LABEL_W - LEARN_W - LESS_W - 5 * STEP - MORE_W, 1), LEGEND_ROW_H)
    return out


def html(login, cal, base):
    def img(name, title=None, themed=True, href=None):
        t = f' title="{title}"' if title else ""
        if themed:
            tag = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{base}d{name}">'
                   f'<img src="{base}l{name}"{t} align="top"></picture>')
        else:
            tag = f'<img src="{base}{name}"{t} align="top">'
        return f'<a href="{href}"{t}>{tag}</a>' if href else tag

    profile = f"https://github.com/{login}"
    by_row = [[None] * len(cal["weeks"]) for _ in range(7)]
    for i, w in enumerate(cal["weeks"]):
        for d in w["contributionDays"]:
            by_row[d["weekday"]][i] = d

    rows = [img("months.svg")]
    for r, days in enumerate(by_row):
        label = {1: "mon.svg", 3: "wed.svg", 5: "fri.svg"}.get(r)
        cells = [img(label) if label else img("blank-label.svg", themed=False)]
        for d in days:
            if d is None:
                cells.append(img("blank.svg", themed=False))
            else:
                link = f"{profile}?tab=overview&from={d['date']}&to={d['date']}"
                cells.append(img(f"c{LEVELS[d['contributionLevel']]}.svg", day_title(d), href=link))
        rows.append("".join(cells))
    legend = [img("learn.svg", href=LEARN_URL), img("spacer.svg", themed=False), img("less.svg")]
    legend += [img(f"lc{level}.svg", LEGEND_TITLES[level]) for level in range(5)]
    legend.append(img("more.svg"))
    rows.append("".join(legend))
    return (f'{plural(cal["totalContributions"], "contribution")} in the last year\n\n'
            f'<kbd>{"<br>".join(rows)}</kbd>\n')


def main():
    login, assets_dir, readme = sys.argv[1], sys.argv[2], sys.argv[3]
    tail = open(sys.argv[4]).read() if len(sys.argv) > 4 else ""
    base = os.environ.get("ASSET_BASE", f"https://raw.githubusercontent.com/{login}/{login}/output/hover/")
    cal = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(assets_dir, exist_ok=True)
    for name, body in images(cal, len(cal["weeks"]) * STEP).items():
        with open(os.path.join(assets_dir, name), "w") as f:
            f.write(body)
    with open(readme, "w") as f:
        f.write(html(login, cal, base) + ("\n" + tail if tail else ""))
    print(f"{login}: {cal['totalContributions']} contributions, README with {len(cal['weeks'])} weeks")


if __name__ == "__main__":
    main()
