// Serves the DuckDB WASM blobs (>25 MiB Workers asset limit) from the
// jsDelivr npm CDN; everything else falls through to Static Assets.
// The CDN files MUST be byte-identical to the build's hashed blobs —
// they are verbatim copies of @duckdb/duckdb-wasm dist files, so bump
// WASM_VERSION whenever that dependency updates and re-verify with:
//   curl -s <url> | md5sum  ==  md5sum build/_app/immutable/assets/*.wasm
// (An R2-bucket variant was tried first and abandoned: jurisdictional
// shadowing made uploads invisible to bindings and public URLs alike.)
const WASM_VERSION = "1.32.0";
const CDN = `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${WASM_VERSION}/dist`;

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const m = url.pathname.match(/^\/_app\/immutable\/assets\/(duckdb-(?:eh|mvp|coi))\.[^/]*\.wasm$/);
    if (m) {
      // Cache-first on the edge: the bytes are content-pinned by WASM_VERSION
      // (deploy-time `make wasm-verify` enforces CDN == build identity), so a
      // cached copy can never go stale within a pinned version.
      const cache = caches.default;
      const cached = await cache.match(req);
      if (cached) return cached;
      const upstream = await fetch(`${CDN}/${m[1]}.wasm`);
      if (!upstream.ok) return new Response("wasm missing from CDN", { status: 502 });
      const res = new Response(upstream.body, {
        headers: {
          "content-type": "application/wasm",
          "cache-control": "public, max-age=31536000, immutable",
        },
      });
      // Clone: one copy to the edge cache, one to the client. A CDN outage
      // after first fill still serves; a version bump changes the URL path
      // (hashed build filename) so it can never serve the wrong bytes.
      // Note: the hashed path means each deploy fills one new key per kind.
      ctx.waitUntil(cache.put(req, res.clone()));
      return res;
    }
    // Content-hashed build files (_app/immutable/…) never change bytes
    // under the same name: serve edge-cached with an immutable year.
    // (Static Assets default here is must-revalidate, i.e. a round trip
    // on every repeat visit — the main repeat-load cost on mobile after
    // the gzipped ~2 MB route bundle.) Anything else passes through.
    if (url.pathname.startsWith("/_app/immutable/")) {
      const cache = caches.default;
      const cached = await cache.match(req);
      if (cached) return cached;
      const res = await env.ASSETS.fetch(req);
      if (res.ok) {
        const fixed = new Response(res.body, {
          status: res.status,
          headers: {
            ...Object.fromEntries(res.headers),
            "cache-control": "public, max-age=31536000, immutable",
          },
        });
        ctx.waitUntil(cache.put(req, fixed.clone()));
        return fixed;
      }
      return res;
    }
    return env.ASSETS.fetch(req);
  },
};
