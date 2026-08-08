# Processes and the OS

**One line:** What your program actually is once it is running, and which of its limits are set by the operating system rather than by your code.

## process-model

A process is a running program with its own virtual memory, file descriptors, environment and process id. It is created by the OS, given CPU time by the scheduler, and reaped when it exits.

- **Exit codes**: 0 means success, anything else is failure. Shells, CI systems, container orchestrators and `&&` all depend on this, so a program that exits 0 after failing breaks every automation around it.
- **stdout and stderr are different streams for a reason.** Program output goes to stdout so it can be piped; diagnostics go to stderr so they survive a pipe and do not corrupt the data. Logging to stdout breaks `yourprog | jq`.
- **Parent and child.** A child inherits the environment and open descriptors. A child whose parent dies is re-parented to init; a child that has exited and not been waited for is a **zombie** holding a slot in the process table.
- Containers change none of this. A container is a process with namespaced views of the filesystem, network and process table, plus cgroup limits. **PID 1 in a container has special responsibilities** - it does not get default signal handlers and must reap orphans - which is why a shell script as PID 1 often fails to forward `SIGTERM`.

## memory

Virtual memory means each process sees a private address space; the OS maps pages of it to physical memory on demand.

- **Stack**: function frames and locals, small (typically 1-8 MB) and automatically managed. Deep or infinite recursion overflows it.
- **Heap**: explicitly or garbage-collected allocations, large, and where leaks live.
- **Resident set size (RSS)** is physical memory actually in use, and is the number that gets you killed. **Virtual size** is address space reserved, is frequently enormous, and means little.
- **Swap** trades a memory shortage for a latency catastrophe: a page fault to disk is roughly 100,000 times slower than RAM. Most server workloads are better off failing fast than swapping.
- The **OOM killer** picks a process and terminates it, usually the largest, with no chance to clean up. In a container, exceeding the cgroup limit gets you killed the same way. Neither produces a graceful shutdown, so the observable symptom is a process that vanishes with no log line - if a service dies silently, check `dmesg` and the exit code (137 = 128 + 9, killed by SIGKILL).
- A **memory leak** in a garbage-collected language is usually an unintended reference: a cache with no eviction, a listener never unregistered, a growing static collection.

## files-descriptors

A file descriptor is a small integer indexing an open file, socket or pipe. Everything is a file: sockets, pipes, terminals, devices.

- There is a **per-process limit** (`ulimit -n`, often 1024 by default, which is very low for a server) and a system-wide one. Exhausting it produces "too many open files", which then surfaces as failures to accept connections or open anything at all - so the error appears far from the leak.
- The usual cause is a descriptor not closed on an error path. Use the language's scope-bound mechanism - `with`, `defer`, `try-with-resources` - so closing does not depend on the happy path.
- **Buffering**: output is buffered until flushed. A process killed with unflushed output loses it, which is why a crashed program's last log lines are often missing. Line-buffer or flush explicitly for logs.
- **Atomic rename** is the safe way to replace a file: write to a temporary file in the same directory, fsync it, then rename over the target. Readers see the old or the new file, never a partial one.

## signals-shutdown

Signals are the OS's asynchronous notifications to a process.

- `SIGTERM`: please stop. **Catchable, and the one that matters.** This is what orchestrators send first.
- `SIGKILL`: stop now. Not catchable, no cleanup. Sent after the grace period expires.
- `SIGINT`: Ctrl-C. `SIGHUP`: traditionally "reload configuration". `SIGSTOP`/`SIGCONT`: pause and resume.

**Graceful shutdown** is the part people skip, and it is what makes deploys invisible:

1. Receive `SIGTERM`.
2. Stop accepting new work, and fail the readiness check so the load balancer stops routing to you.
3. Finish in-flight requests, up to a deadline shorter than the orchestrator's grace period.
4. Close connections and flush buffers.
5. Exit 0.

Without it, every deploy drops the requests in flight, and you see a small error spike you eventually stop noticing. Two details that break it in containers: the grace period (commonly 30 seconds) is a hard ceiling before `SIGKILL`, and if PID 1 is a shell it may never forward the signal to your process at all.

## environment-config

- **Configuration comes from the environment**, not from files baked into the build, so the same artefact runs in every environment. Same image, different config, is what makes a promotion pipeline meaningful.
- Environment variables are strings, are inherited by children, and are **visible in the process table and in crash dumps**. Do not pass long-lived secrets this way if a secret manager or a mounted file is available.
- Precedence should be explicit and boring: defaults, then file, then environment, then command-line flags.
- **Validate configuration at startup and fail fast.** A missing or malformed value should stop the process immediately with a clear message, not surface as a null three hours later on an uncommon path.
- Log the effective configuration at startup, with secrets redacted. It answers "what was it actually running with" better than any amount of later archaeology.

## Numbers to know

- Default file descriptor limit is often 1024. A server needs tens of thousands.
- Container `SIGTERM` grace period: typically 30 seconds before `SIGKILL`.
- Exit code 137 = SIGKILL (usually OOM), 143 = SIGTERM, 130 = SIGINT.
- Page fault to disk: ~100 µs against ~100 ns for RAM.

## Related

- [concurrency](concurrency.md): threads live inside a process
- [errors-and-logging](errors-and-logging.md): stdout, stderr and buffering
