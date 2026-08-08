# CAP and PACELC

**One line:** During a network partition you must give up consistency or availability; the rest of the time you are trading consistency against latency.

## cap

The theorem, stated carefully because the casual version is wrong.

For a distributed system that may be **partitioned** (P), you cannot have both:

- **C**: linearizability: every read sees the most recent completed write.
- **A**: every request to a **non-failed** node gets a non-error response.

The proof is one sentence: if two nodes cannot communicate and both must answer, they must answer from their own state, and their states can differ.

Three misreadings worth killing:

1. **"Pick two."** P is not optional. Networks partition, so real systems are CP or AP. "CA" describes a single-node system or a wish.
2. **C is not "consistency" in the everyday sense**, and it is not ACID's C. It is linearizability specifically.
3. **CAP only applies during a partition.** Which is rare. Which is why CAP alone is a poor guide to actual design.

## pacelc

The extension that covers the other 99.9% of the time:

> **if (P)artition, then (A)vailability or (C)onsistency; (E)lse, (L)atency or (C)onsistency.

The `else` half is the one that shapes daily behaviour. With no partition at all, waiting for a quorum or a synchronous replica still costs latency, and skipping the wait still costs consistency. Every read and every write pays this, all the time.

Classifications: DynamoDB and Cassandra are **PA/EL** (available and fast, eventually consistent). Spanner and etcd are **PC/EC** (consistent always, and you pay the round trips). MongoDB with majority writes is **PC/EC**; with default writes, closer to **PA/EL**.

Naming the `E` half is what separates a real answer from a memorised one.

## quorum

The mechanism most tunable systems use to move along the spectrum.

With N replicas, requiring W acknowledgements to write and R for a read:

- `W + R > N` guarantees the read set and the write set overlap, so a read sees the latest write.
- `W > N/2` prevents two concurrent writes both succeeding, so writes are ordered.
- `N=3, W=2, R=2` is the standard configuration: tolerates one node down for both reads and writes.
- `W=N, R=1` makes reads fast and writes fragile (one node down stops all writes). `W=1, R=N` is the mirror.

What quorum does **not** give you on its own: it is not linearizability. Overlap guarantees a read sees a value at least as new as the last completed write; without read repair, sequencing, and care about concurrent and partial writes, you can still observe anomalies. Systems that claim linearizability layer a consensus protocol (Raft, Paxos) on top.

## tunability

Many stores let you choose per operation, which is the practical form of all this theory.

- Cassandra: `ONE`, `QUORUM`, `LOCAL_QUORUM`, `ALL` per query. `LOCAL_QUORUM` means "a quorum in my datacentre", which keeps latency regional and gives up cross-region guarantees.
- DynamoDB: eventually consistent reads (default, half the cost) or strongly consistent reads.
- MongoDB: write concern (`w:1`, `w:majority`) and read concern (`local`, `majority`, `linearizable`).
- Relational replicas: read from the leader for correctness, from a follower for capacity.

The design move is to make this choice **per operation, not per system**. Payment authorisation reads at quorum; a profile avatar reads at ONE. Applying the strictest requirement globally is how systems end up slow everywhere for the sake of a few operations.

## examples

| System | Partition behaviour | Normal-operation trade | Class |
|---|---|---|---|
| ZooKeeper, etcd | minority side stops serving writes | pays a round trip for consensus | PC/EC |
| Spanner | refuses to serve outside its guarantees | commit-wait on TrueTime uncertainty | PC/EC |
| Cassandra, DynamoDB | both sides keep serving | tunable; default is fast and eventual | PA/EL |
| Single-leader SQL with async followers | followers serve stale reads; writes stop without a leader | leader reads are consistent, follower reads are stale | PC/EC on the leader, PA/EL on followers |
| DNS | serves whatever it has | cached, stale by design | AP, extremely |

## Numbers to know

- Same-region quorum round trip: ~1-3 ms. Cross-region: 50-150 ms. That gap is the entire `EL` versus `EC` decision.
- `N=3, W=2, R=2` survives one node loss. `N=5, W=3, R=3` survives two, at a higher write cost.

## Related

- [consistency-models](consistency-models.md): the spectrum CAP's "C" sits at one end of
- [replication](replication.md): where these choices are implemented
- [multi-region](multi-region.md): where the latency term dominates
