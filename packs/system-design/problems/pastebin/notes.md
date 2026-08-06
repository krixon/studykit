# Pastebin - interviewer notes

**Do not reveal any of this before the attempt.**

This is the gentlest problem in the pack. Its job is to see whether someone can run the *process* - clarify, estimate, sketch, name a tradeoff - on a problem where the technology is not the obstacle.

## Hidden requirements

Wait for the candidate to ask. Volunteer only if they are stuck and the session is coaching.

- Functional: create a paste, read by link, optional expiry, optional syntax highlighting, optional private (unlisted) pastes.
- Non-functional: read-heavy (roughly 10:1), pastes are immutable once created, availability matters more for reads than writes, size limit needed (say 1 MB).
- Deliberately unstated: whether paste ids must be unguessable, whether edits are allowed, whether there are user accounts.

## Back-of-envelope they should reach

- 1M new pastes/day is ~12 writes/second. Trivial.
- 10:1 reads means ~120 reads/second. Also trivial.
- Average paste 10 KB, 1M/day, 5 years: ~18 TB. Large enough to think about, small enough for one system.
- The point is that they *do* an estimate and notice it is a small system, rather than reaching for Kafka.

## Deep dives (pick two)

1. **Where does the text live?** Rows in a database versus object storage with metadata in a database. The right answer is object storage for the blob, database for metadata - and the reason is that large blobs in a relational database bloat the buffer pool and make every other query slower.
2. **Id generation.** Random base62 versus a counter. Random is fine here and is required if unlisted pastes are to be unguessable; a sequential counter makes every paste enumerable, which is a security question disguised as a design one.
3. **Expiry.** A TTL field checked at read time versus a background sweeper. Both, in practice: filter at read for correctness, sweep in the background to reclaim storage.

## Strong-answer signals

- Asks about guessability before choosing an id scheme.
- Separates blob storage from metadata storage and can say why.
- Notices reads dominate and puts a cache or CDN in front, and can say what makes this cacheable (pastes are immutable).
- Gives a size limit and says what happens when it is exceeded.

## Common traps

- Storing megabyte blobs in a relational row without comment.
- A sequential id plus a claim that unlisted pastes are private.
- Reaching for sharding, queues or microservices on a system doing 12 writes/second.
- Forgetting that immutability makes caching trivially safe - it is the single most useful property here.

## Follow-ups

- How would you support paste expiry without scanning the whole table?
- Someone pastes 500 MB. What happens, and where do you stop it?
- One paste goes viral and takes 90% of your traffic. What changes?
- How would you add edit support, and what breaks when you do?
