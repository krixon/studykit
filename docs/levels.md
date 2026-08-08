# Levels

`graduate` · `mid` · `senior` · `lead` · `staff`

One setting, three effects.

## What your level changes

**1. Which questions you are asked.** Every question declares the levels it suits. `./study questions` and `./study plan` only draw from questions that include yours.

**2. Which topics and problems are in scope.** A topic declares its levels too. `consistency-models` starts at senior; `multi-region-checkout` starts at lead. Out-of-scope topics do not appear in your queue, your coverage percentage or your gaps.

**3. The bar you are judged against.** Each pack declares a **calibration brief** per level: the bar an answer must clear, what to assume the person already knows, what to push on, and what not to demand. `./study plan` returns it.

The 1-5 scale does not change. A 4 always means "correct with the tradeoff named". What changes is what counts as the tradeoff, and how much is expected unprompted.

## Seeing the briefs

```
./study levels
```

Prints every level's bar for each enabled pack, with the `assume`, `push_on` and `avoid` that go with it. `avoid` is what stops a graduate being marked down for not producing a cost model.

## Changing it

```
./study config set level lead
```

State and metrics rebuild on the spot. The ledger is untouched, and rows record the level they were taken at, so history stays interpretable after a change.

Moving up:

- **Coverage drops**, because topics that were out of scope are now in it.
- **Existing strengths do not change**, because they are measurements, not judgements. A facet measured at 4 as a senior still reads 4 as a lead, and the next measurement at the new bar is what moves it.

Moving down does the reverse. Out-of-scope measurements stay in the ledger.

## Choosing one

Pick the level you are being **assessed** at, not the one you are comfortable at. Preparing for an interview, use the level of the role; maintaining knowledge for your current job, use your current level.

One level above yours is harsh and works. One level below is comfortable and will not move anything.

## Authoring for levels

The TOML is in [authoring-packs.md](authoring-packs.md#packtoml).

- **Tag generously downwards for mechanism questions and narrowly upwards for judgment ones.** "What does a load balancer do" suits everyone; "does this change the answer, given 500 nodes" does not suit a graduate, who has no basis to judge it.
- **A topic's lowest level should be the level at which its *simplest* facet is fair**, since question tags do the finer filtering.
- **`avoid` matters more than `bar`.** Stating what not to demand is what makes the lower levels usable.
- `./study doctor --verbose` lists any topic with no questions at one of its declared levels.
