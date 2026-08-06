# A job that runs every night - interviewer notes

**Do not reveal any of this before the attempt.**

Batch jobs look like the easiest thing in the system and quietly accumulate every distributed-systems problem: partial failure, retries, duplicates, time zones, and the fact that nobody watches them until a customer complains.

## Hidden requirements

- Functional: find due accounts, generate an invoice per account, email it, record what was sent.
- Non-functional: **never invoice an account twice**, never silently skip one, must complete before business hours, must be resumable after a failure.
- Deliberately unstated: how many accounts, what happens when the job crashes at 60%, whether more than one instance can run, which timezone 02:00 and "today" refer to.

## The questions they should ask

- **What happens if it fails halfway?** The central design question. Answering it forces per-item state rather than a single job-level success flag.
- **Can two instances run at once?** In a scheduled environment with retries, or two application replicas each running a cron, yes - by accident.
- **Whose 02:00, and whose today?** With accounts in multiple countries, a naive date comparison invoices some accounts twice and some never. This is the trap most people walk into.

## Back-of-envelope they should reach

- 100,000 accounts at 200 ms each (query, render a PDF, call the email provider) is 5.5 hours serially. Business hours arrive first.
- Parallelism of 20 brings it to ~17 minutes, and now the email provider's rate limit is the binding constraint rather than your compute.

## Deep dives (pick two or three)

1. **Idempotency and resumability.** Per-account state, not a single job flag: a row per (account, billing period) with a unique constraint, so a re-run skips completed work and the constraint makes double-invoicing structurally impossible. This turns "restart the job" from a frightening operation into a routine one.
2. **Concurrency control.** A lock or lease so two instances do not both run, with the lease held by the runner and expiring so a crashed runner does not block forever. Better still, make the work item-level idempotent so a second runner is harmless rather than forbidden.
3. **Time.** Store and compare in UTC, but "the account's billing date is today" is a question about the account's local calendar. Getting this wrong is invisible in testing and produces duplicate or missing invoices at the edges of the day.
4. **Observability.** A job that fails silently is worse than no job. Needs: a completion signal with a count, an alert if it did **not** run (absence of success, not presence of failure - a dead-man's switch), a per-item failure count, and a dead letter for items that failed repeatedly.
5. **Partial failure of the email step.** The invoice is generated and the email provider times out. Separate the two steps and their state, so a retry re-sends without regenerating - and so an ambiguous send does not regenerate an invoice number.

## Strong-answer signals

- Per-item state with a unique constraint, rather than a job-level flag.
- Alerts on the job **not running**, which is the failure mode a failure-alert cannot catch.
- Separates generate from send, with their own states and retries.
- Notices the timezone question unprompted.
- Chunks the work and bounds concurrency to the slowest downstream dependency.
- Says how they would test it - including running it twice and asserting nothing changes.

## Common traps

- One transaction around the whole run, held open for minutes or hours.
- A single "job succeeded" boolean, so a crash at 60% means either re-running everything or skipping the rest.
- Assuming only one instance can ever run.
- Naive date comparison across time zones.
- Only alerting on failure, so a job that never started is invisible.
- Sending the email before recording that it was sent.

## Follow-ups

- The job dies at 02:40 with 60,000 of 100,000 done. What do you do at 02:41?
- Two instances start simultaneously. What happens?
- The email provider is down for the whole window. What does the morning look like?
- An account is in New Zealand. When is its billing date today?
- The job has not run for three days. How long until someone finds out?
