# Handoff — current state of In The Vial

**Updated 2026-10-01 · HEAD `d6679dd`**

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
| Routing | 17 real page routes via `_redirects`; `src/index.js` rewrites `<head>` per route. |
| API | Separate Worker `in-the-vial-subscribe` on `in-the-vial.com/api/*`. **Deploys manually only.** |
| Storage | KV namespace `SUBS`. No D1, no R2. |
| Checks | `bash .claude/verify.sh` — **9 gates**, exits non-zero. Includes secret scanning and CSP. |

## Current state

- **17 routes live**, all 200, each with its own title/description in both languages,
  server-rendered so scrapers see them. Newest: **`/nad-plus`** (2026-10-01) — a new
  **"Not peptides, sold alongside"** subsection on the science library, for compounds marketed
  in the same storefronts/clinics as the peptides above but chemically unrelated. NAD+ is its
  first entry: route-split like GHK-Cu (Tier B for oral precursors — NMN/NR — where genuine
  RCTs reliably raise blood NAD+; Tier C for direct IV "NAD+ therapy," where the only
  comparative human data is a small retrospective study showing more adverse events and a
  mechanistic problem — NAD+ can't cross an intact cell membrane, so IV infusions hydrolyze
  into the same NMN/NR precursor sold far cheaper as a pill). The addiction/detox claim gets
  an honest **Tier D** — the evidence scale's bottom tier, used for the first time on this
  site — because it traces almost entirely to a single 1961 case series with no RCT ever run.
  No residue-chain diagram on this page; that's the point of the section.
- Just before that, **`/tb-500`, `/cjc-1295`, `/epitalon`** shipped (2026-10-01) — the three
  compounds the science library's "More coming" card had promised since the beginning. Each
  follows the existing evidence-tier template with real PubMed/ClinicalTrials.gov citations:
  TB-500 (Tier C — distinguishes the marketed fragment from the full-length Tβ4 molecule the
  only human trials actually tested), CJC-1295 (Tier B — genuine human PK/safety RCTs exist,
  alongside a 2006 phase 2 trial halted after a participant's death that the marketing omits),
  Epitalon (Tier C — real rodent lifespan data, but nearly all primary literature traces to one
  research group publishing in its own journal). The "More coming" card's promise is fully
  delivered; the only compound items still open are Tesamorelin, Tirzepatide and Melanotan II
  / PT-141, agreed but not started.
- **A corrections log exists** at `/corrections` — the site's own record of what it got wrong,
  starting 2026-09-25 (not backfilled further; see Decisions). It currently lists the two
  tracker errors below. Keep entries newest-first and always state how long the error was live
  — that number is the part no vendor site would publish, and it's what gives the page weight.
- **Spanish coverage is complete** — `check_i18n.py` reports 885 ES keys, 0 untranslated,
  0 duplicate keys. 27 strings are deliberately English (brand, SI units, assay names,
  three-letter amino-acid codes, trial-registry IDs) and listed with reasons in
  `.claude/skills/i18n-check/intentionally-english.txt`.
- **Newsletter issue 001's real-world deliverability has now been checked, not just flagged
  as unverified.** The actual subscriber it was sent to (a Yahoo address, found via
  `wrangler kv key list` — the Gmail account used for internal testing only ever received the
  `[PREVIEW]` copies) never received it: not in Inbox, not in Spam, despite Cloudflare's
  `send_email` binding reporting success. SPF, DKIM and DMARC are all correctly configured for
  `in-the-vial.com` (verified via `dig`), so this isn't the missing-authentication problem it
  looked like — it's more likely sender-reputation/warm-up with a brand-new domain. **DMARC
  aggregate reporting is now enabled** via Cloudflare's built-in DMARC Management (adds an
  `rua=mailto:...@dmarc-reports.cloudflare.net` tag), so the next send's pass/fail rate at
  each provider will actually be visible instead of silent.
- **Security headers live** — CSP with `default-src 'self'`, HSTS, `Referrer-Policy:
  no-referrer`, Permissions-Policy, frame/CORP/COOP. Verified by probe: an external `fetch`
  and a Google Fonts stylesheet are both blocked; `fetch('tracker.json')` still returns 200.
- **Link previews have a card** — `og-image.png`, authored from the site's own type and
  dossier markup, not AI-generated.
- Subscribers: **2 active** — the real Yahoo reader, and the plain Gmail address, which
  subscribed *after* issue 001 went out (that's why it only ever saw previews). The `+en`/`+es`
  Gmail aliases used for testing have since unsubscribed.
- **Google Search Console: verified 2026-09-25** (URL-prefix property, HTML-tag method).
  `sitemap.xml` submitted — **Success, 24 pages discovered** as of verification. Checked again
  2026-09-30/10-01: Page Indexing and Performance still show **"Processing data, please check
  again in a day or so"** — a genuine empty state (confirmed via screenshot, not a loading
  glitch), not yet actionable. Also resubmitted to **IndexNow** (Bing/Yandex/Seznam/Naver) via
  `bash scripts/indexnow.sh` on 2026-10-01 (two separate runs as routes shipped) — **34 URLs
  accepted**, now covering `/corrections`, `/tb-500`, `/cjc-1295`, `/epitalon` and `/nad-plus`
  in both languages.
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
    A plain `python3 -m http.server` can go stale the same way if an old instance is still
    bound to the port from a previous session — it answers with 404s on files that exist and
    whose `cwd` is correct. `lsof -i :PORT`, kill it, and start a fresh one on a new port
    rather than trying to explain the 404.
12. **`.chip-tier` and `.rtype` are `white-space:nowrap` by design** — a tier-chip subtitle or
    citation-type badge that runs long doesn't wrap, it pushes the whole page wider than the
    viewport. This is invisible in English and only shows up once the Spanish translation is
    even longer, or the viewport narrower — caught **three** times now: twice at 375px while
    adding TB-500/CJC-1295/Epitalon, then again at **320px** (not 375px!) on the NAD+ card,
    after 375px had already passed clean. 390px is this project's stated test floor, but 320px
    is a real, common device width and genuinely different fonts/chip text can clear one and
    still fail the other. Keep chip/rtype text short (NAD+'s fix: "TIER B PRECURSOR · TIER C
    IV" → "TIER B ORAL · TIER C IV"), and check **both** 375px and 320px, in both languages,
    with `document.documentElement.scrollWidth` vs `clientWidth` — not just the one the hard
    rule names.

## Unresolved

- **Deliverability of the first send failed, and now we know it** — see Current state above.
  The real subscriber never got issue 001, auth is clean, so this reads as domain-reputation/
  warm-up rather than misconfiguration. DMARC aggregate reports are now on; the next real send
  is the thing to watch to confirm or rule that out.
- **Gmail's native Unsubscribe button (RFC 8058 `POST`) has never been exercised** by a real
  client. The endpoint accepts POST and rejects bad signatures; the button itself is untested.
- **No per-claim provenance dates.** `tracker.json` has `lastReviewed` and 9 dated entries,
  but compound-page claims carry citations without machine-readable review dates, so nothing
  can flag stale content. DOI links across all 9 compound pages are unchecked for rot.
- **No link checking, no accessibility audit, no performance budget** in `verify.sh`.
- **`worker/.claude/settings.json`** is untracked and shadows the project `.claude/` when
  working from `worker/`. Harmless, but surprising.
- **Compound backlog, the promised wave resolved** — TB-500, CJC-1295, Epitalon and the
  "Not peptides, sold alongside" section (NAD+) all shipped 2026-10-01 (see Current state),
  closing out everything the site's "More coming" card had promised. Still open, not yet
  started: Tesamorelin, Tirzepatide, Melanotan II / PT-141.
- **The "not peptides" section currently has one entry.** Nothing else is queued for it yet —
  if a second non-peptide compound gets added later (a hormone, a small molecule), model its
  page on NAD+'s: no chain plate, same evidence-tier rigor, and state up front why it's grouped
  there rather than in the main compound grid.

## Recommended next steps

1. **Check Search Console → Pages** (overdue — was due ~2026-10-02; still showing
   "Processing data" as of 2026-10-01). How many of the 34 sitemap URLs are indexed, and why
   any are excluded. First real signal the site exists.
2. **Read the 2026-10-01 routine report promptly** when it fires at 13:00 UTC today.
   September's sat unread for three weeks while the site served a false regulatory claim —
   don't repeat that.
3. **Watch the next real newsletter send for deliverability**, now that DMARC aggregate
   reports are on. If the Yahoo subscriber still doesn't receive it with clean auth and visible
   reports, that confirms reputation/warm-up rather than a config problem, and the fix is
   consistent low-volume sending over time, not another DNS change.
4. Per-claim provenance dates across all 9 compound pages; DOI link rot.
5. Remaining compound backlog: Tesamorelin, Tirzepatide, Melanotan II / PT-141.
6. **The Tier-D question has now been answered once — ask it again for what's left.**
   TB-500, CJC-1295 and Epitalon were checked against Tier D and landed at C or B instead;
   NAD+'s addiction claim is the first thing on this site actually graded D (a 1961 case
   series, no RCT). The scale can clearly produce every grade now — worth re-checking against
   Tesamorelin, Tirzepatide and Melanotan II / PT-141 once drafted, honestly, not reflexively.
7. **Eyeball `/nad-plus` and the new "Not peptides" science-library subsection in a real
   browser**, not just this session's automated checks — particularly the card's standalone
   layout with no chain plate, which has no other precedent on the site to compare against.

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
- **DMARC reporting goes through Cloudflare's own DMARC Management, not a hand-wired mailbox.**
  Enabling it (Email → DMARC Management → Enable, in the dashboard) adds a
  `rua=mailto:...@dmarc-reports.cloudflare.net` tag to the existing `_dmarc` TXT record and
  gives a dashboard view of per-source pass/fail rates — no new Email Routing rule, no address
  to monitor by hand. Don't re-propose routing raw aggregate-report XML to the owner's inbox.
