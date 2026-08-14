# Levels

`graduate` · `mid` · `senior` · `lead` · `staff`

One setting, three effects.

## What your level changes

**1. What mix of question types you get.** Your level sets the target mix in [question-types.md](question-types.md#levels): a graduate draw leans on recall and discrimination, a senior draw on judgment. It is a starting point, not a rule. Every measurement you record moves it, so a type you answer well loses share and a weak one gains it, and after enough sessions the mix reflects you rather than your level. `PRIOR_STRENGTH` in `studykit/select.py` sets how much evidence that takes.

A question's own `levels` is a preference inside that mix, not a gate. Questions written for your level come first; once you have seen them, the rest of an in-scope topic is reachable. Nothing is withheld because it was tagged for someone else, so a thin pool at your level degrades to harder or easier questions rather than to no questions.

**2. Which topics and problems are in scope.** A topic declares its levels too, and this one *is* a hard filter. `consistency-models` starts at senior; `multi-region-checkout` starts at lead. Out-of-scope topics do not appear in your queue, your coverage percentage or your gaps. Scope is about relevance rather than difficulty: a graduate is not asked about multi-region failover at all, whereas a graduate-tagged question is only ever deprioritised.

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

- **Tag a question for the levels it was written for, not the levels it is survivable at.** "What does a load balancer do" is a graduate question that a staff engineer can answer, so it is a graduate question. Tagging it up to `staff` no longer withholds it from anyone, it just competes for a staff slot it does not deserve.
- **A topic's lowest level is the level at which its *simplest* facet is fair.** This is the tag that decides whether the topic exists for someone, so it is the consequential one.
- **`avoid` matters more than `bar`.** Stating what not to demand is what makes the lower levels usable.
- **Author to the mix per level, not per pack.** A pack can sit on target overall while its graduate pool is nearly all recall. `./study doctor --verbose` reports the mix and the depth for each level, plus any topic with no questions at one of its declared levels.
