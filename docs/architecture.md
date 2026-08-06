# Architecture

## The split

Three parts, with a deliberate line between them.

| Part | Is | Where |
|---|---|---|
| **Engine** | scheduling, scoring, selection, metrics | `studykit/`, pure Python stdlib |
| **Content** | topics, cards, questions, problems | `packs/`, TOML and markdown |
| **Teaching** | asking, judging, explaining | `.agents/skills/`, run by an agent |

The line matters because each part fails differently. Deterministic logic that drifts between sessions is a bug you cannot see; content that lives in code cannot be shared; and judging an answer is not something you can write a function for.

**Anything that must be identical every time is code.** Interval arithmetic, queue order, question selection, coverage, metrics. If the scheduler were a paragraph of instructions to a model, two identical sessions would produce different due dates and nobody would notice.

**Anything requiring judgement is the agent.** Whether an answer named the tradeoff, whether a worked example landed, what the gap actually was.

## Agent harnesses

One copy of every instruction, symlinked into the places each harness looks:

```
AGENTS.md             the instructions
CLAUDE.md         ->  AGENTS.md
.agents/skills/       the session protocols, one directory per skill
.claude/skills/   ->  ../.agents/skills
```

`.agents/` is Codex's repo-level convention and `AGENTS.md` is read by most agents; Claude Code wants `CLAUDE.md` and `.claude/skills/`, and follows both symlinks. `AGENTS.md` names the skills by path, so a harness that does not auto-discover them still finds them.

Support a new harness by symlinking, never by copying. Two copies of a protocol drift, and the copy that drifts is the one nobody is reading.

## Token efficiency

The agent never reads pack files. That is the design decision that keeps a session cheap.

`./study plan 25m` returns a session: the calibration brief, the blocks in order, and the twelve questions already drawn, filtered by level, and interleaved. A few kilobytes. The alternative (reading a manifest, three cards and four question banks, then choosing) is a hundred times that, and worse, it re-derives selection logic every time.

The same principle runs through the rest of the surface:

- `plan` refers to cards and problems **by command**, not by inlining them. Most sessions never open one.
- `record` takes a compact payload with top-level defaults, so a twelve-row session is a dozen short objects.
- `progress` returns a rendered report rather than raw data to be interpreted.

Rule of thumb when extending it: **if the agent would have to read a file to decide something, the CLI should decide it and return the answer.**

## Data flow

```
packs/*.toml ──┐
               ├──► select.py ──► plan / questions  ──► agent runs the session
data/ledger ───┤                                              │
               │                                              ▼
               └──► schedule.py ──► state.json ◄──── record (append + rebuild)
                    metrics.py  ──► metrics.json ──► report.py   ──► terminal
                                                  └► dashboard.py ──► HTML
```

`ledger.jsonl` is the only source of truth. It is append-only and never edited. `state.json` and `metrics.json` are pure functions of it plus the pack taxonomy, rebuilt on every `record`, and deleting them loses nothing.

That property is worth protecting. It means a scheduling change is retroactive: fix the interval function, run `./study rebuild`, and every due date is recomputed from the same history. If state were mutated in place, a bug in the scheduler would be baked into the data.

## Modules

| Module | Responsibility |
|---|---|
| `config.py` | paths, levels, profile, date arithmetic |
| `packs.py` | loading packs, merging the user's bank overlay |
| `ledger.py` | row validation and append-only I/O |
| `schedule.py` | the interval algorithm. **The only implementation** |
| `select.py` | queue order, question drawing, session composition |
| `metrics.py` | everything `metrics.json` contains |
| `report.py` | terminal rendering. Reads only |
| `dashboard.py` | self-contained HTML |
| `tomlwrite.py` | just enough TOML writing to append a banked question |
| `sync.py` | backing the data directory up to its own git remote |
| `cli.py` | argument parsing and command handlers |

Dependencies run one way: `cli` → everything, `select` → `schedule` + `packs` + `ledger`, `schedule` → `ledger` + `packs`, `config` → nothing. No module imports `cli`.

## Rules enforced in code, not in prose

The scoring model has rules that were previously guidance and were violated anyway. These are now mechanical:

- **A measurement must name a facet the pack declares.** `ledger.validate` rejects anything else, so a typo cannot create a phantom facet that is never scheduled.
- **Derived fields cannot be written.** Passing `strength`, `interval`, `due` or `reps` to `record` is an error, not a silent override.
- **A problem row must name a problem.** `topic` must be `problem:<slug>` with `subtopic: overall`, so a problem score cannot be recorded as a topic score.
- **A question id must be banked before it is referenced.** This is what makes "anything shown is banked" true rather than aspirational.
- **Several measurements of one facet on one date collapse to one rep.** Implemented in `compute_items`, so no session can inflate its own evidence count.

## Why not a database

The ledger is a few hundred lines of JSONL after a year of daily use. It is greppable, diffable, and trivially portable. A database would add a dependency, a schema migration story, and a file you cannot read, in exchange for query performance nobody needs at this scale.

The same reasoning applies to packs in TOML rather than in a content service, and to a generated HTML file rather than a dashboard server.

## Extending it

**A new pack.** See [authoring-packs.md](authoring-packs.md). No code changes.

**A new session type.** A skill in `.agents/skills/`, plus a session name in `ledger.SESSIONS` if it should be distinguishable in reports.

**A new technique block.** Add it to `TECHNIQUES` in `select.py` with its cost, then give it a trigger in `_targeted_blocks`. The trigger is the interesting part: a block that fires on preference rather than on a diagnosis is just a menu item.

**A different interval function.** `next_interval` in `schedule.py` is pure and tested. Change it and run `./study rebuild`; history is recomputed rather than migrated.

**A different dashboard.** `metrics.json` is a stable public artefact. Read it with anything.

## Tests

```
./study test --verbose
```

Coverage is concentrated where correctness is not obvious by inspection: the interval function and its caps, the session-mean collapse, `overall` supersession, level filtering, ledger validation and its rejections, and the end-to-end record-then-rebuild path. The content packs are validated by `./study doctor`, which is the more useful check for them.
