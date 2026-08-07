#!/usr/bin/env python3
"""Check that a page route is registered in all three places it has to live.

A route exists in ROUTES (index.html), _redirects, and sitemap.xml. Miss the
_redirects line and the page still works while you click around — it only 404s
on a refresh or a shared link, which is exactly the test nobody runs. This is
the check that catches it.

Usage: python3 .claude/skills/verify/check_routes.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX = ROOT / "index.html"
REDIRECTS = ROOT / "_redirects"
SITEMAP = ROOT / "sitemap.xml"
ORIGIN = "https://in-the-vial.com"

problems = []
notes = []


def fail(msg):
    problems.append(msg)


def parse_routes(html):
    """Pull slug/view/copy out of the ROUTES literal without executing JS."""
    block = re.search(r"var ROUTES=\[(.*?)\n  \];", html, re.S)
    if not block:
        sys.exit("could not locate the ROUTES array in index.html")

    routes = []
    for chunk in block.group(1).split("{slug:")[1:]:
        slug = re.match(r"'([^']*)'", chunk)
        view = re.search(r"view:'([^']*)'", chunk)
        if not slug or not view:
            fail("a ROUTES entry is missing slug or view")
            continue
        routes.append({
            "slug": slug.group(1),
            "view": view.group(1),
            "titles": len(re.findall(r"title:'", chunk)),
            "descs": len(re.findall(r"desc:'", chunk)),
        })
    return routes


html = INDEX.read_text(encoding="utf-8")
routes = parse_routes(html)
if not routes:
    sys.exit("no routes parsed out of index.html")

slugs = [r["slug"] for r in routes]
dupes = {s for s in slugs if slugs.count(s) > 1}
if dupes:
    fail("duplicate slugs in ROUTES: %s" % ", ".join(sorted(dupes)))

for r in routes:
    # Nesting silently breaks url(fonts/…) and fetch('tracker.json'), which are
    # relative and resolve against the document base.
    if r["slug"] != "/" and r["slug"].count("/") != 1:
        fail("slug %s is nested — flat, single-segment slugs only" % r["slug"])
    if not r["slug"].startswith("/"):
        fail("slug %s does not start with /" % r["slug"])
    if '<div class="view" id="view-%s">' % r["view"] not in html and \
       '<div class="view on" id="view-%s">' % r["view"] not in html:
        fail("route %s points at view-%s, which is not in the markup"
             % (r["slug"], r["view"]))
    # Both languages, both fields — the Spanish half has to be indexable too.
    if r["titles"] != 2 or r["descs"] != 2:
        fail("route %s needs an en AND es title and desc (found %d titles, %d descs)"
             % (r["slug"], r["titles"], r["descs"]))

# ---- _redirects -------------------------------------------------------------
rewrites, permanent = {}, {}
for raw in REDIRECTS.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    parts = line.split()
    if len(parts) != 3:
        fail("malformed _redirects line: %r" % raw)
        continue
    src, dst, code = parts
    (rewrites if code == "200" else permanent)[src] = dst

for r in routes:
    if r["slug"] == "/":
        continue  # index.html is served at / directly; no rule needed
    # Target must be "/" — proxying to "/index.html" inherits the asset
    # server's 307 canonicalisation and sends every deep link to the homepage.
    target = rewrites.get(r["slug"])
    if target == "/index.html":
        fail("%s proxies to /index.html, which 307s to / — use `%s / 200`"
             % (r["slug"], r["slug"]))
    elif target != "/":
        fail("%s has no `%s / 200` line in _redirects — it will 404 on refresh"
             % (r["slug"], r["slug"]))
    if permanent.get(r["slug"] + "/") != r["slug"]:
        fail("%s/ has no 301 to %s in _redirects — a trailing slash would move "
             "the document base and break relative asset paths"
             % (r["slug"], r["slug"]))

for src in rewrites:
    if src not in slugs:
        fail("_redirects rewrites %s, which is not a route in ROUTES" % src)
if "/api/*" in rewrites or "/*" in rewrites:
    fail("_redirects contains a catch-all or an /api/* rule — /api/* belongs to "
         "the Worker, and a catch-all can shadow tracker.json and the fonts")

# ---- sitemap.xml ------------------------------------------------------------
locs = set(re.findall(r"<loc>([^<]+)</loc>", SITEMAP.read_text(encoding="utf-8")))
for r in routes:
    for lang_url in (ORIGIN + r["slug"],
                     ORIGIN + r["slug"] + ("?lang=es" if r["slug"] != "/" else "/?lang=es")):
        url = lang_url.replace("//?lang=es", "/?lang=es")
        if url not in locs:
            fail("sitemap.xml is missing %s" % url)

expected = len(routes) * 2
if len(locs) != expected:
    notes.append("sitemap has %d <loc> entries; %d routes x 2 languages = %d"
                 % (len(locs), len(routes), expected))

# ---- report -----------------------------------------------------------------
print("routes declared: %d" % len(routes))
for n in notes:
    print("  note: %s" % n)

if problems:
    print("\nFAIL — %d problem%s:" % (len(problems), "" if len(problems) == 1 else "s"))
    for p in problems:
        print("  • %s" % p)
    sys.exit(1)

print("ok — every route is in ROUTES, _redirects (rewrite + trailing-slash 301) "
      "and sitemap.xml in both languages")
