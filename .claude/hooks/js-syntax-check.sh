#!/usr/bin/env bash
# Syntax-check the inline <script> of the In The Vial page with macOS JavaScriptCore.
# There is no Node in this environment, so jsc is the syntax checker.
#
# Two modes:
#   1. Manual:  bash js-syntax-check.sh in-the-vial/index.html
#   2. PostToolUse hook: reads JSON on stdin, extracts the edited file path, and
#      only acts when that file is in-the-vial/index.html.
#
# Exit 0 = OK (or not applicable). Exit 2 = syntax error (warns via the tool).

set -uo pipefail

JSC="/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc"

# --- resolve the target file -------------------------------------------------
FILE="${1:-}"
if [[ -z "$FILE" && ! -t 0 ]]; then
  INPUT="$(cat)"
  FILE="$(printf '%s' "$INPUT" | python3 -c 'import sys,json;
try:
    d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))
except Exception:
    print("")' 2>/dev/null)"
fi

# Only care about the site file. Match any path ending in index.html — the old
# guard required the literal "in-the-vial/" segment, so running the check on a
# bare "index.html" from inside the repo silently exited 0 and looked like a
# pass. A check that quietly skips is worse than no check.
case "$FILE" in
  *index.html) : ;;
  *) exit 0 ;;
esac
[[ -f "$FILE" ]] || exit 0

if [[ ! -x "$JSC" ]]; then
  echo "js-syntax-check: jsc not found; skipping" >&2
  exit 0
fi

# --- extract the last inline <script> block and parse it ---------------------
TMP="$(mktemp -t itv-script.XXXXXX.js)"
trap 'rm -f "$TMP"' EXIT

python3 - "$FILE" > "$TMP" <<'PY'
import sys, re
src = open(sys.argv[1], encoding="utf-8").read()
# Grab inline scripts, skipping any with src= AND any non-JavaScript type.
# The page carries <script id="tracker-data" type="application/json">, and
# concatenating that JSON into the JS raised a permanent bogus SyntaxError —
# a gate that is always red is a gate nobody reads.
blocks = []
for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", src, re.S | re.I):
    attrs, body = m.group(1), m.group(2)
    if re.search(r"\bsrc\s*=", attrs, re.I):
        continue
    t = re.search(r"\btype\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
    if t and t.group(1).strip().lower() not in (
        "text/javascript", "application/javascript", "module"
    ):
        continue
    blocks.append(body)
sys.stdout.write("\n;\n".join(blocks))
PY

ERR="$("$JSC" "$TMP" 2>&1)"
STATUS=$?

# jsc exits non-zero on runtime errors too; a ReferenceError for document/window
# just means the syntax parsed fine but the DOM isn't present. Only real parse
# errors ("SyntaxError") should fail the check.
if printf '%s' "$ERR" | grep -q "SyntaxError"; then
  echo "js-syntax-check: SyntaxError in $FILE" >&2
  printf '%s\n' "$ERR" | grep "SyntaxError" >&2
  exit 2
fi

exit 0
