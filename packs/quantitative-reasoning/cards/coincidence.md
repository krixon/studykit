# Coincidence and collision

**One line:** How often something improbable happens when you do it a billion times, and why the answer is usually much sooner than people guess.

## Why it exists

Two errors, in opposite directions, both common. People treat a one-in-a-million event as impossible, when a system doing a million things an hour meets it hourly. And people treat independent failures as if they stay independent, when the thing that broke one replica is usually the thing that breaks the others.

Getting these wrong produces id collisions in production, dedup windows that do not dedup, and availability numbers multiplied together that were never independent.

## birthday-bound

Collisions among random values appear at roughly the **square root** of the space, not near its size. For a space of *N* values, a 50% chance of some collision arrives after about `1.18 sqrt(N)` draws.

| Identifier | Space | 50% chance of a collision at |
|---|---|---|
| 32-bit | 4.3 x 10^9 | ~77,000 values |
| 64-bit | 1.8 x 10^19 | ~5.1 x 10^9 values |
| 128-bit (UUIDv4, 122 random bits) | 5.3 x 10^36 | ~2.7 x 10^18 values |

The 32-bit row is the practical one: a 32-bit random id collides at tens of thousands of items, which is an ordinary table, not a large one. This is why a random 32-bit key is never safe and a truncated hash needs its length justified by the count of things it will ever identify.

The general instinct: **halve the bits, halve the exponent.** A 128-bit id has 64 bits of collision resistance, not 128, and a hash truncated to 64 bits gives 32 bits of resistance - which the first row says is not enough.

## id-collisions

- A collision probability that is acceptable for the whole lifetime of a system is the figure to compute, not the probability per insert.
- **Uniqueness in a namespace beats uniqueness in the universe.** Scoping an id to a tenant, a day or a shard shrinks N in the birthday formula, which buys far more than adding bits.
- A unique constraint in the store is the cheap belt-and-braces: it converts a silent collision into an error you can retry. Relying on probability alone with no constraint means the failure is a data corruption rather than an exception.
- Distinguish random from **sequential-with-randomness** (UUIDv7, Snowflake). A time-ordered id with a random suffix has collision resistance from the suffix only, within the same timestamp tick, so the number to check is the per-tick space against the per-tick rate.

## independent-failures

Multiplying probabilities requires independence, and independence is the assumption that fails.

- Three replicas at 99.9% each give 99.9999...% availability **only if** their failures are independent. They share a rack, a power feed, a network, a deployment pipeline, a configuration store and a container image, and every one of those is a common cause.
- The right question is not "how many nines does each have" but "what is the largest thing whose failure takes all of them". That thing sets the real number, and it is usually a deploy or a config push rather than hardware.
- **Correlated failures dominate the arithmetic.** If 1% of outages are correlated and independent failure gives you six nines, the correlated 1% sets your availability at four nines. Adding a fourth replica does not move it.
- Serial dependencies multiply the wrong way: a request that needs five services at 99.9% each is 99.5%, so composing reliable things gives you something less reliable than any of them.

## rare-events-at-scale

Anything with a probability per operation becomes a rate when you know the operation count.

- Expected occurrences = probability x operations. A one-in-a-million event at 10,000 operations per second happens **once every 100 seconds**.
- The corollary that catches people: a bug that reproduces one time in ten thousand is not rare in production, it is continuous. Test volumes and production volumes differ by orders of magnitude, which is why "we could not reproduce it" and "it happens constantly" are both true.
- Very small probabilities over very many trials are well approximated by expecting `n p` events, and the chance of none is about `e^-np`. When `np` is 1, the chance of zero occurrences is 37%, so absence of evidence is weak.
- Read hardware error rates this way too. An uncorrectable bit error rate that sounds negligible per byte becomes a certainty per petabyte, which is why checksums exist.

## correlated-retries

The specific coincidence that causes outages.

- Retries without jitter synchronise. A thousand clients that all failed at the same instant and all back off by the same schedule retry at the same instant, so the recovery attempt is a spike shaped exactly like the event that caused the failure.
- Cache expiry has the same structure. Keys written together with the same TTL expire together, so the stampede is a coordination artefact rather than a load artefact. **Jitter the TTL.**
- Anything on a cron at the top of the hour is a coordinated arrival by construction. Spread the schedule.
- The general remedy is to break the correlation, not to reduce the load: full jitter on backoff, randomised TTLs, staggered schedules. Halving the retry rate delays the spike; randomising it removes the spike.

## Numbers to know

- Collisions at ~`1.18 sqrt(N)`. 32-bit collides at ~77,000 values; 64-bit at ~5.1 x 10^9.
- Halving the bits of an id halves the exponent of its collision resistance.
- Expected events = p x n. One in a million at 10,000/second is one every 100 seconds.
- If `np` = 1, the chance of seeing none is 37%.
- Five services at 99.9% in series give 99.5%.

## Related

- [tails](tails.md): the same product-of-probabilities argument, applied to latency
- [measurement](measurement.md): how many samples before an absence means something
