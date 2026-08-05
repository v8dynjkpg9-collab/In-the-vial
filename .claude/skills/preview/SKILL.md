---
name: preview
description: Launch a local preview of the In The Vial site and open it in the browser. Use when asked to preview, run, serve, or look at the site after a change.
---

# preview

Serve `in-the-vial/index.html` locally and open it so changes can be seen in a real
browser. The site is a single self-contained file, but previewing it over http (not
file://) is required for the language toggle's localStorage and for any future
`tracker.json` fetch.

## Preferred: the preview MCP

If the Claude Preview tools are available, start the server defined in
`.claude/launch.json` (config name **in-the-vial**, port **8142**) and open it.
That config already does `cd in-the-vial && python3 -m http.server 8142`.

## Fallback: manual server

The macOS sandbox can block serving directly from the iCloud folder. If the direct
server fails, copy the file into the session scratchpad and serve from there:

```bash
cp in-the-vial/index.html "$SCRATCHPAD/index.html"
python3 -m http.server -d "$SCRATCHPAD" 8142
```

Then open `http://localhost:8142/index.html`.

## After previewing

- Toggle EN/ES and confirm the language button and dynamic strings switch.
- If you edited copy, run the [i18n-check](../i18n-check/SKILL.md) skill first.
- Stop the server when done.
