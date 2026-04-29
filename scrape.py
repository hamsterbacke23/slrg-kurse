#!/usr/bin/env python3
"""
SLRG Kurskalender scraper.

Talks to the DWR endpoint behind https://ausbildung.slrg.ch/Kurskalender,
paginates through every event and writes a clean `courses.json`.

Re-run any time to refresh. Stdlib only — but needs a Python build with SSL.
"""
from __future__ import annotations

import http.cookiejar
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import ssl  # noqa: F401
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERROR: this Python build has no `ssl` module, so https won't work.\n"
        f"       (you ran: {sys.executable})\n"
        "       Use a Python with SSL, e.g.  /opt/homebrew/bin/python3 scrape.py\n"
    )
    sys.exit(2)

BASE = "https://ausbildung.slrg.ch"
CAL_URL = f"{BASE}/Kurskalender"
DWR_BASE = f"{BASE}/nice2/dwr/call/plaincall"
PAGE_SIZE = 100
OUT = Path(__file__).parent / "courses.json"


DEFAULT_HEADERS = {
    "User-Agent": (
        "slrg-kurse-mirror/1.0 "
        "(+https://github.com/hamsterbacke23/slrg-kurse; "
        "hourly mirror of the public Kurskalender)"
    ),
    "Accept-Language": "de,en;q=0.8",
}


class Session:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def request(self, method: str, url: str, *, data: bytes | None = None,
                headers: dict[str, str] | None = None, timeout: int = 60) -> str:
        h = dict(DEFAULT_HEADERS)
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        with self.opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def set_cookie(self, name: str, value: str, domain: str) -> None:
        c = http.cookiejar.Cookie(
            version=0, name=name, value=value,
            port=None, port_specified=False,
            domain=domain, domain_specified=True, domain_initial_dot=False,
            path="/", path_specified=True,
            secure=True, expires=None, discard=True,
            comment=None, comment_url=None, rest={}, rfc2109=False,
        )
        self.jar.set_cookie(c)


def make_session() -> tuple[Session, str]:
    """Bootstrap a session and return (session, scriptSessionId)."""
    s = Session()

    # 1. Hit the calendar page to seed cookies.
    s.request("GET", CAL_URL, timeout=30)

    # 2. Ask DWR for a session id.
    body = (
        "callCount=1\n"
        "c0-scriptName=__System\n"
        "c0-methodName=generateId\n"
        "c0-id=0\n"
        "batchId=0\n"
        "instanceId=0\n"
        "page=%2FKurskalender\n"
        "scriptSessionId=\n"
    )
    text = s.request(
        "POST",
        f"{DWR_BASE}/__System.generateId.dwr",
        data=body.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=30,
    )
    m = re.search(r'handleCallback\("0","0","([^"]+)"', text)
    if not m:
        raise RuntimeError(f"Could not parse generateId reply:\n{text[:500]}")
    dwr_id = m.group(1)
    s.set_cookie("DWRSESSIONID", dwr_id, "ausbildung.slrg.ch")
    script_session = f"{dwr_id}/{secrets.token_hex(8)}"
    return s, script_session


def search_page(
    s: Session, script_session: str, offset: int, limit: int, batch: int
) -> str:
    body = f"""callCount=1
c0-scriptName=nice2_netui_SearchService
c0-methodName=search
c0-id=0
c0-param0=array:[]
c0-e1=array:[]
c0-e3=string:status
c0-e4=string:relEvent_category
c0-e5=string:geoloc_city
c0-e6=string:first_course_date
c0-e7=string:last_course_date
c0-e8=string:relAddress.company_c
c0-e9=string:more
c0-e2=array:[reference:c0-e3,reference:c0-e4,reference:c0-e5,reference:c0-e6,reference:c0-e7,reference:c0-e8,reference:c0-e9]
c0-e11=number:{offset}
c0-e12=number:{limit}
c0-e10=Object_searchService.Paging:{{offset:reference:c0-e11, limit:reference:c0-e12}}
c0-e14=string:EventRegistration_list
c0-e15=string:list
c0-e13=Object_form.FormIdentifier:{{formName:reference:c0-e14, scope:reference:c0-e15}}
c0-e17=string:EventRegistration_search
c0-e18=string:search
c0-e16=Object_form.FormIdentifier:{{formName:reference:c0-e17, scope:reference:c0-e18}}
c0-e19=null:null
c0-e20=null:null
c0-e21=string:Event
c0-e22=null:null
c0-e23=null:null
c0-e24=array:[]
c0-e25=boolean:true
c0-e28=string:first_course_date
c0-e29=string:ASC
c0-e27=Object_searchService.OrderItem:{{path:reference:c0-e28, direction:reference:c0-e29}}
c0-e26=array:[reference:c0-e27]
c0-e30=null:null
c0-param1=Object_nice2.netui.SearchParameters:{{queryParams:reference:c0-e1, columns:reference:c0-e2, paging:reference:c0-e10, listForm:reference:c0-e13, searchForm:reference:c0-e16, constrictionParams:reference:c0-e19, relatedTo:reference:c0-e20, entityName:reference:c0-e21, pks:reference:c0-e22, manualQuery:reference:c0-e23, searchFilters:reference:c0-e24, skipDefaultDisplay:reference:c0-e25, order:reference:c0-e26, searchFilter:reference:c0-e30}}
batchId={batch}
instanceId=0
page=%2FKurskalender
scriptSessionId={script_session}
"""
    return s.request(
        "POST",
        f"{DWR_BASE}/nice2_netui_SearchService.search.dwr",
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "text/plain",
            "X-Client": "frontend",
            "X-Language": "de",
            "Origin": BASE,
            "Referer": CAL_URL,
        },
        timeout=60,
    )


# ---- DWR-reply parsing ---------------------------------------------------

VALUE_RE = re.compile(r'value:\s*("(?:\\.|[^"\\])*"|\d+|new Date\([^)]+\))')
KEY_RE = re.compile(r"new nice2\.entity\.PrimaryKey\('(\d+)'\)")
TOTAL_RE = re.compile(r"totalRows:\s*(\d+)")
SENDING_RE = re.compile(r"sendingRows:\s*(\d+)")


def _decode_js_string(s: str) -> str:
    # JS string literal -> python str. Strip quotes, decode \uXXXX and \/.
    inner = s[1:-1]
    inner = inner.replace(r"\/", "/")
    return bytes(inner, "utf-8").decode("unicode_escape")


def _decode_value(token: str) -> Any:
    if token.startswith('"'):
        return _decode_js_string(token)
    if token.startswith("new Date"):
        nums = [int(x) for x in re.findall(r"-?\d+", token)]
        # JS months are 0-based.
        y, mo, d = nums[0], nums[1] + 1, nums[2]
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return int(token)


def parse_reply(text: str) -> tuple[int, list[dict[str, Any]]]:
    total_m = TOTAL_RE.search(text)
    total = int(total_m.group(1)) if total_m else 0
    rows: list[dict[str, Any]] = []

    # Each row starts with `{cells:{` and ends right before the next row or `]`.
    # We split on the row-key marker which appears at the end of every row.
    # Easier: walk by finding each PrimaryKey occurrence and slicing the row block
    # around it.
    row_blocks = re.split(r"(?=\{cells:\{status:)", text)
    for block in row_blocks[1:]:
        # cut block at sources marker end
        end = block.find("}],")
        chunk = block if end == -1 else block[: end + 2]

        key_m = KEY_RE.search(chunk)
        if not key_m:
            continue
        key = key_m.group(1)

        def grab(field: str) -> str:
            # find cells block named `field` (or bare `status`/`more`)
            patt = rf'(?:"{field}"|\b{field}):dwr\.engine\.remote\.newObject\("grid\.Cell"'
            m = re.search(patt, chunk)
            if not m:
                return ""
            sub = chunk[m.end() :]
            # collect all `value:` occurrences inside cellValues for this Cell
            # stop at next field marker
            stop = re.search(r'\),(?:"[a-zA-Z_.]+"|more):dwr\.engine\.remote\.newObject\("grid\.Cell"', sub)
            scope = sub if not stop else sub[: stop.start()]
            vals = [_decode_value(v.group(1)) for v in VALUE_RE.finditer(scope)]
            return vals  # type: ignore[return-value]

        status_vals = grab("status")
        # status cellValues = [participation_max, "", registration, ""]
        part_max = status_vals[0] if len(status_vals) > 0 else None
        registered = status_vals[2] if len(status_vals) > 2 else None

        cat_vals = grab("relEvent_category")
        city_vals = grab("geoloc_city")
        first_vals = grab("first_course_date")
        last_vals = grab("last_course_date")
        comp_vals = grab("relAddress.company_c")

        category = cat_vals[0] if cat_vals else ""
        city = city_vals[0] if city_vals else ""
        first = first_vals[0] if first_vals else ""
        last = last_vals[0] if last_vals else ""
        company = comp_vals[0] if comp_vals else ""

        rows.append(
            {
                "key": key,
                "category": category,
                "city": city,
                "first_date": first,
                "last_date": last,
                "company": company,
                "participation_max": part_max,
                "registered": registered,
                "url": f"{CAL_URL}#detail&key={key}",
            }
        )

    return total, rows


def scrape_all() -> list[dict[str, Any]]:
    s, sid = make_session()
    print(f"[ok] session ready ({sid.split('/')[0][:12]}…)", file=sys.stderr)

    all_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    offset = 0
    batch = 1
    total: int | None = None

    while True:
        text = search_page(s, sid, offset=offset, limit=PAGE_SIZE, batch=batch)
        page_total, rows = parse_reply(text)
        if total is None:
            total = page_total
            print(f"[ok] total rows on server: {total}", file=sys.stderr)

        new = 0
        for r in rows:
            if r["key"] in seen:
                continue
            seen.add(r["key"])
            all_rows.append(r)
            new += 1

        print(
            f"[..] offset={offset:>5}  got={len(rows):>3}  new={new:>3}  "
            f"total_collected={len(all_rows)}",
            file=sys.stderr,
        )

        if not rows:
            break
        offset += len(rows)
        batch += 1
        if total is not None and offset >= total:
            break
        time.sleep(0.2)

    return all_rows


def main() -> int:
    rows = scrape_all()
    OUT.write_text(json.dumps({
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "count": len(rows),
        "courses": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] wrote {len(rows)} courses to {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
