"""One-shot backfill for Expedition 33.

The daily scrape only sees mods that Nexus reports as "updated in the last
month", so older / unchanged mods are never discovered. This script probes
every mod_id in [1, max_known + PROBE_AHEAD] and refreshes detail for each,
merging into data/clairobscurexpedition33.json.
"""

from __future__ import annotations

import time

import requests

from .scrape import DATA_DIR, get, load_existing, save, session

SLUG = "clairobscurexpedition33"
PROBE_AHEAD = 100  # probe this many IDs past the highest known mod_id


def main() -> None:
    s = session()
    existing = load_existing(SLUG)
    max_known = max(existing) if existing else 0
    upper = max_known + PROBE_AHEAD
    print(f"E33 backfill: existing={len(existing)} max_id={max_known} upper={upper}")

    refreshed = 0
    discovered = 0
    skipped = 0
    for mod_id in range(1, upper + 1):
        try:
            detail = get(s, f"/games/{SLUG}/mods/{mod_id}.json")
        except requests.HTTPError as e:
            if e.response.status_code in (404, 403, 410):
                skipped += 1
                continue
            raise
        try:
            files = get(s, f"/games/{SLUG}/mods/{mod_id}/files.json")
            detail["files"] = files.get("files", [])
        except requests.HTTPError as e:
            if e.response.status_code in (404, 403, 410):
                detail["files"] = []
            else:
                raise
        prior = existing.get(mod_id, {})
        # Preserve the last_file_update / latest_mod_activity values that
        # the regular scrape tracks; the per-mod detail endpoint doesn't
        # return them, so fall back to updated_timestamp.
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
            print(f"  progress: refreshed={refreshed} discovered={discovered} skipped={skipped}")
        time.sleep(0.1)

    save(SLUG, existing)
    print(
        f"Done. refreshed={refreshed} discovered={discovered} "
        f"skipped={skipped} total={len(existing)} → data/{SLUG}.json"
    )


if __name__ == "__main__":
    main()
