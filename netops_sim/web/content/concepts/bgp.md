title: BGP (Border Gateway Protocol)
---
# BGP (Border Gateway Protocol)

**BGP** is the routing protocol that holds the modern internet together — and, increasingly, the one that holds modern data centers together too. In NSX deployments, BGP is what gets overlay reachability *out* into the underlay so external clients can reach VMs.

The way it works: each speaker has an Autonomous System Number (ASN); two speakers form a TCP connection (a *session* or *neighbor* relationship); they exchange `UPDATE` messages announcing the prefixes they can reach. Each side picks best paths from what it learns. When a session disconnects, the prefixes learned through it get withdrawn and routing reconverges around the remaining sessions.

In NetSimu, the NSX [Tier-0 gateway](concept:tier0) (ASN 65100) peers with [ToR](concept:tor) switches (ASN 65001 and 65002 by rack). The T0 announces overlay prefixes (e.g. `10.50.1.0/24` for the web VPC); the ToRs announce default routes back. When that session is *Established*, north-south traffic flows. When it flaps to *Idle* — which is what the `bgp_flap` lab scenario simulates for 45 seconds — every prefix learned from the peer disappears, and traffic dependent on it stops.

BGP is also what makes ECMP (Equal-Cost Multi-Path) work in a leaf-spine fabric: a ToR has multiple equal-cost paths to any other rack via different spines, and BGP installs them all. When one spine fails, BGP withdraws routes through it and traffic shifts onto the survivors automatically.

**See also:** [BGP session](concept:bgp_session), [Tier-0](concept:tier0), [ToR](concept:tor).
