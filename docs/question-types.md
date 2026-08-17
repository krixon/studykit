# Question types

Five types. Every banked question declares one. Scoring by type is what separates "does not know it" from "cannot apply it", which need opposite remedies.

## Why not just recall

Retrieval practice reliably produces near transfer and repeatedly fails to produce far transfer on complex problem-solving. The failure has a name, the **inert knowledge problem**: holding the knowledge but not recognising that a situation calls for it. That is the actual failure mode past a junior level, so recall is the floor of this system, not its substance.

## The ladder

### `recall`: what is it

Straight retrieval. One line.

> What is the boundary defect in a fixed-window counter?

The floor. Cheap to author, cheap to answer, weakest signal. Necessary at graduate level, where the vocabulary is still being built, and close to worthless at staff.

### `discrimination`: which is it, and what separates them

Two or more confusable things; name the axis.

> Cache-aside and write-back get confused constantly. What axis actually separates them?

Detects **conflation**, which recall cannot. Conflation produces confident wrong answers, so it scores 2 and is the highest-value thing to catch. Author these as contrasting pairs that share surface features and differ in deep structure.

### `judgment`: does this change the answer

A design context, then new information. Does an option become more or less appropriate?

> You are leasing rate-limit tokens locally across 500 nodes. New information: this tenant's limit is 10 per minute. Does local leasing become more or less appropriate?

Answered as `-2 -1 0 +1 +2` plus a clause of why. Near-zero typing for a genuinely hard question.

End with "More or less appropriate?" or whichever variant fits, so the candidate knows whether you want the rating, the remedy, or both. See [The ask](#the-ask).

Adapted from script concordance testing in medical education, which assesses reasoning under uncertainty rather than knowledge. **This is the type that targets far transfer.**

A good judgment question has a defensible answer that is not obvious, and sometimes the honest answer is 0: "it depends, and here is what on". Questions where the new information trivially settles it are recall in disguise.

### `diagnostic`: symptom to cause

Give the observation, ask for the mechanism.

> p99 tripled, error rate flat, cache hit rate unchanged. Most likely cause?

Reverses the direction of reasoning. Forward design and backward diagnosis are different skills, and both show up in real work and in interviews.

### `numeric`: put a number on it

> 500 nodes, 10-token leases, a limit of 1,000,000. Overshoot as a percentage?

One number, no prose. Targets the common habit of correct reasoning with the arithmetic left implicit. The answer should include the working, so a wrong number can be diagnosed as an arithmetic slip or a modelling error.

## The ask

**The stem ends with the ask, and the ask names what it wants.** The type is not visible to whoever answers it, so the wording is the only thing telling them which of several reasonable questions is being put. An answer graded against an ask the stem did not make measures nothing, and it scores the candidate for reading the question as written.

The phrasings are not interchangeable:

| What you want | The ask | Type |
|---|---|---|
| the axis between confusable things | "what separates them?" | `discrimination` |
| the cause behind a symptom | "most likely cause?" | `diagnostic` |
| a test that tells two candidate causes apart | "what would you check to tell which?" | `diagnostic` |
| whether new information moves a decision | "more or less appropriate?" | `judgment` |
| a figure, with the working | "how much, and what is that in ...?" | `numeric` |

**"What separates them" belongs to `discrimination`.** A `diagnostic` that offers two candidate causes and wants a distinguishing test has to say so. Asked as "what separates them", the correct answer is the conceptual difference between the two, which is a different question with a different answer, and the one the phrasing promised.

Where a stem lists candidates, say what they are candidates for. "Two candidates" on its own reads as two scenarios to consider.

## Multiple choice

Use sparingly, and only where **the distractors are the content**: picking between five named consistency models, say, because discriminating the alternatives is itself the skill. Everywhere else use free recall: recognition lets you confirm "I knew that" without ever retrieving, and recognition is theorised as the main thing impeding transfer.

## Levels

Every question declares which levels it suits:

```toml
levels = ["senior", "lead", "staff"]
```

The type ladder and the level ladder are correlated but not the same. A graduate-appropriate `judgment` question exists; it just has a smaller design context and a clearer answer. A staff-level `recall` question exists too, and is usually a waste of a slot.

Bank composition per level:

| Level | recall | discrimination | judgment | diagnostic | numeric |
|---|---:|---:|---:|---:|---:|
| graduate | 40% | 30% | 15% | 10% | 5% |
| mid | 25% | 30% | 25% | 10% | 10% |
| senior+ | 10% | 25% | 35% | 15% | 15% |

`studykit/balance.py` holds these numbers, `select.qtype_weights` draws to them, and `./study doctor --verbose` reports a level that cannot supply them. Change them in one place or the other and the three disagree.

**The unit is the level, not the pack.** A question declares the levels it suits, so one bank holds a different drawable pool per level, each with its own row above. A pack can sit on target in aggregate while its graduate pool is 90% recall. Authoring against the aggregate is what produces that.

**Author for coverage, not for share.** A draw walks the due facets and asks each one for a question of the type the mix wants, so what caps a type is the proportion of facets that hold one at all. Twenty judgment questions on one facet raise the pool's share and change nothing a draw can use. Nor is a surplus a defect: `qtype_weights` sets the share, so extra recall is drawn less often rather than crowding anything out. The number to move is how many facets have one of each type.

`senior+` is one row because above mid the intended mix does not change. What separates senior from staff is the calibration brief, not the question.

`./study progress` shows your measured mean per type: a high `recall` with a low `judgment` means the knowledge is there and inert.

## Stems are self-contained

The topic is never named when a question is asked. Warrant: [research.md](research.md), interleaving and spacing.

Everything needed to fix the frame therefore has to be in the stem, written as scenario rather than as a label.

> What should an error response contain besides a status code?

Unanswerable. HTTP mandates nothing beyond the status code, so a candidate reading this as a protocol question is right to say "nothing", and a candidate reading it as a design question answers something else entirely. The two readings do not overlap.

> You are designing a JSON API. A mobile client calls it, a third-party integrator also calls it, and your support team fields tickets about it. A request fails. Beyond the status code, what goes in the response body?

Same knowledge tested, frame fixed, and nothing pre-activated. "This is an API design question" would also fix the frame, but it names the topic and hands over half the retrieval.

A `judgment` stem carrying a time constraint has a second frame to fix: **design or lever**. "Prices must be visible within 60 seconds" reads as a standing requirement to one candidate and as an incident to another, and the right answers are disjoint - restructure what is cached, versus fire the purge and accept the herd. Say which you are asking for.

The test: if a stem needs a topic label to be answerable, it is missing a sentence.
