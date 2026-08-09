# Newsletter & email — deployed state

> **Deploy this Worker with an explicit config, always:**
> `cd worker && npx wrangler deploy --config wrangler.toml`
> A bare `wrangler deploy` resolves the site Worker's `wrangler.jsonc` at the repo root
> instead, even from this directory. Dry-run first; you must see `env.SUBS` and `env.EMAIL`
> in the bindings. If it says `env.ASSETS`, it is the wrong Worker.

## Subscribe endpoint
- Worker `in-the-vial-subscribe`, route `in-the-vial.com/api/subscribe`
- Subscribers stored in KV namespace `SUBS` (`6c7174d740cc4cb99315a913dec80746`)
- **No mail provider connected yet.** Capture works; sending does not.
  To add one: uncomment `PROVIDER_ENDPOINT` in wrangler.toml,
  `npx wrangler secret put PROVIDER_API_KEY`, then `npx wrangler deploy`.
- Export the list:
  `npx wrangler kv key list --namespace-id 6c7174d740cc4cb99315a913dec80746 --remote`

## Email Routing (corrections@in-the-vial.com)
- Enabled on the zone; MX records live (`route1/2/3.mx.cloudflare.net`)
- Rule `corrections` → forwards to the owner's primary inbox
- Catch-all: disabled, action `drop` — mail to any other @in-the-vial.com
  address is discarded rather than bounced
- ⚠️ Destination address requires a one-time click on Cloudflare's
  verification email before forwarding actually delivers.

## Verified in production (2026-08-06)
Valid signup stores + returns 200 · invalid/empty/malformed → 400 ·
honeypot → fake 200 and NOT stored · foreign origin → 403 · GET → 404 ·
preflight → 204 · real form submission on the live site reached KV.

## Verified end-to-end (2026-08-06)

- Language-aware signup: subscribed through the live site in EN and ES,
  read both back from KV with the correct `language` field.
- One-click unsubscribe: `POST /api/unsubscribe` accepted (was 404),
  `List-Unsubscribe-Post: List-Unsubscribe=One-Click` set on both send paths.
- Unsubscribe clicked from a real preview email → `unsub:` record created,
  other subscribers untouched.
- Unsubscribe link renders as a clickable anchor in both languages.

### Key semantics confirmed (write the broadcast against these)

- Unsubscribe **deletes** `sub:<email>` and **writes** `unsub:<email>`.
- Subscribe **deletes** `unsub:<email>` and **writes** `sub:<email>`.
- So the two states are mutually exclusive; a broadcast can iterate `sub:`
  keys alone. Checking `unsub:` per recipient is belt-and-braces, not
  required — but cheap, and worth keeping if KV listing is ever paginated
  mid-write.
- Every existing record already carries `language`, so the
  "default missing language to en" fallback is defensive only.

### Still not verified

- Gmail/Yahoo's *native* Unsubscribe button (the RFC 8058 POST path).
  The endpoint accepts POST and rejects bad signatures, but the
  mail-client button itself has not been exercised.
