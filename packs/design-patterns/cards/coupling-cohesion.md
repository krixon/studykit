# Coupling and cohesion

**Area:** design-principles · **Levels:** mid → staff+

**One line:** The two properties every design principle is ultimately trying to improve: how much things depend on each other, and how well the things grouped together belong together.

## Why they matter more than the patterns

Patterns are tactics; these are the objective. A design is good when a change is **local** - contained in one place, understandable without reading five other files. Low coupling makes changes local; high cohesion makes the local place the obvious one. If applying a pattern raises coupling or lowers cohesion, the pattern is being applied wrongly, whatever its name.

## coupling-kinds

Weakest to strongest. The goal is to sit as high in this list as the problem allows.

| Kind | What it means | Example |
|---|---|---|
| **Data** | pass exactly the data needed | `calculateTax(amount, rate)` |
| **Stamp** | pass a structure, use part of it | `calculateTax(order)` when only the total is used |
| **Control** | pass a flag that changes the callee's behaviour | `process(data, isDraft)` |
| **Common** | share global mutable state | two modules reading and writing the same global |
| **Content** | reach into another's internals | modifying another object's private field |

Two more that matter and do not fit the classic list:

- **Temporal coupling** — A must be called before B, and nothing enforces it. `open()` then `read()` where calling `read()` first fails at runtime. The fix is to make the invalid order unrepresentable: `open()` returns the object that has `read()`.
- **Semantic coupling** — two modules share an assumption written down nowhere. The worst kind, because nothing in the code shows the connection, and it survives every refactor until it breaks.

**Control coupling** deserves special attention: a boolean parameter that switches behaviour means the function does two things and the call site does not say which. `render(true)` is unreadable at the call site and usually wants to be two functions.

## cohesion

How well the parts of a module belong together. Strongest to weakest:

- **Functional** — everything contributes to one well-defined task. The target.
- **Sequential** — output of one part feeds the next.
- **Communicational** — parts operate on the same data.
- **Temporal** — parts happen at the same time. A `startup()` doing six unrelated things.
- **Logical** — parts are the same *category* of thing, selected by a flag. A `Utils` class, or a `handleEvent(type)` with a switch.
- **Coincidental** — no relationship. `helpers.py`.

The names to recognise in the wild are the bottom two. **A class named `Manager`, `Helper`, `Util` or `Service` with no further qualification is usually coincidentally cohesive** - it is a place things were put, not a thing.

The relationship between the two properties: they trade off if you push either to an extreme. Maximum cohesion alone gives you a thousand tiny classes that must all talk to each other, which is high coupling. Minimum coupling alone gives you one giant module that depends on nothing, which has no cohesion. **The goal is a balance that makes likely changes local**, and "likely changes" is a judgement about the domain, not a property of the code.

## demeter

The Law of Demeter: talk only to your immediate collaborators. A method may call methods on itself, its parameters, objects it created, and its own fields - not on objects it got back from any of those.

`order.getCustomer().getAddress().getPostcode()` couples you to three classes and their entire chain of relationships. Any of them changing breaks you, and you knew about none of them.

- The fix is not a delegating method for every chain. It is to ask **why you need the postcode**: often the right answer is `order.shippingPostcode()`, or better, to move the behaviour to where the data is - `order.calculateShipping()`.
- The genuine exception is **fluent interfaces and data structures**. `builder.name(x).age(y).build()` and `list.filter(...).map(...)` return self or a new value rather than exposing internals, so there is no coupling to a hidden structure. Applying Demeter to those is cargo cult.

The chain is a smell about **behaviour in the wrong place**, not about the number of dots.

## leaky-abstractions

An abstraction leaks when you must know what is underneath to use it correctly.

- An `OrderRepository` returning a database cursor that must be closed, or throwing `SqlException`. The interface says storage; the caller must know it is SQL.
- A cache interface whose `get` sometimes takes 200 ms because it silently falls through to the network.
- A collection interface where one implementation is O(1) and another O(n) for the same call, and callers must know which they have.

Two honest positions to hold at once: **all non-trivial abstractions leak** (performance, failure modes and resource limits always show through), and that is not a reason to skip them. It is a reason to (a) leak deliberately - put timeouts and failure modes *in* the interface rather than pretending they do not exist, (b) translate foreign exception types at the boundary, and (c) be suspicious of an abstraction whose only justification is that it might let you swap the implementation one day.

The test for whether an abstraction is worth it: **does it let you reason about the caller without reading the implementation?** If not, it is indirection, not abstraction.

## Related

- [solid](solid.md) — five heuristics in service of these two properties
- [boundaries](boundaries.md) — coupling across a module boundary is the expensive kind
- [refactoring](refactoring.md) — the smells are mostly coupling and cohesion failures
