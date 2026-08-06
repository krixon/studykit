# Notification service - interviewer notes

**Do not reveal any of this before the attempt.**

A platform problem disguised as a feature. The hard parts are all about being a dependency: idempotency, third-party failure, per-tenant fairness, and preferences.

## Hidden requirements

- Functional: multiple channels (push, email, SMS, in-app), templates, user preferences and opt-outs, scheduling, delivery status.
- Non-functional: never send a duplicate, never lose a critical notification, bursty (a marketing send is 10M in a minute), third-party providers fail regularly.
- Deliberately unstated: whether ordering matters, retention of delivery history, whether callers can be trusted.

## Back-of-envelope they should reach

- 100M users, average 5 notifications/day = 500M/day ≈ 6k/second average.
- A marketing campaign to 10M users in 5 minutes is ~33k/second, so **peak is 5-10x average and driven by one caller**. That number is the whole reason this needs a queue and per-tenant fairness.
- Provider rate limits (SMS especially) are often a lower ceiling than your own capacity.

## Deep dives (pick two or three)

1. **Idempotency.** Callers will retry. A client-supplied idempotency key stored with the outcome, in the same transaction as the send record. Push on the unrecoverable window: the process dies after the provider accepted the SMS but before you recorded it. The honest answers are a provider-side idempotency key where offered, and accepting a rare duplicate otherwise.
2. **Fan-out and fairness.** One tenant's 10M-recipient campaign must not delay another tenant's password reset. This is per-tenant queues or weighted fair queuing, plus a separate priority lane for transactional messages. A single FIFO queue is the trap.
3. **Provider failure.** Retries with backoff, circuit breakers per provider, failover to a secondary provider, and a dead letter queue with a replay path. Push on what "delivered" means - most providers only acknowledge acceptance, so delivery status arrives later by webhook and your state machine must handle it out of order.
4. **Preferences and compliance.** Opt-out must be checked at send time, not at enqueue time, because a campaign enqueued an hour ago may contain users who have since unsubscribed. Getting this wrong is a legal problem, not a bug.

## Strong-answer signals

- Separates transactional from marketing traffic at the architecture level, not just by a priority field.
- Idempotency key from the caller, stored with the result.
- Checks preferences at send time and can say why that is the correct point.
- Treats provider acceptance and actual delivery as different states, with an asynchronous status update path.
- Templates versioned, and rendering separated from delivery.

## Common traps

- One queue for everything, so a campaign starves password resets.
- Assuming provider acceptance means delivered.
- Checking opt-outs when enqueuing.
- Synchronous send in the caller's request path.
- No dead letter queue, or one with no replay path and no alert.

## Follow-ups

- The SMS provider is down for two hours. Walk me through what happens to a message sent at minute one.
- A bug causes a campaign to be enqueued three times. What stops three sends?
- How do you tell a caller whether their notification arrived?
- A user unsubscribes while a 10M campaign is draining. What do they receive?
- How do you rate limit one tenant without starving them?
