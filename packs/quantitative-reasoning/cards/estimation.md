# Back of the envelope

**One line:** Getting to a defensible number in two minutes, so a design argument has a magnitude attached instead of an adjective.

## Why it exists

Most design mistakes are not errors of reasoning, they are errors of magnitude: a scheme that is obviously right at a thousand a day and obviously absurd at a million, argued without anyone working out which one it is. An estimate does not have to be accurate. It has to be good enough to rule things out, and the usual outcome of doing one is discovering that the question was not close.

The failure this addresses is correct reasoning with the arithmetic left implicit. "That will be a lot of traffic" is not an input to a decision.

## powers-of-two

The table worth knowing cold, because it turns byte arithmetic into addition.

| Power | Name | Value |
|---|---|---|
| 2^10 | thousand | 1,024 |
| 2^20 | million | 1,048,576 |
| 2^30 | billion | 1,073,741,824 |
| 2^40 | trillion | ~1.1 x 10^12 |

Read it as: a thousand of anything is `2^10`, so a thousand records of a kilobyte each is `2^10 x 2^10` = a megabyte. A million users with a kilobyte of profile each is a gigabyte. Estimating in powers of two and converting at the end avoids the commonest arithmetic slip, which is losing a factor of a thousand somewhere in the middle.

Decimal and binary prefixes differ by 2.4% at kilo and 10% at tera. It never matters in an estimate and always matters in a disk-full alert.

## unit-discipline

Write the unit on every intermediate value. This one habit catches most estimation errors, because a wrong step usually produces the wrong unit before it produces the wrong number.

- Carry units through the multiplication: `requests/second x bytes/request = bytes/second`.
- If the units of your answer are not the units of the question, the model is wrong, and no amount of re-checking the arithmetic will find it.
- State whether a figure is per second, per day, or peak. "100,000 requests" is not a rate and cannot be compared to a capacity.
- Distinguish a **stock** from a **flow**: gigabytes stored is a stock, gigabytes per day is a flow, and the two answer different questions. Storage growth is a flow integrated over a retention window.

## rate-conversion

The conversions that come up constantly:

- **A day is ~100,000 seconds** (86,400). Use 10^5: it is 16% high and it makes everything divisible.
- **A month is ~2.5 million seconds**, a year ~30 million (3.15 x 10^7).
- **1 per second is ~2.6 million a month**. So a million a month is well under one per second, which is the sanity check that kills a surprising number of "we will need a queue" arguments.
- **Peak is not mean.** A diurnal web workload peaks at roughly 2-3x its daily mean, and a batch-driven one can peak at 100x. Size for peak, cost for mean, and say which one a figure is.

## dominant-term

Almost every estimate has one term that decides the answer, and the value of the estimate is finding it rather than computing the total precisely.

- Compute each term to one significant figure, compare, and drop anything an order of magnitude below the largest. A 3% term does not need to be right.
- If two terms are within a factor of two, you have found a genuine trade-off and the estimate has done its job by locating it.
- Sensitivity is the real output: state which input the answer moves with. "Dominated by the image payload, so it is a bandwidth question, not a request-rate question" is worth more than a number.
- The corollary: **an estimate with no dominant term is usually the wrong model**, because real systems are lopsided.

## sanity-checks

Before quoting a figure, test it against something you already know.

- **Bound it.** Is the answer larger than the whole internet, or smaller than one request? Both happen.
- **Compare to a known scale.** Global card transactions run at a few thousand a second. If your internal tool needs more, re-check.
- **Check the direction.** Does the answer move the right way when you double an input? A model with a sign error survives arithmetic review and fails this.
- **Re-derive one figure a second way.** The cheapest review available: two routes to the same magnitude, or a discrepancy that names the mistake.
- **Say the magnitude out loud.** "Forty terabytes a day" invites the objection that "4 x 10^13 bytes" does not.

## Numbers to know

- A day is 86,400 s, near enough 10^5. A year is 3.15 x 10^7 s.
- L1 cache ~1 ns, main memory ~100 ns, SSD read ~100 us, datacentre round trip ~0.5 ms, cross-continent round trip ~100 ms.
- Light in fibre covers roughly 200 km per millisecond.
- A commodity server does 10^8 simple interpreted operations per second, 10^9 compiled.
- 1 Gbps is 125 MB/s. A 10 Gbps link moves about a terabyte an hour.

## Related

- [tails](tails.md): a mean is the figure an estimate produces and rarely the one a user feels
- [capacity](capacity.md): estimates become headroom decisions
