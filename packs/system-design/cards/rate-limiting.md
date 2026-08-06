# Rate limiting

**Area:** rate-limiting · **Levels:** graduate → staff+

**One line:** Cap how much work a caller can ask for in a window, so one caller cannot take the service down for everyone.

## Why it exists

Three different jobs wear the same name, and they want different designs:

- **Protection** — keep the service inside its capacity. Cares about total load, not fairness.
- **Fairness** — stop one tenant starving the others. Cares about per-tenant shares.
- **Commercial** — enforce a plan. Cares about being exactly right and explainable on an invoice.

Ask which one before choosing an algorithm. A protection limiter can be sloppy and eventually consistent; a commercial one cannot.

## algorithms

| Algorithm | Mechanism | Bursts | Memory | Defect |
|---|---|---|---|---|
| **Fixed window** | count per calendar window, reset at the boundary | allows 2x the limit across a boundary | one counter per key | the **boundary defect**: a burst at the end of one window plus a burst at the start of the next passes twice the limit |
| **Sliding window log** | store every request timestamp, count those inside the window | exact | O(requests) per key | memory grows with traffic, which is exactly the wrong direction under attack |
| **Sliding window counter** | weighted blend of the current and previous fixed windows | close to exact | two counters per key | approximate at the seam; the standard production compromise |
| **Token bucket** | tokens refill at a constant rate, each request takes one, bucket has a maximum | allows a burst up to the bucket size, then paces | two numbers per key | burst size is a separate decision people forget to make |
| **Leaky bucket** | requests queue and drain at a fixed rate | none: output is perfectly smooth | queue | adds latency, and the queue is a place to lose requests |

Token bucket is the usual default: it expresses "sustained rate R with burst B" directly, which is what an API contract actually says.

## distributed-state

The counter has to be shared, and sharing it costs a round trip on the hot path.

- **Centralised store** (Redis and similar) — exact enough, adds a network hop and a new dependency to every request. The store becomes a capacity limit and a failure domain of its own.
- **Sticky routing** — hash the limit key to a node so one node owns the counter. No coordination, but rebalancing moves counters and the hot tenant is now a hot node.
- **Local leasing** — each node takes a lease of N tokens from a central authority and spends them locally. One round trip per N requests instead of per request.

The cost of leasing is **overshoot**. The floor on overshoot is roughly one lease per node, so with 500 nodes and a lease of 10 tokens, the worst case is 5000 tokens issued beyond the limit. Against a limit of 1,000,000 that is 0.5% and irrelevant. Against a limit of 10 it is a 500x overshoot and the scheme is unusable. **Overshoot has to be judged against the limit, not in absolute terms.**

## contract-keys

What you limit by decides what the limit means.

- **By API key or tenant** — the commercial contract. The right default.
- **By user** — fairness inside a tenant.
- **By IP** — the only option for unauthenticated traffic, and unreliable: NAT and mobile carriers put thousands of users behind one address, while an attacker rents thousands of addresses.
- **By endpoint cost** — a search costing 50x a read should draw 50 tokens, not one. Uniform limits on non-uniform work either strangle cheap calls or leave the expensive path unprotected.

State the limit as a triple: **key, cost, window**. Ambiguity here is where limiters get argued about in production.

## failure-modes

- **Fail open or fail closed.** When the limiter's own store is unavailable, do you admit everything or reject everything? Protection limiters fail open (the service is the thing being protected, and rejecting all traffic is the outage you were avoiding). Commercial limiters usually fail closed. Decide it explicitly; the default is whatever the library chose.
- **Synchronised retries.** Rejecting with no `Retry-After` and no jitter produces a client herd that returns together and gets rejected together.
- **The limiter as the bottleneck.** A synchronous hop to a shared counter on every request adds latency and a dependency, and under attack it is the first thing to fall over.
- **Limiting after the expensive work.** A limit applied after authentication and a database read has already spent most of the cost it was meant to save.

## definitions

- **Throttling** — slowing a caller down (queueing, delaying) rather than rejecting.
- **Rate limiting** — rejecting once the rate is exceeded.
- **Load shedding** — dropping work based on the *server's* health rather than the caller's quota. Complementary, not the same thing: shedding protects you when everyone is behaving.
- **Backpressure** — signalling upstream to send less, rather than dropping. See [realtime-delivery](realtime-delivery.md).
- **Quota** — a longer-horizon cap (per day, per month), usually a billing construct.

`429 Too Many Requests` with `Retry-After` is the contract. `503` says the service is unhealthy, which is a different claim.

## Related

- [load-balancing](load-balancing.md) — where edge limits usually live
- [consistent-hashing](consistent-hashing.md) — sticky routing for counters
- [api-design](api-design.md) — how the limit is communicated
