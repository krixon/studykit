# Replication

**Area:** storage · **Levels:** mid → staff+

**One line:** Keep the same data on more than one machine, buying durability, read capacity and availability, and paying in consistency or latency.

## Why it exists

Three distinct goals, and confusing them produces the wrong topology:

- **Durability** — the data survives losing a machine, a rack or a region.
- **Availability** — the service survives losing a machine.
- **Read scale** — more copies means more read capacity.

Only the third is about performance, and it is the one that fails silently when replication lag is ignored.

## topologies

| Topology | Mechanism | Strong when | Weak when |
|---|---|---|---|
| **Single leader** | one writer, followers replicate | almost always: no write conflicts by construction | write throughput is capped by one node; failover is a real event |
| **Multi-leader** | several writers, replicating to each other | multi-region writes, offline-capable clients | concurrent writes to the same key conflict and *something* must resolve them |
| **Leaderless (quorum)** | clients write to R of N, read from W of N | high availability, no failover step | needs read repair and anti-entropy; `W + R > N` is necessary, not sufficient |

Single leader is the default and should be argued *out of*, not into. Multi-leader is a decision to accept conflict resolution as a permanent part of the system.

## sync-vs-async

- **Synchronous** — the leader waits for the follower to acknowledge. No data loss on failover, and the write latency is the slow follower's latency. One stalled follower stalls all writes unless you can fall back.
- **Asynchronous** — the leader acknowledges immediately and ships changes behind. Fast, and a failover loses whatever had not shipped.
- **Semi-synchronous** — wait for *one* follower (or a quorum), not all. The usual compromise: bounded loss, bounded latency cost. This is what "wait for a quorum" means in practice.

The honest way to state the choice is in terms of **RPO**: async replication has a non-zero recovery point objective equal to the lag at the moment of failure, and you should know that number.

## lag-effects

Asynchronous followers are behind, and the anomalies that produces have names and standard fixes:

- **Read-your-writes** — a user writes, then reads from a lagging follower and sees the old value. Fix: route that user's reads to the leader for a bounded window, or track the write position and require a follower at least that current.
- **Monotonic reads** — successive reads hit followers with different lag and time appears to move backwards. Fix: pin a user to one replica.
- **Consistent prefix** — with sharded replication, causally related writes arrive out of order and an answer appears before its question. Fix: keep causally related data in one partition, or carry causal metadata.

These are exactly the [session guarantees](consistency-models.md). Replication lag is where they stop being theory.

## failover

The hard part is not promoting a follower, it is everything around it.

- **Detection.** Distinguishing a dead leader from a slow one is undecidable in an asynchronous network. Every timeout is a bet: too short and you fail over on a GC pause, too long and you extend the outage.
- **Split brain.** Two nodes both believing they lead, both accepting writes. Prevention is fencing: a monotonically increasing epoch or lease that storage rejects if stale. This is the failure that loses data quietly.
- **Lost writes.** Promoting the most up-to-date follower still discards anything the old leader acknowledged but had not shipped. With async replication, some acknowledged writes are gone. Decide in advance whether that is acceptable, because the alternative is synchronous replication and its latency.
- **The thundering reconnect.** Every client reconnects at once to the new leader. Jittered backoff, or the failover itself becomes the outage.

Automatic failover trades a rarer, larger, human-timed outage for more frequent, smaller, automatic ones. That is usually the right trade, and it is a trade.

## conflict-handling

Only arises with multi-leader or leaderless writes.

- **Last-write-wins** by timestamp. Simple, and silently discards data; clock skew decides which write survives. Acceptable only when losing a concurrent update is genuinely fine.
- **Version vectors** — detect that two writes were concurrent rather than ordered. Detection is not resolution: you still have to decide.
- **CRDTs** — data types whose merge is commutative, associative and idempotent, so any order converges. Real, and they constrain what operations you can offer: counters, sets, and text sequences are solved; "transfer money" is not.
- **Application resolution** — keep both versions and let the user or a domain rule decide. The most honest answer, and the most work.
- **Avoid conflicts** — route all writes for a given key to one region. Almost always cheaper than resolving them.

## Numbers to know

- Same-region synchronous replication: adds ~1 ms to a write. Cross-region: adds the round trip, 50-150 ms.
- Async replication lag: normally milliseconds, and seconds to minutes under load, a large write burst, or a long-running query on the follower.
- Quorum: `W + R > N` guarantees overlap. `N=3, W=2, R=2` is the standard configuration.

## Related

- [cap-pacelc](cap-pacelc.md) — the formal version of this tradeoff
- [consistency-models](consistency-models.md) — what the anomalies are called
- [sharding](sharding.md) — the orthogonal axis
