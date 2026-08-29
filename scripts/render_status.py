#!/usr/bin/env python3
"""Validate and render the curated GEP public-status publication."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "status.json"
MARKDOWN_PATH = ROOT / "PROJECT_STATUS.md"
META_PATH = ROOT / "meta.json"

SLICE_RE = re.compile(r"^[A-Z]+[0-9]+(?:R[0-9]+)?$")
PROHIBITED_PUBLIC_TEXT = (
    "trade replicant",
    "/users/",
    "docs/current-slice",
    "github.com/kasselvania/generalized_execution_platform",
    "/pull/",
    "/issues/",
)


class StatusError(ValueError):
    """Raised when curated public status violates its publication contract."""


def load_status(path: Path = SOURCE_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StatusError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise StatusError("status.json must contain one JSON object")
    return value


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise StatusError(f"{field} must be one nonempty trimmed string")
    if "\n" in value or "\r" in value or "|" in value:
        raise StatusError(f"{field} must be one table-safe line")
    return value


def require_slice(value: Any, field: str) -> str:
    text = require_text(value, field)
    if not SLICE_RE.fullmatch(text):
        raise StatusError(f"{field} is not a supported slice key: {text}")
    return text


def validate_status(status: dict[str, Any]) -> None:
    if status.get("schema") != "gep-public-status/v2":
        raise StatusError("schema must be gep-public-status/v2")
    if status.get("project") != "generalized_execution_platform":
        raise StatusError("project must be generalized_execution_platform")
    if status.get("phase") != "pre-production":
        raise StatusError("phase must remain pre-production")

    published_at = require_text(status.get("published_at"), "published_at")
    try:
        parsed_published_at = dt.datetime.fromisoformat(
            published_at.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise StatusError("published_at must be an ISO-8601 timestamp") from error
    if parsed_published_at.tzinfo is None:
        raise StatusError("published_at must include a timezone")

    current = status.get("current")
    if not isinstance(current, dict):
        raise StatusError("current must be one object")
    current_slice = require_slice(current.get("slice"), "current.slice")
    require_text(current.get("title"), "current.title")
    if current.get("status") != "active":
        raise StatusError("current.status must be active")

    last_completed = status.get("last_completed")
    if not isinstance(last_completed, dict):
        raise StatusError("last_completed must be one object")
    last_completed_slice = require_slice(
        last_completed.get("slice"), "last_completed.slice"
    )
    require_text(last_completed.get("title"), "last_completed.title")
    if current_slice == last_completed_slice:
        raise StatusError("current and last-completed slices must differ")
    if status.get("reviewed_through") != last_completed_slice:
        raise StatusError("reviewed_through must equal last_completed.slice")

    position = status.get("position")
    if not isinstance(position, list) or not position:
        raise StatusError("position must contain at least one paragraph")
    for index, paragraph in enumerate(position):
        require_text(paragraph, f"position[{index}]")

    completed = status.get("completed")
    if not isinstance(completed, list) or not completed:
        raise StatusError("completed must contain at least one milestone")
    seen: set[str] = set()
    previous_date: dt.date | None = None
    for index, row in enumerate(completed):
        if not isinstance(row, dict):
            raise StatusError(f"completed[{index}] must be one object")
        date_text = require_text(row.get("date"), f"completed[{index}].date")
        try:
            row_date = dt.date.fromisoformat(date_text)
        except ValueError as error:
            raise StatusError(
                f"completed[{index}].date must use YYYY-MM-DD"
            ) from error
        if previous_date is not None and row_date < previous_date:
            raise StatusError("completed milestones must be chronological")
        previous_date = row_date

        slice_key = require_slice(row.get("slice"), f"completed[{index}].slice")
        if slice_key in seen:
            raise StatusError(f"duplicate completed slice: {slice_key}")
        seen.add(slice_key)
        if row.get("evidence") != "local":
            raise StatusError(f"completed[{index}].evidence must be local")
        result = require_text(row.get("result"), f"completed[{index}].result")
        if not result.endswith("."):
            raise StatusError(f"completed[{index}].result must end with a period")

    if completed[-1].get("slice") != last_completed_slice:
        raise StatusError("last_completed.slice must equal the final completed milestone")
    if current_slice in seen:
        raise StatusError("the active slice cannot also be completed")

    not_yet = status.get("not_yet")
    if not isinstance(not_yet, list) or not not_yet:
        raise StatusError("not_yet must contain at least one explicit nonclaim")
    seen_nonclaims: set[str] = set()
    for index, statement in enumerate(not_yet):
        text = require_text(statement, f"not_yet[{index}]")
        folded = text.casefold()
        if folded in seen_nonclaims:
            raise StatusError(f"duplicate not_yet statement at index {index}")
        seen_nonclaims.add(folded)

    public_text = json.dumps(status, ensure_ascii=False).casefold()
    for prohibited in PROHIBITED_PUBLIC_TEXT:
        if prohibited in public_text:
            raise StatusError(f"prohibited public text found: {prohibited}")


def render_markdown(status: dict[str, Any]) -> str:
    current = status["current"]
    last_completed = status["last_completed"]
    lines = [
        "---",
        "schema_version: 2",
        f"project: {status['project']}",
        f"phase: {status['phase']}",
        f"current_slice: {current['slice']}",
        f"current_slice_title: {current['title']}",
        f"current_slice_status: {current['status']}",
        f"last_completed_slice: {last_completed['slice']}",
        f"last_completed_title: {last_completed['title']}",
        f"reviewed_through: {status['reviewed_through']}",
        "---",
        "",
        "# Generalized Execution Platform — Curated Public Status",
        "",
        "This is a selected public readback of implemented platform boundaries. It is not",
        "the private implementation ledger, a source-code mirror, or a complete project",
        "history. A listed milestone means a bounded local implementation and its stated",
        "evidence exist; it does not imply production or commercial maturity.",
        "",
        "## Current Public Position",
        "",
    ]
    for paragraph in status["position"]:
        lines.extend((paragraph, ""))
    lines.extend(
        (
            "## Exact Implementation Slice Ledger",
            "",
            "| Date | Slice | Evidence | Plain-English result |",
            "|---|---|---:|---|",
        )
    )
    for row in status["completed"]:
        lines.append(
            f"| {row['date']} | **{row['slice']}** | {row['evidence']} | {row['result']} |"
        )
    lines.extend(
        (
            "",
            "## Current Claim Ceiling",
            "",
            "GEP is **pre-production**. It does not yet claim:",
            "",
            "```text",
            *status["not_yet"],
            "```",
            "",
            "## Publication Boundary",
            "",
            "This file is generated from the reviewed, allowlisted `status.json` in this",
            "public repository. It contains selected platform facts only and does not publish",
            "private source, application-specific work, private repository coordinates,",
            "internal review links, secrets, credentials, datasets, or operator evidence.",
            "",
        )
    )
    return "\n".join(lines)


def render_meta(status: dict[str, Any]) -> str:
    value = {
        "version": "public-status-v2",
        "committed_at": status["published_at"],
        "source": "curated-public-ledger",
        "path": "PROJECT_STATUS.md",
        "reviewed_through": status["reviewed_through"],
        "current_slice": status["current"]["slice"],
    }
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def compare(path: Path, expected: str) -> bool:
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError:
        actual = ""
    if actual == expected:
        return True
    diff = difflib.unified_diff(
        actual.splitlines(keepends=True),
        expected.splitlines(keepends=True),
        fromfile=str(path),
        tofile=f"generated:{path.name}",
    )
    sys.stderr.writelines(diff)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the generated public Markdown and metadata",
    )
    args = parser.parse_args()

    try:
        status = load_status()
        validate_status(status)
    except StatusError as error:
        print(f"PUBLIC_STATUS_INVALID: {error}", file=sys.stderr)
        return 1

    markdown = render_markdown(status)
    meta = render_meta(status)
    if args.write:
        MARKDOWN_PATH.write_text(markdown, encoding="utf-8")
        META_PATH.write_text(meta, encoding="utf-8")
        print("PUBLIC_STATUS_RENDERED")
        return 0

    if compare(MARKDOWN_PATH, markdown) and compare(META_PATH, meta):
        print("PUBLIC_STATUS_VALID")
        return 0
    print("PUBLIC_STATUS_STALE: run scripts/render_status.py --write", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
