
import json
import math
import os
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN = os.environ["LANGUAGE_STATS_TOKEN"]
USERNAME = os.environ.get("GITHUB_USERNAME", "htutmyatoo")

EXCLUDED = {
    x.strip().lower()
    for x in os.environ.get(
        "EXCLUDE_LANGUAGES", "HTML,CSS,Jupyter Notebook"
    ).split(",")
    if x.strip()
}

EXCLUDED_REPOS = {
    x.strip().lower()
    for x in os.environ.get(
        "EXCLUDE_REPOS", "htutmyatoo"
    ).split(",")
    if x.strip()
}

SHOW = 5

PALETTE = [
    "#33b8a5",
    "#65dbb5",
    "#62a6e8",
    "#9184e8",
    "#ecc373",
    "#7d8da5",
]

# Card design
WIDTH = 550
HEIGHT = 230
BACKGROUND = "#101b28"
CORNER_RADIUS = 16

# Donut design
CX = 125
CY = 115
RADIUS = 78
THICKNESS = 20

# Legend design
LEGEND_X = 260
LEGEND_Y = 57
LEGEND_SPACING = 29
PERCENT_X = 520


def get_json(url):
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-profile-language-chart",
        },
    )

    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    totals = Counter()
    count = 0
    page = 1

    while True:
        params = urlencode({
            "visibility": "all",
            "affiliation": "owner",
            "per_page": 100,
            "page": page,
        })

        repos = get_json(
            f"https://api.github.com/user/repos?{params}"
        )

        if not repos:
            break

        for repo in repos:
            if (
                repo["owner"]["login"].lower() != USERNAME.lower()
                or repo["fork"]
                or repo["archived"]
            ):
                continue

            if (
                repo["name"].lower() in EXCLUDED_REPOS
                or repo["full_name"].lower() in EXCLUDED_REPOS
            ):
                continue

            languages = get_json(repo["languages_url"])
            count += 1

            for language, size in languages.items():
                if language.lower() not in EXCLUDED:
                    totals[language] += size

        if len(repos) < 100:
            break

        page += 1

    if not totals:
        raise RuntimeError(
            "No language data found. "
            "Check token permissions and exclusion settings."
        )

    ranked = totals.most_common()
    visible = ranked[:SHOW]

    if len(ranked) > SHOW:
        visible.append((
            "Other",
            sum(n for _, n in ranked[SHOW:])
        ))

    total = sum(totals.values())
    circumference = 2 * math.pi * RADIUS

    svg = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{WIDTH}" height="{HEIGHT}" '
            f'viewBox="0 0 {WIDTH} {HEIGHT}" '
            f'role="img" aria-labelledby="title desc">'
        ),
        (
            '<title id="title">'
            'Code distribution across repositories'
            '</title>'
        ),
        (
            '<desc id="desc">'
            'Language percentages represent GitHub-reported '
            'code bytes, not proficiency or commits.'
            '</desc>'
        ),
        (
            f'<rect width="{WIDTH}" height="{HEIGHT}" '
            f'rx="{CORNER_RADIUS}" fill="{BACKGROUND}"/>'
        ),
        (
            f'<circle cx="{CX}" cy="{CY}" r="{RADIUS}" '
            f'fill="none" stroke="#2b3948" '
            f'stroke-width="{THICKNESS}"/>'
        ),
    ]

    # Draw donut segments
    offset = 0

    for index, (language, size) in enumerate(visible):
        fraction = size / total
        length = circumference * fraction

        svg.append(
            f'<circle cx="{CX}" cy="{CY}" '
            f'r="{RADIUS}" fill="none" '
            f'stroke="{PALETTE[index]}" '
            f'stroke-width="{THICKNESS}" '
            f'stroke-dasharray="'
            f'{length:.4f} {circumference - length:.4f}" '
            f'stroke-dashoffset="{-offset:.4f}" '
            f'transform="rotate(-90 {CX} {CY})"/>'
        )

        offset += length

    # Centre label
    svg += [
        (
            f'<text x="{CX}" y="{CY - 2}" '
            f'text-anchor="middle" fill="#f4f7fb" '
            f'font-size="24" font-weight="700" '
            f'font-family="Arial,sans-serif">'
            f'{len(totals)}</text>'
        ),
        (
            f'<text x="{CX}" y="{CY + 17}" '
            f'text-anchor="middle" fill="#9aabba" '
            f'font-size="12" '
            f'font-family="Arial,sans-serif">'
            f'languages</text>'
        ),
    ]

    # Language legend
    for index, (language, size) in enumerate(visible):
        y = LEGEND_Y + index * LEGEND_SPACING
        pct = 100 * size / total

        svg += [
            (
                f'<circle cx="{LEGEND_X}" cy="{y}" '
                f'r="6" fill="{PALETTE[index]}"/>'
            ),
            (
                f'<text x="{LEGEND_X + 16}" y="{y + 5}" '
                f'fill="#e6edf5" font-size="14" '
                f'font-family="Arial,sans-serif">'
                f'{escape(language)}</text>'
            ),
            (
                f'<text x="{PERCENT_X}" y="{y + 5}" '
                f'text-anchor="end" fill="#b8c8d6" '
                f'font-size="14" '
                f'font-family="Arial,sans-serif">'
                f'{pct:.1f}%</text>'
            ),
        ]

    svg.append("</svg>")

    dest = Path("assets/languages.svg")
    dest.parent.mkdir(exist_ok=True, parents=True)
    dest.write_text(
        "\n".join(svg) + "\n",
        encoding="utf-8"
    )

    print(
        f"Generated {dest}: "
        f"{count} repositories, "
        f"{len(totals)} languages, "
        f"{total:,} included bytes"
    )


if __name__ == "__main__":
    main()
