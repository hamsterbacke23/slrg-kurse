#!/usr/bin/env python3
"""
Enrich courses.json with canton + lat/lng using https://api3.geo.admin.ch
(Swiss federal geo-search API). Caches results in geocache.json.

Re-run any time. Safe & idempotent.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import ssl  # noqa: F401
except ImportError:
    sys.stderr.write(
        "ERROR: this Python build has no `ssl` module.\n"
        f"       (you ran: {sys.executable})\n"
        "       Use a Python with SSL, e.g.  /opt/homebrew/bin/python3 geocode.py\n"
    )
    sys.exit(2)

ROOT = Path(__file__).parent
COURSES = ROOT / "courses.json"
CACHE = ROOT / "geocache.json"
API = "https://api3.geo.admin.ch/rest/services/api/SearchServer"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

LABEL_CANTON_RE = re.compile(r"\(([A-Z]{2})\)")
TAGS_RE = re.compile(r"<[^>]+>")


def geocode(city: str, timeout: int = 15) -> dict | None:
    qs = urllib.parse.urlencode(
        {"searchText": city, "type": "locations", "sr": "4326", "limit": "5"}
    )
    req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    results = data.get("results", [])
    # Prefer gg25 (official municipality), then gazetteer.
    def score(r):
        a = r.get("attrs", {})
        origin = a.get("origin", "")
        return (
            0 if origin == "gg25" else 1 if origin == "gazetteer" else 2,
            -int(a.get("weight", 0) or 0),
        )
    results = sorted(results, key=score)
    for res in results:
        a = res.get("attrs", {})
        label = a.get("label", "")
        plain = TAGS_RE.sub("", label)
        m = LABEL_CANTON_RE.search(plain)
        if not m:
            continue
        return {
            "canton": m.group(1),
            "label": plain.strip(),
            "lat": a.get("lat"),
            "lng": a.get("lon"),
        }
    return None


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    if not COURSES.exists():
        print(f"missing {COURSES}; run scrape.py first", file=sys.stderr)
        return 1

    doc = json.loads(COURSES.read_text(encoding="utf-8"))
    courses = doc["courses"]
    cache = load_cache()

    cities = sorted({(c.get("city") or "").strip() for c in courses if c.get("city")})
    print(f"[ok] {len(courses)} courses, {len(cities)} unique cities", file=sys.stderr)

    todo = [c for c in cities if c not in cache]
    print(f"[ok] {len(cache)} cached, {len(todo)} to fetch", file=sys.stderr)

    for i, city in enumerate(todo, 1):
        try:
            info = geocode(city)
        except Exception as exc:
            print(f"  [warn] {city!r}: {exc}", file=sys.stderr)
            info = None
        cache[city] = info  # remember even None to skip next time
        if i % 25 == 0 or i == len(todo):
            save_cache(cache)
            print(f"  [{i:>3}/{len(todo)}] {city!r} -> {info}", file=sys.stderr)
        time.sleep(0.05)
    save_cache(cache)

    enriched = 0
    for c in courses:
        city = (c.get("city") or "").strip()
        info = cache.get(city) if city else None
        if info:
            c["canton"] = info.get("canton")
            c["lat"] = info.get("lat")
            c["lng"] = info.get("lng")
            enriched += 1
        else:
            c.setdefault("canton", None)
            c.setdefault("lat", None)
            c.setdefault("lng", None)

    doc["courses"] = courses
    doc["geocoded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    COURSES.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[done] enriched {enriched}/{len(courses)} courses with canton+coords",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
