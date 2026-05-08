title: Transit Gateway (TGW)
---
# Transit Gateway (TGW)

The **Transit Gateway** in NSX is the cross-VPC routing object inside a [Project](concept:nsx_project). VPCs attach to the TGW; the TGW itself attaches to the [Tier-0](concept:tier0). Traffic from one VPC to another goes VPC → TGW → other VPC; traffic leaving the project entirely goes VPC → TGW → T0 → outside.

There are two flavours: *centralized* (all inter-VPC traffic hairpins through the TGW's data plane on a few Edge nodes — simple, easier to debug, but a bottleneck and a blast radius) and *distributed* (the routing decisions happen in the hypervisor on each host — faster, scales better, harder to introspect). NetSimu uses centralized by default to keep the lab simple and to make policy changes visible at one chokepoint.

If you've used AWS Transit Gateway, the concept is similar — it's a hub-and-spoke router that VPCs share. The NSX TGW is also where you'd attach IPSec/VPN gateways or peer to other Projects.

**See also:** [VPC](concept:vpc), [Tier-0 gateway](concept:tier0), [NSX Project](concept:nsx_project).
