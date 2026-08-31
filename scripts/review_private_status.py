#!/usr/bin/env python3
"""Fail closed when the curated public feed has not reviewed live GEP authority."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_SLICE_HEADING_RE = re.compile(
    r"\A# Current Slice: (?P<slice>[A-Z]+[0-9]+(?:R[0-9]+)?) — "
    r"(?P<title>[^\r\n]+)\r?\n"
)
AUTHORITY_POSTURE_RE = re.compile(
    r"^## Authority posture\r?\n\r?\n```text\r?\n"
    r"(?P<body>.*?)\r?\n```",
    re.DOTALL | re.MULTILINE,
)


def parse_authority_fields(text: str) -> dict[str, str]:
    heading = CURRENT_SLICE_HEADING_RE.match(text)
    if heading is None:
        raise ValueError("current-slice authority has no supported active heading")
    posture = AUTHORITY_POSTURE_RE.search(text)
    if posture is None:
        raise ValueError("current-slice authority has no authority-posture block")

    result = {
        "current_slice": heading.group("slice"),
        "current_slice_title": heading.group("title"),
    }
    for line in posture.group("body").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            result[key.strip()] = value.strip()

    if result.get("status") != "AUTHORIZED_FOR_IMPLEMENTATION":
        raise ValueError("current-slice authority is not authorized for implementation")
    for field in ("last_completed_slice", "last_completed_title"):
        if not result.get(field):
            raise ValueError(f"current-slice authority is missing {field}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare live GEP current-slice authority with the reviewed public cut."
    )
    parser.add_argument(
        "current_slice",
        help="path to docs/current-slice.md, or - to read an exact git-show result",
    )
    args = parser.parse_args()

    try:
        authority_text = (
            sys.stdin.read()
            if args.current_slice == "-"
            else Path(args.current_slice).read_text(encoding="utf-8")
        )
        authority = parse_authority_fields(authority_text)
        public = json.loads((ROOT / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"PUBLIC_STATUS_REVIEW_ERROR: {error}", file=sys.stderr)
        return 2

    expected = {
        "current_slice": public["current"]["slice"],
        "current_slice_title": public["current"]["title"],
        "last_completed_slice": public["reviewed_through"],
        "last_completed_title": public["last_completed"]["title"],
    }
    mismatches = [
        f"{key}: authority={authority.get(key)!r} public={value!r}"
        for key, value in expected.items()
        if authority.get(key) != value
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
