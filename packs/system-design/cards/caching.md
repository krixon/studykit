# Caching

**Area:** caching · **Levels:** graduate → staff+

**One line:** Keep a copy of expensive-to-fetch data somewhere faster, trading memory and staleness for latency and load.

## Why it exists

Two properties of real workloads make caching pay, and if neither holds it is a net loss:

- **Access is skewed.** A small fraction of keys take most of the traffic, so a small cache covers a large share of reads.
- **Reads dominate writes.** A cached value gets re-read many times before it goes stale.

With uniform access over a large keyspace, hit rate approaches `cache_size / keyspace_size`, which is tiny. You would be paying memory, an extra failure domain and staleness risk for nothing.

## read-strategies

Who populates the cache on a miss.

| Strategy | Who reads the source | What it buys | What it costs |
|---|---|---|---|
| **Cache-aside** (lazy) | the application | app stays in control, survives a cache outage by reading the database directly | miss path is in application code, repeated in every caller |
| **Read-through** | the cache | one place to change, callers only know the cache | the cache becomes a hard dependency; an outage is an outage |
| **Refresh-ahead** | the cache, before expiry | hides the miss latency entirely for predictable hot keys | refreshes keys nobody asked for, wasting origin capacity |

Cache-aside is the default. Reach past it when the miss logic is duplicated across many services.

## write-strategies

When the source of truth gets the write. This is a **different axis** from the read strategy, and confusing the two is the most common error on this topic. You can run cache-aside reads with write-back writes.

| Strategy | Mechanism | Gain | Risk |
|---|---|---|---|
| **Write-through** | write cache and database synchronously | cache never stale relative to the database | every write pays database latency |
| **Write-back** (write-behind) | write cache, flush to the database asynchronously | fastest writes, absorbs bursts | acknowledged writes exist only in the cache until flushed; losing the node loses them |
| **Write-around** | write the database only, leave the cache alone | write-once data never pollutes the cache | the first read is guaranteed cold |

Write-back without replication on the cache tier is silent data loss waiting for a restart.

## eviction

Size and TTL are the two knobs. Everything else is a policy for choosing the victim.

- **LRU** — evict least recently used. The default, and fooled by scans: one large sequential pass evicts the genuinely hot working set in favour of items read once.
- **LFU** — evict least frequently used. Resists scans, adapts slowly to a changing working set.
- **TinyLFU / W-TinyLFU** — a frequency sketch decides *admission*, not just eviction, so a one-off read never displaces a hot key. This is what modern in-process caches use.
- **TTL** — bounds staleness rather than size. Independent of the eviction policy and usually needed as well as one.

## stampede-penetration

Two failures that look similar on a dashboard and need different fixes.

**Cache stampede** (thundering herd): many concurrent misses on a key that **exists**, usually at TTL expiry. Every caller goes to the origin at once.

- Request coalescing / single-flight: one caller populates, the rest wait on it.
- TTL jitter: keys populated together must not expire together.
- Stale-while-revalidate: serve the old value while exactly one refresh runs.

**Cache penetration**: repeated misses for keys that **do not exist**, often hostile traffic with random keys.

- Cache the negative result with a short TTL.
- Bloom filter in front, so a definitely-absent key never reaches the origin.

Single-flight does nothing for penetration when every key is distinct, and a bloom filter does nothing for a stampede on a real key. Naming which one you have is most of the fix.

## hot-key

One key takes a disproportionate share of reads. No sharding or hashing scheme helps, because every scheme still maps that key to exactly one owner.

- **Replicate the value**, not the placement: N suffixed copies read at random, or an in-process L1 on every application node so the hot key never crosses the network.
- Distinguish from a **hot shard** (the key *range* is hot, usually a key-design problem) and from **assignment skew** (the ring divided the space badly, which virtual nodes fix). The separating question: is the key hot, the range hot, or the slot hot?

## cache-economics

- Hit rate matters through its complement. Going from 90% to 99% takes misses from 10% to 1%, which is a **10x** reduction in origin load. Each extra nine divides origin load by ten, so the gain is non-linear and the last few points are worth the most.
- The comparison that justifies a distributed cache is against the **origin read it replaces**, not against local RAM.
- Cache memory is bought at RAM prices to save capacity bought at database prices, which is why the trade usually wins by an order of magnitude.

## placement

Client → CDN or edge → in-process L1 → distributed cache (Redis, Memcached) → database buffer pool.

Each layer only sees the traffic the layer in front of it missed, so hit rates compound and the deepest layers see only the true tail. A shared edge cache cannot cache a personalised response; the design move is to split the personalised fragment from the cacheable shell rather than give up on the layer.

## Numbers to know

| | Order of magnitude |
|---|---|
| RAM read | ~100 ns |
| SSD read | ~100 µs |
| Round trip inside a datacentre | ~0.5 ms |
| Cross-region round trip | 50-150 ms |

## Related

- [consistent-hashing](consistent-hashing.md) — how a distributed cache places keys
- [cdn-edge](cdn-edge.md) — the outermost cache layer
- [consistency-models](consistency-models.md) — what staleness actually means
