# Storage engines

**Area:** storage · **Levels:** mid → staff+

**One line:** How a database physically arranges bytes on disk, which decides what it is fast at and what it will never be fast at.

## Why it exists

"Which database?" is usually the wrong question. The answerable one is: **what access pattern does this workload have, and which physical layout serves it?** Two engines with the same SQL interface can differ by an order of magnitude on the same query, purely because of layout.

## btree-vs-lsm

| | B-tree | LSM tree |
|---|---|---|
| Write path | find the page, modify in place | append to an in-memory table, flush sorted runs, compact in the background |
| Write amplification | ~2x (write-ahead log plus page) but random I/O | 10-30x from compaction, but sequential I/O |
| Read path | O(log n), one page read | may check several levels; bloom filters make absent-key reads cheap |
| Space | fragmentation, pages part-full | better compression (sorted immutable runs), plus transient compaction space |
| Latency profile | predictable | good median, tail spikes when compaction and traffic collide |
| Used by | PostgreSQL, MySQL InnoDB, most relational engines | RocksDB, Cassandra, LevelDB, ScyllaDB |

The rule of thumb: **write-heavy favours LSM, read-heavy and latency-sensitive favours B-tree.** The subtlety is that LSM's advantage comes from converting random writes into sequential ones, which mattered enormously on spinning disks and matters less, but still measurably, on NVMe.

## write-amplification

Bytes actually written to the device per byte of logical data.

- B-tree: a one-byte update rewrites a whole page (typically 4-16 KB), plus the write-ahead log entry.
- LSM: each record is rewritten once per compaction level it passes through, so amplification is roughly the number of levels times the fan-out factor.

Why it matters: it consumes device write bandwidth and SSD endurance, and it is the main reason a write-heavy workload can saturate a disk that looks idle in terms of logical throughput. The related quantities are **read amplification** (pages read per logical read) and **space amplification** (bytes stored per logical byte); every engine trades one against the others, and no engine wins all three.

## oltp-vs-olap

| | OLTP | OLAP |
|---|---|---|
| Query shape | fetch or update a few rows by key | scan and aggregate many rows, few columns |
| Layout | **row-oriented**: a row is contiguous | **column-oriented**: a column is contiguous |
| Wins because | one seek gets the whole record | reads only the columns needed, and like values compress 10x+ |
| Indexes | many, selective | few; the scan is the plan |
| Concurrency | thousands of small transactions | a few large queries |

Running analytics on the OLTP database is the classic mistake: a full scan evicts the hot working set from the buffer pool, so the transactional workload gets slower for reasons that do not appear in its own metrics. The standard resolution is a replica for reporting, or an export into a columnar store.

## index-cost

An index is a second copy of some of your data, maintained on every write.

- Every write updates every index on the table. Five indexes make one insert into six writes.
- The **query planner** only benefits if the index matches the predicate's leading columns; a composite index on `(a, b)` serves `WHERE a = ?` and `WHERE a = ? AND b = ?`, and does nothing for `WHERE b = ?`.
- A **covering index**, one that includes every column the query returns, lets the engine answer from the index alone and skip the table entirely. Often the single biggest win available.
- **Low-cardinality** columns (a boolean, a status with three values) rarely justify an index: the planner will choose a scan anyway because a large fraction of rows match.
- Unused indexes are pure cost. Databases can tell you which are never used; almost nobody asks.

## durability

What "the write succeeded" actually promises.

- **Write-ahead log.** Changes go to a sequential log first; the log is what makes crash recovery possible. Commit means the log entry is durable, not that the data pages have been updated.
- **fsync** is where the promise is really made. A write acknowledged before fsync is durable only against process death, not against machine death. Many systems batch fsyncs (group commit) to trade a millisecond of latency for a large throughput gain.
- **Replication changes the unit.** Acknowledging after a quorum of replicas have the log entry is stronger than one machine's fsync, because it survives that machine's disk.
- **Checkpointing** bounds recovery time by periodically making pages consistent so replay starts from a recent point. Longer checkpoint intervals mean less steady-state I/O and slower recovery.

Ask of any datastore: what exactly is durable when it returns success, and against which failures? The answers vary far more than the marketing does.

## Numbers to know

- Page size: typically 4-16 KB. A single-byte update rewrites all of it.
- LSM write amplification: 10-30x. B-tree: ~2x, but random rather than sequential.
- Columnar compression on real data: 5-20x, which is why scans are cheaper than the row count suggests.
- NVMe random read ~100 µs; sequential throughput in GB/s. Both far above spinning disk, and the gap between random and sequential is smaller but still real.

## Related

- [sharding](sharding.md) — when one engine is not enough
- [replication](replication.md) — durability beyond one disk
- [caching](caching.md) — the buffer pool is a cache with the same failure modes
