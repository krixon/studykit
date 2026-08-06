# Design a plugin system - interviewer notes

**Do not reveal any of this before the attempt.**

Open-closed at architectural scale. Most candidates design the happy path in five minutes; the discriminating questions are all about what happens when a plugin misbehaves and how the interface survives version two.

## Hidden requirements

- Functional: register a plugin, discover installed ones, invoke them at defined points, configure them.
- Non-functional: a bad plugin must not take the host down, the core must be able to evolve without breaking existing plugins, plugin authors are other teams who will not read your documentation carefully.
- Deliberately unstated: in-process or out-of-process, first-party or third-party authors, whether plugins can see each other, whether order matters.

## The question that shapes everything

**Are plugin authors trusted?** First-party teams in the same repo is a completely different problem from arbitrary third parties. In-process gives speed and shared types with no isolation; out-of-process (a subprocess, a WASM sandbox, a webhook) gives isolation at the cost of serialisation and latency. A candidate who does not ask this designs for one and is wrong for the other.

## Deep dives (pick two or three)

1. **The extension interface.** What shape are the hooks? Options: an interface each plugin implements, a set of named events they subscribe to, or a middleware pipeline they insert into. Push on **who defines the contract** - a hook taking your internal domain object means every internal change is a breaking change for every plugin, so the payload should be a stable, versioned type owned by the plugin API rather than by the core.
2. **Isolation and failure.** A plugin that throws, hangs, allocates unboundedly, or blocks the loop. Needs a timeout per invocation, exception containment so one plugin's failure does not abort the others or the host operation, and a policy for repeated failure - disable it and alert, rather than failing forever. Push on whether a plugin failing should fail the host operation: the answer differs for an audit plugin and a validation plugin, and the API should let a plugin declare which it is.
3. **Discovery and lifecycle.** A manifest declaring name, version, required host version and requested capabilities; discovery by scanning a directory or reading configuration; explicit init and shutdown so plugins can acquire and release resources. Push on ordering: if two plugins both transform a value, who goes first? Either declare priorities or make the operation order-independent, and say which.
4. **Versioning the API.** This is the part that decides whether the system survives. The core will change; the plugin interface must stay stable or version explicitly. Expand-migrate-contract, a declared minimum host version in the manifest, and a deprecation policy. Ask them how they would remove a hook.
5. **Capabilities.** What can a plugin reach? A plugin handed the whole application context can do anything and now depends on everything. Passing a narrow, purpose-built context per hook is both a security boundary and a coupling boundary.

## Strong-answer signals

- Asks about trust and process boundary before designing.
- Stable, versioned payload types at the boundary rather than internal domain objects.
- Timeouts, error containment, and a disable-on-repeated-failure policy.
- A narrow capability object per hook rather than the whole context.
- An explicit answer on ordering.
- Says how a hook gets removed, not just added.
- Mentions observability - which plugin is slow, which is failing - because with plugins the host gets blamed for other people's code.

## Common traps

- Passing internal domain objects to plugins, freezing the core's internals into the public contract.
- No timeout, so one hanging plugin hangs the host.
- One plugin's exception aborting the whole operation, silently or otherwise.
- Global registration order deciding behaviour, undocumented.
- No versioning story, so the first core change breaks every plugin.
- Giving plugins the full application context because it is convenient.

## Follow-ups

- A plugin hangs for 30 seconds on every request. What does the user see?
- You need to change a hook's signature. Walk me through it with 40 plugins installed.
- Two plugins want to modify the same value. What happens?
- A plugin leaks memory. How do you find out which one?
- Would you allow plugins to call each other? What does that cost you?
