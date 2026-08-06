# Metrics and monitoring pipeline - interviewer notes

**Do not reveal any of this before the attempt.**

Two things make this problem interesting and both are easy to miss: cardinality is the cost driver, and the system must be *more* available than everything it monitors.

## Hidden requirements

- Functional: ingest metrics, store time series, query with aggregation over time and dimensions, evaluate alert rules, dashboards.
- Non-functional: must survive the incidents it is meant to diagnose, ingest is write-heavy and never stops, queries are bursty and mostly recent, retention tiered (high resolution recent, downsampled older).
- Deliberately unstated: push versus pull collection, retention periods, multi-tenancy, whether logs and traces are in scope.

## Back-of-envelope they should reach

- 10,000 hosts × 1000 series each = 10M active series. At one point per 10 seconds that is 1M points/second.
- Naive storage at 16 bytes/point is 16 MB/s, ~1.4 TB/day. **With delta-of-delta and XOR compression it is closer to 1-2 bytes/point**, so ~100-200 GB/day. Knowing compression changes the answer by 10x is the number that matters here.
- Query patterns: 95% of queries touch the last few hours, which justifies a hot/cold tier split.

## Deep dives (pick two or three)

1. **Cardinality.** Series count is the product of label cardinalities, so one label containing a user id or request id is unbounded and takes the system down. Push on defences: per-tenant series limits, rejecting new series past a threshold rather than dying, and surfacing the top cardinality contributors so a team can see what they did. This is the single most important part of the answer.
2. **Storage engine.** Time-series specific: append-only, columnar per series, delta-of-delta encoding for timestamps, XOR for float values, immutable blocks per time window, downsampling into lower-resolution blocks as data ages. Push on why a general relational database is the wrong tool - the access pattern is scan-a-few-columns-over-a-time-range, which is columnar OLAP work.
3. **Push versus pull.** Pull (the collector scrapes targets) gives the collector a health signal for free and needs service discovery. Push (agents send) works for short-lived jobs and through network boundaries but needs its own overload protection. Most large systems run both.
4. **Alerting and availability.** Alert evaluation is a query workload on a schedule, competing with humans for the same resources at exactly the wrong moment. The examinable point is that the monitoring system must fail independently of what it monitors - separate infrastructure, separate region, and an out-of-band path for the alert that says monitoring is down.

## Strong-answer signals

- Leads with cardinality as the cost driver.
- Compression as a first-class design element with a number attached.
- Tiered retention and downsampling, with a reason based on query distribution.
- Explicit independence of the monitoring stack from the monitored stack.
- Notices alert evaluation is a read workload that spikes during incidents.

## Common traps

- Storing metrics in a relational database with no comment on the access pattern.
- No cardinality control, so the design dies the first time someone adds a bad label.
- Monitoring hosted on the infrastructure it monitors.
- Treating alert evaluation as free.
- Ignoring downsampling, then quoting a storage number that is 10x too large.

## Follow-ups

- A team ships a metric labelled with request id. What happens over the next ten minutes, and what should have happened instead?
- Your region loses network. How do you find out?
- An engineer queries 90 days of data across 10,000 series. What do you do?
- How do you keep alerting working while the query tier is overloaded?
- What would you delete from this design if you had a quarter of the budget?
