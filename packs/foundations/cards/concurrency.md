# Concurrency basics

**Area:** concurrency · **Levels:** graduate → staff+

**One line:** Doing more than one thing at a time, where the difficulty is not the doing but the sharing.

## processes-threads

- A **process** has its own memory. Two processes cannot corrupt each other's state, and communicating between them means copying data through a pipe, socket or shared memory segment.
- A **thread** shares memory with its siblings inside a process. Communication is free, which is exactly why threads are dangerous: any thread can modify any shared value at any point.
- **Concurrency** is structuring work so tasks can make progress independently. **Parallelism** is actually running them simultaneously on multiple cores. Concurrency is a design property; parallelism is a hardware outcome. A single-core machine can be highly concurrent.

Context switching costs microseconds and grows with thread count, so a thread per request stops scaling somewhere in the low thousands. That ceiling is what asynchronous I/O exists to remove.

## races-locks

A **race condition** is when the result depends on the interleaving of operations. The classic is read-modify-write: two threads read a counter as 5, both add one, both write 6, and one increment is gone.

The reason this is hard to reason about: `count += 1` is not one operation. It is a load, an add, and a store, and a thread can be suspended between any two of them.

Remedies, cheapest first:

- **Do not share.** Immutable data, or giving each thread its own copy, removes the problem rather than managing it. Always the first choice.
- **Atomic operations.** A compare-and-swap or atomic increment is indivisible in hardware. Fast, and only covers a single variable.
- **Mutex (lock).** One holder at a time. Correct and general; every lock is a serialisation point and therefore a scalability limit.
- **Read-write lock.** Many readers or one writer. Wins when reads vastly outnumber writes, and costs more than a plain mutex when they do not.
- **Message passing.** Own the data in one place and send messages to it. This is what actors, channels and single-threaded event loops all do.

## deadlock

Two threads each hold a lock the other needs, so neither proceeds. It requires four conditions simultaneously - mutual exclusion, hold-and-wait, no preemption, circular wait - and breaking any one prevents it.

The practical prevention is **lock ordering**: if every thread acquires locks in the same global order, a cycle cannot form. Second-best is a timeout on acquisition, which converts a hang into a detectable error you can retry.

Related failures worth naming separately:

- **Livelock**: threads keep changing state in response to each other and no work completes. Everything is running and nothing progresses.
- **Starvation**: a thread never gets the lock because others keep taking it. Fair locks fix it at a throughput cost.
- **Priority inversion**: a low-priority thread holds a lock a high-priority thread needs.

Deadlocks are frequently absent in testing and present in production, because they need an interleaving that only load produces.

## async-io

Most server work is waiting: for a database, an HTTP call, a disk. A thread blocked on I/O consumes memory and a scheduler slot while doing nothing.

Asynchronous I/O lets one thread manage thousands of in-flight operations by registering interest and being notified when data is ready. That is how a single-threaded event loop handles tens of thousands of connections.

What this buys and does not buy:

- It removes the **memory and context-switch cost** of one thread per connection. It does not make anything compute faster.
- **CPU-bound work blocks the loop.** One slow synchronous function stalls every other request on that loop, which is the defining failure mode of async servers.
- Async is **viral**: an async function can only be awaited by an async caller, so adopting it tends to propagate through a codebase.

Use async for I/O-bound work, threads or processes for CPU-bound work, and be clear which one you have.

## atomicity

"Atomic" means indivisible: no observer sees a partial state.

- **Hardware atomics**: compare-and-swap on a single word, the primitive every lock is built from.
- **Database transactions**: atomicity across many rows. See [sql-and-indexes](sql-and-indexes.md).
- **Filesystem atomic rename**: write to a temp file, then rename over the target. Rename within a filesystem is atomic, so a reader sees either the old file or the new one, never a half-written one. This is the standard way to update a config or data file safely, and it is worth knowing because it needs no locks at all.

What is **not** atomic and is often assumed to be: reading a 64-bit value on a 32-bit platform, appending to a shared list, checking a condition and then acting on it (`if not exists: create` is a race), and any sequence of two atomic operations.

## Numbers to know

- Thread context switch: 1-10 µs. Thousands of threads spend real time switching.
- Uncontended mutex: tens of nanoseconds. Contended: microseconds or worse, because it involves the scheduler.
- An event loop handles tens of thousands of connections in one thread, if nothing blocks it.

## Related

- [processes-and-os](processes-and-os.md): what a process actually is
- [sql-and-indexes](sql-and-indexes.md): transactions are concurrency control for data
