# Refactoring and smells

**Area:** refactoring · **Levels:** graduate → staff+

**One line:** Changing the structure of code without changing its behaviour, in steps small enough that you are never far from working.

## What refactoring is not

Refactoring is **behaviour-preserving**. Rewriting a module and also fixing three bugs and adding a feature is not refactoring; it is a rewrite, and it carries a rewrite's risk. The discipline matters because the entire safety argument rests on behaviour being unchanged: if the tests should still pass, a failing test means you made a mistake, and that signal is what makes the process safe.

## smells

A smell is a hint, not a verdict. Each one is a question worth asking.

- **Long method.** Not the line count itself - it is that you cannot hold it in your head, and that the comments dividing it into sections are naming the extractions you have not done yet.
- **Large class / god class.** Too many responsibilities. Look at whether the fields cluster: if half the methods use one group of fields and half use another, that is two classes wearing one name.
- **Long parameter list.** Often a missing concept. Four parameters that always travel together are an object.
- **Feature envy.** A method more interested in another class's data than its own. Usually it belongs on the other class.
- **Data clumps.** The same three fields appearing together everywhere. Same fix as above.
- **Primitive obsession.** A string that is really an email, an int that is really a currency amount. Wrapping it moves validation into the type and makes wrong usage a compile error.
- **Shotgun surgery.** One change requires edits in many places. Cohesion is too low - the thing that changes together is not together.
- **Divergent change.** One class changes for many unrelated reasons. Cohesion is wrong the other way - it should be split.
- **Switch on type.** Frequently wants polymorphism, especially if the same switch appears more than once.
- **Speculative generality.** Abstraction for a case that never arrived. An interface with one implementation, a parameter always passed the same value, a hook nobody uses. Delete it.
- **Comments explaining what.** Usually a name that should have been better. Comments explaining *why* are valuable and different.

Shotgun surgery and divergent change are the pair worth internalising: they are the two ways cohesion fails, and they point in opposite directions.

## safe-steps

The method is what makes this safe, not the intent.

1. **Get a test in place first.** If there is none, write a characterisation test - one asserting what the code currently does, right or wrong. It is not a specification, it is a tripwire.
2. **One transformation at a time**, each mechanical and reversible: rename, extract method, inline, move method, extract class, introduce parameter object.
3. **Run the tests after each step.** The value of small steps is that a failure names the step that broke it.
4. **Commit each step.** A refactor that has been going for two days without a commit cannot be abandoned cheaply, and abandoning cheaply is what lets you try things.
5. **Never mix a refactor with a behaviour change in one commit.** Reviewers cannot see the behaviour change inside a thousand-line diff of moved code, and neither can `git bisect`.

For code with no tests and no seams, the order is inverted: find a seam, get a test around the boundary, then refactor inward. Injecting a dependency purely to make a test possible is a legitimate first step.

The **strangler fig** pattern for large-scale work: put the new implementation alongside the old, route a slice of calls to it, verify, widen the slice, then delete the old one. It keeps the system working throughout, which a big-bang rewrite does not.

## naming

The cheapest refactor and the highest-return one, because names are what everyone reads.

- Name by **what it means**, not how it is done. `activeCustomers`, not `filteredList`.
- Length should scale with scope: `i` in a three-line loop is fine, `d` as a class field is not.
- Avoid noise words: `data`, `info`, `manager`, `helper`, `process`, `handle`. If the name would still fit after the class does something completely different, it says nothing.
- Booleans read as a predicate: `isExpired`, `hasPermission`.
- **Keep the domain's vocabulary.** If the business says "policy", the code should not say "contract". Every translation is a place misunderstandings live.
- A name you cannot choose usually means the thing has no single responsibility. Struggling to name it is information.

## duplication

DRY is about **knowledge**, not text. Two pieces of code that look identical but encode different rules are not duplication, and merging them couples two things that will diverge.

- The real question: **if this rule changes, must both places change?** If yes, it is duplication. If they would change independently, it is coincidence.
- The **rule of three** is the practical heuristic: the second occurrence is noted, the third justifies the abstraction. Two data points do not show you the axis of variation, so abstracting at two frequently produces the wrong abstraction.
- **A wrong abstraction costs more than duplication.** Duplication is visible and mechanical to fix. A wrong abstraction is a shared thing everyone bends with special cases and flags, and unwinding it means understanding every caller. When you find one, inline it back and re-abstract from the concrete cases.
- Duplication across a **module boundary** is often correct: two services sharing a copied model are independently deployable, whereas a shared library couples their release cycles. Inside a module, remove it; across one, think twice.

## Related

- [coupling-cohesion](coupling-cohesion.md) — what most smells are measuring
- [solid](solid.md) — the direction most refactors move in
