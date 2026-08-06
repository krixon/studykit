# Levels

`graduate` · `mid` · `senior` · `lead` · `staff`

One setting, three effects.

## What your level changes

**1. Which questions you are asked.** Every question declares the levels it suits. `./study questions` and `./study plan` only draw from questions that include yours.

**2. Which topics and problems are in scope.** A topic declares its levels too. `consistency-models` starts at senior; `multi-region-checkout` starts at lead. Out-of-scope topics do not appear in your queue, are not counted in your coverage percentage, and are not reported as gaps — so a graduate is not told they have 84 unmeasured facets, most of which they should not be studying yet.

**3. The bar you are judged against.** Each pack declares a **calibration brief** per level: the bar an answer must clear, what to assume the person already knows, what to push on, and what not to demand. `./study plan` returns it, and the skills instruct the agent to apply it.

The 1-5 score scale itself does **not** change. A 4 always means "correct with the tradeoff named". What changes is what counts as the tradeoff, and how much is expected unprompted.

## Seeing the briefs

```
./study levels
```

Prints every level's bar for each enabled pack. Abbreviated, for system-design:

| Level | Bar |
|---|---|
| graduate | Names the component, says what problem it solves, draws a sensible box diagram. Getting the mechanism right is the whole job. |
| mid | Correct mechanism plus the main tradeoff, and a rough sense of scale. |
| senior | Tradeoff named and defended, a number attached, and a failure mode volunteered without being asked. |
| lead | Everything at senior, plus the migration path and the operational burden the team inherits. |
| staff | Correct, quantified, with a failure mode and a blast radius, and an explicit statement of what the design forecloses. |

Each brief also carries `assume`, `push_on` and `avoid`. The `avoid` field is the one that does the most work: it is what stops a graduate being marked down for not producing a cost model.

## Changing it

```
./study config set level lead
```

Takes effect immediately — state and metrics are rebuilt on the spot. Your ledger is untouched, so nothing is lost and nothing is re-scored. Rows record the level they were taken at, so history stays interpretable after a change.

Two things to expect when you move up:

- **Coverage drops**, because topics that were out of scope are now in it. That is the point.
- **Your existing strengths do not change**, because they are measurements, not judgements. A facet measured at 4 as a senior still reads 4 as a lead, and the next measurement at the new bar is what will move it.

Moving down does the reverse, and out-of-scope measurements stay in the ledger rather than being deleted.

## Choosing one

Pick the level you are being **assessed** at, not the one you are comfortable at. If you are preparing for an interview, use the level of the role. If you are maintaining knowledge for your current job, use your current level.

Working one level above yours deliberately is a legitimate and demanding way to use this, and the calibration brief will be harsh. Working one level below is comfortable and will not move anything.

## Authoring for levels

In a pack:

```toml
[calibration.senior]
bar = "Tradeoff named and defended, a number attached, and a failure mode volunteered."
assume = "Has operated systems in production."
push_on = ["why, not what", "what breaks at 10x", "what it costs"]
avoid = "Do not accept a mechanism with no cost attached."

[[topic]]
id = "consistency-models"
levels = ["senior", "lead", "staff"]

[[q]]
levels = ["mid", "senior", "lead", "staff"]
```

Guidance that has held up while writing the shipped packs:

- **Tag generously downwards for mechanism questions and narrowly upwards for judgment ones.** "What does a load balancer do" suits everyone; "does this change the answer, given 500 nodes" does not suit a graduate, who has no basis to judge it.
- **A topic's lowest level should be the level at which its *simplest* facet is fair**, since question tags do the finer filtering.
- **`avoid` matters more than `bar`.** Stating what not to demand is what makes the lower levels usable, and it is the field authors most often skip.
- `./study doctor --verbose` lists any topic with no questions at one of its declared levels, which is the usual authoring gap.
