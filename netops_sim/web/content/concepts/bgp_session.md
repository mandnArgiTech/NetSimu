title: BGP session
---
# BGP session

A **BGP session** (or *neighbor*, or *peering*) is a TCP connection between two routers that's exchanging routing information using the Border Gateway Protocol. Each side has an ASN (autonomous system number); each side announces prefixes it can reach; each side picks best paths from what its peers tell it.

In NetSimu the BGP sessions live between the NSX [Tier-0](concept:tier0) (ASN 65100) and the upstream [ToRs](concept:tor) (ASN 65001 or 65002). The T0 announces overlay prefixes (the [segment](concept:segment) CIDRs); the ToRs announce external prefixes back. Both sides install routes from the other side; that's how north-south traffic finds its way.

A BGP session goes through states — `Idle` → `Connect` → `Active` → `OpenSent` → `OpenConfirm` → `Established` — and in normal operation it stays at `Established`. When something disrupts the underlying TCP connection (link flap, MTU drop, peer reboot), the session goes `Idle` and prefixes get withdrawn; once it re-establishes, prefixes come back. The gap is the outage. The lab's `bgp_flap` scenario walks through this with a 45-second flap and the cascading effects on traffic.

**See also:** [BGP](concept:bgp), [Tier-0 gateway](concept:tier0).
