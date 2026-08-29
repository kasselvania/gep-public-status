#!/usr/bin/env python3
"""Fail closed when the curated public feed has not reviewed current GEP status."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER_RE = re.compile(r"\A---\r?\n(?P<body>.*?)\r?\n---\r?\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError("source status has no frontmatter")
    result: dict[str, str] = {}
    for line in match.group("body").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            result[key.strip()] = value.strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a local private GEP status report with the reviewed public cut."
    )
    parser.add_argument(
        "source_status",
        help="path to PROJECT_STATUS.md, or - to read an exact git-show result",
    )
    args = parser.parse_args()

    try:
        source_text = (
            sys.stdin.read()
            if args.source_status == "-"
            else Path(args.source_status).read_text(encoding="utf-8")
        )
        private = parse_frontmatter(source_text)
        public = json.loads((ROOT / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"PUBLIC_STATUS_REVIEW_ERROR: {error}", file=sys.stderr)
        return 2

    expected = {
        "phase": public["phase"],
        "current_slice": public["current"]["slice"],
        "current_slice_title": public["current"]["title"],
        "last_completed_slice": public["reviewed_through"],
        "last_completed_title": public["last_completed"]["title"],
    }
    mismatches = [
        f"{key}: private={private.get(key)!r} public={value!r}"
        for key, value in expected.items()
        if private.get(key) != value
    ]
    if mismatches:
        print("PUBLIC_STATUS_REVIEW_PENDING", file=sys.stderr)
        for mismatch in mismatches:
            print(f"- {mismatch}", file=sys.stderr)
        return 1

    print(
        "PUBLIC_STATUS_REVIEW_CURRENT: "
        f"reviewed_through={public['reviewed_through']} "
        f"current={public['current']['slice']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
