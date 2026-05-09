title: Spine switch
---
# Spine switch

A **spine** is one of the top-tier switches in a leaf–spine fabric. Every Top-of-Rack switch ([ToR](concept:tor)) connects to every spine, so any rack can reach any other rack in exactly two hops: leaf → spine → leaf. Spines do not connect to hosts directly; their job is to forward packets between ToRs at line rate.

In NetSimu's reference topology there are two spines (Arista 7280SR3, ASN 65000), each connected to all four ToRs. They speak [BGP](concept:bgp) with the ToRs to advertise reachability, and they carry tagged Layer 2 traffic on a few VLANs (notably VLAN 1647, the [TEP](concept:tep) transport VLAN that carries [GENEVE](concept:geneve)-encapsulated overlay traffic).

When a spine fails, half the underlay path capacity disappears. ECMP across the remaining spines absorbs the loss for traffic volume, but if both spines fail the rack is isolated. In production you'd typically run three or four spines for redundancy headroom; two is the textbook minimum.

**See also:** [BGP](concept:bgp), [VLAN](concept:vlan), [encapsulation](concept:encapsulation).
