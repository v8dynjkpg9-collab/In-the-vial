# In The Vial — project guide

Buyer-literacy site for research peptides. *"The label is a claim. Learn to read the proof."*
Independent, evidence-graded, non-commercial: **nothing is sold, no vendor is linked, no dose is recommended.**

## Files

| File | What it is |
|---|---|
| `index.html` | The entire site — markup, CSS, and JS inline. ~210 KB. |
| `tracker.json` | Regulatory tracker content (5 lanes / 9 entries), bilingual `en`/`es` per field. |
| `fonts/` | Self-hosted woff2 (Instrument Serif, IBM Plex Sans/Mono), Latin + Latin-Ext. |

Single-page app: each section is a `.view` div toggled by JS. No build step, no dependencies, no backend.

## Hard rules

**1. Every English string needs a Spanish counterpart.**
Translations live in the `ES` map inside `<script>`, keyed to the *exact* English text. Editing an English string silently orphans its Spanish entry and that snippet falls back to English. When you change user-visible English, update its `ES` key in the same task. Dynamic strings live in `DYN`, not `ES`.

**2. Do not reintroduce third-party requests.**
Fonts are self-hosted deliberately. The privacy policy now promises *"Loading a page does not cause your browser to contact any outside company."* Adding a Google Fonts link, a CDN script, or an analytics tag makes that statement false. If analytics is ever added, the privacy section must be updated first.

**3. The tracker data exists in two places.**
`tracker.json` is the source of truth, fetched at runtime. A copy is also embedded inline in `index.html` (`<script id="tracker-data">`) as the fallback for `file://` and failed fetches. **Update both**, or the offline copy goes stale.

**4. Avoid generic CSS class names.**
`.tc` was defined twice — evidence-tier chip *and* test-guide table cell — and the later rule silently corrupted every TIER C chip. Tier chips are now scoped `.chip-tier.tc`, table cells `.trowg .tc`. Keep component styles scoped to their parent.

**5. Test at 390px before calling anything done.**
Check `document.documentElement.scrollWidth` vs `clientWidth` — they must match. Wide tables belong in `.ledger-wrap` (`overflow-x:auto`), never pushing the page wide.

## Architecture notes

- **Navigation** pushes real history entries (`pushState`), so back/forward and deep links like `#toolkit` work. Keep `href` attributes on nav elements — they're what makes the site keyboard-accessible and screen-reader-navigable; the delegated `preventDefault()` stops the jump.
- **Nav collapses to a hamburger below 760px**; the menu closes on navigation, outside tap, Escape, and viewport resize.
- **`renderTracker()` uses `innerHTML`** because tracker entries contain intentional `<strong>` tags. Only ever put first-party content in `tracker.json`. *(An older review note claiming the site has no `innerHTML` predates this and is no longer accurate.)*
- **`#tracker-lanes` is in the i18n `SKIP` list** — the render owns its own language, driven by `refreshDynamic()` on toggle.
- **Dose calculator** must keep the amber over-capacity warning when `units > 100`; a dose that can't physically be drawn in one pull must never render as if normal. This is a safety behavior, not a nicety.
- Illustrations are **inline SVG** — no requests, no 404s, sharp at any size.

## Design identity

Paper-and-ink investigative *case file*. Neutral ink, single muted rust accent reserved for the actual finding. Signature object: the **CASE FILE №ITV-001** dossier with rotated **UNVERIFIED** stamp. Serif display type, mono for labels/metadata. Don't add decorative color — the restraint is the point.

## Editorial stance

- Evidence tiers grade honestly: **A** approved/robust RCTs → **D** theoretical/anecdotal. Semaglutide is Tier A on purpose, as a calibration point proving the site is pro-evidence, not anti-peptide.
- Never add vendor links, "where to buy," affiliate codes, or dosing protocols. That is the entire premise.
- The tracker's credibility rests on real "last reviewed" dates — never auto-bump one. Automate *gathering*, keep a human on *publishing*.

## Deploy

`main` → connected static host (Cloudflare Pages) → auto-publishes on push. Build command is empty; output directory is `/`. Nothing to compile.

Local preview (needed so `fetch('tracker.json')` works):
```bash
python3 -m http.server 8142
```
