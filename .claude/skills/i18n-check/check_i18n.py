#!/usr/bin/env python3
"""
i18n coverage check for the In The Vial site.

The page translates to Spanish by walking every visible text node and looking
its trimmed value up in the `ES` dictionary. Any visible string that is NOT a
key in `ES` (and is not inside a SKIP selector) silently falls back to English
when the user switches to ES. This script finds those strings so an English
edit never quietly orphans its translation.

Usage:  python3 check_i18n.py [path/to/index.html]
Exit code 0 = full coverage, 1 = untranslated strings found, 2 = parse error.
"""
import sys, re, html
from html.parser import HTMLParser

DEFAULT = "in-the-vial/index.html"
VOID = {"area","base","br","col","embed","hr","img","input","link",
        "meta","param","source","track","wbr"}

def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def extract_es_keys(src):
    """Pull the keys of the `var ES={...}` object literal."""
    start = src.find("var ES={")
    if start == -1:
        raise ValueError("could not find `var ES={` in the file")
    # ES is the last translation object before `var SKIP=`
    end = src.find("var SKIP", start)
    block = src[start:end if end != -1 else len(src)]
    # keys are single-quoted strings immediately followed by a colon
    key_re = re.compile(r"'((?:[^'\\]|\\.)*)'\s*:")
    keys = set()
    for m in key_re.finditer(block):
        raw = m.group(1)
        # unescape \' and \\ the way JS would read the literal
        keys.add(raw.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\"))
    return keys

def extract_skip(src):
    """Parse the runtime SKIP list.

    Only simple `#id` and `.class` selectors are understood here. The browser
    evaluates SKIP with the real CSS engine, so a compound selector like
    `.refs ol` works at runtime but matches NOTHING in this checker — which
    silently reports every skipped string as an orphan. Unsupported selectors
    are surfaced rather than ignored, because a checker that quietly disagrees
    with the runtime is worse than no checker.
    """
    m = re.search(r"var SKIP\s*=\s*'([^']*)'", src)
    ids, classes, unsupported = set(), set(), []
    if m:
        for sel in m.group(1).split(","):
            sel = sel.strip()
            if not sel:
                continue
            if re.fullmatch(r"#[\w-]+", sel):
                ids.add(sel[1:])
            elif re.fullmatch(r"\.[\w-]+", sel):
                classes.add(sel[1:])
            else:
                unsupported.append(sel)
    if unsupported:
        print("warning: SKIP selectors this checker cannot evaluate "
              "(they work in the browser but are ignored here, so their "
              "contents will be reported as orphans):", file=sys.stderr)
        for sel in unsupported:
            print(f"  {sel}   -> use a single class/id instead", file=sys.stderr)
    return ids, classes

class Walker(HTMLParser):
    def __init__(self, skip_ids, skip_classes):
        super().__init__(convert_charrefs=True)
        self.skip_ids, self.skip_classes = skip_ids, skip_classes
        self.stack = []          # list of (tag, id, {classes})
        self.strings = []        # collected visible text nodes

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        a = dict(attrs)
        self.stack.append((tag, a.get("id"),
                           set((a.get("class") or "").split())))

    def handle_startendtag(self, tag, attrs):
        pass  # self-closed, nothing to push

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def _in_skip(self):
        for _, eid, cls in self.stack:
            if eid and eid in self.skip_ids:
                return True
            if cls & self.skip_classes:
                return True
        return False

    def handle_data(self, data):
        if any(t[0] in ("script", "style") for t in self.stack):
            return
        if not data.strip():
            return
        if self._in_skip():
            return
        self.strings.append(data.strip())

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    try:
        src = load(path)
        keys = extract_es_keys(src)
        skip_ids, skip_classes = extract_skip(src)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    body_start = src.find("<body")
    w = Walker(skip_ids, skip_classes)
    w.feed(src[body_start:] if body_start != -1 else src)

    missing = []
    seen = set()
    for s in w.strings:
        if s in seen:
            continue
        seen.add(s)
        if not re.search(r"[A-Za-z]", s):   # skip pure punctuation / numbers
            continue
        if len(s) < 2:
            continue
        if s not in keys:
            missing.append(s)

    total = len(seen)
    print(f"ES dictionary keys:      {len(keys)}")
    print(f"visible text nodes:      {total}")
    print(f"untranslated (fallback): {len(missing)}\n")
    if missing:
        print("These visible strings have no ES entry and stay English when "
              "the site is switched to Spanish:\n")
        for s in missing:
            disp = s if len(s) <= 100 else s[:97] + "..."
            print(f"  • {disp}")
        print(f"\nAdd each to the `ES` object in {path} to close the gap.")
        return 1
    print("Full coverage — every visible string has an ES translation.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
