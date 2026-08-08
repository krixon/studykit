# Complexity and data structures

**One line:** How the cost of an operation grows with the size of the input, and how the structure you chose decides that.

## big-o

Big-O describes **growth**, not speed. It drops constants and lower-order terms, so O(n) and O(100n) are the same class even though one is a hundred times slower on every input.

| Class | Name | Doubling n does |
|---|---|---|
| O(1) | constant | nothing |
| O(log n) | logarithmic | adds one step |
| O(n) | linear | doubles |
| O(n log n) | linearithmic | slightly more than doubles |
| O(n²) | quadratic | quadruples |
| O(2ⁿ) | exponential | squares the work |

What this is actually for: predicting whether something that works on 100 rows will still work on 10 million. O(n²) at 1000 items is a million operations, which is instant. At a million items it is 10¹², which never finishes. The class is a warning about a future you have not reached yet.

**Average, worst and amortised** are different claims. A hash lookup is O(1) average and O(n) worst. Appending to a dynamic array is O(n) on the resize and O(1) **amortised**, because resizes double the capacity and become rare. Quoting the average when the worst case is the one an attacker controls is how algorithmic complexity attacks work.

## structure-choice

Pick by the operations you actually perform, in the proportion you perform them.

| Structure | Lookup | Insert | Ordered | Use when |
|---|---|---|---|---|
| Array / list | O(n) by value, O(1) by index | O(1) at end | insertion order | you iterate, or index by position |
| Hash map | O(1) average | O(1) average | no | you look up by key. **The default** |
| Hash set | O(1) membership | O(1) | no | you ask "have I seen this" |
| Balanced tree / sorted map | O(log n) | O(log n) | yes | you need range queries or ordered iteration |
| Heap | O(1) peek min | O(log n) | partially | you repeatedly need the smallest or largest |
| Deque | O(1) both ends | O(1) both ends | insertion order | queue or stack behaviour |

The most common real-world win is noticing a **linear scan inside a loop** and replacing it with a set or map lookup: O(n²) becomes O(n) with three lines changed.

## hashing

A hash function maps a key to a bucket index. Two keys landing in the same bucket is a **collision**, resolved by chaining (a list per bucket) or open addressing (probe for the next free slot).

- Performance depends on the **load factor** (entries per bucket). Past roughly 0.7-0.75 most implementations grow and rehash.
- A poor hash function, or adversarial input engineered to collide, degrades every operation to O(n). Language runtimes mitigate this with randomised hash seeds.
- A key used in a hash map must be **immutable and consistent**: mutating a key after insertion makes its entry unreachable, because it now hashes to a different bucket.
- Equality and hashing must agree. If two objects are equal, they must hash equally, or the map will hold both.

## sorting-searching

- Comparison sorts cannot beat O(n log n) in the general case. That is a proven bound, not a limitation of current implementations.
- Real library sorts are hybrids (Timsort, introsort): O(n log n) worst case, and much faster on partially ordered data, which real data usually is.
- **Binary search** is O(log n) and requires sorted input. Sorting to enable one search costs more than scanning; sorting to enable many searches pays back quickly.
- **Stability** matters when you sort by one key and then another: a stable sort preserves the previous order among equal elements, which is how multi-key sorting is built.

## memory-locality

Big-O ignores constants, and on modern hardware the constants span two orders of magnitude.

- Sequential access through an array is far faster than following pointers through a linked list of the same length, because the CPU prefetches contiguous memory and each cache miss costs roughly 100 ns against ~1 ns for a cache hit.
- This is why an array with O(n) search often beats a "better" pointer-based structure for small n. The crossover is frequently in the hundreds or thousands of elements, not at 10.
- Practical rule: prefer contiguous structures until you have measured a reason not to, and be suspicious of asymptotic arguments about small collections.

## Numbers to know

- L1 cache ~1 ns, main memory ~100 ns, SSD ~100 µs, network round trip in a datacentre ~0.5 ms.
- 10⁸ simple operations per second is a safe planning figure for interpreted languages, 10⁹ for compiled.
- O(n²) becomes painful around n = 10,000 and impossible around n = 1,000,000.

## Related

- [sql-and-indexes](sql-and-indexes.md): an index is a data structure choice made in a database
- [data-and-encoding](data-and-encoding.md): how much memory your data actually takes
