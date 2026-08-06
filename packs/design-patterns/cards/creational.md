# Creational patterns

**Area:** patterns · **Levels:** graduate → staff+

**One line:** Ways of separating *what gets constructed* from *the code that needs it*, so construction can vary without every caller changing.

## Why they exist

A `new` in the middle of business logic hard-codes a choice: this exact class, with these exact dependencies, right here. That is fine until the choice must vary by configuration, by environment, or by test. Every creational pattern moves that decision somewhere it can be changed.

## factory

- **Factory method** — a method whose job is to create the object, so subclasses or configuration decide which concrete type. Callers ask for the abstraction and never name the implementation.
- **Abstract factory** — a family of related products created together, so you cannot accidentally mix a Windows button with a Mac scrollbar. The consistency constraint is the whole point; without one, an abstract factory is over-engineering.
- **Static factory method** — a named constructor: `Duration.ofSeconds(30)`, `User.fromLegacyRecord(row)`. Cheap, immediately useful, and undersold. It gives construction a name, can return a cached instance or a subtype, and does not need a class hierarchy.

Reach for the static factory method by default. Reach for a factory *object* when the decision genuinely varies at runtime.

## builder

For objects with many optional parameters, or where construction happens in steps.

- Replaces the telescoping constructor - four overloads and a call site reading `new Report(true, false, null, true)` that nobody can decode.
- Allows validation of the whole object at `build()`, rather than parameter by parameter, so cross-field rules have somewhere to live.
- Makes call sites self-documenting because each value is named.

The cost is a second class to maintain, and a window in which a half-built object exists. In languages with named or default arguments, a builder is usually unnecessary - the language already solved it.

## singleton

One instance, globally reachable. The pattern with the worst reputation, and the reputation is earned.

What it actually costs:

- **Hidden dependency.** A class using a singleton has a dependency invisible in its signature, so you cannot tell what it needs by reading its constructor.
- **Untestable.** Global mutable state persists between tests, so tests become order-dependent, and substituting a fake means a global mutation.
- **Concurrency.** Lazy initialisation is a race unless done carefully, and the shared mutable state inside is a race by construction.
- **It conflates two things**: "there should be one of these" and "anyone may reach it from anywhere". The second is the harmful half.

The alternative is almost always: create one instance at the composition root and **inject** it. You keep single-instance semantics and lose the global access. Legitimate uses are rare and tend to be genuinely stateless or process-wide infrastructure, such as a logger façade.

## object-lifetime

The question a container makes explicit, and that you answer implicitly whether or not you use one.

| Lifetime | One instance per | Right for | Danger |
|---|---|---|---|
| **Transient** | request for it | cheap, stateful objects | allocation churn if construction is expensive |
| **Scoped** | request, job or transaction | anything holding per-request state, a unit of work | leaking it into a longer-lived object |
| **Singleton** | process | stateless services, connection pools, caches | any mutable state is now shared across threads |

The failure that catches everyone: a **captive dependency**, where a singleton holds a reference to a scoped object. The scoped object never goes out of scope, so a database session or a request context lives for the life of the process, holding stale data and eventually a connection.

Two rules that prevent most lifetime bugs: a longer-lived object must never capture a shorter-lived one, and anything registered as a singleton must be thread-safe.

## Related

- [dependency-injection](dependency-injection.md) — where construction decisions belong
- [solid](solid.md) — DIP is why factories exist at all
