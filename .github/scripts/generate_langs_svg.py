#!/usr/bin/env python3
"""
Generate a self-hosted langs.svg from real GitHub language data.
Scans all public + private repos the token has access to.
Excludes repos and languages defined in env vars.
"""
import os
import requests

GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]
USERNAME        = os.environ.get("GITHUB_USERNAME", "isatyam18")
EXCLUDE_REPOS   = {r.strip() for r in os.environ.get("EXCLUDE_REPOS", "").split(",") if r.strip()}
EXCLUDE_LANGS   = {l.strip().lower() for l in os.environ.get("EXCLUDE_LANGS", "HTML,CSS,Jupyter Notebook").split(",") if l.strip()}

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

LANG_COLORS = {
    "python":     "#3572A5",
    "javascript": "#f1e05a",
    "typescript": "#3178c6",
    "c":          "#555555",
    "c++":        "#f34b7d",
    "java":       "#b07219",
    "go":         "#00ADD8",
    "rust":       "#dea584",
    "shell":      "#89e051",
    "r":          "#198ce7",
    "kotlin":     "#A97BFF",
    "swift":      "#F05138",
    "ruby":       "#701516",
    "scala":      "#c22d40",
    "dart":       "#00B4AB",
    "lua":        "#000080",
    "matlab":     "#e16737",
    "verilog":    "#b2b7f8",
    "jupyter notebook": "#DA5B0B",
}
DEFAULT_COLOR = "#aaaaaa"


def get_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        resp = requests.get(
            "https://api.github.com/user/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "affiliation": "owner"},
        )
        data = resp.json()
        if not data or "message" in data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def get_langs(owner: str, repo: str) -> dict:
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/languages",
        headers=HEADERS,
    )
    if resp.status_code != 200:
        return {}
    return resp.json()


def build_svg(lang_totals: dict) -> str:
    filtered = {k: v for k, v in lang_totals.items() if k.lower() not in EXCLUDE_LANGS and v > 0}
    if not filtered:
        filtered = {"Python": 1}

    total = sum(filtered.values())
    sorted_langs = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    top_langs = sorted_langs[:8]   # show up to 8 languages

    # --- Dimensions ---
    W = 300
    pad_x = 25
    bar_y = 8
    bar_h = 8
    row_h = 22
    items_per_row = 2
    n_rows = (len(top_langs) + items_per_row - 1) // items_per_row
    height = 45 + bar_h + 10 + row_h * n_rows + 15

    # --- Progress bar segments ---
    bar_width = W - 2 * pad_x
    bar_parts = ""
    cursor = 0.0
    for lang, bytes_val in top_langs:
        pct = bytes_val / total
        seg_w = round(bar_width * pct, 2)
        color = LANG_COLORS.get(lang.lower(), DEFAULT_COLOR)
        bar_parts += (
            f'<rect mask="url(#rect-mask)" x="{round(cursor, 2)}" y="0" '
            f'width="{seg_w}" height="{bar_h}" fill="{color}" />\n        '
        )
        cursor += seg_w

    # --- Legend items ---
    legend_items = ""
    for i, (lang, bytes_val) in enumerate(top_langs):
        col = i % items_per_row
        row = i // items_per_row
        x = col * ((W - 2 * pad_x) // items_per_row)
        y = row * row_h
        pct = bytes_val / total * 100
        color = LANG_COLORS.get(lang.lower(), DEFAULT_COLOR)
        legend_items += (
            f'<g transform="translate({x}, {y})">'
            f'<circle cx="5" cy="6" r="5" fill="{color}" />'
            f'<text x="15" y="10" class="lang-name">{lang} {pct:.2f}%</text>'
            f'</g>\n      '
        )

    svg = f"""<svg width="{W}" height="{height}" viewBox="0 0 {W} {height}"
  fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #70a5fd; }}
    .lang-name {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #38bdae; }}
  </style>

  <!-- Background -->
  <rect x="0.5" y="0.5" rx="4.5" width="{W-1}" height="{height-1}"
        fill="#1a1b27" stroke="#e4e2e2" stroke-opacity="0" />

  <!-- Title -->
  <g transform="translate({pad_x}, 28)">
    <text class="header">Most Used Languages</text>
  </g>

  <!-- Bar -->
  <g transform="translate({pad_x}, 45)">
    <mask id="rect-mask">
      <rect x="0" y="0" width="{bar_width}" height="{bar_h}" fill="white" rx="5"/>
    </mask>
    {bar_parts}
  </g>

  <!-- Legend -->
  <g transform="translate({pad_x}, {45 + bar_h + 14})">
    {legend_items}
  </g>
</svg>"""
    return svg


def main():
    print(f"Fetching repos for {USERNAME}…")
    repos = get_repos()
    print(f"Found {len(repos)} repos")

    lang_totals: dict[str, int] = {}
    for repo in repos:
        name = repo.get("name", "")
        if name in EXCLUDE_REPOS:
            print(f"  Skipping excluded repo: {name}")
            continue
        if repo.get("fork"):
            print(f"  Skipping fork: {name}")
            continue
        langs = get_langs(USERNAME, name)
        for lang, count in langs.items():
            if lang.lower() not in EXCLUDE_LANGS:
                lang_totals[lang] = lang_totals.get(lang, 0) + count
        if langs:
            print(f"  {name}: {list(langs.keys())}")

    print(f"\nTotal language bytes: { {k: v for k, v in sorted(lang_totals.items(), key=lambda x: -x[1])} }")

    svg = build_svg(lang_totals)
    out_path = os.path.join(os.path.dirname(__file__), "..", "..", "langs.svg")
    out_path = os.path.normpath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"\n✅ langs.svg written to {out_path}")


if __name__ == "__main__":
    main()
