# CDN and edge

**Area:** geo-cdn · **Levels:** graduate → staff+

**One line:** Push copies of content and some computation close to users, so most requests never cross an ocean or reach your origin.

## Why it exists

Distance is latency and physics sets the floor: light in fibre covers roughly 200 km per millisecond, so London to Sydney is ~80 ms one way *before* any processing. A cache 20 ms away turns a 300 ms page into a 40 ms one, and it does it by removing round trips rather than making anything faster.

The second reason is capacity. A CDN absorbs the traffic your origin never has to be sized for, including the traffic you did not plan for.

## what-it-caches

Cacheable at a shared edge means **the same bytes are correct for many users**.

- Naturally cacheable: static assets, images, video segments, downloads, public API responses.
- Cacheable with care: HTML shells, personalised-looking pages split into a shared shell plus a client-fetched personal fragment.
- Not cacheable at a shared edge: anything keyed to one user's identity, anything `Set-Cookie` touches.

The controls are HTTP headers, and they are the API between you and the CDN:

- `Cache-Control: max-age` — how long a client may reuse it.
- `s-maxage` — how long a *shared* cache may, overriding `max-age`.
- `stale-while-revalidate` — serve the stale copy while one refresh runs behind it. This is stampede protection you get by writing a header.
- `Vary` — which request headers change the response. `Vary: Cookie` on a cookie-bearing site means an effective hit rate of zero, and this is the most common accidental cache defeat.
- `ETag` / `If-None-Match` — revalidation without re-transferring the body. Saves bandwidth, not the round trip.

## invalidation

Three mechanisms, in increasing order of how much you should prefer them:

1. **Purge** — tell the CDN to drop a key. Global propagation is seconds to a minute, so it is not a consistency mechanism. Purging by wildcard or tag is far more usable than purging by URL, and tag support varies by vendor.
2. **Short TTL** — accept bounded staleness and stop coordinating. Cheap and predictable.
3. **Immutable content-addressed URLs** — put a content hash in the filename, cache for a year, and never invalidate anything. The URL changes when the content does, so there is nothing to purge.

Option 3 is the design that removes the problem instead of managing it. Reach for purge only for content whose URL genuinely must stay stable, such as an article page.

## origin-shield

Without one, every edge location that misses goes to your origin independently, so a purge or a cold start means as many origin requests as you have populated locations. An **origin shield** is a designated mid-tier cache that all edges miss *through*, collapsing those into one.

The same idea as request coalescing, applied to a geographic hierarchy: hit rate compounds at each layer, and the origin only sees the true tail.

## edge-compute

Small functions running in the CDN's locations, with a tight CPU budget, no durable local state, and cold-start costs measured in single-digit milliseconds.

Good fits: auth and token checks, redirects, A/B assignment, header rewriting, request routing, personalising a cached shell, bot filtering. All of these turn an uncacheable response into a cacheable one plus a cheap decision.

Bad fits: anything needing your primary database (you have moved the compute but not the data, so you have added a hop), anything with a large working set, anything requiring strong consistency.

The trap is **data gravity**: edge compute is only a win when the data it needs is also at the edge, or when it needs no data at all.

## tls-latency

A new HTTPS connection costs a TCP handshake plus a TLS handshake: 2 round trips with TLS 1.2, 1 with TLS 1.3, 0 with TLS 1.3 session resumption. A CDN's biggest and least discussed win is **terminating that handshake 20 ms away instead of 150 ms away**, then reusing warm, long-lived connections back to origin.

For a first-time visitor on a fresh connection, handshakes can dominate total page time, which is why "but it is all cached" is not the whole story.

## Numbers to know

- Light in fibre: ~200 km/ms, so ~5 ms per 1000 km each way, before any processing.
- Cross-region round trips: 50-150 ms. Same-region: <10 ms. Edge to user: 5-30 ms.
- TLS 1.3 full handshake: 1 RTT. Resumed: 0 RTT.
- CDN purge propagation: seconds to ~1 minute globally. Not a consistency primitive.

## Related

- [caching](caching.md) — the same mechanics, further in
- [multi-region](multi-region.md) — when the data has to move too
- [load-balancing](load-balancing.md) — anycast and the front door
