#!/usr/bin/env python3
"""
Validate in-the-vial/tracker.json — the data source the regulatory tracker
renders from. Catches the mistakes that would break the render or silently drop
Spanish: missing bilingual fields, unknown status classes, or an ES value that
is identical to EN (an untranslated fallback).

Usage:  python3 validate_tracker.py [path/to/tracker.json]
Exit 0 = valid, 1 = problems found, 2 = file/parse error.
"""
import sys, json

DEFAULT = "in-the-vial/tracker.json"
STATUSES = {"live", "pending", "flux", "closed"}   # the .pill classes the CSS styles
BILINGUAL_TEXT = ("title", "statusLabel", "meta")   # plain text: ES must differ from EN
BILINGUAL_HTML = ("body", "means")                  # may contain <strong>; ES must differ

def bad(msg, errs): errs.append(msg)

def check_bilingual(obj, field, where, errs, require_distinct):
    v = obj.get(field)
    if not isinstance(v, dict) or "en" not in v or "es" not in v:
        bad(f"{where}: '{field}' must be an object with 'en' and 'es'", errs); return
    if not str(v["en"]).strip():
        bad(f"{where}: '{field}.en' is empty", errs)
    if not str(v["es"]).strip():
        bad(f"{where}: '{field}.es' is empty", errs)
    if require_distinct and v.get("en") and v["en"] == v["es"]:
        bad(f"{where}: '{field}.es' is identical to EN — untranslated? "
            f"(\"{str(v['en'])[:50]}\")", errs)

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"error: {e}", file=sys.stderr); return 2

    errs, warns = [], []
    check_bilingual(data, "lastReviewed", "root", warns, require_distinct=False)

    # The tracker's whole credibility rests on its dates. index.html carries a
    # STATIC "Last reviewed" stamp that JS overwrites from this file at runtime —
    # so with JS the page is right while the served HTML can quietly disagree.
    # That drifted to a two-month-stale date once; crawlers and no-JS readers saw
    # it. Fail the check rather than let it happen silently again.
    import os, re as _re
    html_path = os.path.join(os.path.dirname(os.path.abspath(path)), "index.html")
    want = (data.get("lastReviewed") or {}).get("en")
    if want and os.path.isfile(html_path):
        html = open(html_path, encoding="utf-8").read()
        m = _re.search(r'id="tracker-reviewed"[^>]*>([^<]*)<', html)
        if not m:
            bad("index.html: no #tracker-reviewed stamp found", errs)
        else:
            static = m.group(1).replace("Last reviewed:", "").strip()
            if static != want:
                bad(f"index.html static stamp says {static!r} but tracker.json "
                    f"lastReviewed.en is {want!r} — no-JS readers and crawlers "
                    f"see the stale one", errs)

    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        bad("root: 'lanes' must be a non-empty array", errs)
        lanes = []

    n_entries = 0
    for li, lane in enumerate(lanes):
        where = f"lane[{li}]"
        check_bilingual(lane, "title", where, errs, require_distinct=True)
        entries = lane.get("entries")
        if not isinstance(entries, list) or not entries:
            bad(f"{where}: 'entries' must be a non-empty array", errs); continue
        for ei, e in enumerate(entries):
            n_entries += 1
            ew = f"lane[{li}].entry[{ei}]"
            st = e.get("status")
            if st not in STATUSES:
                bad(f"{ew}: status '{st}' not one of {sorted(STATUSES)}", errs)
            for f in BILINGUAL_TEXT:
                check_bilingual(e, f, ew, errs, require_distinct=True)
            for f in BILINGUAL_HTML:
                # body/means: ES identical to EN is only a warning (short shared
                # strings can legitimately match), everything else is an error.
                check_bilingual(e, f, ew, warns if False else errs,
                                require_distinct=True)

    print(f"tracker.json: {len(lanes)} lanes, {n_entries} entries")
    for w in warns:
        print(f"  note: {w}")
    if errs:
        print(f"\n{len(errs)} problem(s):")
        for e in errs:
            print(f"  ✗ {e}")
        return 1
    print("valid — every field bilingual, statuses known, no untranslated ES.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
