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
EXCLUDED = {x.strip().lower() for x in os.environ.get("EXCLUDE_LANGUAGES", "HTML,CSS,Jupyter Notebook").split(",") if x.strip()}
EXCLUDED_REPOS = {x.strip().lower() for x in os.environ.get("EXCLUDE_REPOS", "htutmyatoo").split(",") if x.strip()}
SHOW = 5
PALETTE = ["#33b8a5", "#65dbb5", "#62a6e8", "#9184e8", "#ecc373", "#7d8da5"]


def get_json(url):
    request = Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-language-chart",
    })
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    totals = Counter()
    count = 0
    page = 1
    while True:
        params = urlencode({"visibility": "all", "affiliation": "owner", "per_page": 100, "page": page})
        repos = get_json(f"https://api.github.com/user/repos?{params}")
        if not repos:
            break
        for repo in repos:
            if repo["owner"]["login"].lower() != USERNAME.lower() or repo["fork"] or repo["archived"]:
                continue
            if repo["name"].lower() in EXCLUDED_REPOS or repo["full_name"].lower() in EXCLUDED_REPOS:
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
        raise RuntimeError("No language data found. Check token permissions and exclusion settings.")
    ranked = totals.most_common()
    visible = ranked[:SHOW]
    if len(ranked) > SHOW:
        visible.append(("Other", sum(n for _, n in ranked[SHOW:])))
    total = sum(totals.values())

    # An accessible, GitHub-compatible static SVG (no JavaScript, fonts or external dependencies).
    width, height, cx, cy, radius, thickness = 700, 280, 155, 137, 87, 24
    circumference = 2 * math.pi * radius
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Code distribution across public and private repositories</title>',
        '<desc id="desc">Language percentages represent GitHub-reported source code bytes, not proficiency or commits.</desc>',
        '<rect width="700" height="280" rx="16" fill="#101b28"/>',
        '<text x="28" y="35" fill="#f4f7fb" font-family="Arial,sans-serif" font-size="18" font-weight="700">Code Distribution</text>',
        '<text x="28" y="54" fill="#9aabba" font-family="Arial,sans-serif" font-size="11">Public + private repositories</text>',
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#2b3948" stroke-width="{thickness}"/>',
    ]
    offset = 0
    for index, (language, size) in enumerate(visible):
        fraction = size / total
        length = circumference * fraction
        svg.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{PALETTE[index]}" stroke-width="{thickness}" '
            f'stroke-dasharray="{length:.4f} {circumference-length:.4f}" stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += length
    svg += [
        f'<text x="{cx}" y="{cy-2}" text-anchor="middle" fill="#f4f7fb" font-size="20" font-weight="700" font-family="Arial,sans-serif">{len(totals)}</text>',
        f'<text x="{cx}" y="{cy+17}" text-anchor="middle" fill="#9aabba" font-size="12" font-family="Arial,sans-serif">languages</text>',
    ]
    for index, (language, size) in enumerate(visible):
        y = 78 + index * 29
        pct = 100 * size / total
        svg += [
            f'<circle cx="345" cy="{y}" r="6" fill="{PALETTE[index]}"/>',
            f'<text x="361" y="{y+5}" fill="#e6edf5" font-size="14" font-family="Arial,sans-serif">{escape(language)}</text>',
            f'<text x="643" y="{y+5}" text-anchor="end" fill="#b8c8d6" font-size="14" font-family="Arial,sans-serif">{pct:.1f}%</text>',
        ]
    svg += [
        '<text x="345" y="263" fill="#7e91a4" font-size="10" font-family="Arial,sans-serif">Share of detected code bytes · excludes selected languages</text>',
        '</svg>',
    ]
    dest = Path("assets/languages.svg")
    dest.parent.mkdir(exist_ok=True, parents=True)
    dest.write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"Generated {dest}: {count} repositories, {len(totals)} languages, {total:,} included bytes")


if __name__ == "__main__":
    main()
