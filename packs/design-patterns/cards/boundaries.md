# Boundaries and layering

**One line:** Deciding where the walls go, which direction dependencies cross them, and what each side is allowed to know.

## layering

The traditional stack: presentation → application → domain → infrastructure, each layer depending only on the one below.

It buys a comprehensible dependency order and a rule people can follow. What it gets wrong is the bottom: **the domain ends up depending on the database**, so the rules of the business are expressed in terms of the persistence technology. Change the database and the domain changes with it, which is exactly backwards from how often each actually changes.

Layers also tend to become **anaemic**: the domain layer holds data classes with getters, all behaviour lives in "services" in the application layer, and the domain layer stops being a model of anything. That is not a layering failure so much as what happens when layering is applied without asking where behaviour belongs.

The consistent rule that fixes most of it: **dependencies point towards stability**. The business rules change more slowly than the database vendor and far more slowly than the UI framework, so they should be depended on, not depend.

## ports-adapters

Hexagonal architecture, also called ports and adapters, inverts the bottom of the stack.

- The **domain** sits in the middle and depends on nothing external.
- A **port** is an interface the domain declares for something it needs: `OrderRepository`, `PaymentGateway`, `Clock`. The port belongs to the domain and is expressed in the domain's language.
- An **adapter** implements the port using a real technology: a Postgres repository, a Stripe gateway. The adapter depends on the domain, not the other way round.
- **Driving adapters** (HTTP handlers, CLI, message consumers) call into the domain. **Driven adapters** (database, queue, third-party APIs) are called by it.

Everything crossing the boundary is translated: the vendor's types, exceptions and error codes stop at the adapter, and the domain sees only its own vocabulary. That translation layer is the work, and skipping it is how a "hexagonal" codebase ends up with `StripeException` in a use case.

What it actually buys, in order of how often it pays off:

1. **The domain can be tested with no infrastructure at all** - no database, no network, milliseconds per test. This is the real, everyday return.
2. Infrastructure decisions can be deferred and changed in one place.
3. The domain reads as a description of the business rather than of the plumbing.

What it costs: more files, more mapping code, and a genuine risk of ceremony in a small application where the "domain" is four fields and a create method. In a CRUD service, hexagonal architecture is mostly overhead.

## domain-purity

The domain should not import the framework, the ORM, the HTTP library, or the vendor SDK.

Consequences worth knowing:

- **No ORM entities in the domain**, or persistence concerns leak into the model - lazy-loading proxies, required no-arg constructors, cascade rules shaping your aggregates.
- **No framework annotations** on domain types, though this is where most teams compromise, because the mapping cost is real and the annotation is inert. It is a defensible trade if made deliberately.
- **Time, randomness and identity generation are dependencies**, not ambient facts. `Clock`, `IdGenerator`, `RandomSource` injected as ports is what makes domain logic deterministic to test.
- **Side effects live at the edge.** The domain decides, the adapter performs. A domain method that sends an email has taken infrastructure inside the wall; it should return a decision that something be sent.

The purity is not an aesthetic goal. Every one of these rules exists because breaking it makes some class of change or test harder, and if it does not in your case, the rule has not earned its cost.

## module-seams

Boundaries within a codebase, and how to keep them real.

- A boundary that is only a folder is a **convention**, and conventions erode under deadline pressure. What makes one real is a mechanism: a separate build module, a package-visibility rule, an import-linter in CI, an architecture test that fails the build on a forbidden dependency. **If nothing fails when someone crosses it, it is not a boundary.**
- **Modules should be organised by feature, not by layer**, at the top level. `orders/`, `billing/`, `shipping/` each containing their own handlers, domain and persistence, rather than `controllers/`, `services/`, `repositories/` each containing everything. Changes arrive by feature, so grouping by feature makes them local - which is the whole objective in [coupling-cohesion](coupling-cohesion.md).
- **Each module exposes a narrow public surface** and keeps the rest internal. If everything is public, the boundary describes nothing.
- Cross-module communication should go through the public surface or through events. Reaching into another module's internals is [content coupling](coupling-cohesion.md), and it is what makes a modular monolith gradually stop being modular.

The relationship to services: **a well-bounded module is the precondition for extracting a service, not an alternative to it.** Splitting a tangled codebase into services distributes the tangle and adds a network. Get the boundary right in-process first, where moving it is cheap, and extract only when there is a reason - independent scaling, independent deployment, a team boundary - that is worth the operational cost.

## Related

- [dependency-injection](dependency-injection.md): the composition root wires the adapters to the ports
- [structural](structural.md): an adapter is exactly the pattern of the same name
- [solid](solid.md): this is DIP at architectural scale
