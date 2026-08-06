# Refactor a god class - interviewer notes

**Do not reveal any of this before the attempt.**

The technical content is easy; almost everyone can name the seams. What separates answers is **sequencing and safety** - whether they plan a refactor that can be stopped at any point, and whether they ask why it is being done at all.

## Hidden context

Wait for them to ask.

- Test coverage on this class is about 15%, all of it on the pricing logic.
- It changes roughly weekly, usually for discount rules.
- Two other services call it directly and one imports its internal types.
- Nobody has been able to test the charging path without hitting the payment sandbox.
- There is no specific business driver - a new engineer proposed it after a bad week.

That last point is deliberate. **A strong answer asks what the refactor is for.** "It's ugly" is not a plan; "discount rules change weekly and every change risks the payment path" is.

## The questions they should ask

- **Why now, and what change is it blocking?** The answer determines which seam to cut first.
- **What tests exist?** Decides whether step one is refactoring or characterisation testing.
- **Who else depends on it, and on what?** A public surface constrains what can move.
- **Can it be done incrementally, and can it be abandoned halfway?** A refactor that must complete to be valuable will not survive a competing priority.

## The seams

The class mixes at least five kinds of thing, and the split is not the interesting part:

- **Validation** — pure, easy to extract, high test value per unit of effort.
- **Pricing and discounts** — pure domain logic, changes weekly, and the actual prize.
- **Payment** — an external boundary, wants an adapter behind an interface the domain owns.
- **Persistence** — a repository behind an interface.
- **Notification and analytics** — side effects that should leave the write path, probably as events.

The shape they should converge on: extract the pure domain logic first, because it needs no test infrastructure and cannot break anything at the edges; then put interfaces in front of the external dependencies; then move side effects off the critical path.

## Deep dives (pick two)

1. **Order of operations.** Characterisation tests around the current behaviour first, then the easiest pure extraction, then the boundaries. Push on *why pure logic first*: it is testable with no infrastructure, so it converts the untestable class into a small untestable shell around a well-tested core, and every later step gets safer.
2. **Working without tests.** The seam problem - you cannot test the charging path without a payment call, and you cannot extract it safely without a test. Resolution: introduce the interface and inject it, which is a mechanical change small enough to review by eye, and *then* write the test. Accepting one carefully-reviewed unsafe step to enable all later steps is a legitimate and mature answer.
3. **Not breaking callers.** Keep `OrderService` as a facade delegating to the new pieces, so external callers see no change. Then migrate them one at a time, then delete the facade. Push on the one that imports internal types - that caller has to change first, or a boundary has to be drawn around it.
4. **Stopping halfway.** Every step should leave the codebase better than before it. If the plan only pays off at the end, it will be abandoned at 60% and leave two half-designs, which is worse than either.

## Strong-answer signals

- Asks what the refactor is for before proposing anything.
- Characterisation tests before structural change.
- Extracts pure logic before touching boundaries.
- Keeps the old class as a facade so callers are unaffected.
- Small commits, each independently shippable.
- Explicitly says what they would **not** extract, and why 2,400 lines is not itself the problem.
- Notices that side effects on the write path are a correctness issue, not just a tidiness one.

## Common traps

- Proposing a rewrite.
- A long-lived refactor branch.
- Extracting into `OrderHelper`, `OrderManager`, `OrderUtils` - splitting by nothing.
- Starting with the payment integration, which is the riskiest and least testable part.
- Mocking every new interface in tests, producing a suite that resists further refactoring.
- Not asking about callers, then breaking two other services.

## Follow-ups

- You have two days, not two months. What do you do?
- There are no tests on the charging path and you cannot write one without extracting first. Resolve the circularity.
- Halfway through, a priority feature lands. What state is the code in?
- How do you stop this class re-forming in a year?
- Which of these extractions would you skip entirely?
