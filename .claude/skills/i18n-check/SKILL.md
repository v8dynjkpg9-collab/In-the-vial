---
name: i18n-check
description: Check the In The Vial site for untranslated strings — visible English text that has no entry in the ES dictionary and will silently fall back to English when the page is switched to Spanish. Use after editing any English copy in in-the-vial/index.html, before previewing.
---

# i18n-check

The site translates to Spanish by walking every visible text node and looking its
trimmed value up in the `ES` dictionary (`var ES={...}` in the inline script). Any
visible string that isn't a key in `ES` — and isn't inside a `SKIP` selector —
stays English when the user toggles to Spanish. Editing an English string therefore
silently orphans its old translation.

## When to run

- After editing, adding, or moving any visible English copy in `in-the-vial/index.html`.
- Before previewing or shipping a change that touched text.

## How to run

From the project root:

```bash
python3 .claude/skills/i18n-check/check_i18n.py in-the-vial/index.html
```

Exit code `0` = full coverage, `1` = untranslated strings found, `2` = parse error.

## Reading the output

It prints the ES key count, the visible-text-node count, and every visible string
with no ES entry.

Not every listed string is a bug — brand names (`In The Vial`, `BPC-157`,
`Semaglutide`), units (`mg`, `mL`, `mcg`), and assay abbreviations (`HPLC`,
`LC-MS/MS`, `ICP-MS`) are intentionally left in English. Focus on real prose that
should have a Spanish version.

## Fixing a gap

For each real orphan, add an entry to the `ES` object in `in-the-vial/index.html`,
keyed by the **exact** English string:

```js
'The exact English text':'La traducción exacta al español',
```

Then re-run the check to confirm the count dropped, and (optionally) the
[preview](../preview/SKILL.md) skill to eyeball the Spanish toggle.
