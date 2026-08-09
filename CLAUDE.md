# In The Vial — project guide

Buyer-literacy site for research peptides. *"The label is a claim. Learn to read the proof."*
Independent, evidence-graded, non-commercial: **nothing is sold, no vendor is linked, no dose is recommended.**

## Files

| File | What it is |
|---|---|
| `index.html` | The entire site — markup, CSS, and JS inline. ~210 KB. |
| `tracker.json` | Regulatory tracker content (5 lanes / 9 entries), bilingual `en`/`es` per field. |
| `fonts/` | Self-hosted woff2 (Instrument Serif, IBM Plex Sans/Mono), Latin + Latin-Ext. |
| `_redirects` | Asset-layer route table — one line per page route. |
| `sitemap.xml` | Every route in both languages, with hreflang alternates. |
| `wrangler.jsonc` | The **site** Worker's config. `worker/wrangler.toml` is the subscribe Worker — different deployment. |
| `src/index.js` | Site Worker: rewrites `<head>` per route so link previews are right. |
| `src/routes.js` | **Generated** from `ROUTES` in `index.html`. Never hand-edit. |
| `scripts/build-routes.py` | The generator for the above. |
| `.assetsignore` | Keeps non-site files out of the published assets. |

Single-page app: each section is a `.view` div toggled by JS. No build step, no dependencies, no backend.

## Hard rules

**1. Every English string needs a Spanish counterpart.**
Translations live in the `ES` map inside `<script>`, keyed to the *exact* English text. Editing an English string silently orphans its Spanish entry and that snippet falls back to English. When you change user-visible English, update its `ES` key in the same task. Dynamic strings live in `DYN`, not `ES`.

Coverage is currently **complete** — `check_i18n.py` reports 0 untranslated and gates on that,
so any new orphan fails the build rather than joining a backlog. A string that should *stay*
English (brand, SI units, assay names like `HPLC` or `USP <71>`) goes in
`.claude/skills/i18n-check/intentionally-english.txt` **with its reason**, not into `ES`. The
checker also fails on a stale allowlist entry, so that file cannot quietly start excusing text
it was never meant to cover.

**2. Do not reintroduce third-party requests.**
Fonts are self-hosted deliberately. The privacy policy now promises *"Loading a page does not cause your browser to contact any outside company."* Adding a Google Fonts link, a CDN script, or an analytics tag makes that statement false. If analytics is ever added, the privacy section must be updated first.

**3. The tracker data exists in two places.**
`tracker.json` is the source of truth, fetched at runtime. A copy is also embedded inline in `index.html` (`<script id="tracker-data">`) as the fallback for `file://` and failed fetches. **Update both**, or the offline copy goes stale.

**4. Avoid generic CSS class names.**
`.tc` was defined twice — evidence-tier chip *and* test-guide table cell — and the later rule silently corrupted every TIER C chip. Tier chips are now scoped `.chip-tier.tc`, table cells `.trowg .tc`. Keep component styles scoped to their parent.

**5. Test at 390px before calling anything done.**
Check `document.documentElement.scrollWidth` vs `clientWidth` — they must match. Wide tables belong in `.ledger-wrap` (`overflow-x:auto`), never pushing the page wide.

## Architecture notes

- **Every view is a real page route** (`/toolkit`, `/bpc-157`), defined by the `ROUTES` table in `index.html`. Each route carries its own title and description in both languages and rewrites `<title>`, `description`, `canonical`, `og:*` and the three `hreflang` links on navigation. Keep `href` attributes on nav elements — they make the site keyboard-accessible and screen-reader-navigable, and now also make modifier-click open a real new tab; the delegated `preventDefault()` stops the jump for plain clicks only.

  **Slugs must stay flat — one segment, no nesting.** Fonts load from `url(fonts/…)` and the tracker from `fetch('tracker.json')`, both *relative*. A single-segment path leaves the document base at `/` so those still resolve; `/science/bpc-157` would send them to `/science/fonts/…` and silently 404 the typography and the tracker together. Same reason language is `?lang=es` and not `/es/` — a query string doesn't move the base. This is also why `_redirects` maps trailing slashes with a 301 instead of rewriting them.

- **A route lives in four places**, plus a generated fifth: `ROUTES` in `index.html`,
  `_redirects`, `sitemap.xml`, and `assets.run_worker_first` in `wrangler.jsonc` — then
  `python3 scripts/build-routes.py` to regenerate `src/routes.js`. Every one of these is
  checked by `verify.sh`, because each failure is invisible in the place you'd look:
  miss `_redirects` and it 404s only on a cold load; miss `run_worker_first` and it renders
  perfectly but link previews show the homepage; let `routes.js` drift and the `<head>`
  describes a different page than the body.

- **`<head>` is rewritten twice, on purpose.** The Worker (`src/index.js`) rewrites `title`,
  `description`, `og:*`, `canonical` and `hreflang` server-side with `HTMLRewriter`; the
  router in `index.html` does the same client-side on navigation. The server pass exists
  because social scrapers don't run JS — without it every shared link previewed as the
  homepage. The client pass exists because in-app navigation never hits the server. They read
  the same table, which is why `routes.js` is generated rather than written.

- **Legacy `#view` hashes still resolve** and are upgraded to the real path on load. Newsletter issue 001 shipped `/#tracker` and `/#method` links; they must keep working for as long as that email exists.

- **`_redirects` lists routes explicitly rather than `/* /index.html 200`.** A catch-all risks shadowing `tracker.json`, the fonts, `robots.txt` and `sitemap.xml`, and turns every dead link into a soft-200 homepage instead of an honest 404. Don't add a rule for `/api/*` — that's the Worker's, and its route runs ahead of Pages.

- **Declare functions with unique names inside the main IIFE.** The whole script is one function scope, so two `function render(){}` declarations silently collapse into whichever is declared last — the router's `render` was eaten by the residue-chain renderer's, and the only symptom was the home view showing at every URL. It is the `.tc` collision again, in JavaScript. The router's is now `renderRoute`.
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

## The review team

Tooling lives in `.claude/` **inside this repo** — skills, hooks, settings and agents all
version-controlled together. (They previously sat in the parent folder, outside git, where the hook
path never resolved and nothing was backed up.)

**You are the writer.** Editing `index.html` is a serial, single-threaded job: it is one ~250KB
file, so two agents editing it concurrently clobber each other. Never delegate the edit itself.
Delegate *judgement*, and apply the results yourself.

**Checks are scripts, not agents.** Anything deterministic is a script, because a script's output
can be audited and an agent reporting "I ran the check" cannot be told apart from one that didn't.

**One command runs all of them.** Use this before any deploy:

```bash
bash .claude/verify.sh
```

It gates on: JS syntax · route registration (`ROUTES` / `_redirects` / `sitemap.xml`) ·
tracker schema · inline-tracker drift · newsletter freshness · i18n **delta**. Design-scale
is advisory and never fails the run. Exits non-zero if anything is genuinely broken.

i18n is gated on delta, not absolute count — there is a known backlog of short technical
strings. The baseline lives in `.claude/i18n-baseline.txt`; when you translate some, lower it.

The individual checks still run standalone when you want one in isolation:

```bash
python3 .claude/skills/verify/check_routes.py                   # routes in all three files
python3 .claude/skills/i18n-check/check_i18n.py index.html      # untranslated strings
python3 .claude/skills/tracker/validate_tracker.py tracker.json # tracker schema
python3 .claude/skills/design-scale/audit_scale.py index.html   # design-system sprawl
bash .claude/hooks/js-syntax-check.sh index.html                # JS syntax (also a PostToolUse hook)
```

`verify.sh` does not check how anything *looks*. Still check 390 / 768 / 1280px yourself.

**Two agents exist, for the two things no script can judge:**

| Agent | Judges | Why not a script |
|---|---|---|
| [`evidence-auditor`](.claude/agents/evidence-auditor.md) | Are the scientific and regulatory claims true, and correctly tiered? | Requires reading primary sources and deciding what they actually support. |
| [`design-critic`](.claude/agents/design-critic.md) | Does it *look* right at real breakpoints? | Requires seeing rendered type, rhythm and balance. |

Both are **read-only** by design. That is what lets them run in parallel safely while you hold the
only write lock.

### Adding a compound

1. Draft the page yourself, following [new-compound](.claude/skills/new-compound/SKILL.md).
2. Run `evidence-auditor` on the draft **before** wiring it in. Fabricated trial results are the
   most damaging failure available on this site and the least visible.
3. Apply its BLOCKING findings, then wire in all six places and add the ES keys (~45 per compound).
4. Register the route in all three places — `ROUTES` (with an EN *and* ES title and description),
   `_redirects` (rewrite + trailing-slash 301), and `sitemap.xml` (both language URLs).
5. Run the scripts. Gate on *delta*: a change must add **zero** new orphans.
6. Run `design-critic` at 390 / 768 / 1280px.
7. Load the new route cold (not by clicking to it) to prove `_redirects` was updated.

### Known gaps

- ~~Untranslated attributes.~~ **Fixed.** `applyAria()` translates `aria-label` in a pass of
  its own, because the TreeWalker is `SHOW_TEXT` and never sees attributes. The menu button
  is special-cased: it rewrites its own label as it opens and closes, so its label is derived
  from `aria-expanded` rather than from a cached original. `langBtn` stays
  `"Switch language / Cambiar idioma"` in both languages on purpose.
- **Mobile asserts on hidden views are meaningless.** `.view{display:none}`, so a hidden view
  contributes nothing to `scrollWidth`. Navigate to the view first, then assert — and check in
  **both** languages, since Spanish strings run longer and overflow is often a translation bug.
- ~~Five duplicate `ES` keys.~~ **Fixed** — there were six (the note missed
  `The regulatory tracker`). All had identical values, so removing the earlier copy of each
  changed no behaviour. `check_i18n.py` now fails on any duplicate, so they cannot return.

- **`check_i18n.py` used to under-report.** Its key extraction matched `'…'` followed by `:`,
  which desynchronises on a key that itself begins with a colon — and inline `<em>`/`<strong>`
  tags produce exactly those fragments. It matched the `,\n` between entries as a key and
  reported the real one as untranslated. It now scans the literal properly. If you add a key
  and the checker still calls it missing, suspect the checker, not the key.

## Newsletter

`worker/newsletter-content.js` is **generated** — rebuild it, never hand-edit it:

```bash
python3 newsletter/build.py
```

It compiles `newsletter/*.md` (frontmatter `issue`, `date`, `subject`, `preheader` + body)
into the Worker bundle, ignoring `*.before-edit-*` backups. It refuses to build an issue
with no `{{unsubscribe_url}}`, or one whose EN and ES issue numbers disagree. `--check`
exits non-zero when the compiled file is stale; `verify.sh` runs that.

Publishing an issue is three steps, and only the third sends mail:

```bash
python3 newsletter/build.py && bash .claude/verify.sh
cd worker && npx wrangler deploy
# then the broadcast: dry run, then {"confirm":true,"limit":1}, then the list
```

**The `issue` parameter namespaces the `sent:` markers — it does not select content.**
Content is whatever is compiled into the deployed bundle. The broadcast now rejects a
mismatch with `409 issue_mismatch`; before that guard, an issue number ahead of the bundle
silently re-sent the *previous* issue to the whole list and reported `ok: true`.

## Deploy

`main` → Cloudflare **Worker** `in-the-vial` (static assets, Git integration) → auto-publishes
on push, **~40 seconds**. Nothing to compile.

**It is not Cloudflare Pages.** `wrangler pages project list` returns nothing; an older note
said Pages and it was wrong. This matters in two ways: `_redirects` is read by Workers static
assets (200 proxying included) so routing works, but there are **no automatic per-branch
preview URLs** the way Pages gives them. A branch push builds nothing you can visit unless
preview URLs are enabled for the Worker. Verifying a change live means merging to `main`;
rollback is `git revert` plus another ~40s, or a version rollback in the dashboard.

### Deploying the subscribe Worker — always pass `--config`

```bash
cd worker && npx wrangler deploy --config wrangler.toml
```

**Never bare `npx wrangler deploy` from `worker/`.** Since the site Worker's `wrangler.jsonc`
was added at the repo root, wrangler resolves *that* one even when run from `worker/` — it
reports `env.ASSETS` as the only binding and would deploy the site Worker under the wrong
intent, leaving the subscribe Worker untouched and the newsletter code stale with no error.

**Dry-run first and read the bindings.** The subscribe Worker must show both:

```
env.SUBS (6c7174d740cc4cb99315a913dec80746)   KV Namespace
env.EMAIL (senders: newsletter@in-the-vial.com)   Send Email
```

If you see `env.ASSETS` instead, wrangler picked up the wrong config — stop.

Secrets (`ADMIN_TOKEN`, `UNSUBSCRIBE_SECRET`) are stored separately and survive a deploy;
they are not re-uploaded and not wiped.

### Secrets: always pass `--name`, never rely on the directory

```bash
npx wrangler secret put ADMIN_TOKEN --name in-the-vial-subscribe
npx wrangler secret list --name in-the-vial-subscribe
```

`wrangler secret put` resolves config the same way `deploy` does, so run from `worker/` it
still targets the **site** Worker. It says which one in its output — *"Creating the secret for
the Worker `in-the-vial`"* means it went to the wrong place. The failure is quiet: the command
succeeds, the secret lands on a Worker that never reads it, and the endpoint keeps returning
`401` with the old token still in force.

`--name` skips config resolution altogether and is the only form that cannot be
misdirected. Use it for every `secret` subcommand.

The assets directory is the repo root with nothing excluded, so every tracked file is public:
`CLAUDE.md`, `worker/subscribe.js`, `newsletter/*.md` drafts, `.claude/`. The repo is public so
nothing secret leaks, but unsent drafts are readable and crawlable. An `.assetsignore` would
fix it. Gitignored `*.backup-*` files are **not** served — deployed content is git contents.

Local preview (needed so `fetch('tracker.json')` works):
```bash
python3 -m http.server 8142
```

`http.server` does **not** apply `_redirects`, so it 404s every page route. Fine for content
work; useless for routing.

**To test routing, run the real asset runtime locally:**

```bash
npx wrangler dev --assets=. --port 8791
```

It parses `_redirects` exactly as production does and prints how many rules it accepted. This
is the only local way to catch routing bugs — one shipped to production because it was tested
against a hand-written mimic instead: `/toolkit /index.html 200` looked right and became
`307 -> /`, because Workers static assets canonicalises `/index.html` to `/` and a proxy rule
inherits that redirect. Every deep link silently landed on the homepage. **Proxy to `/`.**
