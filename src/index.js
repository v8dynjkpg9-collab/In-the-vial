/**
 * Site Worker for in-the-vial.com.
 *
 * The site is one index.html served at twelve URLs. The router inside that file
 * rewrites <title>, description, canonical and hreflang on load — which works
 * for anything that executes JavaScript, and not at all for anything that does
 * not. Slack, X, Facebook, LinkedIn and iMessage do not, so every shared link
 * previewed as the homepage regardless of which page it pointed at.
 *
 * This rewrites the same tags server-side, before the bytes leave the edge, so
 * the correct title and description are in the HTML as delivered.
 *
 * Only page routes reach this Worker (see run_worker_first in wrangler.jsonc).
 * Everything else — fonts, tracker.json, _redirects, honest 404s — stays with
 * the asset layer, which is better at it.
 */
import { ORIGIN, ROUTES } from "./routes.js";

const BY_SLUG = new Map(ROUTES.map((r) => [r.slug, r]));

/** Canonical URL for a route in a language. Mirrors urlFor() in index.html. */
function urlFor(route, lang) {
  return ORIGIN + route.slug + (lang === "es" ? "?lang=es" : "");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const route = BY_SLUG.get(path);

    // Not a page route: hand straight back to the asset layer.
    if (!route) return env.ASSETS.fetch(request);

    // Every route renders the same document. Ask for it by its canonical path
    // ("/" — never "/index.html", which the asset layer 307s to "/"), and send
    // no conditional headers: a 304 keyed to the shared document would let a
    // client reuse another route's cached <head>.
    const res = await env.ASSETS.fetch(new Request(new URL("/", url), {
      method: "GET",
      redirect: "manual",
    }));

    const type = res.headers.get("content-type") || "";
    if (!res.ok || !type.includes("text/html")) return res;

    const lang = url.searchParams.get("lang") === "es" ? "es" : "en";
    const copy = route[lang] || route.en;
    const canonical = urlFor(route, lang);
    const set = (attr, value) => ({
      element: (el) => el.setAttribute(attr, value),
    });

    const rewritten = new HTMLRewriter()
      .on("html", set("lang", lang))
      .on("title", { element: (el) => el.setInnerContent(copy.title) })
      .on('meta[name="description"]', set("content", copy.desc))
      .on('meta[property="og:title"]', set("content", copy.title))
      .on('meta[property="og:description"]', set("content", copy.desc))
      .on('meta[property="og:url"]', set("content", canonical))
      .on('meta[property="og:locale"]', set("content", lang === "es" ? "es_ES" : "en_US"))
      .on('meta[property="og:locale:alternate"]', set("content", lang === "es" ? "en_US" : "es_ES"))
      .on('link[rel="canonical"]', set("href", canonical))
      .on('link[hreflang="en"]', set("href", urlFor(route, "en")))
      .on('link[hreflang="es"]', set("href", urlFor(route, "es")))
      .on('link[hreflang="x-default"]', set("href", urlFor(route, "en")))
      .transform(res);

    // The upstream ETag describes "/", so twelve URLs would share one validator
    // and a revalidation could serve the wrong page's head. Drop it; Vary on
    // the query string, since ?lang= changes the response.
    const headers = new Headers(rewritten.headers);
    headers.delete("etag");
    headers.set("vary", "Accept-Encoding");
    headers.set("x-itv-route", route.view);

    return new Response(rewritten.body, { status: res.status, headers });
  },
};
