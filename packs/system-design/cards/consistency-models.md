# Consistency models

**Area:** consistency · **Levels:** senior → staff+

**One line:** A precise statement of which orderings of reads and writes a system may expose, and therefore which surprises your application has to handle.

## Why it exists

"Eventually consistent" says almost nothing: it promises convergence with no bound and no constraint on what you see meanwhile. The models below say exactly what you may observe, which is the difference between a guarantee you can build on and a hope.

## model-spectrum

Strongest to weakest. Each is strictly implementable by the one above it.

| Model | Guarantee | Cost |
|---|---|---|
| **Strict serializability** | transactions appear in a single total order matching real time | consensus per transaction, plus global time |
| **Linearizability** | every operation appears atomic at a point between its call and return; a read sees the latest completed write | a round trip to a quorum, on every operation |
| **Sequential consistency** | one total order all parties agree on, not necessarily matching real time | cheaper; you can observe "stale but consistent" |
| **Causal consistency** | operations related by causality are seen in order; concurrent ones may differ per observer | metadata (version vectors) but no coordination. The strongest model available under partition |
| **Eventual consistency** | replicas converge if writes stop | none. Also promises nothing about what you see before then |

Two distinctions people conflate:

- **Serializability** is about *transactions* (a valid serial order exists). **Linearizability** is about *single objects* in *real time*. They are orthogonal, and "strict serializability" is both.
- **Consistency in ACID** is "the database enforces your invariants", an entirely different word from consistency in CAP.

## session-guarantees

Weaker than linearizability, and usually what users actually notice. These are per-client properties and can be layered on an eventually consistent store cheaply.

- **Read-your-writes.** After you write, you see your write. Absent this, a user edits their profile, the page reloads from a lagging replica, and the edit appears lost.
- **Monotonic reads.** Successive reads never go backwards in time. Absent this, refreshing a page shows a comment, then no comment, then the comment again.
- **Monotonic writes.** Your writes apply in the order you issued them. Absent this, a create-then-update can land as update-then-create.
- **Consistent prefix reads.** If writes happen in an order, no observer sees a suffix without its prefix. Absent this, you see an answer before the question.

Implementation is usually cheap: pin a session to one replica, or carry the client's last-seen version and require the serving replica to be at least that current. Most "eventual consistency is unusable" complaints are solved here rather than by strengthening the store.

## conflict-resolution

Needed whenever two writers can accept a write to the same key concurrently.

- **Last-write-wins.** A timestamp decides. Simple, and it silently destroys one of the writes; clock skew decides which. Only acceptable when a lost concurrent update is genuinely fine.
- **Version vectors.** Detect *that* two writes were concurrent rather than ordered. Detection, not resolution: you still have to choose.
- **CRDTs.** Types whose merge is commutative, associative and idempotent, so replicas converge whatever the order. G-counters, PN-counters, OR-sets, RGA sequences for text. Real and deployed; the constraint is that your operations must fit a lattice, and "debit this account if funds allow" does not.
- **Application-level merge.** Keep both siblings and resolve with domain logic or by asking the user. The honest option, and the expensive one.
- **Avoid the conflict.** Partition writes so one key has one writer. Almost always cheaper than any of the above.

## failure-modes

Anomalies you should be able to name when you see them:

- **Lost update.** Two read-modify-write cycles interleave; one update vanishes. Fix with a compare-and-set on a version, or a transaction with proper isolation.
- **Write skew.** Two transactions each read a set, check an invariant, and write disjoint rows; individually legal, jointly violating the invariant (both on-call engineers go off duty at once). Snapshot isolation permits it; serializable does not.
- **Phantom read.** A predicate query returns different rows on re-execution because another transaction inserted a matching row.
- **Read skew.** A transaction sees part of another's effects: one account before a transfer, the other after. Snapshot isolation prevents this one.
- **Stale read.** A follower serves an old value. Not an isolation anomaly at all, a replication-lag anomaly, and confusing the two sends you to the wrong fix.

Isolation levels are the transactional half of this: read committed permits lost updates and write skew; snapshot isolation removes read skew but permits write skew; serializable removes all of them at a throughput cost. **Snapshot isolation is often labelled "repeatable read", which is not what the SQL standard's repeatable read means.**

## Numbers to know

- Linearizable reads need a quorum round trip: ~1-3 ms same-region, 50-150 ms cross-region.
- Causal consistency needs metadata proportional to the number of writers, not a round trip. That is why it is the strongest model available while partitioned.
- Typical async replication lag: milliseconds normally, seconds to minutes under load. Session guarantees are what make that survivable.

## Related

- [cap-pacelc](cap-pacelc.md): why you cannot have it all
- [replication](replication.md): where lag comes from
- [idempotency](idempotency.md): the practical face of retry-safety
