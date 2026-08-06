# Question types

Five types. Every banked question declares one. Scoring by type is what separates "does not know it" from "cannot apply it", which need opposite remedies.

## Why not just recall

Retrieval practice reliably produces near transfer and repeatedly fails to produce far transfer on complex problem-solving. The failure has a name, the **inert knowledge problem**: holding the knowledge but not recognising that a situation calls for it. That is the actual failure mode past a junior level, so recall is the floor of this system, not its substance.

## The ladder

### `recall` — what is it

Straight retrieval. One line.

> What is the boundary defect in a fixed-window counter?

The floor. Cheap to author, cheap to answer, weakest signal. Necessary at graduate level, where the vocabulary is still being built, and close to worthless on its own at staff.

### `discrimination` — which is it, and what separates them

Two or more confusable things; name the axis.

> Cache-aside and write-back get confused constantly. What axis actually separates them?

Detects **conflation**, which recall cannot. Conflation produces confident wrong answers, so it scores 2 and is the highest-value thing to catch. Author these as contrasting pairs that share surface features and differ in deep structure.

### `judgment` — does this change the answer

A design context, then new information. Does an option become more or less appropriate?

> You are leasing rate-limit tokens locally across 500 nodes. New information: this tenant's limit is 10 per minute. Does local leasing become more or less appropriate?

Answered as `-2 -1 0 +1 +2` plus a clause of why. Near-zero typing for a genuinely hard question.

Adapted from script concordance testing in medical education, which exists to assess reasoning under uncertainty rather than knowledge. Swap diagnosis for design option and it transfers directly. **This is the type that targets far transfer**; weight the bank towards it.

A good judgment question has a defensible answer that is not obvious, and sometimes the honest answer is 0 — "it depends, and here is what on". Questions where the new information trivially settles it are recall in disguise.

### `diagnostic` — symptom to cause

Give the observation, ask for the mechanism.

> p99 tripled, error rate flat, cache hit rate unchanged. Most likely cause?

Reverses the direction of reasoning. Forward design and backward diagnosis are different skills, and both show up in real work and in interviews.

### `numeric` — put a number on it

> 500 nodes, 10-token leases, a limit of 1,000,000. Overshoot as a percentage?

One number, no prose. Targets the common habit of correct reasoning with the arithmetic left implicit. The answer should include the working, so a wrong number can be diagnosed as an arithmetic slip or a modelling error.

## Multiple choice

Use sparingly, and only where **the distractors are the content** — picking between five named consistency models, say, because discriminating the alternatives is itself the skill. Everywhere else use free recall: recognition lets you confirm "I knew that" without ever retrieving, and recognition is theorised as the main thing impeding transfer.

## Levels

Every question declares which levels it suits:

```toml
levels = ["senior", "lead", "staff"]
```

The type ladder and the level ladder are correlated but not the same. A graduate-appropriate `judgment` question exists — it just has a smaller design context and a clearer answer. A staff-level `recall` question exists too, and is usually a waste of a slot.

As a rough guide to bank composition per level:

| Level | recall | discrimination | judgment | diagnostic | numeric |
|---|---:|---:|---:|---:|---:|
| graduate | 40% | 30% | 15% | 10% | 5% |
| mid | 25% | 30% | 25% | 10% | 10% |
| senior+ | 10% | 25% | 35% | 15% | 15% |

These are targets for authoring, not enforced by code. `./study progress` shows your actual measured mean per type, which is the number that matters: a high `recall` with a low `judgment` means the knowledge is there and inert.

## Interleave, and do not announce the topic

Mix topics within a set and never say which card a question came from. Naming the topic pre-activates the schema and does half the retrieval for the candidate. Interleaved practice beats blocked for both retention and problem-solving, and it is specifically what builds discrimination, because it forces identifying *which* concept applies before applying it.

`./study questions` already interleaves the set it returns. Do not reorder it into topic groups.

## Bank format

One `[[q]]` table per question, in `packs/<pack>/questions/<topic>.toml`:

```toml
[[q]]
id = "rl-006"
qtype = "judgment"
subtopic = "distributed-state"
levels = ["senior", "lead", "staff"]
q = "You are leasing rate-limit tokens locally across 500 nodes. New information - this tenant's limit is 10 per minute. Does local leasing become more or less appropriate?"
a = "Much less, -2. The floor on overshoot is roughly one lease per node, so 500 nodes against a limit of 10 is a 5000 percent overshoot. Overshoot has to be judged against the limit, not in absolute terms."
```

Rules:

- `id` is `<topic-prefix>-<nnn>`, stable forever, **never reused**. `./study bank add` assigns them; do not hand-write them.
- **Anything shown is banked.** Generated a question mid-session? `./study bank add` before the session ends. Not optional — an unbanked question cannot be referenced by a ledger row, and the CLI enforces that.
- Exposure history (`shown`, `reps`) is **not** stored on the question. It is derived from the ledger, so packs stay pristine and portable and can be shared without carrying anyone's history.
- Never show the same question twice in one session. `./study questions` handles this; it also prefers unshown or long-unseen items.
