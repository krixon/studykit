# Sharding and partitioning

**Area:** partitioning · **Levels:** mid → staff+

**One line:** Split one dataset across many machines so that capacity, not one server's limits, sets the ceiling.

## Why it exists

Replication gives you read capacity and availability; every node still holds the whole dataset, so the *write* rate and the *storage size* stay bounded by one machine. Sharding is the only tool that moves those two ceilings. It is also the one that costs you transactions, joins and operational simplicity, so it comes after every cheaper option: a bigger box, a read replica, an archive of cold rows.

## partition-schemes

| Scheme | Mechanism | Range queries | Balance | Bites you when |
|---|---|---|---|---|
| **Range** | contiguous key ranges per shard | excellent | poor if the key is sequential | the key correlates with time, so all writes land on the last shard |
| **Hash** | `hash(key) mod N` or a hash ring | destroyed (a scan touches every shard) | very good | you need ordered scans, or you add a node and `mod N` remaps almost everything |
| **Directory / lookup** | an explicit map from key to shard | as good as you build | perfect, you place manually | the directory is a lookup on every request and a single point of failure |
| **Geographic** | by region or jurisdiction | good within a region | follows the population, so it is uneven by construction | a user moves, or a query spans regions |

Hash with a ring (see [consistent-hashing](consistent-hashing.md)) is the common default because it makes adding a node cheap. Range is right when scans dominate. Directory is right when you need to place specific tenants deliberately, which is common in B2B.

## shard-key

The single highest-leverage decision, and the hardest to change.

A good key: has high cardinality, spreads writes evenly, and is present on the read path so most queries hit one shard. That last property is what people forget — a perfectly balanced key that is not in the query predicate turns every read into a scatter-gather across the fleet.

Failure patterns:

- **Monotonic key** (timestamp, auto-increment id). Perfectly ordered, perfectly hot: all writes go to the newest shard.
- **Low cardinality** (country, plan tier). Cannot be spread past the number of distinct values, and the values are not equally sized.
- **Key not in the query** — every read is a scatter-gather; p99 becomes the slowest shard's p99, and slow-shard risk multiplies by the fan-out.
- **Composite key ordered wrongly** — `(day, user)` puts a day on one shard; `(user, day)` spreads users and keeps a user's history together.

## cross-shard-tx

Once data spans shards, a single transaction spanning them costs a distributed commit.

- **Two-phase commit** — atomic, and blocks: if the coordinator dies after prepare, participants hold locks until it returns. Acceptable at low volume, poor for anything on the request path.
- **Saga** — a sequence of local transactions with compensating actions on failure. No locks, no atomicity: intermediate states are visible, and compensation is application logic that must itself be idempotent.
- **Avoid it** — the answer most designs should reach. Choose the shard key so the transactional unit lives on one shard: an order and its lines, an account and its ledger entries. "One shard per transaction boundary" is a design constraint worth paying for.

Cross-shard **reads** are cheaper but not free: scatter-gather makes tail latency the maximum of N shards, so p99 degrades as fan-out rises even when every shard is healthy.

## resharding

Splitting shards on a live system is where sharding projects actually fail.

- `hash(key) mod N` remaps roughly `(N-1)/N` of all keys when N changes. Effectively a full data migration.
- **Consistent hashing** moves only `1/N` of keys.
- **Pre-splitting into logical shards** (say 1024 of them) mapped to a smaller number of physical nodes makes rebalancing a matter of moving whole logical shards, with no rehashing at all. This is what most mature systems do, and it costs almost nothing to decide up front.

A live resharding needs: dual writes to old and new placement, a backfill of historical data, a verification pass comparing both, a read cutover, and a rollback path at every step. Plan it as a project, not a task.

## hot-shard

One shard takes disproportionate load. Diagnose the cause before reaching for a remedy, because they need different ones:

- **Hot key** — one key is popular. No partitioning scheme helps, because every scheme maps it to one owner. Replicate the value (in-process cache, N suffixed copies).
- **Hot range** — the key correlates with time or sequence, so the hot region moves but is always singular. Fix the key design (prefix, hash, or compound).
- **Assignment skew** — keys and traffic are uniform, the ring simply divided the space badly. Virtual nodes fix this one, and only this one.

## replication-vs-sharding

They solve different problems and are almost always used together.

| | Sharding | Replication |
|---|---|---|
| Adds | write capacity, storage capacity | read capacity, availability, durability |
| Each node holds | a slice | a full copy |
| Losing a node | loses that slice, unless replicated | loses nothing |
| Costs | cross-shard queries and transactions | consistency (lag) or latency (sync) |

Shards are replicated: each shard is a replica group. Answering "shard or replicate?" as an either/or is a common misread of the question.

## Numbers to know

- `mod N` resharding moves ~`(N-1)/N` of keys. Consistent hashing moves ~`1/N`.
- Scatter-gather across N shards: expected p99 approaches the max of N shard p99s. Fan-out is a tail-latency multiplier.
- A single well-tuned relational node handles single-digit TB and thousands of writes/second. Below that, sharding is usually premature.

## Related

- [consistent-hashing](consistent-hashing.md) — the placement function
- [replication](replication.md) — the other axis
- [cap-pacelc](cap-pacelc.md) — what a partition costs you
