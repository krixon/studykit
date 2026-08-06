# The endpoint that got slow - interviewer notes

**Do not reveal any of this before the attempt.**

A debugging exercise rather than a design. The signal is **method**: does the candidate narrow the search space with evidence, or list every possible cause they know?

Run this as a dialogue. They ask for evidence; you answer from the script below. Do not volunteer anything.

## The actual cause

Data growth. A query joins orders to a `shipments` table with **no index on the foreign key**. It has always been a sequential scan; at 5,000 shipments it was fast, and the table has now passed a million rows. The plan changed from a nested loop over a small table to a scan of a large one. Nothing was deployed because nothing needed to be - the code was always wrong and the data grew into it.

## The evidence script

Answer only what is asked.

| They ask for | You say |
|---|---|
| When did it start | Gradually over about three weeks, not a step change. Nobody noticed until it crossed a timeout. |
| Is it all requests or some | All of them, consistently. Not a tail problem. |
| Application CPU / memory | Normal. The application is mostly idle and waiting. |
| Database CPU | Elevated, roughly 3x. Disk read throughput is well up. |
| Any deploy, config or infra change | None in six weeks. |
| Slow query log | One query dominates, ~5.8 of the 6 seconds. |
| EXPLAIN on that query | Sequential scan on `shipments`, estimated rows 1.1M, and a nested loop above it. |
| Table sizes over time | `orders` steady at ~200k. `shipments` has gone from 5k to 1.1M since launch. |
| Index list on shipments | Primary key only. No index on `order_id`. |
| Cache hit rate | There is no cache on this path. |
| Traffic volume | Flat. |
| Is it N+1 | No - one query, executed once. |

If they fixate on the application layer, keep answering "normal" until they move to the database. Do not rescue them early; noticing that flat traffic plus idle application plus busy database points downwards is the skill being tested.

## Strong-answer signals

- Establishes the **shape** first: sudden or gradual, all requests or some, correlated with traffic or not. Gradual with flat traffic already rules out most causes.
- Reasons from "nothing was deployed" to "then something outside the code changed" - data volume, a dependency, or the environment.
- Asks for the slow query log or `EXPLAIN` rather than guessing at the query.
- Reads the plan and identifies the sequential scan.
- Proposes the index, and then asks what else has no index on a foreign key - generalising from the instance.
- Mentions adding the index concurrently to avoid locking a live table.

## Weaker patterns

- Listing every possible cause without asking for anything.
- Reaching for a cache before understanding the query. It would mask this, and the underlying problem stays.
- Proposing to scale the database up. It buys time and the growth continues.
- Never asking for `EXPLAIN`.

## Follow-ups

- How would you have caught this before users did?
- What is the risk of adding the index on a live table, and how do you avoid it?
- Would a cache have been an acceptable fix here? Why not?
- Which other tables would you check immediately after fixing this one?
- What alert would have fired three weeks ago?
