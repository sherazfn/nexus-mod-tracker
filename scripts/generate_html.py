"""Generate per-game HTML pages styled to match the bg3-mod-tracker UI."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .changelog_data import Mod, ModUpdate, get_mods
from .components import (
    date_nav,
    date_section,
    empty_state,
    html_document,
    page_layout,
    tabs_script,
)
from .components.tabs import mod_card

ROOT = Path(__file__).resolve().parent.parent

GAMES = [
    {
        "slug": "baldursgate3",
        "label": "Baldur's Gate 3",
        "filename": "index.html",
        "title": "BG3 Nexus Mod Tracker",
    },
    {
        "slug": "clairobscurexpedition33",
        "label": "Expedition 33",
        "filename": "expedition33.html",
        "title": "Expedition 33 Nexus Mod Tracker",
    },
]

# Only render activity from the last N days; older history bloats the page.
CUTOFF_DAYS = 30


def _flatten(mods: dict[int, Mod]) -> list[tuple[Mod, ModUpdate]]:
    out: list[tuple[Mod, ModUpdate]] = []
    for m in mods.values():
        for u in m.updates:
            out.append((m, u))
    return out


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


def _changelog_content(mods: dict[int, Mod]) -> tuple[str, str]:
    if not mods:
        return empty_state("No mods found"), ""

    cutoff = (datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)).date()
    by_date: dict[date, dict[str, list[tuple[Mod, ModUpdate]]]] = {}
    for m, u in _flatten(mods):
        d = u.timestamp.date()
        if d < cutoff:
            continue
        by_date.setdefault(d, {"added": [], "updated": []})[u.update_type].append((m, u))

    if not by_date:
        return empty_state("No mods updated in the last 30 days"), ""

    sorted_dates = sorted(by_date.keys(), reverse=True)
    sections: list[str] = []
    for i, day in enumerate(sorted_dates):
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
    return "\n".join(sections), date_nav()


def _game_switcher(active_slug: str) -> str:
    chips = []
    for g in GAMES:
        is_active = g["slug"] == active_slug
        cls = "platform-chip active" if is_active else "platform-chip"
        onclick = "" if is_active else f"onclick=\"location.href='{g['filename']}'\""
        chips.append(
            f'<button class="{cls}" type="button" {onclick} '
            f'role="tab" aria-selected="{"true" if is_active else "false"}">'
            f'{g["label"]}</button>'
        )
    return (
        '<div class="platform-filter" role="tablist" aria-label="Select game" '
        'style="margin: 0.5rem 0 1.75rem;">'
        + "".join(chips)
        + "</div>"
    )


def generate_one(game: dict) -> int:
    mods = get_mods(game["slug"])
    content, nav = _changelog_content(mods)
    layout = page_layout(
        title=game["title"],
        content=content,
        hero_image_url="favicon.svg",
        date_nav_html=nav,
    )
    layout = layout.replace("</header>", "</header>\n" + _game_switcher(game["slug"]), 1)
    html = html_document(game["title"], layout)
    (ROOT / game["filename"]).write_text(html, encoding="utf-8")
    return len(mods)


def main() -> None:
    for g in GAMES:
        n = generate_one(g)
        print(f"{g['filename']}: {n} mods")


if __name__ == "__main__":
    main()
