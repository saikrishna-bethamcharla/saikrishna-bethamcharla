#!/usr/bin/env python3
"""Builds assets/latest.svg and the link row in README.md from your most recently pushed public repos.

Runs in GitHub Actions with no dependencies. Locally:
  python3 scripts/build_latest.py                     (uses the GitHub API)
  FIXTURE=repos.json python3 scripts/build_latest.py  (uses a saved API response)
"""
import datetime as dt
import html
import json
import os
import re
import urllib.request

USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "saikrishna-bethamcharla"
LIMIT = int(os.environ.get("LIMIT", "5"))
# repos to hide, comma separated (the profile repo itself is always hidden)
EXCLUDE = {USER.lower()} | {x.strip().lower() for x in os.environ.get("EXCLUDE", "").split(",") if x.strip()}
ROOT = os.environ.get("ROOT", ".")
NOW = dt.datetime.fromisoformat(os.environ["NOW"].replace("Z", "+00:00")) if os.environ.get("NOW") else dt.datetime.now(dt.timezone.utc)

LANG = {"TypeScript": "#3178C6", "JavaScript": "#F1E05A", "HTML": "#E34C26", "CSS": "#9B7BFF",
        "Python": "#3572A5", "Java": "#B07219", "Go": "#00ADD8", "Shell": "#89E051"}
ACC, INK, PANEL, LINE, TXT, MUTE = "#7AB8FF", "#060812", "#0B1020", "#2F3A6B", "#E8F1FF", "#8E9BC4"


def fetch():
    if os.environ.get("FIXTURE"):
        return json.load(open(os.environ["FIXTURE"]))
    req = urllib.request.Request(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed&type=owner",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "latest-repos-card"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    return json.load(urllib.request.urlopen(req, timeout=30))


def ago(when):
    d = (NOW - when).total_seconds() / 86400
    if d < 1:
        return "today"
    if d < 2:
        return "yesterday"
    if d < 14:
        return f"{int(d)} days ago"
    if d < 60:
        return f"{int(d // 7)} weeks ago"
    return f"{int(d // 30)} months ago"


repos = [r for r in fetch() if not r.get("fork") and not r.get("archived") and r["name"].lower() not in EXCLUDE]
repos.sort(key=lambda r: r["pushed_at"], reverse=True)
repos = repos[:LIMIT]

rows, W, H = "", 640, 76 + 46 * len(repos)
css = (".sans{font-family:'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif}"
       ".mono{font-family:'JetBrains Mono','SF Mono','Fira Code',Consolas,monospace}"
       ".row{opacity:0;animation:row %ss linear infinite}.live{animation:pulse 1.8s ease-in-out infinite}"
       "@keyframes row{0%%,%s%%{opacity:1}%s%%,100%%{opacity:0}}@keyframes pulse{0%%,100%%{opacity:1}50%%{opacity:.25}}"
       "@media (prefers-reduced-motion: reduce){*{animation:none!important}}")
cycle = 3.0 * max(len(repos), 1)
span = 100 / max(len(repos), 1)
css = css % (cycle, f"{span - 1:.1f}", f"{span:.1f}")

for i, r in enumerate(repos):
    y = 64 + i * 46
    when = dt.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
    days = max((NOW - when).total_seconds() / 86400, 0)
    bar = 584 * max(0.1, 1 - days / 45)
    col = LANG.get(r.get("language") or "", MUTE)
    rows += f'<rect class="row" style="animation-delay:{i*3.0:.1f}s" x="12" y="{y-8}" width="616" height="40" rx="8" fill="{ACC}" fill-opacity=".08"/>'
    rows += f'<text class="sans" x="28" y="{y+14}" font-size="17" font-weight="600" fill="{TXT}">{html.escape(r["name"])}</text>'
    rows += f'<circle cx="{300}" cy="{y+9}" r="4" fill="{col}"/>'
    rows += f'<text class="mono" x="312" y="{y+13}" font-size="12" fill="{MUTE}">{html.escape(r.get("language") or "n/a")}</text>'
    rows += f'<text class="mono" x="612" y="{y+13}" font-size="12" fill="{MUTE}" text-anchor="end">{ago(when)}</text>'
    rows += f'<rect x="28" y="{y+24}" width="584" height="2" rx="1" fill="#1A2140"/><rect x="28" y="{y+24}" width="{bar:.0f}" height="2" rx="1" fill="{ACC}" fill-opacity=".8"/>'

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Recently pushed repositories">
<style>{css}</style>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{PANEL}" stroke="#2A3358"/>
<circle class="live" cx="30" cy="30" r="4" fill="#3DD6B0"/>
<text class="mono" x="44" y="34" font-size="13" fill="{MUTE}">recently pushed</text>
<text class="mono" x="612" y="34" font-size="12" fill="#6F7BA8" text-anchor="end">synced {NOW.strftime("%Y-%m-%d")}</text>
<line x1="12" y1="48" x2="628" y2="48" stroke="{LINE}" stroke-width="1"/>
{rows}
</svg>
'''
os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
open(os.path.join(ROOT, "assets", "latest.svg"), "w", encoding="utf-8").write(svg)

links = " | ".join(f'<a href="{html.escape(r["html_url"])}">{html.escape(r["name"])}</a>' for r in repos)
block = f"<!-- LATEST:START -->\n<p>Open: {links}</p>\n<!-- LATEST:END -->"
path = os.path.join(ROOT, "README.md")
if os.path.exists(path):
    s = open(path, encoding="utf-8").read()
    s2 = re.sub(r"<!-- LATEST:START -->.*?<!-- LATEST:END -->", lambda m: block, s, flags=re.S)
    open(path, "w", encoding="utf-8").write(s2)
print("latest:", [r["name"] for r in repos])
