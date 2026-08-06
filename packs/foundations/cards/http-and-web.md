# HTTP and the web

**Area:** web · **Levels:** graduate → staff+

**One line:** A stateless request-response protocol that every web system is built on, whose statelessness is the source of most of its complications.

## request-response

A request is a method, a path, headers, and optionally a body. A response is a status code, headers, and optionally a body. Nothing else.

The defining property is that HTTP is **stateless**: the server remembers nothing between requests. Everything that feels like state - being logged in, a shopping cart, a wizard step - is reconstructed from something the client sends each time, usually a cookie carrying an identifier.

Connection setup is not free. TCP costs a round trip, TLS costs one or two more, so a fresh HTTPS connection is 2-3 round trips before a byte of your data moves. HTTP/1.1 keep-alive reuses connections; HTTP/2 multiplexes many requests over one; HTTP/3 replaces TCP with QUIC to remove head-of-line blocking.

## methods-status

Methods carry two properties that matter more than their names:

- **Safe**: does not change server state: `GET`, `HEAD`, `OPTIONS`.
- **Idempotent**: repeating it has the same effect as doing it once: `GET`, `PUT`, `DELETE`, `HEAD`. `POST` is neither; `PATCH` usually is not.

This is not pedantry. Browsers, proxies, caches and retry libraries all act on these properties: a `GET` may be prefetched, cached or retried automatically, so putting a state change behind one means it can happen without a user doing anything.

Status classes: `2xx` success, `3xx` redirection, `4xx` the caller must change something, `5xx` we failed and a retry may work. The ones worth knowing precisely: `301` permanent (cached hard by browsers, effectively irreversible), `302`/`307` temporary, `304` not modified, `400` malformed, `401` unauthenticated, `403` authenticated but not allowed, `404` absent, `409` conflict, `422` valid syntax and invalid meaning, `429` rate limited, `500` our bug, `503` try later.

## headers-caching

Headers configure the transfer without touching the body.

- `Content-Type`: what the body is. Getting it wrong is the cause of an enormous share of integration bugs.
- `Cache-Control`: `no-store` (never keep it), `no-cache` (keep, but revalidate before use), `max-age=N`, `private` (browser only, never a shared cache), `public`.
- `ETag` and `If-None-Match`: the server sends a version tag; the client sends it back and gets `304 Not Modified` with no body if unchanged. Saves bandwidth, not the round trip.
- `Vary`: which request headers change the response, so a cache knows to key on them. `Vary: Cookie` on a cookie-bearing site destroys shared caching.
- `Accept-Encoding` / `Content-Encoding`: compression, typically gzip or brotli, routinely 70-80% off a text response.

## cookies-sessions

A cookie is a small value the server sets and the browser returns on every subsequent request to that domain. It is how statelessness is papered over.

Two models:

- **Server-side session**: the cookie holds an opaque id, and the real state lives on the server. Revoking a session is immediate; the server must store and look up session state.
- **Token in the cookie** (a signed JWT, say): the state travels with the request, so the server stores nothing. Revocation becomes the hard problem: a valid token is valid until it expires, so you need a short expiry with refresh, or a deny-list, which reintroduces the server-side lookup you were avoiding.

Flags that are not optional: `HttpOnly` (JavaScript cannot read it, which blunts XSS), `Secure` (HTTPS only), `SameSite=Lax` or `Strict` (mitigates CSRF by not sending the cookie on cross-site requests).

## cors-origins

The **same-origin policy** stops a page on one origin (scheme + host + port) from reading responses from another. It is a browser rule, and it exists because the browser attaches your cookies automatically, so without it any site could read your email by asking for it.

CORS is the mechanism a server uses to opt out of that restriction for specific origins, via `Access-Control-Allow-Origin`. For requests that are not simple, the browser sends a **preflight** `OPTIONS` request first and only proceeds if the response permits it.

Two things people get wrong constantly:

- **CORS is not security for your API.** It restricts browsers. A server, a script or a proxy ignores it entirely, so it protects your users from other websites, not your API from attackers.
- **A CORS error usually means your server did not answer the preflight**, not that the browser is broken.

## Numbers to know

- Fresh HTTPS connection: 2-3 round trips before data. Reused connection: 0.
- gzip on text: typically 70-80% reduction.
- A same-region API call is a few milliseconds; a cross-continent one is 100 ms or more, and no amount of server tuning changes that.

## Related

- [security-basics](security-basics.md): cookies, sessions and what attacks them
- [errors-and-logging](errors-and-logging.md): status codes are an error contract
