# Structural patterns

**Area:** patterns · **Levels:** graduate → staff+

**One line:** Ways of composing objects so the arrangement, rather than inheritance, provides the behaviour you need.

## Why they exist

Inheritance fixes relationships at compile time and gives you one axis of variation. Composition lets you assemble behaviour at runtime along as many axes as you like. Every pattern here is a specific shape of "wrap or combine, rather than subclass".

The four wrapping patterns look identical in a diagram - an object holding another object of a compatible type - and differ entirely in **intent**. Naming the intent is what makes them useful vocabulary rather than trivia.

## adapter

**Intent: make an incompatible interface fit.**

You need `PaymentGateway`; the vendor SDK offers `StripeClient`. An adapter implements your interface and translates calls to theirs.

- The interface **changes**. That is the defining property.
- This is the standard way to keep third-party types out of your domain: the vendor's types stop at the adapter, so replacing the vendor touches one class.
- Also used to retrofit an old class into a new abstraction without editing it, which matters when you do not own it.

## decorator

**Intent: add behaviour without changing the interface.**

Wrap an object in another implementing the **same** interface, adding something before or after delegating.

- Interface **stays the same**, which is precisely what separates it from an adapter.
- Stackable: `Cached(Retrying(Logging(Repository)))`. Each layer is independently testable and can be added or removed by changing wiring only.
- This is the composable alternative to a subclass explosion - three orthogonal behaviours need three decorators rather than eight subclasses.
- The cost is a stack trace with many frames and a runtime object graph that is harder to see than a class hierarchy. Deep stacks get hard to debug.

## facade

**Intent: give a simple interface to a complicated subsystem.**

One class exposing the two operations callers actually need, hiding six collaborating classes behind it.

- Interface is **narrower and simpler**, not equivalent. That separates it from a decorator, and it wraps *many* objects rather than one, which separates it from an adapter.
- Does not forbid access to the subsystem; it just means most callers do not need it.
- The failure mode is a facade that grows until it is the subsystem plus a layer - if every method is a one-line delegation and there are forty of them, it has stopped simplifying anything.

## proxy

**Intent: control access to an object.**

Same interface, and the wrapper decides whether, when or how the real call happens.

- **Virtual proxy**: defer expensive creation until first use (ORM lazy loading).
- **Protection proxy**: check permissions before delegating.
- **Remote proxy**: the real object is on another machine; the proxy handles the transport. Every RPC client stub is this.
- **Caching proxy**: return a stored result instead of calling.

Decorator and proxy have the same shape and differ in purpose: a decorator **adds** to what happens, a proxy **controls whether it happens**. The practical consequence is that a proxy may not call the real object at all.

## composite

**Intent: treat a single object and a tree of objects identically.**

A `Component` interface implemented by both leaves and containers, where the container holds children and implements operations by delegating to them.

- Files and folders, UI elements and panels, a validation rule and a rule set, a query predicate and an AND of predicates.
- The win is that client code has no `if (isLeaf)` anywhere: recursion falls out of the structure.
- The tension is operations that only make sense on one kind - `add(child)` on a leaf. Putting it on the interface forces leaves to throw and violates [Liskov](solid.md); putting it only on the container means clients sometimes need to know which they have. There is no clean resolution, only a choice of which cost to pay.

## Choosing between them

| You want to | Pattern | Interface |
|---|---|---|
| Make a square peg fit a round hole | adapter | changes |
| Add behaviour transparently | decorator | same |
| Hide complexity behind something simpler | facade | narrower |
| Intercept, defer or deny the call | proxy | same |
| Treat one and many the same way | composite | shared by leaf and container |

## Related

- [behavioural](behavioural.md): patterns about how objects interact
- [boundaries](boundaries.md): adapters are how a hexagonal architecture meets the outside
