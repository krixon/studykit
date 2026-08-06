# Chat system - interviewer notes

**Do not reveal any of this before the attempt.**

The visible problem is delivery. The real problems are ordering, the offline path, and the fact that connection state is the hardest thing to scale and fail over.

## Hidden requirements

- Functional: 1:1 and group chat, message history, delivery and read receipts, presence, offline delivery, push when the app is closed, attachments.
- Non-functional: sub-second delivery for connected users, messages must not be lost or duplicated, per-conversation ordering must be consistent for everyone, group size limits.
- Deliberately unstated: end-to-end encryption, message editing and deletion, maximum group size, retention.

## Back-of-envelope they should reach

- 50M daily active users, 40 messages/day each = 2B messages/day ≈ 23k/second average, with peaks 3-5x.
- 50M concurrent connections at ~10 KB of state each is ~500 GB of connection state, so thousands of gateway nodes. **Connection count, not message rate, sizes the fleet.**
- Storage: 2B messages/day at 200 bytes ≈ 400 GB/day, ~150 TB/year. Sharded by conversation.

## Deep dives (pick two or three)

1. **Ordering.** Client timestamps are unusable (clock skew, and clients lie). The workable answer is a per-conversation sequence number assigned by a single owner of that conversation - which makes conversation the natural shard key and the sequencing local. Push on group chat: everyone must see the same order, which a per-conversation sequencer gives for free and a global timestamp does not.
2. **Fan-out.** For 1:1 and small groups, push to each recipient's connection. For very large groups the fan-out cost per message becomes the problem, and the answer is the same hybrid as a feed: push for small, pull-on-open for large, or a shared conversation stream clients read from.
3. **Connection layer.** Stateless gateway nodes holding WebSockets, a registry mapping user to gateway, and a routing tier. Push on: what happens on deploy (mass reconnect, needs jitter and draining), how a message finds a user whose gateway just changed (registry staleness, and the message must be durable until acknowledged), and what happens to a message for a user with no connection (write to their inbox, then push notification).
4. **Delivery semantics.** At-least-once plus client-side deduplication on a message id. Receipts are themselves messages with the same problems. The offline path is the one people forget: the message must be durable *before* it is acknowledged to the sender.

## Strong-answer signals

- Shards by conversation and uses that to make sequencing local.
- Persists before acknowledging to the sender, and can say why the reverse loses messages.
- Client-generated message id used for deduplication and for optimistic local display.
- Treats the offline and push path as a first-class path, not a fallback.
- Notices connections dominate capacity planning and plans for reconnect storms.

## Common traps

- Ordering by client timestamp.
- Assuming the recipient is always connected.
- Acknowledging to the sender before the message is durable.
- One inbox table sharded by user, which makes a group message N writes and per-conversation ordering impossible to guarantee.
- Ignoring what a deploy does to a million open sockets.

## Follow-ups

- Two users send at the same instant in a group of 50. What order does everyone see, and why the same one?
- A user has been offline for a week. What happens when they open the app?
- You deploy the gateway tier. Walk me through the next 60 seconds.
- A group has 100,000 members. What changes?
- Add end-to-end encryption. What in your design stops working?
