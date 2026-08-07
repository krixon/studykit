---
name: progress
description: Report learning progress. Use when the user asks what is due, how they are doing, where the blind spots are, or wants the metrics. Reads the computed report and interprets it; never practises and never edits state.
---

# Progress

Report, do not practise. Lead with what to do next.

```
./study progress
```

That prints the whole report: due now, never measured, weakest facets, score by question type, calibration, thin evidence, uncovered areas, problems, and a recommended next session. It is computed from the ledger, so it is always current.

For the underlying numbers:

```
./study progress --json     # everything, structured
./study status              # one screen
./study queue               # the ordered work list
./study packs               # what content exists and how covered it is
```

## What to add on top

The CLI gives the numbers. Your job is the reading of them:

- **Unknown beats stale.** A never-measured facet is a bigger risk than an overdue known-good one. If the report shows both, say which to attack first and why.
- **Score by question type is the diagnostic that matters.** High `recall` with low `judgment` means the knowledge is there and inert - that needs applied work, not more flashcards. Say so plainly when the gap is a point or more.
- **Calibration.** Positive mean error is overconfidence. Call it out without softening it.
- **Thin evidence.** Anything at one rep carrying a 4 or 5 is not mastery, only not-failing-once. Worth naming when the user is feeling good about a number.
- **Coverage.** Areas with no measurement at all are where a real interview will find them.

Finish with a single recommended next session and its budget. The report already suggests one; agree with it or give a better reason.

## Charts

```
./study dashboard --open
```

Writes a self-contained HTML page - trend over time, score by type, strength by area, calibration, and the same tables. No network, nothing leaves the machine.

## Do not

Do not recompute or edit state here. This skill only reads; `record` is the only thing that writes, and it rebuilds everything itself.
