# Observability

**Area:** observability · **Levels:** mid → staff+

**One line:** Being able to answer questions about your system's behaviour that you did not think to ask before deploying it.

## Why it exists

Monitoring answers questions you predicted: "is CPU high?" Observability answers ones you did not: "why are requests from this one tenant on this one build slow, but only after a cache miss?" The distinction is not academic, it decides whether an incident is a ten-minute investigation or a four-hour guess.

## signals

| Signal | Shape | Strength | Limit |
|---|---|---|---|
| **Metrics** | numbers over time, pre-aggregated | cheap, constant cost, good for alerting and trends | cardinality is bounded, so you cannot slice by user or request id |
| **Logs** | discrete events with context | arbitrary detail | expensive at volume, hard to aggregate, easy to drown in |
| **Traces** | a causally linked tree of spans across services | shows *where* the latency went across service boundaries | needs propagation everywhere, usually sampled |
| **Profiles** | where CPU and memory go inside a process | finds the hot function metrics cannot name | per-process, not per-request |

They compose: an alert fires on a **metric**, a **trace** localises which service and which span, **logs** for that trace id give the detail, a **profile** explains the CPU. A stack with any one missing has a gap you will feel at 3am.

**Structured logs** (key-value, not prose) are the cheapest big win: they make logs queryable and let you skip a metric entirely by aggregating over them.

## slo-sli

- **SLI** — the measurement. "Proportion of requests served in under 300 ms."
- **SLO** — the target. "99.9% over 28 days."
- **SLA** — the contract, with money attached. Should be strictly looser than the SLO.
- **Error budget** — `1 - SLO`. At 99.9% over 28 days that is ~40 minutes of failure you are *allowed*. Spend it deliberately: ship risk while budget remains, freeze and stabilise when it is gone.

Rules worth holding:

- Measure from **the user's side** where possible. Server-side latency excludes exactly the network problems users have.
- Alert on **symptoms**, not causes. "Checkout error rate above budget" survives a re-architecture; "CPU > 80%" fires during a healthy batch job and stays silent during a deadlock.
- Percentiles, never means. A mean latency hides everything that matters, and **percentiles do not average**: you cannot take the mean of per-host p99s and get the fleet p99. Aggregate from histograms.
- Serving 100 requests per page at p99 = 100 ms means most page loads contain a 100 ms request. Fan-out turns a tail into a median, which is why tail latency is a first-class concern rather than a rounding error.

## cardinality

The dominant cost driver in any metrics system, and the one that surprises people.

- A time series exists per unique **combination** of label values. `endpoint` (50) × `status` (6) × `region` (5) = 1500 series for one metric. Add `user_id` and it is unbounded.
- Never label a metric with a user id, request id, session id, full URL path with ids in it, or an unbounded error string. Those belong in logs or traces, which are built for high cardinality.
- The classic incident: someone adds a label containing a customer identifier, series count goes from thousands to millions, and the metrics backend falls over during the outage it was meant to help diagnose.
- **Exemplars** are the bridge: attach a sample trace id to a histogram bucket, so you can jump from "the p99 bucket" to an actual slow request without labelling the metric.

## tracing

- A **trace id** is created at the entry point and propagated through every call (W3C `traceparent`). Each unit of work is a **span** with a parent, so the trace is a tree.
- The value is proportional to coverage. One un-instrumented service in the middle breaks the tree and hides the very hop you are looking for.
- **Sampling**: head-based (decide at the entry point, cheap, and you keep boring traces and drop interesting ones) or tail-based (buffer the trace, decide after seeing it, so you keep all errors and slow requests, at the cost of buffering everything). Tail-based is what you want and costs more to run.
- Propagate the context through queues too. A trace that stops at the queue boundary hides the asynchronous half of your system, which is often where the latency is.

## alerting

- Every alert must be **actionable**. If the response is "acknowledge and ignore", it is not an alert, it is a dashboard.
- Alert on the error budget burn rate, not on raw thresholds: a fast burn pages, a slow burn opens a ticket. This gives you both urgency levels from one SLO.
- **Multi-window, multi-burn-rate** is the standard shape: a short window catches fast failures without a long delay, a long window suppresses noise from a brief blip.
- Alert fatigue is a real failure mode with a measurable proxy: the fraction of pages that lead to action. Below about half, people stop reading them, and the one that mattered is missed.
- Every page should link to a runbook naming the symptom, the likely causes, and the first three checks.

## Numbers to know

- 99.9% over 28 days = ~40 minutes of error budget. 99.99% = ~4 minutes. Each extra nine is a tenfold cost.
- Cardinality: series count is the product of label cardinalities. One unbounded label is unbounded cost.
- Trace sampling in practice: 0.1-1% head-based for volume, plus keep-everything for errors and slow requests.
- Log volume grows with traffic and with verbosity; a debug-level line per request at 10k req/s is roughly 1 TB/day.

## Related

- [message-queues](message-queues.md) — consumer lag is the metric that matters there
- [load-balancing](load-balancing.md) — health signals and what they hide
- [multi-region](multi-region.md) — measuring per-region, not globally
