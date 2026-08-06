# Real-time delivery

**Area:** real-time · **Levels:** mid → staff+

**One line:** Get an update to a user in under a second without asking them to keep asking.

## Why it exists

Polling is simple and wasteful: at a 5-second interval, 1M clients generate 200k requests/second almost all of which return "nothing new". Pushing inverts that: connections are cheap to hold and expensive to establish, so you pay once and send only real events.

The cost is that you now hold state per connected user, and connection state is the hardest kind to scale and to fail over.

## transports

| Transport | Direction | Cost | Right when |
|---|---|---|---|
| **Short polling** | client pulls | wasteful, trivially simple, works everywhere | updates are rare and latency of tens of seconds is fine |
| **Long polling** | client pulls, server holds | a held request per client, plus reconnect churn | you need push semantics through hostile infrastructure |
| **Server-sent events** | server → client only | one HTTP connection, auto-reconnect and event ids built in | a feed, a notification stream, live status. **The under-used default** |
| **WebSocket** | full duplex | a persistent TCP connection per client, own protocol | genuine two-way, low latency: chat, collaboration, games |
| **WebRTC data channels** | peer to peer | complex signalling, NAT traversal | media, or peer-to-peer to avoid a server hop |
| **Push notifications (APNs, FCM)** | server → device | vendor dependency, no ordering guarantees | the app is closed, which no socket can solve |

Choose SSE unless the client genuinely needs to send. It rides on ordinary HTTP, works through proxies, and reconnects with a `Last-Event-ID` without you writing anything.

## fan-out

One event, many recipients. The decision is **when** you do the work.

- **Fan-out on write (push)**: write the item into every recipient's materialised feed at publish time. Reads become a single cheap lookup; a publish by a user with 10M followers becomes 10M writes.
- **Fan-out on read (pull)**: store once, and assemble a recipient's view at read time by querying who they follow. Writes are cheap; reads are a scatter-gather that gets slower as the following list grows.
- **Hybrid**: push for ordinary accounts, pull for a small set of high-fan-out ones, merged at read time. This is what every large system converges on, and knowing *why* it converges there is the point: the distribution is heavily skewed, so the cost is concentrated in a handful of accounts you can special-case.

The threshold ("celebrity" cutoff) is a tunable, and it should be based on measured fan-out cost, not on follower count alone: an account with 1M mostly-inactive followers is cheaper to push than one with 200k active ones.

## presence

"Who is online" is deceptively expensive: it is high-cardinality, high-churn, and interesting to many watchers at once.

- Presence is **soft state**: a heartbeat with a TTL, so a crashed client expires rather than requiring a clean disconnect.
- The cost is not storing it, it is **notifying watchers**. Naively, every status change notifies every contact, so a network of N users with F contacts each is N·F notifications per churn event.
- Standard mitigations: only track presence for users someone is actively watching (an open chat window), batch and debounce changes, and coarsen the state (online / away / offline rather than a precise timestamp).
- Accept staleness. A few seconds of wrong presence is invisible; the machinery to remove it is not.

## backpressure

A slow consumer with a fast producer is the defining failure of push systems, and it fails in an unhelpful way: memory.

- Every connection has a send buffer. A client that cannot keep up makes that buffer grow, and enough of them exhaust the server.
- The options, and each is a product decision: **drop** (fine for presence or telemetry, wrong for chat), **coalesce** (send only the latest state per key: excellent for dashboards and prices), **disconnect** the slow client and let it reconnect and resynchronise, or **block** the producer, which propagates the problem upstream where it may be handled better.
- Bound every buffer explicitly. An unbounded queue converts a slow consumer into an out-of-memory kill of the whole server, taking every other connection with it.
- For catch-up after a disconnect, send a snapshot plus a sequence number rather than replaying the whole event history.

## connection-scaling

- A modern server holds hundreds of thousands of idle connections; the limits are file descriptors, memory per connection (buffers, TLS state), and ephemeral ports on the *outbound* side.
- Connections are **sticky state**. A deploy or a crash disconnects everyone on that node, and they all reconnect at once. Jittered reconnect backoff is not optional, and neither is capping accept rate.
- Routing an event to the right node requires a **connection registry**: user → node, kept in a shared store, or a pub/sub broadcast to every node that filters locally. The registry is exact but is a hot dependency; broadcast is simple but costs O(nodes) per message.
- Load balancers must be configured for long-lived connections: idle timeouts kill sockets that are working correctly but quiet, which is why heartbeats exist at all.
- L4 balancing plus long-lived connections means the pool drifts out of balance and never recovers. Cap connection age to force redistribution.

## Numbers to know

- 1M clients polling every 5s: 200k req/s. The same 1M on sockets: 1M idle connections and only real events on the wire.
- Idle WebSocket: a few KB of kernel and application state per connection, so 100k connections is memory you can budget.
- Heartbeat interval of 30s means up to 30s to notice a dead client. Presence TTL should be 2-3 heartbeats.
- Fan-out on write for a 10M-follower account is 10M writes for one publish. That is the number that forces the hybrid.

## Related

- [message-queues](message-queues.md): what carries events to the delivery tier
- [caching](caching.md): materialised feeds are caches with the same invalidation problem
- [load-balancing](load-balancing.md): long-lived connections break naive balancing
