# Capacity and growth

**One line:** How much room is left, how fast it is disappearing, and why adding machines stops helping sooner than the arithmetic suggests.

## Why it exists

Capacity questions get answered with the wrong quantity. "We are at 40% CPU" is not headroom if the bottleneck is a connection pool. "We doubled the fleet" is not double the throughput if a tenth of the work is serial. And a growth rate quoted per month tells you nothing until you compare it to the interval in which you can act.

## headroom

Headroom is the distance between current load and the load at which the system stops meeting its target. Two things make it harder than a subtraction.

- **The target is a latency, not a limit.** From [queueing](queueing.md), latency explodes near saturation, so usable capacity is the load at which you still meet the percentile, typically 60-70% utilisation rather than 100%. Headroom measured against 100% is roughly double the truth.
- **Headroom is set by the first constraint to bind, not by the resource you happen to graph.** CPU, memory, connection pool, file descriptors, downstream quota, database connections, a licence count: the answer is the minimum over all of them, and it is frequently not the one on the dashboard.

Express it as **time, not percentage**. "We have 30% headroom" invites nobody to act; "at the current growth rate we run out in seven weeks, and provisioning takes three" is a decision. The number that matters is headroom minus lead time.

For a fleet, the useful figure is **N+1 or N+2 capacity**: can you still meet the target with one or two members gone? A pool at 70% utilisation with three members is at 105% with one lost, which is an outage triggered by an ordinary event.

## amdahl

Speedup from parallelism is capped by the fraction of the work that cannot be parallelised. With serial fraction *s* on *p* processors:

**speedup = 1 / (s + (1 - s)/p)**, tending to **1/s** as *p* grows.

| Serial fraction | Max speedup ever | Speedup on 16 |
|---|---|---|
| 5% | 20x | 9.1x |
| 10% | 10x | 6.4x |
| 20% | 5x | 4.0x |

10% serial means 16 machines buy 6.4x, and no number of machines ever buys more than 10x. The lesson is where to spend effort: removing serial work raises the ceiling, adding hardware only approaches it.

In real systems the serial fraction is usually a shared thing - a lock, a leader, a single database, a global counter, a sequence generator. Find it before buying machines.

The **universal scalability law** adds the term Amdahl leaves out: beyond some point, coordination between workers costs more than the work they add, so throughput does not plateau, it **declines**. Any system with contention has a peak concurrency after which more workers make it slower, which is why a load test should look for the peak rather than assume monotonicity.

## growth-rates

- **Compounding is the thing people get wrong.** 10% a month is 3.1x a year, not 2.2x. `(1.1)^12 = 3.14`.
- The doubling time of a compounding rate is about **70 / percent per period**. 10% a month doubles in seven months; 5% a week doubles in fourteen weeks.
- Distinguish growth in **users** from growth in **work**. Work per user often grows too, so the two multiply: 50% more users each doing 50% more is 2.25x, not 2x. Social and graph-shaped features can be worse than linear in users.
- Extrapolate over the horizon you can act in, and no further. A twelve-month projection from three noisy months is arithmetic dressed as forecasting; a six-week projection that beats your three-week provisioning lead time is useful.

## storage-growth

Storage is a flow integrated over a retention window, and it is where estimates most often lose a factor of a thousand.

- Steady state = ingest rate x retention. 10 MB/s retained for 30 days is about 26 TB, and it stops growing at that point - which is the difference between a bounded and an unbounded cost.
- **Count every copy.** Replication factor, backups, snapshot chains, secondary indexes and the read replica each multiply the raw figure. A 3x replication with 30 days of daily snapshots is not 3x.
- Indexes and write amplification are frequently larger than the data. An LSM engine writes 10-30x the logical bytes, which is a device-lifetime and IOPS question rather than a capacity one.
- Compression is the cheapest lever on text, at 70-80%, and does nothing for data that is already compressed. Know which you have before assuming either.
- Retention is the only lever with unbounded return: everything else is a multiplier on a growing number, and retention bounds it.

## cost-per-unit

- Reduce cost to a **unit rate** before comparing anything: cost per request, per user per month, per GB stored, per GB egressed. Totals are incomparable across services of different sizes; unit rates are.
- Fixed and marginal cost behave differently. A cost dominated by a fixed reservation gets cheaper per unit as you grow and cannot be reduced by using less; a marginal cost does the opposite.
- **Egress is usually the surprise.** Compute and storage prices are familiar and cross-region or internet egress frequently dominates a design's bill, which is a reason to move computation to data rather than the reverse.
- The efficiency figure worth tracking is cost per unit against time. Total cost rising with growth is expected; cost per request rising means something is scaling worse than linearly, and that is the signal.

## Numbers to know

- Amdahl: 10% serial caps speedup at 10x, and gives 6.4x on 16 machines.
- Doubling time is about 70 / percent per period. 10% a month doubles in 7 months, 3.1x a year.
- Storage steady state = rate x retention. 10 MB/s for 30 days is ~26 TB.
- Usable utilisation for latency-sensitive work is 60-70%, so headroom against 100% is roughly double the truth.
- A three-member pool at 70% is at 105% after losing one.

## Related

- [queueing](queueing.md): why usable capacity is well short of full
- [estimation](estimation.md): the arithmetic these decisions rest on
