# Ticket booking - interviewer notes

**Do not reveal any of this before the attempt.**

The one problem in the pack where eventual consistency is genuinely unacceptable for part of the system. Its job is to see whether the candidate can identify the small core that needs strong consistency and keep everything else cheap.

## Hidden requirements

- Functional: browse events, see availability, select seats, hold them while paying, confirm, cancel.
- Non-functional: **a seat must never be sold twice**, extreme burst on popular sales (a stadium in 60 seconds), browsing traffic is orders of magnitude higher than booking, payment is a slow third party.
- Deliberately unstated: hold duration, whether seats are numbered or general admission, queueing/waiting room, resale.

## Back-of-envelope they should reach

- A 60,000-seat venue selling out in 2 minutes = ~500 bookings/second sustained, and 10-100x that in browse and attempt traffic.
- Only a few thousand seat rows are contended, and they are all in one event. **The contention is concentrated, not distributed**, which is the key structural insight.
- Browse traffic can be cached and stale; booking traffic cannot.

## Deep dives (pick two or three)

1. **The double-sell.** Options: a database transaction with row-level locking and a unique constraint on (event, seat) - simple, correct, and limited by contention on one event's rows; optimistic concurrency with a version column and retry; or a distributed lock, which is the answer that sounds sophisticated and adds a failure mode. Push hard on why a single-node relational transaction is usually *enough*: the contended set is small and lives on one shard by design.
2. **Holds and expiry.** A hold is a state with a TTL, and the failure case is the process dying between hold and confirm. Expiry must be enforced at read time (a hold whose expiry has passed is not a hold) as well as swept in the background, because a sweeper alone leaves a window.
3. **Payment.** Slow, external, and can succeed after your timeout. This is an idempotency and reconciliation problem: idempotency key on the charge, a state machine that can accept a late success, and a reconciliation job. "We take payment then confirm" without handling the ambiguous outcome is the trap.
4. **Waiting room.** For extreme sales, admitting users at a controlled rate is the design that protects everything behind it, and it is a product decision as much as a technical one.

## Strong-answer signals

- Names precisely which operation needs strong consistency and keeps the rest eventual, with browse served from a cache.
- Shards by event, so contention on one event does not affect others, and notes that this makes the transaction single-shard.
- Handles the ambiguous payment outcome explicitly.
- Enforces hold expiry at read time, not only by sweeper.
- Notices that showing exact live availability to every browser is expensive and unnecessary - approximate is fine until you commit.

## Common traps

- Reaching for a distributed lock when a single-row transaction and a unique constraint suffice.
- Eventual consistency on the seat inventory, then hand-waving the double-sell.
- Holds with no expiry, or expiry only by background sweep.
- Assuming payment either succeeds or fails, with no third outcome.
- Sharding by user or by seat rather than by event, which scatters a transaction that should be local.

## Follow-ups

- Two users click the same seat in the same millisecond. Trace both requests.
- The payment provider times out and later charges the card. What does the user see?
- 100,000 people are waiting for a sale that starts at 09:00. What happens at 09:00:00?
- How would you support general admission (no seat numbers) instead, and what gets easier?
- The event organiser wants to release 500 extra seats mid-sale. What breaks?
