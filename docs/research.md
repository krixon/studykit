# Evidence base

Why the engine works the way it does. Each finding is recorded with the mechanism it licenses, so a design decision can be traced to its warrant and challenged on the evidence rather than on taste.

A finding earns a place here only if it changes what the engine does. Interesting-but-inert research is not listed.

## Retrieval before instruction

**Finding.** Attempting retrieval and failing, before being taught, improves later retention over studying the material directly. Richland, Kornell & Kao (2009) named this the pretesting effect; it sits inside Bjork's desirable difficulties (1994) and the wider testing effect (Roediger & Karpicke 2006).

**What it licenses.** Cold measurement always comes first. `measured` is the pre-teaching score and is the only field that schedules. No session teaches before it tests.

**The boundary that is easy to drop.** In these studies instruction *immediately follows* the pretest. The failed attempt is a primer for a lesson, not a substitute for one. A pretest with no real instruction behind it is just an unanswered question.

## Prior knowledge gates unguided struggle

**Finding.** Two literatures point opposite ways and the disagreement is real. Kapur's productive failure work (2008; Kapur & Bielaczyc 2012) shows learners who attempt problems before instruction outperform those taught first, on transfer especially. Kirschner, Sweller & Clark (2006) argue minimal guidance imposes extraneous cognitive load on novices and loses to worked examples.

The condition that separates them is prior knowledge. Kapur is explicit that productive failure needs learners to hold the requisite prior knowledge resources to generate candidate representations. With nothing to generate from, failure is not productive, it is only failure.

**What it licenses.** The cold attempt is never skipped, but what follows it scales with how badly it went. A score of 1-2 signals there was nothing to generate from, and triggers a worked example rather than a paragraph of correction. See the follow-up ladder in [scoring.md](scoring.md).

**It also licenses levels.** The same question is a desirable difficulty for a senior engineer and an impossible one for a graduate. Filtering the bank by level is this finding applied to content selection rather than to feedback.

## Worked examples reverse with expertise

**Finding.** Worked examples beat unguided problem solving for novices (Sweller & Cooper 1985) and actively harm performance once the learner has the schema, because processing the redundant guidance costs working memory. Kalyuga, Ayres, Chandler & Sweller (2003), the expertise reversal effect.

**What it licenses.** Technique is selected by strength, not by preference. Faded worked examples at 1-2, judgment and diagnostic work at 4-5. Fade the guidance as strength rises rather than teaching the same way at every level. It is also why the ladder tells the agent to say **one line** at 4-5 rather than confirming at length.

## Feedback needs a second retrieval

**Finding.** Corrective feedback after a failed attempt helps, and helps substantially more when the learner then retrieves the corrected answer themselves rather than only reading it. Repeated retrieval with feedback outperforms feedback alone across the testing-effect literature (Butler, Karpicke & Roediger 2008; Pashler et al. 2005).

**What it licenses.** A 1-2 gets re-tested on a **variant** later in the same session, recorded as `post`. Reading a good explanation produces fluency that feels like learning; only the second retrieval shows whether anything was encoded.

The re-test must be a variant, never the same question. Recognition lets a learner confirm "I knew that" without retrieving anything.

## Interleaving and spacing

**Finding.** Interleaved practice beats blocked practice for both retention and problem-solving, and it is specifically what builds the ability to discriminate which concept applies (Rohrer & Taylor 2007; Rohrer, Dedrick & Stershic 2015). Distributed practice beats massed practice, with the optimal gap scaling to the retention interval (Cepeda et al. 2006).

**What it licenses.** Sessions mix topics and never announce which topic a question is from. The queue builder deliberately rotates through topics rather than exhausting one, so that interleaving has something to interleave. Scheduling is expanding-interval, driven by `measured` alone.

## Fluency is not learning

**Finding.** Learners under active methods judge that they have learned less while measurably learning more (Deslauriers et al. 2019). Separately, people substantially overestimate their ability to explain mechanisms until asked to actually do it — the illusion of explanatory depth (Rozenblit & Keil 2002).

**What it licenses.** Self-report never touches scheduling. `predicted` is captured only to compute calibration error. Teach-back exists in [techniques.md](techniques.md) because the gap between feeling able to explain and explaining is invisible from the inside, and the composer fires it specifically when predicted is running above measured.

## Recognition impedes transfer

**Finding.** The failure mode at this level is not absent knowledge but unrecognised applicability — the inert knowledge problem. Multiple choice permits confirmation without retrieval.

**What it licenses.** Free recall by default. Multiple choice only where discriminating the named alternatives is itself the skill. See [question-types.md](question-types.md).

## Contested

Recorded so the engine does not present a live dispute as settled.

- **Does retrieval practice produce far transfer?** [question-types.md](question-types.md) asserts it reliably produces near transfer and often fails at far transfer. That is roughly Van Gog & Sweller's (2015) position, that the testing effect shrinks as element interactivity rises; Karpicke & Aue (2015) rebutted it. The engine hedges by weighting the bank towards `judgment` and by treating full problems as the only integration measure, which is defensible under either reading.

- **Productive failure versus direct instruction.** Genuinely unresolved. The prior-knowledge boundary above is where the two camps come closest, not a proven constant. Effect sizes vary with domain and with how structured the failure phase is.

- **Optimal spacing intervals.** The SM-2 style multipliers in [scoring.md](scoring.md) are conventional, not derived from this literature. Cepeda et al. support expanding intervals scaled to the retention interval; the specific numbers (1.6 / 2.2 / 3.0) are a guess and should be treated as one. If you have data, change them in `studykit/schedule.py` — they are three constants in one dictionary.

## Where this shows up

| Mechanism | Implemented in | Documented in |
|---|---|---|
| Cold-first, three constructs never merged | `studykit/ledger.py` | [scoring.md](scoring.md) |
| Interval, reps cap, session-mean collapse | `studykit/schedule.py` | [scoring.md](scoring.md) |
| Interleaving, technique by strength, budget composition | `studykit/select.py` | [techniques.md](techniques.md) |
| Follow-up ladder, `post` semantics | the skills | [scoring.md](scoring.md) |
| Question types, free-recall default | pack question banks | [question-types.md](question-types.md) |
| Prior knowledge gating content | `levels` in `pack.toml` | [levels.md](levels.md) |
