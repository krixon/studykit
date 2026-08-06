# API design

**Area:** api-schema · **Levels:** graduate → staff+

**One line:** The contract between systems, which outlives the code behind it and is far harder to change.

## Why it exists

An internal function can be renamed in an afternoon. A published endpoint cannot, because you do not control the callers. Every API decision is really a decision about **what you will still be supporting in three years**.

## styles

| Style | Shape | Strong when | Weak when |
|---|---|---|---|
| **REST / HTTP+JSON** | resources and verbs, cacheable by URL | public APIs, broad client support, HTTP caching does real work | one screen needs six round trips; no schema unless you add one |
| **RPC (gRPC, Thrift)** | typed methods over HTTP/2 | service-to-service, strict schemas, streaming, low overhead | browsers need a proxy; opaque to HTTP-layer tooling |
| **GraphQL** | client-specified query over a typed graph | many clients with different data needs, mobile round trips are expensive | caching is hard (POST to one URL), a client can author an expensive query, cost control moves into your resolvers |
| **Webhooks / events** | you call the client | long-running work, fan-out to third parties | delivery becomes your problem: retries, ordering, signing, replay |
| **Async job + poll** | submit, get a token, poll or subscribe | work that outlives a request timeout | two round trips and a state machine to explain |

The choice is mostly about **who owns the round trips** and **who owns the schema**.

## versioning

- **URL version** (`/v2/orders`) — obvious, greppable, and encourages copying the whole surface for one field change.
- **Header or media-type version** — keeps URLs stable and is easy for clients to get wrong by omission.
- **No version, additive only** — the discipline most large APIs converge on: never remove or repurpose a field, only add optional ones.

Version at the granularity of the thing that changes. A global version number for the whole API means every consumer is forced through a migration for a change to one endpoint.

Whatever you choose, the hard part is not issuing v2 but **retiring v1**: you need usage telemetry per version per client, a deprecation window, and someone whose job is chasing the last three callers.

## pagination

- **Offset / page number** — trivial, and wrong under concurrent writes: an insert shifts every subsequent page, so items are skipped or repeated. Cost also grows with offset, since the database still walks the skipped rows.
- **Cursor / keyset** (`WHERE (created_at, id) < (?, ?) ORDER BY … LIMIT n`) — stable under writes and constant cost per page. Cannot jump to page 40, which is almost never a real requirement.

Return the cursor **opaque**. The moment clients parse it you can never change the sort key. Always cap page size server-side, and return the cap you applied rather than silently truncating.

## errors-status

- Use the status code for the **class** of outcome and a body for the detail. `4xx` means the caller must change something; `5xx` means we failed and a retry may work.
- Distinguish the ones callers act on differently: `400` malformed, `401` unauthenticated, `403` authenticated but not allowed, `404` absent, `409` conflict with current state, `422` well-formed but semantically invalid, `429` rate limited, `503` try later.
- A machine-readable `code` field is what clients branch on. A human `message` is for logs. Never make clients regex the message.
- Include a **correlation id** in every error so a support conversation can find the request.
- `200 OK` with `{"error": ...}` inside defeats every intermediary, every retry policy and every dashboard.

## compatibility

**Backward compatible** = old clients work against the new server. **Forward compatible** = new clients work against the old server. Rolling deploys need both, because for a while both versions are live.

Safe: adding an optional field, adding an enum value *if clients were told to tolerate unknown values*, relaxing a validation rule.

Breaking: removing or renaming a field, tightening validation, changing a type (including int to string, and integer ids to strings for JavaScript safety), changing the meaning of an existing value, making an optional field required, adding an enum value clients were not told to tolerate.

The reliable pattern for a breaking change is **expand, migrate, contract**: add the new field alongside the old, write both and read the new, move consumers over with telemetry proving the old one is unused, then remove it. There is no shortcut for the middle step.

## Related

- [idempotency](idempotency.md) — what makes a retry safe
- [rate-limiting](rate-limiting.md) — the limit is part of the contract
- [caching](caching.md) — HTTP caching is an API design decision
