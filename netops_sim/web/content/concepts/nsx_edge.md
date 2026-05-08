title: NSX Edge node
---
# NSX Edge node

An **NSX Edge node** is a special VM (or bare-metal appliance) that runs the *services* the overlay can't run on every host: north-south routing via [Tier-0 gateways](concept:tier0), NAT, load balancing, IPSec VPN, DHCP relay. While the Edge is technically a VM running on an ESX host, it's part of the NSX control/data plane, not a workload.

In NetSimu the two Edges (`edge-01`, `edge-02`) live on hosts in the *cluster-edge* cluster (host-05 and host-06 by default). They run in active-standby for the Tier-0 gateway, so traffic leaving the overlay toward the internet passes through one Edge at a time. If that Edge dies, the standby takes over and traffic flow resumes within a few seconds.

Edges peer [BGP](concept:bgp) with the [ToRs](concept:tor) — that's how reachability for overlay [segments](concept:segment) is announced into the underlay. When the BGP session flaps, traffic that was going north-south stops working until BGP re-establishes; the lab's `bgp_flap` scenario walks through that cascade.

**See also:** [Tier-0 gateway](concept:tier0), [BGP](concept:bgp), [segment](concept:segment).
