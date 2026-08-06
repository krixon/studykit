# Ride matching - interviewer notes

**Do not reveal any of this before the attempt.**

The interesting content is geospatial indexing and the fact that matching is a contended write on a small, geographically local set - which makes it a sharding problem with an unusual key.

## Hidden requirements

- Functional: drivers publish location continuously, riders request a trip, system offers the trip to suitable nearby drivers, driver accepts, both track the trip.
- Non-functional: matching within seconds, location updates are enormous in volume and individually low value, a driver must never be assigned two trips, demand is extremely uneven in space and time.
- Deliberately unstated: pricing, pooling, ETA prediction, cancellation.

## Back-of-envelope they should reach

- 1M active drivers updating location every 4 seconds = 250k writes/second, sustained, forever. **This is the dominant write load and almost none of it is worth durably storing.**
- Matching requests are perhaps 5k/second at peak - four orders of magnitude smaller.
- That asymmetry is the key insight: location is high-volume ephemeral state (memory, overwritten, no durability needed), matching is low-volume contended state (needs correctness).

## Deep dives (pick two or three)

1. **Geospatial index.** Geohash, S2 cells, or H3 hexagons. All map 2D space to a 1D key so it can be indexed and sharded. Push on the boundary problem: a rider at a cell edge has nearby drivers in adjacent cells, so a query must search neighbours too. Then push on cell size - too large and you scan thousands of drivers, too small and you always search many cells. Variable resolution by density is the sophisticated answer, and hexagons are preferred because all neighbours are equidistant, unlike a square grid where diagonals differ.
2. **Sharding by geography.** Natural, and it produces hot shards by construction, because demand concentrates in city centres and at events. Push on how they handle a stadium emptying: dynamic cell splitting, or accepting that some shards are provisioned much larger.
3. **The double-assignment problem.** Two riders matched to the same driver. Needs a compare-and-set on driver state, and an offer with a short TTL so a driver who does not respond is released. Push on the driver-declines and driver-app-crashes paths.
4. **Location write path.** Should not touch durable storage on the hot path. In-memory geospatial store with TTL, asynchronous stream to durable storage for analytics and for the trip record. A candidate writing 250k/second to a relational database has missed the shape of the problem.

## Strong-answer signals

- Separates ephemeral location state from durable trip state, and can say why.
- Names a real geospatial indexing scheme and handles the boundary case.
- Recognises geographic sharding produces hot shards by construction and plans for it.
- Treats the offer as a lease with a TTL rather than an assignment.
- Notices matching quality and matching latency are in tension - waiting longer finds a better match - and treats it as a product decision.

## Common traps

- A naive distance query over all drivers, or a bounding-box scan with no index.
- Persisting every location update durably.
- Assuming uniform geographic distribution.
- Assigning rather than offering, so a non-responding driver blocks the rider.
- Ignoring the cell boundary problem entirely.

## Follow-ups

- A rider is one metre from a cell boundary. Which drivers do you consider?
- A concert ends and 20,000 people request rides in the same square kilometre within two minutes. What happens?
- A driver accepts, then their phone dies. What does the rider experience?
- How do you avoid offering the same trip to two drivers?
- Your in-memory location store loses a node. What is the user-visible impact?
