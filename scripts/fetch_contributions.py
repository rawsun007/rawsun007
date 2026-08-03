#!/usr/bin/env python3
"""Fetch the public contribution calendar for a GitHub user.

No API token and no GraphQL: GitHub serves the calendar as plain HTML at
https://github.com/users/<user>/contributions. Stdlib only, so the daily
workflow needs no pip install step.

Writes data/contributions.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

USER = os.environ.get("GH_USER", "rawsun007")
URL = f"https://github.com/users/{USER}/contributions"
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

DAY_RE = re.compile(
    r'data-date="(?P<date>\d{4}-\d{2}-\d{2})"\s+id="(?P<id>[^"]+)"\s+data-level="(?P<level>\d+)"'
)
TIP_RE = re.compile(
    r'<tool-tip[^>]*\sfor="(?P<id>contribution-day-component-[^"]+)"[^>]*>(?P<text>[^<]*)</tool-tip>'
)
COUNT_RE = re.compile(r"^(?:(?P<n>[\d,]+)\s+contributions?|No contributions)")


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{USER}-profile-art/1.0 (+https://github.com/{USER})",
            "Accept": "text/html",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def parse(html: str) -> list[dict]:
    counts: dict[str, int] = {}
    for m in TIP_RE.finditer(html):
        cm = COUNT_RE.match(m.group("text").strip())
        if not cm:
            continue
        n = cm.group("n")
        counts[m.group("id")] = int(n.replace(",", "")) if n else 0

    days = []
    for m in DAY_RE.finditer(html):
        days.append(
            {
                "date": m.group("date"),
                "level": int(m.group("level")),
                "count": counts.get(m.group("id"), 0),
            }
        )
    days.sort(key=lambda d: d["date"])
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    """Current and longest streak. Today counts only if it already has commits."""
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    today = date.today().isoformat()
    current = 0
    for d in reversed(days):
        if d["date"] > today:
            continue
        if d["count"] > 0:
            current += 1
        elif d["date"] == today:
            continue  # the day is not over yet, do not break the streak
        else:
            break
    return current, longest


def monthly(days: list[dict]) -> list[dict]:
    buckets: dict[str, int] = {}
    for d in days:
        buckets[d["date"][:7]] = buckets.get(d["date"][:7], 0) + d["count"]
    return [{"month": k, "count": v} for k, v in sorted(buckets.items())]


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
    html = fetch(URL)
    days = parse(html)
    if len(days) < 300:
        print(f"error: parsed only {len(days)} days, markup probably changed", file=sys.stderr)
        return 1

    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"])
    current, longest = streaks(days)
    recent = [d for d in days if d["date"] >= (date.today() - timedelta(days=30)).isoformat()]

    payload = {
        "user": USER,
        "generated_at": datetime.now(UTC).replace(microsecond=0, tzinfo=None).isoformat() + "Z",
        "total": total,
        "days": days,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best,
        "last_30_days": sum(d["count"] for d in recent),
        "months": monthly(days),
    }

    changed = write_if_changed(OUT, payload)
    print(f"{len(days)} days, {total} contributions, streak {current} (best {longest})"
          f" -> {OUT if changed else 'unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
