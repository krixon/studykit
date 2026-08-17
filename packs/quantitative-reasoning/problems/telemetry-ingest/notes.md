# Size a vehicle telemetry pipeline - interviewer notes

**Do not reveal any of this before the attempt.**

This is an arithmetic problem wearing a design problem's clothes. What separates answers is not the total but whether the candidate finds the dominant term, keeps peak apart from mean, and notices that the sizing question and the storage question turn on different inputs.

Give figures only when asked for them, one at a time, and note which ones the candidate never asks about.

## Hidden requirements

Supply these when asked. A candidate who starts calculating without asking has skipped the part being examined.

- 250,000 vehicles in the fleet.
- A sample every 5 seconds, but only while the vehicle is driving.
- An average of one hour of driving per vehicle per day.
- At the evening peak, about 15% of the fleet is driving at once.
- A sample is about 400 bytes as JSON, about 80 bytes in a packed binary encoding.
- Retention: 90 days at full resolution. What happens afterwards is deliberately unstated.
- Ingest is handled in about 20 ms per sample, and the storage tier keeps three copies.
- Deliberately unstated, and worth waiting to see whether they ask: whether samples may be lost, whether they must arrive in order, what the data is actually for, whether the fleet is growing.

## Back-of-envelope they should reach

Volume, from the driving hour rather than the day:

- 3600 / 5 = 720 samples per vehicle per driving hour, so 720 per vehicle per day.
- 250,000 x 720 = **180 million samples a day**.
- 180,000,000 / 86,400 = **about 2,100 samples per second as a mean**.

Peak, which is a different calculation and not a multiplier applied to the mean:

- 15% of 250,000 = 37,500 vehicles driving at once, each sending every 5 seconds.
- 37,500 / 5 = **7,500 samples per second at peak**, which is **3.6x the mean**. A candidate who sizes on the mean is out by that factor, and a candidate who invents a peak multiplier without computing it has got the right answer by luck.

Bandwidth, which is the sanity check that kills a line of discussion:

- 7,500 x 400 bytes = 3 MB/s, about **24 Mbps** at peak. The network is not the problem and never becomes one. Say so and move on.

Storage, where the encoding decides the answer:

- JSON: 180,000,000 x 400 bytes = **72 GB a day**, so 90 days is **6.5 TB**, and **19.4 TB** with three copies.
- Packed: 180,000,000 x 80 bytes = **14.4 GB a day**, 90 days is **1.3 TB**, **3.9 TB** with three copies.
- **The encoding moves the answer 5x and nothing else on the table moves it that much.** That is the dominant term, and finding it is the point of the exercise.

Fleet size for ingest, via Little's law and a utilisation target:

- 7,500 per second at 20 ms each is **150 requests in flight** at peak. That is the concurrency the pool must allow, and it is a small number: this is not a thread-per-request scaling problem.
- If a node sustains 2,000 samples per second, a 60% utilisation target makes it 1,200 usable, so 7,500 / 1,200 = 6.25, meaning **7 nodes**, and **8 with one spare** so an ordinary restart is not an incident.
- Check it: 8 nodes at peak is 7,500 / 16,000 = **47% utilised**, and **54%** with one node lost. Both inside the target, which is what N+1 means here.

## Deep dives (pick two or three)

1. **Peak versus mean.** The two numbers come from different models: the mean from a daily total divided by 86,400, the peak from how many vehicles are driving simultaneously. Push on which one sizes the fleet (peak), which one sizes the bill (mean), and what a diurnal or seasonal pattern does to both. A good candidate volunteers that a bank holiday or a weather event moves the peak and not the mean.
2. **The buffer.** Ask what happens if a deploy stalls the ingest tier, or a burst arrives at twice peak for 30 seconds. At 15,000 per second against a comfortable 9,600, the excess is 5,400 per second, so **162,000 samples** accumulate in half a minute. Draining them takes 162,000 / (9,600 - 7,500) = **about 77 seconds**, because drain time is set by the spare capacity and not by the size of the burst. The examinable point is that the queue depth is a latency decision and the bound must be explicit: shed, or buffer to disk, or let the vehicle retry later.
3. **Retention and growth.** 90 days at full resolution is a stock, not a flow, so it stops growing. Then ask what happens at 10% a month: **3.1x in a year**, doubling in about **7 months**, so the 3.9 TB becomes about **12 TB** and the ingest fleet roughly triples. The lever with unbounded return is retention, and downsampling after a window is where the conversation should land.
4. **Rare events at scale.** A fault that shows up on one sample in a million is not rare here: 180 million samples a day means **180 a day**, so a defect nobody could reproduce in testing is continuous in production. This is also the answer to "we have never seen it happen in a test run".
5. **What the data is for.** The strongest candidates ask early. If it is a live map, the requirement is latency and losing a sample is free. If it is billing or a warranty claim, no sample may be lost and the storage question changes shape. Sizing without asking this produces a defensible number for the wrong system.

## Strong-answer signals

- Computes the peak from concurrency rather than multiplying the mean by a number they made up.
- Names the encoding as the dominant term, with the 5x attached.
- States units on every intermediate value, and says whether a figure is per second, per day or peak.
- Sanity-checks at least one figure against something known, and notices the bandwidth is trivial.
- Distinguishes the stock (90 days of storage) from the flow (bytes per day).
- Sizes for the peak, costs for the mean, and says which is which.
- Volunteers what would change the answer: retention, encoding, sample interval, whether idle vehicles report.

## Common traps

- Multiplying 250,000 vehicles by a sample every 5 seconds all day, giving 50,000 per second: a 24x overestimate from ignoring that cars are parked. This is the most common single error and it is worth letting them run into their own sanity check.
- Sizing the fleet on the mean rate.
- Quoting a storage figure without saying which encoding, or forgetting the replication factor entirely.
- Treating peak as mean times an unexamined factor of two.
- Spending time on the network, which is 24 Mbps and never interesting.
- Producing a total with no dominant term named, so nobody knows which input to argue about.
- Confusing 90 days of retention with 90 days of growth.

## Level calibration

- **Mid:** gets to 180 million a day and 7,500 a second at peak, with units, and identifies the encoding as the term that matters.
- **Senior:** the same, plus the fleet sized from a utilisation target rather than raw capacity, and the buffer question answered with a drain time rather than a shrug.
- **Lead:** says what the team should measure and alert on: samples per second against the target, buffer depth in seconds rather than messages, storage growth against the retention window, and a threshold that means stop.
- **Staff:** names the assumption that breaks first. Usually it is the driving hour, which is an average over a fleet whose distribution is nothing like uniform, or the flat 15% peak, which hides a regional peak that is much sharper than a global one.

## Follow-ups

- The product team wants the sample interval down from 5 seconds to 1. Which figures change and by how much?
- Vehicles lose connectivity in a tunnel and upload a backlog on reconnection. What does that do to your peak?
- What do you keep after 90 days, and what does keeping it cost?
- Someone proposes an index on vehicle id and timestamp. What does that do to the storage figure?
- The fleet triples. Which part of this design changes first, and which part does not change at all?
