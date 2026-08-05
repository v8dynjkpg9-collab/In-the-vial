---
name: new-compound
description: Add a new compound page to the In The Vial science library (e.g. TB-500, CJC-1295, Epitalon). Use when adding a peptide to the site — covers the page markup, the residue-chain figure, routing, and the bilingual wiring so no step is missed.
---

# new-compound

Adding a compound touches **six** places in `in-the-vial/index.html`. Miss one and
routing breaks or the Spanish toggle silently shows English. Work through all six,
then verify. Model the new page on the existing BPC-157 / GHK-Cu / Semaglutide pages.

Pick a short **slug** (page id, e.g. `tb500`) and a **chain key** (e.g. `tb5`).

## 1. Science-library card

In the `#view-science` card grid, add an `<a class="ccard" href="#SLUG" data-view="SLUG">`
with: a `<span class="chip-tier tX">` tier chip (`ta` A / `tb` B / `tc` C / `td` D), a
`<div class="chainmini" data-chain="CHAINKEY-mini"></div>`, an `<h3>`, a one-line `<p>`,
and `<span class="go">Read the page →</span>`.

## 2. Compound page view

Add `<div class="view" id="view-SLUG">` modeled on an existing page. The anatomy:

- `<a class="backlink" href="#science" data-view="science">← Science library</a>`
- `<div class="chead"><h1>NAME</h1><span class="chip-tier tX">…TIER…</span></div>`
- `<p class="cdek">` one-paragraph deck.
- **Residue-chain plate** — `<div class="plate mol-plate">` with
  `<svg class="mol-svg" data-chain="CHAINKEY" role="img" aria-label="…">` and a
  `<div class="mol-readout" data-readout="CHAINKEY">…</div>`.
- **No figure.** Do *not* copy the `<figure class="figure">` block from the BPC-157 page — it is a
  bespoke COA illustration for that compound, not a reusable placeholder, and copying it ships wrong
  content plus 17 untranslated SVG labels. Add a figure only when a real asset for *this* compound
  exists.
- `<div class="spec">` grid — Class / Evidence tier / Human data / Regulatory status.
- `<div class="prose">` — `<h3 class="sh">` sections: What it is · How it's proposed
  to work · State of the evidence · Studied in humans vs. animals · Risks & unknowns ·
  Regulatory status · then the claims ledger.
- **The claims ledger must be wrapped:**
  `<div class="ledger-wrap"><table class="ledger">…</table></div>`. Unwrapped, the table pushes the
  page wider than the viewport on mobile. This is easy to miss because it only fails **in Spanish**,
  where the longer strings tip it over — English alone looks fine.
- Close with the "Verify this yourself" `<div class="callout">`.

Keep the honest, evidence-tiered tone; verdict cells use `vd vpart` / `vd vno` / `vd vok`.

## 3. Residue-chain data

In the `CHAINS` object in the script, add:

```js
'CHAINKEY':{ seq:'GEPPPGKPADDAGLV', hi:[0,14] },
```

`seq` is the one-letter amino-acid sequence (drawn as beads); `hi` is an array of
highlighted indices (usually the terminal residues `[0, len-1]`). Optional flags used
by the drawer: `copper:true` (adds a Cu²⁺ diamond), `tail:true` (fatty-acid tail),
`ellipsis:true` (a `···` truncation). The drawer names each residue on hover using the
`AA` (one-letter → English) and `AA_ES` (English → Spanish) maps — all 20 standard
amino acids are already covered.

## 4. Molecular readout string

Add the hover-plate readout to `DYN.mol`, both languages:

```js
CHAINKEY:{ en:'Hover any residue to read its amino acid. …', es:'Pasa el cursor …' },
```

## 5. Routing

Add the slug to `navMap` so the top nav highlights "Science" on this page:

```js
SLUG:'science'
```

## 6. Bilingual coverage (don't skip)

Every new visible English string must get an `ES` dictionary entry keyed by the exact
text, or it silently stays English in Spanish mode. After adding the page, run:

```bash
python3 .claude/skills/i18n-check/check_i18n.py in-the-vial/index.html
```

Add an `ES` entry for each real orphan it lists (brand names, units, and assay codes
are expected to stay English). See the [i18n-check](../i18n-check/SKILL.md) skill.

## Verify

> [!warning] Asserting on a hidden view measures nothing
> `.view{display:none}`, so a view that is not currently shown contributes **zero** to
> `document.documentElement.scrollWidth`. Checking the width on page load "passes" without ever
> testing the new page. **Navigate to the view first**, then assert — and do it in **both
> languages**, because Spanish strings run longer and overflow is as often a translation problem
> as a CSS one.


Run the [verify](../verify/SKILL.md) skill: JS syntax (the hook), i18n coverage, then
[preview](../preview/SKILL.md) and click the new card → page, hover the residue chain,
and toggle EN/ES.
