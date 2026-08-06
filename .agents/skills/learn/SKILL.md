---
name: learn
description: Teach a topic properly, cold-test first. Use when the user asks to learn or be taught something ("teach me consistent hashing", "I don't know anything about CAP"), or when a quiz exposed a facet that stayed weak after a worked example. Tests before teaching, teaches to the gap, then re-tests on variants.
---

# Learn

For when the answer is genuinely not there yet. Every other session type assumes something to retrieve; this one builds it.

**It still tests first.** Attempting and failing before instruction beats studying the material directly, and the failed attempt is the honest score anyway. See `docs/research.md`, retrieval before instruction.

## Setup

```
./study card <topic> --pack <pack>       # the material
./study queue --json                     # which facets are weak or unmeasured
```

If the user named a topic, use it. If they did not, pick the weakest facet from the queue.

Confirm the topic is in scope for their level (`./study packs`). Teaching a staff-level topic to someone configured as a graduate is usually the wrong session; say so and offer the prerequisite instead.

## Run

**1. Cold probe, per facet.** Two or three questions across the topic's facets, scored before you teach anything. Keep it short - this is a diagnosis, not a quiz. Take a `predicted` if offered.

**2. Teach to the diagnosis, not to the card.** The ladder applies here too:

| Cold score | What that facet needs |
|---:|---|
| 4-5 | Nothing. Say so and move on - guidance at this level costs working memory and returns nothing. |
| 3 | The specific missing piece. One or two sentences. |
| 1-2 | A **worked example**: the reasoning executed on a concrete case, with numbers. Then a faded version where they fill in the steps. |

Do not read the card aloud. Use its structure - the facets are the sections - and teach the parts that came back weak.

**3. Contrasting cases** where the failure was a conflation. Present two or three things that share surface features and differ in deep structure, and ask what separates them **before** explaining. This is the direct remedy for a score-2 confident-wrong answer, and it works better than a correction.

**4. Re-test on variants.** Different cases, same facets, spaced from the teaching by other work. Record these as `post`.

## Record

```
./study bank add --json-text '{"pack":"...","topic":"...","questions":[ ... ]}'

./study record --json-text '{"session":"learn","pack":"system-design","rows":[
  {"topic":"consistent-hashing","subtopic":"virtual-nodes","measured":1,"post":3,"taught":true}
]}'
```

- `measured` is the **cold** score, always, and is the only field that schedules.
- `post` is the variant re-test. It never schedules. It is a diagnostic of the teaching, not of the learner: a 2 that stays 2 means the explanation missed or the groundwork is absent, and it should be said plainly.
- Bank every question shown, including the variants.

## Afterwards

A facet taught today is not learned today. Say when it comes back up (`./study status`) and resist the urge to mark it as done - the next cold retrieval is the only thing that will tell you whether it stuck.
