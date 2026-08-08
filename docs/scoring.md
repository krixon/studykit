# Scoring and scheduling

The measurement model. Implemented in `studykit/schedule.py` and nowhere else.

## Three constructs, never merged

| Field | Is | Drives |
|---|---|---|
| `predicted` | the user's own pre-answer rating | calibration only, **never** scheduling |
| `measured` | cold-recall score, taken before any teaching | scheduling and metrics |
| `state.json` | derived from `measured` | what comes up next |

Never hand-set derived state. Never let a self-report move a schedule. `studykit/ledger.py` enforces both: it rejects a row naming a facet the pack does not declare, and rejects any attempt to write a derived field.

`predicted` is the user's number. If they did not state one, the field is **absent**. It is not inferred from how confident an answer sounded, and it is not reconstructed later.

## Score scale

Cold recall, 1-5, judged **before any teaching**:

| | Meaning |
|---|---|
| 1 | No usable answer |
| 2 | A fragment, **or a confident wrong answer** |
| 3 | Core idea, missing the why or the cost |
| 4 | Correct with the tradeoff named |
| 5 | Correct, quantified, and volunteers a failure mode or boundary |

A confident wrong answer scores **2, not 3**. Conflation is worse than a blank, because a blank knows it is a blank and will not self-correct into a design decision.

The scale is fixed; the **bar** moves with level. See [levels.md](levels.md).

## Item identity

The atom is `pack / topic / subtopic`. Everything is measured, stored and scheduled at that level. Topic-level strength is derived, never stored.

Problems are a separate item type: `pack / problem:<slug>`, always with `subtopic: overall`. They carry a performance score and never contribute strength to topics.

## Strength

`strength` is the **most recent** measured score for that sub-topic. Not an average: an old 5 does not offset a fresh 2. History lives in the ledger and drives the trend chart, not current state.

Where several measurements land on one date (several quiz questions on one facet), they collapse to the **mean of that date, rounded half up, counted as one rep**. Eight questions about caching is one piece of evidence about caching, not eight.

A row records the full timestamp it was measured at. Scheduling reads the calendar day off it, so the collapse holds however far apart in the day the questions were asked.

## Evidence quality

Every item tracks `reps`, the count of direct measurement **dates**. This caps how far ahead it can be scheduled:

| reps | Maximum interval |
|---:|---:|
| 1 | 3 days |
| 2 | 10 days |
| 3+ | uncapped, to a 120-day ceiling |

One answer is evidence of not-failing-once, not of mastery. Without the cap, a single lucky 5 schedules itself a week out.

## Interval

SM-2 style, on the **measured** score, from the previous interval:

- **1-2**: reset to 1 day
- **3**: previous × 1.6, minimum 2 days
- **4**: previous × 2.2
- **5**: previous × 3.0
- First measurement starts from a base interval of 2 days
- Then the `reps` cap above, then the 120-day ceiling
- `due = last_measured + interval`

Problems are exempt from the `reps` cap, because a problem is a broad integration measure rather than a single data point. They still respect the ceiling.

**Topic due date** is the earliest due date among its sub-topics. A topic is never "done" while any facet is stale.

The multipliers are conventional, not derived. See the *Contested* section of [research.md](research.md).

## Calibration

`predicted` is captured per question, before the answer, on the same 1-5 scale. It never touches scheduling. It feeds one metric: **mean signed error, `predicted - measured`**, tracked over time. Positive means overconfidence.

## Pretesting

Every session type tests **before** it teaches. Attempting and failing before instruction beats errorless study for retention, and the failed attempt is the honest number anyway. Warrant: [research.md](research.md), retrieval before instruction.

The pretest is a primer for instruction, not a replacement for it.

## The follow-up ladder

A cold score is a diagnosis, and the three bands need different treatment. Teaching identically at every level wastes time at the top and fails to land at the bottom.

| Cold `measured` | What follows | Why |
|---:|---|---|
| 4-5 | One line: a confirmation, or the boundary they did not volunteer. | Guidance at this level is redundant and costs working memory: expertise reversal. |
| 3 | The specific gap, named. | The schema is there; only the missing piece needs supplying. |
| 1-2 | A **worked example**, then a **variant** re-test later in the same session, logged as `post`. | A 1-2 means there was nothing to generate from. Correction alone produces fluency without encoding. |

The re-test has to be a variant rather than the same question, because recognition lets an answer be confirmed without retrieving anything, and it has to be spaced by other work, because back-to-back is a working-memory read. How a session runs the ladder is in the skills; this is what the bands mean.

Warrant: [research.md](research.md), *prior knowledge gates unguided struggle* and *feedback needs a second retrieval*.

## What `post` means

`post` is the variant re-test score, after teaching. It is informational and **never schedules**: `measured` stays the cold number and drives the interval alone.

It earns its place as a diagnostic of the **teaching**, not the learner. A 2 that stays 2 after a worked example means the explanation missed, or the facet needs a dedicated `learn` session rather than a quiz slot. A 2 that reaches 4 means the gap was exposure, and the next rep will tell whether it stuck.

## What each session may write

| Session | May write |
|---|---|
| `quiz` | sub-topic measurements, one per question, with `qtype` |
| `practice` / `review` | a `problem:` score, plus sub-topic rows **only** for facets directly exercised, direction following the evidence |
| `learn` | a pre-teaching measurement, and optionally `post` after teaching |
| `study` | whatever its composed blocks write |

**Problem scores never propagate to topics.** A problem score measures performance on that problem. It may emit sub-topic measurements for facets it genuinely exercised, including negative ones, and it never lifts a topic's strength on its own.

**Measure only what you tested.** A session scores the facets it directly exercised, and the direction follows the evidence. No inference from adjacency, no bumping a topic because a related one went well. If it was not tested, it gets no number.

## Technique selection by strength

Worked examples help at low strength and actively hurt at high strength: expertise reversal, see [research.md](research.md). The composer picks accordingly:

| Strength | Default technique |
|---:|---|
| 1-2 | faded worked example, contrasting cases |
| 3 | discrimination and judgment questions |
| 4-5 | judgment, numeric, diagnostic inversion, full problems |

## Question fairness

A question may only require material the pack actually carries: what is on the card, or what follows from it by reasoning the card supports. Asking for a derivation the material never introduces measures nothing and scores an unfair 1.

Pretesting works because the learner has something to generate from and fails at the edge of it. A question outside the material is not a desirable difficulty, just a wrong one.

If a question is worth asking and the card lacks its grounding, **the card is what needs fixing**.

## The ledger is the only source of truth

`~/.studykit/ledger.jsonl` is append-only and never edited. `state.json` and `metrics.json` are generated from it by `./study record` (or `./study rebuild`), never hand-edited, and lose nothing when deleted.
