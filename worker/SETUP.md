# Newsletter & email — deployed state

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
honeypot → fake 200 and NOT stored · foreign origin → 403 · GET → 405 ·
preflight → 204 · real form submission on the live site reached KV.
