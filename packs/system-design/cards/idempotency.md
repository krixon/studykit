# Idempotency and retries

**One line:** Make repeating an operation harmless, because in a distributed system it will be repeated whether you planned for it or not.

## Why it exists

A client sends a request and the connection drops. It cannot tell whether the server processed it. Both possible actions are wrong in one of the two worlds: retrying may double-charge, not retrying may lose the order.

The way out is to change the operation so both worlds converge: make the second attempt provably the same as the first. Idempotency is not a nicety on top of retries, it is the precondition that makes retries safe.

## keys

An **idempotency key** is a client-generated unique identifier for an *intent*, sent with the request and stored server-side with the outcome.

The protocol:

1. Client generates a key (a UUID) for the logical operation, **before** the first attempt, and reuses it on every retry of that same intent.
2. Server looks it up. If absent, process and store `(key → response, status)` **in the same transaction as the side effect**. If present and complete, return the stored response without reprocessing. If present and in flight, return `409` and let the client retry.
3. Expire keys after a window long enough to cover realistic retries.

Details that decide whether it actually works:

- **The key is the client's, not the server's.** A server-generated id cannot help, because the client never received it in the failure case.
- **Store the response, not just "done".** A retry must get the original result, including the created resource's id.
- **Scope the key** to the caller and endpoint, so two tenants cannot collide and a key cannot be replayed against a different operation.
- **Bind the key to the request body** (hash it). Same key, different payload, is a client bug and should be a `422`, not a silent replay of the wrong thing.
- Writing the key and the side effect in one transaction is what makes it atomic. Two separate writes leave a window where the side effect happened and the key did not.

## retries

Retrying is easy to do badly and the failure is correlated.

- **Only retry what is retryable.** Timeouts, `429`, `503`, connection resets. Never `400`, `401`, `403`, `422`: those will fail identically.
- **Exponential backoff with full jitter**: `sleep = random(0, base * 2^attempt)`. Without jitter, every client that failed together returns together and the recovering service is knocked over by the retry wave.
- **Cap total attempts and total elapsed time.** A retry that outlives the caller's own deadline is pure waste.
- **Retry budgets.** Cap retries as a fraction of total requests (say 10%). Under a broad failure this is what stops retries from tripling the load on a service already failing.
- **Never retry at more than one layer.** Client, gateway and service each retrying three times is 27 attempts. This multiplication is a common cause of a small fault becoming an outage.
- **Circuit breakers** are the complement: stop sending after a failure threshold, probe occasionally, resume. Retries handle transient faults; breakers handle sustained ones. Using retries for a sustained failure just amplifies it.

## exactly-once

There is no exactly-once delivery over an unreliable network. The sender cannot distinguish a lost message from a lost acknowledgement, so it either retries (duplicates possible) or does not (loss possible).

What is achievable is **exactly-once processing**, and there are exactly two routes:

1. **Idempotent consumer**: at-least-once delivery plus deduplication or a naturally idempotent operation.
2. **Transactional coupling**: commit the side effect and the consumption marker (the offset) atomically, so replay cannot double-apply. This only works when both live in a system that can commit them together.

When a vendor says "exactly-once", the question is which of these two it is, and where the boundary sits. Kafka's is the second, within Kafka; the moment your consumer writes to an external database, you are back to the first.

## dedup-windows

Deduplication needs state, and state costs memory that grows with traffic.

- The window must exceed the maximum realistic retry horizon: client backoff, queue redelivery, a consumer restart, and an operator manually replaying a dead letter queue days later. 24 hours is a common floor; long-tail replay argues for more.
- Storage options: a database table with a unique constraint (exact, durable, adds a write), Redis with TTL (fast, and loses the set on failover unless persisted), a bloom filter (constant memory, false positives mean you *drop* a legitimate message, which is usually unacceptable).
- **Expiry is a correctness boundary, not a cleanup detail.** A retry that arrives after the key expires is processed as new. If that is unacceptable, the dedup state must be as durable as the data.
- Under exact-dedup with a unique constraint, the constraint violation *is* the dedup. Catching it and returning the original result is simpler and more reliable than checking first.

## side-effects

Some operations are naturally idempotent and need no key: `PUT` of a full resource, `DELETE` by id, setting a value. Some are not: `POST` a payment, increment a counter, send an email.

- **Increments** are the classic trap: `balance = balance + 10` applied twice is wrong. Replace with a conditional write on a version, or record the *event* with its key and derive the balance.
- **External side effects you cannot recall**: emails, SMS, third-party charges. These need the dedup check before the call, and a durable record that the call was made. If the process dies between calling and recording, you cannot know; the honest mitigations are a provider-side idempotency key (most payment APIs offer one) or accepting a rare duplicate.
- **Ordering plus idempotency** is not the same as either alone. A deduplicated but reordered stream can still apply a stale update over a fresh one. Guard with a version or timestamp on the write, so an older update is rejected rather than merely not-duplicated.

## Related

- [message-queues](message-queues.md): at-least-once is the default you must survive
- [api-design](api-design.md): the header and status codes that carry this
- [consistency-models](consistency-models.md): why ordering and dedup are separate concerns
