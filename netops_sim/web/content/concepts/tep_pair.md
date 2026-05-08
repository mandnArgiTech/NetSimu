title: TEP pair
---
# TEP pair

A **TEP pair** is a logical edge between two host [TEPs](concept:tep) — one tunnel endpoint on each end. NSX maintains telemetry per pair (drop rate, encapsulation errors, last-seen heartbeat) because that's the granularity at which overlay communication actually fails or succeeds.

If you have N hosts in a cluster, you have N×(N-1)/2 TEP pairs — a full mesh. NetSimu's reference cluster has 4 production hosts, so 6 TEP pairs. Each pair's health depends on both its endpoints AND the underlay path between them. A bad cable on a single ToR can degrade several TEP pairs at once.

When you're debugging an overlay problem, looking at TEP-pair telemetry is often more useful than looking at individual TEPs. A TEP that says "I'm healthy" but is one end of a pair with high drop rate is telling you the problem isn't on the local end — it's somewhere on the underlay path between this host and the specific peer.

**See also:** [TEP](concept:tep), [GENEVE](concept:geneve).
