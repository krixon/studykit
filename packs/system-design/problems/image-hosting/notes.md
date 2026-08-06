# Image hosting and delivery - interviewer notes

**Do not reveal any of this before the attempt.**

The interesting parts are the upload path, the variant explosion, and the fact that bandwidth, not storage or compute, is the dominant cost.

## Hidden requirements

- Functional: upload, store, serve at several sizes, delete.
- Non-functional: global audience, read-heavy by orders of magnitude, images immutable once uploaded, uploads can be large and come from poor mobile connections.
- Deliberately unstated: whether images are public or access-controlled, whether originals must be retained, moderation.

## Back-of-envelope they should reach

- 10M uploads/day at 2 MB average = 20 TB/day ingested, ~7 PB/year before variants.
- Variants (say 5 sizes) at 10-20% of the original each roughly doubles storage.
- Serving: if each image is viewed 100 times at 200 KB, that is 200 GB per 1M views. **Egress is the bill**, and a candidate who notices that is thinking about the right thing.

## Deep dives (pick two or three)

1. **Upload path.** The right answer is a pre-signed URL so the client uploads directly to object storage, and the application server never touches the bytes. Push on why: it removes a proxy hop, removes a scaling dimension from your servers, and lets the storage provider handle resumable multipart uploads. Then: how does the app learn the upload finished? An event from the storage layer, not a client callback you trust.
2. **Variant generation.** Eager (generate all sizes on upload: predictable serving latency, wasted work on images nobody views, and a migration every time you add a size) versus lazy (generate on first request, cache at the edge: no wasted work, a cold-start penalty, and a thundering herd risk on a viral image). Most systems do lazy with a CDN in front. Best answer names the trade and picks by view distribution.
3. **Delivery and caching.** Content-addressed URLs make everything immutable and cacheable for a year with no invalidation - this is the design move. Push on what happens with access-controlled images, where signed URLs with short expiry conflict with cacheability.
4. **Deletion.** Deleting from origin does not delete from the CDN or from browsers. Also relevant for legal removal requests, where a purge is required and is not instant.

## Strong-answer signals

- Pre-signed direct upload, with the completion event coming from storage.
- Notices egress is the dominant cost and designs around it (CDN, format negotiation, aggressive caching).
- Content-addressed immutable URLs, so invalidation is a non-problem.
- Separates metadata (small, relational, queryable) from blobs (large, object storage).
- Mentions modern formats (WebP/AVIF) and content negotiation as a real bandwidth lever.

## Common traps

- Uploading through the application server without comment.
- Storing image bytes in the database.
- Eager generation of every variant with no view-distribution argument.
- Assuming deletion is instant and global.
- Ignoring the CDN entirely, then being surprised by the bandwidth number.

## Follow-ups

- Someone uploads a 4 GB file. Where does that fail, and where should it fail?
- A legal takedown requires an image gone within an hour worldwide. What actually happens?
- You want to add an AVIF variant for 200 million existing images. What is the plan?
- Access-controlled images and CDN caching are in tension. Resolve it.
