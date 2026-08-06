# Load balancing

**Area:** networking · **Levels:** graduate → staff+

**One line:** Spread requests across a pool of servers so no single one is the limit, and so losing one is survivable.

## Why it exists

Two jobs, often conflated. **Scale**: one machine cannot serve the traffic. **Availability**: any machine can die without taking the service with it. A design that only addresses the first will happily balance traffic onto a dead host.

## l4-l7

| | Layer 4 | Layer 7 |
|---|---|---|
| Sees | IP and port | the full HTTP request |
| Can route on | connection tuple | path, header, cookie, method |
| Cost | very cheap, kernel or hardware speed | parses and often re-encrypts every request |
| TLS | passes through | usually terminates |
| Good for | raw throughput, non-HTTP protocols | canaries, path routing, per-tenant rules, request-level retries |

L4 balances **connections**; L7 balances **requests**. With HTTP/2 or gRPC that distinction bites: many requests are multiplexed over one long-lived connection, so an L4 balancer pins all of them to one backend and the pool goes lopsided. That is the case where L7 (or client-side balancing) stops being optional.

## algorithms

- **Round robin** — simple, correct only when requests cost roughly the same and backends are identical.
- **Weighted round robin** — same, with a capacity weight per backend. The usual answer for a heterogeneous fleet.
- **Least connections** — routes to the backend with the fewest in-flight requests. Adapts to uneven request cost without measuring it.
- **Least response time / EWMA latency** — the best signal for uneven workloads, and the most sensitive to a backend that is fast because it is failing fast.
- **Consistent hashing on a key** — sticky routing when a backend holds per-key state (a session, a lease, a warm cache). See [consistent-hashing](consistent-hashing.md).
- **Power of two choices** — pick two backends at random, send to the less loaded. Almost all the benefit of least-connections with none of the global state; the standard choice for client-side balancing.

## health-checks

- **Passive**: infer from real traffic (error rates, timeouts). Free, but only notices after users have been hurt.
- **Active**: a probe on an interval. Notices before users do, and costs a request per backend per interval.
- **Shallow vs deep**: a shallow check ("the process is listening") stays green while every dependency is down. A deep check ("I can reach my database") goes red on a shared dependency and can take the **entire fleet** out of rotation at once, which is worse than the original fault.

The resolution is that a deep check should mark a host unhealthy only while a quorum of hosts is still healthy. Balancers implement this as a **panic threshold**: below some fraction healthy, ignore health entirely and spread traffic across everything, on the grounds that a degraded backend beats no backend.

## topology

- **DNS** — cheapest global spread, terrible failover: TTLs and resolver caching mean minutes of traffic to a dead site.
- **Anycast** — the same IP announced from many locations, routed to the nearest by BGP. Fast global failover; you do not control which site a client lands on, and a route flap can break long-lived connections.
- **Hardware or cloud L4** — the front door, usually anycast behind the scenes.
- **L7 proxy tier** — routing, retries, canaries, TLS termination.
- **Client-side / service mesh sidecar** — no extra network hop, per-request balancing over multiplexed connections, and the balancing logic ships with the client rather than the platform.

Real systems stack these: anycast to a region, L4 to a proxy tier, L7 proxy to a service, mesh inside it.

## failure-modes

- **Retry storms.** Every layer retrying multiplies load exactly when the system is least able to take it. Budget retries (a cap on the fraction of traffic that may be retries), add jitter, and never retry at more than one layer.
- **Herding after a failover.** All connections re-establish at once against the survivors. Stagger reconnects with jittered backoff.
- **Balancing onto a black hole.** Health checks pass while the backend serves errors quickly. Fast failure looks like low latency to a latency-based algorithm, so it attracts *more* traffic. Track success rate, not just latency.
- **The balancer as a single point of failure.** Needs its own redundancy, and its own capacity headroom for the failover case.
- **Uneven long-lived connections.** See l4-l7 above; the pool drifts out of balance and never recovers without connection recycling (a max connection age).

## Numbers to know

- Health check interval of 5-10s with a 2-3 failure threshold means **15-30 seconds** of blackholing before a dead backend leaves rotation. That is the real detection budget.
- DNS-based failover is bounded below by the TTL plus resolver disobedience: assume minutes, not seconds.

## Related

- [consistent-hashing](consistent-hashing.md) — sticky routing
- [rate-limiting](rate-limiting.md) — what the balancer enforces at the edge
- [observability](observability.md) — how you see the pool going lopsided
