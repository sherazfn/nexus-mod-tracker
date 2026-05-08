"""Daily Nexus Mods scraper for tracked games.

For each game, fetches the list of mods updated in the last week and merges
their metadata into a per-game JSON file. The first run on an empty dataset
seeds with `period=1m` to backfill. Subsequent runs use `period=1w` to stay
ahead of any missed days.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://api.nexusmods.com/v1"
GAMES = ["baldursgate3", "clairobscurexpedition33"]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USER_AGENT = "nexus-mod-tracker/0.1 (+https://github.com/sherazfn/nexus-mod-tracker)"


def session() -> requests.Session:
    api_key = os.environ.get("NEXUS_API_KEY")
    if not api_key:
        sys.exit("NEXUS_API_KEY is not set")
    s = requests.Session()
    s.headers.update(
        {
            "accept": "application/json",
            "apikey": api_key,
            "User-Agent": USER_AGENT,
        }
    )
    return s


def get(s: requests.Session, path: str) -> dict | list:
    url = f"{API_BASE}{path}"
    for attempt in range(5):
        r = s.get(url, timeout=30)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "60"))
            print(f"429 on {path}; sleeping {wait}s")
            time.sleep(wait + 1)
            continue
        r.raise_for_status()
        remaining = r.headers.get("x-rl-daily-remaining")
        if remaining is not None:
            print(f"  rate-limit daily remaining: {remaining}")
        return r.json()
    sys.exit(f"giving up on {path} after retries")


def load_existing(slug: str) -> dict[int, dict]:
    path = DATA_DIR / f"{slug}.json"
    if not path.exists():
        return {}
    with path.open() as f:
        items = json.load(f)
    return {m["mod_id"]: m for m in items}


def save(slug: str, mods: dict[int, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{slug}.json"
    ordered = sorted(mods.values(), key=lambda m: m["mod_id"])
    with path.open("w") as f:
        json.dump(ordered, f, indent=2, sort_keys=True)


def scrape_game(s: requests.Session, slug: str) -> None:
    print(f"\n=== {slug} ===")
    existing = load_existing(slug)
    period = "1m" if not existing else "1w"
    print(f"Existing mods: {len(existing)}; period={period}")

    updated = get(s, f"/games/{slug}/mods/updated.json?period={period}")
    print(f"Updated entries: {len(updated)}")

    fetch_ids: list[int] = []
    for entry in updated:
        mod_id = entry["mod_id"]
        latest = entry["latest_file_update"]
        prior = existing.get(mod_id, {}).get("latest_file_update", -1)
        if mod_id not in existing or latest > prior:
            fetch_ids.append(mod_id)

    print(f"Need to fetch detail for: {len(fetch_ids)}")
    for i, mod_id in enumerate(fetch_ids, 1):
        try:
            detail = get(s, f"/games/{slug}/mods/{mod_id}.json")
        except requests.HTTPError as e:
            if e.response.status_code in (404, 403, 410):
                print(f"  [{i}/{len(fetch_ids)}] {mod_id}: skip detail ({e.response.status_code})")
                continue
            raise
        try:
            files = get(s, f"/games/{slug}/mods/{mod_id}/files.json")
            detail["files"] = files.get("files", [])
        except requests.HTTPError as e:
            if e.response.status_code in (404, 403, 410):
                print(f"  [{i}/{len(fetch_ids)}] {mod_id}: no files ({e.response.status_code})")
                detail["files"] = []
            else:
                raise
        match = next((u for u in updated if u["mod_id"] == mod_id), None)
        if match:
            detail["latest_file_update"] = match["latest_file_update"]
            detail["latest_mod_activity"] = match["latest_mod_activity"]
        existing[mod_id] = detail
        if i % 25 == 0:
            print(f"  [{i}/{len(fetch_ids)}] fetched")
        time.sleep(0.1)

    save(slug, existing)
    print(f"Saved {len(existing)} mods → data/{slug}.json")


def main() -> None:
    s = session()
    for slug in GAMES:
        scrape_game(s, slug)


if __name__ == "__main__":
    main()
