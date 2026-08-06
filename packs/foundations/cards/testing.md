# Testing

**Area:** quality · **Levels:** graduate → staff+

**One line:** Executable claims about what your code does, whose real value is that they let you change it later without fear.

## test-levels

| Level | Scope | Speed | Catches | Costs |
|---|---|---|---|---|
| **Unit** | one function or class, no I/O | microseconds | logic errors | says nothing about whether the pieces fit together |
| **Integration** | a few real components, often a real database | milliseconds to seconds | wiring, SQL, serialisation | slower, needs setup |
| **End-to-end** | the whole system through its real interface | seconds to minutes | the things users actually hit | slow, flaky, expensive to diagnose |

The **pyramid** advice - many unit, fewer integration, very few end-to-end - is about feedback speed and diagnosis cost, not about purity. A failing unit test names the broken function; a failing end-to-end test tells you something, somewhere, is wrong.

The common counter-argument has force: a system of perfectly unit-tested components that were mocked into agreement can be entirely broken. That is why the middle layer matters more than the pyramid's shape suggests, and why testing against a real database in a container is usually worth its cost.

## doubles

Replacements for real dependencies, and the names are not interchangeable:

- **Stub**: returns canned answers. "This lookup returns a user."
- **Mock**: a stub that also asserts it was called correctly. "The email service was called once with this address."
- **Fake**: a real working implementation that is not production-grade. An in-memory repository. Usually the best of the three, because it exercises real behaviour.
- **Spy**: records calls for inspection afterwards, without prescribing them up front.

The failure mode is **over-mocking**: a test asserting that your code called three methods in a particular order tests the implementation, not the behaviour. Any refactor breaks it even though nothing observable changed, so the test suite becomes a tax on improvement rather than a licence for it.

Rule of thumb: mock at the **boundaries you do not own** - a third-party HTTP API, a payment provider, the clock. Use real implementations or fakes inside your own code.

## what-to-assert

Assert on **observable behaviour**, not internal steps. The test should still pass after a rewrite that keeps the behaviour.

- Given-when-then, or arrange-act-assert: a test with no clear act step is usually testing several things at once.
- One logical assertion per test. Not literally one `assert` line, but one claim - a failure should name what broke without you reading the body.
- Test the **edges**: empty, one, many, maximum, null, negative, duplicate, the boundary value and both sides of it. Bugs cluster at boundaries.
- Include the **error paths**. Most untested code is error-handling code, which is also the code that runs when things are already going badly.
- The test name should state the claim: `rejects_expired_token` beats `test_auth_2`.

## flakiness

A test that passes and fails on the same code. The most corrosive problem a suite can have, because it teaches people to re-run rather than investigate, and then a real failure gets re-run too.

Usual causes:

- **Time**: a test that depends on the current time, or a sleep that is long enough on your laptop and not on CI. Inject a clock; wait for a condition rather than a duration.
- **Order dependence**: a test that passes only after another test has run. Caused by shared mutable state that is not reset. Randomise test order to expose it.
- **Concurrency**: a genuine race, in the test or in the code. Often the test is right and the code is broken.
- **External dependencies**: a real network call in a unit test.

The policy that works: quarantine a flaky test immediately, then fix or delete it. A flaky test left in the suite costs more than no test.

## coverage

Coverage measures which lines executed while tests ran. That is all it measures.

- It is a good tool for finding **untested areas** - a file at 0% is worth a look.
- It is a bad **target**. Coverage is trivially gamed by tests with no assertions, and mandating 100% produces tests written to touch lines rather than to check behaviour, which is where Goodhart's law arrives.
- **Branch coverage** is more informative than line coverage: a line with an `if` can be fully covered with only one side of the condition ever taken.
- What coverage cannot tell you: whether the assertions are right, whether the behaviour is right, or whether the untested 10% is the payment code.

## Related

- [errors-and-logging](errors-and-logging.md): the error paths are the ones nobody tests
- [version-control](version-control.md): bisect only works if the tests are trustworthy
