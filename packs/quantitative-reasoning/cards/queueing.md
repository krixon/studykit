# Queueing intuition

**One line:** Why latency does not rise smoothly with load but explodes near saturation, and the two formulas that let you predict where.

## Why it exists

Almost everyone's mental model of load is linear: twice the traffic, twice the response time. The real curve is flat and then vertical, and the interesting part is a narrow band of utilisation nobody plans for. This is why a system that has been fine for months falls over on a 20% traffic increase, and why "we have plenty of CPU headroom" is compatible with a service that is already unusable.

You do not need queueing theory. You need two results and the shape of one curve.

## littles-law

**L = λW.** Items in the system equals arrival rate times time in the system.

It is an identity, not a model: no distribution is assumed, nothing has to be random, and it holds for any stable system over any long enough interval. That makes it the most reliably useful formula in the subject.

What it is actually for is computing the third quantity when you know two:

- 2,000 requests/second at 50 ms each means **100 requests in flight**. That is your concurrency, and therefore your thread or connection pool floor.
- The same 2,000/second at 500 ms means **1,000 in flight**. Latency went up 10x and required concurrency went up 10x, which is how a latency problem becomes a resource exhaustion problem.
- Read backwards: a pool capped at 200 with 50 ms service time caps throughput at 4,000/second, no matter what the CPU is doing. **A pool size is a throughput decision.**

The trap is applying it to an unstable system. If arrivals exceed service capacity, there is no steady state, the queue grows without bound, and W is not a number.

## utilisation-latency

For a single queue with random arrivals, waiting time scales as **1/(1 - ρ)** where ρ is utilisation.

| Utilisation | Latency multiplier |
|---|---|
| 50% | 2x |
| 70% | 3.3x |
| 80% | 5x |
| 90% | 10x |
| 95% | 20x |
| 99% | 100x |

The shape is the lesson. Going from 50% to 70% busy costs you 65% more latency. Going from 90% to 95% doubles it again. **The last 10% of capacity is not 10% of the capacity**, and this is why target utilisation for a latency-sensitive service sits around 60-70% rather than anywhere near full.

Two consequences worth stating separately:

- **Batch and interactive workloads want opposite utilisations.** A batch job should run a machine at 95%, because throughput is the goal and latency is irrelevant. Running an interactive service there is a choice to be slow.
- **More servers at the same utilisation are faster than fewer.** Pooling helps: ten servers behind one queue at 80% beat ten servers with their own queues at 80%, because a free server can take work from a busy one. That is the argument for a shared queue over sticky routing.

## variability

Utilisation is half the story; the other half is how uneven the arrivals and the work are.

- Waiting time rises with the **variability** of both arrival times and service times. Same average load, more bursty arrivals, longer queues.
- This is why a slow endpoint sharing a pool with fast ones damages the fast ones: high service-time variance in one queue lengthens the wait for everything in it. Separating pools by expected cost is the fix, and it is the reason for bulkheads.
- It is also why smoothing arrivals is worth real effort. A token bucket in front of a queue converts a burst into a rate and moves you left along the utilisation curve.
- **Coordinated arrivals are the worst case.** Cron jobs on the hour, retries without jitter, and cache expiries with the same TTL all convert a manageable mean into a spike.

## queue-depth

A queue is a shock absorber for bursts and a latency amplifier for overload, and the same buffer does both.

- Queue depth **is** latency, by Little's law: a 1,000-item queue draining at 500/second is 2 seconds of waiting, regardless of how fast each item is served.
- An unbounded queue is a way of converting a capacity problem into a timeout problem. Every item still gets served, long after anyone cares about the answer. **Bound every queue.**
- The useful policy at the bound is usually to shed, not to block: rejecting quickly is a better answer than accepting work you cannot finish in time. Where clients retry, rejecting fast also stops the queue absorbing load it will only re-emit.
- Prefer **dropping the oldest** when items expire in value. A queue served last-in-first-out under overload delivers some fresh answers instead of a uniformly stale set, which is counterintuitive and often correct.

## concurrency-limits

- A concurrency limit is the most reliable overload control there is, because it bounds L directly and therefore bounds W by Little's law.
- Set it from measurement rather than intuition: find the concurrency at which throughput stops rising, and cap slightly below it. Beyond that point extra concurrency adds latency and no throughput.
- Adaptive limits, which shrink the cap when latency rises, track a moving capacity better than a fixed number and are what a rate limit cannot do, since a rate limit does not know how slow you have become.
- **Per-dependency limits, not one global one.** A single pool means one slow downstream consumes all the concurrency and starves the paths that are healthy.

## Numbers to know

- L = λW. 1,000/second at 100 ms is 100 concurrent.
- Latency multiplier 1/(1 - ρ): 5x at 80% utilisation, 10x at 90%, 100x at 99%.
- Target 60-70% utilisation for latency-sensitive work, 90%+ for batch.
- Queue depth over drain rate is waiting time. 1,000 deep at 500/second is 2 s.

## Related

- [tails](tails.md): the tail is mostly queueing, and fan-out multiplies it
- [capacity](capacity.md): headroom is the distance from the cliff
