# CLI reference

```
./study <command> [options]
```

Global options work on either side of the command name:

- `--date YYYY-MM-DD`: treat this as today, for what is due and how overdue it is. For testing, or for reading the queue as it stood. It never changes when a measurement happened.
- `--json`: machine-readable output where a human view also exists.
- `--version`

Environment:

| Variable | Effect |
|---|---|
| `STUDYKIT_DATA` | where your data lives. Default `$XDG_DATA_HOME/studykit`, else `~/.studykit`. |
| `STUDYKIT_PACKS` | where the shipped packs are read from. Default `<repo>/packs`. Installed packs always come from the data directory as well. |
| `STUDYKIT_PYTHON` | which interpreter to use, if `python3` is older than 3.12. |
| `STUDYKIT_TODAY` | override today's date, for `as_of` reasoning. |
| `STUDYKIT_NOW` | override the timestamp new rows are stamped with. |
| `NO_COLOR` | disable colour. |

Errors exit `2` with a one-line message on stderr and no traceback. `doctor` and `test` exit `1` when they find problems.

A command invoked with nothing to act on prints its own help and exits `0`, rather than treating the omission as an error. That covers `./study` itself, the commands that only group subcommands, and the ones that need an argument or a JSON payload to do anything.

---

## Getting started

### `setup`

Interactive first run. Sets your level, packs, default session length and default problem mode, then creates the data directory.

```
./study setup
./study setup --level senior --packs system-design,foundations --non-interactive
./study setup --force                 # overwrite an existing profile
```

Options: `--level`, `--packs`, `--budget`, `--mode`, `--no-confidence`, `--non-interactive`, `--force`.

### `config`

```
./study config get                    # everything, as JSON
./study config get level
./study config set level lead
./study config set packs system-design,design-patterns
./study config set budget 45m
./study config set mode interview
./study config set confidence_prompt false
./study config set sync_auto true
```

Rebuilds state and metrics on any change.

| Key | Effect |
|---|---|
| `level` | the interviewer bar, which topics are in scope, and the question-type mix |
| `packs` | comma-separated, what is in rotation |
| `budget` | default session length |
| `mode` | `coaching` or `interview` |
| `confidence_prompt` | whether to ask for a pre-answer confidence |
| `sync_remote` | git remote backing up the data directory. Set it with `sync init` |
| `sync_branch` | branch on that remote. Default `main` |
| `sync_auto` | push after every session that writes. Needs a remote first |

---

## Reading

### `status`

One screen: overdue count, due today, never tested, coverage, mean strength, and the recommended next session.

### `progress`

The full report: due now, never measured, weakest facets, score by question type, calibration, thin evidence, uncovered areas, problems, and a recommendation. `--json` gives state, metrics and recommendation together.

### `queue`

The ordered work list: overdue first, then due today, staler first within each band, with weakness breaking ties. Every third slot is held for a never-measured facet, so a backlog cannot starve discovery. `--limit N`, `--json`.

### `packs`

Every installed pack, marked `on` or `off` by whether it is in rotation, with per-topic coverage at your level.

```
./study packs                         # what is installed, and what is on
./study packs enable foundations      # add to the rotation
./study packs disable design-patterns # remove from it
```

Both take several names. Rotation is what `plan`, `questions` and `queue` draw from; an installed pack that is off stays listed and stays out of the queue. Taking the last pack out is refused, because an empty rotation means every pack rather than none.

### `levels`

The level ladder and each enabled pack's calibration brief.

### `card <topic>`

Prints a knowledge card. `--pack` disambiguates if two packs share a topic id. `--json` wraps it with the topic's metadata.

### `problem [slug]`

```
./study problem                       # the one the scheduler picks
./study problem --list                # everything at your level, with history
./study problem url-shortener         # the candidate-facing prompt
./study problem url-shortener --notes # the interviewer notes
```

**The prompt and the notes are separate files.** Without `--notes` the notes are unreachable, which is what makes it safe for an agent to fetch a problem mid-session.

### `export <what>`

Prints `state`, `metrics`, `ledger` or `profile` as JSON, for piping elsewhere.

---

## Running a session

These emit JSON and are meant for an agent.

### `plan [budget]`

Composes a session to fit the budget: the calibration brief, blocks in order, questions already drawn and interleaved, and a queue preview.

```
./study plan 25m
./study plan 1h
./study plan "half day"
./study plan                          # your configured default
```

Options: `--level` (override for this call), `--mode`, `--seed N` (reproducible), `--no-problem`.

Budgets accept `15m`, `1h`, `90`, `half day`, `full day`, `quick`, `open`.

### `questions`

Draws questions from the bank across the topics in scope at your level, ordered by the queue, interleaved across topics.

```
./study questions --count 8
./study questions --topic caching --subtopic hot-key
./study questions --qtype judgment --count 5
```

Anything already recorded today is excluded, and unshown or long-unseen questions are preferred over recently answered ones.

The type mix comes from your level and your measured means per type, described in [levels.md](levels.md#what-your-level-changes). Within a type, questions written for your level come first and the rest of the topic is the fallback.

The response includes `author_for`: facets with no question left to draw.

---

## Writing

### `bank add`

Banks questions generated during a session. Assigns ids; never write ids yourself.

```
./study bank add --json-text '{
  "pack": "system-design",
  "topic": "caching",
  "questions": [
    {"subtopic": "hot-key", "qtype": "judgment", "q": "...", "a": "..."}
  ]
}'
```

Top-level `pack`, `topic` and `levels` act as defaults for every question; each question may override them. `levels` defaults to your level alone, since a question asked mid-session was written for the level it was asked at. Set it explicitly if the question suits a range.

Writes to `~/.studykit/bank/<pack>/<topic>.toml`, your private overlay, which merges with the pack at load time. The CLI assigns each id as `<prefix>-u<hash of the question>`. `--into-pack` writes into the pack's own directory instead, with a sequential id, for pack authors.

Also accepts `--file` or piped stdin.

A question stating a figure needs a `derivation`, and is refused without one, or if a figure in it matches no derivation result. Nothing is written when a batch is refused. See [authoring-packs.md](authoring-packs.md#figures-are-derived-not-asserted).

### `bank check`

The same figure check, writing nothing. Use it **before** a question is asked, not after.

```
./study bank check --json-text '{"questions": [
  {"q": "Origin is 150 ms RTT away and setup is 350 ms.", "a": "Three round trips.",
   "derivation": ["rtt_ms = 150", "setup_ms = 3 * rtt_ms"]}
]}'

error: These figures match no derivation result: 350 ms.
       The derivation gives rtt_ms = 150, setup_ms = 450.
```

Returns the figures it found and every value it computed, so it doubles as a way to see what the scanner considers a magnitude.

### `record`

Appends measurements, then rebuilds `state.json` and `metrics.json`.

```
./study record --json-text '{
  "session": "quiz",
  "pack": "system-design",
  "rows": [
    {"topic": "caching", "subtopic": "hot-key", "qtype": "judgment",
     "qid": "ca-014", "measured": 2, "predicted": 4, "post": 4, "taught": true}
  ]
}'
```

`session`, `pack`, `at` and `level` at the top level are defaults for every row. A bare JSON array of rows also works.

**When a row happened.** The ledger stores `at`, a full local timestamp with its offset, and a row is stamped with the moment it is recorded. Set `at` yourself only to be exact about a session you are writing up. `--date` is the `as_of` for the rebuild that follows and has no bearing on when a measurement happened.

Scheduling works in whole days, read off `at`.

| Field | Required | Notes |
|---|---|---|
| `session` | yes | `quiz` `practice` `review` `learn` `study` `drill` |
| `pack` | yes | must be installed |
| `topic` | yes | a pack topic, or `problem:<slug>` |
| `subtopic` | yes | declared by the topic, or `overall` |
| `measured` | yes | 1-5, the **cold** score |
| `at` | no | ISO 8601 local timestamp. Defaults to now |
| `qtype` | no | quiz rows only |
| `qid` | no | must already be banked |
| `predicted` | no | the user's own number. Omit if they did not give one |
| `post` | no | variant re-test after teaching. Never schedules |
| `taught` | no | true if the 1-2 branch ran |
| `note` | no | free text, shown in reports |

Rejected: unknown topics or subtopics, unknown question ids, scores outside 1-5, and any attempt to set a derived field (`strength`, `interval`, `due`, `reps`). `--dry-run` validates without writing.

### `rebuild`

Recomputes `state.json` and `metrics.json` from the ledger. `record` does this automatically; you only need it after editing the ledger by hand or changing packs.

### `dashboard`

```
./study dashboard
./study dashboard --open
./study dashboard --out ~/study.html
```

Writes a self-contained HTML page: inline CSS, inline SVG, no network requests. Light and dark, with a theme toggle.

---

## Maintenance

### `sync`

Backs the data directory up to a git remote of your own. The tool repo and the data repo are separate: `studykit` can be public while your ledger is not.

```
./study sync init git@github.com:you/studykit-data.git
./study sync init git@github.com:you/studykit-data.git --auto
./study sync                          # commit what changed, push
./study sync -m "after the Friday session"
./study sync status
```

`init` makes the data directory its own git repository, points it at the remote, writes a `.gitignore` for the derived files, and pushes. It refuses when the remote already has history. Clone that into your data directory instead:

```
rm -rf ~/.studykit && git clone git@github.com:you/studykit-data.git ~/.studykit
```

Only the source of truth is tracked: `ledger.jsonl`, `profile.json`, `bank/` and `attempts/`. `state.json`, `metrics.json` and `dashboard.html` are rebuilt on every write, so committing them would produce a diff on every command and a conflict on every second machine.

With `sync_auto` on, every `record` and `bank add` pushes. A failed push never fails the session: the measurement is already on disk, and a warning tells you to run `./study sync` later.

`doctor` reports whether anything is unpushed, and flags a configured remote whose data directory is not a repository.

### `test`

Runs the repository test suite.

```
./study test
./study test --verbose
```

### `doctor`

Validates packs and data: missing cards, unknown subtopics in questions, duplicate ids, problems missing a prompt or notes, areas not declared, and every ledger row re-validated against the current taxonomy.

Notes also carry what each level can supply, against the targets in [question-types.md](question-types.md#levels): any level where too few facets hold a question of a type its mix will ask for, and any level holding fewer than two questions per in-scope facet. Both are notes rather than problems, since a target is an authoring guide.

```
./study doctor
./study doctor --verbose      # also list notes, e.g. topics with no questions at a level
```

Exits 1 if it finds problems.
