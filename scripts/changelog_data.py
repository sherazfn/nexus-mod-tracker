"""Build Mod / ModUpdate objects from a Nexus data/{slug}.json file."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class ModUpdate:
    timestamp: datetime
    update_type: str  # 'added' or 'updated'
    version: str


@dataclass
class Mod:
    item_id: int
    name: str
    summary: Optional[str] = None
    profile_url: Optional[str] = None
    logo_url: Optional[str] = None
    updates: list[ModUpdate] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    author: Optional[str] = None
    date_updated: int = 0
    popularity_rank: int = 0
    downloads_today: int = 0
    downloads_total: int = 0
    subscribers: int = 0
    rating_percent: int = 0
    rating_weighted: float = 0.0


def _to_dt(epoch: int | None) -> datetime:
    if not epoch:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def _build_mod(slug: str, raw: dict) -> Mod:
    mod_id = raw.get("mod_id")
    profile_url = f"https://www.nexusmods.com/{slug}/mods/{mod_id}"
    logo = raw.get("picture_url") or None
    files = raw.get("files") or []
    files_sorted = sorted(files, key=lambda f: f.get("uploaded_timestamp") or 0)

    updates: list[ModUpdate] = []
    for i, f in enumerate(files_sorted):
        ts = f.get("uploaded_timestamp")
        if not ts:
            continue
        updates.append(
            ModUpdate(
                timestamp=_to_dt(ts),
                update_type="added" if i == 0 else "updated",
                version=str(f.get("version") or ""),
            )
        )

    return Mod(
        item_id=mod_id,
        name=raw.get("name") or "(unnamed)",
        summary=raw.get("summary") or "",
        profile_url=profile_url,
        logo_url=logo,
        updates=updates,
        platforms=[],  # Nexus is PC-only for these games
        author=raw.get("author") or raw.get("uploaded_by"),
        date_updated=raw.get("updated_timestamp") or 0,
        downloads_total=raw.get("mod_downloads", 0),
        subscribers=raw.get("mod_unique_downloads", 0),
        rating_percent=raw.get("endorsement_count", 0),
    )


def get_mods(slug: str) -> dict[int, Mod]:
    path = DATA_DIR / f"{slug}.json"
    if not path.exists():
        return {}
    with path.open() as f:
        raw_list = json.load(f)
    out: dict[int, Mod] = {}
    for raw in raw_list:
        mod = _build_mod(slug, raw)
        if mod.updates:
            out[mod.item_id] = mod
    return out
