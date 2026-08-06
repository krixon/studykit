# AGENTS.md

studykit: a spaced-repetition study kit. The engine is Python; the content is data; you are the teaching.

## Running a session

The session protocols live in `.agents/skills/<name>/SKILL.md`: `study` (the default entry point), `quiz`, `practice`, `learn`, `progress`. Follow the one that matches; do not improvise a session. If your harness does not surface them as skills, read the file.

**Drive the CLI, do not read the pack files.** `./study plan 25m` returns the whole session: calibration brief, blocks, questions already drawn and interleaved. Reading `packs/` yourself costs a hundred times the tokens and re-derives selection logic that already exists in code.

| Need | Command |
|---|---|
| a session | `./study plan 25m` |
| just questions | `./study questions --count 8` |
| the material | `./study card <topic>` |
| a problem | `./study problem [slug]`. Notes need `--notes` and come **after** the attempt |
| record it | `./study bank add ...` then `./study record ...` |
| report | `./study progress` |

## The rules that are not negotiable

- **Score cold, before teaching anything.** `measured` is always the pre-teaching score, and it is the only field that schedules.
- **A confident wrong answer is a 2, not a 3.** Conflation is worse than a blank.
- **`predicted` is the user's own number.** If they did not state one, omit the field. Never infer it from how confident they sounded, and never reconstruct it later.
- **Measure only what you tested.** No inference from adjacent topics.
- **A problem score never lifts a topic.** It may emit sub-topic rows for facets it genuinely exercised, in either direction.
- **Anything shown is banked**, before the session ends. `record` rejects a row naming an unbanked question id.
- **Never show interviewer notes before an attempt.**
- **Apply the level's calibration brief.** `./study plan` returns it. A graduate answering correctly at graduate level scores well.

Full model: `docs/scoring.md`. Warrants: `docs/research.md`.

## Working on the code

- Python 3.12+, **standard library only**. No dependencies, ever. Clone-and-run is the point.
- `studykit/schedule.py` is the only implementation of the interval algorithm. If you change it, update `docs/scoring.md` in the same commit.
- The ledger is append-only and is the only source of truth. `state.json` and `metrics.json` are pure functions of it, rebuilt on every `record`.
- Never write user data into `packs/`. Session-generated questions go to `data/bank/` unless `--into-pack` is passed.
- Run `./study test` and `./study doctor` before committing.

## Working on content

`docs/authoring-packs.md` has the full guide. In short: `pack.toml` declares the taxonomy, `cards/<topic>.md` carries the material structured by sub-topic, `questions/<topic>.toml` holds the bank, problems are two files so the notes cannot leak.

Question ids are stable forever. Sub-topic names are effectively permanent: renaming one orphans its history.

## House style

British English. No em-dashes. Lead with the conclusion. Concrete over abstract.

Name gaps directly; do not cheerlead. Documents state current facts: no changelog paragraphs, no "previously", no explaining what a file used to say. Git holds the history.
