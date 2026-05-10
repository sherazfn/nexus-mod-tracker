"""Chunked backfill: probe every mod_id for a game.

The daily scrape only sees mods Nexus reports as updated in the last
month, so older / unchanged mods are never picked up. This walks every
mod_id, fetching detail + files, and persists progress between runs so
it can stay under the Nexus daily rate limit (2500 calls/day).

Progress is tracked in data/.backfill_state.json keyed by slug:
    {"slug": {"next_id": 1234, "max_probed": 1233, "done": false}}

Usage:
    python -m scripts.backfill --slug baldursgate3 --limit 1000
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

from .scrape import DATA_DIR, get, load_existing, save, session

PROBE_AHEAD = 100  # probe this many IDs past the highest known mod_id
STATE_PATH = DATA_DIR / ".backfill_state.json"


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    with STATE_PATH.open() as f:
        return json.load(f)


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True, help="Nexus game slug, e.g. baldursgate3")
    p.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="max number of mod_ids to probe in this run (each = 2 API calls)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    slug = args.slug
    limit = args.limit

    s = session()
    existing = load_existing(slug)
    state = load_state()
    slug_state = state.get(slug, {"next_id": 1, "max_probed": 0, "done": False})

    if slug_state.get("done"):
        print(f"{slug}: backfill already marked done; nothing to do")
        return

    max_known = max(existing) if existing else 0
    upper = max_known + PROBE_AHEAD
    start = slug_state["next_id"]
    end = min(upper, start + limit - 1)

    if start > upper:
        print(f"{slug}: start={start} > upper={upper}; marking done")
        slug_state["done"] = True
        state[slug] = slug_state
        save_state(state)
        return

    print(
        f"{slug} backfill: existing={len(existing)} max_known={max_known} "
        f"upper={upper} probing={start}..{end} (limit={limit})"
    )

    refreshed = 0
    discovered = 0
    skipped = 0
    last_id = start - 1
    try:
        for mod_id in range(start, end + 1):
            last_id = mod_id
            try:
                detail = get(s, f"/games/{slug}/mods/{mod_id}.json")
            except requests.HTTPError as e:
                if e.response.status_code in (404, 403, 410):
                    skipped += 1
                    continue
                raise
            try:
                files = get(s, f"/games/{slug}/mods/{mod_id}/files.json")
                detail["files"] = files.get("files", [])
            except requests.HTTPError as e:
                if e.response.status_code in (404, 403, 410):
                    detail["files"] = []
                else:
                    raise
            prior = existing.get(mod_id, {})
            detail["latest_file_update"] = prior.get(
                "latest_file_update", detail.get("updated_timestamp", 0)
            )
            detail["latest_mod_activity"] = prior.get(
                "latest_mod_activity", detail.get("updated_timestamp", 0)
            )
            if mod_id in existing:
                refreshed += 1
            else:
                discovered += 1
            existing[mod_id] = detail
            if (refreshed + discovered) % 25 == 0:
                print(
                    f"  id={mod_id} refreshed={refreshed} "
                    f"discovered={discovered} skipped={skipped}"
                )
            time.sleep(0.1)
    finally:
        save(slug, existing)
        slug_state["next_id"] = last_id + 1
        slug_state["max_probed"] = max(slug_state.get("max_probed", 0), last_id)
        if slug_state["next_id"] > upper:
            slug_state["done"] = True
        state[slug] = slug_state
        save_state(state)
        print(
            f"Done. refreshed={refreshed} discovered={discovered} "
            f"skipped={skipped} total={len(existing)} "
            f"next_id={slug_state['next_id']} done={slug_state['done']}"
        )


if __name__ == "__main__":
    main()
