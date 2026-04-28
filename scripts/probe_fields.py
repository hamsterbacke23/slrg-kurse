"""Probe what extra fields the SLRG search exposes."""
import re
import sys
sys.path.insert(0, ".")
from scrape import make_session, DWR_BASE, BASE, CAL_URL  # type: ignore

s, sid = make_session()

extras = [
    "geoloc_zip", "geoloc_postal", "geoloc_postalcode", "geoloc_country",
    "geoloc_lat", "geoloc_lon", "geoloc_lng", "geoloc_latitude", "geoloc_longitude",
    "geoloc_canton", "geoloc_state", "geoloc_region", "geoloc_address",
    "geoloc_street", "geoloc_house_number", "geoloc_house_no",
    "address_zip", "relAddress.geoloc_zip", "relAddress.geoloc_city",
    "relAddress.geoloc_zip_c", "relAddress.address_canton",
]
fields = [
    "status", "relEvent_category", "geoloc_city", "first_course_date",
    "last_course_date", "relAddress.company_c", "more",
] + extras

lines = ["callCount=1", "c0-scriptName=nice2_netui_SearchService",
         "c0-methodName=search", "c0-id=0",
         "c0-param0=array:[]", "c0-e1=array:[]"]
refs = []
for i, f in enumerate(fields, start=3):
    lines.append(f"c0-e{i}=string:{f}")
    refs.append(f"reference:c0-e{i}")
n = 3 + len(fields)
lines.append(f"c0-e2=array:[{','.join(refs)}]")
lines += [
    f"c0-e{n+1}=number:0",
    f"c0-e{n+2}=number:1",
    f"c0-e{n}=Object_searchService.Paging:{{offset:reference:c0-e{n+1}, limit:reference:c0-e{n+2}}}",
    f"c0-e{n+4}=string:EventRegistration_list",
    f"c0-e{n+5}=string:list",
    f"c0-e{n+3}=Object_form.FormIdentifier:{{formName:reference:c0-e{n+4}, scope:reference:c0-e{n+5}}}",
    f"c0-e{n+7}=string:EventRegistration_search",
    f"c0-e{n+8}=string:search",
    f"c0-e{n+6}=Object_form.FormIdentifier:{{formName:reference:c0-e{n+7}, scope:reference:c0-e{n+8}}}",
    f"c0-e{n+9}=null:null",
    f"c0-e{n+10}=null:null",
    f"c0-e{n+11}=string:Event",
    f"c0-e{n+12}=null:null",
    f"c0-e{n+13}=null:null",
    f"c0-e{n+14}=array:[]",
    f"c0-e{n+15}=boolean:true",
    f"c0-e{n+18}=string:first_course_date",
    f"c0-e{n+19}=string:ASC",
    f"c0-e{n+17}=Object_searchService.OrderItem:{{path:reference:c0-e{n+18}, direction:reference:c0-e{n+19}}}",
    f"c0-e{n+16}=array:[reference:c0-e{n+17}]",
    f"c0-e{n+20}=null:null",
    f"c0-param1=Object_nice2.netui.SearchParameters:{{queryParams:reference:c0-e1, columns:reference:c0-e2, paging:reference:c0-e{n}, listForm:reference:c0-e{n+3}, searchForm:reference:c0-e{n+6}, constrictionParams:reference:c0-e{n+9}, relatedTo:reference:c0-e{n+10}, entityName:reference:c0-e{n+11}, pks:reference:c0-e{n+12}, manualQuery:reference:c0-e{n+13}, searchFilters:reference:c0-e{n+14}, skipDefaultDisplay:reference:c0-e{n+15}, order:reference:c0-e{n+16}, searchFilter:reference:c0-e{n+20}}}",
    "batchId=1", "instanceId=0", "page=%2FKurskalender",
    f"scriptSessionId={sid}", "",
]
body = "\n".join(lines)

text = s.request(
    "POST",
    f"{DWR_BASE}/nice2_netui_SearchService.search.dwr",
    data=body.encode(),
    headers={
        "Content-Type": "text/plain",
        "X-Client": "frontend",
        "X-Language": "de",
        "Origin": BASE,
        "Referer": CAL_URL,
    },
    timeout=60,
)
print(text[:6000])
print("\n\n--- looks like exception:", "Exception" in text or "exception" in text)
