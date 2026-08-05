#!/usr/bin/env python3
"""
Measure design-system discipline in the single-file site.

"Looks alright but not quite sophisticated" is usually not a taste problem —
it's scale sprawl. Near-duplicate values (13px / 13.5px / 14px / 14.5px) read
as sloppy without a viewer being able to name why. This makes that measurable
so it can be tracked instead of argued about.

Usage:  python3 audit_scale.py [index.html] [--json]
Exit 0 always (informational); use --strict to exit 1 when over budget.
"""
import sys, re, json, collections

# Budgets for a design this size. Deliberately generous — the point is to catch
# sprawl, not to enforce a single opinionated scale.
BUDGET = {
    "font-size":      10,
    "letter-spacing":  8,
    "line-height":     6,
    "spacing":        14,
    "border-radius":   4,
}

def css_of(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"<style[^>]*>(.*?)</style>", s, re.S)
    if not m:
        print(f"error: no <style> block in {path}", file=sys.stderr)
        raise SystemExit(2)
    return m.group(1)

def collect(css):
    out = {}
    out["font-size"] = collections.Counter(
        float(v) for v in re.findall(r"font-size\s*:\s*([\d.]+)px", css))
    out["letter-spacing"] = collections.Counter(
        re.findall(r"letter-spacing\s*:\s*([-\d.]+em)", css))
    out["line-height"] = collections.Counter(
        re.findall(r"line-height\s*:\s*([\d.]+)\b(?!px)", css))
    out["border-radius"] = collections.Counter(
        float(v) for v in re.findall(r"border-radius\s*:\s*([\d.]+)px", css))
    sp = []
    for m in re.finditer(r"(?:padding|margin|gap)[a-z-]*\s*:\s*([^;}]+)", css):
        sp += [float(x) for x in re.findall(r"([\d.]+)px", m.group(1))]
    out["spacing"] = collections.Counter(sp)
    return out

def neighbours(vals, floor=8.0, rel=0.12):
    """Values close enough to look like a mistake rather than a decision.

    Uses a RELATIVE threshold above a floor: 13px vs 14px (8% apart) reads as
    sloppy, while 1px vs 2px (a hairline vs a border) is obviously deliberate.
    An absolute tolerance flags the latter and buries the real signal.
    """
    nums = sorted(v for v in vals if isinstance(v, float) and v >= floor)
    return [(a, b) for a, b in zip(nums, nums[1:]) if 0 < (b - a) / a <= rel]

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else "index.html"
    as_json = "--json" in sys.argv
    strict = "--strict" in sys.argv

    data = collect(css_of(path))
    report, over = {}, False

    for key, counter in data.items():
        n = len(counter)
        budget = BUDGET[key]
        ok = n <= budget
        over = over or not ok
        top = sorted(counter.items(), key=lambda x: -x[1])[:8]
        report[key] = {
            "distinct": n, "budget": budget, "within_budget": ok,
            "most_used": [[str(v), c] for v, c in top],
            "near_duplicates": [[a, b] for a, b in neighbours(counter.keys())],
        }

    grid = sum(c for v, c in data["spacing"].items() if v % 4 == 0)
    total = sum(data["spacing"].values()) or 1
    report["grid_discipline_pct"] = round(100 * grid / total)

    if as_json:
        print(json.dumps(report, indent=2))
        return 1 if (strict and over) else 0

    print(f"Design scale audit — {path}\n")
    for key in ("font-size", "letter-spacing", "line-height", "spacing", "border-radius"):
        r = report[key]
        mark = "ok  " if r["within_budget"] else "OVER"
        print(f"  [{mark}] {key:<15} {r['distinct']:>3} distinct  (budget {r['budget']})")
        if r["near_duplicates"]:
            pairs = ", ".join(f"{a:g}/{b:g}" for a, b in r["near_duplicates"][:6])
            print(f"         near-duplicates a viewer reads as sloppy: {pairs}")
    print(f"\n  spacing on a 4px grid: {report['grid_discipline_pct']}%")
    if over:
        print("\n  Consolidating near-duplicates onto one scale is the single highest-leverage")
        print("  change for perceived polish. Nothing here is a bug — it is discipline.")
    return 1 if (strict and over) else 0

if __name__ == "__main__":
    sys.exit(main())
