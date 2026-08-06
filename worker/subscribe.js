import { NEWSLETTERS } from "./newsletter-content.js";

/**
 * in-the-vial.com newsletter Worker
 *
 * Routes:
 *   POST /api/subscribe
 *   POST /api/newsletter/test
 *   POST /api/newsletter/broadcast   (dry run unless {"confirm": true})
 *   GET|POST /api/unsubscribe?email=...&token=...
 */

const ALLOWED_ORIGINS = [
  "https://in-the-vial.com",
  "https://www.in-the-vial.com",
];

const EMAIL_RE = /^[^\s@]+@[^\s@.]+\.[^\s@]{2,}$/;
const FROM_EMAIL = "newsletter@in-the-vial.com";
const FROM_NAME = "In The Vial";
const REPLY_TO = "corrections@in-the-vial.com";
const SITE_URL = "https://in-the-vial.com";

function cors(origin) {
  const allowed = ALLOWED_ORIGINS.includes(origin)
    ? origin
    : ALLOWED_ORIGINS[0];

  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Vary": "Origin",
  };
}

function json(body, status = 200, origin = "") {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...cors(origin),
    },
  });
}

function htmlResponse(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
    },
  });
}

function normalizeEmail(value) {
  return String(value || "").trim().toLowerCase();
}

function isValidEmail(email) {
  return Boolean(
    email &&
    email.length <= 254 &&
    EMAIL_RE.test(email)
  );
}

function authorized(request, env) {
  if (!env.ADMIN_TOKEN) return false;

  // Constant-time, matching how the unsubscribe token is checked. A plain ===
  // short-circuits on the first differing byte, which leaks how much of a
  // guessed token was correct. Impractical to exploit over the internet, but
  // the safe comparison already exists in this file and costs nothing.
  const header = request.headers.get("Authorization") || "";
  return constantTimeEqual(header, `Bearer ${env.ADMIN_TOKEN}`);
}

function bytesToHex(bytes) {
  return [...new Uint8Array(bytes)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function makeUnsubscribeToken(email, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(email)
  );

  return bytesToHex(signature);
}

function constantTimeEqual(left, right) {
  if (typeof left !== "string" || typeof right !== "string") return false;
  if (left.length !== right.length) return false;

  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

async function unsubscribeUrl(email, env) {
  const token = await makeUnsubscribeToken(
    email,
    env.UNSUBSCRIBE_SECRET
  );

  const params = new URLSearchParams({ email, token });
  return `${SITE_URL}/api/unsubscribe?${params.toString()}`;
}

async function handleSubscribe(request, env, origin) {
  if (origin && !ALLOWED_ORIGINS.includes(origin)) {
    return json({ ok: false, error: "bad_origin" }, 403, origin);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "bad_request" }, 400, origin);
  }

  const email = normalizeEmail(body.email);
  const honeypot = String(body.company || "");
  const requestedLanguage = String(body.language || "").toLowerCase();
  const language = ["en", "es"].includes(requestedLanguage)
    ? requestedLanguage
    : "en";

  // Quietly accept obvious bot submissions.
  if (honeypot) {
    return json({ ok: true }, 200, origin);
  }

  if (!isValidEmail(email)) {
    return json({ ok: false, error: "invalid_email" }, 400, origin);
  }

  if (!env.SUBS) {
    return json({ ok: false, error: "not_configured" }, 503, origin);
  }

  // Resubscribing removes any earlier unsubscribe record.
  await env.SUBS.delete(`unsub:${email}`);

  await env.SUBS.put(
    `sub:${email}`,
    JSON.stringify({
      at: new Date().toISOString(),
      list: "tracker-digest",
      status: "subscribed",
      language,
    })
  );

  return json({ ok: true }, 200, origin);
}


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderInlineMarkdown(value) {
  let output = escapeHtml(value);

  // Bold and italics used in the newsletter drafts.
  output = output.replace(
    /\*\*(.+?)\*\*/g,
    "<strong>$1</strong>"
  );

  output = output.replace(
    /\*(.+?)\*/g,
    "<em>$1</em>"
  );

  // Convert standalone URLs after escaping the text. This runs post-escape, so
  // an ampersand in a query string is already "&amp;" — which is exactly what
  // belongs inside an href anyway.
  //
  // The pattern deliberately covers query strings, not just "/#anchor" links:
  // the unsubscribe URL carries ?email=...&token=... and previously fell
  // through as plain text, leaving readers with a URL they had to copy by hand.
  // A trailing . or , is excluded so sentence punctuation stays outside the link.
  output = output.replace(
    /(https:\/\/in-the-vial\.com\/[^\s<>")]*[^\s<>").,])/g,
    '<a href="$1" style="color:#3f5c46;text-decoration:underline">$1</a>'
  );

  return output;
}

function markdownToEmailHtml(markdown, unsubscribe, language) {
  const localized = language === "es"
    ? {
        preview: "Vista previa privada",
        issue: "Edición",
        website: "Abrir In The Vial",
      }
    : {
        preview: "Private preview",
        issue: "Issue",
        website: "Open In The Vial",
      };

  const source = markdown.replaceAll(
    "{{unsubscribe_url}}",
    unsubscribe
  );

  const lines = source.split(/\r?\n/);
  const parts = [];
  let paragraph = [];
  let listItems = [];

  function flushParagraph() {
    if (!paragraph.length) return;

    parts.push(
      `<p style="margin:0 0 18px;font-size:16px;line-height:1.65">` +
      `${renderInlineMarkdown(paragraph.join(" "))}</p>`
    );

    paragraph = [];
  }

  function flushList() {
    if (!listItems.length) return;

    const items = listItems
      .map((item) =>
        `<li style="margin:0 0 12px;padding-left:4px">` +
        `${renderInlineMarkdown(item)}</li>`
      )
      .join("");

    parts.push(
      `<ul style="margin:0 0 22px;padding-left:24px;` +
      `font-size:16px;line-height:1.6">${items}</ul>`
    );

    listItems = [];
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    if (line === "---") {
      flushParagraph();
      flushList();
      parts.push(
        '<hr style="border:0;border-top:1px solid #d9d7cf;margin:30px 0">'
      );
      continue;
    }

    if (line.startsWith("# ")) {
      flushParagraph();
      flushList();
      parts.push(
        `<h1 style="margin:0 0 22px;font-size:32px;line-height:1.18;` +
        `font-weight:700">${renderInlineMarkdown(line.slice(2))}</h1>`
      );
      continue;
    }

    if (line.startsWith("## ")) {
      flushParagraph();
      flushList();
      parts.push(
        `<h2 style="margin:32px 0 14px;font-size:22px;line-height:1.25;` +
        `font-weight:700">${renderInlineMarkdown(line.slice(3))}</h2>`
      );
      continue;
    }

    if (line.startsWith("- ")) {
      flushParagraph();
      listItems.push(line.slice(2));
      continue;
    }

    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  return `<!doctype html>
<html lang="${language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <title>In The Vial</title>
</head>
<body style="margin:0;background:#f3f1e9;color:#1d211d;font-family:Arial,Helvetica,sans-serif">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0">
    ${escapeHtml(NEWSLETTERS[language].preheader)}
  </div>

  <div style="max-width:680px;margin:0 auto;padding:28px 14px 48px">
    <div style="margin:0 0 12px;padding:10px 14px;background:#e6eadf;
      border:1px solid #ccd3c4;font-size:12px;letter-spacing:.08em;
      text-transform:uppercase">
      ${localized.preview} · ${localized.issue} ${escapeHtml(
        NEWSLETTERS[language].issue
      )}
    </div>

    <article style="background:#fff;border:1px solid #d9d7cf;padding:36px 32px">
      <p style="margin:0 0 24px;font-size:13px;letter-spacing:.11em;
        text-transform:uppercase;font-weight:700">
        In The Vial
      </p>

      ${parts.join("\n")}

      <p style="margin:30px 0 0;font-size:13px;line-height:1.5;color:#62665f">
        <a href="${SITE_URL}/#home"
          style="color:#3f5c46;text-decoration:underline">
          ${localized.website}
        </a>
      </p>
    </article>
  </div>
</body>
</html>`;
}

function markdownToPlainText(markdown, unsubscribe) {
  return markdown
    .replaceAll("{{unsubscribe_url}}", unsubscribe)
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/^---$/gm, "----------------------------------------");
}

async function handleNewsletterPreview(request, env, origin) {
  if (!authorized(request, env)) {
    return json({ ok: false, error: "unauthorized" }, 401, origin);
  }

  if (!env.EMAIL || !env.UNSUBSCRIBE_SECRET) {
    return json({ ok: false, error: "not_configured" }, 503, origin);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "bad_request" }, 400, origin);
  }

  const recipient = normalizeEmail(body.to);
  const language = String(body.language || "").toLowerCase();

  if (!isValidEmail(recipient)) {
    return json({ ok: false, error: "invalid_email" }, 400, origin);
  }

  if (!["en", "es"].includes(language)) {
    return json({ ok: false, error: "invalid_language" }, 400, origin);
  }

  const newsletter = NEWSLETTERS[language];

  if (!newsletter) {
    return json({ ok: false, error: "newsletter_not_found" }, 404, origin);
  }

  const unsubscribe = await unsubscribeUrl(recipient, env);

  const html = markdownToEmailHtml(
    newsletter.markdown,
    unsubscribe,
    language
  );

  const text = markdownToPlainText(
    newsletter.markdown,
    unsubscribe
  );

  try {
    const result = await env.EMAIL.send({
      from: FROM_EMAIL,
      to: recipient,
      replyTo: REPLY_TO,
      subject: `[PREVIEW ${language.toUpperCase()}] ${newsletter.subject}`,
      text,
      html,
      headers: {
        "List-Unsubscribe": `<${unsubscribe}>`,
        // RFC 8058. Without this the header above is only a hint and the
        // client falls back to a confirmation flow; with it, the native
        // Unsubscribe button removes the reader in one action — which is
        // what the site's privacy notice already promises.
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "X-Campaign-ID": `tracker-digest-${newsletter.issue}-${language}-preview`,
      },
    });

    return json({
      ok: true,
      language,
      issue: newsletter.issue,
      messageId: result.messageId,
    }, 200, origin);
  } catch (error) {
    console.error(
      "preview_send_failed",
      error?.code || "unknown",
      error?.message || "unknown"
    );

    return json({ ok: false, error: "send_failed" }, 502, origin);
  }
}

async function handleTestSend(request, env, origin) {
  if (!authorized(request, env)) {
    return json({ ok: false, error: "unauthorized" }, 401, origin);
  }

  if (!env.EMAIL || !env.UNSUBSCRIBE_SECRET) {
    return json({ ok: false, error: "not_configured" }, 503, origin);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "bad_request" }, 400, origin);
  }

  const recipient = normalizeEmail(body.to);

  if (!isValidEmail(recipient)) {
    return json({ ok: false, error: "invalid_email" }, 400, origin);
  }

  const unsubscribe = await unsubscribeUrl(recipient, env);

  const subject = "In The Vial newsletter system test";

  const text = [
    "In The Vial",
    "",
    "The protected newsletter Worker is working.",
    "",
    "This is a single-recipient test. No subscriber broadcast was triggered.",
    "",
    `Unsubscribe: ${unsubscribe}`,
  ].join("\n");

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <title>${subject}</title>
</head>
<body style="margin:0;background:#f5f3ed;color:#1d211d;font-family:Arial,sans-serif">
  <div style="max-width:640px;margin:0 auto;padding:40px 20px">
    <div style="background:#ffffff;border:1px solid #d9d7cf;padding:32px">
      <p style="margin:0 0 8px;font-size:13px;letter-spacing:.08em;text-transform:uppercase">
        In The Vial
      </p>
      <h1 style="margin:0 0 20px;font-size:28px;line-height:1.2">
        Newsletter system test
      </h1>
      <p style="font-size:17px;line-height:1.6">
        The protected newsletter Worker is working.
      </p>
      <p style="font-size:15px;line-height:1.6">
        This message was sent to one test recipient. No subscriber broadcast
        was triggered.
      </p>
      <hr style="border:0;border-top:1px solid #dedcd5;margin:28px 0">
      <p style="font-size:12px;line-height:1.5;color:#666">
        You can
        <a href="${unsubscribe}" style="color:#3f5c46">unsubscribe here</a>.
      </p>
    </div>
  </div>
</body>
</html>`;

  try {
    const result = await env.EMAIL.send({
      from: FROM_EMAIL,
      to: recipient,
      replyTo: REPLY_TO,
      subject,
      text,
      html,
      headers: {
        "List-Unsubscribe": `<${unsubscribe}>`,
        // RFC 8058. Without this the header above is only a hint and the
        // client falls back to a confirmation flow; with it, the native
        // Unsubscribe button removes the reader in one action — which is
        // what the site's privacy notice already promises.
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
      },
    });

    return json({
      ok: true,
      messageId: result.messageId,
    }, 200, origin);
  } catch (error) {
    console.error(
      "test_send_failed",
      error?.code || "unknown",
      error?.message || "unknown"
    );

    return json({ ok: false, error: "send_failed" }, 502, origin);
  }
}


/**
 * Broadcast an issue to the list.
 *
 * Defaults to a dry run: you must pass {"confirm": true} to actually send.
 * A missing flag sends nothing, because the failure mode of guessing wrong
 * here is mailing real people a duplicate.
 *
 * Idempotency: a `sent:<issue>:<email>` marker is written after each
 * successful send and checked before it. A retried, double-clicked or
 * resumed broadcast therefore skips anyone already reached, rather than
 * sending twice. Markers are per-issue, so a later issue is unaffected.
 */
async function handleBroadcast(request, env, origin) {
  if (!authorized(request, env)) {
    return json({ ok: false, error: "unauthorized" }, 401, origin);
  }
  if (!env.SUBS || !env.EMAIL || !env.UNSUBSCRIBE_SECRET) {
    return json({ ok: false, error: "not_configured" }, 503, origin);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "bad_request" }, 400, origin);
  }

  const issue = String(body.issue || "").trim();
  const confirm = body.confirm === true;
  const onlyLanguage = String(body.language || "").toLowerCase();
  const limit = Number.isInteger(body.limit) && body.limit > 0 ? body.limit : null;

  if (!issue) {
    return json({ ok: false, error: "missing_issue" }, 400, origin);
  }
  if (onlyLanguage && !["en", "es"].includes(onlyLanguage)) {
    return json({ ok: false, error: "invalid_language" }, 400, origin);
  }

  const summary = {
    issue,
    dryRun: !confirm,
    considered: 0,
    byLanguage: { en: 0, es: 0 },
    alreadySent: 0,
    wouldSend: 0,
    sent: 0,
    failed: 0,
    skippedNoContent: 0,
  };

  let cursor;
  do {
    const page = await env.SUBS.list({ prefix: "sub:", cursor, limit: 200 });
    cursor = page.list_complete ? undefined : page.cursor;

    for (const key of page.keys) {
      if (limit && summary.wouldSend + summary.sent >= limit) {
        cursor = undefined;
        break;
      }

      const email = key.name.slice("sub:".length);
      if (!isValidEmail(email)) continue;

      const raw = await env.SUBS.get(key.name);
      if (!raw) continue;

      let record;
      try {
        record = JSON.parse(raw);
      } catch {
        continue;
      }
      if (record.status && record.status !== "subscribed") continue;

      // Records predating the language field are English by default.
      const language = ["en", "es"].includes(record.language) ? record.language : "en";
      if (onlyLanguage && language !== onlyLanguage) continue;

      summary.considered += 1;
      summary.byLanguage[language] += 1;

      if (!NEWSLETTERS[language]) {
        summary.skippedNoContent += 1;
        continue;
      }

      // The guard. Checked before sending, written only after success, so a
      // crash mid-send retries rather than silently dropping someone.
      const sentKey = `sent:${issue}:${email}`;
      if (await env.SUBS.get(sentKey)) {
        summary.alreadySent += 1;
        continue;
      }

      if (!confirm) {
        summary.wouldSend += 1;
        continue;
      }

      try {
        const unsubscribe = await unsubscribeUrl(email, env);
        const newsletter = NEWSLETTERS[language];
        await env.EMAIL.send({
          from: FROM_EMAIL,
          to: email,
          replyTo: REPLY_TO,
          subject: newsletter.subject,
          text: markdownToPlainText(newsletter.markdown, unsubscribe),
          html: markdownToEmailHtml(newsletter.markdown, unsubscribe, language),
          headers: {
            "List-Unsubscribe": `<${unsubscribe}>`,
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "X-Campaign-ID": `tracker-digest-${issue}-${language}`,
          },
        });
        await env.SUBS.put(sentKey, new Date().toISOString());
        summary.sent += 1;
      } catch (error) {
        // Never log the address: these logs are readable in the dashboard.
        console.error("broadcast_send_failed", language, String(error).slice(0, 120));
        summary.failed += 1;
      }
    }
  } while (cursor);

  return json({ ok: true, ...summary }, 200, origin);
}

async function handleUnsubscribe(request, env) {
  if (!env.SUBS || !env.UNSUBSCRIBE_SECRET) {
    return htmlResponse(unsubscribePage(
      "Unable to process this request",
      "The unsubscribe service is temporarily unavailable."
    ), 503);
  }

  const url = new URL(request.url);
  const email = normalizeEmail(url.searchParams.get("email"));
  const suppliedToken = String(url.searchParams.get("token") || "");

  if (!isValidEmail(email) || !suppliedToken) {
    return htmlResponse(unsubscribePage(
      "Invalid unsubscribe link",
      "This link is incomplete or malformed."
    ), 400);
  }

  const expectedToken = await makeUnsubscribeToken(
    email,
    env.UNSUBSCRIBE_SECRET
  );

  if (!constantTimeEqual(suppliedToken, expectedToken)) {
    return htmlResponse(unsubscribePage(
      "Invalid unsubscribe link",
      "This link could not be verified."
    ), 403);
  }

  await env.SUBS.delete(`sub:${email}`);

  await env.SUBS.put(
    `unsub:${email}`,
    JSON.stringify({
      at: new Date().toISOString(),
      list: "tracker-digest",
    })
  );

  return htmlResponse(unsubscribePage(
    "You’re unsubscribed",
    "This address has been removed from the In The Vial tracker digest."
  ));
}

function unsubscribePage(title, message) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <meta name="robots" content="noindex">
  <title>${title} — In The Vial</title>
</head>
<body style="margin:0;background:#f5f3ed;color:#1d211d;font-family:Arial,sans-serif">
  <main style="max-width:620px;margin:0 auto;padding:72px 20px">
    <section style="background:#fff;border:1px solid #d9d7cf;padding:36px">
      <p style="margin:0 0 10px;font-size:13px;letter-spacing:.08em;text-transform:uppercase">
        In The Vial
      </p>
      <h1 style="font-size:30px;line-height:1.2;margin:0 0 18px">
        ${title}
      </h1>
      <p style="font-size:17px;line-height:1.6;margin:0 0 26px">
        ${message}
      </p>
      <a href="${SITE_URL}/#home" style="color:#3f5c46">
        Return to In The Vial
      </a>
    </section>
  </main>
</body>
</html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";


    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: cors(origin),
      });
    }

    if (
      url.pathname === "/api/subscribe" &&
      request.method === "POST"
    ) {
      return handleSubscribe(request, env, origin);
    }

    if (
      url.pathname === "/api/newsletter/preview" &&
      request.method === "POST"
    ) {
      return handleNewsletterPreview(request, env, origin);
    }

    if (
      url.pathname === "/api/newsletter/test" &&
      request.method === "POST"
    ) {
      return handleTestSend(request, env, origin);
    }

    if (
      url.pathname === "/api/newsletter/broadcast" &&
      request.method === "POST"
    ) {
      return handleBroadcast(request, env, origin);
    }

    // GET  = a human clicking the link in the email body.
    // POST = RFC 8058 one-click, which is what Gmail/Yahoo's own "Unsubscribe"
    //        button issues. Without POST here the mail client's button fails,
    //        readers press "spam" instead, and deliverability degrades for
    //        everyone on the list.
    if (
      url.pathname === "/api/unsubscribe" &&
      (request.method === "GET" || request.method === "POST")
    ) {
      return handleUnsubscribe(request, env);
    }

    return json({ ok: false, error: "not_found" }, 404, origin);
  },
};
