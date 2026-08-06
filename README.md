# studykit

A spaced-repetition study kit for engineering knowledge, driven by a coding agent.

You tell it how long you have. It decides what you work on, asks questions calibrated to your level, scores you before it teaches you anything, and schedules what comes back and when. The scheduling, scoring and metrics are code; the teaching is an agent; the content is data.

```
git clone <this repo> && cd studykit
./study setup
```

Then say **`study 25m`** to your coding agent. Claude Code and Codex both work out of the box; so does anything else that reads `AGENTS.md`.

No dependencies, no install, no virtualenv, no account. Python 3.12+ and a shell.

---

## What it does

| Say | Get |
|---|---|
| `study 25m` / "I've got an hour" | a session composed from the due queue to fit the box |
| `quiz` | rapid-fire questions, judgment-weighted, low typing |
| `practice` | a full design problem, coaching or interview mode |
| `learn <topic>` | taught properly - tested first, then taught to the gap |
| `progress` | what's due, what's weak, what's never been measured |

`study` is the default. It picks the work so you don't have to.

## What ships with it

Three content packs, ready to use:

| Pack | Topics | Questions | Problems | For |
|---|---:|---:|---:|---|
| **foundations** | 10 | 127 | 4 | HTTP, SQL, concurrency, testing, security, encoding, the OS |
| **design-patterns** | 8 | 93 | 3 | SOLID, GoF patterns, DI, coupling, refactoring, boundaries |
| **system-design** | 16 | 237 | 12 | caching through multi-region, graduate to Staff+ |

Every question is tagged with the levels it suits, so a graduate and a staff engineer studying the same topic get different questions and are judged against different bars.

## Levels

`graduate` · `mid` · `senior` · `lead` · `staff`

Your level does three things: filters the question bank, filters which topics and problems are in scope, and sets the **calibration brief** the agent judges you against. At graduate, a correct mechanism scores well. At staff, an unquantified claim with no failure mode does not.

```
./study levels                    # see every level's bar
./study config set level lead     # change it
```

## How a session goes

```
you:   study 25m
agent: 12 questions across 12 topics, weakest first. Starting.
       > What is the boundary defect in a fixed-window counter?
you:   burst at the end of one window plus the start of the next
agent: 4. You didn't say it's twice the limit in under one window - that's the number
       that makes it concrete.
       > p99 tripled, error rate flat, cache hit rate unchanged. Most likely cause?
...
agent: Recorded. caching/hot-key 2 -> 3, next 7 Aug. Two facets came back 2;
       both got a worked example and a variant re-test.
```

Then `./study dashboard --open` for the charts.

## The design in one paragraph

Retrieval practice reliably builds near transfer and reliably fails to build far transfer, which is the thing that actually matters past a junior level. So the unit of assessment is judgment, not facts: five question types weighted towards judgment and discrimination, interleaved across topics without announcing which topic a question comes from. Everything is measured at sub-topic granularity, scheduled only on cold-recall scores taken before any teaching, and never inferred from adjacent evidence. Self-reported confidence is captured but kept strictly away from scheduling, where it feeds a calibration metric instead. Every mechanism traces to a citation in [docs/research.md](docs/research.md), including the two places the evidence is genuinely contested.

## Your data

Everything you generate lives in `data/`, which is git-ignored:

```
data/profile.json      your level and preferences
data/ledger.jsonl      append-only history of every measurement
data/state.json        current strength and due dates, derived
data/metrics.json      computed metrics, derived
data/bank/             questions generated during your sessions
data/attempts/         your problem attempts
data/dashboard.html    generated charts
```

Nothing leaves your machine unless you ask it to. The ledger is the only source of truth; `state.json` and `metrics.json` are rebuilt from it on every `record`, so they can always be deleted and regenerated.

Point `STUDYKIT_DATA` somewhere else to keep it out of the repo entirely, or to run more than one profile.

### Backing it up

The ledger is the one thing here that cannot be regenerated. Give it a private repository of its own:

```
./study sync init git@github.com:you/studykit-data.git --auto
```

That makes `data/` its own git repository, separate from this one, and pushes after every session that writes. `./study sync` does it by hand; `./study sync status` says what is outstanding. Derived files stay untracked. On a second machine, clone the data repo into `data/` and carry on.

## Commands

```
./study setup                     interactive first run
./study status                    one screen: what's due, what's next
./study progress                  full report
./study plan 25m                  compose a session (JSON, for the agent)
./study questions --count 8       draw questions (JSON, for the agent)
./study card caching              print a knowledge card
./study problem --list            problems at your level
./study record --json-text '...'  append measurements, rebuild everything
./study dashboard --open          self-contained HTML charts
./study packs                     what content exists, how covered it is
./study sync                      push your data to its private repo
./study doctor                    validate packs and data
./study test                      run the test suite with Python 3.12+
```

Full reference: [docs/cli.md](docs/cli.md).

## Documentation

| File | What it covers |
|---|---|
| [docs/scoring.md](docs/scoring.md) | the measurement and scheduling model, in full |
| [docs/research.md](docs/research.md) | the evidence base every mechanism traces to |
| [docs/question-types.md](docs/question-types.md) | the five question types and why judgment is weighted |
| [docs/techniques.md](docs/techniques.md) | the block menu the session composer draws from |
| [docs/levels.md](docs/levels.md) | how levels filter content and set the bar |
| [docs/authoring-packs.md](docs/authoring-packs.md) | writing your own pack |
| [docs/cli.md](docs/cli.md) | every command and flag |
| [docs/architecture.md](docs/architecture.md) | how the pieces fit, and why the split is where it is |

## Requirements

Python 3.12 or newer, and a POSIX shell. That is the whole list. If `python3` on your PATH is older, set `STUDYKIT_PYTHON=/path/to/python3.12`.

Tests: `./study test --verbose`

Working on it? `git config core.hooksPath .githooks` runs the tests and `doctor` before every push. `git push --no-verify` skips them once.

## Licence

MIT. See [LICENSE](LICENSE).
