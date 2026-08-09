#!/usr/bin/env bash
# Render og-image.png from scripts/og/template.html.
#
# The link-preview card is the one raster image on this site. It is AUTHORED —
# built from the site's own tokens, type and dossier markup — not generated, so
# it can be rebuilt exactly and reviewed like any other source file. A PNG in a
# repo with no way to regenerate it is a dead end the moment the wordmark or a
# colour changes.
#
# Output is 2x (2400x1260) for a 1200x630 card, which is what retina timelines
# and Slack unfurls want. Nothing here is loaded by readers — only by scrapers —
# so its weight does not touch page load.
#
#   bash scripts/og/build.sh

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

OUT=og-image.png
TEMPLATE=scripts/og/template.html

# Chrome ships under a couple of names; take the first that exists.
CHROME=""
for c in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Google Chrome 2.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"; do
  [ -x "$c" ] && CHROME="$c" && break
done

if [ -z "$CHROME" ]; then
  echo "No Chromium-based browser found. Install Chrome, or render" >&2
  echo "$TEMPLATE at 1200x630 by hand and save it as $OUT." >&2
  exit 1
fi

# The template loads fonts by relative path, so it must be rendered from its own
# directory for ../../fonts to resolve.
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=1200,630 \
  --screenshot="$PWD/$OUT" "file://$PWD/$TEMPLATE" 2>/dev/null

if [ ! -f "$OUT" ]; then
  echo "render failed — no $OUT produced" >&2
  exit 1
fi

read -r W H < <(sips -g pixelWidth -g pixelHeight "$OUT" 2>/dev/null \
  | awk '/pixelWidth/{w=$2} /pixelHeight/{h=$2} END{print w, h}')

if [ "$W" != "2400" ] || [ "$H" != "1260" ]; then
  echo "unexpected size ${W}x${H} — expected 2400x1260" >&2
  exit 1
fi

printf 'wrote %s (%sx%s, %s bytes)\n' "$OUT" "$W" "$H" "$(wc -c <"$OUT" | tr -d ' ')"
echo 'If the wordmark, tagline or palette changed, re-check the card before committing.'
