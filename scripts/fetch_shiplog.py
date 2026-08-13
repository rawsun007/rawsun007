#!/usr/bin/env python3
"""Fetch the last things I actually shipped: releases and commit subjects.

A contribution heatmap says how often. This says what.

The obvious source, /users/<user>/events/public, is no use: its PushEvent
payloads carry only the before/head SHAs now, no commit messages at all. So this
walks the repos instead, most recently pushed first, and reads their commits and
releases directly.

Walking /users/<user>/repos only ever sees repos this account owns, so work
merged into someone else's project was invisible here. Merged pull requests are
fetched separately, through search, and only for repos owned by somebody else:
in our own repos the commit walk above already covers the same work.

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
MERGED_PRS = 20        # one search page; older merges cannot win a slot anyway
# Ten "most recent" rows is a popularity contest local work always wins: a
# release day here is five or six commits, while a merge into someone else's
# project is one row that took a week. Left purely chronological, the first
# run of this feature pushed its own commit to the top and knocked the only
# open-source row off the bottom. Hold a few slots back.
RESERVED_FOR_MERGES = 3

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


def merged_elsewhere() -> list[dict]:
    """Pull requests of ours that someone else merged into their project.

    Deliberately skips repos we own. Those commits land on a branch the repo
    walk already reads, so counting the merge too would spend two of ten slots
    saying one thing.

    Search is a separate, stricter rate limit (10/min unauthenticated), so this
    is one page and one request.
    """
    found = safe(
        f"/search/issues?q=author:{USER}+type:pr+is:merged"
        f"&sort=updated&order=desc&per_page={MERGED_PRS}"
    )
    items = found.get("items", []) if isinstance(found, dict) else []

    rows: list[dict] = []
    for item in items:
        full = str(item.get("repository_url", "")).rsplit("/repos/", 1)[-1]
        owner = full.split("/")[0]
        if not full or owner.lower() == USER.lower():
            continue
        merged_at = (item.get("pull_request") or {}).get("merged_at")
        title = str(item.get("title", "")).strip()
        if not merged_at or not title:
            continue
        rows.append({"kind": "merge", "repo": full, "at": merged_at, "text": title})
    return rows


def collect() -> list[dict]:
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=100")
    rows: list[dict] = merged_elsewhere()

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


def top(rows: list[dict], keep: int) -> list[dict]:
    """The newest ``keep`` rows, except merges cannot all be crowded out.

    Takes the newest rows as usual, then, if fewer than ``RESERVED_FOR_MERGES``
    merges survived, trades the oldest local rows for the newest merges that
    missed out. The result is still shown newest-first; only which rows make
    the cut changes.
    """
    chosen = rows[:keep]
    merges = [r for r in rows if r["kind"] == "merge"]
    want = merges[: min(RESERVED_FOR_MERGES, len(merges))]
    missing = [m for m in want if m not in chosen]
    if not missing:
        return chosen

    # Drop from the oldest end, and never drop a merge to seat another one.
    droppable = [r for r in reversed(chosen) if r["kind"] != "merge"]
    for merge, victim in zip(missing, droppable, strict=False):
        chosen[chosen.index(victim)] = merge
    chosen.sort(key=lambda r: r["at"], reverse=True)
    return chosen


def write_if_changed(path: Path, payload: dict) -> bool:
    """Write only when something other than the timestamp moved.

    Every field here is derived from GitHub, so on a quiet day the only
    difference between two runs is generated_at. Writing that anyway produces a
    daily commit that says nothing changed by changing something, which buries
    the days that did change and makes the timestamp a lie about the data's age
    rather than the run's.
    """
    if path.exists():
        try:
            old = json.loads(path.read_text())
            if {k: v for k, v in old.items() if k != "generated_at"} == \
               {k: v for k, v in payload.items() if k != "generated_at"}:
                return False
        except (json.JSONDecodeError, OSError):
            pass   # unreadable: rewrite it
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1) + "\n")
    return True


def main() -> int:
    rows = collect()
    if not rows:
        print("error: nothing came back, the API shape or the account changed", file=sys.stderr)
        return 1

    payload = {
        "user": USER,
        "generated_at": datetime.now(UTC).replace(microsecond=0, tzinfo=None).isoformat() + "Z",
        "entries": top(rows, KEEP),
    }
    changed = write_if_changed(OUT, payload)
    print(f"{len(rows)} rows, kept {len(payload['entries'])}"
          f" -> {OUT if changed else 'unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
