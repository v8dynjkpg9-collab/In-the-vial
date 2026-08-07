#!/usr/bin/env bash
# Every deterministic check on the site, in one command.
#
#   bash .claude/verify.sh
#
# Exits non-zero if anything is actually broken, so it can gate a deploy.
# Runnable from any directory. Checks are scripts, never agents — a script's
# output can be audited; an agent reporting "I ran the check" cannot.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

fail=0
section() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ok()      { printf '  ok    %s\n' "$1"; }
bad()     { printf '  FAIL  %s\n' "$1"; fail=1; }
note()    { printf '  note  %s\n' "$1"; }

# ---------------------------------------------------------------- JS syntax --
section "JavaScript syntax"
if out=$(bash .claude/hooks/js-syntax-check.sh index.html 2>&1); then
  ok "index.html inline script parses"
else
  bad "syntax error in index.html"; printf '%s\n' "$out" | sed 's/^/        /'
fi

# ------------------------------------------------------------------- routes --
section "Page routes (ROUTES / _redirects / sitemap.xml)"
if out=$(python3 .claude/skills/verify/check_routes.py 2>&1); then
  ok "$(printf '%s' "$out" | tail -1)"
else
  printf '%s\n' "$out" | sed 's/^/        /'
  bad "a route is not registered in all three places"
fi

# The Worker rewrites <head> from src/routes.js; the browser reads ROUTES from
# index.html. Drift means a page's head describes a different page than its body.
if out=$(python3 scripts/build-routes.py --check 2>&1); then
  ok "src/routes.js matches ROUTES in index.html"
else
  printf '%s\n' "$out" | sed 's/^/        /'
  bad "src/routes.js is stale — run: python3 scripts/build-routes.py"
fi

# ------------------------------------------------------------------ tracker --
section "Tracker schema"
if out=$(python3 .claude/skills/tracker/validate_tracker.py tracker.json 2>&1); then
  ok "$(printf '%s' "$out" | tail -1)"
else
  printf '%s\n' "$out" | sed 's/^/        /'
  bad "tracker.json is invalid"
fi

# The inline copy in index.html is the file:// and failed-fetch fallback. If it
# drifts from tracker.json, offline readers silently get stale regulation.
if python3 - <<'PY'
import json, re, sys
inline = re.search(r'<script id="tracker-data" type="application/json">(.*?)</script>',
                   open('index.html', encoding='utf-8').read(), re.S)
if not inline:
    sys.exit(1)
sys.exit(0 if json.loads(inline.group(1)) == json.load(open('tracker.json', encoding='utf-8')) else 1)
PY
then
  ok "inline tracker copy matches tracker.json"
else
  bad "inline <script id=\"tracker-data\"> has drifted from tracker.json — update both"
fi

# ---------------------------------------------------------------- newsletter --
section "Newsletter"
if out=$(python3 newsletter/build.py --check 2>&1); then
  ok "worker/newsletter-content.js is current"
else
  printf '%s\n' "$out" | sed 's/^/        /'
  bad "newsletter-content.js is stale — deploying now would send the old issue"
fi

# ---------------------------------------------------------------------- i18n --
# Coverage is complete, so this gates on the exit code rather than on a delta
# against a baseline. The old baseline existed only because the checker counted
# 22 deliberately-English strings — brand, SI units, assay names — as orphans,
# which pinned the number at 29 forever. Those now live in
# intentionally-english.txt with their reasons, and the count means something.
section "Translation coverage"
if out=$(python3 .claude/skills/i18n-check/check_i18n.py index.html 2>&1); then
  ok "$(printf '%s' "$out" | grep -E 'intentionally English|untranslated' | tr '\n' ' ' | tr -s ' ')"
else
  printf '%s\n' "$out" | sed -n '/^These\|^  •\|^  x/p' | head -20 | sed 's/^/        /'
  bad "untranslated strings, a stale allowlist entry, or a duplicate ES key"
fi

# ------------------------------------------------------------ design system --
# Advisory only. Sprawl is discipline, not a defect, and must never block a fix.
section "Design scale (advisory)"
python3 .claude/skills/design-scale/audit_scale.py index.html 2>&1 \
  | grep -E '^\s+[a-z].*:\s+[0-9]+%' | sed 's/^ */  /' || true

# -------------------------------------------------------------------- result --
if [ "$fail" -ne 0 ]; then
  printf '\n\033[1mVERIFY FAILED\033[0m — fix the above before deploying.\n'
  exit 1
fi
printf '\n\033[1mVERIFY PASSED\033[0m\n'
printf 'Not covered here: how it looks. Check 390 / 768 / 1280px before calling it done.\n'
