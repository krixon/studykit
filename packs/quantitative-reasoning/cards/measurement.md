# Measurement and sampling

**One line:** Whether a number you have collected supports the claim you are about to make with it.

## Why it exists

The arithmetic in the other topics assumes its inputs mean something. Most production numbers do not, for reasons that have nothing to do with the arithmetic: too few samples, samples drawn from the wrong population, aggregation that destroys the quantity, or a comparison against a baseline that was not comparable. A confident decision from a bad measurement is worse than no measurement, because it is not revisited.

## sample-size

- The uncertainty in an estimated proportion falls as **1/sqrt(n)**. Four times the samples halves the error bar, which is why precision is expensive and order-of-magnitude confidence is cheap.
- A rough interval on a proportion is `p ± 1/sqrt(n)`. At n = 100 that is ±10 points, which is too wide to support most conclusions people draw from a hundred requests.
- For a **percentile** you need enough samples above the percentile to have any resolution: p99 needs on the order of 1,000 per window and p99.9 needs 10,000. Below that the figure moves because of who arrived, not because of what changed.
- **Rare events need exposure, not time.** To see a one-in-ten-thousand fault with reasonable confidence you need on the order of 30,000 trials. A ten-minute test at 10 requests/second is 6,000 and will usually see nothing, which is not evidence of absence.
- If `np` is the expected count, seeing zero occurrences is unremarkable whenever `np` is near or below 1.

## sampling-bias

Whether the sample represents the population, which no amount of extra samples fixes.

- **Survivorship.** Latency measured only over completed requests excludes the ones that timed out, so the metric improves as the system gets worse. Every latency figure needs its treatment of failures stated.
- **Head-based trace sampling** at 1% keeps 1% of everything, so it keeps 1% of the rare slow traces you actually wanted. Tail-based sampling decides after seeing the outcome and keeps the interesting ones, at the cost of buffering.
- **Coordinated omission** is the subtle one: a load generator that waits for a response before sending the next request stops measuring during exactly the interval the system was slow, so the worst behaviour is under-sampled and the tail is understated, often by a lot. A generator must issue at the intended rate regardless of responses.
- **Who is in the sample.** Client-side metrics from users whose requests failed to load the reporting script are missing; the population is "users for whom things mostly worked".

## load-test-validity

A load test measures the system you built in the test, and the differences from production are the result.

- **Working set.** Synthetic keys drawn uniformly defeat every cache, and real traffic is skewed. A test can be an order of magnitude pessimistic on cache hit rate or optimistic on database load, depending on which way the synthesis is wrong.
- **Data volume.** Query plans change with table size. A test against a small dataset validates correctness and tells you nothing about the plan production will choose.
- **Cold versus warm.** JIT compilation, connection pools, page cache and CDN fill mean the first minutes are not the steady state. Discard the ramp.
- **Find the knee, do not confirm a target.** Ramp until throughput stops rising and latency turns up, and report that point. A test that confirms the system handles the target load leaves you not knowing whether the margin is 5% or 5x, and from the [universal scalability law](capacity.md) throughput may decline past the peak rather than plateau.
- **One variable.** A test with a new instance type, a new build and a new dataset produces one number and no attribution.

## aggregation-traps

- **Averaging percentiles across hosts or windows is wrong**, and the wrongness is invisible. Aggregate the distribution, not the summary. See [tails](tails.md).
- **Simpson's paradox.** An overall rate can move opposite to every subgroup's rate when the mix of subgroups shifts. A latency improvement in every endpoint with an overall regression means traffic moved towards the slow endpoints, and the aggregate is describing the mix rather than the system.
- **Rate versus ratio.** Errors per second and error rate diverge when traffic changes. Alerting on the count fires during a traffic spike that is behaving correctly and stays quiet during an outage where traffic collapsed.
- **Resolution loss.** A one-minute average hides a fifteen-second saturation entirely, and a five-minute one hides most incidents. The window has to be shorter than the event you want to detect.
- **Averaging a ratio of averages** is not the ratio. Compute the ratio from summed numerators and denominators.

## before-after

- A change compared against last week is confounded by everything else that differs about last week: day of the week, a release, a marketing campaign, the weather. **Prefer a concurrent control** - a canary taking a share of live traffic - to a historical one.
- **Regression to the mean** makes any intervention triggered by an unusually bad period look effective, because the period was going to improve anyway. This is the most common way a fix gets credited for a recovery it did not cause.
- Decide the metric and the threshold **before** looking. Choosing which metric to report after seeing the data is how noise becomes a result.
- Quote an interval, not a point. "3% faster" with an unstated error bar of ±8% is not a finding, and the honest version of that sentence is that the change was too small to detect.
- **A/A test your comparison first.** Run the two arms with no difference between them; whatever difference you see is your noise floor, and no result smaller than it means anything.

## Numbers to know

- Error falls as 1/sqrt(n): 4x the samples halves the interval. Rough interval `p ± 1/sqrt(n)`.
- p99 needs ~1,000 samples per window; p99.9 needs ~10,000.
- Seeing a one-in-10,000 event with confidence needs ~30,000 trials.
- `np` at or below 1 makes zero observations unremarkable.
- An averaging window hides any event shorter than itself.

## Related

- [tails](tails.md): the percentiles this topic is telling you not to trust
- [coincidence](coincidence.md): how often a rare thing should have appeared
