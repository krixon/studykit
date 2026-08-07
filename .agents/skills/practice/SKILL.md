---
name: practice
description: Work a full design problem from a pack, in coaching or interview mode. Use when the user wants to attempt a problem end to end, or re-attempt one cold. Presents the candidate-facing prompt only, runs the attempt, gives structured feedback, and records sub-topic measurements for the facets the problem actually exercised.
---

# Practice

A full problem. The only block that measures integration, and the only place the transfer gap shows up - the difference between a facet's strength in isolation and its strength when it has to be recognised inside a larger problem.

## Setup

1. **Mode.** Coaching (default: collaborative, hints allowed, feedback inline) or interview (present it and get out of the way, neutral open probes only, no teaching, all feedback held to the end). Ask once if not stated; the user can switch mid-session.

2. **Select.**
   ```
   ./study problem            # the one the scheduler picks
   ./study problem --list     # everything at this level, with attempt history
   ./study problem <slug>     # a specific one
   ```
   For a cold re-attempt, do not show the previous attempt first.

3. **Present the candidate-facing prompt only.** `./study problem <slug>` prints exactly that.

   **Do not read the interviewer notes until the attempt is over.** They are a separate file for a reason. When the attempt ends:
   ```
   ./study problem <slug> --notes
   ```

## Run

Let the user drive.

- **Coaching**: nudge through phases they skip - requirements, estimates, high-level design, deep dives, bottlenecks and failure - with pointed questions rather than lectures.
- **Interview**: do not enumerate sub-parts or hint at structure. Answer clarifying questions, ask neutral open probes, hold everything else.

Then probe two to four follow-ups from the notes and from whatever they glossed over.

Apply the level bar. `./study levels` prints the calibration brief for each level; the notes for some problems also carry per-level guidance. A mid-level candidate is not expected to volunteer blast radius; a staff candidate who does not is showing you something.

## Feedback

**Verdict** in one line - would this pass the bar for their level, and where is the gap. Then:

- **Strengths** - specific, not encouraging noise.
- **Gaps and what a stronger answer adds** - name the technique, the number, the failure mode.
- **Follow-ups they should be able to answer.**
- **Cards worth reading** - `./study card <topic>`.

## Record

Write the attempt to `~/.studykit/attempts/<pack>/<slug>/YYYY-MM-DD.md` in whatever structure serves the diff. For a re-attempt, compare against the previous file and call out what improved and what regressed.

Then:

```
./study record --json-text '{"session":"practice","pack":"system-design","rows":[
  {"topic":"problem:url-shortener","subtopic":"overall","measured":4},
  {"topic":"caching","subtopic":"hot-key","measured":2,"note":"missed the L1 for the hot-key tail"},
  {"topic":"api-design","subtopic":"errors-status","measured":4}
]}'
```

**The rule that matters here:** a problem score measures performance on that problem. It may emit sub-topic rows for facets the attempt genuinely exercised, including negative ones, and it **never lifts a topic's strength on its own**. A good overall score does not raise a topic whose facets went badly - if the attempt showed a caching failure, record the caching failure, whatever the overall verdict was.

Problem rows must use `subtopic: "overall"` and a `problem:<slug>` topic; the CLI rejects anything else.
