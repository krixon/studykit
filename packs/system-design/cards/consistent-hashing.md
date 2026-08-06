# Consistent hashing

**Area:** partitioning · **Levels:** mid → staff+

**One line:** A placement function where adding or removing a node moves only about `1/N` of the keys instead of nearly all of them.

## definition

With `hash(key) mod N`, changing N changes the divisor, so almost every key maps somewhere new: going from 4 nodes to 5 remaps roughly 80% of them. For a cache that is a total flush; for a database it is a full migration.

Consistent hashing removes N from the function. Keys and nodes are hashed into the same circular space, and a key belongs to the first node clockwise from it. Adding a node only takes keys from its immediate successor. Removing one gives its keys to its successor. Everything else is untouched.

The property, stated precisely: **only `K/N` keys move when a node joins or leaves**, where K is the key count.

## ring-mechanics

- Hash the identifier of each node onto a circle, typically 0 to 2^32.
- Hash each key onto the same circle.
- Walk clockwise from the key; the first node found owns it.
- Lookup is a binary search over the sorted node positions: O(log N), with the ring small enough to hold in memory on every client.
- For replication, keep walking and take the next R **distinct** nodes. Skipping duplicates matters once virtual nodes exist, or all R replicas can land on the same physical machine.

## virtual-nodes

With one point per node, random placement divides the circle badly. The variance is large: with a handful of nodes some own several times the arc of others, and there is no way to fix it without moving nodes.

Give each physical node V positions on the ring (typically 100-200). Load variance falls roughly as `1/sqrt(V)`, so a few hundred virtual nodes gets imbalance into the low single-digit percent.

Two further benefits, both usually more valuable than the balance itself:

- **Departure spreads.** When a node dies, its V arcs each go to a different successor, so the load is absorbed by the whole cluster rather than dumped on one neighbour.
- **Heterogeneous capacity.** Give a machine twice the hardware twice the virtual nodes and it takes twice the keys, with no other change.

Cost: the ring is V times larger to store and search, and rebalancing touches more, smaller ranges.

## rebalancing

- **Join**: the new node claims arcs from several successors and streams those keys across. Until the transfer completes, reads must be served from the old owner or routed to both.
- **Leave (planned)**: hand off before departing.
- **Leave (crash)**: the successor becomes the owner immediately and serves from its replica. If replication factor is 1, those keys are gone.
- **Bounded loads**: a variant that caps any node at `(1 + ε)` times the average, spilling overflow to the next node. It buys tighter balance at the cost of lookups sometimes needing more than one hop.

Ring membership itself has to be agreed. Gossip converges eventually and can serve stale views during a change; a coordination service (etcd, ZooKeeper) gives a consistent view and a dependency.

## alternatives

- **Rendezvous hashing (HRW)** — for each key compute `hash(key, node)` for every node and take the highest. Same minimal-disruption property, no ring to maintain, natural weighting, and trivially correct. Lookup is O(N) rather than O(log N), which is fine for tens of nodes and not for thousands.
- **Jump consistent hash** — O(1) time, no memory, perfectly balanced. Only maps to buckets `0..N-1` and can only add or remove at the *end*, so it cannot express arbitrary node removal. Ideal for a shard count you only ever grow.
- **Maglev hashing** — a lookup table giving O(1) lookups with near-perfect balance and low disruption; designed for load balancers, where lookups massively outnumber membership changes.
- **Fixed logical shards** — pre-split into 1024 shards and map shards to nodes with an explicit table. Not a hash at all: rebalancing is moving whole shards, placement is deliberate, and the table is the source of truth. Frequently the most operable answer.

## hot-key

Consistent hashing balances **keyspace**, not **traffic**. A key read 40% of the time still maps to exactly one node no matter how the ring is arranged, and no number of virtual nodes changes that.

The remedies are at a different layer: replicate the value across nodes with a suffixed key read at random, or keep an in-process L1 cache on every client so the hot key never leaves the process.

Distinguish the three imbalances, because only the third is a hashing problem at all:

| Symptom | Actually | Fix |
|---|---|---|
| one key takes most reads | workload skew | replicate the value, L1 cache |
| one range takes most writes | key-design skew | change the key (prefix, hash, compound) |
| one node owns twice the arc | assignment skew | virtual nodes |

## Numbers to know

- `mod N`: ~`(N-1)/N` of keys move on a change. Consistent hashing: ~`1/N`.
- Virtual nodes: 100-200 per physical node is the usual range; imbalance falls as ~`1/sqrt(V)`.
- Ring lookup: O(log(N·V)) with a sorted array plus binary search.

## Related

- [sharding](sharding.md) — what the ring is placing
- [caching](caching.md) — the classic use, and where hot keys live
- [load-balancing](load-balancing.md) — sticky routing to stateful backends
