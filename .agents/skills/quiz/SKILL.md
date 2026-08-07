---
name: quiz
description: Rapid-fire retrieval practice using the five question types (recall, discrimination, judgment, diagnostic, numeric). Use when the user wants quick low-typing questions rather than a full problem. Draws from the banked questions, interleaves topics without announcing them, and records a measurement per question.
---

# Quiz

Short questions, one-line answers, judgment weighted over recall.

## Select

```
./study questions --count 8
```

Returns questions already filtered to the user's level, drawn from the most-due and never-measured facets, and interleaved so consecutive questions come from different topics. Take them in the order given.

`author_for` in the response lists facets with no in-level question in the bank. Write one from the card (`./study card <topic>`), ask it, and bank it before the session ends.

**A question may only require what the pack carries** - what is on the card, or what follows from it by reasoning the card supports. A question outside the material measures nothing and scores an unfair 1. If a question is worth asking and the card lacks its grounding, the card is what needs fixing.

**Never say which topic a question is from.** Naming it pre-activates the schema and does half the retrieval.

Leave room for follow-ups: a set of 6 where two score 1-2 runs to 8. Plan the box accordingly rather than skipping the re-tests.

## Run

One at a time, unless the user prefers batches.

1. Ask the question.
2. Take a **predicted** confidence 1-5 first, if they engage with it. One keystroke. Skip silently if they do not; never nag. If they did not give one, the field is absent - do not invent it.
3. Take the answer. **Stop the turn after asking.** Never write the candidate's answer, and never continue past a question into the response to it. If the turn ends with a question, that is the whole turn.
4. Score it cold, **before teaching anything**. A confident wrong answer is a **2**, not a 3, because conflation will not self-correct.
5. Follow the ladder below. It is the protocol, not a suggestion.

| Cold score | What follows |
|---:|---|
| 4-5 | One line. Confirm, or name the boundary they did not volunteer. Next question. |
| 3 | Name the specific gap. Next question. |
| 1-2 | **Worked example**, then a variant re-test later in the set. |

Judge against the level's bar, which `./study plan` returns in its `calibration` block and `./study levels` prints on demand.

## Never score an answer that was not given

A question with no answer from the candidate has no score, and no ledger row. Not a 1, not an omitted `measured` with the row kept: no row at all. A fabricated turn scored as though it were real corrupts the ledger, which is append-only, and it is worse than a missed measurement because it looks like data.

If you find you have scored an answer the candidate did not write, say so plainly, drop the row, and re-ask the question cold. Do not reconstruct what they "would have" said.

## The 1-2 branch

A 1-2 means there was nothing to generate from, so correction alone will not land. Reading a good explanation produces fluency that feels like learning and is not.

- **Teach with a worked example** - the reasoning executed on a concrete case, with the numbers, not a restatement of the principle.
- **Re-test on a variant.** Same facet, different case. Never the question just asked: recognition lets an answer be confirmed without retrieving anything.
- **Space it.** At least two other questions between the teaching and the re-test.
- Record the variant score as `post` on that row. `post` never schedules; `measured` stays the cold number.
- Bank the variant like any other shown question.

If `post` comes back 1-2 as well, say so plainly and flag the facet for a dedicated teaching session. That is a signal about the explanation or the missing groundwork, not about effort.

## Record

Bank first (ids must exist before they can be referenced), then record.

```
./study bank add --json-text '{"pack":"system-design","topic":"caching","questions":[
  {"subtopic":"hot-key","qtype":"judgment","q":"...","a":"..."}
]}'

./study record --json-text '{"session":"quiz","pack":"system-design","rows":[
  {"topic":"caching","subtopic":"hot-key","qtype":"judgment","qid":"ca-014","measured":2,"predicted":4,
   "post":4,"taught":true}
]}'
```

Row order does not matter - several measurements of one facet on one date collapse to their mean and count as one rep, which is what the model intends.

`record` rebuilds state and metrics. Nothing else to run.
