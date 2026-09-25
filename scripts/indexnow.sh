#!/usr/bin/env bash
# Tell IndexNow-consuming search engines that this site's URLs changed.
#
# Bing, Yandex, Seznam and Naver consume IndexNow; Bing also backs DuckDuckGo
# and Ecosia. Google does NOT participate — Google needs Search Console, which
# requires signing in and therefore a human.
#
# Unlike Search Console this needs no account: ownership is proved by hosting
# a key file at the site root whose filename IS the key. That file must stay
# published — delete it and every future submission is rejected.
#
# The URL list comes from sitemap.xml so the two can never disagree.
#
#   bash scripts/indexnow.sh            # submit every sitemap URL
#   bash scripts/indexnow.sh --dry-run  # show the payload, send nothing

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

HOST=in-the-vial.com
KEYFILE=$(ls -1 [0-9a-f]*.txt 2>/dev/null | head -1)
[ -z "$KEYFILE" ] && { echo "no IndexNow key file at the repo root" >&2; exit 1; }
KEY=${KEYFILE%.txt}

URLS=$(grep -oE '<loc>[^<]+</loc>' sitemap.xml | sed 's/<[^>]*>//g')
COUNT=$(printf '%s\n' "$URLS" | grep -c .)

PAYLOAD=$(python3 - "$HOST" "$KEY" <<PY
import json,sys,subprocess
urls=[l for l in subprocess.run(["grep","-oE","<loc>[^<]+</loc>","sitemap.xml"],
      capture_output=True,text=True).stdout.splitlines()]
urls=[u.replace("<loc>","").replace("</loc>","") for u in urls]
print(json.dumps({"host":sys.argv[1],"key":sys.argv[2],
  "keyLocation":"https://%s/%s.txt"%(sys.argv[1],sys.argv[2]),"urlList":urls}))
PY
)

if [ "${1:-}" = "--dry-run" ]; then
  printf '%s\n' "$PAYLOAD" | python3 -m json.tool
  echo "dry run — $COUNT urls, nothing sent"
  exit 0
fi

# The key file must be live BEFORE submitting, or the endpoint returns 403.
live=$(curl -s -o /dev/null -w '%{http_code}' "https://$HOST/$KEY.txt")
[ "$live" != "200" ] && { echo "key file not reachable (HTTP $live) — deploy first" >&2; exit 1; }

code=$(curl -s -o /tmp/indexnow.out -w '%{http_code}' -X POST "https://api.indexnow.org/indexnow" \
  -H "Content-Type: application/json; charset=utf-8" --data "$PAYLOAD")
echo "submitted $COUNT urls -> HTTP $code"
# A 202 returns an empty body, so anything that tests the body for content must
# not decide the exit status — this script reported failure on success once.
[ -s /tmp/indexnow.out ] && head -c 300 /tmp/indexnow.out
case "$code" in
  200|202) echo "accepted (202 means queued, which is normal)"; exit 0;;
  400) echo "bad request — check the payload" >&2; exit 1;;
  403) echo "key not valid: the key file must be live and match" >&2; exit 1;;
  422) echo "urls do not belong to the host, or key mismatch" >&2; exit 1;;
  429) echo "too many requests — submit less often" >&2; exit 1;;
  *)   echo "unexpected response" >&2; exit 1;;
esac
