"""Generate per-game HTML pages styled to match the bg3-mod-tracker UI.

Layout: game switcher inside the header bar; a single controls row with
date nav + Today button + platform filter + sort.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .changelog_data import Mod, ModUpdate, get_mods
from .components import date_section, empty_state, html_document, tabs_script
from .components.modal import MODAL_SCRIPT, info_button, info_modal
from .components.tabs import mod_card

ROOT = Path(__file__).resolve().parent.parent

GAMES = [
    {
        "slug": "baldursgate3",
        "label": "Baldur's Gate 3",
        "filename": "index.html",
        "title": "BG3 Nexus Mod Tracker",
        "logo": "assets/img/logo.png",
        "bg_kind": "svg",
        "bg_url": "assets/img/d20.svg",
        "bg_tint_top": "rgba(201, 162, 39, 0.08)",
        "bg_tint_bottom": "rgba(139, 105, 20, 0.05)",
    },
    {
        "slug": "clairobscurexpedition33",
        "label": "Expedition 33",
        "filename": "expedition33.html",
        "title": "Expedition 33 Nexus Mod Tracker",
        "logo": "assets/img/exp33-logo.svg",
        "bg_kind": "tile",
        "bg_url": "assets/img/exp33-bg.png",
        "bg_tile_size": 220,
        "bg_opacity": 0.05,
        "bg_tint_top": "rgba(232, 193, 77, 0.07)",
        "bg_tint_bottom": "rgba(120, 70, 90, 0.06)",
    },
]

CUTOFF_DAYS = 30


# ---------- changelog content ------------------------------------------------


def _flatten(mods: dict[int, Mod]) -> list[tuple[Mod, ModUpdate]]:
    return [(m, u) for m in mods.values() for u in m.updates]


def _cards(updates: list[tuple[Mod, ModUpdate]]) -> str:
    if not updates:
        return empty_state("No mods in this category")
    return "\n".join(
        mod_card(
            title=m.name,
            summary=m.summary or "",
            image_url=m.logo_url,
            profile_url=m.profile_url,
            platforms=m.platforms,
            author=m.author,
            date_updated=m.date_updated,
            popularity_rank=m.popularity_rank,
            downloads_today=m.downloads_today,
            subscribers=m.subscribers,
        )
        for m, _ in updates
    )


def _changelog_sections(mods: dict[int, Mod]) -> str:
    if not mods:
        return empty_state("No mods found")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)).date()
    by_date: dict[date, dict[str, list[tuple[Mod, ModUpdate]]]] = {}
    for m, u in _flatten(mods):
        d = u.timestamp.date()
        if d < cutoff:
            continue
        by_date.setdefault(d, {"added": [], "updated": []})[u.update_type].append((m, u))

    if not by_date:
        return empty_state("No mods updated in the last 30 days")

    sections: list[str] = []
    for i, day in enumerate(sorted(by_date.keys(), reverse=True)):
        new_mods = by_date[day]["added"]
        upd_mods = by_date[day]["updated"]
        sections.append(
            date_section(
                date_str=day.strftime("%B %d, %Y"),
                new_count=len(new_mods),
                updated_count=len(upd_mods),
                content_new=_cards(new_mods) if new_mods else empty_state("No new mods"),
                content_updated=_cards(upd_mods) if upd_mods else empty_state("No updates"),
                is_first=(i == 0),
            )
        )
    sections.append(tabs_script())
    return "\n".join(sections)


# ---------- header + controls -----------------------------------------------


def _header(game: dict) -> str:
    chips = []
    for g in GAMES:
        is_active = g["slug"] == game["slug"]
        cls = "game-chip active" if is_active else "game-chip"
        onclick = "" if is_active else f"onclick=\"location.href='{g['filename']}'\""
        chips.append(
            f'<button class="{cls}" type="button" {onclick} '
            f'aria-selected="{"true" if is_active else "false"}">{g["label"]}</button>'
        )
    game_tabs = '<div class="header-game-tabs" role="tablist">' + "".join(chips) + "</div>"

    return f"""<header class="app-header">
    <div class="header-content">
        <img src="{game['logo']}" alt="" class="header-logo">
        <span class="header-title">{game['title']}</span>
        {game_tabs}
        <div class="header-stat">
            <span class="header-stat-value" id="total-mods">--</span>
            <span>mods</span>
        </div>
        {info_button()}
    </div>
</header>
<div class="toast" id="toast" aria-live="polite"></div>"""


def _controls_row() -> str:
    return """<div class="controls-row">
    <div class="date-nav-inline">
        <button class="date-nav-btn prev" onclick="prevDate()" aria-label="Previous date">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 12L6 8l4-4"/></svg>
        </button>
        <div class="date-nav-pill"><span class="date-nav-current">Loading...</span></div>
        <button class="date-nav-btn next" onclick="nextDate()" aria-label="Next date">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 12l4-4-4-4"/></svg>
        </button>
        <span class="date-nav-badge" style="display:none"></span>
    </div>
    <button class="today-btn" type="button" onclick="goToToday()">Today</button>
    <span class="ctrl-sep" aria-hidden="true"></span>
    <div class="platform-filter inline" role="tablist" aria-label="Filter by platform">
        <button class="platform-chip active" data-filter="all" onclick="setPlatformFilter('all')" role="tab" aria-selected="true">All</button>
        <button class="platform-chip" data-filter="pc" onclick="setPlatformFilter('pc')" role="tab" aria-selected="false">PC</button>
        <button class="platform-chip" data-filter="console" onclick="setPlatformFilter('console')" role="tab" aria-selected="false">Console</button>
    </div>
    <span class="ctrl-sep" aria-hidden="true"></span>
    <div class="sort-bar inline">
        <label class="sort-label" for="sort-select">Sort</label>
        <select id="sort-select" class="sort-select" onchange="setSortMode(this.value)">
            <option value="default">Default</option>
            <option value="recent">Most recently updated</option>
            <option value="popular">Most popular</option>
            <option value="downloads">Downloads today</option>
            <option value="subscribers">Most subscribed</option>
            <option value="name-asc">Name A–Z</option>
            <option value="name-desc">Name Z–A</option>
            <option value="author-asc">Author A–Z</option>
        </select>
    </div>
</div>"""


# ---------- per-page CSS overrides ------------------------------------------


CUSTOM_CSS = """
<style>
/* Constrain header-logo height so BG3's wide PNG and Exp33's square SVG
   don't change the header's vertical rhythm between pages. */
.header-logo {
    height: 44px;
    width: auto;
    max-width: 120px;
    object-fit: contain;
}

/* Game switcher — segmented control, mirrors the New/Updated tab-group. */
.header-game-tabs {
    display: inline-flex;
    align-items: center;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 9999px;
    box-shadow: var(--shadow-sm);
    padding: 0.25rem;
    gap: 0.25rem;
    margin-left: 0.5rem;
    pointer-events: auto;
}
.game-chip {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border: none;
    background: transparent;
    border-radius: 9999px;
    cursor: pointer;
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-secondary);
    transition: all 0.2s ease;
}
.game-chip:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}
.game-chip.active {
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-secondary));
    color: var(--bg-primary);
    cursor: default;
}

/* Vertical separator inside the controls row. */
.ctrl-sep {
    display: inline-block;
    width: 1px;
    height: 22px;
    background: linear-gradient(180deg, transparent, var(--border-color), transparent);
    margin: 0 0.25rem;
}

/* Single horizontal controls row replacing the stacked date-nav / platform / sort. */
.controls-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.85rem;
    padding: 0.75rem 1rem;
    flex-wrap: wrap;
    margin-top: 0.25rem;
}
.controls-row .date-nav-inline {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}
.controls-row .platform-filter.inline,
.controls-row .sort-bar.inline {
    padding: 0;
    margin: 0;
}

/* Today button — chip styled, highlights gold when on the latest section. */
.today-btn {
    background: rgba(255,255,255,0.04);
    color: var(--text-secondary, #94a3b8);
    border: 1px solid var(--border-color, #334155);
    border-radius: 999px;
    padding: 0.35rem 0.9rem;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.today-btn:hover {
    color: var(--text-primary, #f1f5f9);
    border-color: var(--gold-primary, #d4af37);
}
.today-btn.active {
    background: var(--gold-primary, #d4af37);
    color: #1a1a1a;
    border-color: var(--gold-primary, #d4af37);
}

/* Hide the legacy floating LATEST badge (kept hidden in DOM for JS compat). */
.date-nav-badge { display: none !important; }
</style>
"""


def _per_game_background(game: dict) -> str:
    if game["bg_kind"] == "svg":
        return f"""<style>
body {{
    background-image:
        url("{game['bg_url']}"),
        radial-gradient(ellipse at top, {game['bg_tint_top']}, transparent 60%),
        radial-gradient(ellipse at bottom, {game['bg_tint_bottom']}, transparent 60%) !important;
}}
</style>"""

    # tile: PNG that needs CSS-applied opacity via a pseudo-element overlay.
    return f"""<style>
body {{
    background-image:
        radial-gradient(ellipse at top, {game['bg_tint_top']}, transparent 60%),
        radial-gradient(ellipse at bottom, {game['bg_tint_bottom']}, transparent 60%) !important;
    position: relative;
}}
body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("{game['bg_url']}");
    background-repeat: repeat;
    background-size: {game['bg_tile_size']}px {game['bg_tile_size']}px;
    opacity: {game['bg_opacity']};
    pointer-events: none;
    z-index: 0;
}}
</style>"""


TODAY_BTN_SCRIPT = """
<script>
(function () {
    function syncTodayBtn() {
        const sections = document.querySelectorAll('.date-section');
        if (!sections.length) return;
        let activeIdx = Array.from(sections).findIndex(s => s.classList.contains('active'));
        if (activeIdx < 0) activeIdx = 0;
        const btn = document.querySelector('.today-btn');
        if (btn) btn.classList.toggle('active', activeIdx === 0);
    }
    window.goToToday = function () {
        while (typeof currentDateIndex !== 'undefined' && currentDateIndex > 0) {
            nextDate();
        }
        syncTodayBtn();
    };
    document.addEventListener('click', function (e) {
        if (e.target.closest('.date-nav-btn')) {
            requestAnimationFrame(syncTodayBtn);
        }
    });
    window.addEventListener('load', syncTodayBtn);
    document.addEventListener('DOMContentLoaded', syncTodayBtn);
})();
</script>
"""


# ---------- assembly ---------------------------------------------------------


def generate_one(game: dict) -> int:
    mods = get_mods(game["slug"])
    sections = _changelog_sections(mods)
    body = f"""{_header(game)}
{_controls_row()}
<main class="changelog-container">
    <div class="changelog-stack">
{sections}
    </div>
</main>
{info_modal()}
{MODAL_SCRIPT}
{TODAY_BTN_SCRIPT}"""
    html = html_document(game["title"], body)
    html = html.replace("</head>", CUSTOM_CSS + _per_game_background(game) + "</head>", 1)
    (ROOT / game["filename"]).write_text(html, encoding="utf-8")
    return len(mods)


def main() -> None:
    for g in GAMES:
        n = generate_one(g)
        print(f"{g['filename']}: {n} mods")


if __name__ == "__main__":
    main()
