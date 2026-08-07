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
import sys, re, html, pathlib
from html.parser import HTMLParser

DEFAULT = "in-the-vial/index.html"
ALLOWLIST = pathlib.Path(__file__).resolve().parent / "intentionally-english.txt"


def load_allowlist():
    """Strings that are deliberately English — brand, units, assay names.

    Kept in a file rather than inline so each decision carries its reasoning,
    and so the list is reviewable on its own.
    """
    if not ALLOWLIST.exists():
        return set()
    out = set()
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out
VOID = {"area","base","br","col","embed","hr","img","input","link",
        "meta","param","source","track","wbr"}

def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def extract_es_keys(src):
    """Pull the keys of the `var ES={...}` object literal.

    This scans the literal rather than regex-matching "'...' followed by :".
    That pattern desynchronises on a key which itself begins with a colon —
    it matches the ",\\n    " between two entries as the key and swallows the
    real one, which then reports as an untranslated orphan that is in fact
    translated. Inline <em>/<strong> tags split sentences, so fragments
    starting with punctuation are normal here, not exotic.

    Keys are string literals in value position after `{` or `,` at depth 0.
    """
    start = src.find("var ES={")
    if start == -1:
        raise ValueError("could not find `var ES={` in the file")
    i = src.index("{", start)
    end = src.find("var SKIP", start)
    block = src[i:end if end != -1 else len(src)]

    keys = []
    depth = 0
    expect_key = False
    pos = 0
    n = len(block)
    while pos < n:
        ch = block[pos]
        if ch == "/" and pos + 1 < n and block[pos + 1] == "*":     # /* comment */
            close = block.find("*/", pos + 2)
            pos = n if close == -1 else close + 2
            continue
        if ch == "/" and pos + 1 < n and block[pos + 1] == "/":     # // comment
            nl = block.find("\n", pos)
            pos = n if nl == -1 else nl + 1
            continue
        if ch in "'\"":
            quote, buf, pos = ch, [], pos + 1
            while pos < n and block[pos] != quote:
                if block[pos] == "\\" and pos + 1 < n:              # \' \" \\ \n
                    nxt = block[pos + 1]
                    buf.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
                    pos += 2
                    continue
                buf.append(block[pos])
                pos += 1
            pos += 1                                                # closing quote
            if expect_key and depth == 1:
                keys.append("".join(buf))
                expect_key = False
            continue
        if ch == "{":
            depth += 1
            expect_key = depth == 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        elif ch == "," and depth == 1:
            expect_key = True
        pos += 1
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
        key_list = extract_es_keys(src)
        keys = set(key_list)
        skip_ids, skip_classes = extract_skip(src)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    body_start = src.find("<body")
    w = Walker(skip_ids, skip_classes)
    w.feed(src[body_start:] if body_start != -1 else src)

    allowed = load_allowlist()
    missing, intentional = [], []
    seen = set()
    for s in w.strings:
        if s in seen:
            continue
        seen.add(s)
        if not re.search(r"[A-Za-z]", s):   # skip pure punctuation / numbers
            continue
        if len(s) < 2:
            continue
        if s in keys:
            continue
        (intentional if s in allowed else missing).append(s)

    # An allowlist entry for a string that is no longer on the page is dead
    # weight, and worse: if that text comes back in a different context it is
    # excused without anyone deciding to excuse it.
    stale = sorted(allowed - seen)

    # A duplicated key is silent: the object literal keeps the last one, so two
    # copies behave identically right up until someone edits one of them and
    # cannot work out why the change had no effect.
    dupes = {}
    for k in key_list:
        dupes[k] = dupes.get(k, 0) + 1
    dupes = {k: c for k, c in dupes.items() if c > 1}

    total = len(seen)
    print(f"ES dictionary keys:      {len(keys)}")
    print(f"visible text nodes:      {total}")
    print(f"intentionally English:   {len(intentional)}")
    print(f"untranslated (fallback): {len(missing)}")
    print(f"duplicate ES keys:       {len(dupes)}\n")

    if missing:
        print("These visible strings have no ES entry and stay English when "
              "the site is switched to Spanish:\n")
        for s in missing:
            disp = s if len(s) <= 100 else s[:97] + "..."
            print(f"  • {disp}")
        print(f"\nAdd each to the `ES` object in {path}, or — if it should stay "
              f"English — to\n{ALLOWLIST.name} with the reason.")
    if stale:
        print("\nThese allowlist entries are no longer on the page. Remove them, "
              "or they will\nsilently excuse the same text if it reappears "
              "somewhere it should be translated:\n")
        for s in stale:
            print(f"  • {s}")
    if dupes:
        print("\nThese ES keys appear more than once. The literal silently keeps "
              "the last, so\nediting an earlier copy changes nothing:\n")
        for k, c in sorted(dupes.items()):
            disp = k if len(k) <= 80 else k[:77] + "..."
            print(f"  • x{c}  {disp}")
    if missing or stale or dupes:
        return 1

    print("Full coverage — every visible string is translated or "
          "deliberately English.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
