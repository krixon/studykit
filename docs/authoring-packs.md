# Authoring a pack

A pack is content. It declares what there is to learn and says nothing about scheduling, scoring or session structure. The engine owns those, so a pack is portable and can be shared without carrying anyone's history.

## Layout

```
packs/<name>/
  pack.toml                    manifest: levels, areas, topics, problems, calibration
  cards/<topic>.md             one knowledge card per topic
  questions/<topic>.toml       one question bank per topic
  problems/<slug>/prompt.md    candidate-facing ask
  problems/<slug>/notes.md     interviewer notes, never shown before an attempt
```

The filename conventions are load-bearing: `cards/<topic id>.md` and `questions/<topic id>.toml` are found by the topic's id, not by anything in the manifest.

Drop a directory into `packs/` and it is available. `./study config set packs a,b` chooses which are in rotation.

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

## Sub-topics are the unit of everything

Sub-topics are the atom of measurement, scheduling and reporting. Get them right and everything else follows.

- **Four to seven per topic.** Fewer and the topic is too coarse to schedule usefully; more and each one is measured too rarely to mean anything.
- **Name them by what is known, not by section heading.** `stampede-penetration` is a facet you can be right or wrong about. `overview` is not.
- **They must be independently assessable.** If you cannot write a question that tests one without testing another, they are one facet.
- **Adding a sub-topic makes it appear as unmeasured**, so the addition immediately shows up in everyone's queue. That is intended, and it is why renaming one is a breaking change: the old name's history is orphaned. Choose carefully, and prefer adding to renaming.

## Cards

Plain markdown, no frontmatter. Start with an H1 and a one-line summary.

**Structure the body by sub-topic**, using the sub-topic id as a heading. That is what makes question fairness mechanical: a question is fair if the card carries its grounding, and with facet-shaped headings it is obvious whether it does.

```markdown
# Caching

**Area:** caching · **Levels:** graduate → staff+

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
- `levels` defaults to the pack's levels if omitted. Be deliberate rather than relying on the default.
- Ids are stable forever and never reused, because the ledger references them.
- **Exposure history is not stored here.** `shown` and `reps` are derived from the ledger, so a pack can be shared without carrying anyone's history.

Weight the bank towards `judgment` and `discrimination`. `recall` is the floor, not the point.

Write the answer as what a **strong** answer contains, not as a minimal key. The agent scores against it and uses it to name the gap, so "Less, -2, because the floor on overshoot is one lease per node" is far more useful than "Less appropriate".

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

A good prompt is under-specified on purpose. If a candidate can start designing without asking anything, the prompt has given away too much.

## Validating

```
./study doctor --verbose
```

Checks: cards exist, questions name declared sub-topics, ids are unique across the pack, problems have both files, areas are declared, and every ledger row still validates against the taxonomy. `--verbose` adds notes: topics with no card, missing calibration briefs, and any topic with no questions at one of its declared levels, which is the usual authoring gap.

Then use it:

```
./study config set packs <your-pack>
./study plan 25m
```

The fastest way to find a weak card is to be quizzed on it. A question you cannot answer from the card is a card problem, not a question problem.
