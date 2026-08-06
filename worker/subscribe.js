/**
 * in-the-vial.com — newsletter subscribe endpoint
 *
 * WHY THIS EXISTS AS A WORKER RATHER THAN AN EMBEDDED FORM
 * The site's privacy policy states that loading a page does not cause the
 * visitor's browser to contact any outside company. An embedded provider form
 * (Substack, Mailchimp, ConvertKit) would make that false. Here the browser
 * only ever talks to in-the-vial.com; this Worker talks to the mail provider
 * server-side, so the promise survives.
 *
 * The subscriber list is more sensitive than a typical newsletter list — it is
 * a record of people interested in research peptides. Treat it accordingly:
 * never log full addresses, never expose the list over a GET route, and keep
 * the provider key in a Worker secret rather than in this file.
 *
 * SETUP
 *   1. wrangler secret put PROVIDER_API_KEY
 *   2. set PROVIDER_ENDPOINT in wrangler.toml vars (Buttondown shown below)
 *   3. wrangler deploy
 *   4. route POST https://in-the-vial.com/api/subscribe -> this Worker
 */

const ALLOWED_ORIGINS = [
  "https://in-the-vial.com",
  "https://www.in-the-vial.com",
];

// Deliberately conservative. Rejects the obvious junk without trying to be a
// full RFC 5322 parser, which is a well-known way to reject valid addresses.
const EMAIL_RE = /^[^\s@]+@[^\s@.]+\.[^\s@]{2,}$/;

function cors(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}

function json(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...cors(origin) },
  });
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors(origin) });
    }
    if (request.method !== "POST") {
      return json({ ok: false, error: "method_not_allowed" }, 405, origin);
    }
    if (origin && !ALLOWED_ORIGINS.includes(origin)) {
      return json({ ok: false, error: "bad_origin" }, 403, origin);
    }

    let email, hp;
    try {
      const body = await request.json();
      email = String(body.email || "").trim().toLowerCase();
      hp = String(body.company || "");      // honeypot, see the form markup
    } catch {
      return json({ ok: false, error: "bad_request" }, 400, origin);
    }

    // Bots fill every field they find. Humans never see this one.
    // Return success so the bot does not learn it was caught.
    if (hp) return json({ ok: true }, 200, origin);

    if (!email || email.length > 254 || !EMAIL_RE.test(email)) {
      return json({ ok: false, error: "invalid_email" }, 400, origin);
    }

    // Light abuse control: one signup per address per hour, keyed by a hash so
    // the KV namespace never contains a readable list of addresses.
    if (env.RATE) {
      const digest = await crypto.subtle.digest(
        "SHA-256", new TextEncoder().encode(email)
      );
      const key = [...new Uint8Array(digest)]
        .map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
      if (await env.RATE.get(key)) {
        return json({ ok: true, already: true }, 200, origin);
      }
      await env.RATE.put(key, "1", { expirationTtl: 3600 });
    }

    // ---- store first -------------------------------------------------
    // The list lives in your own Cloudflare account. This works with no mail
    // provider at all, so the form can go live before a sender is chosen —
    // a signup box that silently fails is worse than no signup box.
    if (env.SUBS) {
      await env.SUBS.put(`sub:${email}`, JSON.stringify({
        at: new Date().toISOString(),
        list: "tracker-digest",
      }));
    }

    // ---- forward to a sender, only if one is configured ----------------
    if (env.PROVIDER_ENDPOINT && env.PROVIDER_API_KEY) {
      const res = await fetch(env.PROVIDER_ENDPOINT, {
        method: "POST",
        headers: {
          "Authorization": `Token ${env.PROVIDER_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email_address: email, tags: ["tracker-digest"] }),
      });

      // 409 = already subscribed. Not an error the reader needs to see, and
      // reporting it would leak whether an address is on the list.
      if (!res.ok && res.status !== 409) {
        // Never echo the provider's response body — it can contain the address.
        console.error("provider_error", res.status);
        // The address is already stored, so this is still a success for the
        // reader. Failing here would make them retype an address we have.
        if (!env.SUBS) {
          return json({ ok: false, error: "provider_error" }, 502, origin);
        }
      }
    } else if (!env.SUBS) {
      // Nothing configured at all — refuse rather than pretend it worked.
      console.error("no_storage_or_provider_configured");
      return json({ ok: false, error: "not_configured" }, 503, origin);
    }

    return json({ ok: true }, 200, origin);
  },
};
