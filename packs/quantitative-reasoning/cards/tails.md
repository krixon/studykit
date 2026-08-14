# Tails and percentiles

**One line:** Why the average latency of a system is not the latency anyone experiences, and what happens to a tail when a request touches many things.

## Why it exists

A mean latency answers a question nobody has. Users do not experience the average of their requests; they experience the slow ones, and they remember those. Every serious latency target is a percentile, and percentiles behave in ways that averages do not - they do not add, they do not average, and they get worse as a system is decomposed.

## mean-vs-percentile

A **percentile** is a threshold: p99 = 300 ms means 99% of requests finished within 300 ms. It says nothing about how bad the other 1% is.

- The mean is dragged by outliers and hides them at the same time. A service at 20 ms mean can have a p99 of 2 s, and the mean barely moves when the tail doubles.
- **The mean is not a percentile of anything.** In a right-skewed distribution, which every latency distribution is, the mean sits somewhere around p60-p80. Reporting the mean answers "what is a typical request" badly and "what do my worst users get" not at all.
- p50 is the median and is the honest "typical". Quote p50 and p99 together: p50 describes the system working, p99 describes it failing, and the ratio between them describes how consistent it is.
- **Beyond p99 the numbers get expensive to trust.** p99.9 needs thousands of samples per window to mean anything, and p100 is one unlucky request and a garbage collection pause.

## tail-amplification

The central result. If a request fans out to *n* backends and must wait for all of them, the probability that none of them is slow is the product of the individual probabilities.

With each backend independently fast 99% of the time:

| Fan-out | Chance all are fast | Chance at least one is slow |
|---|---|---|
| 1 | 99.0% | 1.0% |
| 10 | 90.4% | 9.6% |
| 20 | 81.8% | 18.2% |
| 100 | 36.6% | 63.4% |

So a request touching 100 shards, each with a one-in-a-hundred slow path, is slow **63% of the time**. The p99 of the parts has become roughly the p37 of the whole. This is why decomposing a service makes tails worse for free, and why every fan-out design needs one of: fewer backends on the critical path, a hedged request to a second replica, or a partial answer returned on a deadline.

The lever with the best return is usually reducing *n*, because the effect is exponential in it.

## percentile-arithmetic

Three operations that look reasonable and are wrong.

- **You cannot average percentiles.** The mean of each host's p99 is not the fleet's p99. A host serving 1% of traffic contributes equally to the average and negligibly to the true figure. Aggregate the underlying distribution - histogram buckets or a sketch - not the summary.
- **You cannot add percentiles.** Two sequential calls each at p99 = 100 ms does not give p99 = 200 ms for the pair, because the two slow events rarely coincide. The sum's p99 is lower than the sum of the p99s, and its mean is the sum of the means. Means add; percentiles do not.
- **You cannot take a percentile of a percentile.** A weekly p99 computed from seven daily p99s is not a weekly p99.

The rule underneath all three: percentiles are order statistics, and order statistics need the raw distribution.

## retries-and-tails

Retries are the standard tail remedy and the standard cause of an outage.

- A retry on a timeout converts a slow request into two requests. When the cause is transient it works. When the cause is saturation, it adds load exactly where load is the problem - a positive feedback loop, and the mechanism behind most retry storms.
- **Bound the total, not the attempt.** A retry budget expressed as a fraction of overall traffic, typically a few percent, degrades instead of amplifying.
- **Hedging** is the version that helps a tail: send a second request to a different replica after a delay set at about p95, and take the first answer. It costs a few percent extra load and cuts the tail sharply, because it is a bet on independence rather than a bet on the problem clearing.
- Exponential backoff with **jitter**. Without jitter, retries synchronise and arrive as a spike; the retry storm is a coordination problem as much as a load problem.

## measuring-tails

- Measure where the user is. Server-side latency omits queueing in the accept backlog, TLS setup, and the network, which is often most of what the user feels.
- **Sample size decides what you can claim.** To see p99 you need on the order of a thousand requests per window; p99.9 needs tens of thousands. A p99 over a one-minute window on a low-traffic endpoint is noise with a decimal point.
- Histograms with fixed buckets aggregate correctly across hosts and lose precision inside a bucket. Averaged summaries aggregate incorrectly and look precise. Prefer the first.
- **Watch the ratio, not just the level.** p99/p50 rising while both are within target is the earliest signal that a system is losing headroom.

## Numbers to know

- 99% each, 20-way fan-out: 18.2% of requests hit at least one slow backend.
- 99% each, 100-way fan-out: 63.4%.
- p99 needs ~1,000 samples per window, p99.9 needs ~10,000.
- A right-skewed distribution puts its mean around p60-p80.
- Hedging at p95 costs about 5% extra requests.

## Related

- [queueing](queueing.md): where the tail comes from in the first place
- [coincidence](coincidence.md): the same independence argument, pointed at failures
