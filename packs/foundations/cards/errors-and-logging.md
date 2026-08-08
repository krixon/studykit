# Errors and logging

**One line:** Deciding what to do when things go wrong, and leaving behind enough evidence for whoever has to work out why.

## error-handling

The first question for any error is: **can this code do something useful about it?**

- If yes, handle it here.
- If no, let it propagate to a caller who can, adding context on the way.
- At the top of a request or job, there is a boundary that must catch everything, turn it into a response or a retry, and log it. That boundary is the only place a bare catch-all belongs.

Failure patterns, in rough order of how much damage they do:

- **Swallowing.** `catch { }` with an empty body destroys the evidence and converts a loud failure into a quiet wrong answer.
- **Logging and continuing** as if nothing happened, when the code below assumes the operation succeeded.
- **Catching too broadly**, so a programming error - a typo, a null - is handled as if it were an expected condition.
- **Losing the cause.** Wrapping an exception without chaining the original throws away the stack trace that named the actual line.

The useful distinction is between **expected** conditions (the user typed an invalid email, the record is not there, the remote service is rate limiting) and **bugs** (a null where the type says non-null). Expected conditions are part of your design and deserve a modelled outcome. Bugs should fail loudly and fast, because a bug handled gracefully is a bug that ships.

## exceptions-vs-results

Two ways to signal failure, and languages differ on which they favour.

**Exceptions.** A failure unwinds the stack until someone catches it.
- Keeps the happy path clean and readable.
- Failure is invisible in the signature, so callers do not know what can go wrong or that anything can.
- Cheap to write, and easy to leave uncaught.

**Result types.** The function returns success-or-failure as a value.
- Failure is in the type, so the compiler makes you deal with it.
- Callers cannot forget, and every call site gets noisier.
- Composing many fallible calls needs language support to stay readable.

Neither is universally right. What is universally right: **be consistent within a codebase**, and do not use exceptions for control flow in the ordinary case - an exception thrown on the common path is both slow and misleading to whoever reads the logs.

For a user-facing error, three audiences need three things: the user needs a message they can act on, the developer needs the stack and the inputs, and the support conversation needs a correlation id linking the two. Never show the user the stack, and never make the developer guess.

## log-levels

Levels exist so that volume can be turned down without losing the important lines.

| Level | Means | Test |
|---|---|---|
| `ERROR` | something failed and needs attention | would you want to be told? |
| `WARN` | something is wrong but was handled | is it a recurring signal worth noticing? |
| `INFO` | a significant business event happened | would you want this in production, forever? |
| `DEBUG` | detail for diagnosing a specific problem | off in production by default |
| `TRACE` | firehose | on for minutes, deliberately |

Most codebases suffer from **level inflation**: everything is `ERROR` because it felt important while writing it. The consequence is that the error log stops being read, so the real error is missed. If nobody would act on it, it is not an error.

## structured-logs

Log key-value pairs, not sentences.

```
level=error event=payment_failed order_id=8842 provider=stripe
    attempt=3 duration_ms=1204 error=timeout trace_id=abc123
```

versus `"Payment failed for order 8842 after 3 attempts"`.

The structured version can be filtered, grouped, counted and graphed. The prose version can only be grepped, and the grep breaks the moment someone rewords the message.

What every line should carry: a **correlation or trace id** so all lines for one request can be pulled together, the identifiers needed to find the affected record, a duration for anything that took time, and the outcome. Attach these once at the request boundary rather than passing them to every call.

**Log once, at the point where the decision is made.** Logging at every level of the stack as an exception propagates produces five lines describing one event, and makes counting errors impossible.

## what-not-to-log

Logs are copied, shipped to third parties, retained for years, and read by more people than you expect. Treat them as semi-public.

Never log: passwords, tokens, API keys, session ids, full card numbers, national identifiers, health data, or complete request bodies from endpoints that carry any of these. Redact at the point of logging, not in a later pipeline stage, because the pipeline is where the copy already exists.

Also worth avoiding: personal data beyond what an investigation needs (it inherits the retention and residency rules of your database, and usually gets neither), and anything at a rate proportional to traffic and value near zero - a debug line per request at 10k requests/second is about a terabyte a day, and the cost is real.

The awkward one: an exception message often contains the input that caused it, which is exactly the data you were careful not to log. Sanitise error messages at the boundary.

## Related

- [testing](testing.md): error paths are the least-tested code
- [security-basics](security-basics.md): logs are a common leak path
