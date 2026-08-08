# Dependency injection

**One line:** Give an object its collaborators rather than letting it fetch them, so what it depends on is visible, substitutable, and decided in one place.

## inversion

Three related ideas that get used interchangeably and are not the same:

- **Dependency inversion (DIP)**: a *principle*: high-level policy and low-level detail both depend on an abstraction, and the abstraction belongs to the policy. This is about the direction of the arrow.
- **Dependency injection (DI)**: a *technique*: pass dependencies in rather than constructing or locating them internally. This is about where `new` happens.
- **Inversion of control (IoC)**: a *style*: the framework calls you rather than you calling it. DI is one instance of it.

You can do DI without DIP (injecting a concrete class), and DIP without a framework (hand-wired constructors). Neither requires a container.

The forms, in order of preference:

- **Constructor injection**: dependencies are parameters. The signature states exactly what the class needs, and an object cannot exist in a half-configured state. **The default.**
- **Method injection**: pass it to the one method that needs it. Right when the dependency varies per call, such as the current user.
- **Property/setter injection**: assign afterwards. Allows a partially built object and makes the dependency optional in a way that is rarely intended. Use for genuinely optional collaborators only.
- **Service locator**: the object asks a registry for what it needs. This is not DI: the dependency is hidden again, just behind a different global. Usually an anti-pattern, and the honest counter-argument is that it is sometimes the only option in a framework you do not control.

The real benefit is not testability, though that is the one people cite. It is that **a constructor signature becomes an honest declaration of what the class needs**, so a class with nine dependencies is visibly doing too much. DI makes bad cohesion legible.

## wiring

Somewhere, concrete types must be chosen and connected. That place is the **composition root**: one location, as close to the program entry point as possible, where the object graph is built.

- Everything else takes its dependencies and never constructs its collaborators.
- Only the composition root knows about concrete implementations, so swapping one is a single edit.
- **Manual wiring is a legitimate choice** and often the right one. A container earns its place at a few hundred registrations, not at twenty, and the cost of a container is that resolution failures become runtime errors far from the cause.
- If wiring is spread across the codebase, there is no composition root, and the benefit is gone even if constructor injection is used everywhere.

## lifetimes

Whoever wires the graph must decide how long each object lives.

| Lifetime | One per | For |
|---|---|---|
| Transient | resolution | cheap, stateful objects |
| Scoped | request, job, transaction | per-request state, unit of work, database session |
| Singleton | process | stateless services, pools, caches |

Two rules prevent almost every lifetime bug:

- **A longer-lived object must never capture a shorter-lived one.** A singleton holding a scoped database session is a *captive dependency*: the session outlives its scope, holds a connection forever, and serves stale data. Containers can detect this; hand-wiring cannot, so it needs discipline.
- **Anything registered as a singleton must be thread-safe**, because it will be used concurrently whether you planned for that or not.

## test-seams

A seam is a place where behaviour can be changed without editing the code around it. DI creates seams at every constructor parameter.

- Substitute a fake repository, a fixed clock, a deterministic random source, a fake payment gateway. The three that matter most in practice are **time, randomness and I/O**, because they are the sources of untestable behaviour and all three are trivially injectable.
- The seam should be at a **boundary you own**. Injecting every internal collaborator to mock it in tests produces tests coupled to the implementation, which then resist the refactoring they were supposed to enable. See [testing](../../foundations/cards/testing.md).
- A class with a long constructor is not a DI problem, it is a cohesion problem that DI has made visible. The fix is to split the class, not to introduce a parameter object that hides the count.

The signal that DI has been over-applied: an interface with exactly one implementation, that will only ever have one, existing solely so a test can mock it. If you would not swap it in production, consider whether the test should use the real thing.

## Related

- [solid](solid.md): DIP is the principle this technique serves
- [creational](creational.md): where construction goes instead
- [boundaries](boundaries.md): the composition root sits outside every boundary
