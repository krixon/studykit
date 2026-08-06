# Behavioural patterns

**Area:** patterns · **Levels:** graduate → staff+

**One line:** Ways of assigning responsibility between objects so that varying behaviour does not mean editing a growing conditional.

## strategy

**Intent: make an algorithm interchangeable at runtime.**

Extract the varying part behind an interface and pass an implementation in. Sorting orders, pricing rules, retry policies, compression algorithms.

- Replaces a `switch` on a type code with polymorphism, which is the textbook [open-closed](solid.md) move: adding a strategy adds a class rather than editing an existing method.
- Each strategy is independently testable, and the caller becomes trivial.
- **In a language with first-class functions, a strategy is usually just a function.** A one-method interface with one implementation is a function wearing a costume, and the costume costs a file.
- The cost is that behaviour is no longer visible at the call site: you have to know how it was wired to know what runs.

## observer

**Intent: notify interested parties without knowing who they are.**

The subject keeps a list of observers and calls them on a change. Events, callbacks, pub/sub, reactive streams.

- Buys decoupling: the subject depends on an interface, not on the observers, so new listeners are added without touching it.
- Costs, and they are real:
  - **Control flow becomes invisible.** Reading the publisher tells you nothing about what happens next; you have to find the subscribers.
  - **Ordering is usually unspecified**, and code that quietly depends on it is fragile.
  - **Errors in one observer** can break the notification loop, or be swallowed, depending on implementation. Decide which.
  - **Lifecycle leaks** — an observer that never unsubscribes keeps the subject alive and keeps being called. This is one of the most common memory leaks in long-lived applications.
- Synchronous in-process observers make the publisher wait for every subscriber, so one slow listener slows the write path. Asynchronous ones trade that for the delivery problems in a [message queue](../../system-design/cards/message-queues.md).

## template-method

**Intent: fix the shape of an algorithm and let subclasses fill in steps.**

A base class defines the sequence and calls abstract hooks the subclass implements.

- Effective when the sequence is genuinely fixed and the steps genuinely vary.
- Uses inheritance, which is its weakness: one axis of variation, tight coupling to the base class's internals, and a subclass that must know which hooks may be called when.
- **The composition equivalent is usually better**: pass in strategies for the varying steps rather than subclassing. Most modern codebases prefer that, and it is a good instinct.
- Watch for it becoming a base class with fifteen hooks, six of which are optional. At that point the "fixed sequence" is not fixed.

## state

**Intent: change behaviour when internal state changes, without a conditional in every method.**

Each state is an object implementing the same interface, and transitions replace the current state object.

- The alternative it replaces is a `switch (this.status)` repeated in eight methods, where adding a state means finding all eight and every one you miss is a bug.
- Makes the state machine explicit and enumerable, so illegal transitions can be refused in one place rather than allowed by omission.
- Strategy and state have an identical structure and different intent: a **strategy** is chosen by the caller and does not change itself, while a **state** transitions itself in response to events. If the object decides its own next behaviour, it is state.
- Overkill for two states and a boolean. Worth it around four or five states, or as soon as transitions have rules.

## command

**Intent: turn a request into an object.**

An operation with its parameters, packaged so it can be stored, queued, logged, retried or undone.

- Makes possible: undo and redo (each command knows its inverse), queuing and deferred execution, an audit log of intent rather than of effect, and retrying a failed operation without reconstructing it.
- This is what a job in a work queue is, and what an event-sourced system stores.
- **Undo is the demanding case.** Either each command stores enough to reverse itself, or you snapshot state, and the choice depends on whether commands are small and reversible or large and lossy.
- The cost is a class per operation, so it is over-engineering unless you need at least one of storage, deferral, audit or undo. If you only need to call the thing, call it.

## Choosing between them

| Symptom | Pattern |
|---|---|
| A `switch` on a type, chosen by the caller | strategy |
| A `switch` on internal status, repeated across methods | state |
| Several places need to react to one thing happening | observer |
| Same sequence, different steps | template method, or strategy injection |
| The request needs to outlive the call | command |

## Related

- [structural](structural.md) — patterns about composition rather than interaction
- [solid](solid.md) — most of these are open-closed applied to one axis
