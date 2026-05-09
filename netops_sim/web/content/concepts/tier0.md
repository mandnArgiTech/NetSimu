title: Tier-0 gateway
---
# Tier-0 gateway

A **Tier-0 gateway** is the NSX router that connects the overlay to the outside world. Anything leaving the NSX fabric — VMs talking to the internet, on-premise services, other data centers — exits through a T0. It sits on top of the [NSX Edge nodes](concept:nsx_edge), runs in active-standby or active-active, and peers [BGP](concept:bgp) with the underlay [ToRs](concept:tor) so external reachability is exchanged.

In NetSimu the T0 (`t0-prod`) lives on edge-01 and edge-02, has ASN 65100, and BGP-peers with tor-01 and tor-02. It announces overlay [segment](concept:segment) prefixes upstream and learns external prefixes (default routes, partner data centers) from the ToRs. When that BGP session is healthy, traffic flows; when it flaps, north-south breaks until adjacency re-establishes.

The T0 is the most heavily-loaded data-plane object in a typical NSX deployment because every north-south packet hits it. That's also why it's the most visible point when something goes wrong: latency spikes, dropped sessions, asymmetric paths — all show up at the T0 first.

**See also:** [NSX Edge node](concept:nsx_edge), [BGP](concept:bgp), [N-S vs E-W](concept:encapsulation).
