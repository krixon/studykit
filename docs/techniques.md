# Technique menu

The blocks `./study plan` draws from. Each targets a specific failure, has a rough cost so a session can be built to fit a budget, and fires on a diagnosis rather than on preference. Warrants are in [research.md](research.md); selection is implemented in `studykit/select.py`.

| Block | Targets | Budget | Fires when |
|---|---|---:|---|
| **Quiz set** | retrieval, discrimination | 5-15m | anything is due |
| **Contrasting cases** | conflation | 10m | a confident-wrong (strength 2) is on record |
| **Estimation drill** | quantification | 5m | `numeric` scores lag the other types |
| **Diagnostic inversion** | symptom to cause | 10m | strength 3+, never tested backwards |
| **Teach-back** | illusion of explanatory depth | 12m | `predicted` runs more than 0.5 above `measured` |
| **Design critique** | evaluation | 18m | strength 3-4, applied work on a small budget |
| **Faded worked example** | rebuilding a weak facet | 25m | strength 1-2 |
| **Full problem** | far transfer, integration | 50m | several related facets at 4+, or an unattempted problem |
| **Cold re-attempt** | durability | 45m | a problem attempted two or more weeks ago and now due |
| **Card writing** | consolidation | 20m | a facet with no card, or a card a question exposed as thin |

## Notes on the less obvious ones

Each block's own instructions travel with it, in the `instruction` field `plan` returns.

**Contrasting cases.** Two or three things that share surface features and differ in deep structure, with the ask coming before any explanation. The direct remedy for a score-2 conflation, and better than a correction, because a correction addresses the wrong answer rather than the missing axis.

**Teach-back.** The user explains the concept as if to a competent engineer who has not met it. The gap between feeling able to explain something and actually explaining it is large and invisible from the inside. Cheap to run, brutal as a diagnostic, which is why the composer fires it on a calibration signal rather than on a strength signal.

**Design critique.** A deliberately flawed design, and what breaks in it. Evaluation is cheaper than generation for the same signal, so it fits budgets where a full problem does not.

**Faded worked example.** A complete worked design, then a variant with parts removed for the user to fill. Only for weak facets: worked examples help at low strength and actively hurt at high strength, so fade them out as strength rises.

**Full problem.** The only block that measures integration, and the only place the **transfer gap** can be observed: the difference between a facet's strength in isolation and its strength when it has to be recognised inside a larger problem. Worth the time cost for that alone, and the reason the composer will spend most of a 60-minute budget on one.

**Cold re-attempt.** The same problem, without showing the previous attempt first. Durability is a different property from performance, and it is the one that predicts whether the knowledge is there in three months.

## Budget composition

`./study plan <budget>` fills the box from the due queue, hardest-first, interleaved across topics and packs:

| Budget | Shape |
|---|---|
| 10m | one quiz set, 4-6 questions, mixed types, most-due facets |
| 25m | quiz set of 10-12, plus a targeted block chosen by the weakest facet |
| 45-60m | one full problem plus a short set, or three targeted blocks |
| half day | a problem, the blocks its gaps expose, and card writing |
| full day | two problems in different areas, consolidation, and a cold re-attempt |

Two minutes are always reserved at the end for recording.

The queue rotates through topics rather than exhausting one, so a 12-question set draws from up to 12 different topics.

## Overriding it

The composer is deterministic and you can argue with it:

```
./study plan 25m --no-problem       # never include a full problem
./study plan 25m --seed 7           # reproducible selection
./study questions --topic caching   # ignore the queue, drill one topic
./study problem <slug>              # a specific problem
```

Drilling one topic is blocked practice, which measures worse than it feels. It is the right call when you are learning something new and the wrong one when you are maintaining something known.
