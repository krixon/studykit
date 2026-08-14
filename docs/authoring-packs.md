# Authoring a pack

A pack is content. It declares what there is to learn and says nothing about scheduling, scoring or session structure, so it can be shared without carrying anyone's history.

## Layout

```
<name>/
  pack.toml                    manifest: levels, areas, topics, problems, calibration
  cards/<topic>.md             one knowledge card per topic
  questions/<topic>.toml       one question bank per topic
  problems/<slug>/prompt.md    candidate-facing ask
  problems/<slug>/notes.md     interviewer notes, never shown before an attempt
```

The filename conventions are load-bearing: `cards/<topic id>.md` and `questions/<topic id>.toml` are found by the topic's id, not by anything in the manifest.

Two directories are searched: `packs/` in the checkout, for the packs that ship with it, and `~/.studykit/packs/` for packs you install. Drop a directory into either and it is available. Installing to the second keeps `git status` clean and syncs the pack with your data to your other machines. Two packs sharing a name is an error naming both directories.

`./study packs enable <name>` and `./study packs disable <name>` choose what is in rotation, or `./study config set packs a,b` replaces the list outright. `./study packs` says where each one was loaded from.

## pack.toml

```toml
[pack]
name = "system-design"
title = "System design"
description = "One line, shown in `./study packs`."
levels = ["graduate", "mid", "senior", "lead", "staff"]
areas = ["caching", "storage", "consistency"]

[calibration.senior]
bar = "Tradeoff named and defended, a number attached, and a failure mode volunteered."
assume = "Has operated systems in production."
push_on = ["why, not what", "what breaks at 10x", "what it costs"]
avoid = "Do not accept a mechanism with no cost attached."

[[topic]]
id = "caching"
title = "Caching"
area = "caching"                 # must be in pack.areas
prefix = "ca"                    # seeds question ids: ca-001
levels = ["graduate", "mid", "senior", "lead", "staff"]
subtopics = ["read-strategies", "write-strategies", "eviction", "hot-key"]

[[problem]]
slug = "url-shortener"
title = "URL shortener"
areas = ["storage", "caching"]
levels = ["mid", "senior", "lead", "staff"]
minutes = 45                     # what the composer budgets for it
```

A calibration brief per level is optional but strongly recommended: without one the agent falls back on its own judgement, which drifts. `./study doctor --verbose` lists missing ones.

## Sub-topics

The atom of measurement, scheduling and reporting.

- **Four to seven per topic.** Fewer and the topic is too coarse to schedule usefully; more and each one is measured too rarely to mean anything.
- **Name them by what is known, not by section heading.** `stampede-penetration` is a facet you can be right or wrong about. `overview` is not.
- **They must be independently assessable.** If you cannot write a question that tests one without testing another, they are one facet.
- **Adding a sub-topic makes it appear as unmeasured**, so it shows up in everyone's queue immediately. Renaming one is a breaking change: the old name's history is orphaned. Prefer adding to renaming.

## Cards

Plain markdown, no frontmatter. Start with an H1 and a one-line summary. `./study card` prints the area and level range above it, from the manifest, so a card never states its own.

**Structure the body by sub-topic**, using the sub-topic id as a heading. That is what makes question fairness mechanical: a question is fair if the card carries its grounding, and with facet-shaped headings it is obvious whether it does.

```markdown
# Caching

**One line:** Keep a copy of expensive-to-fetch data somewhere faster.

## Why it exists
...

## read-strategies
...

## hot-key
...

## Numbers to know
| | |

## Related
- [consistent-hashing](consistent-hashing.md)
```

What makes a card good here, as opposed to a good article:

- **Written for retrieval, not reading.** Tables of contrasts, named failure modes, numbers with orders of magnitude. Prose that flows nicely is harder to be quizzed on.
- **State the tradeoff, not just the mechanism.** Every technique section should say what it costs and when it is wrong.
- **Include the numbers.** A card with no numbers cannot support a `numeric` question, and `numeric` is where hand-waving gets caught.
- **Name the conflations explicitly.** "These two get confused constantly; the axis that separates them is X" is the single highest-value sentence you can write, because it is what `discrimination` questions test.
- Links are relative markdown paths. No wiki-links, no vault, no plugins.

## Question banks

```toml
topic = "caching"

[[q]]
id = "ca-001"
qtype = "discrimination"
subtopic = "write-strategies"
levels = ["mid", "senior", "lead", "staff"]
q = "Cache-aside and write-back get confused constantly. What axis actually separates them?"
a = "They are on different axes entirely. Cache-aside is a READ strategy; write-back is a WRITE strategy. You can run cache-aside reads with write-back writes."
```

- `qtype` is one of `recall` `discrimination` `judgment` `diagnostic` `numeric`. See [question-types.md](question-types.md).
- `subtopic` must be declared by the topic. `doctor` catches it if not.
- `levels` defaults to the pack's levels if omitted. Be deliberate rather than relying on the default: every level named here is a pool the question has to earn its place in, and tagging a recall question up to `staff` inflates that pool's recall share while giving a staff candidate nothing. `doctor` reports the resulting mix per level.
- Ids are stable forever and never reused, because the ledger references them.
- Numeric tails, `ca-001`, belong to pack authors. Questions banked during a session get `ca-u<hash>`, derived from the question text, so a session can never mint an id a pack later wants and two machines that bank the same question offline agree on one id.
- **Exposure history is not stored here.** `shown` and `reps` are derived from the ledger.

**A stem has to stand on its own**: [question-types.md](question-types.md#stems-are-self-contained). The cheapest way to find one that does not is to answer it deliberately under the other reading and see whether the banked answer still applies.

Write the answer as what a **strong** answer contains, not as a minimal key. The agent scores against it and uses it to name the gap, so "Less, -2, because the floor on overshoot is one lease per node" beats "Less appropriate".

### Figures are derived, not asserted

A question that states a figure carries `derivation`: the arithmetic, one `name = expression` per step.

```toml
[[q]]
id = "cd-u25bb12fb"
qtype = "numeric"
q = "2M daily users make 40 API calls each. Origin is 140 ms RTT, TLS 1.3, no edge termination. How much of the day is pure connection setup?"
a = "80M requests. Each is cold: 3 x 140 = 420 ms, of which 280 ms is setup. Aggregate 22.4M seconds, about 260 human-days of waiting per day."
derivation = [
  "users = 2_000_000",
  "calls_per_user = 40",
  "requests = users * calls_per_user",
  "rtt_ms = 140",
  "setup_ms = 2 * rtt_ms",
  "aggregate_s = requests * setup_ms / 1000",
  "aggregate_days = aggregate_s / 86400",
]
```

`doctor` evaluates it and checks that every magnitude in `q` and `a` falls out of some step; `bank add` refuses a new question that states figures without one. A wrong figure scores the candidate against something that has no correct answer, and the ledger it lands in is append-only.

- Numbers, the operators `+ - * / // % **`, and `abs round min max log log2 log10 exp sqrt ceil floor`. Nothing else evaluates.
- Put the **inputs** in as well, not just the results. `rtt_ms = 140` is what lets the 140 ms in the stem be recognised.
- A figure may round to the precision it is written to, so `about 30x` accepts 29.33. Scientific notation with one significant figure, `1e-19`, claims an order of magnitude and nothing finer.
- Only magnitudes are checked: a unit, a scale word, a thousands separator, an exponent, `1 in 5`, or a value of 1000 or more. `TLS 1.3` and `the next 3 nodes` are counts and are left alone, so a figure hiding in a bare count is still yours to get right.
- Units are not converted. If the prose says both `280 ms` and `0.28 s`, derive both.

Deriving a figure a second way is the cheapest review there is. `./study bank check --json-text '{"questions": [...]}'` runs the same check and writes nothing, which is what to use **before** a question is asked rather than after.

## Problems

Two files, deliberately.

`prompt.md` is everything the candidate sees: a one-line ask, deliberately under-specified so they have to ask clarifying questions, and nothing else.

`notes.md` is never shown before an attempt. `./study problem <slug>` cannot return it; you need `--notes`. Include:

- **Hidden requirements**, functional and non-functional, that a good candidate extracts by asking.
- **Back-of-envelope numbers** they should reach, with the arithmetic.
- **Two or three deep-dive areas**, each with what to push on.
- **Strong-answer signals**: what separates a good answer from a correct one.
- **Common traps.**
- **Level calibration**, if the problem spans several levels and the bar differs meaningfully.
- **Follow-up questions.**

If a candidate can start designing without asking anything, the prompt has given away too much.

## Validating

```
./study doctor --verbose
```

Checks: cards exist, questions name declared sub-topics, ids are unique across the pack, problems have both files, areas are declared, every `derivation` evaluates and accounts for the figures quoted around it, and every ledger row still validates against the taxonomy. `--verbose` adds notes: topics with no card, missing calibration briefs, questions stating figures with no derivation, derivation steps nothing quotes, any topic with no questions at one of its declared levels, which is the usual authoring gap, and any level whose facet coverage or depth cannot supply the mix in [question-types.md](question-types.md#levels).

Then use it:

```
./study packs enable <your-pack>
./study plan 25m
```

The fastest way to find a weak card is to be quizzed on it. A question you cannot answer from the card is a card problem, not a question problem.
