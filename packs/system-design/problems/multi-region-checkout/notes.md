# Multi-region checkout - interviewer notes

**Do not reveal any of this before the attempt.**

This problem rewards saying no. It is framed as a design task and the strongest answers begin by interrogating the requirement, because the right architecture depends entirely on which of latency, availability or compliance is driving it - and often on none of them being worth the cost.

## Hidden requirements

- Functional: browse, cart, inventory check, payment, order creation, order history.
- Non-functional: **why multi-region has not been stated**. Latency for distant users, surviving region loss, and data residency lead to three different designs.
- Deliberately unstated: the RTO and RPO, whether inventory is shared globally, whether users travel between regions.

## Back-of-envelope they should reach

- Cross-region round trip 75-150 ms. A checkout with three sequential cross-region calls is 300+ ms of pure network.
- Multi-region typically costs 2-3x, including idle standby capacity and inter-region transfer.
- If the driver is availability: what is a region outage actually worth? An hour of downtime per year against a 2-3x permanent cost is a business calculation, and the candidate should say so rather than assume.

## Deep dives (pick two or three)

1. **Decompose by consistency need.** This is the core of a strong answer. Browse and catalogue: fully replicated, stale is fine, serve locally. Cart: user-scoped, so partition by user home region - no conflicts. Inventory: globally contended, and the hard part. Payment: external, idempotent, and effectively single-region per transaction. Order history: written once, replicated, read locally. **Refusing to give the whole system one consistency model is the signal.**
2. **Inventory.** The genuinely hard piece. Options: single authoritative region (simple, correct, slow for distant users, and unavailable if that region is down); regional allocation where each region is granted a slice of stock and can sell from it without coordination (fast, available, and can under-sell when one region exhausts its slice while another has stock); or accept oversell and reconcile, which many real retailers do because the cost of an occasional cancellation is lower than the cost of coordination. Regional allocation is the same leasing idea as a rate limiter, with the same overshoot analysis.
3. **Failover.** RTO and RPO must come from the business first. Push on the failback path and on how often the failover is exercised. An untested standby is not a capability.
4. **Residency.** If a region's data cannot leave, active-active replication of everything is off the table regardless of engineering preference, and the design must partition by home region with a global identifier index.

## Strong-answer signals

- Asks *why* multi-region before designing anything, and is willing to recommend against it.
- Decomposes by data class rather than picking one consistency model.
- Regional inventory allocation with an explicit under-sell or over-sell analysis.
- Partitions users by home region to eliminate cart and profile conflicts.
- Names the migration path from the current single-region system, not just the target state.
- States what they would deliberately keep single-region.

## Common traps

- Designing active-active for everything and hand-waving inventory conflicts.
- Last-write-wins on inventory or cart.
- Synchronous cross-region writes on the checkout path.
- No migration story - describing only the end state.
- Accepting the multi-region premise without asking what it is for.

## Follow-ups

- The last unit of stock is requested from two regions simultaneously. What happens?
- Region A is unreachable for 30 minutes. What can a user in region B still do, and what fails?
- A user in Europe travels to the US and checks out. Which region serves them?
- What is your RPO for orders, and how do you know?
- How would you get from the current single-region system to this, without a big-bang cutover?
- What would you tell a VP who wants this delivered in a quarter?
