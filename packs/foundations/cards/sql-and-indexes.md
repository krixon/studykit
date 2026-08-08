# SQL and indexes

**One line:** A declarative language over a relational store, where the difference between a fast query and a slow one is usually an index and almost never the SQL syntax.

## joins

A join matches rows in one table to rows in another on a condition.

- **INNER**: only rows with a match on both sides.
- **LEFT**: every row from the left, with nulls where the right has no match. The usual way to ask "customers and their orders, including customers with none".
- **RIGHT**: the mirror, and rare because you can flip the tables.
- **FULL OUTER**: everything from both sides.
- **CROSS**: every combination. Almost always accidental, and the cause of a query that returns a billion rows.

The trap: adding a `WHERE` condition on the right-hand table of a `LEFT JOIN` silently converts it to an inner join, because a null fails the comparison. Put the condition in the `ON` clause instead.

Joins are not slow. Joins **without an index on the join column** are slow, because the database falls back to scanning.

## normalisation

Store each fact once, and reference it from everywhere else.

- **1NF**: no repeating groups; one value per column.
- **2NF**: non-key columns depend on the whole key.
- **3NF**: non-key columns depend on nothing but the key.

The plain-language version: if changing one fact requires updating many rows, it is not normalised, and eventually the copies will disagree.

**Denormalisation** is deliberately duplicating data to avoid a join, trading write cost and consistency risk for read speed. It is a legitimate optimisation *after* measuring, and a common source of bugs before. Store the customer's name on the order if you need the name at the time of the order to be historically fixed - that is not denormalisation, that is a different fact.

## indexes

An index is a sorted structure (usually a B-tree) mapping column values to rows, so the database can seek instead of scanning.

- Every index is maintained on **every write**, so five indexes turn one insert into six writes.
- A **composite** index on `(a, b)` serves `WHERE a = ?` and `WHERE a = ? AND b = ?`. It does nothing for `WHERE b = ?`, because the index is ordered by `a` first and there is no way to seek into it without knowing `a`. This leading-column rule is the single most useful thing to know here.
- A **covering** index includes every column the query returns, so the answer comes from the index alone and the table is never touched. Often the largest single win available.
- Indexes on **low-cardinality** columns (a boolean, a three-value status) are usually useless: too many rows match, so the planner scans anyway. A **partial** index over just the rare values works where a plain one does not.
- Wrapping a column in a function - `WHERE lower(email) = ?` - defeats the index unless you built an index on that expression.

`EXPLAIN` (or `EXPLAIN ANALYZE`) shows the plan the database chose. Reading it is the difference between guessing and knowing, and the words to look for are sequential scan, index scan, and the estimated versus actual row counts.

## n-plus-one

Fetch a list of N things, then issue one query per thing to load a related field. One query becomes N+1, and it usually appears when an ORM lazily loads a relation inside a loop.

- The symptom is a page that is fine with 10 rows and unusable with 500, and a log full of identical queries differing only by id.
- The fix is to fetch the related data in one query - a join, or an `IN` clause with the collected ids, or the ORM's eager-loading option.
- It is the most common performance bug in application code, and it is invisible in a code review unless you are looking for it.

## transactions

A transaction groups statements so they succeed or fail together. **ACID**:

- **Atomicity**: all of it or none of it.
- **Consistency**: declared constraints hold before and after.
- **Isolation**: concurrent transactions do not see each other's partial work, to a degree set by the isolation level.
- **Durability**: once committed, it survives a crash.

Isolation levels trade correctness for concurrency: read committed (the common default) permits lost updates and non-repeatable reads; repeatable read (usually implemented as snapshot isolation) removes those and permits write skew; serializable removes everything at a throughput cost.

Two rules worth holding:

- **Keep transactions short.** A transaction holds locks; a long one blocks other writers and, in an MVCC database, prevents cleanup of old row versions.
- **Never do I/O inside a transaction.** An HTTP call to a payment provider inside an open transaction means a slow third party is holding your database locks.

## Numbers to know

- An indexed lookup on a million rows is microseconds; a sequential scan is milliseconds to seconds.
- An N+1 over 500 rows at 1 ms each is half a second of pure latency, all of it avoidable.
- A single well-tuned relational node handles thousands of writes per second and single-digit terabytes. Most systems never outgrow it.

## Related

- [complexity](complexity.md): an index is a data structure choice
- [concurrency](concurrency.md): isolation is concurrency control for data
