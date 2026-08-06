# SOLID principles

**Area:** design-principles · **Levels:** graduate → staff+

**One line:** Five heuristics about where to put boundaries, all of which are really about making the changes you expect cheap and the ones you do not expect possible.

## Why they exist

Every one of these principles is an answer to the same question: **when this changes, how much has to change with it?** They are not laws, they are not free, and each has a cost paid in indirection. Applied without a named axis of change, they produce elaborate structure that absorbs a change nobody makes.

## srp

**Single responsibility.** A class should have one reason to change.

The useful formulation is Martin's later one: **one responsibility to one actor**. If the finance team's rules and the reporting team's rules both live in the same class, two different groups of people request changes to the same code, and their changes collide.

- The clue is in the word "and" when describing the class, and in a commit history where unrelated features keep touching the same file.
- The failure mode of over-applying it is a swarm of one-method classes where following a single operation means opening nine files. Small is not the goal; **cohesive** is.

## ocp

**Open-closed.** Open for extension, closed for modification. You should be able to add behaviour without editing existing code.

- The mechanism is usually polymorphism or a registry: new payment types plug in rather than adding a branch to an existing `switch`.
- The precondition people skip: it only works along the axis you predicted. Guessing the wrong axis buys you an abstraction that never varies while the real variation still needs edits everywhere.
- Practical rule: **wait for the second case.** Add the abstraction when the second implementation actually arrives, not when you imagine it might. The rewrite from a concrete implementation to an interface is cheap; unwinding a wrong abstraction is not.

## lsp

**Liskov substitution.** A subtype must be usable anywhere its supertype is, without the caller knowing.

Violations look like:

- Overriding a method to throw "not supported" (the classic read-only collection inheriting from a mutable one).
- Strengthening a precondition - the subclass rejects input the parent accepted.
- Weakening a postcondition - the subclass returns less than the parent promised.
- Callers doing `if (x is SpecialCase)`, which is the smell that announces the hierarchy is wrong.

The famous example: `Square extends Rectangle` breaks because setting a rectangle's width and expecting the height to stay put is a reasonable caller assumption that a square cannot honour.

This is the most concrete of the five, and the most commonly violated, because inheritance is taught as reuse when it is really a promise of substitutability.

## isp

**Interface segregation.** No client should be forced to depend on methods it does not use.

- A fat interface means every implementer writes stubs, and every consumer recompiles when an unrelated method changes.
- Segregate by **client need**, not by symmetry: if one caller only reads and another only writes, that is two interfaces, even if one class implements both.
- Related benefit that is often the real one: a narrow interface is trivial to fake in a test. A ten-method interface where you need one method is a test-setup tax paid forever.

## dip

**Dependency inversion.** Depend on abstractions, not concretions. High-level policy should not depend on low-level detail; both should depend on an abstraction.

The point is the direction of the arrow. Normally business logic calls a database class, so the domain depends on the infrastructure. Invert it: the domain **declares** the interface it needs (`OrderRepository`), and the database implementation depends on the domain by implementing it. The dependency now points inwards, and the domain can be understood, tested and changed without the database.

The commonest misreading: putting an interface in front of everything. An interface with exactly one implementation, that will only ever have one, and that lives beside its implementation, is indirection with no inversion. **DIP is about which way dependencies point across a boundary**, not about how many interfaces exist.

## The honest summary

- SRP and ISP are about **size and grouping** of units.
- LSP is a **correctness constraint** on inheritance, and the only one of the five that can be objectively violated.
- OCP and DIP are about **direction of dependency**.

All five earn their keep in code that has been alive long enough to change repeatedly. In a script that will be deleted next month, they cost more than they return.

## Related

- [coupling-cohesion](coupling-cohesion.md): what these principles are really managing
- [dependency-injection](dependency-injection.md): how DIP is wired up in practice
- [boundaries](boundaries.md): DIP at architectural scale
