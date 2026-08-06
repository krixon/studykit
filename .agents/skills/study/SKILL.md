---
name: study
description: Budget-driven study session across the installed packs. Use when the user says how much time they have ("study 15m", "I've got an hour", "all afternoon") or just wants to be told what to work on. Composes a session from the due queue, runs it, records the measurements and rebuilds the metrics.
---

# Study

The main entry point. The user gives a budget; the CLI chooses the work. They should never have to decide what to practise.

## Compose

```
./study plan 25m
```

That returns JSON: the level calibration brief, the blocks to run in order, the questions already drawn, and a queue preview. Selection is deterministic and lives in code - do not second-guess it, and do not go picking topics yourself.

If the user gave no budget, use `./study plan` (it uses their configured default) or ask once, offering 10m / 25m / 1h.

State the plan in **one line**, then start. No menus, no ceremony.

## Run

Each block carries an `instruction` field. Follow it.

- `quiz-set` — run the `quiz` protocol on the supplied questions.
- `full-problem` / `cold-re-attempt` — run the `practice` protocol on the named problem.
- `faded-worked-example`, `contrasting-cases`, `diagnostic-inversion`, `teach-back`, `estimation-drill`, `card-writing` — the instruction describes the block. Fetch the card with `./study card <topic> --pack <pack>` only if you need the material.

If a block has `author_for` entries, the bank has no in-level question for those facets. Write one, ask it, and bank it (see below).

**Apply the calibration brief.** The plan's `calibration` block states the bar for the user's level, what to push on, and what not to demand. A graduate answering correctly at graduate level scores well; do not silently judge them at staff level.

Keep typing low. Terse bullets are a complete answer. Infer structure from fragments and probe only the gaps that matter.

## Record

Two calls, in this order, because a ledger row naming an unbanked question id is rejected.

**1. Bank anything you generated.** Every question shown gets banked, with no exceptions. The CLI assigns the id.

```
./study bank add --json-text '{"pack":"system-design","topic":"caching","questions":[
  {"subtopic":"hot-key","qtype":"judgment","q":"...","a":"..."}
]}'
```

**2. Record the measurements.**

```
./study record --json-text '{"session":"study","pack":"system-design","rows":[
  {"topic":"caching","subtopic":"hot-key","qtype":"judgment","qid":"ca-014","measured":3,"predicted":4}
]}'
```

`record` rebuilds `state.json` and `metrics.json` itself. Nothing else to run.

Then offer `./study dashboard --open` if they want to see the charts.

## The rules that are not negotiable

- **Score cold, before teaching anything.** `measured` is always the pre-teaching score. A confident wrong answer is a 2, not a 3.
- **`predicted` is the user's own number.** If they did not state one, leave the field out. Never infer it from how confident they sounded.
- **Measure only what you tested.** No inference from adjacent topics, no bumping a topic because a related one went well.
- **A problem score never lifts a topic.** It may emit sub-topic rows for facets it genuinely exercised, in either direction.
- Full model: `docs/scoring.md`. Warrants: `docs/research.md`.

## House style

Name gaps directly. Do not cheerlead.
