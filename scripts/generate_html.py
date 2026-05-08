"""Render index.html with a game tab selector and a sortable mod table per game."""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

GAMES = [
    ("baldursgate3", "Baldur's Gate 3"),
    ("clairobscurexpedition33", "Clair Obscur: Expedition 33"),
]


def load(slug: str) -> list[dict]:
    p = DATA_DIR / f"{slug}.json"
    if not p.exists():
        return []
    with p.open() as f:
        return json.load(f)


def fmt_ts(epoch: int | None) -> str:
    if not epoch:
        return ""
    return dt.datetime.utcfromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")


def row_html(slug: str, m: dict) -> str:
    name = html.escape(m.get("name", "(unnamed)"))
    summary = html.escape((m.get("summary") or "")[:200])
    author = html.escape(m.get("author") or m.get("uploaded_by") or "")
    version = html.escape(m.get("version") or "")
    endorsements = m.get("endorsement_count", 0)
    downloads = m.get("mod_downloads", 0)
    updated = fmt_ts(m.get("updated_timestamp") or m.get("latest_file_update"))
    mod_id = m["mod_id"]
    url = f"https://www.nexusmods.com/{slug}/mods/{mod_id}"
    return (
        f'<tr data-updated="{m.get("updated_timestamp") or m.get("latest_file_update") or 0}" '
        f'data-downloads="{downloads}" data-endorsements="{endorsements}">'
        f'<td><a href="{url}" target="_blank" rel="noopener">{name}</a><div class="summary">{summary}</div></td>'
        f"<td>{author}</td><td>{version}</td><td>{updated}</td>"
        f"<td>{downloads:,}</td><td>{endorsements:,}</td></tr>"
    )


def game_section(slug: str, label: str) -> str:
    mods = load(slug)
    mods.sort(key=lambda m: m.get("updated_timestamp") or m.get("latest_file_update") or 0, reverse=True)
    rows = "\n".join(row_html(slug, m) for m in mods)
    return f"""<section class="game" id="game-{slug}" hidden>
<h2>{html.escape(label)} <small>({len(mods):,} tracked mods)</small></h2>
<table class="mods">
<thead><tr>
<th data-sort="name">Mod</th>
<th data-sort="author">Author</th>
<th data-sort="version">Version</th>
<th data-sort="updated">Updated</th>
<th data-sort="downloads">Downloads</th>
<th data-sort="endorsements">Endorsements</th>
</tr></thead>
<tbody>
{rows}
</tbody>
</table>
</section>"""


def main() -> None:
    sections = "\n".join(game_section(slug, label) for slug, label in GAMES)
    tabs = "\n".join(
        f'<button class="tab" data-target="game-{slug}">{html.escape(label)}</button>'
        for slug, label in GAMES
    )
    generated = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Nexus Mod Tracker</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: light dark; }}
body {{ font-family: system-ui, sans-serif; margin: 1.5rem auto; max-width: 1200px; padding: 0 1rem; }}
h1 {{ margin-bottom: 0; }}
.meta {{ color: #888; font-size: 0.9rem; margin-bottom: 1rem; }}
.tabs {{ display: flex; gap: 0.5rem; margin: 1rem 0; }}
.tab {{ padding: 0.5rem 1rem; cursor: pointer; border: 1px solid #888; background: transparent; color: inherit; border-radius: 4px; }}
.tab.active {{ background: #4a90e2; color: white; border-color: #4a90e2; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #444; vertical-align: top; }}
th {{ cursor: pointer; user-select: none; }}
.summary {{ font-size: 0.85rem; color: #999; margin-top: 0.2rem; }}
input[type="search"] {{ padding: 0.4rem; width: 300px; margin-bottom: 0.5rem; }}
</style>
</head>
<body>
<h1>Nexus Mod Tracker</h1>
<div class="meta">Generated {generated}. Data from the Nexus Mods API.</div>
<input type="search" id="filter" placeholder="Filter by name or author...">
<div class="tabs">{tabs}</div>
{sections}
<script>
const tabs = document.querySelectorAll('.tab');
const sections = document.querySelectorAll('section.game');
function activate(id) {{
  tabs.forEach(t => t.classList.toggle('active', t.dataset.target === id));
  sections.forEach(s => s.hidden = s.id !== id);
}}
tabs.forEach(t => t.addEventListener('click', () => activate(t.dataset.target)));
activate(tabs[0].dataset.target);

document.getElementById('filter').addEventListener('input', e => {{
  const q = e.target.value.toLowerCase();
  document.querySelectorAll('section.game tbody tr').forEach(tr => {{
    tr.hidden = q && !tr.textContent.toLowerCase().includes(q);
  }});
}});

document.querySelectorAll('table.mods th').forEach((th, idx) => {{
  th.addEventListener('click', () => {{
    const tbody = th.closest('table').querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const key = th.dataset.sort;
    const dir = th.dataset.dir === 'asc' ? -1 : 1;
    th.dataset.dir = dir === 1 ? 'asc' : 'desc';
    rows.sort((a, b) => {{
      let av, bv;
      if (['updated', 'downloads', 'endorsements'].includes(key)) {{
        av = +a.dataset[key]; bv = +b.dataset[key];
      }} else {{
        av = a.children[idx].textContent; bv = b.children[idx].textContent;
      }}
      return av > bv ? dir : av < bv ? -dir : 0;
    }});
    rows.forEach(r => tbody.appendChild(r));
  }});
}});
</script>
</body>
</html>
"""
    (ROOT / "index.html").write_text(out)
    print(f"Wrote index.html ({len(out):,} bytes)")


if __name__ == "__main__":
    main()
