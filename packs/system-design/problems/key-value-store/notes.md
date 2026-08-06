# Distributed key-value store - interviewer notes

**Do not reveal any of this before the attempt.**

The hardest problem in the pack. It exercises partitioning, replication, consistency and storage engines simultaneously, and the differentiator is whether the candidate *chooses a point on the spectrum and defends it* rather than describing all of them.

## Hidden requirements

- Functional: get, put, delete by key. Possibly TTL, compare-and-set, range scan.
- Non-functional: horizontally scalable, tolerates node and rack failure, single-digit millisecond reads, a stated consistency guarantee, operable by a team that is not you.
- Deliberately unstated: **the consistency model**. This is the point. A candidate who does not ask has skipped the decision that determines every other decision.

## Back-of-envelope they should reach

- 100 TB of data, 3x replication = 300 TB raw. At 10 TB per node that is 30-40 nodes minimum.
- 1M ops/second across 30 nodes = ~33k ops/second per node, which is achievable for an in-memory or SSD-backed engine and not for spinning disks.
- Quorum reads at N=3, W=2, R=2 cost one extra round trip, roughly 1-2 ms within a region.

## Deep dives (pick three)

1. **Partitioning.** Consistent hashing with virtual nodes, or fixed logical shards with a lookup table. Push on: how membership is agreed (gossip versus a coordination service), what happens to reads during a rebalance, and how replicas are chosen so all three do not land on one physical machine or one rack.
2. **Replication and consistency.** Leaderless quorum (Dynamo-style) versus per-partition consensus (Raft group per shard). The trade: quorum is simpler, always writable, and gives you conflicts and read repair; Raft gives linearizability per key and a leader election per shard on failure. Both are correct answers if defended. Push on what W + R > N does and does not guarantee.
3. **Storage engine.** LSM for write throughput and compression, B-tree for predictable read latency. Push on compaction interacting with foreground traffic, bloom filters for absent keys, and what durability the write acknowledgement actually implies.
4. **Failure handling.** Hinted handoff, read repair, Merkle-tree anti-entropy, and what happens when a node is down for a week and returns. Push on the operational question: how does an operator know the cluster is converged?
5. **Operability.** The under-asked dimension and the reason this problem is lead-level: how do you add a node, how do you take one out safely, how do you know when it is done, what do you page on, and what does an operator do when a shard is unavailable.

## Strong-answer signals

- Asks for the consistency requirement first, and lets it drive the rest.
- Picks one design and defends the boundaries, rather than listing options.
- Explicit rack and zone awareness in replica placement.
- Has an answer for "how does a user of this system know their write is durable".
- Talks about operations - drain, rebalance, backup, restore - not just steady state.
- Names something they would deliberately not support (range scans, transactions, secondary indexes) and says why.

## Common traps

- Never fixing the consistency model, so every subsequent answer is conditional.
- Consistent hashing without distinct-node replica selection.
- Quorum described as if it gives linearizability.
- No answer for rebalancing while serving.
- Designing for steady state only, with no operational story.

## Follow-ups

- Trace a put with N=3, W=2 where one replica is down. What does the client see, and what happens later?
- A node is down for a week and comes back. What must happen before it serves reads?
- Two clients write the same key from two regions concurrently. What is the outcome under your design?
- An operator needs to remove a rack for maintenance. Walk me through it.
- Someone asks you to add multi-key transactions. What do you tell them?
