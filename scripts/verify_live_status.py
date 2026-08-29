#!/usr/bin/env python3
"""Verify that the public feed and deployed site still agree on the feed owner."""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = "https://raw.githubusercontent.com/kasselvania/gep-public-status/main/"
SITE_ROOT = "https://gep.peterkassel.com/"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        f"{url}?publication_check={int(time.time())}",
        headers={"User-Agent": "gep-public-status-validator/2"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        return response.read()


def main() -> int:
    try:
        for name in ("PROJECT_STATUS.md", "meta.json"):
            local = (ROOT / name).read_bytes()
            remote = fetch(RAW_ROOT + name)
            if local != remote:
                raise RuntimeError(f"live public feed differs from checked-out {name}")
        site_script = fetch(SITE_ROOT + "js/main.js").decode("utf-8")
        if "kasselvania/gep-public-status/main/" not in site_script:
            raise RuntimeError("deployed site does not name the curated public feed")
    except (OSError, UnicodeDecodeError, RuntimeError, urllib.error.URLError) as error:
        print(f"PUBLIC_STATUS_LIVE_INVALID: {error}", file=sys.stderr)
        return 1
    print("PUBLIC_STATUS_LIVE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
