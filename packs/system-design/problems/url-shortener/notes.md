# URL shortener - interviewer notes

**Do not reveal any of this before the attempt.**

Deceptively simple. It is fundamentally a key-value lookup plus a distributed unique-id problem, and the differentiator is whether the candidate recognises that and resists over-engineering.

## Hidden requirements

- Functional: create a short link (optional custom alias, optional expiry), redirect, click analytics.
- Non-functional: redirect p99 well under 50 ms, extremely read-heavy, links effectively permanent, high availability for redirects specifically.
- Deliberately unstated: whether the same long URL must map to one code (dedup is optional), whether analytics must be real time, whether codes must be unguessable.

## Back-of-envelope they should reach

- 100M new URLs/month ≈ 40 writes/second average. Reads at 100:1 ≈ 4000/second, peaks 10x.
- 100M/month × 5 years ≈ 6B records at ~500 bytes ≈ 3 TB. Shardable, and small enough that a single well-tuned store is not absurd.
- Base62, 7 characters: 62^7 ≈ 3.5 trillion. Plenty. Being able to compute this is the point.

## Deep dives (pick two or three)

1. **Key generation.** Counter plus base62 (needs coordination, produces guessable sequential codes), hash of the URL plus collision handling (needs read-before-write), or a key generation service handing out pre-allocated ranges (no write-path coordination). Push on what happens when the KGS restarts and re-issues a range - the standard answer is to persist the high-water mark before handing out the range, so a restart skips forward rather than repeating.
2. **Read path.** This is a hot-key problem: a viral link takes a huge share of traffic. Cache, CDN, and in-process L1 for the extreme tail. Expiry interacts with caching.
3. **301 versus 302.** A 301 is cached by the browser, so subsequent visits never reach you: analytics die and you lose the ability to change or revoke the target. A 302 keeps control at the cost of the round trip. This is the classic differentiator and almost nobody volunteers it.

## Strong-answer signals

- Recognises the shape (KV lookup plus unique id) and says so before designing.
- KGS with pre-allocated ranges, and handles the restart double-issue.
- Volunteers 301 versus 302 and its analytics implication.
- Treats custom aliases as a separate uniqueness constraint with a different write path.
- Analytics off the hot path - fire an event to a queue, aggregate asynchronously, never write to a counter synchronously on redirect.

## Common traps

- Hashing and hand-waving collisions.
- Random generation with read-before-write on the write path, then not noticing it becomes read-before-write on a hot table.
- Forgetting the 301 analytics implication entirely.
- Over-indexing on write scale when it is a read problem by two orders of magnitude.
- Incrementing a click counter synchronously in the redirect path.

## Level calibration

- **Graduate/mid**: a correct KV design with a cache, and a coherent id scheme, is a good answer. 301/302 is a bonus.
- **Senior+**: expect the 301/302 tradeoff, analytics off the hot path, and a number for the key space.
- **Lead/staff**: expect the KGS restart failure mode, the hot-key tail, and an explicit statement of what they would not build.

## Follow-ups

- How do you guarantee uniqueness without a read-before-write?
- How would you support link expiry and reclaim codes?
- Analytics at scale without slowing the redirect?
- Multi-region: how do reads and writes behave, and where does the counter live?
- Someone is using you to shorten phishing links. What changes in the design?
