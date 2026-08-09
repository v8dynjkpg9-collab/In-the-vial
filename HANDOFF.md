# Handoff — current state of In The Vial

**Updated 2026-08-09 · HEAD `7c13560`**

This file exists so a reviewer with no prior context can pick the project up without anyone
pasting a transcript. It describes the project **as it is now**, not a changelog — `git log`
is the changelog, and the commit messages carry the reasoning.

Publicly readable, no account needed:
<https://github.com/v8dynjkpg9-collab/In-the-vial/blob/main/HANDOFF.md>

*(Add `?plain=1` for the unrendered source, or swap the host for
`raw.githubusercontent.com` and drop `/blob` if a tool needs plain text.)*

It is in `.assetsignore`, so it is not served on the website.

**Rewrite this file at the end of any session that changes how the project works.** Replace
sections rather than appending; a handoff that grows into a log stops being useful.

---

## What this is

`in-the-vial.com` — an independent, non-commercial buyer-literacy site about research
peptides. *"The label is a claim. Learn to read the proof."* Evidence-graded A–D, fully
bilingual EN/ES. Nothing is sold, no vendor is linked, no dose is recommended.

Read `CLAUDE.md` before proposing changes. It holds the hard rules and, more usefully, the
reasons behind them.

## Architecture in one pass

| Piece | Reality |
|---|---|
| Site | **One** `index.html` (~300 KB, markup + CSS + JS inline). No build step, no dependencies. |
| Hosting | Cloudflare **Worker** `in-the-vial`, static assets + Git integration. **Not Pages** — `wrangler pages project list` is empty. |
| Deploy | Push to `main` → auto-publishes in **~40 s**. No branch preview URLs exist. |
| Routing | 12 real page routes via `_redirects`; `src/index.js` rewrites `<head>` per route. |
| API | Separate Worker `in-the-vial-subscribe` on `in-the-vial.com/api/*`. **Deploys manually only.** |
| Storage | KV namespace `SUBS`. No D1, no R2. |
| Checks | `bash .claude/verify.sh` — 8 gates, exits non-zero. |

## Current state

- **12 routes live**, all 200, each with its own title/description in both languages,
  server-rendered so scrapers see them.
- **Spanish coverage is complete** — `check_i18n.py` reports 0 untranslated, 0 duplicate keys.
  22 strings are deliberately English (brand, SI units, assay names) and listed with reasons
  in `.claude/skills/i18n-check/intentionally-english.txt`.
- **Newsletter issue 001 was sent for real on 2026-08-09** — 3/3 subscribers, 0 failures.
  First send in the project's history. Idempotency verified in production: re-running now
  reports `alreadySent: 3, wouldSend: 0`.
- **Security headers live** — CSP with `default-src 'self'`, HSTS, `Referrer-Policy:
  no-referrer`, Permissions-Policy, frame/CORP/COOP. Verified by probe: an external `fetch`
  and a Google Fonts stylesheet are both blocked; `fetch('tracker.json')` still returns 200.
- **Link previews have a card** — `og-image.png`, authored from the site's own type and
  dossier markup, not AI-generated.
- Subscribers: **3** — one real reader, plus `+en` and `+es` aliases used for testing.

## Traps that will waste your time

Every one of these cost real time in the last session. They all fail **silently**.

1. **`npx wrangler deploy` from `worker/` deploys the WRONG Worker.** The site Worker's
   `wrangler.jsonc` sits at the repo root and wrangler resolves it even from inside `worker/`.
   Use `npx wrangler deploy --config wrangler.toml`. Dry-run first: bindings must be
   `env.SUBS` + `env.EMAIL`. If you see `env.ASSETS`, stop.
2. **`wrangler secret put` has the same failure**, and reports success. Always
   `--name in-the-vial-subscribe`. Read the Worker name in its output.
3. **`_redirects` must proxy to `/`, never `/index.html`.** Workers static assets
   canonicalises `/index.html` with a 307, and a `200` proxy rule inherits that redirect —
   this shipped once and sent all 12 routes to the homepage.
4. **Stale edge cache mimics a broken deploy.** Revalidation against an unchanged ETag
   re-serves stored headers. Three false alarms in one session. Re-check with
   `?cb=$(date +%s)` before concluding anything is broken.
5. **The broadcast's `limit` cannot choose a recipient.** It stops after N in KV order. To
   reach one person, use `/api/newsletter/preview` (`{"to": …}`) or the `language` filter.
6. **Route slugs must stay flat.** Fonts and `tracker.json` load by *relative* path; a nested
   slug moves the document base and 404s both.
7. **Unique function names inside the main IIFE.** It is one scope — two `function render(){}`
   declarations silently collapse into the last one.

## Unresolved

- **Deliverability of the first send is unverified.** The one real subscriber's copy may have
  landed in spam; first send from a new domain is when that gets decided. No SPF/DKIM/DMARC
  audit has been done.
- **Gmail's native Unsubscribe button (RFC 8058 `POST`) has never been exercised** by a real
  client. The endpoint accepts POST and rejects bad signatures; the button itself is untested.
- **No per-claim provenance dates.** `tracker.json` has `lastReviewed` and 9 dated entries,
  but compound-page claims carry citations without machine-readable review dates, so nothing
  can flag stale content. 12 DOI links are unchecked for rot.
- **No link checking, no accessibility audit, no performance budget** in `verify.sh`.
- **`worker/.claude/settings.json`** is untracked and shadows the project `.claude/` when
  working from `worker/`. Harmless, but surprising.
- **Compound backlog**: TB-500, CJC-1295, Epitalon (already promised by the site's "More
  coming" card), Tesamorelin, Tirzepatide, Melanotan II / PT-141. Plus a "Not peptides, sold
  alongside" section for NAD+, agreed but not built.

## Recommended next steps

1. Check whether the real subscriber's copy landed in inbox or spam, and audit SPF/DKIM/DMARC
   if it did not.
2. Add per-claim review dates when the next compound goes in — the metadata is cheapest to
   write at authoring time, and it is what makes staleness detectable.
3. Add DOI link checking to the monthly review routine, not to `verify.sh` (network-bound).
4. Enable non-production branch builds on the site Worker to get real preview URLs. Right now
   the only way to see a change live is to merge.

## Automation already running

A scheduled cloud agent, **In The Vial — monthly regulatory tracker review**, fires on the
**1st of each month at 13:00 UTC**, first run **2026-09-01**. It checks the 5 tracker lanes
against primary sources and reports what moved. It is **report-only, enforced structurally**:
granted only `Read, Grep, Glob, WebSearch, WebFetch`, so it cannot commit, push, bump
`lastReviewed`, or send anything.

## Decisions taken, so they are not re-proposed

- **No AI-generated imagery.** On a site arguing that everything is a claim until an
  instrument says otherwise, a synthetic photo of a lab that does not exist is the wrong kind
  of picture. Charts, timelines and evidence matrices must be built from real data as inline
  SVG — generated ones invent values. The site has **zero raster images** except the
  link-preview card, which is authored from its own design tokens.
- **No D1 / R2 / AI Gateway / MCP platform.** Proposed three times, declined each time: it
  assumed a `package.json`, a build step and a staging pipeline this repo does not have, and
  would have added account-level Cloudflare OAuth as an HTTP-reachable target. The
  coordination problem it solves does not exist for a solo project with a public repo.
- **`script-src` keeps `'unsafe-inline'`.** The site is one inline script; a stale SHA-256
  hash would kill all JavaScript rather than degrade the page. The CSP here is a privacy
  control, not an XSS defence. Revisit if the site ever accepts user input.
- **Checks are scripts, never agents.** A script's output can be audited; an agent reporting
  "I ran the check" cannot be told apart from one that did not.
