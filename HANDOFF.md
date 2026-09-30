# Handoff — current state of In The Vial

**Updated 2026-09-29 · HEAD `51bb5b7`**

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
| Routing | 13 real page routes via `_redirects`; `src/index.js` rewrites `<head>` per route. |
| API | Separate Worker `in-the-vial-subscribe` on `in-the-vial.com/api/*`. **Deploys manually only.** |
| Storage | KV namespace `SUBS`. No D1, no R2. |
| Checks | `bash .claude/verify.sh` — **9 gates**, exits non-zero. Includes secret scanning and CSP. |

## Current state

- **13 routes live**, all 200, each with its own title/description in both languages,
  server-rendered so scrapers see them. Newest: **`/corrections`** (2026-09-25).
- **A corrections log exists** at `/corrections` — the site's own record of what it got wrong,
  starting 2026-09-25 (not backfilled further; see Decisions). It currently lists the two
  tracker errors below. Keep entries newest-first and always state how long the error was live
  — that number is the part no vendor site would publish, and it's what gives the page weight.
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
- **Google Search Console: verified 2026-09-25** (URL-prefix property, HTML-tag method).
  `sitemap.xml` submitted — **Success, 24 pages discovered** as of verification (now 26 URLs
  in the sitemap after `/corrections` was added; Pages count not yet rechecked since). Also
  submitted to **IndexNow** (Bing/Yandex/Seznam/Naver) via `bash scripts/indexnow.sh` — rerun
  after adding `/corrections` too.
- **Tracker corrected 2026-09-24.** Two entries had gone factually stale; `lastReviewed` is
  now September 2026. Found by the monthly routine, verified against the Federal Register.
  This is what `/corrections` now documents publicly.

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
7. **`html_handling` strips `.html`.** `/foo.html` 307s to `/foo`. This killed Google's
   HTML-file verification, and is the same mechanism as the `/index.html` -> `/` 307 above.
   Third time it has bitten.
8. **Two public files must never be deleted:** the `google-site-verification` meta tag in
   `index.html` (removing it un-verifies Search Console) and
   `71a90b9ae4786f1ecf95e3a4ba1a62e3.txt` (removing it breaks IndexNow). Neither is a secret.
9. **Unique function names inside the main IIFE.** It is one scope — two `function render(){}`
   declarations silently collapse into the last one.
10. **A new route needs registration in five places, not one.** `ROUTES` in `index.html` (with
    EN+ES title/desc), `_redirects` (both the bare rewrite and the trailing-slash redirect),
    `sitemap.xml` (both languages), `wrangler.jsonc`'s `run_worker_first` list, and then
    regenerate `src/routes.js` via `python3 scripts/build-routes.py`. `verify.sh` catches a
    missed one but only after the fact — check `python3 .claude/skills/verify/check_routes.py`
    directly while adding a route for faster feedback.
11. **The local `wrangler dev` server wedges intermittently** — `workerd` stays listening on
    the port but stops answering requests (curl hangs or returns `000`), even across clean
    restarts. When this happens, verify against the live deploy instead (push, wait ~40s,
    curl the real URL) rather than losing time diagnosing the local server. Not yet root-caused.

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

1. **Rerun IndexNow** (`bash scripts/indexnow.sh`) to submit `/corrections` — it was added
   after the last submission and Google's Search Console sitemap already has 26 URLs, but
   IndexNow was only run against the 24-URL version.
2. **Check Search Console → Pages** (overdue — was due ~2026-10-02). How many of the 26 are
   indexed, and why any are excluded. First real signal the site exists.
3. **Read the 2026-10-01 routine report promptly.** September's sat unread for three weeks
   while the site served a false regulatory claim — don't repeat that.
4. Check whether issue 001 reached the one real subscriber's inbox or spam.
5. Per-claim provenance dates with the next compound; DOI link rot.
6. **Next compound to rate should aim honestly at Tier D if the evidence warrants it.** The
   evidence scale's bottom tier has never been used on this site — worth checking whether
   that's accurate or whether something in the backlog (or already published) deserves it.
7. Compound backlog: TB-500, CJC-1295, Epitalon, then the NAD+ section.
8. **Eyeball `/corrections?lang=es` in a real browser.** The Spanish translation for that page
   was verified via `check_i18n.py` (0 untranslated) and the server-rendered `<title>`, but the
   client-side body-text rendering was never visually confirmed in a browser this session
   because the local dev server was wedged (see trap #11).

*Deferred deliberately:* splitting `/toolkit` into four routes. Structurally correct for SEO,
but the landscape is eight established vendor domains and a new site will not beat them on
explanation quality. Revisit once indexing shows something.

## Automation already running

A scheduled cloud agent, **In The Vial — monthly regulatory tracker review**
(`trig_01MDEQLNaLSXnuZcZrXgfAP7`, inspect via the `RemoteTrigger` tool), fires on the
**1st of each month at 13:00 UTC**. First run 2026-09-01 succeeded and found the two stale
entries corrected on 2026-09-24 and now documented at `/corrections`. Confirmed still enabled
as of 2026-09-29, with `next_run_at: 2026-10-01T13:03:43Z` and no run since September 1st. It
checks the 5 tracker lanes against primary sources and reports what moved. It is
**report-only, enforced structurally**: granted only `Read, Grep, Glob, WebSearch, WebFetch`,
so it cannot commit, push, bump `lastReviewed`, or send anything.

**Read the report promptly when it fires.** September's sat unread for three weeks while the
site continued serving a false regulatory claim — the automation only closes the loop if a
human reads the output. `RemoteTrigger {action: "list_runs", trigger_id: "..."}` then
`get_run_log` on the session retrieves it, but the final message truncates around ~15k chars
and the claude.ai session page 403s to `WebFetch` — verify any long report's factual claims
against primary sources directly rather than relying on retrieving the full text.

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
- **The `/corrections` log starts 2026-09-25, not backfilled to the project's beginning.**
  Earlier fixes exist in `git log` but weren't recorded in "what it said / what's true / how
  long it was live" form at the time. Reconstructing that from commit messages risks describing
  an old error inaccurately — on the one page whose entire premise is accuracy. Starting late
  and honest beats starting complete and guessed.
