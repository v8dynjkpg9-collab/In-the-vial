#!/usr/bin/env python3
"""Extract the ROUTES table from index.html into src/routes.js for the Worker.

index.html stays the single source of truth: it has to work standalone, opened
straight off disk, with no build step. But the Worker needs the same titles and
descriptions to rewrite <head> server-side, and two hand-maintained copies of
the same table would drift the first time someone edits one — silently, because
the browser would still show the right thing.

So: generate, and let verify.sh gate the drift.

Extraction runs the literal through node rather than regex, so quoting and
escapes are the JS engine's problem, not ours.

Usage:
    python3 scripts/build-routes.py            # write src/routes.js
    python3 scripts/build-routes.py --check    # exit 1 if out of date
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "src" / "routes.js"

HEADER = """// GENERATED — do not edit. Source: the ROUTES table in index.html.
// Rebuild with: python3 scripts/build-routes.py
//
// The browser reads ROUTES from index.html; the Worker reads this. They must
// agree, or a page's <head> would describe a different page than its body.
"""


def extract():
    html = INDEX.read_text(encoding="utf-8")
    block = re.search(r"var ORIGIN='([^']*)';\s*var ROUTES=(\[.*?\n  \]);", html, re.S)
    if not block:
        sys.exit("could not find ORIGIN and ROUTES in index.html")
    origin, literal = block.group(1), block.group(2)

    # Let node parse it — the literal is JS, not JSON.
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False,
                                     encoding="utf-8") as fh:
        fh.write("console.log(JSON.stringify(%s));" % literal)
        script = fh.name
    try:
        proc = subprocess.run(["node", script], capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("node is required to parse the ROUTES literal (brew install node)")
    finally:
        pathlib.Path(script).unlink(missing_ok=True)

    if proc.returncode != 0:
        sys.exit("could not parse the ROUTES literal:\n" + proc.stderr.strip())

    routes = json.loads(proc.stdout)
    for r in routes:
        for key in ("slug", "view"):
            if not r.get(key):
                sys.exit("a route is missing %s" % key)
        for lang in ("en", "es"):
            copy = r.get(lang) or {}
            if not copy.get("title") or not copy.get("desc"):
                sys.exit("route %s is missing a %s title or desc" % (r["slug"], lang))
    return origin, routes


def render(origin, routes):
    return (HEADER
            + "\nexport const ORIGIN = %s;\n\nexport const ROUTES = %s;\n"
            % (json.dumps(origin), json.dumps(routes, indent=2, ensure_ascii=False)))


def main():
    origin, routes = extract()
    rendered = render(origin, routes)
    OUT.parent.mkdir(exist_ok=True)

    current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if current == rendered:
        print("src/routes.js is up to date (%d routes)" % len(routes))
        return 0
    if "--check" in sys.argv:
        print("src/routes.js is STALE — run: python3 scripts/build-routes.py")
        print("The Worker would serve <head> metadata for the wrong page.")
        return 1
    OUT.write_text(rendered, encoding="utf-8")
    print("wrote src/routes.js (%d routes)" % len(routes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
