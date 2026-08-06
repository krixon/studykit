# Abstract over payment providers - interviewer notes

**Do not reveal any of this before the attempt.**

The best problem in this pack for separating people who apply patterns from people who reason about abstractions, because the honest answer includes "some of this cannot be abstracted, and here is what I do about that."

## Hidden context

Answer when asked.

- The existing provider's SDK types appear in about 60 files, including the domain.
- Provider B does not support one thing provider A does: partial refunds.
- Provider B settles asynchronously - the charge is "pending" for up to two days - while A is synchronous.
- Both send webhooks, with different payload shapes, different signing schemes, and different delivery guarantees.
- Region determines the provider, and a customer's region does not change.

The partial refund and the async settlement are the interesting parts. They are where a naive common interface breaks.

## Deep dives (pick two or three)

1. **Who owns the interface.** The domain declares `PaymentGateway` in its own language; adapters implement it. The failure mode is designing the interface by looking at provider A's SDK, which produces "an abstraction" that is provider A with renamed methods - and provider B then does not fit. Push on this hard: the interface should be derived from **what the business needs**, and adapters should absorb the difference.
2. **The lowest common denominator problem.** A cannot do everything B does and vice versa. Options: intersect (only expose what both support, losing partial refunds you already offer), union with capability flags (`gateway.supports(PARTIAL_REFUND)`, with callers branching - which leaks the providers back into the domain), or model the domain operation honestly and let one adapter implement it by a workaround (full refund plus re-charge). **There is no clean answer**, and the strongest candidates say so and then choose with a stated reason.
3. **Async settlement.** Provider A returns a result; B returns "pending". If the interface is synchronous, B does not fit and you end up with a boolean or an exception meaning "not really done". The right move is to make the domain model asynchronous for both - a payment has a lifecycle with states, and A's adapter simply moves through it immediately. This is the second time the same lesson appears: **model the harder case, and let the simpler provider be a degenerate instance of it.**
4. **Webhooks.** Different shapes, different signatures, different guarantees, arriving out of order and more than once. Each adapter verifies its own signature and translates to a common internal event. Push on idempotency and ordering: webhooks are at-least-once and unordered, so the handler needs a dedup key and a state machine that rejects a stale transition rather than applying it.
5. **The migration.** 60 files reference the SDK. Introduce the interface, adapt the existing provider behind it, migrate call sites incrementally, then add provider B. Adding B first as a parallel implementation of a not-yet-existing abstraction is the common mistake.
6. **Testing.** A contract test suite that both adapters must pass is the mechanism that keeps the abstraction honest, and it is what tells you at build time that B does not satisfy something you assumed.

## Strong-answer signals

- Derives the interface from business needs, not from provider A's SDK.
- Explicitly names the lowest-common-denominator problem and chooses, rather than pretending the interface is clean.
- Models the asynchronous case as the general one.
- Per-adapter webhook verification, translating to a common internal event.
- Idempotency and out-of-order handling on webhooks.
- A contract test suite both adapters run against.
- Says what deliberately stays provider-specific, and where that leaks.

## Common traps

- An interface that is provider A's SDK with renamed methods.
- Assuming synchronous settlement, then bolting on a "pending" special case.
- Leaking provider types or exceptions into the domain.
- Capability flags everywhere, so callers branch per provider and the abstraction buys nothing.
- Treating webhooks as reliable, ordered and exactly-once.
- Adding provider B before the existing integration is behind the interface.

## Follow-ups

- Provider B cannot do partial refunds. What does your interface say, and what does a caller do?
- A webhook arrives twice, out of order, three days late. What happens?
- How do you know provider B's adapter is correct before you have any traffic?
- The business adds a third provider that only does bank transfers. Does your abstraction survive?
- Which parts of this would you deliberately not abstract?
