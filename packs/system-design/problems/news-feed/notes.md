# Social news feed - interviewer notes

**Do not reveal any of this before the attempt.**

The canonical fan-out problem. What separates a good answer is not knowing "hybrid" as a word but being able to derive why the distribution of follower counts forces it.

## Hidden requirements

- Functional: feed of posts from accounts you follow, newest-first or ranked, infinite scroll, new-post notification.
- Non-functional: feed open in under ~200 ms, read-heavy by orders of magnitude, follower counts are extremely skewed, freshness of seconds is fine.
- Deliberately unstated: ranking versus chronological, ads, whether a post can be deleted or edited after fan-out.

## Back-of-envelope they should reach

- 300M daily actives opening 10 times/day = 3B feed reads/day ≈ 35k/second, peaks 3x.
- 100M posts/day ≈ 1200/second. **Read:write is roughly 3000:1**, which is the number that justifies precomputing feeds.
- Average 200 followers means fan-out on write is ~240k writes/second, which is large but tractable. One account with 10M followers is 10M writes for one post, which is not.

## Deep dives (pick two or three)

1. **Fan-out.** On write (precompute each user's feed: cheap reads, catastrophic for high-follower accounts), on read (assemble at read time: cheap writes, scatter-gather reads that degrade with following count), hybrid. Push for the derivation: the follower distribution is heavy-tailed, so almost all accounts are cheap to push and a handful are ruinous, which is exactly the shape that a special case fits.
2. **Feed storage.** A capped list of post ids per user in a fast store, hydrated with post content at read time. Push on why ids not content: content is shared across millions of feeds, so storing it per feed multiplies storage and makes edits impossible to propagate.
3. **The celebrity threshold.** Not follower count alone - the real cost is active followers times read rate. Push on how they would measure it and how they would change it safely.
4. **Ranking.** Once the feed is ranked rather than chronological, precomputation gets harder because the ranking depends on the reader and on time. Common answer: precompute a candidate set, rank at read time. Notice that this reintroduces read-time cost deliberately.

## Strong-answer signals

- Derives the hybrid from the follower distribution rather than reciting it.
- Stores ids and hydrates, and can say why.
- Caps feed length and can justify the number (nobody scrolls past a few hundred).
- Handles the inactive-user problem: do not fan out to accounts that have not opened the app in months, materialise on their return.
- Separates the write path (fan-out, asynchronous, queued) from the read path entirely.

## Common traps

- Pure fan-out on write with no celebrity handling, then no answer for a 10M-follower post.
- Storing full post content in every follower's feed.
- Unbounded feed length.
- Synchronous fan-out in the post request.
- Ignoring that a deleted post now exists in millions of materialised feeds.

## Follow-ups

- An account with 50M followers posts. Trace what happens in the next 10 seconds.
- A user deletes a post that was fanned out to 5M feeds. What do those users see?
- A dormant user returns after a year. What does their feed contain and how did it get there?
- You want to move from chronological to ranked. What in your design has to change?
- How would you A/B test a ranking change without doubling the infrastructure?
