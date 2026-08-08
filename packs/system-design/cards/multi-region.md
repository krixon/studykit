# Multi-region and DR

**One line:** Run in more than one geography for latency, availability or law, and pay for it in consistency and operational complexity.

## Why it exists

Three reasons, and they want different architectures. Being unclear which one you are solving is how teams build an expensive system that satisfies none of them.

- **Latency**: users are far away and the round trip is physics. Wants data close to users.
- **Availability**: a region can fail. Wants a warm copy elsewhere and a tested way to use it.
- **Compliance**: data must stay in a jurisdiction. Wants strict partitioning, not replication.

Ask which one, and whether a multi-AZ single-region deployment already gives you most of it. It usually does, for far less money: AZs are independent failure domains a millisecond apart, which is the good part of multi-region without the expensive part.

## topologies

| Topology | Writes | Failover | Cost |
|---|---|---|---|
| **Single region, multi-AZ** | one place | automatic within region | cheapest; region loss is an outage |
| **Active-passive (warm standby)** | one region, replicated out | promote the standby, minutes | paying for idle capacity; the untested path |
| **Active-active, partitioned by key** | each region owns a set of keys | reroute that key set | no write conflicts by construction. **The best answer when the data partitions cleanly** |
| **Active-active, replicated everywhere** | any region, any key | none needed | conflicts are permanent and must be resolved; needs CRDTs or LWW |
| **Read-local, write-global** | one region, reads everywhere | promote | simple and correct; writers far from the leader pay the round trip |

Partitioning by key, usually by user or tenant home region, is the most under-used option. It gives active-active latency and availability while keeping single-writer semantics per key, which removes conflict resolution entirely.

## data-residency

- Some data legally cannot leave a jurisdiction (GDPR for some categories, various data-localisation laws). This is a hard constraint that overrides the architecture, not a preference to balance.
- It usually forces **partitioning by user home region**, with only non-personal or aggregated data replicated globally.
- The awkward parts are the shared ones: a global user directory, cross-region search, analytics. The common resolution is to keep an identifier globally and the personal data locally, so a global index points into regional stores.
- Backups, logs and traces carry personal data too, and are the usual place residency is accidentally violated.

## failover

The mechanism is straightforward; the failure modes are not.

- **Traffic steering**: DNS is slow (TTLs plus resolvers that ignore them, so minutes) and anycast plus health-checked BGP is fast but coarse. Global load balancers with health checks sit in between and are usually the right answer.
- **Data**: promoting the standby loses whatever async replication had not shipped. That gap is your RPO, and you should have measured it rather than assumed it.
- **The untested path is the one that fails.** A standby that has never taken production traffic has stale configuration, cold caches, unscaled connection pools and expired credentials. Regular failover exercises, ideally as scheduled traffic shifts rather than drills, are what makes the number real.
- **Failback** is harder than failover: the recovered region is now behind, and re-syncing while serving is a second migration.
- **Split brain** across regions is worse than within one, because the partition can last longer. Fencing tokens and a single authoritative source of "who leads" are the mitigation.

## rto-rpo

- **RTO**: recovery *time* objective: how long until service resumes.
- **RPO**: recovery *point* objective: how much data you may lose, measured in time.

They are set by the business, then the architecture is chosen to meet them. Doing this in the other order is how a team ends up with an expensive design nobody asked for.

| Target | What it takes |
|---|---|
| RPO = 0 | synchronous cross-region replication, so every write pays 50-150 ms |
| RPO ≈ seconds | asynchronous replication, monitored lag, accepted small loss |
| RPO ≈ hours | periodic backups and log shipping |
| RTO ≈ minutes | warm standby, automated promotion, rehearsed |
| RTO ≈ hours | restore from backup, and you must have timed a real restore |

**A backup that has never been restored is not a backup.** Time the restore, and know how long it takes at current data volume, not at the volume when the runbook was written.

## latency-tradeoffs

- Cross-region round trip is 50-150 ms and cannot be optimised away. A synchronous write to another region costs at least that, on every write.
- A page making several sequential cross-region calls multiplies it: three dependent calls at 100 ms is 300 ms before any work.
- Reads are the easy half: serve locally from a replica and accept staleness, choosing per operation which reads need the leader.
- Writes are the hard half, and the options are exactly: send them to one region (simple, slow for distant users), partition ownership (fast, needs clean partitioning), or accept conflicts (fast, needs resolution).
- Watch for **hidden cross-region calls**: a service deployed regionally calling a global dependency, a cache miss falling through to a distant origin, or a "local" queue whose consumers are elsewhere. These are the ones that make p99 mysterious.

## Numbers to know

- Cross-region RTT: 50-150 ms (London-Virginia ~75 ms, London-Sydney ~250 ms). Same-region cross-AZ: ~1 ms.
- Light in fibre: ~200 km/ms, so the floor is geography, not engineering.
- DNS failover: minutes, TTL plus resolver disobedience. Anycast/BGP: seconds.
- Multi-region typically costs 2-3x, including idle standby capacity and inter-region data transfer, which is billed and is not negligible.

## Related

- [cap-pacelc](cap-pacelc.md): the `E`/`L` half is this card
- [replication](replication.md): the mechanism underneath
- [cdn-edge](cdn-edge.md): solving the latency case without moving the data
