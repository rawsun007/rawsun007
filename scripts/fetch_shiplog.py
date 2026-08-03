#!/usr/bin/env python3
"""Fetch the last things I actually shipped: releases and commit subjects.

A contribution heatmap says how often. This says what.

The obvious source, /users/<user>/events/public, is no use: its PushEvent
payloads carry only the before/head SHAs now, no commit messages at all. So this
walks the repos instead, most recently pushed first, and reads their commits and
releases directly.

Unauthenticated works (60 requests an hour, this uses about a dozen). Set
GITHUB_TOKEN for headroom; the workflow passes the one Actions already has.

Writes data/shiplog.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

USER = os.environ.get("GH_USER", "rawsun007")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent / "data" / "shiplog.json"

KEEP = 10
REPOS_TO_WALK = 6      # most recently pushed; older ones cannot win a slot anyway
COMMITS_PER_REPO = 10

# A bot's commit is not something a person decided to do.
SKIP = ("chore: refresh contribution heatmap", "[skip ci]", "Merge branch", "Merge pull request")
# "Release v0.15.1" is the version bump behind a release that already has its
# own row. Two lines saying the same thing wastes one of only ten slots.
SKIP_PATTERN = re.compile(r"^Release v?\d+\.\d+")


def api(path: str) -> list | dict:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "User-Agent": f"{USER}-profile-art/1.0 (+https://github.com/{USER})",
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def safe(path: str) -> list | dict:
    """A single repo failing (empty, moved, rate-limited) must not cost the
    whole log: the page is better slightly short than missing."""
    try:
        return api(path)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as err:
        print(f"  skipped {path}: {err}", file=sys.stderr)
        return []


def collect() -> list[dict]:
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=100")
    rows: list[dict] = []

    for repo in repos[:REPOS_TO_WALK]:
        name, full = repo["name"], repo["full_name"]

        for rel in safe(f"/repos/{full}/releases?per_page=5"):
            if rel.get("draft") or not rel.get("published_at"):
                continue
            rows.append({"kind": "release", "repo": name, "at": rel["published_at"],
                         "text": f'released {rel["tag_name"]}'})

        for commit in safe(f"/repos/{full}/commits?author={USER}&per_page={COMMITS_PER_REPO}"):
            info = commit.get("commit", {})
            subject = info.get("message", "").split("\n")[0].strip()
            when = info.get("author", {}).get("date", "")
            if not subject or not when or any(s in subject for s in SKIP):
                continue
            if SKIP_PATTERN.match(subject):
                continue
            rows.append({"kind": "commit", "repo": name, "at": when, "text": subject})

    rows.sort(key=lambda r: r["at"], reverse=True)
    return rows


def main() -> int:
    rows = collect()
    if not rows:
        print("error: nothing came back, the API shape or the account changed", file=sys.stderr)
        return 1

    payload = {
        "user": USER,
        "generated_at": datetime.now(UTC).replace(microsecond=0, tzinfo=None).isoformat() + "Z",
        "entries": rows[:KEEP],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"{len(rows)} rows, kept {len(payload['entries'])} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
