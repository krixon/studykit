# Distributed rate limiter - interviewer notes

**Do not reveal any of this before the attempt.**

The question underneath is: how much inaccuracy can you buy latency with? A candidate who picks an algorithm without first asking what the limiter is *for* has missed the problem.

## Hidden requirements

- Functional: per-tenant limits, different limits per plan, different costs per endpoint, communicate the limit to callers.
- Non-functional: adds under ~1 ms to the request path, must not become the bottleneck, must keep working when its own state store is unavailable.
- Deliberately unstated: whether the limit is a commercial contract or overload protection, how exact it must be, whether tenants can burst.

## Back-of-envelope they should reach

- 1M requests/second across 500 servers = 2000 req/s per server.
- A central counter means 1M round trips/second to the store, which is a large Redis cluster existing solely to count. That number is what motivates leasing.
- Leasing 100 tokens at a time cuts it to 10k/second, a 100x reduction, at a cost of up to 500 × 100 = 50,000 tokens of overshoot.

## Deep dives (pick two or three)

1. **Algorithm.** Should land on token bucket, and be able to say why: it expresses "rate R with burst B", which is what an API contract says, in two numbers of state. Sliding window log is exact and its memory grows with traffic, which is the wrong direction under attack.
2. **Distributed state.** Central store, sticky routing, or local leasing. The examinable insight is that **overshoot must be judged relative to the limit**: 50,000 tokens of slop against a 10M/hour plan is nothing; against a 10/minute plan it is absurd. A good answer uses different strategies for large and small limits.
3. **Failure mode.** The store is unreachable. Fail open or closed? Protection limiters fail open with a conservative local fallback, because failing closed causes the outage the limiter existed to prevent. Commercial limiters may fail closed. The answer must be "it depends on which of these it is" with a reason.
4. **Contract.** 429 with Retry-After and jitter, plus limit/remaining/reset headers. Push on what happens without jitter - synchronised client retries produce a self-sustaining spike.

## Strong-answer signals

- Asks what the limiter is for before choosing anything.
- Weighted costs per endpoint rather than one limit for all calls.
- Overshoot analysis with actual numbers, and the recognition that it scales with node count over limit size.
- Different strategy for small limits (sticky routing or central) versus large ones (leasing).
- Places the check at the edge, before expensive work.

## Common traps

- Choosing an algorithm before establishing the requirement.
- Central Redis on every request with no discussion of the added latency and dependency.
- Uniform limits across endpoints of wildly different cost.
- Fail-closed by default with no reasoning.
- Rate limiting after authentication and a database read, so the cost is already spent.

## Level calibration

- **Mid**: correct algorithm choice with the boundary defect understood, a central counter, and a sensible 429 contract.
- **Senior+**: leasing with an overshoot calculation, fail-open reasoning, weighted costs.
- **Lead/staff**: expects the small-limit versus large-limit split, the retry-storm interaction, and a statement of what they would not build.

## Follow-ups

- One tenant's limit is 10 requests per minute. Does your design still work? Show me the numbers.
- Redis is down. What happens to the next million requests?
- A customer says they were rate limited unfairly. How do you answer them?
- How do you change a tenant's limit without a deploy, and how fast does it take effect?
- The limiter is now the slowest thing in the request path. What do you do?
