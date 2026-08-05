---
name: tracker
description: Add, edit, or validate entries in the In The Vial regulatory tracker (in-the-vial/tracker.json). Use when updating the tracker with a new FDA/regulatory development, changing a status, or checking the tracker data is well-formed before previewing.
---

# tracker

The regulatory tracker renders from `in-the-vial/tracker.json` — edit that file, not
the HTML. Every field is **bilingual** (`{ "en": ..., "es": ... }`), so each change
must be made in both languages.

## Data shape

```json
{
  "lastReviewed": { "en": "June 2026", "es": "junio de 2026" },
  "lanes": [
    {
      "title": { "en": "GLP-1 enforcement", "es": "Aplicación sobre GLP-1" },
      "entries": [
        {
          "title":       { "en": "...", "es": "..." },
          "status":      "closed",
          "statusLabel": { "en": "Closed", "es": "Cerrado" },
          "body":        { "en": "...<strong>date</strong>...", "es": "..." },
          "means":       { "en": "<strong>What it means:</strong> ...", "es": "<strong>Qué significa:</strong> ..." },
          "meta":        { "en": "Updated June 2026 · Source: ...", "es": "Actualizado junio de 2026 · Fuente: ..." }
        }
      ]
    }
  ]
}
```

- **`status`** must be one of: `live`, `pending`, `flux`, `closed` — this is the CSS
  pill color. `statusLabel` is the separate visible text (e.g. status `live` with
  label "Ongoing" or "In effect").
- **`body`** and **`means`** may contain inline `<strong>`; other tags aren't styled.
- Keep `meta` in the form `Updated <month year> · Source: <source>`.

## Add or edit an entry

1. Edit `in-the-vial/tracker.json`. Add the entry to the right lane (or add a new lane
   object). Fill **both** `en` and `es` for every field.
2. If the review date changed, bump `lastReviewed` (both languages).
3. Validate (below). Then preview with the [preview](../preview/SKILL.md) skill and
   toggle EN/ES to confirm the new row reads correctly in both.

## Validate

```bash
python3 .claude/skills/tracker/validate_tracker.py in-the-vial/tracker.json
```

It checks every field is bilingual and non-empty, every `status` is known, and flags
any `es` that is identical to its `en` (an untranslated fallback). Exit 0 = valid,
1 = problems, 2 = parse error.

## Notes

- The tracker loads via `fetch`, so it only renders over the http preview server, not
  `file://`. See [preview](../preview/SKILL.md).
- This file is the seam for future automation: a scheduled job can regenerate
  `tracker.json` and this validator can gate it. Never auto-publish regulatory claims
  without human review.
