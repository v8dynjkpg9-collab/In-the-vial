---
name: verify
description: Verify a change to the In The Vial site actually works — syntax-check the JS, check translation coverage, and confirm behavior in a browser. Use before calling a change done.
---

# verify

A short checklist to confirm an edit to `in-the-vial/index.html` is actually sound,
given the environment has no Node.

## Steps

1. **JS syntax** — parse the inline script with macOS JavaScriptCore. A `PostToolUse`
   hook already runs this automatically after every edit; to run it by hand:

   ```bash
   bash .claude/hooks/js-syntax-check.sh in-the-vial/index.html
   ```

   A valid file reports no syntax error (a `ReferenceError: document` when executed
   is expected — it means the syntax parsed and only failed at runtime outside a
   browser).

2. **Translation coverage** — if you touched copy, run the
   [i18n-check](../i18n-check/SKILL.md) skill and resolve any real orphans.

3. **Behavior in a browser** — use the [preview](../preview/SKILL.md) skill and
   confirm the specific thing you changed:
   - Language toggle flips EN ↔ ES (including dynamic strings).
   - The [dose calculator](../../..) over-100-units warning still fires (try
     2 mg / 2 mL / 1200 mcg → should warn).
   - No console errors on load.

## Definition of done

Syntax clean, no untranslated real prose, the changed behavior confirmed live, and
no console errors.
