# Message queues and logs

**One line:** Decouple producers from consumers in time, so a slow or dead consumer does not become the producer's problem.

## Why it exists

A synchronous call couples availability (if they are down, you are down), latency (you wait for their slowest path) and capacity (their limit is your limit). A queue breaks all three, and charges you in exchange: eventual consistency, ordering questions, duplicate handling, and a new system to operate.

Reach for one when work can be done later, when a burst must be absorbed, or when one event has many independent consumers.

## queue-vs-log

The distinction that explains most confusion in this area.

| | Queue (SQS, RabbitMQ) | Log (Kafka, Kinesis, Pulsar) |
|---|---|---|
| Message after consumption | deleted on acknowledgement | retained for a configured window |
| Position | the broker tracks per-message state | the consumer tracks an **offset** |
| Multiple consumers | compete; each message goes to one | each consumer group reads everything independently |
| Replay | impossible, it is gone | rewind the offset and re-read |
| Ordering | per queue, weakly | strict within a partition |
| Scaling consumers | add workers freely | bounded by partition count |

Rule of thumb: **queue for work distribution, log for event distribution.** "We need to add a second consumer of these events" is trivial with a log and a re-architecture with a queue.

## delivery-semantics

- **At-most-once**: acknowledge before processing. Fast; loses messages on a crash.
- **At-least-once**: acknowledge after processing. Never loses; duplicates whenever an acknowledgement is lost or a worker dies mid-flight. **This is what you will actually run.**
- **Exactly-once**: the message is processed exactly one time.

Exactly-once delivery is impossible over an unreliable network: the sender cannot distinguish "the message was lost" from "the acknowledgement was lost", so it must either retry (risking duplicates) or not (risking loss). What systems provide is **exactly-once processing**, which is at-least-once delivery plus either an idempotent consumer or a transactional write that commits the message offset and the side effect atomically. Kafka's exactly-once is this: transactions across the log and the offset store, within Kafka.

Practically: assume duplicates and make consumers idempotent. See [idempotency](idempotency.md).

## ordering

Global ordering across a distributed system costs a single serialisation point, which is a throughput ceiling. Nobody wants it once they price it.

The standard compromise is **ordering within a partition key**: all events for one entity go to one partition, which one consumer reads in order. Events for different entities are unordered relative to each other, which is almost always fine.

Consequences worth stating:

- The partition key is a **shard key** and inherits every hot-shard problem: pick one entity that is 30% of traffic and one partition is 30% of the load. See [sharding](sharding.md).
- Concurrency within a partition is 1, so a slow message blocks everything behind it for that key.
- Retrying a failed message by re-queueing it at the tail **breaks the ordering you were preserving**. That is the trap: retry and ordering pull in opposite directions, and you must choose which one this stream needs.

## consumer-lag

The single most important metric on any queue or log: how far behind the consumer is, in messages and in time.

- **Time lag** is the number the business understands ("notifications are 20 minutes late"). Track both.
- Rising lag with steady input means the consumer is under-provisioned or has slowed down. Rising lag with rising input means a burst, which is what the queue is for.
- **Queue depth alone is a poor alert.** A deep queue draining fast is healthy; a shallow queue that never drains is not. Alert on the *derivative* and on the projected drain time.
- The buffer is not infinite. Decide what happens when it fills: block producers (backpressure), drop oldest, drop newest, or spill to cheaper storage. Not deciding means the broker decides, usually badly.

## dlq-poison

A **poison message** fails every time it is processed. Without a limit, it is retried forever, blocking its partition or burning capacity, and the retry loop looks like healthy traffic on a dashboard.

- Cap redelivery attempts, then move the message to a **dead letter queue**.
- Back off exponentially with jitter between attempts, and put retries on a separate queue so they do not block first attempts.
- **A dead letter queue nobody monitors is a data loss mechanism with extra steps.** Alert on non-zero depth, and keep enough context on the message (original topic, failure count, last error, correlation id) to diagnose and replay it.
- Have a replay path back to the main queue after a fix. Designing the DLQ without designing the replay is the common half-solution.

## partitions

- Partition count sets **maximum consumer parallelism** in a log: more consumers than partitions means idle consumers.
- Partition count is hard to increase after the fact, because it changes the key-to-partition mapping and therefore breaks per-key ordering across the change. Over-provision partitions early; they are cheap.
- More partitions cost open file handles, memory, and longer leader elections and rebalances.
- A **rebalance** (a consumer joining or leaving) pauses consumption for the group. Frequent rebalances from aggressive timeouts or slow processing produce a group that spends its time rebalancing rather than consuming.

## Numbers to know

- Kafka on commodity hardware: hundreds of thousands of messages/second per broker for small messages, limited by network and page cache before CPU.
- Retention is a capacity decision: 7 days of a 100 MB/s stream is ~60 TB before replication.
- Consumer parallelism ≤ partition count. Always.

## Related

- [idempotency](idempotency.md): how consumers survive at-least-once
- [sharding](sharding.md): a partition key is a shard key
- [observability](observability.md): lag is the signal that matters
