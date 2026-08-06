# CLI reference

```
./study <command> [options]
```

Global options work on either side of the command name:

- `--date YYYY-MM-DD` — treat this as today. For backfilling, or for testing.
- `--json` — machine-readable output where a human view also exists.
- `--version`

Environment:

| Variable | Effect |
|---|---|
| `STUDYKIT_DATA` | where your data lives. Default `<repo>/data`. |
| `STUDYKIT_PACKS` | where packs are loaded from. Default `<repo>/packs`. |
| `STUDYKIT_PYTHON` | which interpreter to use, if `python3` is older than 3.12. |
| `STUDYKIT_TODAY` | override today's date globally. |
| `NO_COLOR` | disable colour. |

Errors exit `2` with a one-line message on stderr and no traceback. `doctor` exits `1` when it finds problems.

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
```

Rebuilds state and metrics on any change.

---

## Reading

### `status`

One screen: overdue count, due today, never tested, coverage, mean strength, and the recommended next session.

### `progress`

The full report — due now, never measured, weakest facets, score by question type, calibration, thin evidence, uncovered areas, problems, and a recommendation. `--json` gives state, metrics and recommendation together.

### `queue`

The ordered work list: overdue first (weakest first within that), then never-measured, then due today. `--limit N`, `--json`.

### `packs`

What content is installed and how covered it is, per topic. `--all` includes packs not enabled in your profile.

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

**The prompt and the notes are separate files.** Without `--notes` you cannot get the notes, which is what makes it safe for an agent to fetch a problem mid-session.

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

Draws questions from the bank, filtered to your level, ordered by the queue, interleaved across topics.

```
./study questions --count 8
./study questions --topic caching --subtopic hot-key
./study questions --qtype judgment --count 5
```

The response includes `author_for`: facets with no in-level question banked, which the agent should write and bank.

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

Top-level `pack`, `topic` and `levels` act as defaults for every question; each question may override them. `levels` defaults to your level and everything above it.

Writes to `data/bank/<pack>/<topic>.toml` — your private overlay, which merges with the shipped pack at load time. `--into-pack` writes into the pack itself instead, for pack authors.

Also accepts `--file` or piped stdin.

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

`session`, `pack`, `date` and `level` at the top level are defaults for every row. A bare JSON array of rows also works.

| Field | Required | Notes |
|---|---|---|
| `session` | yes | `quiz` `practice` `review` `learn` `study` `drill` |
| `pack` | yes | must be installed |
| `topic` | yes | a pack topic, or `problem:<slug>` |
| `subtopic` | yes | declared by the topic, or `overall` |
| `measured` | yes | 1-5, the **cold** score |
| `qtype` | no | quiz rows only |
| `qid` | no | must already be banked |
| `predicted` | no | the user's own number. Omit if they did not give one |
| `post` | no | variant re-test after teaching. Never schedules |
| `taught` | no | true if the 1-2 branch ran |
| `note` | no | free text, shown in reports |

Rejected: unknown topics or subtopics, unknown question ids, scores outside 1-5, and any attempt to set a derived field (`strength`, `interval`, `due`, `reps`). `--dry-run` validates without writing.

Several rows for one facet on one date collapse to their mean and count as **one** rep — that is intended, not a bug.

### `rebuild`

Recomputes `state.json` and `metrics.json` from the ledger. `record` does this automatically; you only need it after editing the ledger by hand or changing packs.

### `dashboard`

```
./study dashboard
./study dashboard --open
./study dashboard --out ~/study.html
```

Writes a self-contained HTML page — inline CSS, inline SVG, no network requests. Light and dark, with a theme toggle.

---

## Maintenance

### `doctor`

Validates packs and data: missing cards, unknown subtopics in questions, duplicate ids, problems missing a prompt or notes, areas not declared, and every ledger row re-validated against the current taxonomy.

```
./study doctor
./study doctor --verbose      # also list notes, e.g. topics with no questions at a level
```

Exits 1 if it finds problems. Worth running after editing a pack.
